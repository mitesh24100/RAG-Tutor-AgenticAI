from fastapi import FastAPI
from pydantic import BaseModel
from db import init_db, upsert_progress, get_progress
from agents import planner, teacher, quiz_maker, feedback, store_lesson_content, retrieve_related
import uvicorn

app = FastAPI()

init_db()

class StartReq(BaseModel):
    user_id: str
    topic: str
    
class SubmitReq(BaseModel):
    user_id: str
    topic: str
    answers: list[str]

@app.post("/start")
def start(req: StartReq):
    