import os
import asyncio
import logging
from dotenv import load_dotenv
import random
import sys
import time
import threading

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# State management
user_states = {}
user_scores = {}

# Quiz questions based on economic theory lectures
quiz_questions = [
    {
        "question": "Что является предметом экономической теории?",
        "options": ["А) Законы функционирования и развития хозяйства", "Б) Политические отношения", "В) Социальные проблемы"],
        "answer": "А",
        "difficulty": "easy",
        "time_limit": 10
    },
    {
        "question": "Какой метод используется для познания экономических явлений?",
        "options": ["А) Метод научной абстракции", "Б) Только наблюдение", "В) Интуитивный метод"],
        "answer": "А",
        "difficulty": "medium",
        "time_limit": 20
    },
    {
        "question": "Что характеризует основное противоречие экономического развития?",
        "options": ["А) Ограниченные ресурсы и безграничные потребности", "Б) Избыток товаров", "В) Недостаток денег"],
        "answer": "А",
        "difficulty": "hard",
        "time_limit": 30
    },
    {
        "question": "Какие типы экономических систем существуют?",
        "options": ["А) Традиционная, командная, рыночная, смешанная", "Б) Только рыночная", "В) Государственная и частная"],
        "answer": "А",
        "difficulty": "easy",
        "time_limit": 10
    },
    {
        "question": "Какое влияние оказывает снижение процентной ставки?",
        "options": ["А) Увеличивает инвестиции", "Б) Увеличивает инфляцию", "В) Снижает спрос на кредит"],
        "answer": "А",
        "difficulty": "medium",
        "time_limit": 20
    },
    {
        "question": "Что такое экономический цикл?",
        "options": ["А) Периоды роста и спада экономики", "Б) Устойчивое экономическое развитие", "В) Нестабильность цен"],
        "answer": "А",
        "difficulty": "hard",
        "time_limit": 30
    },
    {
        "question": "Что такое дефляция?",
        "options": ["А) Рост цен", "Б) Снижение цен", "В) Стабильность цен"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 10
    },
    {
        "question": "Какой показатель характеризует безработицу?",
        "options": ["А) Уровень безработицы", "Б) Индекс цен", "В) Валютный курс"],
        "answer": "А",
        "difficulty": "medium",
        "time_limit": 20
    },
    {
        "question": "Что такое девальвация рубля?",
        "options": ["А) Укрепление рубля", "Б) Ослабление рубля", "В) Стабильность курса"],
        "answer": "Б",
        "difficulty": "hard",
        "time_limit": 30
    },
    {
        "question": "Что показывает индекс потребительских цен?",
        "options": ["А) Динамику цен на товары и услуги", "Б) Уровень безработицы", "В) Объём экспорта"],
        "answer": "А",
        "difficulty": "easy",
        "time_limit": 10
    },
    {
        "question": "Что такое рецессия?",
        "options": ["А) Экономический рост", "Б) Экономический спад", "В) Стабильная экономика"],
        "answer": "Б",
        "difficulty": "medium",
        "time_limit": 20
    },
    {
        "question": "Что такое фискальная политика?",
        "options": ["А) Политика в области налогов и расходов", "Б) Денежная политика", "В) Торговая политика"],
        "answer": "А",
        "difficulty": "hard",
        "time_limit": 30
    },
    {
        "question": "Какой налог является прямым?",
        "options": ["А) НДС", "Б) Подоходный налог", "В) Акциз"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 10
    },
    {
        "question": "Что показывает коэффициент Джини?",
        "options": ["А) Уровень инфляции", "Б) Неравенство доходов", "В) Экономический рост"],
        "answer": "Б",
        "difficulty": "medium",
        "time_limit": 20
    },
    {
        "question": "Что такое стагфляция?",
        "options": ["А) Рост + инфляция", "Б) Спад + дефляция", "В) Стагнация + инфляция"],
        "answer": "В",
        "difficulty": "hard",
        "time_limit": 30
    },
    {
        "question": "Какой вид безработицы связан с поиском новой работы?",
        "options": ["А) Структурная", "Б) Фрикционная", "В) Циклическая"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 10
    },
    {
        "question": "Что такое ликвидность?",
        "options": ["А) Способность активов превращаться в деньги", "Б) Доходность инвестиций", "В) Уровень риска"],
        "answer": "А",
        "difficulty": "medium",
        "time_limit": 20
    }
]

# Simple HTTP-based bot using webhooks
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.parse

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"

    def send_message(self, chat_id, text, reply_markup=None):
        """Send message to Telegram chat"""
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }

        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)

        try:
            req_data = urllib.parse.urlencode(data).encode('utf-8')
            request = urllib.request.Request(f"{self.api_url}/sendMessage", data=req_data)
            request.add_header('Content-Type', 'application/x-www-form-urlencoded; charset=utf-8')
            response = urllib.request.urlopen(request)
            return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            print(f"Error sending message: {e}")
            return None

    def _question_timer(self, chat_id, time_limit):
        """Timer for quiz questions"""
        time.sleep(time_limit)

        # Check if user is still in quiz mode and hasn't answered
        if chat_id in user_states and user_states[chat_id].get('mode') in ['quiz', 'quiz_session'] and not user_states[chat_id].get('answered', False):
            # Time's up
            question = user_states[chat_id]['current_question']
            correct_answer = question['answer']

            # Mark as answered to prevent double processing
            user_states[chat_id]['answered'] = True

            # Update user statistics
            if chat_id not in user_scores:
                user_scores[chat_id] = {
                    'name': "Аноним",
                    'correct': 0,
                    'incorrect': 0,
                    'total': 0
                }

            # Handle session mode differently
            if user_states[chat_id].get('mode') == 'quiz_session':
                session = user_states[chat_id]
                user_scores[chat_id]['total'] += 1
                user_scores[chat_id]['incorrect'] += 1

                # Check if session should continue
                if session['current_question_num'] >= session['questions_count']:
                    # Session complete
                    session_percentage = round((session['session_correct'] / session['questions_count']) * 100, 1)
                    text = (
                        f"⏰ Время вышло! Правильный ответ: {correct_answer}\n\n"
                        f"🏁 Сессия завершена!\n"
                        f"📊 Результат: {session['session_correct']}/{session['questions_count']} ({session_percentage}%)"
                    )
                    self.send_message(chat_id, text, self.get_main_keyboard())
                    del user_states[chat_id]
                else:
                    # Continue session
                    session['current_question_num'] += 1
                    text = f"⏰ Время вышло! Правильный ответ: {correct_answer}\n\nСледующий вопрос..."
                    self.send_message(chat_id, text)
                    time.sleep(2)
                    self.quiz_question_session(chat_id)
            else:
                # Single question mode
                user_scores[chat_id]['total'] += 1
                user_scores[chat_id]['incorrect'] += 1

                score = user_scores[chat_id]
                percentage = round((score['correct'] / score['total']) * 100, 1)

                text = (
                    f"⏰ Время вышло!\n"
                    f"Правильный ответ: {correct_answer}\n\n"
                    f"📊 Ваша статистика:\n"
                    f"Правильных ответов: {score['correct']}\n"
                    f"Всего вопросов: {score['total']}\n"
                    f"Процент правильных: {percentage}%"
                )

                self.send_message(chat_id, text, self.get_main_keyboard())
                del user_states[chat_id]

    def get_main_keyboard(self):
        """Get main keyboard markup"""
        return {
            'keyboard': [
                [{'text': '🖋️ Проверь себя'}, {'text': '📊 Моя статистика'}],
                [{'text': '🏆 Рейтинг'}, {'text': '📚 Словарь терминов'}],
                [{'text': '📈 Полезные ссылки'}, {'text': '📒 Курс лекций'}],
                [{'text': '📽️ Темы докладов'}, {'text': '📐 Формулы'}],
                [{'text': '🧮 Калькулятор'}, {'text': '📰 Новости'}],
                [{'text': '🎯 Уровни сложности'}, {'text': '🎮 Быстрая игра'}],
                [{'text': '❓ Помощь'}]
            ],
            'resize_keyboard': True
        }

    def quiz_question(self, chat_id):
        """Send quiz question with timer"""
        question = random.choice(quiz_questions)

        # Get difficulty level emoji
        difficulty_emoji = {
            'easy': '🟢',
            'medium': '🟡', 
            'hard': '🔴'
        }

        difficulty_text = {
            'easy': 'Легкий',
            'medium': 'Средний',
            'hard': 'Сложный'
        }

        # Save user state with timer
        user_states[chat_id] = {
            'mode': 'quiz',
            'current_question': question,
            'start_time': time.time(),
            'answered': False
        }

        emoji = difficulty_emoji.get(question['difficulty'], '⚪')
        diff_name = difficulty_text.get(question['difficulty'], 'Обычный')

        text = f"🧠 Вопрос ({emoji} {diff_name}, {question['time_limit']} сек.):\n{question['question']}\n\n"
        for option in question['options']:
            text += f"{option}\n"

        # Create inline keyboard for quiz answers
        inline_keyboard = {
            'inline_keyboard': [
                [
                    {'text': 'А', 'callback_data': 'quiz_А'},
                    {'text': 'Б', 'callback_data': 'quiz_Б'},
                    {'text': 'В', 'callback_data': 'quiz_В'}
                ]
            ]
        }

        text += f"\n⏰ У вас есть {question['time_limit']} секунд для ответа!\nОтветьте буквой (А, Б или В)"

        self.send_message(chat_id, text, inline_keyboard)

        # Start timer thread
        timer_thread = threading.Thread(target=self._question_timer, args=(chat_id, question['time_limit']))
        timer_thread.daemon = True
        timer_thread.start()

    def check_quiz_answer(self, chat_id, username, user_answer):
        """Check quiz answer with timer validation"""
        if chat_id not in user_states or user_states[chat_id].get('mode') not in ['quiz', 'quiz_session']:
            return False

        # Check if already answered (timer expired)
        if user_states[chat_id].get('answered', False):
            return False

        # Mark as answered to prevent timer from processing
        user_states[chat_id]['answered'] = True

        # Calculate response time if available
        start_time = user_states[chat_id].get('start_time', 0)
        current_time = time.time()
        response_time = round(current_time - start_time, 1) if start_time else 0
        time_limit = user_states[chat_id]['current_question']['time_limit']

        # Check if answer was given in time (only if timer was started)
        if start_time and response_time > time_limit:
            text = f"⏰ Слишком поздно! Время ответа истекло ({response_time}с > {time_limit}с)"
            self.send_message(chat_id, text, self.get_main_keyboard())
            if user_states[chat_id].get('mode') != 'quiz_session':
                del user_states[chat_id]
            return True

        # Check which mode we're in
        if user_states[chat_id].get('mode') == 'quiz_session':
            return self._handle_session_quiz_answer(chat_id, username, user_answer)
        else:
            return self._handle_single_quiz_answer(chat_id, username, user_answer)

    def _handle_single_quiz_answer(self, chat_id, username, user_answer):
        """Handle single quiz question answer"""
        # Initialize user score if not exists
        if chat_id not in user_scores:
            user_scores[chat_id] = {
                'name': username or "Аноним",
                'correct': 0,
                'incorrect': 0,
                'total': 0
            }

        correct_answer = user_states[chat_id]['current_question']['answer']
        user_answer = user_answer.upper().strip()
        difficulty = user_states[chat_id]['current_question']['difficulty']

        # Calculate response time and bonus
        start_time = user_states[chat_id].get('start_time', 0)
        current_time = time.time()
        response_time = round(current_time - start_time, 1) if start_time else 0
        time_limit = user_states[chat_id]['current_question']['time_limit']

        # Time bonus calculation
        time_bonus = ""
        if start_time and response_time <= time_limit * 0.5:
            time_bonus = " ⚡ Быстрый ответ!"
        elif start_time and response_time <= time_limit * 0.75:
            time_bonus = " 👍 Хорошая скорость!"

        # Update statistics
        user_scores[chat_id]['total'] += 1

        difficulty_emoji = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}
        emoji = difficulty_emoji.get(difficulty, '⚪')

        if user_answer == correct_answer:
            user_scores[chat_id]['correct'] += 1
            score = user_scores[chat_id]
            percentage = round((score['correct'] / score['total']) * 100, 1)
            
            time_text = f"⏱️ Время ответа: {response_time}с из {time_limit}с\n" if start_time else ""
            
            text = (
                f"✅ Правильно! {emoji}{time_bonus} 🎉\n"
                f"{time_text}\n"
                f"📊 Ваша статистика:\n"
                f"Правильных ответов: {score['correct']}\n"
                f"Всего вопросов: {score['total']}\n"
                f"Процент правильных: {percentage}%"
            )
        else:
            user_scores[chat_id]['incorrect'] += 1
            score = user_scores[chat_id]
            percentage = round((score['correct'] / score['total']) * 100, 1)
            
            time_text = f"⏱️ Время ответа: {response_time}с из {time_limit}с\n" if start_time else ""
            
            text = (
                f"❌ Неверно. Правильный ответ: {correct_answer}\n"
                f"{time_text}\n"
                f"📊 Ваша статистика:\n"
                f"Правильных ответов: {score['correct']}\n"
                f"Всего вопросов: {score['total']}\n"
                f"Процент правильных: {percentage}%"
            )

        self.send_message(chat_id, text, self.get_main_keyboard())
        del user_states[chat_id]
        return True

    def _handle_session_quiz_answer(self, chat_id, username, user_answer):
        """Handle quiz session answer"""
        session = user_states[chat_id]

        # Initialize user score if not exists
        if chat_id not in user_scores:
            user_scores[chat_id] = {
                'name': username or "Аноним",
                'correct': 0,
                'incorrect': 0,
                'total': 0
            }

        correct_answer = session['current_question']['answer']
        user_answer = user_answer.upper().strip()

        # Calculate response time
        start_time = session.get('start_time', 0)
        current_time = time.time()
        response_time = round(current_time - start_time, 1) if start_time else 0
        time_limit = session['current_question']['time_limit']

        # Update session and global statistics
        user_scores[chat_id]['total'] += 1

        if user_answer == correct_answer:
            user_scores[chat_id]['correct'] += 1
            session['session_correct'] += 1
            result_emoji = "✅"
            result_text = "Правильно!"
            
            # Time bonus
            if start_time and response_time <= time_limit * 0.5:
                result_text += " ⚡"
            elif start_time and response_time <= time_limit * 0.75:
                result_text += " 👍"
        else:
            user_scores[chat_id]['incorrect'] += 1
            result_emoji = "❌"
            result_text = f"Неверно. Правильный ответ: {correct_answer}"

        # Check if session is complete
        if session['current_question_num'] >= session['questions_count']:
            # Session complete
            session_percentage = round((session['session_correct'] / session['questions_count']) * 100, 1)
            total_percentage = round((user_scores[chat_id]['correct'] / user_scores[chat_id]['total']) * 100, 1)

            final_text = (
                f"{result_emoji} {result_text}\n\n"
                f"🏁 Сессия завершена!\n\n"
                f"📊 Результаты сессии:\n"
                f"Правильных ответов: {session['session_correct']}/{session['questions_count']}\n"
                f"Процент: {session_percentage}%\n\n"
                f"📈 Общая статистика:\n"
                f"Всего правильных: {user_scores[chat_id]['correct']}\n"
                f"Общий процент: {total_percentage}%"
            )

            # Add achievement
            if session_percentage == 100:
                final_text += "\n\n🏆 Поздравляем! Идеальный результат!"
            elif session_percentage >= 80:
                final_text += "\n\n🥇 Отличный результат!"
            elif session_percentage >= 60:
                final_text += "\n\n🥈 Хороший результат!"

            self.send_message(chat_id, final_text, self.get_main_keyboard())
            del user_states[chat_id]
        else:
            # Continue session
            session['current_question_num'] += 1

            progress_text = (
                f"{result_emoji} {result_text}\n\n"
                f"📊 Прогресс: {session['session_correct']}/{session['current_question_num'] - 1} правильных\n"
                f"Следующий вопрос..."
            )

            self.send_message(chat_id, progress_text)

            # Small delay before next question
            threading.Timer(2.0, self.quiz_question_session, args=[chat_id]).start()

        return True

    def show_leaderboard(self, chat_id):
        """Show leaderboard"""
        if not user_scores:
            self.send_message(
                chat_id, 
                "🏆 Рейтинг пуст. Начните викторину, чтобы попасть в топ!",
                self.get_main_keyboard()
            )
            return

        # Sort by percentage, then by correct answers
        sorted_users = sorted(
            user_scores.items(),
            key=lambda x: (x[1]['correct'] / max(x[1]['total'], 1), x[1]['correct']),
            reverse=True
        )

        text = "🏆 Топ-10 участников:\n\n"
        for i, (user_id, score) in enumerate(sorted_users[:10], 1):
            percentage = round((score['correct'] / max(score['total'], 1)) * 100, 1)
            text += f"{i}. {score['name']} - {percentage}% ({score['correct']}/{score['total']})\n"

        self.send_message(chat_id, text, self.get_main_keyboard())

    def show_stats(self, chat_id):
        """Show user statistics"""
        if chat_id not in user_scores:
            self.send_message(
                chat_id,
                "📊 У вас пока нет статистики. Начните викторину!",
                self.get_main_keyboard()
            )
            return

        score = user_scores[chat_id]
        percentage = round((score['correct'] / max(score['total'], 1)) * 100, 1)

        stats_text = (
            f"📊 Ваша статистика:\n\n"
            f"👤 Имя: {score['name']}\n"
            f"✅ Правильных ответов: {score['correct']}\n"
            f"❌ Неправильных ответов: {score['incorrect']}\n"
            f"📝 Всего вопросов: {score['total']}\n"
            f"📈 Процент правильных: {percentage}%\n\n"
        )

        # Determine skill level
        if percentage >= 90:
            stats_text += "🏆 Уровень: Эксперт по экономике!"
        elif percentage >= 75:
            stats_text += "🥇 Уровень: Продвинутый"
        elif percentage >= 60:
            stats_text += "🥈 Уровень: Хороший"
        elif percentage >= 40:
            stats_text += "🥉 Уровень: Базовый"
        else:
            stats_text += "📚 Уровень: Начинающий"

        self.send_message(chat_id, stats_text, self.get_main_keyboard())

    def show_dictionary(self, chat_id):
        """Show economics dictionary"""
        text = "📚 Словарь экономических терминов:\n\n"
        dictionary = {
            "ВВП": "Валовой внутренний продукт - общая рыночная стоимость всех товаров и услуг, произведенных в стране за определенный период.",
            "Инфляция": "Устойчивое повышение общего уровня цен на товары и услуги в экономике.",
            "Дефляция": "Снижение общего уровня цен в экономике, противоположность инфляции.",
            "Рецессия": "Период экономического спада, характеризующийся сокращением ВВП в течение двух или более кварталов подряд.",
            "Ключевая ставка": "Процентная ставка, по которой центральный банк предоставляет кредиты коммерческим банкам."
        }

        for term, definition in dictionary.items():
            text += f"🔹 <b>{term}</b>\n{definition}\n\n"

        self.send_message(chat_id, text, self.get_main_keyboard())

    def show_useful_links(self, chat_id):
        """Show useful links"""
        text = "📈 Полезные ресурсы по экономике:\n\n"
        links = {
            "📈 Центральный банк РФ": "https://cbr.ru - Официальный сайт ЦБ РФ",
            "📊 Росстат": "https://rosstat.gov.ru - Федеральная служба государственной статистики",
            "💼 Минэкономразвития": "https://economy.gov.ru - Министерство экономического развития РФ",
            "📰 РБК Экономика": "https://rbc.ru/economics - Экономические новости"
        }

        for name, link in links.items():
            text += f"{name}\n{link}\n\n"

        self.send_message(chat_id, text, self.get_main_keyboard())

    def show_course(self, chat_id):
        """Show course materials"""
        course_text = (
            "📒 Курс лекций по экономике:\n\n"
            "📖 <b>Модуль 1: Основы экономической теории</b>\n"
            "• Предмет и методы экономической науки\n"
            "• Базовые экономические понятия\n"
            "• Типы экономических систем\n\n"
            "📖 <b>Модуль 2: Микроэкономика</b>\n"
            "• Спрос и предложение\n"
            "• Эластичность\n"
            "• Поведение потребителя\n\n"
            "📖 <b>Модуль 3: Макроэкономика</b>\n"
            "• ВВП и национальные счета\n"
            "• Инфляция и безработица\n"
            "• Денежно-кредитная политика\n\n"
            "💡 Для углубленного изучения используйте 'Полезные ссылки'"
        )
        self.send_message(chat_id, course_text, self.get_main_keyboard())

    def show_presentation_topics(self, chat_id):
        """Show presentation topics"""
        text = "📽️ Темы для докладов и исследований:\n\n"
        topics = [
            "🏦 Роль Центрального банка в экономике России",
            "💱 Влияние курса рубля на российскую экономику",
            "📈 Анализ динамики ВВП России за последние 10 лет",
            "🏭 Структурные проблемы российской экономики",
            "🌍 Влияние санкций на экономику России",
            "⚡ Энергетический сектор как драйвер экономики",
            "🌾 Роль аграрного сектора в экономике России",
            "💼 Малый и средний бизнес: проблемы и перспективы"
        ]

        for i, topic in enumerate(topics, 1):
            text += f"{i}. {topic}\n"

        text += f"\n💡 Выберите тему для собственного исследования!"
        self.send_message(chat_id, text, self.get_main_keyboard())

    def show_formulas(self, chat_id):
        """Show economic formulas"""
        text = "📐 Основные экономические формулы:\n\n"
        formulas = {
            "Темп инфляции": "((ИПЦ_текущий - ИПЦ_базовый) / ИПЦ_базовый) × 100%",
            "Реальный ВВП": "Номинальный ВВП / Дефлятор ВВП",
            "Уровень безработицы": "(Количество безработных / Рабочая сила) × 100%",
            "Реальная процентная ставка": "Номинальная ставка - Темп инфляции"
        }

        for formula_name, formula in formulas.items():
            text += f"🔹 <b>{formula_name}</b>\n{formula}\n\n"

        self.send_message(chat_id, text, self.get_main_keyboard())

    def show_calculator(self, chat_id):
        """Show calculator options"""
        calc_text = (
            "🧮 Экономический калькулятор:\n\n"
            "<b>Доступные расчеты:</b>\n\n"
            "📊 Темп инфляции\n"
            "💰 Реальная процентная ставка\n"
            "📈 Темп роста ВВП\n"
            "💼 Уровень безработицы\n\n"
            "💡 Для выполнения расчетов отправьте команду:\n"
            "/calc [тип расчета] [значения]\n\n"
            "Примеры:\n"
            "• /calc inflation 100 105 (инфляция)\n"
            "• /calc real_rate 10 3 (реальная ставка)\n"
            "• /calc growth 1000 1100 (рост ВВП)\n"
            "• /calc unemployment 50 1000 (безработица)"
        )
        self.send_message(chat_id, calc_text, self.get_main_keyboard())

    def handle_calculator(self, chat_id, command_parts):
        """Handle calculator commands"""
        if len(command_parts) < 2:
            self.send_message(chat_id, "❌ Неверный формат команды. Используйте /calc [тип] [значения]", self.get_main_keyboard())
            return

        calc_type = command_parts[1].lower()

        try:
            if calc_type == "inflation" and len(command_parts) >= 4:
                old_value = float(command_parts[2])
                new_value = float(command_parts[3])
                inflation_rate = ((new_value - old_value) / old_value) * 100
                result = f"📊 Темп инфляции: {inflation_rate:.2f}%"

            elif calc_type == "real_rate" and len(command_parts) >= 4:
                nominal_rate = float(command_parts[2])
                inflation_rate = float(command_parts[3])
                real_rate = nominal_rate - inflation_rate
                result = f"💰 Реальная процентная ставка: {real_rate:.2f}%"

            elif calc_type == "growth" and len(command_parts) >= 4:
                old_gdp = float(command_parts[2])
                new_gdp = float(command_parts[3])
                growth_rate = ((new_gdp - old_gdp) / old_gdp) * 100
                result = f"📈 Темп роста ВВП: {growth_rate:.2f}%"

            elif calc_type == "unemployment" and len(command_parts) >= 4:
                unemployed = float(command_parts[2])
                labor_force = float(command_parts[3])
                unemployment_rate = (unemployed / labor_force) * 100
                result = f"💼 Уровень безработицы: {unemployment_rate:.2f}%"

            else:
                result = "❌ Неизвестный тип расчета или недостаточно параметров"

            self.send_message(chat_id, result, self.get_main_keyboard())

        except ValueError:
            self.send_message(chat_id, "❌ Ошибка: введите числовые значения", self.get_main_keyboard())
        except ZeroDivisionError:
            self.send_message(chat_id, "❌ Ошибка: деление на ноль", self.get_main_keyboard())

    def show_news(self, chat_id):
        """Show news sources"""
        news_text = (
            "📰 Источники экономических новостей:\n\n"
            "🔸 <b>Российские источники:</b>\n"
            "• РБК Экономика - rbc.ru/economics\n"
            "• Ведомости - vedomosti.ru\n"
            "• Коммерсантъ - kommersant.ru\n\n"
            "🔸 <b>Международные источники:</b>\n"
            "• Bloomberg - bloomberg.com\n"
            "• Financial Times - ft.com\n"
            "• Reuters Economics - reuters.com\n\n"
            "📊 Регулярно следите за экономическими новостями!"
        )
        self.send_message(chat_id, news_text, self.get_main_keyboard())

    def send_help(self, chat_id):
        """Send help message"""
        help_text = (
            "❓ Помощь по боту:\n\n"
            "<b>Доступные функции:</b>\n\n"
            "🖋️ <b>Проверь себя</b> - экономическая викторина\n"
            "📊 <b>Моя статистика</b> - ваши результаты\n"
            "🏆 <b>Рейтинг</b> - топ участников\n"
            "📚 <b>Словарь терминов</b> - основные понятия\n"
            "📈 <b>Полезные ссылки</b> - важные ресурсы\n"
            "📒 <b>Курс лекций</b> - учебные материалы\n"
            "📽️ <b>Темы докладов</b> - идеи для работ\n"
            "📐 <b>Формулы</b> - экономические формулы\n"
            "🧮 <b>Калькулятор</b> - математические вычисления\n"
            "📰 <b>Новости</b> - экономические новости\n\n"
            "💡 <b>Как пользоваться:</b>\n"
            "• Используйте кнопки меню для навигации\n"
            "• В викторине отвечайте буквами А, Б или В\n"
            "• Результаты сохраняются в статистике"
        )
        self.send_message(chat_id, help_text, self.get_main_keyboard())

    def show_difficulty_levels(self, chat_id):
        """Show difficulty level selection"""
        text = "🎯 Выберите уровень сложности:\n\n"

        inline_keyboard = {
            'inline_keyboard': [
                [{'text': '🟢 Базовый (5 вопросов)', 'callback_data': 'difficulty_easy'}],
                [{'text': '🟡 Средний (10 вопросов)', 'callback_data': 'difficulty_medium'}],
                [{'text': '🔴 Сложный (15 вопросов)', 'callback_data': 'difficulty_hard'}],
                [{'text': '🏆 Эксперт (20 вопросов)', 'callback_data': 'difficulty_expert'}]
            ]
        }

        self.send_message(chat_id, text, inline_keyboard)

    def start_quiz_with_difficulty(self, chat_id, difficulty):
        """Start quiz with selected difficulty"""
        difficulty_settings = {
            'easy': {'count': 5, 'name': 'Базовый'},
            'medium': {'count': 10, 'name': 'Средний'},
            'hard': {'count': 15, 'name': 'Сложный'},
            'expert': {'count': 20, 'name': 'Эксперт'}
        }

        settings = difficulty_settings.get(difficulty, difficulty_settings['easy'])

        # Initialize quiz session
        user_states[chat_id] = {
            'mode': 'quiz_session',
            'difficulty': difficulty,
            'questions_count': settings['count'],
            'current_question_num': 1,
            'session_correct': 0,
            'session_questions': []
        }

        text = f"🎯 Режим: {settings['name']}\n📝 Вопросов: {settings['count']}\n\n🚀 Начинаем!"
        self.send_message(chat_id, text)

        # Start first question
        self.quiz_question_session(chat_id)

    def quiz_question_session(self, chat_id):
        """Send quiz question in session mode"""
        if chat_id not in user_states or user_states[chat_id]['mode'] != 'quiz_session':
            return

        session = user_states[chat_id]
        question = random.choice(quiz_questions)

        # Avoid repeating questions in session
        while question in session['session_questions'] and len(session['session_questions']) < len(quiz_questions):
            question = random.choice(quiz_questions)

        session['session_questions'].append(question)
        session['current_question'] = question

        text = (
            f"🎯 Вопрос {session['current_question_num']}/{session['questions_count']}\n\n"
            f"🧠 {question['question']}\n\n"
        )

        for option in question['options']:
            text += f"{option}\n"

        inline_keyboard = {
            'inline_keyboard': [
                [
                    {'text': 'А', 'callback_data': 'quiz_А'},
                    {'text': 'Б', 'callback_data': 'quiz_Б'},
                    {'text': 'В', 'callback_data': 'quiz_В'}
                ]
            ]
        }

        self.send_message(chat_id, text, inline_keyboard)

    def start_quick_game(self, chat_id):
        """Start quick 5-question game"""
        text = "🎮 Быстрая игра - 5 случайных вопросов!\n\n🚀 Поехали!"
        self.send_message(chat_id, text)

        user_states[chat_id] = {
            'mode': 'quiz_session',
            'difficulty': 'quick',
            'questions_count': 5,
            'current_question_num': 1,
            'session_correct': 0,
            'session_questions': []
        }

        self.quiz_question_session(chat_id)

    def send_start(self, chat_id, username):
        """Send start message"""
        user_name = username or "друг"
        welcome_text = (
            f"👋 Привет, {user_name}! Добро пожаловать в улучшенную экономическую викторину!\n\n"
            f"🧠 Проверьте свои знания в области экономики\n"
            f"📊 Отслеживайте свою статистику\n"
            f"🏆 Соревнуйтесь с другими участниками\n"
            f"🎯 Выбирайте уровень сложности\n"
            f"🎮 Играйте в быстрые игры\n\n"
            f"Используйте кнопки ниже для навигации!"
        )
        self.send_message(chat_id, welcome_text, self.get_main_keyboard())

    def handle_callback_query(self, callback_query):
        """Handle callback query (inline keyboard buttons)"""
        query_id = callback_query['id']
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        username = callback_query['from'].get('first_name', '')

        # Answer callback query
        try:
            answer_url = f"{self.api_url}/answerCallbackQuery"
            answer_data = urllib.parse.urlencode({'callback_query_id': query_id}).encode('utf-8')
            urllib.request.urlopen(urllib.request.Request(answer_url, data=answer_data))
        except:
            pass

        # Handle quiz answers
        if data.startswith('quiz_'):
            answer = data.replace('quiz_', '')
            self.check_quiz_answer(chat_id, username, answer)
            return

        # Handle difficulty selection
        elif data.startswith('difficulty_'):
            difficulty = data.replace('difficulty_', '')
            self.start_quiz_with_difficulty(chat_id, difficulty)
            return

    def handle_message(self, chat_id, text, username):
        """Handle incoming message"""
        # Check if user is in quiz mode
        if self.check_quiz_answer(chat_id, username, text):
            return

        # Handle button commands
        if text == "🖋️ Проверь себя":
            self.quiz_question(chat_id)
        elif text == "📊 Моя статистика":
            self.show_stats(chat_id)
        elif text == "🏆 Рейтинг":
            self.show_leaderboard(chat_id)
        elif text == "📚 Словарь терминов":
            self.show_dictionary(chat_id)
        elif text == "📈 Полезные ссылки":
            self.show_useful_links(chat_id)
        elif text == "📒 Курс лекций":
            self.show_course(chat_id)
        elif text == "📽️ Темы докладов":
            self.show_presentation_topics(chat_id)
        elif text == "📐 Формулы":
            self.show_formulas(chat_id)
        elif text == "🧮 Калькулятор":
            self.show_calculator(chat_id)
        elif text == "📰 Новости":
            self.show_news(chat_id)
        elif text == "❓ Помощь":
            self.send_help(chat_id)
        elif text == "🎯 Уровни сложности":
            self.show_difficulty_levels(chat_id)
        elif text == "🎮 Быстрая игра":
            self.start_quick_game(chat_id)
        elif text == "/start":
            self.send_start(chat_id, username)
        elif text == "/quiz":
            self.quiz_question(chat_id)
        elif text == "/stats":
            self.show_stats(chat_id)
        elif text == "/leaderboard":
            self.show_leaderboard(chat_id)
        elif text == "/help":
            self.send_help(chat_id)
        elif text.startswith("/calc"):
            command_parts = text.split()
            self.handle_calculator(chat_id, command_parts)
        else:
            # Unknown command
            self.send_message(
                chat_id,
                "🤔 Не понимаю команду. Используйте кнопки меню или /help для получения помощи.",
                self.get_main_keyboard()
            )

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            if 'message' in data:
                message = data['message']
                chat_id = message['chat']['id']
                text = message.get('text', '')
                username = message.get('from', {}).get('first_name', '')

                bot.handle_message(chat_id, text, username)

            elif 'callback_query' in data:
                bot.handle_callback_query(data['callback_query'])

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        except Exception as e:
            print(f"Error handling webhook: {e}")
            self.send_response(500)
            self.end_headers()

def run_polling():
    """Run bot in polling mode"""
    offset = 0
    error_count = 0
    max_errors = 5

    print("💡 Для остановки бота нажмите Ctrl+C")

    while True:
        try:
            # Get updates
            url = f"{bot.api_url}/getUpdates?offset={offset}&timeout=30"

            # Create request with proper headers
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'TelegramBot/1.0')

            response = urllib.request.urlopen(request, timeout=35)
            data = json.loads(response.read().decode('utf-8'))

            if data['ok']:
                error_count = 0  # Reset error count on success
                for update in data['result']:
                    offset = update['update_id'] + 1

                    if 'message' in update:
                        message = update['message']
                        chat_id = message['chat']['id']
                        text = message.get('text', '')
                        username = message.get('from', {}).get('first_name', '')

                        bot.handle_message(chat_id, text, username)

                    elif 'callback_query' in update:
                        bot.handle_callback_query(update['callback_query'])
            else:
                print(f"❌ API error: {data.get('description', 'Unknown error')}")

        except urllib.error.HTTPError as e:
            error_count += 1
            if e.code == 409:
                print(f"⚠️  Конфликт polling ({error_count}/{max_errors}): Другой экземпляр бота уже запущен")
                if error_count >= max_errors:
                    print("❌ Слишком много конфликтов. Проверьте, что не запущен другой экземпляр бота.")
                    break
                import time
                time.sleep(10)  # Wait longer for 409 errors
            else:
                print(f"Polling error ({error_count}/{max_errors}): HTTP Error {e.code}: {e.reason}")
                import time
                time.sleep(5)

        except KeyboardInterrupt:
            print("\n🛑 Бот остановлен пользователем")
            break

        except Exception as e:
            error_count += 1
            print(f"Polling error ({error_count}/{max_errors}): {e}")
            if error_count >= max_errors:
                print("❌ Слишком много ошибок. Остановка бота.")
                break
            import time
            time.sleep(5)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Ошибка: Не найден токен бота. Проверьте переменную окружения TELEGRAM_BOT_TOKEN")
        exit(1)

    print("🤖 Запуск улучшенного экономического викторина-бота...")
    bot = TelegramBot(TOKEN)

    # Test bot connection and clear pending updates
    try:
        # Get bot info
        response = urllib.request.urlopen(f"{bot.api_url}/getMe")
        data = json.loads(response.read().decode('utf-8'))
        if data['ok']:
            print(f"✅ Бот подключен: @{data['result']['username']}")
            print(f"📝 Имя бота: {data['result']['first_name']}")
        else:
            print("❌ Ошибка подключения к боту")
            exit(1)

        # Clear any pending updates to avoid conflicts
        try:
            clear_url = f"{bot.api_url}/getUpdates?offset=-1"
            urllib.request.urlopen(clear_url)
            print("🧹 Очищены ожидающие обновления")
        except:
            pass  # If clearing fails, continue anyway

    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        exit(1)

    print("🔄 Запуск в режиме polling...")
    try:
        run_polling()
    except KeyboardInterrupt:
        print("\n🛑 Завершение работы...")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        print("👋 Бот остановлен")