import os
import logging
import asyncio
import random
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    Filters
)

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Quiz modes
class QuizMode(Enum):
    QUICK = "mode_quick"
    EASY = "difficulty_easy"
    MEDIUM = "difficulty_medium"
    HARD = "difficulty_hard"
    TOPICS = "mode_topics"
    SINGLE = "mode_single"

# State management
user_states: Dict[int, Dict] = {}
user_scores: Dict[int, Dict] = {}

# Quiz questions (example)
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

class TimerManager:
    """Асинхронный менеджер таймеров"""
    def __init__(self):
        self.timers: Dict[str, asyncio.Task] = {}

    async def set_timer(self, key: str, delay: float, callback, *args):
        """Установить таймер"""
        self.cancel_timer(key)
        task = asyncio.create_task(self._timer_task(key, delay, callback, args))
        self.timers[key] = task

    def cancel_timer(self, key: str):
        """Отменить таймер"""
        if key in self.timers:
            self.timers[key].cancel()
            del self.timers[key]

    async def _timer_task(self, key: str, delay: float, callback, args):
        """Асинхронная задача таймера"""
        try:
            await asyncio.sleep(delay)
            await callback(*args)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Timer error: {e}")
        finally:
            self.cancel_timer(key)

timer_manager = TimerManager()

def format_question_text(question: Dict, state: Dict, result: Optional[str] = None) -> str:
    """Форматирует текст вопроса с результатом или без"""
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    try:
        await update.message.reply_text(
            f"🚀 Бот запущен! Привет, {user.first_name}!",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("❌ Произошла ошибка, попробуйте позже.")

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("🖋️ Проверь себя", callback_data="quiz_menu")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton("🏆 Рейтинг", callback_data="leaderboard")],
        [InlineKeyboardButton("📚 Словарь терминов", callback_data="dictionary")],
        [InlineKeyboardButton("📒 Курс лекций", callback_data="course")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def quiz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню выбора режима викторины"""
    query = update.callback_query
    await query.answer()
    text = "🖋️ <b>Проверь себя</b> - выберите режим викторины:\n\n"
    keyboard = [
        [InlineKeyboardButton("🎮 Быстрая игра (5 вопросов)", callback_data=QuizMode.QUICK.value)],
        [InlineKeyboardButton("🟢 Легкий (10 вопросов)", callback_data=QuizMode.EASY.value)],
        [InlineKeyboardButton("🟡 Средний (15 вопросов)", callback_data=QuizMode.MEDIUM.value)],
        [InlineKeyboardButton("🔴 Сложный (20 вопросов)", callback_data=QuizMode.HARD.value)],
        [InlineKeyboardButton("📚 По темам", callback_data=QuizMode.TOPICS.value)],
        [InlineKeyboardButton("🔀 Случайный вопрос", callback_data=QuizMode.SINGLE.value)],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in quiz_menu: {e}")
        await query.message.reply_text("❌ Произошла ошибка, попробуйте позже.")

async def show_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор темы для викторины"""
    query = update.callback_query
    await query.answer()
    topics = sorted(set(q["topic"] for q in quiz_questions))
    keyboard = [[InlineKeyboardButton(f"{i}. {topic}", callback_data=f"topic_{topic}")] for i, topic in enumerate(topics, 1)]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_quiz_menu")])
    try:
        await query.edit_message_text(
            text="📚 <b>Выберите тему для изучения:</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in show_topic_selection: {e}")
        await query.message.reply_text("❌ Произошла ошибка, попробуйте позже.")

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str, topic: Optional[str] = None):
    """Запуск викторины"""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    config = {
        QuizMode.QUICK.value: {"count": 5, "difficulty_filter": ["easy", "medium", "hard"]},
        QuizMode.EASY.value: {"count": 10, "difficulty_filter": ["easy"]},
        QuizMode.MEDIUM.value: {"count": 15, "difficulty_filter": ["medium"]},
        QuizMode.HARD.value: {"count": 20, "difficulty_filter": ["hard"]},
        QuizMode.TOPICS.value: {"count": 15, "topic": topic},
        QuizMode.SINGLE.value: {"count": 1, "difficulty_filter": ["easy", "medium", "hard"]}
    }[mode]
    
    questions = (
        [q for q in quiz_questions if q["topic"] == config["topic"]]
        if "topic" in config
        else [q for q in quiz_questions if q["difficulty"] in config["difficulty_filter"]]
    )
    
    if not questions:
        try:
            await query.edit_message_text("❌ Вопросы по выбранной теме не найдены", parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error in start_quiz: {e}")
        return
    
    user_states[chat_id] = {
        "mode": "quiz_session",
        "questions": random.sample(questions, min(len(questions), config["count"])),
        "current_index": 0,
        "correct_answers": 0,
        "start_time": time.time(),
        "answered": False
    }
    
    try:
        await ask_question(chat_id, context.bot)
    except Exception as e:
        logger.error(f"Error starting quiz: {e}")
        await query.message.reply_text("❌ Произошла ошибка при запуске викторины.")

async def ask_question(chat_id: int, bot):
    """Задать вопрос пользователю"""
    if chat_id not in user_states:
        return
    
    state = user_states[chat_id]
    if state["current_index"] >= len(state["questions"]):
        await finish_quiz(chat_id, bot)
        return
    
    question = state["questions"][state["current_index"]]
    state["current_question"] = question
    state["start_time"] = time.time()
    state["answered"] = False
    
    text = format_question_text(question, state)
    # Dynamic button generation
    keyboard = [[InlineKeyboardButton(opt[:1], callback_data=f"answer_{opt[:1]}") for opt in question["options"]]]
    
    try:
        message = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        state["last_message_id"] = message.message_id
        await timer_manager.set_timer(
            f"timeout_{chat_id}",
            question["time_limit"],
            handle_timeout,
            chat_id,
            bot
        )
    except Exception as e:
        logger.error(f"Error in ask_question: {e}")
        await bot.send_message(chat_id, "❌ Произошла ошибка при отправке вопроса.")

async def handle_timeout(chat_id: int, bot):
    """Обработка таймаута ответа"""
    if chat_id not in user_states or user_states[chat_id].get("answered"):
        return
    
    state = user_states[chat_id]
    state["answered"] = True
    question = state["current_question"]
    
    user_scores.setdefault(chat_id, {"correct": 0, "total": 0, "name": "Аноним"})["total"] += 1
    result_text = f"⏰ Время вышло! Правильный ответ: <b>{question['answer']}</b>"
    text = format_question_text(question, state, result=result_text)
    
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=state["last_message_id"],
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in handle_timeout: {e}")
    
    state["current_index"] += 1
    await asyncio.sleep(2)
    await ask_question(chat_id, bot)

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка ответа пользователя"""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    if chat_id not in user_states or user_states[chat_id].get("answered"):
        return
    
    state = user_states[chat_id]
    state["answered"] = True
    user_answer = query.data.replace("answer_", "")
    timer_manager.cancel_timer(f"timeout_{chat_id}")
    
    user_scores.setdefault(chat_id, {
        "correct": 0,
        "total": 0,
        "name": query.from_user.first_name or "Аноним"
    })["total"] += 1
    
    question = state["current_question"]
    is_correct = user_answer == question["answer"]
    response_time = time.time() - state["start_time"]
    
    if is_correct:
        state["correct_answers"] += 1
        user_scores[chat_id]["correct"] += 1
        message = "✅ <b>Правильно!</b> 🎉"
        if response_time < question["time_limit"] / 2:
            message += " ⚡ Быстрый ответ!"
    else:
        message = f"❌ <b>Неверно.</b> Правильный ответ: <b>{question['answer']}</b>"
    
    message += f"\n⏱️ Время ответа: {response_time:.1f}с"
    
    try:
        await query.edit_message_text(text=message, parse_mode="HTML")
        state["current_index"] += 1
        await asyncio.sleep(1.5)
        await ask_question(chat_id, context.bot)
    except Exception as e:
        logger.error(f"Error in check_answer: {e}")
        await query.message.reply_text("❌ Произошла ошибка при обработке ответа.")

async def finish_quiz(chat_id: int, bot):
    """Завершение викторины и вывод результатов"""
    if chat_id not in user_states:
        return
    
    state = user_states[chat_id]
    score = user_scores.get(chat_id, {"correct": 0, "total": 0})
    correct = state["correct_answers"]
    total = len(state["questions"])
    percentage = (correct / total) * 100 if total > 0 else 0
    
    text = (
        f"🏁 <b>Викторина завершена!</b>\n\n"
        f"📊 Результаты:\n"
        f"✅ Правильных ответов: {correct}/{total}\n"
        f"📈 Процент: {percentage:.1f}%\n\n"
    )
    
    if percentage >= 90:
        text += "🏆 <b>Уровень: Эксперт по экономике!</b>"
    elif percentage >= 70:
        text += "🥇 <b>Уровень: Продвинутый</b>"
    elif percentage >= 50:
        text += "🥈 <b>Уровень: Средний</b>"
    else:
        text += "📚 <b>Уровень: Начинающий</b>"
    
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in finish_quiz: {e}")
    
    del user_states[chat_id]

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пользователя"""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    if chat_id not in user_scores:
        await query.edit_message_text("📊 У вас пока нет статистики", parse_mode="HTML")
        return
    
    score = user_scores[chat_id]
    total = max(score["total"], 1)
    percentage = (score["correct"] / total) * 100
    text = (
        f"📊 <b>Статистика пользователя:</b>\n\n"
        f"👤 Имя: {score.get('name', 'Аноним')}\n"
        f"✅ Правильных ответов: {score['correct']}\n"
        f"📝 Всего вопросов: {score['total']}\n"
        f"📈 Процент правильных: {percentage:.1f}%\n\n"
    )
    
    if percentage >= 90:
        text += "🏆 <b>Уровень: Эксперт по экономике!</b>"
    elif percentage >= 70:
        text += "🥇 <b>Уровень: Продвинутый</b>"
    elif percentage >= 50:
        text += "🥈 <b>Уровень: Средний</b>"
    else:
        text += "📚 <b>Уровень: Начинающий</b>"
    
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in show_stats: {e}")

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать таблицу лидеров"""
    query = update.callback_query
    await query.answer()
    
    if not user_scores:
        await query.edit_message_text("🏆 Рейтинг пока пуст", parse_mode="HTML")
        return
    
    sorted_users = sorted(
        user_scores.values(),
        key=lambda x: (x["correct"] / max(x["total"], 1), x["correct"]),
        reverse=True
    )[:10]
    
    text = "🏆 <b>Топ-10 игроков:</b>\n\n"
    for i, user in enumerate(sorted_users, 1):
        percentage = (user["correct"] / max(user["total"], 1)) * 100
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} {user.get('name', 'Аноним')} - {percentage:.1f}%\n"
    
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in show_leaderboard: {e}")

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            text="🏠 Главное меню",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in back_to_main: {e}")

async def back_to_quiz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в меню викторины"""
    query = update.callback_query
    await query.answer()
    await quiz_menu(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего действия"""
    chat_id = update.effective_chat.id
    timer_manager.cancel_timer(f"timeout_{chat_id}")
    if chat_id in user_states:
        del user_states[chat_id]
    try:
        await update.message.reply_text(
            "❌ Действие отменено",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in cancel: {e}")

async def dictionary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for dictionary functionality"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="📚 Словарь терминов находится в разработке.",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

async def course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for course functionality"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="📒 Курс лекций находится в разработке.",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for help functionality"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="❓ Помощь: Используйте /start для начала, /cancel для отмены текущего действия.",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("Токен не установлен!")
    
    app = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(quiz_menu, pattern="^quiz_menu$"))
    app.add_handler(CallbackQueryHandler(show_topic_selection, pattern=f"^{QuizMode.TOPICS.value}$"))
    app.add_handler(CallbackQueryHandler(show_stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(show_leaderboard, pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(back_to_quiz_menu, pattern="^back_to_quiz_menu$"))
    app.add_handler(CallbackQueryHandler(dictionary, pattern="^dictionary$"))
    app.add_handler(CallbackQueryHandler(course, pattern="^course$"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))
    
    # Обработчики выбора режима
    for mode in QuizMode:
        app.add_handler(CallbackQueryHandler(
            lambda update, ctx, m=mode.value: start_quiz(update, ctx, m),
            pattern=f"^{mode.value}$"
        ))
    
    # Обработчик выбора темы
    app.add_handler(CallbackQueryHandler(
        lambda update, ctx: start_quiz(
            update,
            ctx,
            QuizMode.TOPICS.value,
            topic=update.callback_query.data.replace("topic_", "")
        ),
        pattern="^topic_"
    ))
    
    # Обработчик ответов
    app.add_handler(CallbackQueryHandler(check_answer, pattern="^answer_"))
    
    logger.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()