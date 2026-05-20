#!/usr/bin/env python3
import os
import sys
import requests
import time
from datetime import datetime
import jdatetime
from zoneinfo import ZoneInfo

# ========== CONFIGURATION ==========
RUBIKA_TOKEN = os.environ.get("RUBIKA_TOKEN", "")
if not RUBIKA_TOKEN:
    print("❌ RUBIKA_TOKEN missing", flush=True)
    sys.exit(1)

RUBIKA_USER_IDS = [
    "b0JWE2R0cCz01c6f676803e07bf4e745",
    "b0BZaDD0cCz0546b41e14d71ff9ccf0b",
]

LAT = 36.772269
LON = 53.123903
FORECAST_DAYS = 15
SHOW_DAYS = 7

BASE_API = f"https://botapi.rubika.ir/v3/{RUBIKA_TOKEN}"
SEND_MESSAGE_URL = f"{BASE_API}/sendMessage"

# ========== Helper functions ==========
def gregorian_to_jalali(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        jd = jdatetime.date.fromgregorian(year=dt.year, month=dt.month, day=dt.day)
        persian_digits = {'0':'۰','1':'۱','2':'۲','3':'۳','4':'۴','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹'}
        year_str = ''.join(persian_digits.get(ch, ch) for ch in str(jd.year))
        month_str = ''.join(persian_digits.get(ch, ch) for ch in str(jd.month).zfill(2))
        day_str = ''.join(persian_digits.get(ch, ch) for ch in str(jd.day).zfill(2))
        month_names = {
            1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر", 5: "مرداد", 6: "شهریور",
            7: "مهر", 8: "آبان", 9: "آذر", 10: "دی", 11: "بهمن", 12: "اسفند"
        }
        return f"{day_str} {month_names[jd.month]} {year_str}"
    except:
        return date_str

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

def to_persian_digits(s):
    persian_digits = {'0':'۰','1':'۱','2':'۲','3':'۳','4':'۴','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹'}
    return ''.join(persian_digits.get(ch, ch) for ch in s)

def fetch_forecast():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "daily": [
            "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "rain_sum", "snowfall_sum",
            "windspeed_10m_max", "weathercode",
            "sunrise", "sunset"
        ],
        "hourly": [
            "temperature_2m", "precipitation", "precipitation_probability"
            # windspeed_10m removed as requested
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

def build_hourly_table(hourly_data, day_index, dates):
    """
    Build a formatted hourly table with columns:
    ساعت | دما | بارش | احتمال بارش
    """
    target_date = dates[day_index]
    times = hourly_data.get("time", [])
    start_idx = None
    end_idx = None
    for i, t in enumerate(times):
        if t.startswith(target_date):
            if start_idx is None:
                start_idx = i
            end_idx = i
    if start_idx is None:
        return "⚠️ داده ساعتی در دسترس نیست"

    temp = hourly_data.get("temperature_2m", [])
    precip = hourly_data.get("precipitation", [])
    precip_prob = hourly_data.get("precipitation_probability", [])

    # Prepare lines
    lines = []
    # Column headers (with fixed widths for alignment)
    header = f"{'ساعت':<6} {'دما':<4} {'بارش':<6} {'احتمال بارش':<10}"
    lines.append("🔽 پیش‌بینی ساعتی")
    lines.append(header)
    lines.append("-" * 30)
    for i in range(start_idx, min(end_idx + 1, start_idx + 24)):
        hour_str = times[i].split("T")[1][:5]  # HH:MM
        t = safe_float(temp[i] if i < len(temp) else None)
        p = safe_float(precip[i] if i < len(precip) else None)
        pp = safe_float(precip_prob[i] if i < len(precip_prob) else None)
        # Format each row
        line = f"{hour_str:<6} {t:>3.0f}°   {p:>4.1f}   {pp:>5.0f}%"
        lines.append(line)
    return "\n".join(lines)

def build_daily_summary(day_data, date_str, sunrise, sunset, idx):
    jdate = gregorian_to_jalali(date_str)
    t_min = safe_float(day_data["min_t"])
    t_max = safe_float(day_data["max_t"])
    p = safe_float(day_data["precip"])
    r = safe_float(day_data["rain"])
    s = safe_float(day_data["snow"])
    w = safe_float(day_data["wind"])
    desc = day_data["desc"]

    lines = [f"📅 {jdate}"]
    lines.append(f"🌡️ {t_min:.0f}~{t_max:.0f}°C")
    if p > 0:
        precip_line = f"💧 بارش: {p:.1f}mm"
        if r > 0:
            precip_line += f" (باران {r:.1f})"
        if s > 0:
            precip_line += f" برف {s:.1f}cm"
        lines.append(precip_line)
    if w > 0:
        lines.append(f"🌬️ باد: {w:.0f}km/h")
    lines.append(f"☁️ {desc}")
    if idx < len(sunrise) and sunrise[idx] and idx < len(sunset) and sunset[idx]:
        sr = sunrise[idx].split("T")[1][:5] if "T" in sunrise[idx] else sunrise[idx]
        ss = sunset[idx].split("T")[1][:5] if "T" in sunset[idx] else sunset[idx]
        lines.append(f"🌅 {sr}  🌇 {ss}")
    return "\n".join(lines)

def get_update_header():
    tehran_tz = ZoneInfo("Asia/Tehran")
    now_tehran = datetime.now(tehran_tz)
    update_str = now_tehran.strftime("%Y-%m-%d %H:%M:%S")
    update_str_fa = to_persian_digits(update_str)
    return f"پیش‌بینی {SHOW_DAYS} روزه هوای سوته\nبروزرسانی: {update_str_fa}\n{'='*40}"

def split_forecast_messages(forecast):
    if not forecast or "daily" not in forecast:
        return ["⚠️ اطلاعات آب و هوا در دسترس نیست."]

    daily = forecast["daily"]
    hourly = forecast.get("hourly", {})
    dates = daily.get("time", [])
    if not dates:
        return ["⚠️ داده‌ای یافت نشد."]

    dates = dates[:SHOW_DAYS]
    max_t = daily.get("temperature_2m_max", [])[:SHOW_DAYS]
    min_t = daily.get("temperature_2m_min", [])[:SHOW_DAYS]
    precip = daily.get("precipitation_sum", [])[:SHOW_DAYS]
    rain = daily.get("rain_sum", [])[:SHOW_DAYS]
    snow = daily.get("snowfall_sum", [])[:SHOW_DAYS]
    wind = daily.get("windspeed_10m_max", [])[:SHOW_DAYS]
    codes = daily.get("weathercode", [])[:SHOW_DAYS]
    sunrise = daily.get("sunrise", [])[:SHOW_DAYS]
    sunset = daily.get("sunset", [])[:SHOW_DAYS]

    header = get_update_header()
    messages = []

    # Summary message for all SHOW_DAYS
    summary_lines = [header, "\n📋 خلاصه روزانه:"]
    for i in range(SHOW_DAYS):
        day_data = {
            "min_t": min_t[i] if i < len(min_t) else 0,
            "max_t": max_t[i] if i < len(max_t) else 0,
            "precip": precip[i] if i < len(precip) else 0,
            "rain": rain[i] if i < len(rain) else 0,
            "snow": snow[i] if i < len(snow) else 0,
            "wind": wind[i] if i < len(wind) else 0,
            "desc": weather_desc_persian(int(safe_float(codes[i] if i < len(codes) else 0)))
        }
        daily_text = build_daily_summary(day_data, dates[i], sunrise, sunset, i)
        summary_lines.append(daily_text)
        summary_lines.append("")
    messages.append("\n".join(summary_lines).strip())

    # Separate hourly message for each day (only if hourly data exists)
    if hourly:
        for i in range(SHOW_DAYS):
            jdate = gregorian_to_jalali(dates[i])
            hourly_title = f"{header}\n\n📅 {jdate} – داده ساعتی"
            hourly_table = build_hourly_table(hourly, i, dates)
            msg = f"{hourly_title}\n\n{hourly_table}"
            messages.append(msg.strip())
    else:
        # If no hourly data, send a single error instead of 7 messages
        messages.append("⚠️ داده ساعتی در پاسخ API وجود ندارد.")

    return messages

def send_rubika_message(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(SEND_MESSAGE_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "OK":
                print(f"✅ Sent to {chat_id} (length: {len(text)} chars)", flush=True)
            else:
                print(f"❌ Rubika error: {data}", flush=True)
        else:
            print(f"❌ HTTP error {resp.status_code}", flush=True)
    except Exception as e:
        print(f"❌ Exception: {e}", flush=True)

def main():
    print(f"🌤️ Weather bot - Hourly without wind, with column headers", flush=True)
    start_time = time.time()
    max_runtime = 5.9 * 3600
    interval = 600

    iteration = 0
    while time.time() - start_time < max_runtime:
        iteration += 1
        print(f"\n🔄 Iteration {iteration} at {datetime.now().strftime('%H:%M:%S')}", flush=True)

        forecast = fetch_forecast()
        if forecast:
            messages = split_forecast_messages(forecast)
            for uid in RUBIKA_USER_IDS:
                for msg in messages:
                    send_rubika_message(uid, msg)
                    time.sleep(0.5)
        else:
            error_msg = "⚠️ پیش‌بینی در دسترس نیست"
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
