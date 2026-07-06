"""Weather forecasting web app powered by Open-Meteo (no API key required)."""

from __future__ import annotations

import os
import re
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

COORD_PATTERN = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)\s*$"
)

WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Dense drizzle", "🌦️"),
    61: ("Slight rain", "🌧️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    71: ("Slight snow", "🌨️"),
    73: ("Moderate snow", "🌨️"),
    75: ("Heavy snow", "🌨️"),
    77: ("Snow grains", "🌨️"),
    80: ("Slight rain showers", "🌦️"),
    81: ("Moderate rain showers", "🌦️"),
    82: ("Violent rain showers", "⛈️"),
    85: ("Slight snow showers", "🌨️"),
    86: ("Heavy snow showers", "🌨️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with slight hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️"),
}


def describe_weather(code: int | None) -> tuple[str, str]:
    if code is None:
        return ("Unknown", "🌡️")
    return WMO_CODES.get(code, ("Unknown", "🌡️"))


def parse_coordinates(query: str) -> tuple[float, float] | None:
    match = COORD_PATTERN.match(query)
    if not match:
        return None

    latitude = float(match.group(1))
    longitude = float(match.group(2))
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def format_place_label(name: str, admin1: str | None, country: str | None) -> str:
    parts = [part for part in (name, admin1, country) if part]
    return ", ".join(parts)


def normalize_open_meteo_result(item: dict, index: int) -> dict:
    name = item.get("name") or "Unknown place"
    admin1 = item.get("admin1")
    country = item.get("country")
    feature = (item.get("feature_code") or "place").lower()

    return {
        "id": f"om-{item.get('id', index)}",
        "name": name,
        "label": format_place_label(name, admin1, country),
        "latitude": item["latitude"],
        "longitude": item["longitude"],
        "country": country,
        "admin1": admin1,
        "place_type": feature.replace("_", " "),
        "source": "open-meteo",
    }


def normalize_nominatim_result(item: dict, index: int) -> dict:
    display_name = item.get("display_name") or "Unknown place"
    name = item.get("name") or display_name.split(",")[0].strip()
    place_type = (item.get("type") or item.get("class") or "place").replace("_", " ")

    return {
        "id": f"osm-{item.get('osm_id', index)}",
        "name": name,
        "label": display_name,
        "latitude": float(item["lat"]),
        "longitude": float(item["lon"]),
        "country": None,
        "admin1": None,
        "place_type": place_type,
        "source": "openstreetmap",
    }


def places_are_nearby(left: dict, right: dict, threshold_km: float = 8.0) -> bool:
    lat_diff = abs(left["latitude"] - right["latitude"])
    lon_diff = abs(left["longitude"] - right["longitude"])
    return lat_diff < threshold_km / 111 and lon_diff < threshold_km / 111


def search_places(query: str, limit: int = 12) -> list[dict]:
    places: list[dict] = []

    try:
        response = requests.get(
            GEOCODING_URL,
            params={"name": query, "count": limit, "language": "en", "format": "json"},
            timeout=10,
        )
        response.raise_for_status()
        for index, item in enumerate(response.json().get("results") or []):
            places.append(normalize_open_meteo_result(item, index))
    except requests.RequestException:
        pass

    if len(places) < limit:
        try:
            response = requests.get(
                NOMINATIM_URL,
                params={"q": query, "format": "json", "limit": limit, "addressdetails": 0},
                headers={"User-Agent": "WeatherForecastApp/1.0"},
                timeout=10,
            )
            response.raise_for_status()
            for index, item in enumerate(response.json() or []):
                candidate = normalize_nominatim_result(item, index)
                if any(places_are_nearby(candidate, existing) for existing in places):
                    continue
                places.append(candidate)
                if len(places) >= limit:
                    break
        except requests.RequestException:
            pass

    return places[:limit]


def location_from_coordinates(latitude: float, longitude: float) -> dict:
    return {
        "name": f"{latitude:.4f}°, {longitude:.4f}°",
        "label": f"Coordinates {latitude:.4f}°, {longitude:.4f}°",
        "latitude": latitude,
        "longitude": longitude,
        "country": None,
        "admin1": None,
        "place_type": "coordinates",
    }


def location_from_place(place: dict) -> dict:
    return {
        "name": place["name"],
        "label": place["label"],
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "country": place.get("country"),
        "admin1": place.get("admin1"),
        "place_type": place.get("place_type"),
    }


def fetch_forecast(latitude: float, longitude: float) -> dict:
    response = requests.get(
        FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "weather_code,wind_speed_10m,wind_direction_10m,precipitation",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,wind_speed_10m_max",
            "timezone": "auto",
            "forecast_days": 7,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def wind_direction(degrees: float | None) -> str:
    if degrees is None:
        return "N/A"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = round(degrees / 45) % 8
    return directions[index]


def build_forecast_payload(location: dict) -> dict:
    forecast = fetch_forecast(location["latitude"], location["longitude"])
    current = forecast.get("current") or {}
    daily = forecast.get("daily") or {}

    current_code = current.get("weather_code")
    current_label, current_icon = describe_weather(current_code)

    daily_forecast = []
    dates = daily.get("time") or []
    for index, date_str in enumerate(dates):
        code = (daily.get("weather_code") or [None])[index]
        label, icon = describe_weather(code)
        daily_forecast.append(
            {
                "date": date_str,
                "day_name": datetime.strptime(date_str, "%Y-%m-%d").strftime("%a"),
                "icon": icon,
                "label": label,
                "temp_max": (daily.get("temperature_2m_max") or [None])[index],
                "temp_min": (daily.get("temperature_2m_min") or [None])[index],
                "precip_prob": (daily.get("precipitation_probability_max") or [None])[
                    index
                ],
            }
        )

    return {
        "location": {
            "name": location.get("name"),
            "label": location.get("label") or location.get("name"),
            "country": location.get("country"),
            "admin1": location.get("admin1"),
            "place_type": location.get("place_type"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "timezone": forecast.get("timezone"),
        },
        "current": {
            "temperature": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "wind_direction": wind_direction(current.get("wind_direction_10m")),
            "precipitation": current.get("precipitation"),
            "weather_code": current_code,
            "label": current_label,
            "icon": current_icon,
            "time": current.get("time"),
        },
        "daily": daily_forecast,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/places")
def places_api():
    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify({"error": "Please enter a place name."}), 400

    coordinates = parse_coordinates(query)
    if coordinates:
        latitude, longitude = coordinates
        place = location_from_coordinates(latitude, longitude)
        return jsonify({"places": [place], "query": query})

    try:
        places = search_places(query)
        if not places:
            return jsonify({"error": f'No places found for "{query}".'}), 404
        return jsonify({"places": places, "query": query})
    except requests.RequestException:
        return jsonify({"error": "Unable to reach the location service. Try again later."}), 502


@app.route("/api/weather")
def weather_api():
    latitude = request.args.get("lat", type=float)
    longitude = request.args.get("lon", type=float)
    query = (request.args.get("q") or "").strip()

    try:
        if latitude is not None and longitude is not None:
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                return jsonify({"error": "Invalid coordinates."}), 400
            location = location_from_coordinates(latitude, longitude)
        elif query:
            coordinates = parse_coordinates(query)
            if coordinates:
                location = location_from_coordinates(*coordinates)
            else:
                places = search_places(query, limit=1)
                if not places:
                    return jsonify({"error": f'No places found for "{query}".'}), 404
                location = location_from_place(places[0])
        else:
            return jsonify({"error": "Please enter a place name or coordinates."}), 400

        payload = build_forecast_payload(location)
        return jsonify(payload)
    except requests.RequestException:
        return jsonify({"error": "Unable to reach the weather service. Try again later."}), 502


if __name__ == "__main__":
    from server import main

    main()
