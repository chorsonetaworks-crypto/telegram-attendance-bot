import datetime
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- ការកំណត់រចនាសម្ព័ន្ធ (Configuration) ---
TOKEN = "8255597988:AAGHTdpa5_RlAW3CQnyr3LkllJo6RPuX5P0"
ADMIN_IDS = [820995778]  # Telegram ID របស់អ្នក (Admin)

# កន្លែងរក្សាទុកទិន្នន័យបណ្តោះអាសន្នជា File CSV
DATA_FILE = "attendance_records.csv"

def init_db():
    try:
        pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        df = pd.DataFrame(columns=["user_id", "username", "full_name", "action", "date", "time", "timestamp"])
        df.to_csv(DATA_FILE, index=False)

def log_attendance(user_id, username, full_name, action):
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    df = pd.read_csv(DATA_FILE)
    new_row = {
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "action": action,
        "date": date_str,
        "time": time_str,
        "timestamp": now.isoformat()
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    return date_str, time_str

# --- ប៊ូតុងបញ្ជាសម្រាប់បុគ្គលិក ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📍 Check In"), KeyboardButton("🚪 Check Out")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        f"សួស្តី {update.effective_user.first_name}!\nសូមជ្រើសរើស Check In ឬ Check Out ខាងក្រោម៖",
        reply_markup=reply_markup
    )

# --- ការកត់ត្រាពេលបុគ្គលិកចុច ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    if text in ["📍 Check In", "🚪 Check Out"]:
        action = "CHECK_IN" if text == "📍 Check In" else "CHECK_OUT"
        date_str, time_str = log_attendance(user.id, user.username, full_name, action)
        await update.message.reply_text(
            f"✅ បានកត់ត្រាជោគជ័យ!\n\nបុគ្គលិក: {full_name}\nសកម្មភាព: {action}\nកាលបរិច្ឆេទ: {date_str}\nម៉ោង: {time_str}"
        )

# --- ប្រព័ន្ធទាញយករបាយការណ៍ជា Excel សម្រាប់ Admin ---
async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int, report_name: str):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ សូមអភ័យទោស សកម្មភាពនេះសម្រាប់តែ Admin ប៉ុណ្ណោះ។")
        return

    df = pd.read_csv(DATA_FILE)
    if df.empty:
        await update.message.reply_text("មិនទាន់មានទិន្នន័យវត្តមាននៅឡើយទេ។")
        return

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
    filtered_df = df[df["timestamp"] >= cutoff_date]

    # បង្កើតឯកសារ Excel
    excel_filename = f"{report_name}_Attendance_Report.xlsx"
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, sheet_name='Attendance', index=False)

    # ផ្ញើឯកសារ Excel មកកាន់ Telegram របស់ Admin
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=open(excel_filename, 'rb'),
        caption=f"📊 របាយការណ៍វត្តមាន ({report_name}) - {days} ថ្ងៃចុងក្រោយ"
    )

async def report_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_report(update, context, days=7, report_name="Weekly")

async def report_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_report(update, context, days=30, report_name="Monthly")

# --- កម្មវិធីចាប់ផ្តើមដំណើរការ ---
if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report_weekly", report_weekly))
    app.add_handler(CommandHandler("report_monthly", report_monthly))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot កំពុងដំណើរការ...")
    app.run_polling()
