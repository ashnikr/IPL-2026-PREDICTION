"""
Weather Data Collector.

Fetches weather data for IPL match venues using WeatherAPI.
"""

import json
from datetime import datetime, date
from pathlib import Path

import requests
import pandas as pd

from utils.logger import logger
from config.settings import settings


class WeatherCollector:
    """Collect weather data for IPL venues."""

    WEATHERAPI_URL = "https://api.weatherapi.com/v1"

    # City coordinates for IPL venues
    VENUE_COORDINATES = {
        "Mumbai": {"lat": 19.0760, "lon": 72.8777},
        "Chennai": {"lat": 13.0827, "lon": 80.2707},
        "Bengaluru": {"lat": 12.9716, "lon": 77.5946},
        "Kolkata": {"lat": 22.5726, "lon": 88.3639},
        "Delhi": {"lat": 28.6139, "lon": 77.2090},
        "Hyderabad": {"lat": 17.3850, "lon": 78.4867},
        "Jaipur": {"lat": 26.9124, "lon": 75.7873},
        "Mohali": {"lat": 30.7046, "lon": 76.7179},
        "Ahmedabad": {"lat": 23.0225, "lon": 72.5714},
        "Lucknow": {"lat": 26.8467, "lon": 80.9462},
        "Dharamsala": {"lat": 32.2190, "lon": 76.3234},
        "Visakhapatnam": {"lat": 17.6868, "lon": 83.2185},
        "Guwahati": {"lat": 26.1445, "lon": 91.7362},
        "Pune": {"lat": 18.5204, "lon": 73.8567},
        "Raipur": {"lat": 21.2514, "lon": 81.6296},
        "Mullanpur": {"lat": 30.8500, "lon": 76.5800},
    }

    # Default weather for when API is unavailable
    DEFAULT_WEATHER = {
        "Mumbai": {"temperature": 32, "humidity": 75, "wind_speed": 15, "dew_probability": 0.7, "rain_probability": 0.2},
        "Chennai": {"temperature": 34, "humidity": 70, "wind_speed": 12, "dew_probability": 0.6, "rain_probability": 0.15},
        "Bengaluru": {"temperature": 28, "humidity": 55, "wind_speed": 10, "dew_probability": 0.4, "rain_probability": 0.25},
        "Kolkata": {"temperature": 33, "humidity": 80, "wind_speed": 14, "dew_probability": 0.8, "rain_probability": 0.3},
        "Delhi": {"temperature": 35, "humidity": 45, "wind_speed": 18, "dew_probability": 0.5, "rain_probability": 0.1},
        "Hyderabad": {"temperature": 35, "humidity": 50, "wind_speed": 16, "dew_probability": 0.5, "rain_probability": 0.15},
        "Jaipur": {"temperature": 36, "humidity": 35, "wind_speed": 20, "dew_probability": 0.3, "rain_probability": 0.05},
        "Mohali": {"temperature": 33, "humidity": 50, "wind_speed": 15, "dew_probability": 0.5, "rain_probability": 0.1},
        "Ahmedabad": {"temperature": 36, "humidity": 40, "wind_speed": 18, "dew_probability": 0.4, "rain_probability": 0.05},
        "Lucknow": {"temperature": 34, "humidity": 50, "wind_speed": 14, "dew_probability": 0.5, "rain_probability": 0.1},
        "Dharamsala": {"temperature": 22, "humidity": 55, "wind_speed": 12, "dew_probability": 0.3, "rain_probability": 0.2},
        "Guwahati": {"temperature": 28, "humidity": 75, "wind_speed": 10, "dew_probability": 0.6, "rain_probability": 0.35},
        "Raipur": {"temperature": 35, "humidity": 40, "wind_speed": 14, "dew_probability": 0.4, "rain_probability": 0.1},
        "Mullanpur": {"temperature": 32, "humidity": 48, "wind_speed": 16, "dew_probability": 0.45, "rain_probability": 0.1},
    }

    def __init__(self):
        self.api_key = settings.weather_api_key
        self.cache_dir = settings.cache_dir / "weather"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_weather(self, city: str, match_date: str = None) -> dict:
        """Get weather data for a city."""
        # Check cache first
        cache_key = f"{city}_{match_date or 'current'}"
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

        # Try API if key available
        if self.api_key:
            weather = self._fetch_from_api(city, match_date)
            if weather:
                cache_file.write_text(json.dumps(weather))
                return weather

        # Return defaults
        city_key = self._normalize_city(city)
        default = self.DEFAULT_WEATHER.get(city_key, {
            "temperature": 32, "humidity": 60, "wind_speed": 15,
            "dew_probability": 0.5, "rain_probability": 0.15,
        })
        default["city"] = city
        default["source"] = "default"
        return default

    def _fetch_from_api(self, city: str, match_date: str = None) -> dict | None:
        """Fetch weather from WeatherAPI."""
        try:
            if match_date:
                endpoint = f"{self.WEATHERAPI_URL}/forecast.json"
                params = {"key": self.api_key, "q": city, "dt": match_date, "aqi": "no"}
            else:
                endpoint = f"{self.WEATHERAPI_URL}/current.json"
                params = {"key": self.api_key, "q": city, "aqi": "no"}

            resp = requests.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if match_date and "forecast" in data:
                day = data["forecast"]["forecastday"][0]["day"]
                return {
                    "city": city,
                    "date": match_date,
                    "temperature": day.get("avgtemp_c"),
                    "humidity": day.get("avghumidity"),
                    "wind_speed": day.get("maxwind_kph"),
                    "rain_probability": day.get("daily_chance_of_rain", 0) / 100,
                    "dew_probability": self._estimate_dew(day.get("avghumidity", 50), day.get("avgtemp_c", 30)),
                    "condition": day.get("condition", {}).get("text"),
                    "source": "weatherapi",
                }
            elif "current" in data:
                current = data["current"]
                return {
                    "city": city,
                    "temperature": current.get("temp_c"),
                    "humidity": current.get("humidity"),
                    "wind_speed": current.get("wind_kph"),
                    "rain_probability": 0.3 if "rain" in current.get("condition", {}).get("text", "").lower() else 0.05,
                    "dew_probability": self._estimate_dew(current.get("humidity", 50), current.get("temp_c", 30)),
                    "condition": current.get("condition", {}).get("text"),
                    "source": "weatherapi",
                }
        except Exception as e:
            logger.warning(f"WeatherAPI failed for {city}: {e}")

        return None

    def _estimate_dew(self, humidity: float, temperature: float) -> float:
        """Estimate dew probability based on humidity and temperature."""
        # Evening matches (most IPL games) have higher dew probability
        if humidity > 70 and temperature > 25:
            return min(0.95, humidity / 100 * 1.1)
        elif humidity > 50:
            return humidity / 100 * 0.8
        return humidity / 100 * 0.5

    def _normalize_city(self, city: str) -> str:
        """Normalize city name for lookup."""
        city_map = {
            "bangalore": "Bengaluru",
            "bengaluru": "Bengaluru",
            "new delhi": "Delhi",
            "navi mumbai": "Mumbai",
            "chandigarh": "Mohali",
            "new chandigarh": "Mullanpur",
            "raipur": "Raipur",
            "guwahati": "Guwahati",
            "dharamshala": "Dharamsala",
        }
        return city_map.get(city.lower(), city.title())

    def get_weather_for_venues(self, venues: list[dict]) -> pd.DataFrame:
        """Get weather for multiple venues."""
        weather_data = []
        for venue in venues:
            city = venue.get("city", "")
            match_date = venue.get("date")
            weather = self.get_weather(city, match_date)
            weather["venue"] = venue.get("venue", "")
            weather_data.append(weather)

        return pd.DataFrame(weather_data)

    def get_match_weather_impact(self, city: str, match_date: str = None) -> dict:
        """Calculate weather impact scores for a match."""
        weather = self.get_weather(city, match_date)

        # Calculate impact scores
        dew_factor = weather.get("dew_probability", 0.5)
        temp = weather.get("temperature", 30)
        humidity = weather.get("humidity", 60)
        wind = weather.get("wind_speed", 15)

        # Batting-friendly conditions: high temp, low humidity, no dew
        batting_advantage = (
            (temp - 20) / 20 * 0.3
            + (1 - humidity / 100) * 0.3
            + (1 - dew_factor) * 0.2
            + wind / 40 * 0.2  # Wind helps boundaries
        )

        # Chasing advantage increases with dew
        chase_advantage = dew_factor * 0.6 + (humidity / 100) * 0.2 + 0.2

        return {
            **weather,
            "batting_advantage": round(min(1, max(0, batting_advantage)), 3),
            "chase_advantage": round(min(1, max(0, chase_advantage)), 3),
            "rain_risk": weather.get("rain_probability", 0.1),
        }
