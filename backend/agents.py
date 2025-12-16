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


def _clean_text(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    # Remove markdown fences if any
    s = re.sub(r"^```.*?\n", "", s, flags=re.DOTALL)
    s = re.sub(r"```$", "", s)
    return s.strip()


# =====================================================================================
# 1. PLANNER AGENT
# =====================================================================================

def planner(topic: str) -> List[Dict[str, str]]:
    """
    Create a simple 3-step lesson plan.
    """
    
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
        - 1 short paragraph ( around 50 - 150 words)
        - Clear explanations in simple language
        - End with a short 1–2 sentence summary

        If helpful, use the context below:
        {context}

    """
    tutorial = _clean_text(_call_llm(prompt))
    
    # Now generate a question + expected answer
    question_prompt = f"""
        Based ONLY on the tutorial below, write ONE clear quiz question in a single sentence to test understanding.

        Tutorial:
        {tutorial}

        Return ONLY the question , do not try to return answer associated with it please.
    """
    question = _clean_text(_call_llm(question_prompt))
    
    
    # Expected answer prompt
    answer_prompt = f"""
        Based ONLY on the tutorial below, write a concise expected answer to the question provided.  

        Tutorial:
        {tutorial}  
        Question:
        {question}
        Return ONLY the expected answer in a single sentence (of about 10-20 words).
    """
    expected_answer = _clean_text(_call_llm(answer_prompt))
    
    
    
    
    return {
        "tutorial": tutorial,
        "question": question,
        "expected_answer": expected_answer,
    }
    



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

        Return ONLY either "good" or "bad":
        
    """
    rating = _clean_text(_call_llm(prompt, temperature=0.0, max_tokens=400))
    print("Tutorial quality rating:", rating)
    
    return rating


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
   
    # 2. RAG retrieval (use lesson_title as query)
    retrieved = rag_retrieve(lesson_title)

    # 3. Tutor generation with validation/retries
    tutor_data = tutor_generate(lesson_title, retrieved, max_retries=3)
    
    # 4. Evaluate tutorial quality and optionally regenerate (1 quick retry)
    rating = evaluator_check(tutor_data["tutorial"], lesson_title)
    
    while rating.lower() != "good":
        print("Regenerating tutorial due to low quality...")
        tutor_data = tutor_generate(lesson_title, retrieved, max_retries=2)
        rating = evaluator_check(tutor_data["tutorial"], lesson_title)
        
    
    # 5. Store tutorial to FAISS for later retrieval
    try:
        store_lesson_content(lesson_title, tutor_data["tutorial"])
    except Exception:
        pass
    
    return {
        "lesson_plan": lessons,
        "lesson_title": lesson_title,
        "tutorial": tutor_data["tutorial"],
        "question": tutor_data["question"],
        "expected_answer": tutor_data["expected_answer"],
        "evaluation": rating
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
    student_answer = student_answer.strip()
    expected_answer = expected_answer.strip()
    
    # Correctness prompt
    prompt = f"""
        You are an expert evaluator.
        Given the expected answer and the student's answer, determine if the student's answer demonstrates mastery of the topic.
        Expected Answer:
        {expected_answer}
        Student's Answer:
        {student_answer}    
        Is the student's answer essentially correct?
        Respond with ONLY one word: yes or no.
    """
    
    correctness = _clean_text(_call_llm(prompt, temperature=0.0, max_tokens=50)).lower()
    
    correct = correctness.startswith("y")
    
    
    # Mastery prompt
    mastery_prompt = f"""
        You are grading understanding depth of the student on the below lesson.
        Lesson: {lesson_title}

        Below is the expected answer and the student's answer.
        Expected answer:
        {expected_answer}
        Student answer:
        {student_answer}

        Rate the student's mastery of the topic on a scale from 0 to 1 according to the below scale.
        - 1.0 = fully correct and clear
        - 0.7 = mostly correct, minor gaps
        - 0.4 = partially correct
        - 0.0 = incorrect or irrelevant

        PLEASE Return ONLY the mastery score between 0 to 1 (single digit) and nothing else please.
    """
    
    mastery = _clean_text(_call_llm(mastery_prompt, temperature=0.0, max_tokens=10))
    try:
        mastery = re.findall(r"0\.\d+|1\.0|1", mastery)[0]
        mastery = float(mastery)
    except Exception:
        mastery = 0.0  # default if parsing fails

    print("Mastery score:", mastery)
    print("Type:", type(mastery))
    
    
    # Feedback prompt
    feedback_prompt = f"""
        You are giving constructive feedback to a learner.

        Lesson: {lesson_title}

        Expected answer:
        {expected_answer}

        Student answer:
        {student_answer}

        Write ONE short constructive sentence (feedback) in about 20-30 words that you will give to the student (no emojis).
    """
    
    feedback = _clean_text(_call_llm(feedback_prompt, temperature=0.2, max_tokens=150))
    
    
    return {
        "correct": correct,
        "mastery": mastery,
        "feedback": feedback
    }
    

    
