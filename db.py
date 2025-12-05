# db.py
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import Optional
import os

DB_URL = os.getenv("TUTOR_DB", "sqlite:///./tutor.db")
engine = create_engine(DB_URL, echo=False)

class UserProgress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    topic: str
    current_lesson_idx: int = 0
    mastery: float = 0.0

def init_db():
    SQLModel.metadata.create_all(engine)

def get_progress(user_id: str, topic: str):
    with Session(engine) as s:
        q = s.exec(select(UserProgress).where(UserProgress.user_id==user_id, UserProgress.topic==topic)).first()
        return q

def upsert_progress(user_id: str, topic: str, idx: int | None = None, mastery: float | None = None):
    with Session(engine) as s:
        obj = s.exec(select(UserProgress).where(UserProgress.user_id==user_id, UserProgress.topic==topic)).first()
        if not obj:
            obj = UserProgress(user_id=user_id, topic=topic)
        if idx is not None:
            obj.current_lesson_idx = idx
        if mastery is not None:
            obj.mastery = mastery
        s.add(obj)
        s.commit()
        s.refresh(obj)
        return obj
