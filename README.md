# ChatInfoBot

Your own private Telegram bot for inspecting chat IDs, user IDs, message metadata, and more — no need to trust random third-party bots.

## Setup

### 1. Create your bot

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the API token you receive

### 2. Configure

```bash
cp .env.example .env
```

Paste your token into `.env`:

```
BOT_TOKEN=123456789:ABCdef...
```

### 3. Install & Run (locally)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

### 3b. Or deploy to Railway

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app), create a new project, and connect your repo
3. In the service settings, add the environment variable `BOT_TOKEN` with your token
4. Deploy — that's it, the bot runs 24/7

## Commands

| Command | What it does |
|---------|-------------|
| `/start` | Show help |
| `/id` | Quick chat ID + your user ID (reply to a message to also see that user's ID) |
| `/info` | Full details for the current chat (description, invite link, member count, etc.) |
| `/me` | Your user profile info |
| `/json` | Raw JSON dump of the message (reply to a message to dump that one) |

## Other tricks

- **Forward a message** to the bot to see where it came from (user ID, channel ID, etc.)
- **Send any media** (photo, video, sticker, document) to get file IDs you can reuse in other bots
- **Add the bot to a group** and it will greet with full group info — then use any command in the group
- **Reply to someone's message** with `/id` to see their user ID without them needing to interact with the bot

## What info can it extract?

- User ID, first/last name, username, language, premium status
- Chat/group/channel ID, title, type, description, invite link
- Message ID, date, thread ID, media group ID
- Forward origin (original sender user/channel/chat ID)
- File IDs for photos, videos, documents, audio, voice, stickers, animations
- Contact, location, and poll metadata
- Sender chat (when posting on behalf of a channel)
- Via-bot info (for inline bot results)
- Full raw JSON of any message
