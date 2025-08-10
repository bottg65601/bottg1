import os
import logging
import asyncio
import random
import time
import json
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

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# State management
user_states = {}
user_scores = {}

# Quiz questions based on economic theory lectures - organized by topics
quiz_questions = [
    # Лекция 1: Предмет и метод экономической теории
    {
        "question": "Что является предметом экономической теории?",
        "options": ["А) Политические отношения", "Б) Законы функционирования и развития хозяйства", "В) Социальные проблемы"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Основы экономической теории"
    },
    {
        "question": "Какие функции выполняет экономическая наука?",
        "options": ["А) Только познавательную", "Б) Политическую и социальную", "В) Познавательную, методологическую, практическую"],
        "answer": "В",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Основы экономической теории"
    },
    # ... (все остальные вопросы из вашего оригинального кода)
]

# Dictionary of economic terms
economics_dictionary = {
    "Экономика": "Сфера человеческой деятельности по созданию материальных и культурных благ для удовлетворения потребностей людей",
    "Экономические ресурсы": "Ограниченные относительно потребности в них ресурсы (земля, труд, капитал)",
    # ... (все остальные термины из вашего оригинального кода)
}

# Economic formulas
economic_formulas = {
    "Темп инфляции": "((ИПЦ_текущий - ИПЦ_базовый) / ИПЦ_базовый) × 100%",
    "Реальный ВВП": "Номинальный ВВП / Дефлятор ВВП × 100",
    # ... (все остальные формулы из вашего оригинального кода)
}

# Useful links
useful_links = {
    "📈 Центральный банк РФ": "https://cbr.ru - Официальный сайт ЦБ РФ",
    "📊 Росстат": "https://rosstat.gov.ru - Федеральная служба государственной статистики",
    # ... (все остальные ссылки из вашего оригинального кода)
}

# News sources
news_sources = {
    "📰 РБК Экономика": "https://rbc.ru/economics - Экономические новости",
    "💼 Ведомости": "https://vedomosti.ru - Деловые новости",
    # ... (все остальные новостные источники из вашего оригинального кода)
}

# Presentation topics
presentation_topics = [
    "📊 Методы экономических исследований и их применение",
    "🔄 Экономические аспекты деятельности правоохранительных органов",
    # ... (все остальные темы докладов из вашего оригинального кода)
]

class TimerManager:
    """Асинхронный менеджер таймеров"""
    def __init__(self):
        self.timers = {}
    
    async def set_timer(self, key, delay, callback, *args):
        """Установить таймер"""
        self.cancel_timer(key)
        task = asyncio.create_task(self._timer_task(key, delay, callback, args))
        self.timers[key] = task
    
    def cancel_timer(self, key):
        """Отменить таймер"""
        if key in self.timers:
            self.timers[key].cancel()
            del self.timers[key]
    
    async def _timer_task(self, key, delay, callback, args):
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

# Глобальный менеджер таймеров
timer_manager = TimerManager()

def get_main_keyboard():
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("🖋️ Проверь себя", callback_data="quiz_menu")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton("🏆 Рейтинг", callback_data="leaderboard")],
        [InlineKeyboardButton("📚 Словарь терминов", callback_data="dictionary")],
        [InlineKeyboardButton("📈 Полезные ссылки", callback_data="useful_links")],
        [InlineKeyboardButton("📒 Курс лекций", callback_data="lectures")],
        [InlineKeyboardButton("📽️ Темы докладов", callback_data="presentation_topics")],
        [InlineKeyboardButton("📐 Формулы", callback_data="formulas")],
        [InlineKeyboardButton("🧮 Калькулятор", callback_data="calculator")],
        [InlineKeyboardButton("📰 Новости", callback_data="news")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}! Добро пожаловать в экономическую викторину!\n\n"
        "🧠 Проверьте свои знания в области экономики\n"
        "📊 Отслеживайте свою статистику и прогресс\n"
        "🏆 Соревнуйтесь с другими участниками\n"
        "🎯 Выбирайте подходящий уровень сложности или изучайте по темам\n"
        "🎮 Играйте в быстрые игры или проходите полные сессии\n"
        "⏰ Отвечайте быстро - время ограничено!\n\n"
        "Бот основан на полном курсе лекций по экономической теории!\n\n"
        "Используйте кнопки ниже для навигации по функциям бота!",
        reply_markup=get_main_keyboard()
    )

async def quiz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню выбора режима викторины"""
    query = update.callback_query
    await query.answer()
    
    text = "🖋️ <b>Проверь себя</b> - выберите режим викторины:\n\n"
    keyboard = [
        [InlineKeyboardButton("🎮 Быстрая игра (5 вопросов)", callback_data="mode_quick")],
        [InlineKeyboardButton("🟢 Легкий (10 вопросов)", callback_data="difficulty_easy")],
        [InlineKeyboardButton("🟡 Средний (15 вопросов)", callback_data="difficulty_medium")],
        [InlineKeyboardButton("🔴 Сложный (20 вопросов)", callback_data="difficulty_hard")],
        [InlineKeyboardButton("🏆 Эксперт (все вопросы)", callback_data="difficulty_expert")],
        [InlineKeyboardButton("📚 По темам", callback_data="mode_topics")],
        [InlineKeyboardButton("🔀 Случайный вопрос", callback_data="mode_single")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def show_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор темы для викторины"""
    query = update.callback_query
    await query.answer()
    
    topics = [
        "Основы экономической теории",
        "Экономические системы", 
        "Рынок и рыночный механизм",
        "Конкуренция и рыночные структуры",
        "Предприятие и производство",
        "Рынки факторов производства",
        "Макроэкономика",
        "Экономический рост и циклы",
        "Макроэкономические проблемы",
        "Государственное регулирование",
        "Денежно-кредитная система",
        "Мировая экономика"
    ]
    
    keyboard = []
    for i, topic in enumerate(topics, 1):
        keyboard.append([InlineKeyboardButton(f"{i}. {topic}", callback_data=f"topic_{i-1}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_quiz_menu")])
    
    await query.edit_message_text(
        text="📚 <b>Выберите тему для изучения:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str, difficulty: str = None, topic: str = None):
    """Запуск викторины"""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    # Определение параметров викторины
    if mode == "mode_quick":
        config = {"count": 5, "difficulty_filter": ["easy", "medium", "hard"]}
    elif mode == "difficulty_easy":
        config = {"count": 10, "difficulty_filter": ["easy"]}
    elif mode == "difficulty_medium":
        config = {"count": 15, "difficulty_filter": ["medium"]}
    elif mode == "difficulty_hard":
        config = {"count": 20, "difficulty_filter": ["hard"]}
    elif mode == "difficulty_expert":
        config = {"count": len(quiz_questions), "difficulty_filter": ["easy", "medium", "hard"]}
    elif mode == "mode_topics":
        topics = [
            "Основы экономической теории",
            "Экономические системы",
            # ... (все темы)
        ]
        selected_topic = topics[int(topic)]
        config = {"count": len([q for q in quiz_questions if q["topic"] == selected_topic]), "topic": selected_topic}
    elif mode == "mode_single":
        config = {"count": 1, "difficulty_filter": ["easy", "medium", "hard"]}
    
    # Фильтрация вопросов
    if "topic" in config:
        questions = [q for q in quiz_questions if q["topic"] == config["topic"]]
    else:
        questions = [q for q in quiz_questions if q["difficulty"] in config["difficulty_filter"]]
    
    if not questions:
        await query.edit_message_text("❌ Вопросы по выбранной теме не найдены")
        return
    
    # Сохранение состояния пользователя
    user_states[chat_id] = {
        "mode": "quiz_session",
        "questions": random.sample(questions, min(len(questions), config["count"])),
        "current_index": 0,
        "correct_answers": 0,
        "start_time": time.time(),
        "answered": False
    }
    
    # Запуск первого вопроса
    await ask_question(chat_id, context.bot)

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
    
    # Формирование сообщения
    difficulty_emoji = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}
    emoji = difficulty_emoji.get(question['difficulty'], '⚪')
    
    text = (
        f"🎯 Вопрос {state['current_index'] + 1}/{len(state['questions'])} {emoji}\n"
        f"📚 Тема: {question['topic']}\n\n"
        f"🧠 <b>{question['question']}</b>\n\n"
    )
    for option in question["options"]:
        text += f"{option}\n"
    text += f"\n⏰ У вас есть <b>{question['time_limit']}</b> секунд!"
    
    keyboard = [[
        InlineKeyboardButton("А", callback_data="answer_A"),
        InlineKeyboardButton("Б", callback_data="answer_B"),
        InlineKeyboardButton("В", callback_data="answer_C")
    ]]
    
    # Отправка вопроса
    message = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    state["last_message_id"] = message.message_id
    
    # Установка таймера
    await timer_manager.set_timer(
        f"timeout_{chat_id}",
        question["time_limit"],
        handle_timeout,
        chat_id,
        bot
    )

async def handle_timeout(chat_id: int, bot):
    """Обработка таймаута ответа"""
    if chat_id not in user_states or user_states[chat_id].get("answered"):
        return
    
    state = user_states[chat_id]
    state["answered"] = True
    question = state["current_question"]
    
    # Обновление статистики
    if chat_id not in user_scores:
        user_scores[chat_id] = {"correct": 0, "total": 0, "name": "Аноним"}
    
    user_scores[chat_id]["total"] += 1
    
    # Формирование сообщения о таймауте
    result_text = f"⏰ Время вышло! Правильный ответ: <b>{question['answer']}</b>"
    
    difficulty_emoji = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}
    emoji = difficulty_emoji.get(question['difficulty'], '⚪')
    
    text = (
        f"🎯 Вопрос {state['current_index'] + 1}/{len(state['questions'])} {emoji}\n"
        f"📚 Тема: {question['topic']}\n\n"
        f"🧠 <b>{question['question']}</b>\n\n"
    )
    for option in question["options"]:
        text += f"{option}\n"
    text += f"\n{result_text}"
    
    # Редактирование исходного сообщения
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=state["last_message_id"],
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка редактирования сообщения: {e}")
    
    # Переход к следующему вопросу
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
    
    # Отмена таймера
    timer_manager.cancel_timer(f"timeout_{chat_id}")
    
    # Инициализация статистики
    if chat_id not in user_scores:
        user_scores[chat_id] = {
            "correct": 0, 
            "total": 0, 
            "name": query.from_user.first_name or "Аноним"
        }
    
    user_scores[chat_id]["total"] += 1
    
    # Проверка ответа
    question = state["current_question"]
    is_correct = user_answer == question["answer"]
    response_time = time.time() - state["start_time"]
    
    # Формирование сообщения
    difficulty_emoji = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}
    emoji = difficulty_emoji.get(question['difficulty'], '⚪')
    
    if is_correct:
        state["correct_answers"] += 1
        user_scores[chat_id]["correct"] += 1
        message = "✅ <b>Правильно!</b> 🎉"
        if response_time <= question["time_limit"] * 0.5:
            message += " ⚡ Быстрый ответ!"
        elif response_time <= question["time_limit"] * 0.75:
            message += " 👍 Хорошая скорость!"
    else:
        message = f"❌ <b>Неверно.</b> Правильный ответ: <b>{question['answer']}</b>"
    
    message += f"\n⏱️ Время ответа: {response_time:.1f}с из {question['time_limit']}с"
    
    text = (
        f"🎯 Вопрос {state['current_index'] + 1}/{len(state['questions'])} {emoji}\n"
        f"📚 Тема: {question['topic']}\n\n"
        f"🧠 <b>{question['question']}</b>\n\n"
    )
    for option in question["options"]:
        text += f"{option}\n"
    text += f"\n{message}"
    
    # Отправка результата
    try:
        await query.edit_message_text(
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка редактирования сообщения: {e}")
    
    # Переход к следующему вопросу
    state["current_index"] += 1
    await asyncio.sleep(1.5)
    await ask_question(chat_id, context.bot)

async def finish_quiz(chat_id: int, bot):
    """Завершение викторины и вывод результатов"""
    if chat_id not in user_states:
        return
    
    # Отмена активного таймера
    timer_manager.cancel_timer(f"timeout_{chat_id}")
    
    state = user_states[chat_id]
    score = user_scores.get(chat_id, {"correct": 0, "total": 0})
    
    # Расчет результатов
    correct = state["correct_answers"]
    total = len(state["questions"])
    percentage = (correct / total) * 100 if total > 0 else 0
    
    # Формирование сообщения
    text = (
        f"🏁 <b>Викторина завершена!</b>\n\n"
        f"📊 Результаты:\n"
        f"✅ Правильных ответов: {correct}/{total}\n"
        f"📈 Процент: {percentage:.1f}%\n\n"
    )
    
    # Определение уровня
    if percentage >= 90:
        text += "🏆 <b>Уровень: Эксперт по экономике!</b>"
    elif percentage >= 80:
        text += "🥇 <b>Уровень: Продвинутый</b>"
    elif percentage >= 60:
        text += "🥈 <b>Уровень: Хороший</b>"
    elif percentage >= 40:
        text += "🥉 <b>Уровень: Базовый</b>"
    else:
        text += "📚 <b>Уровень: Начинающий</b>"
    
    # Отправка результатов
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )
    
    # Очистка состояния
    del user_states[chat_id]

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пользователя"""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    if chat_id not in user_scores:
        await query.edit_message_text(
            "📊 У вас пока нет статистики. Начните викторину!",
            reply_markup=get_main_keyboard()
        )
        return
    
    score = user_scores[chat_id]
    total = max(score["total"], 1)
    percentage = (score["correct"] / total) * 100
    
    text = (
        f"📊 <b>Ваша статистика:</b>\n\n"
        f"👤 Имя: {score.get('name', 'Аноним')}\n"
        f"✅ Правильных ответов: {score['correct']}\n"
        f"❌ Неправильных ответов: {score['total'] - score['correct']}\n"
        f"📝 Всего вопросов: {score['total']}\n"
        f"📈 Процент правильных: {percentage:.1f}%\n\n"
    )
    
    # Оценка уровня
    if percentage >= 90:
        text += "🏆 <b>Уровень: Эксперт по экономике!</b>"
    elif percentage >= 75:
        text += "🥇 <b>Уровень: Продвинутый</b>"
    elif percentage >= 60:
        text += "🥈 <b>Уровень: Хороший</b>"
    elif percentage >= 40:
        text += "🥉 <b>Уровень: Базовый</b>"
    else:
        text += "📚 <b>Уровень: Начинающий</b>"
    
    await query.edit_message_text(
        text=text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать таблицу лидеров"""
    query = update.callback_query
    await query.answer()
    
    if not user_scores:
        await query.edit_message_text(
            "🏆 Рейтинг пуст. Начните викторину, чтобы попасть в топ!",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Сортировка пользователей
    sorted_users = sorted(
        user_scores.items(),
        key=lambda x: (x[1]["correct"] / max(x[1]["total"], 1), x[1]["correct"]),
        reverse=True
    )[:10]
    
    text = "🏆 <b>Топ-10 участников:</b>\n\n"
    for i, (user_id, user) in enumerate(sorted_users, 1):
        percentage = (user["correct"] / max(user["total"], 1)) * 100
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} {user.get('name', 'Аноним')} - {percentage:.1f}% ({user['correct']}/{user['total']})\n"
    
    await query.edit_message_text(
        text=text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

async def show_dictionary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать словарь терминов"""
    query = update.callback_query
    await query.answer()
    
    text = "📚 <b>Словарь экономических терминов:</b>\n\n"
    for term, definition in economics_dictionary.items():
        text += f"📌 <b>{term}</b>\n{definition}\n\n"
    
    await query.edit_message_text(
        text=text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

async def show_useful_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать полезные ссылки"""
    query = update.callback_query
    await query.answer()
    
    text = "📈 <b>Полезные ресурсы по экономике:</b>\n\n"
    for name, link in useful_links.items():
        text += f"{name}\n{link}\n\n"
    
    await query.edit_message_text(
        text=text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

async def show_formulas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать экономические формулы"""
    query = update.callback_query
    await query.answer()
    
    text = "📐 <b>Основные экономические формулы:</b>\n\n"
    for formula_name, formula in economic_formulas.items():
        text += f"🔹 <b>{formula_name}</b>\n<code>{formula}</code>\n\n"
    
    await query.edit_message_text(
        text=text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

async def show_presentation_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать темы для докладов"""
    query = update.callback_query
    await query.answer()
    
    text = "📝 <b>Темы для докладов по экономической теории:</b>\n\n"
    for i, topic in enumerate(presentation_topics, 1):
        text += f"{i}. {topic}\n"
    
    await query.edit_message_text(
        text=text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

async def show_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать новостные источники"""
    query = update.callback_query
    await query.answer()
    
    text = "📰 <b>Источники экономических новостей:</b>\n\n"
    text += "🔸 <b>Российские источники:</b>\n"
    for name, link in list(news_sources.items())[:4]:
        text += f"• {name}\n{link}\n"
    
    text += "\n🔸 <b>Международные источники:</b>\n"
    for name, link in list(news_sources.items())[4:]:
        text += f"• {name}\n{link}\n"
    
    await query.edit_message_text(
        text=text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "❓ <b>Помощь по боту:</b>\n\n"
        "<b>Доступные функции:</b>\n\n"
        "🖋️ <b>Проверь себя</b> - экономическая викторина с разными режимами:\n"
        "  • Быстрая игра (5 вопросов)\n"
        "  • По уровням сложности (10-20 вопросов)\n"
        "  • По темам лекций\n"
        "  • Случайные вопросы\n\n"
        "📊 <b>Моя статистика</b> - ваши результаты и уровень\n"
        "🏆 <b>Рейтинг</b> - топ участников\n"
        "📚 <b>Словарь терминов</b> - основные экономические понятия\n"
        "📈 <b>Полезные ссылки</b> - важные ресурсы по экономике\n"
        "📒 <b>Курс лекций</b> - структурированные учебные материалы\n"
        "📽️ <b>Темы докладов</b> - идеи для исследовательских работ\n"
        "📐 <b>Формулы</b> - основные экономические формулы\n"
        "🧮 <b>Калькулятор</b> - экономические вычисления\n"
        "📰 <b>Новости</b> - источники экономических новостей\n\n"
        "<b>Команды:</b>\n"
        "/start - начать работу с ботом\n"
        "/help - показать эту помощь\n"
        "/quiz - начать викторину"
    )
    
    await query.edit_message_text(
        text=text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="🏠 Главное меню",
        reply_markup=get_main_keyboard()
    )

async def back_to_quiz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в меню викторины"""
    query = update.callback_query
    await query.answer()
    await quiz_menu(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего действия"""
    chat_id = update.effective_chat.id
    # Отмена таймера
    timer_manager.cancel_timer(f"timeout_{chat_id}")
    if chat_id in user_states:
        del user_states[chat_id]
    await update.message.reply_text(
        "❌ Действие отменено",
        reply_markup=get_main_keyboard()
    )

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("Токен не установлен!")
    
    app = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CommandHandler("quiz", quiz_menu))
    
    # Регистрация обработчиков callback-запросов
    app.add_handler(CallbackQueryHandler(quiz_menu, pattern="^quiz_menu$"))
    app.add_handler(CallbackQueryHandler(show_topic_selection, pattern="^mode_topics$"))
    app.add_handler(CallbackQueryHandler(show_stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(show_leaderboard, pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(show_dictionary, pattern="^dictionary$"))
    app.add_handler(CallbackQueryHandler(show_useful_links, pattern="^useful_links$"))
    app.add_handler(CallbackQueryHandler(show_formulas, pattern="^formulas$"))
    app.add_handler(CallbackQueryHandler(show_presentation_topics, pattern="^presentation_topics$"))
    app.add_handler(CallbackQueryHandler(show_news, pattern="^news$"))
    app.add_handler(CallbackQueryHandler(show_help, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(back_to_quiz_menu, pattern="^back_to_quiz_menu$"))
    
    # Обработчики выбора режима викторины
    quiz_modes = [
        "mode_quick", "difficulty_easy", "difficulty_medium", 
        "difficulty_hard", "difficulty_expert", "mode_single"
    ]
    for mode in quiz_modes:
        app.add_handler(CallbackQueryHandler(
            lambda update, ctx, m=mode: start_quiz(update, ctx, m), 
            pattern=f"^{m}$"
        ))
    
    # Обработчики выбора темы
    app.add_handler(CallbackQueryHandler(
        lambda update, ctx: start_quiz(
            update, 
            ctx, 
            "mode_topics", 
            topic=update.callback_query.data.replace("topic_", "")
        ),
        pattern="^topic_"
    ))
    
    # Обработчик ответов
    app.add_handler(CallbackQueryHandler(
        check_answer, 
        pattern="^answer_"
    ))
    
    # Запуск бота
    logger.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()