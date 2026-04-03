import os
import json
import time
import logging
import requests
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "chats.jsonl"
FACTS_FILE = LOG_DIR / "user_facts.json"

chat_logger = logging.getLogger("chat")
chat_logger.setLevel(logging.INFO)
_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(message)s"))
chat_logger.addHandler(_handler)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_HISTORY = 8

# Memory for conversation history and user facts
user_histories = defaultdict(list)
user_facts = defaultdict(dict)

def save_user_facts():
    try:
        with open(FACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_facts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving facts: {e}")

def load_user_facts():
    if not FACTS_FILE.exists():
        return
    try:
        with open(FACTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for uid_str, facts in data.items():
                user_facts[int(uid_str)] = facts
        print(f"Loaded facts for {len(user_facts)} users.")
    except Exception as e:
        print(f"Error loading facts: {e}")

def load_history_from_logs():
    if not LOG_FILE.exists():
        return
    
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    uid = data.get("user_id")
                    if uid:
                        # Add user message and assistant reply to history
                        user_histories[uid].append({"role": "user", "content": data["message"]})
                        user_histories[uid].append({"role": "assistant", "content": data["reply"]})
                        # Keep only the last MAX_HISTORY messages
                        if len(user_histories[uid]) > MAX_HISTORY:
                            user_histories[uid] = user_histories[uid][-MAX_HISTORY:]
                except json.JSONDecodeError:
                    continue
        msg_count = sum(len(h) for h in user_histories.values())
        print(f"Loaded {msg_count} messages from logs into history memory.")
    except Exception as e:
        print(f"Error loading history: {e}")

# Initial load
load_history_from_logs()
load_user_facts()

# System prompt
SYSTEM_PROMPT_FILE = Path("system_prompt.txt")

def load_system_prompt() -> str:
    try:
        return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        print("Warning: system_prompt.txt not found. Using fallback.")
        return "You are a helpful assistant."

SYSTEM_PROMPT_TEMPLATE = load_system_prompt()

def generate_reply(user_id: int, user_text: str, history_limit: int = MAX_HISTORY) -> str:
    if not OPENROUTER_API_KEY:
        return "api key belum diset ke."

    facts = user_facts.get(user_id, {})
    user_bio = "Info user: " + ", ".join([f"{k}={v}" for k, v in facts.items()]) if facts else "Belum ada info user."

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(user_bio=user_bio)
    messages = [{"role": "system", "content": system_prompt}]
    
    current_history = user_histories[user_id][-history_limit:]
    messages.extend(current_history)
    messages.append({"role": "user", "content": user_text})

    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/openclaw-agents/telegram-autoreply",
                "X-Title": "Telegram Autoreply Bot",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "max_tokens": 1500, 
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_reply = data["choices"][0]["message"]["content"]
        
        # Clean potential analysis blocks (anything before a known starting point or just take the last bit)
        # Some models use "Okay," or "Analysis:" or just a thought block.
        # We try to find the last part that doesn't look like analysis.
        reply = raw_reply
        if "###MEMORY:" in reply:
            parts = reply.split("###MEMORY:")
            reply = parts[0].strip()
            mem_line = parts[1].split("\n")[0].strip()
            if "=" in mem_line:
                for pair in mem_line.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        user_facts[user_id][k.strip().lower()] = v.strip()
                save_user_facts()

        # Final cleanup for "Thinking" blocks
        if "Okay," in reply and len(reply) > 200:
             # Heuristic: if it's long and starts with "Okay,", it might be analysis
             # Let's try to split by double newline and take the last part if the first part looks meta
             lines = reply.split("\n\n")
             if len(lines) > 1:
                 reply = lines[-1].strip()

        # Update history
        user_histories[user_id].append({"role": "user", "content": user_text})
        user_histories[user_id].append({"role": "assistant", "content": reply})
        if len(user_histories[user_id]) > MAX_HISTORY:
            user_histories[user_id] = user_histories[user_id][-MAX_HISTORY:]
            
        return reply
    except Exception as e:
        print(f"Error: {e}")
        if history_limit > 2:
            return generate_reply(user_id, user_text, history_limit=history_limit // 2)
        return "sorry br0 lagi ada error. coba kirim lagi chat yang tadi"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text:
        return
        
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    print(f"--- Incoming from @{username} ({user_id}) ---")
    print(f"Message: {user_text}")

    reply = generate_reply(user_id, user_text)

    print(f"Reply: {reply}")
    print(f"-------------------------------------------")

    log = json.dumps({
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "username": username,
        "message": user_text,
        "reply": reply,
    }, ensure_ascii=False)
    chat_logger.info(log)

    MAX_LENGTH = 4000
    if len(reply) <= MAX_LENGTH:
        await update.message.reply_text(reply)
    else:
        for i in range(0, len(reply), MAX_LENGTH):
            await update.message.reply_text(reply[i:i + MAX_LENGTH])


def main():
    if not BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not found in environment.")
        return
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
