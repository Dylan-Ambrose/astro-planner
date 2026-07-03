from fastapi import FastAPI
import requests
from datetime import date, timedelta

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Astro planner is alive"}


def fetch_cloud_forecast(lat: float, lon: float):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "cloudcover",
        "forecast_days": 7,
        "timezone": "auto"
    }
    response = requests.get(url, params=params)
    return response.json()


def fetch_moon_data(lat: float, lon: float):
    results = []
    today = date.today()

    for i in range(7):
        target_date = today + timedelta(days=i)
        url = "https://api.sunrisesunset.io/json"
        params = {
            "lat": lat,
            "lng": lon,
            "date": target_date.isoformat(),
            "time_format": "24"
        }
        response = requests.get(url, params=params)
        data = response.json()["results"]
        results.append({
            "date": target_date.isoformat(),
            "sunset": data["sunset"],
            "moonrise": data["moonrise"],
            "moonset": data["moonset"],
            "moon_phase": data["moon_phase"],
            "moon_illumination": data["moon_illumination"]
        })

    return results


def average_night_cloud_cover(hourly_times, hourly_clouds, target_date):
    # "Night" = 10pm on target_date through 4am the next day
    night_values = []
    for time_str, cloud in zip(hourly_times, hourly_clouds):
        hour_date, hour_time = time_str.split("T")
        hour = int(hour_time.split(":")[0])

        if hour_date == target_date and hour >= 22:
            night_values.append(cloud)
        elif hour_date == (date.fromisoformat(target_date) + timedelta(days=1)).isoformat() and hour <= 4:
            night_values.append(cloud)

    if not night_values:
        return None
    return round(sum(night_values) / len(night_values), 1)


@app.get("/forecast")
def get_forecast(lat: float, lon: float):
    return fetch_cloud_forecast(lat, lon)


@app.get("/moon")
def get_moon(lat: float, lon: float):
    return fetch_moon_data(lat, lon)


@app.get("/best-nights")
def best_nights(lat: float, lon: float):
    cloud_data = fetch_cloud_forecast(lat, lon)
    moon_data = fetch_moon_data(lat, lon)

    hourly_times = cloud_data["hourly"]["time"]
    hourly_clouds = cloud_data["hourly"]["cloudcover"]

    results = []
    for night in moon_data:
        avg_cloud = average_night_cloud_cover(hourly_times, hourly_clouds, night["date"])
        if avg_cloud is None:
            continue

        # Weighted score: cloud cover matters more than moon illumination.
        # 70% weight on cloud, 30% weight on moon — lower score is better.
        score = (avg_cloud * 0.7) + (night["moon_illumination"] * 0.3)

        results.append({
            "date": night["date"],
            "avg_night_cloud_cover_percent": avg_cloud,
            "moon_illumination_percent": night["moon_illumination"],
            "moon_phase": night["moon_phase"],
            "score": round(score, 1)
        })

    results.sort(key=lambda x: x["score"])
    return results