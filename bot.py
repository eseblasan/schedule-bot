import json
import os
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

import day
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from Schedule import ScheduleForDay, Lesson

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
        data = json.load(f)

    full_schedule = {}

    for week_name, days in data.items():
        week_days_list = []

        for day_name, lessons_raw in days.items():
            lessons_objects = []

            for l in lessons_raw:
                lesson = Lesson(
                    start=l.get("start"),
                    end=l.get("end"),
                    subject=l.get("subject"),
                    lesson_type=l.get("type"),
                    group=l.get("group")
                )
                lessons_objects.append(lesson)

            day_obj = ScheduleForDay(day=day_name, lessons=lessons_objects)
            week_days_list.append(day_obj)

        full_schedule[week_name] = week_days_list

    return full_schedule


def get_week():
    today = date.today()
    weeks_passed = (today - SEMESTER_START).days // 7
    return "week1" if weeks_passed % 2 == 0 else "week2"


def format_day(lessons):
    if not lessons:
        return "Пар немає"

    result = ""
    for l in lessons:
        result += (
            f"🕘 {l.start} – {l.end}\n"
            f"📚 {l.subject}\n"
            f"👤 {l.lesson_type}\n"
        )
        if l.group:
            result += f"👥 {l.group}\n"
        result += "\n"
    return result

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
    day_data = next((d for d in schedule[week] if d.day == day), None)
    lessons = day_data.lessons if day_data else []

    if not lessons:
        text = "📅 Сьогодні пар немає. Відпочивай! 😎"
    else:
        text = f"📅 Сьогодні:\n\n{format_day(lessons)}"

    await update.message.reply_text(text)


import datetime


async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule = load_schedule()
    now = datetime.datetime.now(KYIV)
    tomorrow_date = now + datetime.timedelta(days=1)
    tomorrow_idx = tomorrow_date.weekday()  # 0 = monday, 6 = sunday

    day_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][tomorrow_idx]

    week = get_week()
    if tomorrow_idx == 0:
        week = "week2" if week == "week1" else "week1"
    day_data = next((d for d in schedule[week] if d.day == day_name), None)

    lessons = day_data.lessons if day_data else []

    if not lessons:
        response_text = f"📅 Завтра ({day_name}) пар немає. Можна виспатися! 😴"
    else:
        response_text = f"📅 Завтра:\n\n{format_day(lessons)}"

    await update.message.reply_text(response_text)


async def week_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule = load_schedule()
    week_key = get_week()

    msg = f"📆 РОЗКЛАД: {week_key.upper()}\n"
    msg += "" + "—" * 20 + "\n\n"

    for day_obj in schedule[week_key]:
        msg += f"🔹 {day_obj.day.upper()}:\n"

        if not day_obj.lessons:
            msg += "   Вихідний 🙌\n"
        else:
            msg += format_day(day_obj.lessons)
        msg += "\n"

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
