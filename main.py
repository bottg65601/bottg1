import os
import logging
import asyncio
import random
import time
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)
from aiohttp import web

# ================== ЛОГИ ==================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==================
user_states = {}
user_scores = {}
lectures = {}
quiz_questions = []

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

# ================== ЗАГРУЗКА ЛЕКЦИЙ ==================
def load_lectures_from_file(filename="lecture.txt"):
    lectures_data = {}
    if not os.path.exists(filename):
        logger.warning(f"Файл {filename} не найден — лекции будут пустыми")
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

# ================== ЗАГРУЗКА ВОПРОСОВ ==================
def load_quiz_questions():
    return [
        {
            "question": "Что является предметом экономической теории?",
            "options": ["А) Политические отношения", "Б) Законы функционирования и развития хозяйства", "В) Социальные проблемы"],
            "answer": "Б",
            "difficulty": "easy",
            "time_limit": 15,
            "topic": "Основы экономической теории"
        },
    ]

# ================== КЛАВИАТУРЫ ==================
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖋️ Проверь себя", callback_data="quiz_menu")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton("🏆 Рейтинг", callback_data="leaderboard")],
        [InlineKeyboardButton("📚 Курс лекций", callback_data="lectures")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ])

# ================== ВСПОМОГАТЕЛЬНЫЕ ==================
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
    await update.message.reply_text(
        f"🚀 Привет, {update.effective_user.first_name}!\n"
        "📚 Я помогу тебе изучить экономическую теорию и проверить знания",
        reply_markup=get_main_keyboard()
    )

async def quiz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🎮 Быстрая игра (5 вопросов)", callback_data="mode_quick")],
        [InlineKeyboardButton("🟢 Легкий (10 вопросов)", callback_data="difficulty_easy")],
        [InlineKeyboardButton("🟡 Средний (15 вопросов)", callback_data="difficulty_medium")],
        [InlineKeyboardButton("🔴 Сложный (20 вопросов)", callback_data="difficulty_hard")],
        [InlineKeyboardButton("📚 По темам", callback_data="mode_topics")],
        [InlineKeyboardButton("🔀 Случайный вопрос", callback_data="mode_single")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    await query.edit_message_text("🖋️ Выберите режим викторины:", reply_markup=InlineKeyboardMarkup(keyboard))

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str, topic: str = None):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    config = {
        "mode_quick": {"count": 5, "difficulty_filter": ["easy", "medium", "hard"]},
        "difficulty_easy": {"count": 10, "difficulty_filter": ["easy"]},
        "difficulty_medium": {"count": 15, "difficulty_filter": ["medium"]},
        "difficulty_hard": {"count": 20, "difficulty_filter": ["hard"]},
        "mode_topics": {"count": 15, "topic": topic},
        "mode_single": {"count": 1, "difficulty_filter": ["easy", "medium", "hard"]}
    }[mode]

    if "topic" in config:
        questions = [q for q in quiz_questions if q["topic"] == config["topic"]]
    else:
        questions = [q for q in quiz_questions if q["difficulty"] in config["difficulty_filter"]]

    if not questions:
        await query.edit_message_text("❌ Нет вопросов по выбранному критерию")
        return

    user_states[chat_id] = {
        "mode": "quiz_session",
        "questions": random.sample(questions, min(len(questions), config["count"])),
        "current_index": 0,
        "correct_answers": 0,
        "answered": False
    }
    await ask_question(chat_id, context.bot)

async def ask_question(chat_id: int, bot):
    state = user_states[chat_id]
    if state["current_index"] >= len(state["questions"]):
        await finish_quiz(chat_id, bot)
        return

    question = state["questions"][state["current_index"]]
    state["current_question"] = question
    state["answered"] = False

    text = format_question_text(question, state)
    keyboard = [[
        InlineKeyboardButton("А", callback_data="answer_A"),
        InlineKeyboardButton("Б", callback_data="answer_B"),
        InlineKeyboardButton("В", callback_data="answer_C")
    ]]

    msg = await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    state["last_message_id"] = msg.message_id

    await timer_manager.set_timer(f"timeout_{chat_id}", question["time_limit"], handle_timeout, chat_id, bot)

async def handle_timeout(chat_id: int, bot):
    if chat_id not in user_states or user_states[chat_id]["answered"]:
        return

    state = user_states[chat_id]
    state["answered"] = True
    question = state["current_question"]

    result_text = f"⏰ Время вышло! Правильный ответ: <b>{question['answer']}</b>"
    text = format_question_text(question, state, result=result_text)

    await bot.edit_message_text(chat_id=chat_id, message_id=state["last_message_id"], text=text, parse_mode="HTML")
    state["current_index"] += 1
    await asyncio.sleep(2)
    await ask_question(chat_id, bot)

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if chat_id not in user_states or user_states[chat_id]["answered"]:
        return

    state = user_states[chat_id]
    state["answered"] = True
    timer_manager.cancel_timer(f"timeout_{chat_id}")

    user_answer = query.data.replace("answer_", "")
    question = state["current_question"]

    is_correct = user_answer == question["answer"]
    if is_correct:
        state["correct_answers"] += 1
        user_scores.setdefault(chat_id, {"correct": 0, "total": 0, "name": query.from_user.first_name})
        user_scores[chat_id]["correct"] += 1
    user_scores.setdefault(chat_id, {"correct": 0, "total": 0, "name": query.from_user.first_name})
    user_scores[chat_id]["total"] += 1

    msg = "✅ Правильно!" if is_correct else f"❌ Неверно. Правильный ответ: {question['answer']}"
    await query.edit_message_text(msg, parse_mode="HTML")

    state["current_index"] += 1
    await asyncio.sleep(1.5)
    await ask_question(chat_id, context.bot)

async def finish_quiz(chat_id: int, bot):
    state = user_states[chat_id]
    correct = state["correct_answers"]
    total = len(state["questions"])
    percentage = (correct / total) * 100

    text = (
        f"🏁 Викторина завершена!\n\n"
        f"✅ {correct}/{total} ({percentage:.1f}%)"
    )

    await bot.send_message(chat_id, text, reply_markup=get_main_keyboard())
    del user_states[chat_id]

# ========== ЛЕКЦИИ ==========
async def show_lectures_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not lectures:
        await query.edit_message_text("❌ Лекции пока недоступны", reply_markup=get_main_keyboard())
        return
    keyboard = [[InlineKeyboardButton(f"📖 {lec['title']}", callback_data=f"lecture_{lec_id}_0")] for lec_id, lec in lectures.items()]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    await query.edit_message_text("📚 Выберите лекцию:", reply_markup=InlineKeyboardMarkup(keyboard))

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
    text = f"📚 <b>{lecture['title']}</b>\n\n<b>{section['title']}</b>\n\n{section['content']}"
    buttons = []
    if section_index > 0:
        buttons.append(InlineKeyboardButton("⬅️", callback_data=f"lecture_{lecture_id}_{section_index-1}"))
    if section_index < len(lecture["sections"]) - 1:
        buttons.append(InlineKeyboardButton("➡️", callback_data=f"lecture_{lecture_id}_{section_index+1}"))
    nav = [buttons] if buttons else []
    nav.append([InlineKeyboardButton("📚 К лекциям", callback_data="lectures")])
    nav.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(nav), parse_mode="HTML")

# ========== СТАТИСТИКА И РЕЙТИНГ ==========
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    if chat_id not in user_scores:
        await query.edit_message_text("📊 У вас пока нет статистики", reply_markup=get_main_keyboard())
        return
    score = user_scores[chat_id]
    percentage = (score["correct"] / max(score["total"], 1)) * 100
    text = f"📊 {score['name']}\n✅ {score['correct']}/{score['total']} ({percentage:.1f}%)"
    await query.edit_message_text(text, reply_markup=get_main_keyboard())

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not user_scores:
        await query.edit_message_text("🏆 Рейтинг пуст", reply_markup=get_main_keyboard())
        return
    sorted_users = sorted(user_scores.values(), key=lambda u: (u["correct"]/max(u["total"],1)), reverse=True)[:10]
    text = "🏆 Топ игроков:\n\n"
    for i, u in enumerate(sorted_users, 1):
        pct = (u["correct"]/max(u["total"],1))*100
        text += f"{i}. {u['name']} — {pct:.1f}%\n"
    await query.edit_message_text(text, reply_markup=get_main_keyboard())

# ========== ПРОЧЕЕ ==========
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🏠 Главное меню", reply_markup=get_main_keyboard())

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "❓ Помощь\n\n"
        "📚 Лекции — теория\n"
        "🖋️ Викторина — тесты\n"
        "📊 Статистика — ваши результаты\n"
        "🏆 Рейтинг — топ игроков"
    )
    await query.edit_message_text(text, reply_markup=get_main_keyboard())

# ================== HTTP-СЕРВЕР ДЛЯ FLY.IO ==================
async def handle_health(request):
    return web.Response(text="OK")

def start_health_server():
    app = web.Application()
    app.router.add_get("/health", handle_health)
    web.run_app(app, host="0.0.0.0", port=8080)

# ================== MAIN ==================
def main():
    global lectures, quiz_questions
    lectures = load_lectures_from_file("lecture.txt")
    quiz_questions = load_quiz_questions()

    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("Токен Telegram не найден")

    # Запускаем HTTP-сервер в отдельном потоке
    threading.Thread(target=start_health_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(quiz_menu, pattern="^quiz_menu$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: start_quiz(u, c, "mode_quick"), pattern="^mode_quick$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: start_quiz(u, c, "difficulty_easy"), pattern="^difficulty_easy$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: start_quiz(u, c, "difficulty_medium"), pattern="^difficulty_medium$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: start_quiz(u, c, "difficulty_hard"), pattern="^difficulty_hard$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: start_quiz(u, c, "mode_single"), pattern="^mode_single$"))
    app.add_handler(CallbackQueryHandler(check_answer, pattern="^answer_"))
    app.add_handler(CallbackQueryHandler(show_stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(show_leaderboard, pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(show_lectures_menu, pattern="^lectures$"))
    app.add_handler(CallbackQueryHandler(show_lecture, pattern=r"^lecture_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(show_help, pattern="^help$"))

    logger.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
