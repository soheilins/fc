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

# ========== HARDCODED RECIPIENTS ==========
# Add as many Rubika user IDs as you want
RUBIKA_USER_IDS = [
    "b0JWE2R0cCz01c6f676803e07bf4e745",   # first user
    # Add more below, e.g.:
    # "another_user_id_here",
]

if not RUBIKA_USER_IDS:
    print("❌ No user IDs defined", flush=True)
    sys.exit(1)

# Coordinates for Sari, Iran
LAT = 36.5633
LON = 53.0601

# Rubika API endpoint for sending text messages
BASE_API = f"https://botapi.rubika.ir/v3/{RUBIKA_TOKEN}"
SEND_MESSAGE_URL = f"{BASE_API}/sendMessage"

# ------------------------------------------------------------

def fetch_forecast():
    """Fetch 10-day forecast from Open-Meteo (free, no API key)."""
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
        return resp.json()
    except Exception as e:
        print(f"❌ Forecast error: {e}", flush=True)
        return None

def weather_symbol(code):
    """Convert WMO weather code to a simple emoji + description."""
    if code == 0:
        return "☀️ Clear"
    elif code in (1, 2, 3):
        return "⛅ Partly cloudy"
    elif code in (45, 48):
        return "🌫️ Fog"
    elif code in (51, 53, 55):
        return "🌧️ Drizzle"
    elif code in (61, 63, 65):
        return "🌧️ Rain"
    elif code in (71, 73, 75):
        return "❄️ Snow"
    elif code in (80, 81, 82):
        return "🌧️ Showers"
    else:
        return "🌡️ Mixed"

def format_message(forecast):
    """Build a clean, readable forecast message."""
    if not forecast or "daily" not in forecast:
        return "⚠️ Could not retrieve weather data for Sari."

    daily = forecast["daily"]
    dates = daily["time"]
    max_t = daily["temperature_2m_max"]
    min_t = daily["temperature_2m_min"]
    rain = daily["precipitation_sum"]
    codes = daily["weathercode"]

    msg = f"📍 **10‑Day Forecast – Sari, Iran**\n"
    msg += f"🕒 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    msg += "─────────────────\n"

    for i in range(len(dates)):
        date = dates[i]
        t_min = min_t[i]
        t_max = max_t[i]
        prec = rain[i]
        symbol = weather_symbol(codes[i])

        msg += f"📅 {date}\n"
        msg += f"   🌡️ {t_min:.0f}° – {t_max:.0f}°C\n"
        msg += f"   💧 Rain: {prec:.1f} mm\n"
        msg += f"   {symbol}\n\n"

    msg += "─────────────────\n"
    msg += "🌐 Source: Open‑Meteo"
    return msg

def send_to_rubika(chat_id, text):
    """Send a text message to a single Rubika user."""
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        resp = requests.post(SEND_MESSAGE_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "OK":
                print(f"✅ Sent to {chat_id}", flush=True)
            else:
                print(f"⚠️ API error for {chat_id}: {data}", flush=True)
        else:
            print(f"❌ HTTP {resp.status_code} for {chat_id}", flush=True)
    except Exception as e:
        print(f"❌ Exception for {chat_id}: {e}", flush=True)

def main():
    print("🌤️ Weather bot started", flush=True)
    forecast = fetch_forecast()
    if forecast:
        message = format_message(forecast)
        for uid in RUBIKA_USER_IDS:
            send_to_rubika(uid, message)
    else:
        error_msg = "❌ Weather forecast unavailable right now."
        for uid in RUBIKA_USER_IDS:
            send_to_rubika(uid, error_msg)

if __name__ == "__main__":
    main()
