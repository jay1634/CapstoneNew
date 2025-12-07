import requests

BASE_URL = "http://127.0.0.1:8000"


def api_chat(session_id: str, message: str, name: str | None = None):
    payload = {
        "session_id": session_id,
        "message": message,
        "name": name,
    }
    res = requests.post(f"{BASE_URL}/chat", json=payload, timeout=30)
    res.raise_for_status()
    return res.json()


def api_generate_itinerary(
    session_id: str,
    destination: str,
    days: int,
    budget: float,
    interests,
    food_preferences: str | None,
):
    payload = {
        "session_id": session_id,
        "destination": destination,
        "days": days,
        "budget": budget,
        "interests": interests,
        "food_preferences": food_preferences,
    }
    res = requests.post(f"{BASE_URL}/generate_itinerary", json=payload, timeout=60)
    res.raise_for_status()
    return res.json()
