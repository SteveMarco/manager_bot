import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ================= CONFIG =================
BOT_TOKEN = "8429437338:AAHsdYbsU_2OqOY6b6JDQkbvYY4RXhdm8TM"

ADMIN_ID = 8443707949             # your Telegram ID
ADMIN_CHANNEL_ID = -1003576468345 # private channel ID

UPI_ID = "teamsinchuu07@abcdicici"
QR_IMAGE = "upi_qr.png"
DB_FILE = "db.json"

SERVICES = {
    "Followers 1K": 75,
    "Followers 2.5K": 170,
    "Followers 5K": 360,
    "Likes 1K": 60,
    "Likes 2.5K": 140,
    "Likes 5K": 280
}

# ================= DATABASE =================
def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        data = {"users": {}, "orders": []}
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return data

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

# ================= ADMIN NOTIFY =================
async def notify_admin(context, text):
    await context.bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    await context.bot.send_message(ADMIN_CHANNEL_ID, text, parse_mode="Markdown")

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    db = load_db()
    db["users"].setdefault(uid, {"balance": 0})
    save_db(db)

    keyboard = [
        [InlineKeyboardButton(f"{k} – ₹{v}", callback_data=f"service|{k}")]
        for k, v in SERVICES.items()
    ]
    keyboard += [
        [InlineKeyboardButton("💰 Show Balance", callback_data="balance")],
        [InlineKeyboardButton("📜 Order History", callback_data="history")],
        [InlineKeyboardButton("📝 Feedback", callback_data="feedback")],
        [InlineKeyboardButton("📞 Contact Admin", callback_data="contact_admin")],
        [InlineKeyboardButton("💳 Recharge", callback_data="recharge")]
    ]

    await update.message.reply_text(
        "📊 *Instagram SMM Panel*\n\nSelect a service:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================= SERVICE SELECT =================
async def service_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    service = query.data.split("|")[1]
    context.user_data["pending_service"] = service

    if "Followers" in service:
        await query.message.reply_text("📥 Send *Instagram Profile Link*:", parse_mode="Markdown")
    else:
        await query.message.reply_text("📥 Send *Instagram Post Link*:", parse_mode="Markdown")

# ================= PLACE ORDER =================
async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    service = context.user_data["pending_service"]
    link = update.message.text.strip()
    price = SERVICES[service]

    db = load_db()
    if db["users"][uid]["balance"] < price:
        await update.message.reply_text("❌ Insufficient balance")
        return

    db["users"][uid]["balance"] -= price
    order_id = len(db["orders"]) + 1
    db["orders"].append({
        "order_id": order_id,
        "user_id": uid,
        "service": service,
        "link": link,
        "price": price,
        "status": "Processing"
    })
    save_db(db)

    await update.message.reply_text(
        f"✅ *Order Placed Successfully*\n\n"
        f"📦 {service}\n"
        f"🔗 {link}\n"
        f"💰 Remaining Balance: ₹{db['users'][uid]['balance']}",
        parse_mode="Markdown"
    )

    await notify_admin(
        context,
        f"🛒 *NEW ORDER*\n"
        f"🆔 Order ID: {order_id}\n"
        f"👤 User ID: {uid}\n"
        f"📦 {service}\n"
        f"🔗 {link}\n"
        f"💰 ₹{price}"
    )

    context.user_data.clear()

# ================= RECHARGE =================
async def recharge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_photo(
        photo=open(QR_IMAGE, "rb"),
        caption=(
            f"💳 *Recharge Wallet*\n\n"
            f"UPI ID:\n`{UPI_ID}`\n\n"
            "Scan QR & pay.\nSend screenshot after payment."
        ),
        parse_mode="Markdown"
    )

# ================= SCREENSHOT =================
async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    caption = (
        "💳 *RECHARGE REQUEST*\n\n"
        f"👤 User ID: `{uid}`\n\n"
        "Approve:\n`/approve USERID AMOUNT`\n"
        "Reject:\n`/reject USERID reason`"
    )
    await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=caption, parse_mode="Markdown")
    await context.bot.send_photo(ADMIN_CHANNEL_ID, update.message.photo[-1].file_id, caption=caption, parse_mode="Markdown")
    await update.message.reply_text("✅ Screenshot sent to admin.")

# ================= ADMIN ACTIONS =================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    uid, amount = context.args[0], int(context.args[1])
    db = load_db()
    db["users"].setdefault(uid, {"balance": 0})
    db["users"][uid]["balance"] += amount
    save_db(db)
    await context.bot.send_message(int(uid), f"✅ Recharge Approved\n₹{amount} added.")
    await notify_admin(context, f"✅ Recharge Approved\nUser: {uid}\n₹{amount}")

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    uid = context.args[0]
    reason = " ".join(context.args[1:]) or "Payment not verified"
    await context.bot.send_message(int(uid), f"❌ Payment Rejected\nReason: {reason}")
    await notify_admin(context, f"❌ Recharge Rejected\nUser: {uid}\n{reason}")

async def complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    order_id = int(context.args[0])
    db = load_db()
    for o in db["orders"]:
        if o["order_id"] == order_id:
            o["status"] = "Completed"
            save_db(db)
            await context.bot.send_message(
                int(o["user_id"]),
                f"✅ Order Completed Successfully\nOrder ID: {order_id}\nService: {o['service']}"
            )
            await notify_admin(context, f"🎉 Order Completed\nOrder ID: {order_id}")
            return

# ================= CONTACT ADMIN =================
async def contact_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["contact_admin"] = True
    await query.message.reply_text("📞 Send your message to admin:")

async def contact_admin_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message.text
    await notify_admin(
        context,
        f"📩 USER QUERY\nUser ID: {uid}\nMessage:\n{msg}\n\nReply:\n/reply {uid} MESSAGE"
    )
    context.user_data.clear()
    await update.message.reply_text("✅ Message sent to admin.")

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    uid = context.args[0]
    msg = " ".join(context.args[1:])
    await context.bot.send_message(int(uid), f"📩 Admin Reply\n\n{msg}")
    await notify_admin(context, f"📩 Admin replied to {uid}")

# ================= BALANCE / HISTORY =================
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = load_db()
    uid = str(query.from_user.id)
    await query.message.reply_text(f"💰 Balance: ₹{db['users'][uid]['balance']}")

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    db = load_db()
    orders = [o for o in db["orders"] if o["user_id"] == uid]
    if not orders:
        await query.message.reply_text("No orders found.")
        return
    text = "📜 Order History\n\n"
    for o in orders:
        text += f"{o['order_id']} | {o['service']} | {o['status']}\n"
    await query.message.reply_text(text)

# ================= FEEDBACK =================
async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["feedback"] = True
    await query.message.reply_text("📝 Send your feedback:")

async def feedback_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await notify_admin(context, f"📝 FEEDBACK\nUser ID: {uid}\n{update.message.text}")
    context.user_data.clear()
    await update.message.reply_text("Thanks for your feedback!")

# ================= TEXT ROUTER (FIX FOR LIKES) =================
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("contact_admin"):
        await contact_admin_receive(update, context)
        return
    if context.user_data.get("feedback"):
        await feedback_receive(update, context)
        return
    if context.user_data.get("pending_service"):
        await receive_link(update, context)
        return

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("approve", approve))
app.add_handler(CommandHandler("reject", reject))
app.add_handler(CommandHandler("complete", complete))
app.add_handler(CommandHandler("reply", admin_reply))

app.add_handler(CallbackQueryHandler(service_handler, pattern="^service"))
app.add_handler(CallbackQueryHandler(show_balance, pattern="^balance$"))
app.add_handler(CallbackQueryHandler(history, pattern="^history$"))
app.add_handler(CallbackQueryHandler(feedback_start, pattern="^feedback$"))
app.add_handler(CallbackQueryHandler(contact_admin_start, pattern="^contact_admin$"))
app.add_handler(CallbackQueryHandler(recharge, pattern="^recharge$"))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
app.add_handler(MessageHandler(filters.PHOTO, screenshot))

print("🤖 Instagram SMM Panel Bot Running...")
app.run_polling()

