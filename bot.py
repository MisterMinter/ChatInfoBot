import html
import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from telegram import Chat, Message, Update, User
from telegram.constants import ChatType, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def esc(text: str | None) -> str:
    """HTML-escape a string, returning empty string for None."""
    if text is None:
        return ""
    return html.escape(str(text))


def fmt_user(user: User) -> str:
    lines = [
        f"<b>User Info</b>",
        f"  ID: <code>{user.id}</code>",
        f"  First name: {esc(user.first_name)}",
    ]
    if user.last_name:
        lines.append(f"  Last name: {esc(user.last_name)}")
    if user.username:
        lines.append(f"  Username: @{esc(user.username)}")
    lines.append(f"  Is bot: {user.is_bot}")
    if user.language_code:
        lines.append(f"  Language: {esc(user.language_code)}")
    if user.is_premium:
        lines.append(f"  Premium: Yes")
    return "\n".join(lines)


def fmt_chat(chat: Chat) -> str:
    lines = [
        f"<b>Chat Info</b>",
        f"  ID: <code>{chat.id}</code>",
        f"  Type: {esc(chat.type)}",
    ]
    if chat.title:
        lines.append(f"  Title: {esc(chat.title)}")
    if chat.username:
        lines.append(f"  Username: @{esc(chat.username)}")
    if chat.first_name:
        lines.append(f"  First name: {esc(chat.first_name)}")
    if chat.last_name:
        lines.append(f"  Last name: {esc(chat.last_name)}")
    return "\n".join(lines)


def fmt_chat_full(chat: Chat) -> str:
    """Format full chat info from getChat API response."""
    lines = [
        f"<b>Chat Info (full)</b>",
        f"  ID: <code>{chat.id}</code>",
        f"  Type: {esc(chat.type)}",
    ]
    if chat.title:
        lines.append(f"  Title: {esc(chat.title)}")
    if chat.username:
        lines.append(f"  Username: @{esc(chat.username)}")
    if chat.first_name:
        lines.append(f"  First name: {esc(chat.first_name)}")
    if chat.last_name:
        lines.append(f"  Last name: {esc(chat.last_name)}")
    if chat.description:
        lines.append(f"  Description: {esc(chat.description)}")
    if chat.bio:
        lines.append(f"  Bio: {esc(chat.bio)}")
    if chat.invite_link:
        lines.append(f"  Invite link: {esc(chat.invite_link)}")
    if chat.linked_chat_id:
        lines.append(f"  Linked chat ID: <code>{chat.linked_chat_id}</code>")
    if chat.has_private_forwards:
        lines.append(f"  Has private forwards: Yes")
    if chat.has_restricted_voice_and_video_messages:
        lines.append(f"  Restricted voice/video: Yes")
    if chat.join_to_send_messages:
        lines.append(f"  Join to send: Yes")
    if chat.join_by_request:
        lines.append(f"  Join by request: Yes")
    if chat.slow_mode_delay:
        lines.append(f"  Slow mode delay: {chat.slow_mode_delay}s")
    if chat.message_auto_delete_time:
        lines.append(f"  Auto-delete: {chat.message_auto_delete_time}s")
    if chat.has_aggressive_anti_spam_enabled:
        lines.append(f"  Aggressive anti-spam: Yes")
    if chat.has_hidden_members:
        lines.append(f"  Hidden members: Yes")
    if chat.has_protected_content:
        lines.append(f"  Protected content: Yes")
    return "\n".join(lines)


def fmt_message_meta(msg: Message) -> str:
    lines = [
        f"<b>Message Info</b>",
        f"  Message ID: <code>{msg.message_id}</code>",
        f"  Date: {msg.date.strftime('%Y-%m-%d %H:%M:%S UTC') if msg.date else 'N/A'}",
    ]
    if msg.message_thread_id:
        lines.append(f"  Thread ID: <code>{msg.message_thread_id}</code>")
    if msg.media_group_id:
        lines.append(f"  Media group ID: <code>{esc(msg.media_group_id)}</code>")
    if msg.is_topic_message:
        lines.append(f"  Topic message: Yes")
    return "\n".join(lines)


def fmt_forward_origin(msg: Message) -> str | None:
    if not msg.forward_origin:
        return None

    origin = msg.forward_origin
    lines = [f"<b>Forward Origin</b>"]
    lines.append(f"  Type: {esc(origin.type)}")
    lines.append(f"  Date: {origin.date.strftime('%Y-%m-%d %H:%M:%S UTC') if origin.date else 'N/A'}")

    if origin.type == "user" and origin.sender_user:
        lines.append(f"  Sender user ID: <code>{origin.sender_user.id}</code>")
        lines.append(f"  Sender name: {esc(origin.sender_user.first_name)}")
        if origin.sender_user.username:
            lines.append(f"  Sender username: @{esc(origin.sender_user.username)}")
    elif origin.type == "hidden_user":
        lines.append(f"  Sender name: {esc(origin.sender_user_name)}")
    elif origin.type == "chat" and origin.sender_chat:
        lines.append(f"  Sender chat ID: <code>{origin.sender_chat.id}</code>")
        if origin.sender_chat.title:
            lines.append(f"  Sender chat title: {esc(origin.sender_chat.title)}")
        if origin.author_signature:
            lines.append(f"  Author signature: {esc(origin.author_signature)}")
    elif origin.type == "channel" and origin.chat:
        lines.append(f"  Channel ID: <code>{origin.chat.id}</code>")
        if origin.chat.title:
            lines.append(f"  Channel title: {esc(origin.chat.title)}")
        if origin.chat.username:
            lines.append(f"  Channel username: @{esc(origin.chat.username)}")
        if origin.message_id:
            lines.append(f"  Original message ID: <code>{origin.message_id}</code>")
        if origin.author_signature:
            lines.append(f"  Author signature: {esc(origin.author_signature)}")

    return "\n".join(lines)


def fmt_media_info(msg: Message) -> str | None:
    """Extract info about any media attached to the message."""
    parts: list[str] = []

    if msg.photo:
        largest = msg.photo[-1]
        parts.append(
            f"<b>Photo</b>\n"
            f"  File ID: <code>{esc(largest.file_id)}</code>\n"
            f"  Unique ID: <code>{esc(largest.file_unique_id)}</code>\n"
            f"  Size: {largest.width}x{largest.height}"
        )
    if msg.video:
        v = msg.video
        parts.append(
            f"<b>Video</b>\n"
            f"  File ID: <code>{esc(v.file_id)}</code>\n"
            f"  Unique ID: <code>{esc(v.file_unique_id)}</code>\n"
            f"  Size: {v.width}x{v.height}, {v.duration}s\n"
            f"  MIME: {esc(v.mime_type)}"
        )
    if msg.document:
        d = msg.document
        parts.append(
            f"<b>Document</b>\n"
            f"  File ID: <code>{esc(d.file_id)}</code>\n"
            f"  Unique ID: <code>{esc(d.file_unique_id)}</code>\n"
            f"  Name: {esc(d.file_name)}\n"
            f"  MIME: {esc(d.mime_type)}"
        )
    if msg.audio:
        a = msg.audio
        parts.append(
            f"<b>Audio</b>\n"
            f"  File ID: <code>{esc(a.file_id)}</code>\n"
            f"  Unique ID: <code>{esc(a.file_unique_id)}</code>\n"
            f"  Duration: {a.duration}s\n"
            f"  MIME: {esc(a.mime_type)}"
        )
    if msg.voice:
        vo = msg.voice
        parts.append(
            f"<b>Voice</b>\n"
            f"  File ID: <code>{esc(vo.file_id)}</code>\n"
            f"  Unique ID: <code>{esc(vo.file_unique_id)}</code>\n"
            f"  Duration: {vo.duration}s"
        )
    if msg.sticker:
        s = msg.sticker
        parts.append(
            f"<b>Sticker</b>\n"
            f"  File ID: <code>{esc(s.file_id)}</code>\n"
            f"  Unique ID: <code>{esc(s.file_unique_id)}</code>\n"
            f"  Emoji: {esc(s.emoji)}\n"
            f"  Set: {esc(s.set_name)}"
        )
    if msg.animation:
        a = msg.animation
        parts.append(
            f"<b>Animation/GIF</b>\n"
            f"  File ID: <code>{esc(a.file_id)}</code>\n"
            f"  Unique ID: <code>{esc(a.file_unique_id)}</code>"
        )
    if msg.contact:
        c = msg.contact
        parts.append(
            f"<b>Contact</b>\n"
            f"  Phone: {esc(c.phone_number)}\n"
            f"  Name: {esc(c.first_name)} {esc(c.last_name)}\n"
            f"  User ID: <code>{c.user_id or 'N/A'}</code>"
        )
    if msg.location:
        loc = msg.location
        parts.append(
            f"<b>Location</b>\n"
            f"  Lat: {loc.latitude}\n"
            f"  Lon: {loc.longitude}"
        )
    if msg.poll:
        p = msg.poll
        parts.append(
            f"<b>Poll</b>\n"
            f"  ID: <code>{esc(p.id)}</code>\n"
            f"  Question: {esc(p.question)}\n"
            f"  Type: {esc(p.type)}"
        )

    return "\n\n".join(parts) if parts else None


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context) -> None:
    await update.message.reply_text(
        "<b>Chat Info Bot</b> — your own private metadata inspector.\n\n"
        "<b>Commands:</b>\n"
        "/start — This help message\n"
        "/id — Quick ID of current chat + your user ID\n"
        "/info — Full details for this chat\n"
        "/me — Your full user profile info\n"
        "/json — Raw JSON dump of the last message\n\n"
        "<b>Other tricks:</b>\n"
        "• Forward any message here to see its origin info\n"
        "• Send any media to see file IDs and metadata\n"
        "• Add me to a group to inspect group info\n"
        "• Reply to a message with /json to dump that message",
        parse_mode=ParseMode.HTML,
    )


async def cmd_id(update: Update, context) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    lines = [f"<b>Quick IDs</b>"]
    if user:
        lines.append(f"  Your user ID: <code>{user.id}</code>")
    lines.append(f"  This chat ID: <code>{chat.id}</code>")
    lines.append(f"  Chat type: {esc(chat.type)}")

    if msg.reply_to_message:
        replied = msg.reply_to_message
        lines.append("")
        lines.append(f"<b>Replied-to message</b>")
        lines.append(f"  Message ID: <code>{replied.message_id}</code>")
        if replied.from_user:
            lines.append(f"  From user ID: <code>{replied.from_user.id}</code>")
            name = replied.from_user.first_name or ""
            if replied.from_user.username:
                name += f" (@{replied.from_user.username})"
            lines.append(f"  From: {esc(name)}")
        if replied.sender_chat:
            lines.append(f"  Sender chat ID: <code>{replied.sender_chat.id}</code>")

    await msg.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_info(update: Update, context) -> None:
    chat = update.effective_chat
    try:
        full_chat = await context.bot.get_chat(chat.id)
        text = fmt_chat_full(full_chat)
    except Exception:
        text = fmt_chat(chat)

    if chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        try:
            count = await context.bot.get_chat_member_count(chat.id)
            text += f"\n  Member count: {count}"
        except Exception:
            pass

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_me(update: Update, context) -> None:
    user = update.effective_user
    if not user:
        await update.message.reply_text("Could not determine your user info.")
        return
    await update.message.reply_text(fmt_user(user), parse_mode=ParseMode.HTML)


async def cmd_json(update: Update, context) -> None:
    target = update.effective_message
    if target.reply_to_message:
        target = target.reply_to_message

    raw = target.to_json()
    try:
        formatted = json.dumps(json.loads(raw), indent=2, ensure_ascii=False)
    except Exception:
        formatted = raw

    MAX_LEN = 4000
    if len(formatted) > MAX_LEN:
        formatted = formatted[:MAX_LEN] + "\n... (truncated)"

    await update.effective_message.reply_text(
        f"<pre>{esc(formatted)}</pre>",
        parse_mode=ParseMode.HTML,
    )


async def handle_any_message(update: Update, context) -> None:
    """Respond to any non-command message with all extractable info."""
    msg = update.effective_message
    if not msg:
        return

    sections: list[str] = []

    if msg.from_user:
        sections.append(fmt_user(msg.from_user))

    sections.append(fmt_chat(update.effective_chat))
    sections.append(fmt_message_meta(msg))

    if msg.sender_chat:
        sections.append(
            f"<b>Sender Chat (posted on behalf of)</b>\n"
            f"  ID: <code>{msg.sender_chat.id}</code>\n"
            f"  Type: {esc(msg.sender_chat.type)}\n"
            f"  Title: {esc(msg.sender_chat.title)}"
        )

    fwd = fmt_forward_origin(msg)
    if fwd:
        sections.append(fwd)

    media = fmt_media_info(msg)
    if media:
        sections.append(media)

    if msg.reply_to_message:
        r = msg.reply_to_message
        reply_lines = [f"<b>Reply-to Message</b>", f"  Message ID: <code>{r.message_id}</code>"]
        if r.from_user:
            reply_lines.append(f"  From user ID: <code>{r.from_user.id}</code>")
            reply_lines.append(f"  From: {esc(r.from_user.first_name)}")
        if r.sender_chat:
            reply_lines.append(f"  Sender chat ID: <code>{r.sender_chat.id}</code>")
        sections.append("\n".join(reply_lines))

    if msg.via_bot:
        sections.append(
            f"<b>Via Bot</b>\n"
            f"  ID: <code>{msg.via_bot.id}</code>\n"
            f"  Username: @{esc(msg.via_bot.username)}"
        )

    text = "\n\n".join(sections)

    MAX_LEN = 4000
    if len(text) > MAX_LEN:
        text = text[:MAX_LEN] + "\n... (truncated)"

    await msg.reply_text(text, parse_mode=ParseMode.HTML)


async def handle_new_members(update: Update, context) -> None:
    """When the bot is added to a group, send a greeting with the group info."""
    msg = update.effective_message
    bot_id = context.bot.id

    if not msg.new_chat_members:
        return

    for member in msg.new_chat_members:
        if member.id == bot_id:
            try:
                full_chat = await context.bot.get_chat(update.effective_chat.id)
                text = (
                    f"<b>Hello!</b> I'm now in this chat. Here's what I see:\n\n"
                    f"{fmt_chat_full(full_chat)}"
                )
            except Exception:
                text = (
                    f"<b>Hello!</b> I'm now in this chat.\n\n"
                    f"{fmt_chat(update.effective_chat)}"
                )
            await msg.reply_text(text, parse_mode=ParseMode.HTML)
            return


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(CommandHandler("me", cmd_me))
    app.add_handler(CommandHandler("json", cmd_json))

    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members)
    )

    app.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_any_message)
    )

    logger.info("Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
