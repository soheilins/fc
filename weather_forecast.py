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

RUBIKA_USER_IDS = [
    "b0JWE2R0cCz01c6f676803e07bf4e745",
]

LAT = 36.5633
LON = 53.0601
FORECAST_DAYS = 16

BASE_API = f"https://botapi.rubika.ir/v3/{RUBIKA_TOKEN}"
SEND_MESSAGE_URL = f"{BASE_API}/sendMessage"

# ========== Persian formatting ==========
def to_persian_digits(num):
    """Convert Latin digits to Persian digits."""
    persian_digits = {'0':'۰','1':'۱','2':'۲','3':'۳','4':'۴','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹','.':'.', '-':'-'}
    if isinstance(num, float):
        num_str = f"{num:.1f}" if num != int(num) else f"{int(num)}"
    else:
        num_str = str(num)
    return ''.join(persian_digits.get(ch, ch) for ch in num_str)

def persian_rtl(text):
    """Reshape, apply bidi, and force RTL."""
    if not text:
        return text
    try:
        # First reshape Arabic letters
        reshaped = arabic_reshaper.reshape(text)
        # Then apply bidi algorithm to get visual order
        bidi_text = get_display(reshaped)
        # Add Right-to-Left Embedding and Right-to-Left Mark
        return "\u202B" + bidi_text + "\u200F"
    except:
        return text

MONTHS_PERSIAN = {
    1: "ژانویه", 2: "فوریه", 3: "مارس", 4: "آوریل", 5: "مه", 6: "ژوئن",
    7: "ژوئیه", 8: "اوت", 9: "سپتامبر", 10: "اکتبر", 11: "نوامبر", 12: "دسامبر"
}

def format_persian_date(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day = to_persian_digits(dt.day)
    year = to_persian_digits(dt.year)
    month_name = MONTHS_PERSIAN.get(dt.month, "")
    return f"{day} {month_name} {year}"

def weather_desc_persian(code):
    if code is None:
        return "متغیر"
    code_map = {
        0: "صاف", 1: "کمی ابر", 2: "نیمه ابری", 3: "ابری",
        45: "مه آلود", 48: "مه یخ‌زده",
        51: "بارون خفیف", 53: "بارون متوسط", 55: "بارون شدید",
        61: "باران خفیف", 63: "باران متوسط", 65: "باران شدید",
        71: "برف خفیف", 73: "برف متوسط", 75: "برف شدید",
        80: "رگبار خفیف", 81: "رگبار متوسط", 82: "رگبار شدید",
        95: "طوفان رعد و برق", 96: "طوفان با تگرگ", 99: "طوفان شدید با تگرگ"
    }
    return code_map.get(code, "متغیر")

def safe_float(val, default=0):
    try:
        if val is None:
            return default
        return float(val)
    except:
        return default

def safe_int(val, default=0):
    try:
        if val is None:
            return default
        return int(val)
    except:
        return default

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

def format_persian_forecast(forecast):
    if not forecast or "daily" not in forecast:
        return persian_rtl("اطلاعات آب و هوا در دسترس نیست")

    daily = forecast["daily"]
    dates = daily.get("time", [])
    if not dates:
        return persian_rtl("داده‌ای یافت نشد")

    max_t = daily.get("temperature_2m_max", [])
    min_t = daily.get("temperature_2m_min", [])
    feels_max = daily.get("apparent_temperature_max", [])
    feels_min = daily.get("apparent_temperature_min", [])
    precip = daily.get("precipitation_sum", [])
    rain = daily.get("rain_sum", [])
    snow = daily.get("snowfall_sum", [])
    wind = daily.get("windspeed_10m_max", [])
    uv = daily.get("uv_index_max", [])
    codes = daily.get("weathercode", [])
    sunrise = daily.get("sunrise", [])
    sunset = daily.get("sunset", [])

    lines = []
    # Header
    lines.append("پیش‌بینی ۱۶ روزه هوای ساری")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Convert datetime digits to Persian
    now_persian = ''.join([to_persian_digits(ch) if ch.isdigit() else ch for ch in now_str])
    lines.append(f"بروزرسانی: {now_persian}")
    lines.append("──────────────────────────────")

    for i in range(len(dates)):
        date_persian = format_persian_date(dates[i])
        t_min = safe_float(min_t[i] if i < len(min_t) else None)
        t_max = safe_float(max_t[i] if i < len(max_t) else None)
        f_min = safe_float(feels_min[i] if i < len(feels_min) else None)
        f_max = safe_float(feels_max[i] if i < len(feels_max) else None)
        p = safe_float(precip[i] if i < len(precip) else None)
        r = safe_float(rain[i] if i < len(rain) else None)
        s = safe_float(snow[i] if i < len(snow) else None)
        w = safe_float(wind[i] if i < len(wind) else None)
        u = safe_float(uv[i] if i < len(uv) else None)
        code = safe_int(codes[i] if i < len(codes) else None)

        # Line with date and temperatures
        temp_line = f"📅 {date_persian}  |  🌡️ {to_persian_digits(t_min)}–{to_persian_digits(t_max)} درجه"
        if f_max > 0 or f_min > 0:
            temp_line += f"  (احساس {to_persian_digits(f_min)}–{to_persian_digits(f_max)} درجه)"
        lines.append(temp_line)

        # Details line
        details = []
        if p > 0:
            det = f"🌧️ {to_persian_digits(p)} میلی‌متر"
            if r > 0:
                det += f" (باران {to_persian_digits(r)})"
            if s > 0:
                det += f" ❄️ برف {to_persian_digits(s)} سانتی‌متر"
            details.append(det)
        if w > 0:
            details.append(f"💨 باد {to_persian_digits(w)} کیلومتر بر ساعت")
        if u > 0:
            details.append(f"☀️ UV {to_persian_digits(u)}")
        desc = weather_desc_persian(code)
        detail_line = f"   {desc}"
        if details:
            detail_line += "  |  " + "  |  ".join(details)
        lines.append(detail_line)

        # Sunrise/sunset
        if i < len(sunrise) and sunrise[i] and i < len(sunset) and sunset[i]:
            sr = sunrise[i].split("T")[1][:5] if "T" in sunrise[i] else sunrise[i]
            ss = sunset[i].split("T")[1][:5] if "T" in sunset[i] else sunset[i]
            # Convert time digits
            sr_persian = ''.join([to_persian_digits(ch) if ch.isdigit() else ch for ch in sr])
            ss_persian = ''.join([to_persian_digits(ch) if ch.isdigit() else ch for ch in ss])
            lines.append(f"   🌅 طلوع {sr_persian}  |  غروب {ss_persian}")

        lines.append("")  # blank line

    lines.append("──────────────────────────────")
    lines.append("🌐 داده‌ها: Open‑Meteo")

    raw_text = "\n".join(lines)
    # Apply reshaping and bidi to the whole text
    return persian_rtl(raw_text)

def send_rubika_message(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(SEND_MESSAGE_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "OK":
                print(f"✅ Sent to {chat_id}", flush=True)
            else:
                print(f"❌ Rubika error: {data}", flush=True)
        else:
            print(f"❌ HTTP error {resp.status_code}: {resp.text[:200]}", flush=True)
    except Exception as e:
        print(f"❌ Exception: {e}", flush=True)

def main():
    print("🌤️ Weather bot (Persian digits & RTL fix)", flush=True)
    start_time = time.time()
    max_runtime = 5.9 * 3600
    interval = 3600

    iteration = 0
    while time.time() - start_time < max_runtime:
        iteration += 1
        print(f"\n🔄 Iteration {iteration} at {datetime.now().strftime('%H:%M:%S')}", flush=True)

        forecast = fetch_forecast()
        if forecast:
            message = format_persian_forecast(forecast)
            print(f"Message length: {len(message)} chars, lines: {message.count(chr(10))}", flush=True)
            for uid in RUBIKA_USER_IDS:
                send_rubika_message(uid, message)
        else:
            error_msg = persian_rtl("⚠️ پیش‌بینی در دسترس نیست")
            for uid in RUBIKA_USER_IDS:
                send_rubika_message(uid, error_msg)

        elapsed = time.time() - start_time
        if elapsed + interval > max_runtime:
            break
        print(f"⏳ Sleeping {interval} seconds...", flush=True)
        time.sleep(interval)

    print("🏁 Run completed.", flush=True)

if __name__ == "__main__":
    main()
