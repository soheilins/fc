#!/usr/bin/env python3
import os
import sys
import requests
from datetime import datetime

# ========== CONFIGURATION ==========
RUBIKA_TOKEN = os.environ.get("RUBIKA_TOKEN", "")

if not RUBIKA_TOKEN:
    print("❌ RUBIKA_TOKEN environment variable not set", flush=True)
    sys.exit(1)

# ========== MULTIPLE RECIPIENTS (OPTION 2: HARDCODED) ==========
RUBIKA_USER_IDS = [
    "b0JWE2R0bQW0eae5690fa217ebebf122",   # your Rubika user ID
    # Add more user IDs below, one per line, comma after each except last
    # "another_user_id_here",
    # "third_user_id_here",
]

if not RUBIKA_USER_IDS:
    print("❌ No Rubika user IDs defined in the script", flush=True)
    sys.exit(1)

# Coordinates for Sari, Iran
LAT = 36.5633
LON = 53.0601

# Rubika API endpoints
BASE_API = f"https://botapi.rubika.ir/v3/{RUBIKA_TOKEN}"
SEND_MESSAGE_URL = f"{BASE_API}/sendMessage"

def fetch_10day_forecast():
    """Fetch 10‑day weather forecast from Open‑Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "weathercode"
        ],
        "timezone": "Asia/Tehran",
        "forecast_days": 10
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data
    except Exception as e:
        print(f"❌ Failed to fetch forecast: {e}", flush=True)
        return None

def format_forecast_message(forecast_data):
    """Convert Open‑Meteo JSON into a nice Persian/English text."""
    if not forecast_data or "daily" not in forecast_data:
        return "⚠️ Could not retrieve weather data."

    daily = forecast_data["daily"]
    dates = daily["time"]
    max_temps = daily["temperature_2m_max"]
    min_temps = daily["temperature_2m_min"]
    precip = daily["precipitation_sum"]
    weather_codes = daily["weathercode"]

    # Simple weather code description (WMO standard)
    def weather_desc(code):
        if code == 0:
            return "☀️ Clear sky"
        elif code in [1, 2, 3]:
            return "⛅ Partly cloudy"
        elif code in [45, 48]:
            return "🌫️ Fog"
        elif code in [51, 53, 55]:
            return "🌧️ Light drizzle"
        elif code in [61, 63, 65]:
            return "🌧️ Rain"
        elif code in [71, 73, 75]:
            return "❄️ Snow"
        elif code in [80, 81, 82]:
            return "🌧️ Rain showers"
        else:
            return "🌡️ Varied"

    message = f"📍 **10‑Day Weather Forecast for Sari, Iran**\n"
    message += f"🕒 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += "─" * 30 + "\n"

    for i in range(len(dates)):
        date = dates[i]
        max_t = max_temps[i]
        min_t = min_temps[i]
        rain = precip[i]
        wcode = weather_codes[i]
        desc = weather_desc(wcode)

        message += f"📅 {date}\n"
        message += f"   🌡️ {min_t:.0f}°C – {max_t:.0f}°C\n"
        message += f"   💧 Rain: {rain:.1f} mm\n"
        message += f"   {desc}\n\n"

    message += "─" * 30 + "\n"
    message += "🌐 Source: Open‑Meteo (free weather API)"
    return message

def send_rubika_message(chat_id, text):
    """Send a text message via Rubika bot to a single user."""
    payload = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(SEND_MESSAGE_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"✅ Forecast sent to user {chat_id}", flush=True)
        else:
            print(f"⚠️ Failed to send to {chat_id}: {resp.status_code} - {resp.text}", flush=True)
    except Exception as e:
        print(f"❌ Exception sending to {chat_id}: {e}", flush=True)

def main():
    print("🌤️ Starting weather bot for Sari...", flush=True)
    forecast = fetch_10day_forecast()
    if forecast:
        msg = format_forecast_message(forecast)
        # Send to every user in the hardcoded list
        for user_id in RUBIKA_USER_IDS:
            send_rubika_message(user_id, msg)
    else:
        error_msg = "❌ Weather forecast unavailable at the moment."
        for user_id in RUBIKA_USER_IDS:
            send_rubika_message(user_id, error_msg)

if __name__ == "__main__":
    main()
