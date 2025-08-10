import os
import logging
import asyncio
import random
import time
import json
import math
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

# Quiz questions (сокращено для примера)
quiz_questions = [
    {
        "question": "Что является предметом экономической теории?",
        "options": ["А) Политические отношения", "Б) Законы функционирования и развития хозяйства", "В) Социальные проблемы"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Основы экономической теории"
    },
    # ... (остальные вопросы)
]

# Лекции
lectures = {
    1: {
        "id": 1,
        "title": "Лекция 1. Предмет и метод экономической теории",
        "sections": [
            {
                "title": "Введение в экономическую теорию",
                "content": (
                    "Понятие «экономика» имеет в современных условиях два основных значения. "
                    "Во-первых, экономика – это особая сфера человеческой деятельности по созданию материальных и культурных благ "
                    "для удовлетворения потребностей людей. Особенность и значимость этой сферы человеческой деятельности заключается "
                    "в том, что без удовлетворения основных материальных потребностей (пищи, одежде, жилье) немыслимы все без исключения "
                    "виды деятельности людей, существование человеческого общества в целом.\n\n"
                    "Во-вторых, экономика (экономическая теория) – это наука о законах функционирования и развития хозяйства. "
                    "Люди не только участвуют в экономической деятельности непосредственно, но и направляют свои усилия на то, "
                    "чтобы понять закономерности развития экономических процессов в обществе. Она относится к разряду социальных наук, "
                    "поскольку экономические явления осуществляются посредством социальных отношений между людьми."
                )
            },
            {
                "title": "Предмет и метод экономической науки",
                "content": (
                    "В теоретической экономике исследуются и анализируются различные стороны экономической жизни общества. "
                    "Прежде всего, это деятельность людей в сферах производства, распределения, обмена, потребления и воспроизводства "
                    "материальных благ и услуг как на национальном и международном уровнях, так и на уровне предприятий и фирм.\n\n"
                    "В производстве предмет изучения теоретической экономики – это выбор людьми способа использования ограниченных "
                    "производительных ресурсов (земли, труда, оборудования, технических знаний) для создания материальных благ и услуг."
                )
            },
            {
                "title": "Функции экономической науки",
                "content": (
                    "1. Познавательная функция: раскрывает законы и закономерности развития экономики\n"
                    "2. Методологическая функция: служит теоретическим фундаментом для других экономических наук\n"
                    "3. Практическая функция: разработка принципов рационального хозяйствования и обоснование экономической политики\n\n"
                    "Экономические знания особенно важны для сотрудников правоохранительных органов, которые фактически являются "
                    "участниками экономических отношений при обеспечении правопорядка."
                )
            },
            {
                "title": "Экономические ресурсы и выбор",
                "content": (
                    "Основное противоречие экономики: между безграничностью потребностей и ограниченностью ресурсов.\n\n"
                    "Виды экономических ресурсов:\n"
                    "- Природные (земля, полезные ископаемые)\n"
                    "- Материальные (средства производства)\n"
                    "- Трудовые (рабочая сила)\n"
                    "- Финансовые (денежные средства)\n"
                    "- Информационные (научные знания, технологии)\n\n"
                    "Кривая производственных возможностей показывает альтернативные комбинации товаров, которые могут быть произведены "
                    "при полном использовании ресурсов."
                )
            }
        ]
    },
    # ... (дополнительные лекции)
}

class TimerManager:
    """Асинхронный менеджер таймеров"""
    def __init__(self):
        self.timers = {}
    
    async def set_timer(self, key, delay, callback, *args):
        """Установить таймер"""
        # Отменить существующий таймер если есть
        self.cancel_timer(key)
        
        # Создать новую задачу
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

def format_question_text(question, state, result=None):
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
    if result is not None:
        text += f"\n{result}"
    else:
        text += f"\n⏰ У вас есть <b>{question['time_limit']}</b> секунд!"
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"🚀 Бот запущен! Привет, {user.first_name}!\n"
        "📚 Я помогу тебе изучить основы экономической теории и проверить знания",
        reply_markup=get_main_keyboard()
    )

def get_main_keyboard():
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("🖋️ Проверь себя", callback_data="quiz_menu")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton("🏆 Рейтинг", callback_data="leaderboard")],
        [InlineKeyboardButton("📚 Курс лекций", callback_data="lectures")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

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
    
    topics = sorted(set(q["topic"] for q in quiz_questions))
    
    keyboard = []
    for i, topic in enumerate(topics, 1):
        keyboard.append([InlineKeyboardButton(f"{i}. {topic}", callback_data=f"topic_{topic}")])
    
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
    config = {
        "mode_quick": {"count": 5, "difficulty_filter": ["easy", "medium", "hard"]},
        "difficulty_easy": {"count": 10, "difficulty_filter": ["easy"]},
        "difficulty_medium": {"count": 15, "difficulty_filter": ["medium"]},
        "difficulty_hard": {"count": 20, "difficulty_filter": ["hard"]},
        "mode_topics": {"count": 15, "topic": topic},
        "mode_single": {"count": 1, "difficulty_filter": ["easy", "medium", "hard"]}
    }[mode]
    
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
    text = format_question_text(question, state)
    
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
    text = format_question_text(question, state, result=result_text)
    
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
        user_scores[chat_id] = {"correct": 0, "total": 0, "name": query.from_user.first_name or "Аноним"}
    
    user_scores[chat_id]["total"] += 1
    
    # Проверка ответа
    question = state["current_question"]
    is_correct = user_answer == question["answer"]
    response_time = time.time() - state["start_time"]
    
    # Формирование сообщения
    if is_correct:
        state["correct_answers"] += 1
        user_scores[chat_id]["correct"] += 1
        message = "✅ <b>Правильно!</b> 🎉"
        time_bonus = " ⚡ Быстрый ответ!" if response_time < question["time_limit"] / 2 else ""
        message += time_bonus
    else:
        message = f"❌ <b>Неверно.</b> Правильный ответ: <b>{question['answer']}</b>"
    
    message += f"\n⏱️ Время ответа: {response_time:.1f}с"
    
    # Отправка результата
    await query.edit_message_text(
        text=message,
        parse_mode="HTML"
    )
    
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
    elif percentage >= 70:
        text += "🥇 <b>Уровень: Продвинутый</b>"
    elif percentage >= 50:
        text += "🥈 <b>Уровень: Средний</b>"
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
        await query.edit_message_text("📊 У вас пока нет статистики")
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
    
    # Оценка уровня
    if percentage >= 90:
        text += "🏆 <b>Уровень: Эксперт по экономике!</b>"
    elif percentage >= 70:
        text += "🥇 <b>Уровень: Продвинутый</b>"
    elif percentage >= 50:
        text += "🥈 <b>Уровень: Средний</b>"
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
        await query.edit_message_text("🏆 Рейтинг пока пуст")
        return
    
    # Сортировка пользователей
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
    
    await query.edit_message_text(
        text=text,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

async def show_lectures_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню лекций"""
    query = update.callback_query
    await query.answer()
    
    text = "📚 <b>Курс лекций по экономической теории</b>\n\nВыберите лекцию:\n"
    keyboard = []
    
    for lecture_id, lecture in lectures.items():
        keyboard.append([InlineKeyboardButton(
            f"📖 {lecture['title']}", 
            callback_data=f"lecture_{lecture_id}_0"
        )])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def show_lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать раздел лекции"""
    query = update.callback_query
    await query.answer()
    
    # Парсим данные из callback_data: lecture_<id>_<section_index>
    _, lecture_id, section_index = query.data.split("_")
    lecture_id = int(lecture_id)
    section_index = int(section_index)
    
    lecture = lectures.get(lecture_id)
    if not lecture or section_index >= len(lecture["sections"]):
        await query.edit_message_text("❌ Лекция не найдена")
        return
    
    section = lecture["sections"][section_index]
    
    # Формируем текст лекции
    text = (
        f"📚 <b>{lecture['title']}</b>\n\n"
        f"🔹 <b>{section['title']}</b>\n\n"
        f"{section['content']}\n\n"
        f"📄 Раздел {section_index + 1}/{len(lecture['sections'])}"
    )
    
    # Формируем клавиатуру навигации
    keyboard = []
    
    # Кнопки навигации
    if section_index > 0:
        keyboard.append(InlineKeyboardButton("⬅️ Предыдущий", callback_data=f"lecture_{lecture_id}_{section_index - 1}"))
    if section_index < len(lecture["sections"]) - 1:
        keyboard.append(InlineKeyboardButton("Следующий ➡️", callback_data=f"lecture_{lecture_id}_{section_index + 1}"))
    
    # Добавляем кнопки только если есть что размещать в ряду
    if keyboard:
        keyboard = [keyboard]  # делаем список списков
    
    keyboard.append([InlineKeyboardButton("📚 К списку лекций", callback_data="lectures")])
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")])
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "❓ <b>Помощь по использованию бота</b>\n\n"
        "Этот бот поможет вам изучить основы экономической теории и проверить свои знания.\n\n"
        "Основные функции:\n"
        "🖋️ <b>Проверь себя</b> - тестирование по различным темам экономики\n"
        "📊 <b>Моя статистика</b> - просмотр ваших результатов тестирования\n"
        "🏆 <b>Рейтинг</b> - таблица лидеров среди всех пользователей\n"
        "📚 <b>Курс лекций</b> - учебные материалы по экономической теории\n\n"
        "Для начала работы используйте команду /start или кнопки меню."
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
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(quiz_menu, pattern="^quiz_menu$"))
    app.add_handler(CallbackQueryHandler(show_topic_selection, pattern="^mode_topics$"))
    app.add_handler(CallbackQueryHandler(show_stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(show_leaderboard, pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(show_lectures_menu, pattern="^lectures$"))
    app.add_handler(CallbackQueryHandler(show_lecture, pattern=r"^lecture_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(show_help, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    app.add_handler(CallbackQueryHandler(back_to_quiz_menu, pattern="^back_to_quiz_menu$"))
    
    # Обработчики выбора режима
    quiz_modes = [
        "mode_quick", "difficulty_easy", "difficulty_medium", 
        "difficulty_hard", "mode_single"
    ]
    for mode in quiz_modes:
        app.add_handler(CallbackQueryHandler(
            lambda update, ctx, m=mode: start_quiz(update, ctx, m), 
            pattern=f"^{mode}$"
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