from typing import Dict, Any, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .llm_client import chat_with_llm
from .rag_pipeline import retrieve_context
from .itinerary import build_itinerary
from .memory import memory

from .tools.free_routes_tool import get_multiple_routes
from .tools.weather_tool import get_live_weather
import re

app = FastAPI(title="Travel Planner Chatbot")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


class ChatRequest(BaseModel):
    session_id: str
    message: str
    name: str | None = None


class ChatResponse(BaseModel):
    reply: str
    used_rag: bool


class ItineraryRequest(BaseModel):
    session_id: str
    destination: str
    days: int = 3
    budget: float = 500.0
    interests: List[str] = []
    food_preferences: str | None = None


class ItineraryResponse(BaseModel):
    itinerary_text: str


@app.get("/")
def root() -> Dict[str, str]:
    return {"message": "Travel planner backend running"}


from .tools.weather_tool import get_live_weather
import re


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(body: ChatRequest):
  

    if body.name:
        memory.update_prefs(body.session_id, {"name": body.name})

    # ✅ CITY EXTRACTION
    city_match = re.findall(
        r"visit ([A-Za-z ]+)|in ([A-Za-z ]+)|weather in ([A-Za-z ]+)",
        body.message,
        re.IGNORECASE,
    )

    extracted_city = None
    if city_match:
        extracted_city = next(
            (c.strip() for group in city_match for c in group if c),
            None,
        )

    # ✅ LIVE WEATHER (FORCED)
    weather_info = None
    if extracted_city:
        weather_info = get_live_weather(extracted_city)

    # ✅ RAG + MEMORY
    rag_context, _ = retrieve_context(body.message, k=4)
    history = memory.get_history(body.session_id)

    system_msg = (
        "You are a professional travel expert. "
        "You MUST strictly use the LIVE WEATHER data if provided. "
        "Never ignore it."
    )

    if weather_info:
        prompt = (
            f"LIVE WEATHER DATA (USE THIS):\n{weather_info}\n\n"
            f"DOCUMENT CONTEXT:\n{rag_context}\n\n"
            f"USER QUESTION:\n{body.message}\n\n"
            "Now give FINAL weather-based travel advice."
        )
    else:
        prompt = (
            f"DOCUMENT CONTEXT:\n{rag_context}\n\n"
            f"USER QUESTION:\n{body.message}"
        )

    reply = chat_with_llm(prompt, system_message=system_msg, history=history)

    # ✅ FORCE weather into visible reply
    if weather_info and "ERROR" not in weather_info:
        reply = f"🌦️ {weather_info}\n\n{reply}"

    memory.add_turn(body.session_id, f"User: {body.message}")
    memory.add_turn(body.session_id, f"Assistant: {reply}")

    return ChatResponse(reply=reply, used_rag=True)


@app.post("/generate_itinerary", response_model=ItineraryResponse)
def generate_itinerary_endpoint(body: ItineraryRequest) -> ItineraryResponse:
    # store prefs
    memory.update_prefs(
        body.session_id,
        {
            "destination": body.destination,
            "days": body.days,
            "budget": body.budget,
            "interests": body.interests,
            "food_preferences": body.food_preferences,
        },
    )

    question = f"Travel guide and main attractions for {body.destination}"
    rag_context, _ = retrieve_context(question, k=6)

    text = build_itinerary(
        destination=body.destination,
        days=body.days,
        budget=body.budget,
        interests=body.interests,
        food_pref=body.food_preferences,
        rag_context=rag_context,
    )
    return ItineraryResponse(itinerary_text=text)

class RouteRequest(BaseModel):
    origin: str
    destination: str


@app.post("/routes")
def routes_endpoint(body: RouteRequest):
    return get_multiple_routes(body.origin, body.destination)
