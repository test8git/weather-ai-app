import requests
import re

from langchain_core.tools import tool
from tavily import TavilyClient
from dotenv import load_dotenv
import os

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

HEADERS = {
    "User-Agent": "GeneralAIAssistant/1.0"
}

PLACE_TYPES = {

    "restaurant":"restaurant",
    "restaurants":"restaurant",
    "hotel":"hotel",
    "hotels":"hotel",
    "hospital":"hospital",
    "atm":"atm",
    "bank":"bank",
    "fuel":"fuel",
    "petrol":"fuel",
    "petrol pump":"fuel",
    "coffee":"cafe",
    "cafe":"cafe",
    "mall":"mall",
    "shopping":"mall",
    "museum":"museum",
    "park":"park",
    "school":"school",
    "college":"college",
    "airport":"airport",
    "railway station":"station",
    "tourist":"tourism",
    "temple":"place_of_worship"
}

# Detect place category
def detect_category(question):
    q = question.lower()
    for key, value in PLACE_TYPES.items():
        if key in q:
            return value

    return "restaurant"

# Detect Location
def detect_location(question):
    m = re.search(r"\b(?:in|at|near)\s+(.+)", question, re.I)
    if m:
        return m.group(1).strip()

    return question


def geocode(location):

    params = {

        "q": location,
        "format": "json",
        "limit": 1

    }

    r = requests.get(
        NOMINATIM_URL,
        params=params,
        headers=HEADERS,
        timeout=20
    )

    data = r.json()

    if not data:
        return None

    return (
        float(data[0]["lat"]),
        float(data[0]["lon"])
    )

# overpass API search
def overpass_search(category, lat, lon):

    query = f"""
[out:json];

(
node["amenity"="{category}"](around:5000,{lat},{lon});
way["amenity"="{category}"](around:5000,{lat},{lon});
relation["amenity"="{category}"](around:5000,{lat},{lon});
);

out center;
"""

    r = requests.post(
        OVERPASS_URL,
        data=query,
        headers=HEADERS,
        timeout=40
    )

    data = r.json()

    places = []

    for item in data.get("elements", []):

        tags = item.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        lat1 = item.get("lat")
        lon1 = item.get("lon")

        if not lat1:
            center = item.get("center", {})
            lat1 = center.get("lat")
            lon1 = center.get("lon")

        places.append({
            "name": name,
            "address": tags.get("addr:full", ""),
            "lat": lat1,
            "lon": lon1,
            "google_maps":
                f"https://www.google.com/maps/search/?api=1&query={lat1},{lon1}"

        })

    return places
    

# Tavily search
def tavily_search(question):
    response = tavily.search(query=question, max_results=10)

    places = []
    for r in response["results"]:
        places.append({
            "name": r["title"],
            "url": r["url"]
        })

    return places


@tool(description="""
    Search places such as restaurants,
    hotels,
    hospitals,
    ATMs,
    petrol pumps,
    tourist attractions,
    etc.
    """)
def search_places(question: str):
    try:

        ### Use when also calling overpass API

        category = detect_category(question)
        location = detect_location(question)
        geo = geocode(location)

        if geo is None:

            return {
                "success": False,
                "message": "Unable to locate place."
            }

        lat, lon = geo
        osm_places = overpass_search(category, lat, lon)

        tavily_places = tavily_search(question)

        merged = {}

        for p in osm_places:

            merged[p["name"]] = p

        for p in tavily_places:

            if p["name"] not in merged:
                merged[p["name"]] = p

        # print(merged)

        return {

            "success": True,
            "type": "places",
            "category": category,
            "location": location,
            "places": list(merged.values())[:10]
        }

        # output = []

        # for i, place in enumerate(list(merged.values())[:5], start=1):
        #     output.append(f"""{i}. {place.get("name","")}
        #                     Address:
        #                     {place.get("address","Not Available")}
        #                     Google Maps:
        #                     {place.get("google_maps","")}
        #                     """)

        # return "\n\n".join(output)

    except Exception as e:

        # return {
        #     "success": False,
        #     "message": str(e)
        # }

        return f"Error: {e}"    