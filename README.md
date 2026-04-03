# Telegram Autoreply Bot

A Telegram bot that automatically replies to messages using an LLM via the OpenRouter API, configurable with a custom system prompt and persona.

## Features

- Auto-replies to text messages using any OpenRouter-supported model
- Configurable persona via `system_prompt.txt`
- Per-user conversation history (last 8 messages retained in context)
- Persistent user facts — the LLM can emit `###MEMORY:` directives to learn and remember details about users across sessions
- All conversations logged to `logs/chats.jsonl` (JSONL format)
- CLI log viewer with follow mode
- Docker Compose support
- Graceful fallback — recursively retries with halved history on API failure

## Requirements

- Python 3.12+
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- An OpenRouter API key (from [openrouter.ai](https://openrouter.ai))

## Setup

1. Clone the repository:

```bash
git clone https://github.com/openclaw-agents/telegram-autoreply-bot.git
cd telegram-autoreply-bot
```

2. Copy and configure environment variables:

```bash
cp .env.example .env
```

Edit `.env` and set your keys:

```
TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
OPENROUTER_API_KEY=<your-openrouter-api-key>
OPENROUTER_MODEL=qwen/qwen3.6-plus:free
```

3. Copy and customize the system prompt:

```bash
cp system_prompt.txt.example system_prompt.txt
```

Edit `system_prompt.txt` to define the bot's persona.

4. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Local

```bash
python autoreply.py
```

### Docker

```bash
docker compose up -d
```

## Log Viewer

View the last N chat entries:

```bash
python view_logs.py -n 10
```

Follow logs in real time (like `tail -f`):

```bash
python view_logs.py -f
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from BotFather | (required) |
| `OPENROUTER_API_KEY` | OpenRouter API key | (required) |
| `OPENROUTER_MODEL` | OpenRouter model ID | `qwen/qwen3.6-plus:free` |

## Project Structure

| File | Description |
|---|---|
| `autoreply.py` | Main bot logic — message handling, LLM calls, fact extraction |
| `view_logs.py` | CLI log viewer for `logs/chats.jsonl` |
| `system_prompt.txt` | Bot persona prompt (gitignored, copy from `.example`) |
| `.env` | Environment variables (gitignored, copy from `.example`) |
| `logs/chats.jsonl` | Persistent conversation log |
| `logs/user_facts.json` | Persisted user facts extracted from LLM output |

## License

MIT
