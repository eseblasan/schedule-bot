import json
import os
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# =========================
# 🌍 TIMEZONE
# =========================
KYIV = ZoneInfo("Europe/Kyiv")

# =========================
# 🔐 TOKEN
# =========================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN not found in environment")

# =========================
# 🔥 НАСТРОЙКИ СЕМЕСТРА
# =========================
SEMESTER_START = date(2026, 2, 2)  # первый понедельник 1 недели

# =========================
# 📦 УТИЛИТЫ
# =========================

def load_schedule():
    with open("schedule.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_week():
    today = date.today()
    weeks_passed = (today - SEMESTER_START).days // 7
    return "week1" if weeks_passed % 2 == 0 else "week2"

def format_day(lessons):
    if not lessons:
        return "🎉 Пар нет"

    text = ""
    for l in lessons:
        text += (
            f"🕘 {l['start']}–{l['end']}\n"
            f"📘 {l['subject']}\n"
            f"📌 {l.get('type', '—')}\n\n"
        )
    return text

# =========================
# 🔔 УВЕДОМЛЕНИЯ
# =========================

async def notify_lesson(context: ContextTypes.DEFAULT_TYPE):
    lesson = context.job.data

    text = (
        "⏰ *Скоро пара!*\n\n"
        f"🕘 {lesson['start']}–{lesson['end']}\n"
        f"📘 {lesson['subject']}\n"
        f"📌 {lesson.get('type', '—')}"
    )

    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=text,
        parse_mode="Markdown"
    )

def schedule_today(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    schedule = load_schedule()
    week = get_week()

    now = datetime.now(KYIV)
    today = now.strftime("%A").lower()

    lessons = schedule[week].get(today, [])

    for lesson in lessons:
        start_time = datetime.strptime(lesson["start"], "%H:%M").time()

        notify_time = datetime.combine(
            now.date(),
            start_time,
            tzinfo=KYIV
        ) - timedelta(minutes=10)

        if notify_time > now:
            context.job_queue.run_once(
                notify_lesson,
                when=notify_time,
                chat_id=chat_id,
                data=lesson,
                name=str(chat_id)
            )

# =========================
# 📌 КОМАНДЫ
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Я бот з розкладом.\n\n"
        "/today — пари сьогодні\n"
        "/tomorrow — пари завтра\n"
        "/week — весь тиждень\n"
        "/notify — увімкнути нагадування\n"
        "/testnotify — тест JobQueue"
    )

async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # удаляем старые уведомления
    for job in context.job_queue.get_jobs_by_name(str(update.effective_chat.id)):
        job.schedule_removal()

    schedule_today(context, update.effective_chat.id)

    await update.message.reply_text(
        "🔔 Уведомления включены\n"
        "Я напомню за 10 минут до пары 😉"
    )

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule = load_schedule()
    week = get_week()
    day = datetime.now(KYIV).strftime("%A").lower()

    await update.message.reply_text(
        f"📅 Сьогодні:\n\n{format_day(schedule[week].get(day, []))}"
    )

async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule = load_schedule()
    week = get_week()
    tomorrow_idx = (datetime.now(KYIV).weekday() + 1) % 7
    day = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"][tomorrow_idx]

    await update.message.reply_text(
        f"📅 Завтра:\n\n{format_day(schedule[week].get(day, []))}"
    )

async def week_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule = load_schedule()
    week = get_week()

    msg = f"📆 {week.upper()}\n\n"
    for day, lessons in schedule[week].items():
        msg += f"🔹 {day.capitalize()}:\n"
        msg += format_day(lessons) + "\n"

    await update.message.reply_text(msg)

async def test_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.job_queue.run_once(
        lambda c: c.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🧪 JobQueue работает 🔥"
        ),
        when=10
    )
    await update.message.reply_text("🧪 Тест через 10 секунд")

# =========================
# 🚀 ЗАПУСК
# =========================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("today", today))
app.add_handler(CommandHandler("tomorrow", tomorrow))
app.add_handler(CommandHandler("week", week_cmd))
app.add_handler(CommandHandler("notify", notify))
app.add_handler(CommandHandler("testnotify", test_notify))

print("✅ Bot started")
app.run_polling()
