import requests
from ..config import OPENWEATHER_API_KEY


def get_live_weather(city: str) -> str:
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "YOUR_OPENWEATHER_API_KEY_HERE":
        return "ERROR: Weather API key is missing."

    try:
        city = city.strip()

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
        }

        res = requests.get(url, params=params, timeout=10)

        print("WEATHER RAW RESPONSE:", res.text)

        if res.status_code != 200:
            return f"ERROR: Weather API failed | City: {city} | Status: {res.status_code} | {res.text}"

        data = res.json()

        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        desc = data["weather"][0]["description"].title()
        wind = data["wind"]["speed"]

        return (
            f"{city.title()} Live Weather: {temp}°C (Feels like {feels}°C), "
            f"{desc}, Humidity {humidity}%, Wind {wind} m/s."
        )

    except Exception as e:
        return f"ERROR: Weather API crashed: {e}"
