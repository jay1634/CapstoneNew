import math
from functools import lru_cache
import requests


# =========================
# ✅ FREE GEOCODING (NOMINATIM)
# =========================
@lru_cache(maxsize=100)
def geocode(city: str):
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city, "format": "json", "limit": 1}
        headers = {"User-Agent": "travel-planner-capstone"}

        r = requests.get(url, params=params, headers=headers, timeout=8)
        data = r.json()

        if not data:
            return None

        return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None


# =========================
# ✅ OSRM REAL ROAD ROUTING (CAR)
# =========================
def osrm_route(lat1, lon1, lat2, lon2):
    try:
        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{lon1},{lat1};{lon2},{lat2}"
        )
        params = {"overview": "full", "geometries": "geojson"}

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if "routes" not in data or not data["routes"]:
            return None

        route = data["routes"][0]

        return {
            "distance_km": round(route["distance"] / 1000, 2),
            "time_min": int(route["duration"] / 60),
            "geometry": route["geometry"]["coordinates"],  # [[lon,lat], ...]
        }

    except Exception:
        return None


# =========================
# ✅ FALLBACK HAVERSINE
# =========================
def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.asin(math.sqrt(a))
    return round(R * c, 2)


def _time_minutes(distance_km: float, speed_kmph: float) -> int:
    if speed_kmph <= 0:
        return 0
    return int(round((distance_km / speed_kmph) * 60))


# =========================
# ✅ MULTI-MODAL ROUTE ENGINE WITH MAP DATA
# =========================
def get_multiple_routes(origin: str, destination: str):

    src = geocode(origin)
    dst = geocode(destination)

    if not src or not dst:
        base_km = 500.0
        route_geometry = []
        origin_city = origin.title()
        dest_city = destination.title()
    else:
        lat1, lon1 = src
        lat2, lon2 = dst

        osrm = osrm_route(lat1, lon1, lat2, lon2)

        if osrm:
            base_km = osrm["distance_km"]
            route_geometry = osrm["geometry"]
        else:
            base_km = haversine_km(lat1, lon1, lat2, lon2)
            route_geometry = []

        origin_city = origin.title()
        dest_city = destination.title()

    if base_km < 20:
        base_km = 20.0

    SPEED_CAR = 50.0
    SPEED_BUS = 40.0
    SPEED_TRAIN = 70.0

    # ⭐ RECOMMENDED
    car1 = round(base_km * 0.10, 2)
    train1 = round(base_km * 0.75, 2)
    bus1 = round(base_km - car1 - train1, 2)

    recommended = {
        "total_distance_km": round(car1 + train1 + bus1, 2),
        "total_time_min": (
            _time_minutes(car1, SPEED_CAR)
            + _time_minutes(train1, SPEED_TRAIN)
            + _time_minutes(bus1, SPEED_BUS)
        ),
        "geometry": route_geometry,
        "segments": [
            {"mode": "car", "from": f"{origin_city} Home", "to": f"{origin_city} Station", "distance_km": car1, "time_min": _time_minutes(car1, SPEED_CAR)},
            {"mode": "train", "from": f"{origin_city} Station", "to": f"{dest_city} Station", "distance_km": train1, "time_min": _time_minutes(train1, SPEED_TRAIN)},
            {"mode": "bus", "from": f"{dest_city} Station", "to": f"{dest_city} Hotel", "distance_km": bus1, "time_min": _time_minutes(bus1, SPEED_BUS)},
        ],
    }

    # ⚡ FASTEST
    fastest = {
        "total_distance_km": round(base_km * 0.95, 2),
        "total_time_min": _time_minutes(base_km, SPEED_TRAIN),
        "geometry": route_geometry,
        "segments": [
            {"mode": "train", "from": origin_city, "to": dest_city, "distance_km": round(base_km * 0.95, 2), "time_min": _time_minutes(base_km, SPEED_TRAIN)},
        ],
    }

    # 💸 CHEAPEST
    cheapest = {
        "total_distance_km": round(base_km, 2),
        "total_time_min": _time_minutes(base_km, SPEED_BUS),
        "geometry": route_geometry,
        "segments": [
            {"mode": "bus", "from": origin_city, "to": dest_city, "distance_km": round(base_km, 2), "time_min": _time_minutes(base_km, SPEED_BUS)},
        ],
    }

    return {
        "recommended": recommended,
        "fastest": fastest,
        "cheapest": cheapest,
    }
