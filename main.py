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
achievements = {}

# Конфигурация
CONFIG = {
    "data_file": "user_data.json",
    "backup_interval": 3600,  # Секунды между сохранениями
    "progress_chars": "⬜🟩",
    "progress_length": 10
}

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
    {
        "question": "Что характеризует метод научной абстракции?",
        "options": ["А) Отвлечение от случайного и выделение устойчивого", "Б) Изучение только конкретных фактов", "В) Применение только математических методов"],
        "answer": "А",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Основы экономической теории"
    },
    {
        "question": "Что такое экономические ресурсы?",
        "options": ["А) Безграничные природные богатства", "Б) Ограниченные относительно потребности в них ресурсы", "В) Только денежные средства"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Основы экономической теории"
    },
    {
        "question": "Какие факторы производства выделяют в экономической теории?",
        "options": ["А) Только труд и капитал", "Б) Деньги и технологии", "В) Земля, капитал, труд, предпринимательские способности"],
        "answer": "В",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Основы экономической теории"
    },
    {
        "question": "Что показывает кривая производственных возможностей?",
        "options": ["А) Минимальные затраты производства", "Б) Максимально возможное производство при полном использовании ресурсов", "В) Динамику цен на товары"],
        "answer": "Б",
        "difficulty": "hard",
        "time_limit": 25,
        "topic": "Основы экономической теории"
    },
    {
        "question": "Что такое альтернативные издержки?",
        "options": ["А) Прямые денежные затраты", "Б) Налоги и сборы", "В) Ценность благ при наиболее выгодном использовании ресурса"],
        "answer": "В",
        "difficulty": "hard",
        "time_limit": 25,
        "topic": "Основы экономической теории"
    },

    # Лекция 2: Экономические системы
    {
        "question": "Какие типы экономических систем существуют?",
        "options": ["А) Традиционная, командно-административная, рыночная, смешанная", "Б) Только рыночная и плановая", "В) Капиталистическая и социалистическая"],
        "answer": "А",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Экономические системы"
    },
    {
        "question": "Что характеризует традиционную экономику?",
        "options": ["А) Централизованное планирование", "Б) Решения принимаются согласно традициям и обычаям", "В) Рыночное ценообразование"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Экономические системы"
    },
    {
        "question": "Какие модели смешанной экономики существуют?",
        "options": ["А) Только европейская и азиатская", "Б) Северная и южная", "В) Американская, японская, шведская, германская, китайская"],
        "answer": "В",
        "difficulty": "hard",
        "time_limit": 25,
        "topic": "Экономические системы"
    },
    {
        "question": "Что характеризует командно-административную экономику?",
        "options": ["А) Частная собственность и свободный рынок", "Б) Централизованное планирование и государственная собственность", "В) Традиции и обычаи"],
        "answer": "Б",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Экономические системы"
    },

    # Лекция 3: Рынок и рыночный механизм
    {
        "question": "Что такое рынок в экономическом понимании?",
        "options": ["А) Место торговли", "Б) Только биржевые операции", "В) Совокупность отношений производства и обмена товаров при помощи денег"],
        "answer": "В",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Рынок и рыночный механизм"
    },
    {
        "question": "Что характеризует закон спроса?",
        "options": ["А) С увеличением цены объем спроса уменьшается", "Б) Спрос не зависит от цены", "В) С увеличением цены спрос растет"],
        "answer": "А",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Рынок и рыночный механизм"
    },
    {
        "question": "Что такое эластичность спроса?",
        "options": ["А) Постоянство спроса", "Б) Мера реакции объема спроса на изменение цены", "В) Рост спроса независимо от цены"],
        "answer": "Б",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Рынок и рыночный механизм"
    },
    {
        "question": "Что такое рыночная инфраструктура?",
        "options": ["А) Только торговые центры", "Б) Производственные предприятия", "В) Совокупность организационно-правовых форм, связывающих субъектов рынка"],
        "answer": "В",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Рынок и рыночный механизм"
    },
    {
        "question": "Что представляет собой биржа?",
        "options": ["А) Форма регулярно действующего оптового рынка", "Б) Розничный магазин", "В) Производственное предприятие"],
        "answer": "А",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Рынок и рыночный механизм"
    },

    # Лекция 4: Конкуренция
    {
        "question": "Что такое конкуренция в экономике?",
        "options": ["А) Государственное регулирование", "Б) Экономическая состязательность субъектов за реализацию интересов", "В) Международное сотрудничество"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Конкуренция и рыночные структуры"
    },
    {
        "question": "Какие виды конкуренции существуют?",
        "options": ["А) Только ценовая", "Б) Государственная и частная", "В) Совершенная и несовершенная"],
        "answer": "В",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Конкуренция и рыночные структуры"
    },
    {
        "question": "Что такое монополия?",
        "options": ["А) Исключительное положение хозяйствующего субъекта на рынке", "Б) Множество конкурентов", "В) Государственное регулирование"],
        "answer": "А",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Конкуренция и рыночные структуры"
    },
    {
        "question": "Какие типы монополий выделяют по происхождению?",
        "options": ["А) Большая и малая", "Б) Закрытая, естественная, открытая", "В) Внутренняя и внешняя"],
        "answer": "Б",
        "difficulty": "hard",
        "time_limit": 25,
        "topic": "Конкуренция и рыночные структуры"
    },
    {
        "question": "Что характеризует олигополию?",
        "options": ["А) Много мелких производителей", "Б) Один покупатель на рынке", "В) Господство нескольких крупных фирм на рынке"],
        "answer": "В",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Конкуренция и рыночные структуры"
    },

    # Лекция 5: Предприятие и издержки
    {
        "question": "Какие издержки относятся к постоянным?",
        "options": ["А) Расходы на сырье и материалы", "Б) Расходы, не зависящие от объема выпускаемой продукции", "В) Заработная плата рабочих"],
        "answer": "Б",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Предприятие и производство"
    },
    {
        "question": "Что такое производственная функция?",
        "options": ["А) График производства", "Б) План выпуска продукции", "В) Зависимость между количеством ресурсов и объемом выпуска"],
        "answer": "В",
        "difficulty": "hard",
        "time_limit": 25,
        "topic": "Предприятие и производство"
    },
    {
        "question": "Какие виды прибыли различают в экономической теории?",
        "options": ["А) Бухгалтерская, экономическая, нормальная", "Б) Только валовая", "В) Чистая и грязная"],
        "answer": "А",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Предприятие и производство"
    },

    # Лекция 6: Рынки факторов производства
    {
        "question": "Что такое земельная рента?",
        "options": ["А) Налог на землю", "Б) Доход, получаемый собственником земли от сдачи ее в аренду", "В) Стоимость земельного участка"],
        "answer": "Б",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Рынки факторов производства"
    },
    {
        "question": "Что характеризует рынок труда?",
        "options": ["А) Только количество работников", "Б) Размер заработной платы", "В) Спрос и предложение рабочей силы"],
        "answer": "В",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Рынки факторов производства"
    },

    # Лекция 7: Макроэкономические показатели
    {
        "question": "Что такое валовой внутренний продукт (ВВП)?",
        "options": ["А) Только экспорт страны", "Б) Общая рыночная стоимость товаров и услуг, произведенных в стране", "В) Количество предприятий в стране"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Макроэкономика"
    },
    {
        "question": "Что представляет собой система национальных счетов?",
        "options": ["А) Банковская система", "Б) Система измерения макроэкономических показателей", "В) Налоговая система"],
        "answer": "Б",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Макроэкономика"
    },

    # Лекция 8: Экономический рост и циклы
    {
        "question": "Что такое экономический цикл?",
        "options": ["А) Постоянный экономический рост", "Б) Стабильность цен", "В) Периодические колебания экономической активности"],
        "answer": "В",
        "difficulty": "hard",
        "time_limit": 25,
        "topic": "Экономический рост и циклы"
    },
    {
        "question": "Какие типы экономического роста существуют?",
        "options": ["А) Экстенсивный и интенсивный", "Б) Быстрый и медленный", "В) Внутренний и внешний"],
        "answer": "А",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Экономический рост и циклы"
    },

    # Лекция 9: Безработица и инфляция
    {
        "question": "Что такое инфляция?",
        "options": ["А) Снижение уровня цен", "Б) Устойчивое повышение общего уровня цен", "В) Стабильность цен"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Макроэкономические проблемы"
    },
    {
        "question": "Что такое дефляция?",
        "options": ["А) Снижение общего уровня цен", "Б) Повышение общего уровня цен", "В) Стабильность цен"],
        "answer": "А",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Макроэкономические проблемы"
    },
    {
        "question": "Какой показатель характеризует состояние рынка труда?",
        "options": ["А) Индекс потребительских цен", "Б) Уровень безработицы", "В) Валютный курс"],
        "answer": "Б",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Макроэкономические проблемы"
    },
    {
        "question": "Что такое стагфляция?",
        "options": ["А) Экономический рост с инфляцией", "Б) Спад с дефляцией", "В) Застой экономики с инфляцией"],
        "answer": "В",
        "difficulty": "hard",
        "time_limit": 30,
        "topic": "Макроэкономические проблемы"
    },
    {
        "question": "Какой вид безработицы связан с поиском работы?",
        "options": ["А) Фрикционная", "Б) Структурная", "В) Циклическая"],
        "answer": "А",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Макроэкономические проблемы"
    },

    # Лекция 10: Бюджетно-налоговая политика
    {
        "question": "Что такое бюджетный дефицит?",
        "options": ["А) Превышение доходов над расходами", "Б) Превышение расходов бюджета над доходами", "В) Равенство доходов и расходов"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Государственное регулирование"
    },
    {
        "question": "Что включает в себя фискальная политика?",
        "options": ["А) Только денежную политику", "Б) Бюджетно-налоговые меры государства", "В) Международную торговлю"],
        "answer": "Б",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Государственное регулирование"
    },

    # Лекция 11: Денежно-кредитная политика
    {
        "question": "Какие функции выполняют деньги?",
        "options": ["А) Только средство платежа", "Б) Только мера стоимости", "В) Мера стоимости, средство обращения, средство накопления"],
        "answer": "В",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Денежно-кредитная система"
    },
    {
        "question": "Что характеризует монетарную политику?",
        "options": ["А) Налоговое регулирование", "Б) Управление денежной массой и процентными ставками", "В) Государственные расходы"],
        "answer": "Б",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Денежно-кредитная система"
    },
    {
        "question": "Какое влияние оказывает снижение ключевой ставки ЦБ?",
        "options": ["А) Снижает инфляцию", "Б) Стимулирует инвестиции и кредитование", "В) Уменьшает спрос на кредиты"],
        "answer": "Б",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Денежно-кредитная система"
    },
    {
        "question": "Что означает девальвация национальной валюты?",
        "options": ["А) Укрепление валюты", "Б) Ослабление валюты относительно других", "В) Стабильность курса"],
        "answer": "Б",
        "difficulty": "hard",
        "time_limit": 25,
        "topic": "Денежно-кредитная система"
    },

    # Лекция 12: Мировое хозяйство
    {
        "question": "Что такое мировое хозяйство?",
        "options": ["А) Экономика одной страны", "Б) Система взаимосвязанных национальных экономик", "В) Только международная торговля"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Мировая экономика"
    },
    {
        "question": "Что показывает индекс потребительских цен (ИПЦ)?",
        "options": ["А) Уровень безработицы", "Б) Изменение стоимости потребительской корзины", "В) Объем экспорта"],
        "answer": "Б",
        "difficulty": "easy",
        "time_limit": 15,
        "topic": "Макроэкономика"
    },

    # Дополнительные концептуальные вопросы
    {
        "question": "Что показывает коэффициент Джини?",
        "options": ["А) Уровень инфляции", "Б) Неравенство в распределении доходов", "В) Темп экономического роста"],
        "answer": "Б",
        "difficulty": "hard",
        "time_limit": 25,
        "topic": "Социально-экономические показатели"
    },
    {
        "question": "Что такое ликвидность активов?",
        "options": ["А) Высокая доходность", "Б) Низкий уровень риска", "В) Способность быстро превращаться в деньги"],
        "answer": "В",
        "difficulty": "medium",
        "time_limit": 20,
        "topic": "Финансовые рынки"
    }
]

class TimerManager:
    """Улучшенный менеджер таймеров"""
    def __init__(self):
        self.timers = {}
        self.lock = threading.Lock()
    
    def set_timer(self, key, delay, callback, *args):
        """Установить таймер с автоматической очисткой"""
        with self.lock:
            if key in self.timers:
                self.timers[key].cancel()
            
            timer = threading.Timer(delay, self._timer_callback, args=(key, callback, args))
            timer.daemon = True
            self.timers[key] = timer
            timer.start()
    
    def cancel_timer(self, key):
        """Отменить таймер"""
        with self.lock:
            if key in self.timers:
                self.timers[key].cancel()
                del self.timers[key]
    
    def _timer_callback(self, key, callback, args):
        """Внутренний callback таймера"""
        try:
            callback(*args)
        except Exception as e:
            logger.error(f"Timer callback error: {e}")
        finally:
            with self.lock:
                if key in self.timers:
                    del self.timers[key]

# Глобальный менеджер таймеров
timer_manager = TimerManager()

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.running = True
        self.cleanup_interval = 300  # 5 минут

    def send_message(self, chat_id, text, reply_markup=None):
        """Send message to Telegram chat with improved error handling"""
        try:
            if isinstance(text, str):
                text = text.encode('utf-8').decode('utf-8')
            
            data = {
                'chat_id': str(chat_id),
                'text': text[:4096],
                'parse_mode': 'HTML'
            }

            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)

            req_data = urllib.parse.urlencode(data, safe='', encoding='utf-8').encode('utf-8')
            request = urllib.request.Request(f"{self.api_url}/sendMessage", data=req_data)
            request.add_header('Content-Type', 'application/x-www-form-urlencoded; charset=utf-8')

            with urllib.request.urlopen(request, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                if not result.get('ok'):
                    logger.error(f"API error: {result}")
                return result
                    
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {e}")
            return None

    def cleanup_old_states(self):
        """Очистка старых состояний пользователей"""
        try:
            current_time = time.time()
            cutoff_time = current_time - 1800  # 30 минут
            
            # Очистка старых состояний
            expired_users = []
            for chat_id, state in user_states.items():
                last_activity = state.get('last_activity', current_time)
                if last_activity < cutoff_time:
                    expired_users.append(chat_id)
            
            for chat_id in expired_users:
                timer_manager.cancel_timer(f"quiz_{chat_id}")
                if chat_id in user_states:
                    del user_states[chat_id]
                    
            if expired_users:
                logger.info(f"Cleaned up {len(expired_users)} expired user states")
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def _question_timer_callback(self, chat_id):
        """Улучшенный callback таймера для вопросов"""
        try:
            if chat_id not in user_states:
                return

            state = user_states[chat_id]
            if state.get('answered', False) or state.get('mode') not in ['quiz', 'quiz_session']:
                return

            state['answered'] = True
            question = state.get('current_question')
            if not question:
                return

            correct_answer = question['answer']

            if chat_id not in user_scores:
                user_scores[chat_id] = {
                    'name': "Аноним",
                    'correct': 0,
                    'incorrect': 0,
                    'total': 0
                }

            if state.get('mode') == 'quiz_session':
                self._handle_session_timeout(chat_id, correct_answer)
            else:
                self._handle_single_timeout(chat_id, correct_answer)
                
        except Exception as e:
            logger.error(f"Timer callback error for chat {chat_id}: {e}")

    def _handle_session_timeout(self, chat_id, correct_answer):
        """Обработка таймаута в режиме сессии"""
        try:
            session = user_states[chat_id]
            user_scores[chat_id]['total'] += 1
            user_scores[chat_id]['incorrect'] += 1

            if session['current_question_num'] >= session['questions_count']:
                session_percentage = round((session['session_correct'] / session['questions_count']) * 100, 1)
                total_percentage = round((user_scores[chat_id]['correct'] / user_scores[chat_id]['total']) * 100, 1)

                text = (
                    f"⏰ Время вышло! Правильный ответ: <b>{correct_answer}</b>\n\n"
                    f"🏁 Сессия завершена!\n\n"
                    f"📊 Результаты сессии:\n"
                    f"Правильных ответов: {session['session_correct']}/{session['questions_count']}\n"
                    f"Процент: {session_percentage}%\n\n"
                    f"📈 Общая статистика:\n"
                    f"Всего правильных: {user_scores[chat_id]['correct']}\n"
                    f"Общий процент: {total_percentage}%"
                )
                self.send_message(chat_id, text, self.get_main_keyboard())
                if chat_id in user_states:
                    del user_states[chat_id]
            else:
                session['current_question_num'] += 1
                text = f"⏰ Время вышло! Правильный ответ: <b>{correct_answer}</b>\n\nСледующий вопрос..."
                self.send_message(chat_id, text)

                timer_manager.set_timer(f"next_question_{chat_id}", 2.0, self.quiz_question_session, chat_id)
                
        except Exception as e:
            logger.error(f"Session timeout error: {e}")

    def _handle_single_timeout(self, chat_id, correct_answer):
        """Обработка таймаута одиночного вопроса"""
        try:
            user_scores[chat_id]['total'] += 1
            user_scores[chat_id]['incorrect'] += 1

            score = user_scores[chat_id]
            percentage = round((score['correct'] / score['total']) * 100, 1)

            text = (
                f"⏰ Время вышло!\n"
                f"Правильный ответ: <b>{correct_answer}</b>\n\n"
                f"📊 Ваша статистика:\n"
                f"Правильных ответов: {score['correct']}\n"
                f"Всего вопросов: {score['total']}\n"
                f"Процент правильных: {percentage}%"
            )

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
        f"🚀 Бот запущен! Привет, {user.first_name}!",
        reply_markup=get_main_keyboard()
    )

def get_main_keyboard():
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