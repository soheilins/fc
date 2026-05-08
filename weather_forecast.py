#!/usr/bin/env python3
import os
import sys
import requests
import time
import arabic_reshaper
from bidi.algorithm import get_display

RUBIKA_TOKEN = os.environ.get("RUBIKA_TOKEN", "")
if not RUBIKA_TOKEN:
    print("❌ RUBIKA_TOKEN not set")
    sys.exit(1)

RUBIKA_USER_ID = "b0JWE2R0cCz01c6f676803e07bf4e745"   # replace if different

BASE_API = f"https://botapi.rubika.ir/v3/{RUBIKA_TOKEN}"
SEND_MESSAGE_URL = f"{BASE_API}/sendMessage"

raw_text = "پیش‌بینی ۱۶ روزه هوای ساری: دوشنبه ۱۰ اردیبهشت ۱۴۰۴، دمای ۱۳ تا ۲۱ درجه"

def reshape_persian(text):
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except:
        return text

methods = {
    "1. Plain (no reshaping)": raw_text,
    "2. Only reshape + bidi": reshape_persian(raw_text),
    "3. RTL Embedding (U+202B)": "\u202B" + reshape_persian(raw_text) + "\u202C",
    "4. LTR Embedding (U+202A)": "\u202A" + reshape_persian(raw_text) + "\u202C",
    "5. RTL Override (U+202E)": "\u202E" + reshape_persian(raw_text) + "\u202C",
    "6. LTR Override (U+202D)": "\u202D" + reshape_persian(raw_text) + "\u202C",
    "7. RTL Isolate (U+2067)": "\u2067" + reshape_persian(raw_text) + "\u2069",
    "8. LTR Isolate (U+2066)": "\u2066" + reshape_persian(raw_text) + "\u2069",
    "9. First char RLM (U+200F) + reshape": "\u200F" + reshape_persian(raw_text),
    "10. First char LRM (U+200E) + reshape": "\u200E" + reshape_persian(raw_text),
}

def send_message(chat_id, text, method_name):
    payload = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(SEND_MESSAGE_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "OK":
                print(f"✅ Sent: {method_name}")
            else:
                print(f"❌ Failed: {method_name} - {data}")
        else:
            print(f"❌ HTTP error for {method_name}: {resp.status_code}")
    except Exception as e:
        print(f"❌ Exception for {method_name}: {e}")

def main():
    print("Sending RTL test messages...")
    for name, text in methods.items():
        send_message(RUBIKA_USER_ID, text, name)
        time.sleep(1)
    print("All sent. Check your Rubika chat.")

if __name__ == "__main__":
    main()
