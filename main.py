import os
import logging
import asyncio
import random
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)

# ================== ЛОГИ ==================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================== СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ ==================
user_states = {}
user_scores = {}

# ================== ФУНКЦИЯ ЗАГРУЗКИ ЛЕКЦИЙ ==================
def load_lectures_from_file(filename="lecture.txt"):
    """Загрузка лекций из текстового файла"""
    lectures_data = {}
    if not os.path.exists(filename):
        logger.warning(f"Файл {filename} не найден")
        return lectures_data

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    lecture_blocks = content.split("### ЛЕКЦИЯ")
    for block in lecture_blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()
        try:
            header = lines[0].strip()
            lecture_id = int(header.split(".")[0])
            lecture_title = ".".join(header.split(".")[1:]).strip()
        except Exception as e:
            logger.error(f"Ошибка парсинга заголовка лекции: {e}")
            continue

        sections = []
        section_title = None
        section_content = []

        for line in lines[1:]:
            if line.startswith("## "):
                if section_title:
                    sections.append({
                        "title": section_title,
                        "content": "\n".join(section_content).strip()
                    })
                    section_content = []
                section_title = line[3:].strip()
            else:
                section_content.append(line)

        if section_title:
            sections.append({
                "title": section_title,
                "content": "\n".join(section_content).strip()
            })

        lectures_data[lecture_id] = {
            "id": lecture_id,
            "title": lecture_title,
            "sections": sections
        }

    logger.info(f"Загружено лекций: {len(lectures_data)}")
    return lectures_data

# ================== ПОДГРУЗКА ЛЕКЦИЙ ==================
lectures = load_lectures_from_file("lecture.txt")

# ================== ВОПРОСЫ ВИКТОРИНЫ (пример) ==================
quiz_questions = [
    {
        "question": "Что является предметом экономической теории?",
        "options": ["А) Политические отношения", "Б) Законы функционирования и развития хозяйства", "В) Социальные проблемы"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Основы экономической теории"
    },
]

# ================== МЕНЕДЖЕР ТАЙМЕРОВ ==================
class TimerManager:
    def __init__(self):
        self.timers = {}

    async def set_timer(self, key, delay, callback, *args):
        self.cancel_timer(key)
        task = asyncio.create_task(self._timer_task(key, delay, callback, args))
        self.timers[key] = task

    def cancel_timer(self, key):
        if key in self.timers:
            self.timers[key].cancel()
            del self.timers[key]

    async def _timer_task(self, key, delay, callback, args):
        try:
            await asyncio.sleep(delay)
            await callback(*args)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Ошибка таймера: {e}")
        finally:
            self.cancel_timer(key)

timer_manager = TimerManager()

# ================== УТИЛИТЫ ==================
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖋️ Проверь себя", callback_data="quiz_menu")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton("🏆 Рейтинг", callback_data="leaderboard")],
        [InlineKeyboardButton("📚 Курс лекций", callback_data="lectures")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ])

def format_question_text(question, state, result=None):
    difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
    emoji = difficulty_emoji.get(question["difficulty"], "⚪")
    text = (
        f"🎯 Вопрос {state['current_index'] + 1}/{len(state['questions'])} {emoji}\n"
        f"📚 Тема: {question['topic']}\n\n"
        f"🧠 <b>{question['question']}</b>\n\n"
    )
    for option in question["options"]:
        text += f"{option}\n"
    if result:
        text += f"\n{result}"
    else:
        text += f"\n⏰ У вас есть <b>{question['time_limit']}</b> секунд!"
    return text

# ================== ОБРАБОТЧИКИ ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🚀 Привет, {user.first_name}!\n"
        "📚 Я помогу тебе изучить экономическую теорию и проверить знания",
        reply_markup=get_main_keyboard()
    )

async def show_lectures_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not lectures:
        await query.edit_message_text("❌ Лекции пока недоступны", reply_markup=get_main_keyboard())
        return

    text = "📚 <b>Курс лекций</b>\n\nВыберите лекцию:"
    keyboard = [[InlineKeyboardButton(f"📖 {lec['title']}", callback_data=f"lecture_{lec_id}_0")]
                for lec_id, lec in lectures.items()]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def show_lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, lecture_id, section_index = query.data.split("_")
    lecture_id, section_index = int(lecture_id), int(section_index)

    lecture = lectures.get(lecture_id)
    if not lecture:
        await query.edit_message_text("❌ Лекция не найдена")
        return

    section = lecture["sections"][section_index]
    text = (
        f"📚 <b>{lecture['title']}</b>\n\n"
        f"🔹 <b>{section['title']}</b>\n\n"
        f"{section['content']}\n\n"
        f"📄 Раздел {section_index + 1}/{len(lecture['sections'])}"
    )

    buttons = []
    if section_index > 0:
        buttons.append(InlineKeyboardButton("⬅️ Предыдущий", callback_data=f"lecture_{lecture_id}_{section_index - 1}"))
    if section_index < len(lecture["sections"]) - 1:
        buttons.append(InlineKeyboardButton("Следующий ➡️", callback_data=f"lecture_{lecture_id}_{section_index + 1}"))

    nav_buttons = [buttons] if buttons else []
    nav_buttons.append([InlineKeyboardButton("📚 К списку лекций", callback_data="lectures")])
    nav_buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(nav_buttons), parse_mode="HTML")

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🏠 Главное меню", reply_markup=get_main_keyboard())

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "❓ <b>Помощь</b>\n\n"
        "Этот бот поможет вам изучить основы экономической теории и пройти викторину.\n"
        "📚 Курс лекций — теоретические материалы\n"
        "🖋️ Проверь себя — тесты по темам\n"
        "📊 Моя статистика — личные результаты\n"
        "🏆 Рейтинг — топ игроков"
    )
    await query.edit_message_text(text, reply_markup=get_main_keyboard(), parse_mode="HTML")

# ================== ЗАПУСК ==================
def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("Токен Telegram не найден в переменных окружения")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_lectures_menu, pattern="^lectures$"))
    app.add_handler(CallbackQueryHandler(show_lecture, pattern=r"^lecture_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(show_help, pattern="^help$"))

    logger.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
