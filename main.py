from fastapi import Request
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from personas import get_game_agent
from activities import get_activity_task
from crewai import Task, Crew, Process
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI()

class ChatRequest(BaseModel):
    persona: str
    activity: str
    user_input: str
    username: str
    history: list[str]  # Full list of previous chat lines


@app.post("/chat")
def chat(req: ChatRequest, request: Request):
    print("🧪 DEBUG | GEMINI_API_KEY =", os.getenv("GEMINI_API_KEY"))
    persona_data = get_game_agent(req.persona, req.username)
    if not persona_data:
        raise HTTPException(status_code=404, detail="Persona not found")

    task_description, expected_output = get_activity_task(
    activity_name=req.activity,
    persona=persona_data,
    user_input=req.user_input,
    history=req.history,
    username=req.username
)


    if not task_description:
        raise HTTPException(status_code=400, detail="Activity not supported yet")

    task = Task(
        description=task_description,
        expected_output=expected_output,
        agent=persona_data["agent"]
    )

    crew = Crew(
        agents=[persona_data["agent"]],
        tasks=[task],
        process=Process.sequential
    )

    try:
        result = crew.kickoff()
        return {"reply": result}
    except Exception as e:
        return {"error": str(e)}
