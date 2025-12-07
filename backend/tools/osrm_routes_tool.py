import requests
import polyline

def get_osrm_route(lat1, lon1, lat2, lon2):
    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}"
        f"?overview=full&geometries=polyline"
    )

    r = requests.get(url, timeout=15)
    data = r.json()

    if "routes" not in data:
        raise Exception("OSRM routing failed")

    route = data["routes"][0]

    return {
        "distance_km": round(route["distance"] / 1000, 2),
        "duration_min": round(route["duration"] / 60),
        "geometry": polyline.decode(route["geometry"]),
    }
