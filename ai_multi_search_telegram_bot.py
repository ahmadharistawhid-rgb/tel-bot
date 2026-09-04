#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import requests

# =========================
# Telegram
# =========================
BOT_TOKEN = "8933563838:AAFmzbZfekSwf4M2AqqZocBeKkdUM7gFL_Y"
ALLOWED_CHAT_ID = 8605371301
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# =========================
# Existing AI Multi Search backend
# =========================
FIREBASE_KEY = "AIzaSyA27E7jUV8osRY7NzwP2fZwGoTkp5gJhZw"
SEARCH_URL = "https://ai-multi-search-backend-321697147922.europe-west6.run.app/ask"

FIREBASE_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 16; 2311DRK48M Build/BP2A.250605.031.A3)",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "Content-Type": "application/json",
    "X-Android-Package": "com.lmtechstudio.aimultisearch",
    "X-Android-Cert": "5D08264B44E0E53FBCCC70B4F016474CC6C5AB5C",
    "Accept-Language": "ar-EG, en-US",
    "X-Client-Version": "Android/Fallback/X23001000/FirebaseCore-Android",
    "X-Firebase-GMPID": "1:321697147922:android:26e6fb8e30dcc23dfffccb",
    "X-Firebase-Client": "H4sIAAAAAAAA_6tWykhNLCpJSk0sKVayio7VUSpLLSrOzM9TslIyUqoFAFyivEQfAAAA",
}

token = None
token_expiry = 0

SEARCH_CFG = {
    "perplexity": {"app_version": "1.2.8", "search_id": "825a35c5-aac2-49d7-8317-5b7a68ae6cae"},
    "claude": {"app_version": "1.2.8", "search_id": "825a35c5-aac2-49d7-8317-5b7a68ae6cae"},
    "openai": {"app_version": "DEV_TEST", "search_id": "f0a6705c-e33e-4288-a3ef-c91cd6564b59"},
    "deepseek": {"app_version": "1.2.8", "search_id": "f0a6705c-e33e-4288-a3ef-c91cd6564b59"},
    "gemini": {"app_version": "1.2.8", "search_id": "b2ed082e-5793-4de0-9e42-c8c7fb57b5d5"},
    "llama": {"app_version": "1.2.8", "search_id": "b2ed082e-5793-4de0-9e42-c8c7fb57b5d5"},
}


def get_firebase_token():
    global token, token_expiry

    if token and time.time() < token_expiry - 60:
        return token

    r = requests.post(
        "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser",
        params={"key": FIREBASE_KEY},
        data=json.dumps({"clientType": "CLIENT_TYPE_ANDROID"}),
        headers=FIREBASE_HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()

    token = "Bearer " + data["idToken"]
    token_expiry = time.time() + int(data["expiresIn"])
    return token


def make_prompt(question, deepseek=False):
    base = (
        "You MUST answer in the EXACT same language as the user question.\n"
        "Do NOT change language.\n"
        "Do NOT mix languages.\n"
        "Do NOT translate unless explicitly asked.\n\n"
        "Formatting rules:\n"
        "- No tables.\n"
        "- No markdown tables.\n"
        "- No ASCII tables.\n"
        "- Do NOT use pipe characters: |\n"
        "- Use clean bullet points or short paragraphs.\n\n"
        f"User question:\n{question}"
    )

    if deepseek:
        return "Never reply in Chinese unless explicitly asked.\n\n" + base
    return base


def ask_provider(provider, question, firebase_token):
    cfg = SEARCH_CFG[provider]
    app_version = cfg["app_version"]

    payload = {
        "provider": provider,
        "prompt": make_prompt(question, provider == "deepseek"),
        "plan": "ULTRA",
        "app_version": app_version,
    }

    headers = {
        "User-Agent": "okhttp/4.12.0",
        "Accept-Encoding": "gzip",
        "authorization": firebase_token,
        "x-plan": "ULTRA",
        "x-app-version": app_version,
        "x-search-id": cfg["search_id"],
        "x-search-expected": "2",
        "content-type": "application/json; charset=utf-8",
    }

    r = requests.post(
        SEARCH_URL,
        data=json.dumps(payload),
        headers=headers,
        timeout=60,
    )
    r.raise_for_status()

    data = r.json()
    if data.get("ok"):
        return data.get("answer", "پاسخی دریافت نشد.")

    return "خطا: " + str(data.get("message", "پاسخ نامعتبر از سرور"))


def run_search(question):
    firebase_token = get_firebase_token()
    results = {}

    for provider in SEARCH_CFG:
        try:
            results[provider] = ask_provider(provider, question, firebase_token)
        except Exception as e:
            results[provider] = f"خطا در {provider}: {e}"

    return results


def telegram(method, payload=None):
    r = requests.post(
        f"{TG_API}/{method}",
        json=payload or {},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def send_message(chat_id, text):
    # Telegram message limit is 4096 chars.
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)] or [""]
    for chunk in chunks:
        telegram("sendMessage", {
            "chat_id": chat_id,
            "text": chunk,
        })


def process_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    # Only the configured Telegram ID can use the bot.
    if chat_id != ALLOWED_CHAT_ID:
        return

    text = (message.get("text") or "").strip()
    if not text:
        return

    if text == "/start":
        send_message(
            chat_id,
            "سلام 👋\n"
            "سؤال خودت را در همین یک فیلد بفرست.\n"
            "من آن را برای Providerهای AI ارسال می‌کنم و نتایج را برمی‌گردانم."
        )
        return

    if text == "/help":
        send_message(chat_id, "فقط سؤال خودت را به‌صورت یک پیام ارسال کن.")
        return

    send_message(chat_id, "⏳ در حال دریافت پاسخ‌ها...")

    try:
        results = run_search(text)

        parts = [f"🔎 سؤال:\n{text}\n"]
        for provider, answer in results.items():
            parts.append(f"\n━━ {provider.upper()} ━━\n{answer}")

        send_message(chat_id, "".join(parts))

    except Exception as e:
        send_message(chat_id, f"❌ خطا:\n{e}")


def main():
    print("Telegram AI Multi Search Bot started.")

    offset = None

    while True:
        try:
            data = telegram(
                "getUpdates",
                {
                    "timeout": 50,
                    "offset": offset,
                    "allowed_updates": ["message"],
                },
            )

            for update in data.get("result", []):
                offset = update["update_id"] + 1

                message = update.get("message")
                if message:
                    process_message(message)

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
