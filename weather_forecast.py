#!/usr/bin/env python3
import os
import sys
import requests
import time
from datetime import datetime
import arabic_reshaper
from bidi.algorithm import get_display

# ========== CONFIGURATION ==========
RUBIKA_TOKEN = os.environ.get("RUBIKA_TOKEN", "")
if not RUBIKA_TOKEN:
    print("❌ RUBIKA_TOKEN missing", flush=True)
    sys.exit(1)

# Your Rubika user ID
RUBIKA_USER_IDS = [
    "b0JWE2R0cCz01c6f676803e07bf4e745",
]

# Sari, Iran coordinates
LAT = 36.5633
LON = 53.0601
FORECAST_DAYS = 16

BASE_API = f"https://botapi.rubika.ir/v3/{RUBIKA_TOKEN}"
SEND_MESSAGE_URL = f"{BASE_API}/sendMessage"

# ========== Persian helpers ==========
def persian(text):
    if not text:
        return text
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

MONTHS_PERSIAN = {
    1: "ژانویه", 2: "فوریه", 3: "مارس", 4: "آوریل", 5: "مه", 6: "ژوئن",
    7: "ژوئیه", 8: "اوت", 9: "سپتامبر", 10: "اکتبر", 11: "نوامبر", 12: "دسامبر"
}

def format_persian_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        persian_digits = {'0':'۰','1':'۱','2':'۲','3':'۳','4':'۴','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹'}
        day_p = ''.join(persian_digits.get(ch, ch) for ch in str(dt.day))
        year_p = ''.join(persian_digits.get(ch, ch) for ch in str(dt.year))
        month_name = MONTHS_PERSIAN.get(dt.month, "")
        return f"{day_p} {month_name} {year_p}"
    except:
        return date_str

def weather_desc_persian(code):
    code_map = {
        0: "صاف ☀️", 1: "کمی ابر ⛅", 2: "نیمه ابری ☁️", 3: "ابری 🌥️",
        45: "مه آلود 🌫️", 48: "مه یخ‌زده 🌫️",
        51: "بارون خفیف 🌧️", 53: "بارون متوسط 🌧️", 55: "بارون شدید 🌧️",
        61: "باران خفیف 🌦️", 63: "باران متوسط 🌧️", 65: "باران شدید 🌧️",
        71: "برف خفیف ❄️", 73: "برف متوسط ❄️", 75: "برف شدید ❄️",
        80: "رگبار خفیف 🌦️", 81: "رگبار متوسط 🌦️", 82: "رگبار شدید ⛈️",
        95: "طوفان رعد و برق ⛈️", 96: "طوفان با تگرگ ⛈️", 99: "طوفان شدید با تگرگ ⛈️"
    }
    return code_map.get(code, "متغیر 🌡️")

def fetch_forecast():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "daily": [
            "temperature_2m_max", "temperature_2m_min",
            "apparent_temperature_max", "apparent_temperature_min",
            "precipitation_sum", "rain_sum", "snowfall_sum",
            "windspeed_10m_max", "uv_index_max", "weathercode",
            "sunrise", "sunset"
        ],
        "timezone": "Asia/Tehran",
        "forecast_days": FORECAST_DAYS
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"❌ Forecast error: {e}", flush=True)
        return None

def format_persian_message(forecast):
    if not forecast or "daily" not in forecast:
        return "⚠️ اطلاعات آب و هوا در دسترس نیست."

    daily = forecast["daily"]
    dates = daily["time"]
    max_t = daily["temperature_2m_max"]
    min_t = daily["temperature_2m_min"]
    feels_max = daily.get("apparent_temperature_max", [None]*len(dates))
    feels_min = daily.get("apparent_temperature_min", [None]*len(dates))
    precip = daily["precipitation_sum"]
    rain = daily.get("rain_sum", [0]*len(dates))
    snow = daily.get("snowfall_sum", [0]*len(dates))
    wind = daily.get("windspeed_10m_max", [0]*len(dates))
    uv = daily.get("uv_index_max", [0]*len(dates))
    codes = daily.get("weathercode", [0]*len(dates))
    sunrise = daily.get("sunrise", [""]*len(dates))
    sunset = daily.get("sunset", [""]*len(dates))

    msg = persian(f"📌 **پیش‌بینی {len(dates)} روزه هوای ساری**\n")
    msg += persian(f"🕒 بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    msg += "─" * 30 + "\n"

    for i in range(len(dates)):
        date_persian = format_persian_date(dates[i])
        msg += persian(f"📅 {date_persian}\n")
        msg += persian(f"   🌡️ {min_t[i]:.0f}–{max_t[i]:.0f}°C\n")
        if feels_max[i] is not None:
            msg += persian(f"   🤔 احساس: {feels_min[i]:.0f}–{feels_max[i]:.0f}°C\n")
        msg += persian(f"   🌧️ بارش: {precip[i]:.1f} mm")
        if rain[i] > 0:
            msg += persian(f" (باران {rain[i]:.1f} mm)")
        if snow[i] > 0:
            msg += persian(f" ❄️ برف {snow[i]:.1f} cm")
        msg += "\n"
        if wind[i] > 0:
            msg += persian(f"   💨 باد: تا {wind[i]:.0f} km/h\n")
        if uv[i] > 0:
            msg += persian(f"   ☀️ UV: {uv[i]:.1f}\n")
        msg += persian(f"   {weather_desc_persian(codes[i])}\n")
        if sunrise[i] and sunset[i]:
            sr = sunrise[i].split("T")[1][:5] if "T" in sunrise[i] else sunrise[i]
            ss = sunset[i].split("T")[1][:5] if "T" in sunset[i] else sunset[i]
            msg += persian(f"   🌅 طلوع {sr}  |  غروب {ss}\n")
        msg += "\n"

    msg += "─" * 30 + "\n"
    msg += persian("🌐 داده‌ها: Open‑Meteo")
    return msg

def send_rubika_message(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(SEND_MESSAGE_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"✅ Sent to {chat_id}", flush=True)
        else:
            print(f"⚠️ Failed to {chat_id}: {resp.text[:100]}", flush=True)
    except Exception as e:
        print(f"❌ Exception to {chat_id}: {e}", flush=True)

def main():
    print("🌤️ Weather bot started (16 days, 6h run, hourly send)", flush=True)
    start_time = time.time()
    max_runtime = 5.9 * 3600   # 5.9 hours
    interval = 3600            # 1 hour

    iteration = 0
    while time.time() - start_time < max_runtime:
        iteration += 1
        print(f"\n🔄 Iteration {iteration} at {datetime.now().strftime('%H:%M:%S')}", flush=True)

        forecast = fetch_forecast()
        if forecast:
            message = format_persian_message(forecast)
            for uid in RUBIKA_USER_IDS:
                send_rubika_message(uid, message)
        else:
            error_msg = persian("⚠️ پیش‌بینی در دسترس نیست – بعداً تلاش کنید.")
            for uid in RUBIKA_USER_IDS:
                send_rubika_message(uid, error_msg)

        elapsed = time.time() - start_time
        if elapsed + interval > max_runtime:
            print("⏰ Runtime limit reached, exiting.", flush=True)
            break
        print(f"⏳ Sleeping {interval} seconds...", flush=True)
        time.sleep(interval)

    print("🏁 6‑hour run completed.", flush=True)

if __name__ == "__main__":
    main()
