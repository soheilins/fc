#!/usr/bin/env python3
import os
import sys
import requests
import time
from datetime import datetime
import jdatetime
from zoneinfo import ZoneInfo   # برای زمان ایران

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
FORECAST_DAYS = 15          # تعداد روزهای پیش‌بینی (خلاصه روزانه)
HOURLY_DAYS = 3              # فقط برای ۳ روز اول جدول ساعتی نمایش داده شود

BASE_API = f"https://botapi.rubika.ir/v3/{RUBIKA_TOKEN}"
SEND_MESSAGE_URL = f"{BASE_API}/sendMessage"

# ========== توابع کمکی ==========
def gregorian_to_jalali(date_str):
    """تبدیل تاریخ میلادی به شمسی با اعداد فارسی و نام ماه"""
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
    """ترجمه کد وضعیت هوا به فارسی"""
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
    """تبدیل ارقام انگلیسی به فارسی"""
    persian_digits = {'0':'۰','1':'۱','2':'۲','3':'۳','4':'۴','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹'}
    return ''.join(persian_digits.get(ch, ch) for ch in s)

def fetch_forecast():
    """دریافت پیش‌بینی روزانه و ساعتی از Open‑Meteo"""
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
            "temperature_2m", "precipitation", "precipitation_probability",
            "windspeed_10m", "windgusts_10m", "relative_humidity_2m",
            "pressure_msl", "cloud_cover", "visibility"
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
    ساخت جدول ساعتی برای یک روز مشخص
    hourly_data: دیکشنری داده‌های ساعتی از API
    day_index: ایندکس روز (0 برای اولین روز)
    dates: لیست تاریخ‌های روزانه
    """
    # پیدا کردن بازه ساعات مربوط به این روز
    target_date = dates[day_index]
    # زمان‌ها در Open‑Meteo به صورت "2026-05-20T00:00" هستند
    times = hourly_data.get("time", [])
    start_idx = None
    end_idx = None
    for i, t in enumerate(times):
        if t.startswith(target_date):
            if start_idx is None:
                start_idx = i
            end_idx = i
    if start_idx is None:
        return "⚠️ داده ساعتی برای این روز در دسترس نیست"

    # استخراج داده‌های ۲۴ ساعت
    temp = hourly_data.get("temperature_2m", [])
    precip = hourly_data.get("precipitation", [])
    precip_prob = hourly_data.get("precipitation_probability", [])
    wind = hourly_data.get("windspeed_10m", [])
    windgust = hourly_data.get("windgusts_10m", [])
    humidity = hourly_data.get("relative_humidity_2m", [])
    pressure = hourly_data.get("pressure_msl", [])
    cloud = hourly_data.get("cloud_cover", [])
    visibility = hourly_data.get("visibility", [])

    lines = []
    lines.append("🔽 **پیش‌بینی ساعتی**")
    lines.append("ساعت - دما - بارش(mm) - احتمال بارش% - باد(km/h) - تندباد - رطوبت% - فشار(hPa) - ابر% - دید(km)")
    lines.append("────────────────────────────────────────────────────────────────────────────")

    for i in range(start_idx, min(end_idx + 1, start_idx + 24)):
        hour_str = times[i].split("T")[1][:5]  # HH:MM
        t = safe_float(temp[i] if i < len(temp) else None)
        p = safe_float(precip[i] if i < len(precip) else None)
        pp = safe_float(precip_prob[i] if i < len(precip_prob) else None)
        w = safe_float(wind[i] if i < len(wind) else None)
        wg = safe_float(windgust[i] if i < len(windgust) else None)
        h = safe_float(humidity[i] if i < len(humidity) else None)
        pr = safe_float(pressure[i] if i < len(pressure) else None)
        c = safe_float(cloud[i] if i < len(cloud) else None)
        vis = safe_float(visibility[i] if i < len(visibility) else None) / 1000  # تبدیل متر به کیلومتر

        line = f"{hour_str} | {t:.0f}° | {p:.1f} | {pp:.0f}% | {w:.0f} | {wg:.0f} | {h:.0f} | {pr:.0f} | {c:.0f} | {vis:.1f}"
        lines.append(line)

    lines.append("")
    return "\n".join(lines)

def build_forecast_text(forecast):
    if not forecast or "daily" not in forecast:
        return "⚠️ اطلاعات آب و هوا در دسترس نیست."

    daily = forecast["daily"]
    hourly = forecast.get("hourly", {})
    dates = daily.get("time", [])
    if not dates:
        return "⚠️ داده‌ای یافت نشد."

    max_t = daily.get("temperature_2m_max", [])
    min_t = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    rain = daily.get("rain_sum", [])
    snow = daily.get("snowfall_sum", [])
    wind = daily.get("windspeed_10m_max", [])
    codes = daily.get("weathercode", [])
    sunrise = daily.get("sunrise", [])
    sunset = daily.get("sunset", [])

    # زمان ایران با اعداد فارسی
    tehran_tz = ZoneInfo("Asia/Tehran")
    now_tehran = datetime.now(tehran_tz)
    update_str = now_tehran.strftime("%Y-%m-%d %H:%M:%S")
    update_str_fa = to_persian_digits(update_str)

    lines = []
    lines.append(f"پیش‌بینی {FORECAST_DAYS} روزه هوای سوته")
    lines.append(f"بروزرسانی: {update_str_fa}")
    lines.append("=" * 60)

    for i in range(len(dates)):
        jdate = gregorian_to_jalali(dates[i])
        t_min = safe_float(min_t[i] if i < len(min_t) else None)
        t_max = safe_float(max_t[i] if i < len(max_t) else None)
        p = safe_float(precip[i] if i < len(precip) else None)
        r = safe_float(rain[i] if i < len(rain) else None)
        s = safe_float(snow[i] if i < len(snow) else None)
        w = safe_float(wind[i] if i < len(wind) else None)
        code = int(safe_float(codes[i] if i < len(codes) else None))
        desc = weather_desc_persian(code)

        lines.append(f"\n📅 {jdate}")
        lines.append(f"🌡️ دما: {t_min:.0f} تا {t_max:.0f} درجه سانتی‌گراد")

        if p > 0:
            precip_line = f"💧 بارش: {p:.1f} میلی‌متر"
            if r > 0:
                precip_line += f" (باران {r:.1f})"
            if s > 0:
                precip_line += f" برف {s:.1f} سانتی‌متر"
            lines.append(precip_line)

        if w > 0:
            lines.append(f"🌬️ باد: تا {w:.0f} کیلومتر بر ساعت")

        lines.append(f"☁️ وضعیت: {desc}")

        if i < len(sunrise) and sunrise[i] and i < len(sunset) and sunset[i]:
            sr = sunrise[i].split("T")[1][:5] if "T" in sunrise[i] else sunrise[i]
            ss = sunset[i].split("T")[1][:5] if "T" in sunset[i] else sunset[i]
            lines.append(f"🌅 طلوع: {sr}  |  غروب: {ss}")

        # اضافه کردن جدول ساعتی فقط برای ۳ روز اول
        if i < HOURLY_DAYS and hourly:
            hourly_table = build_hourly_table(hourly, i, dates)
            lines.append(hourly_table)
        else:
            lines.append("")  # خط خالی بین روزها

    return "\n".join(lines)

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
            print(f"❌ HTTP error {resp.status_code}", flush=True)
    except Exception as e:
        print(f"❌ Exception: {e}", flush=True)

def main():
    print("🌤️ Weather bot for Suteh - Hourly for first 3 days, 10min interval", flush=True)
    start_time = time.time()
    max_runtime = 5.9 * 3600
    interval = 600

    iteration = 0
    while time.time() - start_time < max_runtime:
        iteration += 1
        print(f"\n🔄 Iteration {iteration} at {datetime.now().strftime('%H:%M:%S')}", flush=True)

        forecast = fetch_forecast()
        if forecast:
            text = build_forecast_text(forecast)
            # در صورت نیاز می‌توانید پیام را به چند بخش تقسیم کنید
            for uid in RUBIKA_USER_IDS:
                send_rubika_message(uid, text)
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
