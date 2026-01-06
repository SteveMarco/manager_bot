import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.error import BadRequest

# ================= CONFIG =================
BOT_TOKEN = "8507972610:AAEcYUpzHx6TJENmYNbXwutCxsj5t4F1jBA"

FORCE_JOIN_CHANNEL = "@riskisgoodbro"     # channel username
NOTIFY_CHANNEL_ID = -1003597689797        # admin/notification channel ID

DB_FILE = "storage.json"

# ================= DATABASE =================
def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

# ================= FORCE JOIN CHECK =================
async def is_user_joined(bot, user_id):
    try:
        member = await bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except BadRequest:
        return False

def join_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL.replace('@','')}")],
        [InlineKeyboardButton("🔄 Check Again", callback_data="check_join")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_user_joined(context.bot, user_id):
        await update.message.reply_text(
            "🚫 *Access Denied*\n\n"
            "Please join our channel to use this bot.",
            reply_markup=join_keyboard(),
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        "🗄️ *Personal Storage Bot*\n\n"
        "Send me:\n"
        "📷 Photos\n🎥 Videos\n📄 Documents\n🎧 Audio\n🎤 Voice\n\n"
        "Commands:\n"
        "/myfiles – View saved files\n"
        "/savedfiles – Get all files",
        parse_mode="Markdown"
    )

# ================= CHECK JOIN CALLBACK =================
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if await is_user_joined(context.bot, user_id):
        await query.message.edit_text("✅ You have joined the channel.\n\nSend /start")
    else:
        await query.message.reply_text(
            "❌ Still not joined.",
            reply_markup=join_keyboard()
        )

# ================= SAVE FILE =================
async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_user_joined(context.bot, user_id):
        await update.message.reply_text(
            "🚫 Please join our channel first.",
            reply_markup=join_keyboard()
        )
        return

    uid = str(user_id)
    db = load_db()
    db["users"].setdefault(uid, [])

    msg = update.message
    file_info = None
    file_type = None

    if msg.photo:
        file_info = msg.photo[-1].file_id
        file_type = "Photo"
    elif msg.video:
        file_info = msg.video.file_id
        file_type = "Video"
    elif msg.document:
        file_info = msg.document.file_id
        file_type = "Document"
    elif msg.audio:
        file_info = msg.audio.file_id
        file_type = "Audio"
    elif msg.voice:
        file_info = msg.voice.file_id
        file_type = "Voice"
    else:
        return

    db["users"][uid].append({
        "type": file_type.lower(),
        "file_id": file_info
    })
    save_db(db)

    await update.message.reply_text("✅ File saved permanently.")

    # 🔔 Notify Admin Channel
    await context.bot.send_message(
        NOTIFY_CHANNEL_ID,
        f"📥 *New File Stored*\n\n"
        f"👤 User ID: `{uid}`\n"
        f"📄 Type: {file_type}\n"
        f"📦 Total Files: {len(db['users'][uid])}",
        parse_mode="Markdown"
    )

# ================= LIST FILES =================
async def myfiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    db = load_db()

    if uid not in db["users"] or not db["users"][uid]:
        await update.message.reply_text("📭 No saved files.")
        return

    keyboard = [
        [InlineKeyboardButton(f"{f['type'].upper()} #{i+1}", callback_data=f"get|{i}")]
        for i, f in enumerate(db["users"][uid])
    ]

    await update.message.reply_text(
        "📂 *Your Saved Files*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================= SEND SINGLE FILE =================
async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = str(query.from_user.id)
    index = int(query.data.split("|")[1])
    db = load_db()
    f = db["users"][uid][index]

    if f["type"] == "photo":
        await query.message.reply_photo(f["file_id"])
    elif f["type"] == "video":
        await query.message.reply_video(f["file_id"])
    elif f["type"] == "document":
        await query.message.reply_document(f["file_id"])
    elif f["type"] == "audio":
        await query.message.reply_audio(f["file_id"])
    elif f["type"] == "voice":
        await query.message.reply_voice(f["file_id"])

# ================= SEND ALL FILES =================
async def savedfiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    db = load_db()

    if uid not in db["users"] or not db["users"][uid]:
        await update.message.reply_text("📭 No saved files.")
        return

    await update.message.reply_text(
        f"📦 Sending all files ({len(db['users'][uid])})..."
    )

    for f in db["users"][uid]:
        try:
            if f["type"] == "photo":
                await update.message.reply_photo(f["file_id"])
            elif f["type"] == "video":
                await update.message.reply_video(f["file_id"])
            elif f["type"] == "document":
                await update.message.reply_document(f["file_id"])
            elif f["type"] == "audio":
                await update.message.reply_audio(f["file_id"])
            elif f["type"] == "voice":
                await update.message.reply_voice(f["file_id"])
        except:
            pass

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("myfiles", myfiles))
app.add_handler(CommandHandler("savedfiles", savedfiles))

app.add_handler(CallbackQueryHandler(check_join, pattern="^check_join$"))
app.add_handler(CallbackQueryHandler(get_file, pattern="^get"))

app.add_handler(
    MessageHandler(
    filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO | filters.VOICE,
    save_file
)

)

print("🗄️ Storage Bot Dude  Notifications Running...")
app.run_polling()
