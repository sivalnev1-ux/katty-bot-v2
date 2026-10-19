import json
import os
import random
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from fastapi import FastAPI, Request

GREEN_BASE = os.environ.get("GREEN_BASE", "https://7107.api.greenapi.com")
GREEN_ID = os.environ.get("GREEN_ID", "710722744965")
GREEN_TOKEN = os.environ.get("GREEN_TOKEN", "a5f2cc63f99842d39d27056289fc398becd25aea26a74d3bad")
DESK = os.environ.get("DESK_URL", "https://katty-desk-production.up.railway.app")
XAI_KEY = os.environ.get("XAI_API_KEY", "")
XAI_URL = "https://api.x.ai/v1/chat/completions"

KNOWN = Path(__file__).with_name("known_phones.txt")
SEEN = Path("/tmp/katty_seen.txt")
NIGHT_SENT = Path("/tmp/katty_night_sent.txt")
HOURS_IMG = Path(__file__).with_name("hours.jpg")
INTRO_IMG = Path(__file__).with_name("intro_prices.png")
LOYALTY_IMG = Path(__file__).with_name("loyalty.jpg")
SUPPORT = "972524864703@c.us"

WELCOME = """היי מותק 
שמי קטיה אני בת 35 אוקראינית 
המפגש אצלי עד לחצי שעה ב 400 שקל בלבד!
כולל פינוק מלא!!!
תמונות וסירטונים שלי אתה יכול לראות בערוצים שלי :

https://t.me/kattykinkfun

https://whatsapp.com/channel/0029Vb8aPq3Fsn0nFznuKY1Q

מתי נוח להגיע?"""

SYSTEM = """את קטיה, בת 35, אוקראינית, בבאר שבע. כותבת קצר כמו וואטסאפ חי. לא בוט.

כללים קשיחים:
- פגישה ראשונה רק חצי שעה, 400 שקל, מזומן במקום. שעה רק מביקור שני ורק אם הוא שאל. שעתיים ומעלה — אף פעם.
- הנחה אין. אם מבקש זול: שלחי פלייר מחירי היכרות (10 דק 250 / 15 דק 300) ותגידי "הנחה אין, אבל יש מחיר היכרות". אם כבר היה — אפשר להציע חבילה 4+1 או 3+1.
- שעות: 09:00–22:00 כל יום כולל שבת. לילה אין.
- מקום: באר שבע, שכונת דרום, צמוד לעיר העתיקה. כתובת מדויקת רק כשהוא יוצא / בדרך. אחרת: כתובת מדויקת 40 דק לפני.
- רק אחד. אין קבוצות, אין שלישיות.
- יציאה: רק עד חצי שעה באזור באר שבע, 800 שקל, רק אחד על אחד.
- תוספות רק אם שאל: מקלחת ביחד +100, נשיקות +150 (לא מעשן/לא שתה), ירידה לי +100, לגמור עליי או בפה +100, אנאלי +200 מחליטה במקום, סטראפ-און +200. אין חדירה באצבעות.
- שליטה/מלכת/הצלפות: https://kattykink.netlify.app/mistress
- תמונות נוספות: קיבלתה בהודעה ראשונה. אם ממשיך — בקשה לא לכתוב סתם.
- אם אומר שיגיע / בערב / מחר: מחכה לך.
- שפה: עברית → עברית, רוסית → רוסית. קצר. בלי הרצאות.
- לא להבטיח "עכשיו פותחת". רק "רגע".
- אם לא מבין או מבקש יציאה מסובכת: רגע, בודקת. ודווח לתמיכה.

תענה רק את התשובה הסופית, בלי הסברים."""

app = FastAPI()
MUTED: set[str] = set()


def load_set(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()}


KNOWN_PHONES = load_set(KNOWN)


def phone_of(chat_id: str) -> str:
    return (chat_id or "").split("@")[0]


def already(phone: str) -> bool:
    return phone in KNOWN_PHONES or phone in load_set(SEEN)


def mark_seen(phone: str) -> None:
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    with SEEN.open("a", encoding="utf-8") as f:
        f.write(phone + "\n")
    KNOWN_PHONES.add(phone)


def night_already(phone: str) -> bool:
    if not NIGHT_SENT.exists():
        return False
    return phone in {x.strip() for x in NIGHT_SENT.read_text(encoding="utf-8").splitlines() if x.strip()}


def mark_night(phone: str) -> None:
    NIGHT_SENT.parent.mkdir(parents=True, exist_ok=True)
    with NIGHT_SENT.open("a", encoding="utf-8") as f:
        f.write(phone + "\n")


def bot_on() -> bool:
    try:
        r = requests.get(f"{DESK}/api/board", timeout=8)
        return not bool(r.json().get("paused"))
    except Exception:
        return True


def is_night() -> bool:
    now = datetime.now(timezone(timedelta(hours=3)))
    h = now.hour
    return h >= 23 or h < 8


def send(chat_id: str, text: str) -> None:
    time.sleep(random.uniform(1.2, 2.2))
    url = f"{GREEN_BASE}/waInstance{GREEN_ID}/sendMessage/{GREEN_TOKEN}"
    try:
        requests.post(url, json={"chatId": chat_id, "message": text}, timeout=20)
    except Exception:
        pass


def send_file(chat_id: str, path: Path, caption: str = ""):
    time.sleep(1.3)
    if not path.exists():
        if caption:
            send(chat_id, caption)
        return
    try:
        url = f"{GREEN_BASE}/waInstance{GREEN_ID}/sendFileByUpload/{GREEN_TOKEN}"
        with path.open("rb") as f:
            files = {"file": (path.name, f, "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png")}
            data = {"chatId": chat_id, "caption": caption}
            r = requests.post(url, data=data, files=files, timeout=30)
            if not r.ok and caption:
                send(chat_id, caption)
    except Exception:
        if caption:
            send(chat_id, caption)


def wants_discount(text: str) -> bool:
    t = (text or "").lower()
    keys = ("הנחה", "זול", "תזיל", "פחות", "скидк", "дешев", "дешевле", "дешёв", "discount", "cheaper")
    return any(k in t for k in keys)


def send_hours(chat_id: str):
    send_file(chat_id, HOURS_IMG, "כרגע לא עובדת. שעות העבודה שלי: 9:00–22:00. תכתוב לי בשעות האלה, בבקשה.")


def history(chat_id: str) -> str:
    url = f"{GREEN_BASE}/waInstance{GREEN_ID}/getChatHistory/{GREEN_TOKEN}"
    try:
        r = requests.post(url, json={"chatId": chat_id, "count": 15}, timeout=20)
        data = r.json()
    except Exception:
        return ""
    if not isinstance(data, list):
        return ""
    lines = []
    for m in reversed(data[-12:]):
        who = "קליינט" if m.get("type") == "incoming" else "קטיה"
        txt = m.get("textMessage") or ""
        if txt:
            lines.append(f"{who}: {txt}")
    return "\n".join(lines)


def ask_grok(hist: str, text: str) -> str:
    if not XAI_KEY:
        return "רגע, בודקת."
    payload = {
        "model": "grok-3",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"היסטוריה:\n{hist}\n\nהודעה חדשה:\n{text}"},
        ],
        "temperature": 0.4,
        "max_tokens": 180,
    }
    try:
        r = requests.post(
            XAI_URL,
            headers={"Authorization": f"Bearer {XAI_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=25,
        )
        if r.ok:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return "רגע, בודקת."


@app.get("/")
def health():
    return {"ok": True, "known": len(KNOWN_PHONES), "grok": bool(XAI_KEY)}


@app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()
    if body.get("typeWebhook") != "incomingMessageReceived":
        return {"ok": True}
    if not bot_on():
        return {"ok": True, "skipped": "paused"}

    sender = ((body.get("senderData") or {}).get("chatId")) or ""
    if not sender.endswith("@c.us"):
        return {"ok": True}
    phone = phone_of(sender)
    if phone in MUTED:
        return {"ok": True, "muted": True}

    if is_night():
        if not night_already(phone):
            if already(phone):
                send_hours(sender)
            else:
                send(sender, WELCOME)
                send_hours(sender)
                mark_seen(phone)
            mark_night(phone)
        return {"ok": True, "night": True}

    msg = body.get("messageData") or {}
    text = (
        ((msg.get("textMessageData") or {}).get("textMessage"))
        or ((msg.get("extendedTextMessageData") or {}).get("text"))
        or ""
    )
    if not text.strip():
        return {"ok": True}

    if not already(phone):
        send(sender, WELCOME)
        mark_seen(phone)
        return {"ok": True, "welcome": True}

    hist = history(sender)
    low = (text + " " + hist).lower()
    if any(w in low for w in ("יציאה", "לצאת", "выезд", "ко мне", "outcall", "не понял", "לא מבין", "???",
                               "שניים", "שלושה", "זוג", "חברים", "יחד", "двоем", "вдвоем", "троих", "тройнич", "group", "together", "пара")):
        send(sender, "минутку")
        send(SUPPORT, f"⚠️ Требует внимания. Чат {phone}\nТекст: {text[:100]}")
        MUTED.add(phone)
        return {"ok": True, "support": True}

    if wants_discount(text):
        send_file(sender, INTRO_IMG, "הנחה אין מותק. יש מחיר היכרות: 10 דק 250 / 15 דק 300")
        send_file(sender, LOYALTY_IMG, "ואם בא לך קבוע — יש חבילה: 4+1 או 3+1 (Private Month)")
        mark_seen(phone)
        return {"ok": True, "discount": True}

    reply = ask_grok(hist, text)
    if reply:
        send(sender, reply)
    mark_seen(phone)
    return {"ok": True}
