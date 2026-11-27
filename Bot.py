
import os
import json
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

OWNER_ID = int(os.environ["OWNER_ID"])
TOKEN = os.environ["BOT_TOKEN"]

DATA_FILE = Path("settings.json")

DEFAULT_SETTINGS = {
    "text": "Hello! Thanks for messaging.\nPlease check the links below:",
    "links": [
        ["Link 1", "https://example.com"],
        ["Link 2", "https://example.com"],
        ["Link 3", "https://example.com"],
    ],
    "paused": [],
    "chats": {},
}


def load_settings():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


settings = load_settings()


def save_settings():
    DATA_FILE.write_text(json.dumps(settings, indent=2))


def is_owner(update):
    user = update.effective_user
    return user is not None and user.id == OWNER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    await update.effective_message.reply_text(
        "Saad Auto Reply Bot\n\n"
        "/settext Your message\n"
        "/setlinks Name1 | URL1 | Name2 | URL2 | Name3 | URL3\n"
        "/chats - show chats\n"
        "/pause CHAT_ID - pause a chat\n"
        "/resume CHAT_ID - resume a chat"
    )


async def settext(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    text = update.effective_message.text.partition(" ")[2].strip()

    if not text:
        await update.effective_message.reply_text(
            "Use: /settext Your auto reply message"
        )
        return

    settings["text"] = text
    save_settings()

    await update.effective_message.reply_text("Auto reply message updated!")


async def setlinks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    raw = update.effective_message.text.partition(" ")[2]
    parts = [p.strip() for p in raw.split("|")]

    if len(parts) != 6:
        await update.effective_message.reply_text(
            "Use:\n"
            "/setlinks Name1 | URL1 | Name2 | URL2 | Name3 | URL3"
        )
        return

    links = []
    for i in range(0, 6, 2):
        name, url = parts[i], parts[i + 1]

        if not url.startswith(("https://", "http://")):
            await update.effective_message.reply_text(
                "Har link http:// ya https:// se start hona chahiye."
            )
            return

        links.append([name, url])

    settings["links"] = links
    save_settings()

    await update.effective_message.reply_text("3 links updated!")


async def chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    known = settings["chats"]

    if not known:
        await update.effective_message.reply_text("Abhi koi chat record nahi.")
        return

    lines = []
    for chat_id, name in list(known.items())[-50:]:
        status = "PAUSED" if int(chat_id) in settings["paused"] else "ACTIVE"
        lines.append(f"{name} — {chat_id} — {status}")

    await update.effective_message.reply_text("\n".join(lines))


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update) or not context.args:
        return

    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("Valid chat ID do.")
        return

    if chat_id not in settings["paused"]:
        settings["paused"].append(chat_id)

    save_settings()
    await update.effective_message.reply_text(f"Chat {chat_id} paused.")


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update) or not context.args:
        return

    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("Valid chat ID do.")
        return

    settings["paused"] = [
        cid for cid in settings["paused"] if cid != chat_id
    ]

    save_settings()
    await update.effective_message.reply_text(f"Chat {chat_id} resumed.")


async def business_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.business_message

    if not msg or not msg.business_connection_id:
        return

    chat_id = msg.chat_id

    # Owner's manual outgoing message pauses that chat.
    if msg.from_user and msg.from_user.id == OWNER_ID:
        if chat_id not in settings["paused"]:
            settings["paused"].append(chat_id)
            save_settings()
        return

    # Don't auto-reply to bots.
    if msg.from_user and msg.from_user.is_bot:
        return

    settings["chats"][str(chat_id)] = (
        msg.chat.full_name if msg.chat else str(chat_id)
    )
    save_settings()

    if chat_id in settings["paused"]:
        return

    keyboard = [
        [InlineKeyboardButton(name, url=url)]
        for name, url in settings["links"]
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        business_connection_id=msg.business_connection_id,
        text=settings["text"],
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settext", settext))
    app.add_handler(CommandHandler("setlinks", setlinks))
    app.add_handler(CommandHandler("chats", chats))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))

    app.add_handler(
        MessageHandler(filters.ALL, business_reply)
    )

    base_url = os.environ["RENDER_EXTERNAL_URL"].rstrip("/")
    port = int(os.environ.get("PORT", "10000"))
    path = os.environ.get("WEBHOOK_PATH", "telegram-hook")

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=path,
        webhook_url=f"{base_url}/{path}",
        secret_token=os.environ["WEBHOOK_SECRET"],
        allowed_updates=[
            "business_connection",
            "business_message",
            "edited_business_message",
            "message",
        ],
    )


if __name__ == "__main__":
    main()
