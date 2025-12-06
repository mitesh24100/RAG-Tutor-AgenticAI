# db.py
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional
import os

DB_URL = os.getenv("TUTOR_DB", "sqlite:///./data/tutor.db")
engine = create_engine(DB_URL, echo=False)


class UserProgress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    user_id: str
    topic: str

    # Which lesson student is on
    current_lesson_idx: int = 0

    # Most recent mastery score
    mastery: float = 0.0

    # Store generated question + expected answer
    question: Optional[str] = None
    expected_answer: Optional[str] = None

    # (Optional) store latest tutorial
    tutorial: Optional[str] = None


def init_db():
    SQLModel.metadata.create_all(engine)


def get_progress(user_id: str, topic: str):
    with Session(engine) as s:
        q = s.exec(
            select(UserProgress)
            .where(UserProgress.user_id == user_id, UserProgress.topic == topic)
        ).first()
        return q


def upsert_progress(
    user_id: str,
    topic: str,
    idx: int | None = None,
    mastery: float | None = None,
    question: str | None = None,
    expected_answer: str | None = None,
    tutorial: str | None = None,
):
    """
    Inserts or updates user progress including generated tutorial,
    question, and expected answer.
    """
    with Session(engine) as s:
        obj = s.exec(
            select(UserProgress)
            .where(UserProgress.user_id == user_id, UserProgress.topic == topic)
        ).first()

        if not obj:
            obj = UserProgress(user_id=user_id, topic=topic)

        # Update fields
        if idx is not None:
            obj.current_lesson_idx = idx
        if mastery is not None:
            obj.mastery = mastery
        if question is not None:
            obj.question = question
        if expected_answer is not None:
            obj.expected_answer = expected_answer
        if tutorial is not None:
            obj.tutorial = tutorial

        s.add(obj)
        s.commit()
        s.refresh(obj)
        return obj
