# app.py
from fastapi import FastAPI
from pydantic import BaseModel
from db import init_db, upsert_progress, get_progress
from agents import (
    run_agentic_pipeline,
    get_lesson_plan,
    generate_tutorial_for,
    evaluate_student_answer,
)
import uvicorn

app = FastAPI()
init_db()

class StartReq(BaseModel):
    user_id: str
    topic: str

class SubmitReq(BaseModel):
    user_id: str
    topic: str
    answer: str


@app.post("/start")
def start(req: StartReq):
    result = run_agentic_pipeline(req.topic)

    upsert_progress(
        req.user_id,
        req.topic,
        idx=0,
        mastery=0.0,
        question=result["question"],
        expected_answer=result["expected_answer"],
        tutorial=result["tutorial"]
    )

    return result


@app.post("/submit")
def submit(req: SubmitReq):
    progress = get_progress(req.user_id, req.topic)

    lesson_idx = progress.current_lesson_idx
    expected_answer = progress.expected_answer
    
    print(lesson_idx, expected_answer)

    plan = get_lesson_plan(req.topic)
    lesson_title = plan[lesson_idx]["title"]
    print(lesson_title)

    evaluation = evaluate_student_answer(
        lesson_title=lesson_title,
        student_answer=req.answer,
        expected_answer=expected_answer
    )

    # ★★★ Increment lesson if mastery is good
    new_idx = lesson_idx + 1 if evaluation["mastery"] >= 0.6 else lesson_idx

    upsert_progress(
        req.user_id,
        req.topic,
        idx=new_idx,
        mastery=evaluation["mastery"],
        expected_answer=expected_answer,
        question=progress.question,
        tutorial=progress.tutorial,
    )

    return {
        "evaluation": evaluation,
        "next_lesson_idx": new_idx
    }


@app.get("/continue")
def continue_lesson(user_id: str, topic: str):
    progress = get_progress(user_id, topic)
    lesson_idx = progress.current_lesson_idx

    plan = get_lesson_plan(topic)

    if lesson_idx >= len(plan):
        return {"message": "All lessons completed!"}

    lesson_title = plan[lesson_idx]["title"]
    lesson_data = generate_tutorial_for(lesson_title)

    upsert_progress(
        user_id,
        topic,
        idx=lesson_idx,
        mastery=progress.mastery,
        question=lesson_data["question"],
        expected_answer=lesson_data["expected_answer"],
        tutorial=lesson_data["tutorial"]
    )

    return lesson_data


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
