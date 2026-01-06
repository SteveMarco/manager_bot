import os
import sqlite3
from datetime import datetime, date, time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ---------- TIMEZONE ----------
os.environ["TZ"] = "Asia/Kolkata"

# ---------- CONFIG ----------
BOT_TOKEN = "8220389274:AAFojIhbRmGdzY0J55j34sthZJqqjvUoL9U"
CHANNEL_ID = -1003349435060
PRIVATE_CHANNEL_LINK = "https://t.me/+zfw6yQ3gb1JmYTRl"
LOW_STOCK_LIMIT = 7

ADMIN_IDS = [8443707949]

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ---------- DATABASE ----------
conn = sqlite3.connect("shop.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS rice_stock(brand TEXT, kg INTEGER, pcs INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS udhar(name TEXT, phone TEXT, pending INTEGER, updated_time TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS contacts(name TEXT, phone TEXT UNIQUE)")
cur.execute("CREATE TABLE IF NOT EXISTS joined_users(user_id INTEGER UNIQUE)")
conn.commit()

# ---------- JOIN VERIFY HELPERS ----------
def is_verified_user(user_id: int) -> bool:
    cur.execute("SELECT 1 FROM joined_users WHERE user_id=?", (user_id,))
    return cur.fetchone() is not None

def mark_user_verified(user_id: int):
    cur.execute("INSERT OR IGNORE INTO joined_users VALUES(?)", (user_id,))
    conn.commit()

# ---------- BUTTONS ----------
kb = ReplyKeyboardMarkup(
    [
        ["➕ Add Rice", "🗑️ Remove Brand"],
        ["📦 Brand Stocks", "📊 Total Stocks"],
        ["➕ Add / Update Udhar"],
        ["📇 Contacts", "❌ Remove Paid Udhar"],
        ["💰 Pending Summary"],
        ["⏱ Time Records"]
    ],
    resize_keyboard=True
)

# ---------- START (ONE-TIME JOIN CHECK) ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_verified_user(user_id):
        try:
            member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
            if member.status in ["member", "administrator", "creator"]:
                mark_user_verified(user_id)
            else:
                raise Exception
        except:
            await update.message.reply_text(
                "🔒 Please join our private channel once to use this bot:\n\n"
                f"{PRIVATE_CHANNEL_LINK}\n\n"
                "After joining, press /start again."
            )
            return

    context.user_data.clear()
    await update.message.reply_text(
        "🙏 ಸ್ವಾಗತ\n🌾 ಅನೂಪ್ ಮಯಾಂಕ್ ಬಾಲಾಜಿ ರೈಸ್ ಕಾರ್ನರ್‌ಗೆ 🌾",
        reply_markup=kb
    )

# ---------- ADMIN BUTTON MODES ----------
async def add_rice(update, context):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Permission denied")
    context.user_data["mode"] = "add_rice"
    await update.message.reply_text("Send:\nBrand Kg Pcs")

async def remove_brand(update, context):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Permission denied")
    context.user_data["mode"] = "remove_brand"
    await update.message.reply_text("Send brand name")

async def add_udhar(update, context):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Permission denied")
    context.user_data["mode"] = "udhar"
    await update.message.reply_text(
        "New Udhar:\nName Phone Amount\n\nChange:\nName /change Amount"
    )

async def remove_udhar(update, context):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Permission denied")
    context.user_data["mode"] = "remove_udhar"
    await update.message.reply_text("Send person name")

# ---------- VIEW FEATURES ----------
async def brand_stocks(update, context):
    cur.execute("SELECT brand, kg, pcs FROM rice_stock")
    rows = cur.fetchall()
    msg = "📦 Brand Stocks\n\n" + "\n".join(f"{b} {k}kg – {p} pcs" for b, k, p in rows) if rows else "No stock"
    await update.message.reply_text(msg)

async def total_stocks(update, context):
    cur.execute("SELECT SUM(pcs) FROM rice_stock")
    await update.message.reply_text(f"📊 Total bags left: {cur.fetchone()[0] or 0}")

async def pending_summary(update, context):
    cur.execute("SELECT name, pending FROM udhar WHERE pending > 0")
    rows = cur.fetchall()
    if not rows:
        return await update.message.reply_text("No pending")
    msg = f"💰 Pending Summary\nTotal: ₹{sum(r[1] for r in rows)}\n\n"
    msg += "\n".join(f"{n} – ₹{p}" for n, p in rows)
    await update.message.reply_text(msg)

async def time_records(update, context):
    cur.execute("SELECT name, pending, updated_time FROM udhar")
    rows = cur.fetchall()
    msg = "⏱ Time Records\n\n" + "\n".join(f"{n} – ₹{p} – {t}" for n, p, t in rows) if rows else "No records"
    await update.message.reply_text(msg)

async def contacts_list(update, context):
    cur.execute("SELECT name, phone FROM contacts")
    rows = cur.fetchall()
    msg = "📇 Udhar Contacts\n\n" + "\n".join(f"{n} – {p}" for n, p in rows) if rows else "No contacts"
    msg += "\n\n/remove Name (Admin only)"
    await update.message.reply_text(msg)

# ---------- REMOVE CONTACT ----------
async def remove_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Permission denied")
    if not context.args:
        return await update.message.reply_text("Usage: /remove Name")
    name = " ".join(context.args)
    cur.execute("DELETE FROM contacts WHERE name=?", (name,))
    conn.commit()
    await update.message.reply_text(f"✅ Contact removed: {name}")

# ---------- TEXT ROUTER ----------
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ You are not allowed to make changes")

    text = update.message.text.strip()
    mode = context.user_data.get("mode")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        if mode == "add_rice":
            b, k, p = text.split()
            cur.execute("DELETE FROM rice_stock WHERE brand=?", (b,))
            cur.execute("INSERT INTO rice_stock VALUES(?,?,?)", (b, int(k), int(p)))

        elif mode == "remove_brand":
            cur.execute("DELETE FROM rice_stock WHERE brand=?", (text,))

        elif mode == "udhar":
            if "/change" in text:
                n, _, a = text.split()
                cur.execute("UPDATE udhar SET pending=?, updated_time=? WHERE name=?", (int(a), now, n))
            else:
                n, ph, a = text.split()
                cur.execute("DELETE FROM udhar WHERE name=?", (n,))
                cur.execute("INSERT INTO udhar VALUES(?,?,?,?)", (n, ph, int(a), now))
                cur.execute("INSERT OR IGNORE INTO contacts VALUES(?,?)", (n, ph))

        elif mode == "remove_udhar":
            cur.execute("DELETE FROM udhar WHERE name=?", (text,))

        conn.commit()
        await update.message.reply_text("✅ Done")
    except:
        await update.message.reply_text("❌ Format error")

# ---------- LOW STOCK ALERT ----------
async def low_stock_alert(context):
    cur.execute("SELECT brand, kg, pcs FROM rice_stock WHERE pcs <= ?", (LOW_STOCK_LIMIT,))
    rows = cur.fetchall()
    if rows:
        msg = "⚠️ LOW STOCK ALERT\n\n" + "\n".join(f"{b} {k}kg – {p} pcs" for b, k, p in rows)
        await context.bot.send_message(CHANNEL_ID, msg)

# ---------- DAILY SUMMARY ----------
async def daily_summary(context):
    today = date.today()
    cur.execute("SELECT brand, kg, pcs FROM rice_stock")
    stocks = cur.fetchall()
    cur.execute("SELECT name, pending FROM udhar WHERE pending > 0")
    udhars = cur.fetchall()

    msg = f"🌙 DAILY SUMMARY ({today})\n\n🌾 STOCK:\n"
    msg += "\n".join(f"{b} {k}kg – {p} pcs" for b, k, p in stocks)
    msg += f"\n\n👥 Pending Persons: {len(udhars)}\n💰 Total Pending: ₹{sum(u[1] for u in udhars)}\n"
    msg += "\n".join(f"{n} – ₹{a}" for n, a in udhars)

    await context.bot.send_message(CHANNEL_ID, msg)

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remove", remove_contact))

    app.add_handler(MessageHandler(filters.Regex("➕ Add Rice"), add_rice))
    app.add_handler(MessageHandler(filters.Regex("🗑️ Remove Brand"), remove_brand))
    app.add_handler(MessageHandler(filters.Regex("📦 Brand Stocks"), brand_stocks))
    app.add_handler(MessageHandler(filters.Regex("📊 Total Stocks"), total_stocks))
    app.add_handler(MessageHandler(filters.Regex("➕ Add / Update Udhar"), add_udhar))
    app.add_handler(MessageHandler(filters.Regex("📇 Contacts"), contacts_list))
    app.add_handler(MessageHandler(filters.Regex("❌ Remove Paid Udhar"), remove_udhar))
    app.add_handler(MessageHandler(filters.Regex("💰 Pending Summary"), pending_summary))
    app.add_handler(MessageHandler(filters.Regex("⏱ Time Records"), time_records))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    app.job_queue.run_repeating(low_stock_alert, interval=1800, first=60)
    app.job_queue.run_daily(daily_summary, time=time(hour=21, minute=0))

    print("✅ Rice Shop Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()

