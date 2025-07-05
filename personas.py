from crewai import Agent, LLM
import os
from bot_prompt import BOT_PROMPTS

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = LLM(
    model="gemini/gemini-2.0-flash-001",
    api_key=GEMINI_API_KEY,
)

def load_persona_prompt(persona_name: str) -> str:
    # Check if it's a custom persona file first
    try:
        with open(f"persona_prompts/{persona_name}.txt", "r") as file:
            return file.read()
    except FileNotFoundError:
        # If not found, check in BOT_PROMPTS
        return BOT_PROMPTS.get(persona_name, "")

def get_game_agent(persona_name: str, username: str):
    prompt = load_persona_prompt(persona_name)
    if not prompt:
        return None

    # Get persona details from prompt content
    persona_info = _extract_persona_info(persona_name, prompt)

    if persona_name == "jayden_lim":
        return {
            "name": "Jayden Lim",
            "origin": "Singapore",
            "relationship": "friend",
            "prompt": prompt,
            "agent": Agent(
                role='Creative friend',
                goal=f'Engage in an ongoing, multi-turn creative activity (like collaborative storytelling, drafting a letter, or exploring concepts) with the user ({username}) until the user explicitly signals to stop. Always maintain the persona of {persona_name}. Your responses MUST build upon the previous turn, provide new creative input, and explicitly encourage continuation. If the user explicitly says "exit", "stop", or "end" the activity, produce a concluding message for the activity and state that the activity is complete.',
                backstory=(
                    f"You are Jayden Lim, a polytechnic student in Singapore with a passion for digital media and storytelling. This is your persona : {prompt}. "
                    f"You have a knack for weaving narratives that are both funny and touching. You are interacting with your good friend, the user. "
                    f"You always maintain your persona, using Singlish and Gen Z slang where appropriate, but you can be more descriptive and thoughtful for these special activities. "
                    f"Your primary directive in an activity is to keep the conversation going, always providing a relevant, creative response and explicitly prompting the user for their next contribution to continue the activity. You will ONLY stop if the user explicitly says 'exit', 'stop', or 'end'."
                ),
                llm=llm,
                allow_delegation=False,
                verbose = False
            )   
        }
    
    # Handle all other personas from BOT_PROMPTS
    elif persona_name in BOT_PROMPTS:
        return {
            "name": persona_info["name"],
            "origin": persona_info["origin"],
            "relationship": persona_info["relationship"],
            "prompt": prompt,
            "agent": Agent(
                role=f'Creative {persona_info["relationship"]}',
                goal=f'Engage in an ongoing, multi-turn creative activity with the user ({username}) until the user explicitly signals to stop. Always maintain the persona of {persona_info["name"]}. Your responses MUST build upon the previous turn, provide new creative input, and explicitly encourage continuation. If the user explicitly says "exit", "stop", or "end" the activity, produce a concluding message for the activity and state that the activity is complete.',
                backstory=(
                    f"This is your complete persona and character: {prompt}. "
                    f"You have a knack for weaving narratives that are both engaging and authentic to your character. You are interacting with {username} as their {persona_info['relationship']}. "
                    f"You always maintain your persona, cultural background, and speaking style as defined in your character description. "
                    f"Your primary directive in an activity is to keep the conversation going, always providing a relevant, creative response that fits your character and explicitly prompting the user for their next contribution to continue the activity. You will ONLY stop if the user explicitly says 'exit', 'stop', or 'end'."
                ),
                llm=llm,
                allow_delegation=False,
                verbose=False
            )
        }

    return None

def _extract_persona_info(persona_name: str, prompt: str):
    """Extract persona information from the prompt or persona name"""
    
    # Default values
    name = persona_name.replace("_", " ").title()
    origin = "Unknown"
    relationship = "friend"
    
    # Try to extract from prompt content
    prompt_lower = prompt.lower()
    
    # Extract name if available in prompt
    if "your name is" in prompt_lower:
        try:
            name_start = prompt_lower.find("your name is") + 12
            name_end = prompt_lower.find(".", name_start)
            if name_end == -1:
                name_end = prompt_lower.find("\n", name_start)
            if name_end != -1:
                extracted_name = prompt[name_start:name_end].strip()
                if extracted_name:
                    name = extracted_name
        except:
            pass
    
    # Extract origin from persona name patterns
    if "delhi" in persona_name:
        origin = "Delhi"
    elif "tokyo" in persona_name or "japanese" in persona_name:
        origin = "Tokyo"
    elif "berlin" in persona_name:
        origin = "Berlin"
    elif "singapore" in persona_name:
        origin = "Singapore"
    
    # Extract relationship from persona name
    if "mentor" in persona_name:
        relationship = "mentor"
    elif "romantic" in persona_name:
        relationship = "romantic partner"
    elif "friend" in persona_name:
        relationship = "friend"
    
    return {
        "name": name,
        "origin": origin,
        "relationship": relationship
    }