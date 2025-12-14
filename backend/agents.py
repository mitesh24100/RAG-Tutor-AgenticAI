# agents.py
"""
Simple Agentic Pipeline (improved):
Planner → RAG → Tutor → Evaluator (with validation + retries)

This version:
- Uses stronger prompts to force full multi-paragraph tutorials.
- Validates JSON outputs and retries when output is invalid or contains placeholder answers.
- Keeps the same function names / structure so it's compatible with your app.py and db.py.
"""

from typing import List, Dict, Any
from models import get_chat_model
from embeddings import get_embeddings
from vectorstore import create_or_load_faiss, add_texts, save_faiss, similarity_search
from utils import safe_json_load
import json
import os
import re
import time

# Load FAISS store globally (lazy load)
FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "./data/faiss_index")
_faiss_store, _emb = create_or_load_faiss(index_path=FAISS_INDEX_DIR)


# ----------------------------
# Helpers: robust LLM call + JSON parsing + validation
# ----------------------------
def _call_llm(prompt: str, temperature: float = 0.2, max_tokens: int | None = None):
    """
    Call the chat model wrapper returned by get_chat_model().
    We attempt to return a plain string (the content).
    """
    llm = get_chat_model(temperature=temperature, max_tokens=max_tokens)
    try:
        res = llm.invoke(prompt)
        # Many wrappers return an object with .content
        if hasattr(res, "content"):
            return res.content
        # sometimes it's already a string
        if isinstance(res, str):
            return res
        # fallback
        return str(res)
    except Exception as e:
        # surface minimal info but don't crash
        return f"LLM_CALL_FAILED: {e}"


def _parse_json_with_retries(raw_prompt: str, tries: int = 2, wait: float = 0.5):
    """
    Call the LLM with raw_prompt and attempt to parse JSON from output.
    Retries `tries` times if parsing fails. Returns parsed object or None.
    """
    for attempt in range(tries):
        out = _call_llm(raw_prompt)
        parsed = safe_json_load(out)
        if parsed is not None:
            return parsed, out
        time.sleep(wait)
    return None, out


def _looks_like_placeholder(s: str) -> bool:
    """
    Heuristics to detect placeholder or incomplete expected answers.
    """
    if not s or s.strip() == "":
        return True
    low = s.strip().lower()
    # common placeholders or ellipses
    if "..." in s or low.endswith("...") or low.startswith("one important") or low.startswith("an important"):
        return True
    # too short to be a real expected answer
    if len(s.strip().split()) <= 2:
        return True
    return False


# =====================================================================================
# 1. PLANNER AGENT
# =====================================================================================

def planner(topic: str) -> List[Dict[str, str]]:
    """
    Create a simple 3-step lesson plan.
    """
    prompt = f"""
You are an educational planner.

Create exactly 3 short lesson items for the topic: "{topic}".
Return ONLY a JSON array of objects with keys: title (short), goal (one sentence).

Example:
[
  {{"title": "Intro to X", "goal": "Understand basic ideas"}},
  ...
]
"""
    raw = _call_llm(prompt, temperature=0.0)
    parsed = safe_json_load(raw)
    if parsed and isinstance(parsed, list):
        return parsed
    # fallback
    return [
        {"title": f"Introduction to {topic}", "goal": "Understand basics"},
        {"title": f"Core Concepts in {topic}", "goal": "Learn essentials"},
        {"title": f"Applications of {topic}", "goal": "Apply knowledge"},
    ]


# =====================================================================================
# 2. RAG RETRIEVAL AGENT
# =====================================================================================

def rag_retrieve(query: str, k: int = 4):
    """
    RAG retrieval using FAISS. Returns a list of Document-like objects as returned by similarity_search.
    """
    global _faiss_store
    if _faiss_store is None:
        return []
    try:
        docs = similarity_search(_faiss_store, query, k=k)
        return docs
    except Exception:
        return []


def store_lesson_content(title: str, content: str):
    """
    Store generated tutorial so future lessons can retrieve it.
    """
    global _faiss_store
    _faiss_store = add_texts(
        _faiss_store,
        texts=[content],
        metadatas=[{"title": title, "content": content}],
    )
    save_faiss(_faiss_store, FAISS_INDEX_DIR)


# =====================================================================================
# 3. TUTOR AGENT (Tutorial + Question + Expected Answer) with validation
# =====================================================================================

def tutor_generate(lesson_title: str, retrieved_chunks, max_retries: int = 2):
    context = ""
    for chunk in retrieved_chunks:
        md = chunk.metadata
        context += md.get("content", "") + "\n\n"

    prompt = f"""
You are an expert instructor.
Write a detailed, friendly tutorial for the lesson:

Lesson: "{lesson_title}"

Use this structure:
- 1 short paragraphs (~200–250 words)
- Clear explanations in simple language
- Include 1–2 concrete examples
- End with a short 2–3 sentence summary
- Then produce one quiz question and its expected short correct answer.

If helpful, use the context below:
{context}

Return ONLY JSON in this exact shape:

{{
  "tutorial": "... full tutorial ...",
  "question": "... one question ...",
  "expected_answer": "... short correct answer based on the question ..."
}}
"""
    output = _call_llm(prompt)
    print(output)
    return output
    """
    for _ in range(max_retries):
        raw = _call_llm(prompt, temperature=0.2, max_tokens=1500)
        data = safe_json_load(raw)
        if data and data.get("tutorial") and data.get("question") and data.get("expected_answer"):
            return data

    # fallback
    return {
        "tutorial": f"A detailed tutorial on {lesson_title} could not be generated.",
        "question": f"What is one key idea from {lesson_title}?",
        "expected_answer": f"A key idea is a concise explanation of {lesson_title}."
    }"""



# =====================================================================================
# 4. EVALUATOR AGENT (checks tutorial quality)
# =====================================================================================

def evaluator_check(tutorial: str, lesson_title: str) -> str:
    """
    Ask the LLM to judge tutorial quality. Return JSON with 'quality' and 'reason'.
    """
    prompt = f"""
Please evaluate the following tutorial for lesson '{lesson_title}'.

Tutorial:
{tutorial}

Return ONLY JSON:
{{
  "quality": "good" or "bad" only,
  "reason": "one-sentence explanation"
}}
"""
    output = _call_llm(prompt, temperature=0.0, max_tokens=400)
    print("Evaluator output:", output)
    return output
    """
    parsed = safe_json_load(raw)
    if parsed and isinstance(parsed, dict) and "quality" in parsed:
        return parsed
    # fallback consider it good but note fallback
    return {"quality": "good", "reason": "fallback evaluation (could not parse model response)"}"""


# =====================================================================================
# 5. MAIN PIPELINE RUNNER
# =====================================================================================

def run_agentic_pipeline(topic: str) -> Dict[str, Any]:
    """
    Planner → RAG → Tutor (with validation) → Evaluator → store
    """
    # 1. Planner
    lessons = planner(topic)
    lesson_title = lessons[0]["title"]
    print(lessons, lesson_title)
    print("*******")
    # 2. RAG retrieval (use lesson_title as query)
    retrieved = rag_retrieve(lesson_title)

    # 3. Tutor generation with validation/retries
    tutor_data = tutor_generate(lesson_title, retrieved, max_retries=3)
    
    cleaned_tutor_data = tutor_data.strip()
    cleaned_tutor_data = re.sub(r"^```json|```$", "", cleaned_tutor_data).strip()
    
    cleaned_tutor_data = json.loads(cleaned_tutor_data)
    
    tutorial = cleaned_tutor_data["tutorial"]
    question = cleaned_tutor_data["question"]
    expected_answer = cleaned_tutor_data["expected_answer"]
    
    print("$$$$$$$$$$$$$$$$$$$$$$$")
    print(tutorial, question, expected_answer)
    print("*******")
    # 4. Evaluate tutorial quality and optionally regenerate (1 quick retry)
    eval_result_str = evaluator_check(tutorial, lesson_title)
    cleaned_eval_result = eval_result_str.strip()
    cleaned_eval_result = re.sub(r"^```json|```$", "", cleaned_eval_result).strip()
    
    cleaned_eval_result = json.loads(cleaned_eval_result)
    print(cleaned_eval_result["quality"])
    print(cleaned_eval_result["reason"])
    
    
    
    # 5. Store tutorial to FAISS for later retrieval
    try:
        store_lesson_content(lesson_title, tutorial)
    except Exception:
        pass
    
    return {
        "lesson_plan": lessons,
        "lesson_title": lesson_title,
        "tutorial": tutorial,
        "question": question,
        "expected_answer": expected_answer,
        "evaluation": cleaned_eval_result["quality"]
    }


# =====================================================================================
# Helper Functions for app.py
# =====================================================================================

def get_lesson_plan(topic: str):
    return planner(topic)


def generate_tutorial_for(lesson_title: str):
    retrieved = rag_retrieve(lesson_title)
    return tutor_generate(lesson_title, retrieved, max_retries=2)


def evaluate_student_answer(lesson_title: str, student_answer: str, expected_answer: str):
    """
    Evaluate student's answer semantically against expected_answer and return mastery.
    """
    prompt = f"""
You are an evaluator comparing a student's short answer to the expected correct answer.

Lesson: {lesson_title}

Expected (concise): {expected_answer}
Student answer: {student_answer}

Return ONLY JSON:
{{
  "mastery": a number between 0 and 1,
  "correct": true/false,
  "feedback": "a short constructive sentence"
}}
"""
    raw = _call_llm(prompt, temperature=0.4, max_tokens=300)
    parsed = safe_json_load(raw)
    if parsed and isinstance(parsed, dict) and "mastery" in parsed:
        # ensure numeric conversion safety
        try:
            parsed["mastery"] = float(parsed["mastery"])
        except Exception:
            parsed["mastery"] = 0.0
        return parsed
    # fallback: very conservative exact-match heuristic
    low_student = (student_answer or "").strip().lower()
    low_expected = (expected_answer or "").strip().lower()
    correct = low_expected in low_student or low_student in low_expected
    mastery = 1.0 if correct else 0.0
    feedback = "Looks good." if correct else "Answer is incomplete or not precise."
    return {"mastery": mastery, "correct": correct, "feedback": feedback}
