from fastapi import Request
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from personas import get_game_agent
from activities import get_activity_task
from crewai import Task, Crew, Process
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime
import os
import httpx
import time

load_dotenv()
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your website's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
ACTIVITY_XP = {
    # Friend
    "city_shuffle": 3,
    "nickname_game": 3,
    "text_truth_or_dare": 3,
    "dream_room_builder": 5,
    "friendship_scrapbook": 5,
    "scenario_shuffle": 5,
    "letter_from_the_future": 8,
    "undo_button": 8,
    "friendship_farewell": 8,
    # Romantic
    "date_duel": 3,
    "flirt_or_fail": 3,
    "whats_in_my_pocket": 3,
    "love_in_another_life": 5,
    "daily_debrief": 5,
    "mood_meal": 5,
    "unsent_messages": 8,
    "i_would_never": 8,
    "breakup_simulation": 8,
    # Mentor
    "one_minute_advice_column": 3,
    "word_of_the_day": 3,
    "compliment_mirror": 3,
    "if_i_were_you": 5,
    "burning_questions_jar": 5,
    "skill_swap_simulation": 5,
    "buried_memory_excavation": 8,
    "failure_autopsy": 8,
    "letters_you_never_got": 8,
    # Spiritual
    "symbol_speak": 3,
    "spiritual_whisper": 3,
    "story_fragment": 3,
    "desire_detachment_game": 5,
    "god_in_the_crowd": 5,
    "past_life_memory": 5,
    "karma_knot": 8,
    "mini_moksha_simulation": 8,
    "divine_mirror": 8,
}
class ChatRequest(BaseModel):
    persona: str
    activity: str
    user_input: str
    username: str
    email: str = "" 
    history: list[str]  # Full list of previous chat lines


def award_xp_to_user(email, bot_id, xp_amount, coin_amount=0, reason="Game activity"):
    XP_BACKEND_URL = "https://novibe-backend-233451779807.us-central1.run.app/award-xp"
    payload = {
        "email": email,
        "bot_id": bot_id,
        "xp_amount": xp_amount,
        "coin_amount": coin_amount,
        "reason": reason
    }
    try:
        response = httpx.post(XP_BACKEND_URL, json=payload, timeout=5)
        return response.json()
    except Exception as e:
        print(f"Failed to award XP: {e}")
        return None

def get_current_user_xp(email, bot_id):
    XP_STATUS_URL = f"https://novibe-backend-233451779807.us-central1.run.app/user-xp-current/{email}/{bot_id}"
    try:
        response = httpx.get(XP_STATUS_URL, timeout=5)
        return response.json()
    except Exception as e:
        print(f"Failed to fetch current XP: {e}")
        return None

def get_current_user_xp_with_retry(email, bot_id, retries=5, delay=1.0):
    for i in range(retries):
        result = get_current_user_xp(email, bot_id)
        if result and "detail" not in result:
            return result
        time.sleep(delay)
    return result  # Return last result even if not found

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        xp_amount = ACTIVITY_XP.get(req.activity, 2)
        print("DEBUG | Awarding XP to:", req.email, req.persona)
        xp_response = award_xp_to_user(
            email=req.email,
            bot_id=req.persona,
            xp_amount=xp_amount,
            reason=f"Completed activity: {req.activity}"
        )
        if xp_response and xp_response.get("success"):
            time.sleep(2.5)
        xp_status = get_current_user_xp_with_retry(req.email, req.persona)

        # Extract the string response from CrewOutput
        bot_response_str = result.raw if hasattr(result, "raw") else str(result)

        log_activity_message_to_supabase(
            email=req.email,
            bot_id=req.persona,
            user_message=req.user_input,
            bot_response=bot_response_str,
            platform="game_activity",
            activity_name=req.activity
        )

        print("DEBUG | XP Award Response:", xp_response)
        print("DEBUG | XP Status Response:", xp_status)
        return {
            "reply": result,
            "xp_award": xp_response,
            "xp_amount": xp_amount,
            "xp_status": xp_status
        }
    except Exception as e:
        return {"error": str(e)}

def log_activity_message_to_supabase(email, bot_id, user_message, bot_response, platform="game_activity", activity_name=None):
    now = datetime.utcnow().isoformat()
    # Ensure bot_response is a string
    if isinstance(bot_response, dict):
        bot_response = bot_response.get("raw") or bot_response.get("response") or str(bot_response)
    data = {
        "email": email,
        "bot_id": bot_id,
        "user_message": user_message,
        "bot_response": bot_response,
        "requested_time": now,
        "platform": platform
    }
    if activity_name:
        data["activity_name"] = activity_name
    print("📝 [log_activity_message_to_supabase] Inserting data:", data)  # <--- ADD THIS LINE
    try:
        res = supabase.table("message_paritition").insert(data).execute()
        print("✅ Activity message logged to Supabase:", res)
        return res
    except Exception as e:
        print("❌ Failed to log activity message to Supabase:", e)
        return None
