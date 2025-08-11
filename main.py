# main.py
import os
import logging
import json
import random
import sys
import time
import threading
import urllib.request
import urllib.parse
from dotenv import load_dotenv
from flask import Flask, request, jsonify

# -------------------------
# Configuration / Logging
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Ensure stdout uses utf-8 in environments that need it
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Load .env if present
load_dotenv()

TOKEN = os.getenv('TELEGRAM_TOKEN')
APP_NAME = os.getenv('APP_NAME')        # optional, used to form webhook URL if WEBHOOK_URL not provided
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # if provided, will be used as webhook endpoint
PORT = int(os.environ.get('PORT', 8080))

# -------------------------
# Simple environment checks
# -------------------------
if not TOKEN:
    logger.error("TELEGRAM_TOKEN is not set. Please set it in environment or via fly secrets.")
    sys.exit(1)

# -------------------------
# State and questions
# -------------------------
user_states = {}
user_scores = {}

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

# -------------------------
# Timer manager (for timeouts)
# -------------------------
class TimerManager:
    """Управление таймерами для вопросов"""
    def __init__(self):
        self.timers = {}
        self.lock = threading.Lock()

    def set_timer(self, key, delay, callback, *args):
        with self.lock:
            if key in self.timers:
                try:
                    self.timers[key].cancel()
                except Exception:
                    pass
            timer = threading.Timer(delay, self._timer_callback, args=(key, callback, args))
            timer.daemon = True
            self.timers[key] = timer
            timer.start()

    def cancel_timer(self, key):
        with self.lock:
            if key in self.timers:
                try:
                    self.timers[key].cancel()
                except Exception:
                    pass
                del self.timers[key]

    def _timer_callback(self, key, callback, args):
        try:
            callback(*args)
        except Exception as e:
            logger.error(f"Timer callback error: {e}")
        finally:
            with self.lock:
                if key in self.timers:
                    del self.timers[key]

timer_manager = TimerManager()

# -------------------------
# TelegramBot helper
# -------------------------
class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"

    def _request(self, method, data=None):
        url = f"{self.api_url}/{method}"
        try:
            if data is None:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    return json.loads(resp.read().decode('utf-8'))
            else:
                encoded = urllib.parse.urlencode(data, safe='', encoding='utf-8').encode('utf-8')
                req = urllib.request.Request(url, data=encoded)
                req.add_header('Content-Type', 'application/x-www-form-urlencoded; charset=utf-8')
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            logger.error(f"Request error {method}: {e}")
            return None

    def send_message(self, chat_id, text, reply_markup=None):
        data = {
            'chat_id': str(chat_id),
            'text': text[:4096],
            'parse_mode': 'HTML'
        }
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup, ensure_ascii=False)
        return self._request('sendMessage', data)

    def answer_callback(self, callback_query_id, text=None):
        data = {'callback_query_id': callback_query_id}
        if text:
            data['text'] = text
        return self._request('answerCallbackQuery', data)

    def set_webhook(self, url, allowed_updates=None, drop_pending_updates=True):
        data = {'url': url}
        if allowed_updates:
            data['allowed_updates'] = json.dumps(allowed_updates, ensure_ascii=False)
        if drop_pending_updates:
            data['drop_pending_updates'] = 'true'
        return self._request('setWebhook', data)

# -------------------------
# Bot logic functions
# -------------------------
def get_main_keyboard():
    return {
        'keyboard': [
            [{'text': '🖋️ Проверь себя'}, {'text': '📊 Моя статистика'}],
            [{'text': '🏆 Рейтинг'}, {'text': '📚 Словарь терминов'}],
            [{'text': '📈 Полезные ссылки'}, {'text': '📒 Курс лекций'}],
            [{'text': '❓ Помощь'}]
        ],
        'resize_keyboard': True
    }

def quiz_question_single(chat_id, bot_obj):
    question = random.choice(quiz_questions)
    user_states[chat_id] = {
        'mode': 'quiz',
        'current_question': question,
        'start_time': time.time(),
        'answered': False
    }

    difficulty_emoji = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}
    emoji = difficulty_emoji.get(question.get('difficulty', ''), '')

    text = f"🧠 {emoji} <b>{question['question']}</b>\n\n"
    for opt in question['options']:
        text += f"{opt}\n"

    inline_keyboard = {
        'inline_keyboard': [
            [
                {'text': 'А', 'callback_data': 'quiz_А'},
                {'text': 'Б', 'callback_data': 'quiz_Б'},
                {'text': 'В', 'callback_data': 'quiz_В'}
            ]
        ]
    }

    text += f"\n⏰ У вас есть <b>{question['time_limit']}</b> секунд для ответа!"
    bot_obj.send_message(chat_id, text, inline_keyboard)

    # set timer for question timeout
    timer_manager.set_timer(f"quiz_{chat_id}", question['time_limit'], question_timeout, chat_id)

def question_timeout(chat_id):
    try:
        state = user_states.get(chat_id)
        if not state or state.get('answered', False):
            return

        state['answered'] = True
        question = state.get('current_question')
        correct = question.get('answer') if question else "—"

        # update scores
        if chat_id not in user_scores:
            user_scores[chat_id] = {'name': 'Аноним', 'correct': 0, 'incorrect': 0, 'total': 0}

        user_scores[chat_id]['total'] += 1
        user_scores[chat_id]['incorrect'] += 1

        percentage = round((user_scores[chat_id]['correct'] / user_scores[chat_id]['total']) * 100, 1)

        text = (
            f"⏰ Время вышло!\n"
            f"Правильный ответ: <b>{correct}</b>\n\n"
            f"📊 Ваша статистика:\n"
            f"Правильных ответов: {user_scores[chat_id]['correct']}\n"
            f"Всего вопросов: {user_scores[chat_id]['total']}\n"
            f"Процент правильных: {percentage}%"
        )

        bot_instance.send_message(chat_id, text, get_main_keyboard())

    except Exception as e:
        logger.error(f"question_timeout error: {e}")
    finally:
        if chat_id in user_states:
            try:
                del user_states[chat_id]
            except Exception:
                pass

def show_stats(chat_id):
    if chat_id not in user_scores:
        bot_instance.send_message(chat_id, "📊 У вас пока нет статистики. Начните викторину!", get_main_keyboard())
        return

    score = user_scores[chat_id]
    percentage = round((score['correct'] / max(score['total'], 1)) * 100, 1)

    stats_text = (
        f"📊 <b>Ваша статистика:</b>\n\n"
        f"👤 Имя: {score.get('name','Аноним')}\n"
        f"✅ Правильных ответов: {score['correct']}\n"
        f"❌ Неправильных ответов: {score['incorrect']}\n"
        f"📝 Всего вопросов: {score['total']}\n"
        f"📈 Процент правильных: {percentage}%\n\n"
    )

    if percentage >= 90:
        stats_text += "🏆 <b>Уровень: Эксперт по экономике!</b>"
    elif percentage >= 75:
        stats_text += "🥇 <b>Уровень: Продвинутый</b>"
    elif percentage >= 60:
        stats_text += "🥈 <b>Уровень: Хороший</b>"
    elif percentage >= 40:
        stats_text += "🥉 <b>Уровень: Базовый</b>"
    else:
        stats_text += "📚 <b>Уровень: Начинающий</b>"

    bot_instance.send_message(chat_id, stats_text, get_main_keyboard())

# -------------------------
# Update processing
# -------------------------
def process_update(bot_obj, update):
    try:
        # handle message
        if 'message' in update:
            message = update['message']
            chat = message.get('chat', {})
            chat_id = chat.get('id')
            text = message.get('text', '')

            # update last_activity where applicable
            if chat_id and chat_id in user_states:
                user_states[chat_id]['last_activity'] = time.time()

            # simple command handling
            if text == '/start':
                bot_obj.send_message(chat_id, "👋 Привет! Я бот по экономической теории. Используй меню ниже.", get_main_keyboard())
                return

            if text == '🖋️ Проверь себя':
                quiz_question_single(chat_id, bot_obj)
                return

            if text == '📊 Моя статистика':
                show_stats(chat_id)
                return

            if text == '❓ Помощь' or text == '/help':
                help_text = (
                    "❓ <b>Помощь</b>\n\n"
                    "• Нажмите <b>🖋️ Проверь себя</b> чтобы начать случайный вопрос.\n"
                    "• Используйте кнопки в викторине (А/Б/В) для ответа.\n"
                    "• Команда /start — приветствие."
                )
                bot_obj.send_message(chat_id, help_text, get_main_keyboard())
                return

            # otherwise default reply
            bot_obj.send_message(chat_id, "Я вас не понял. Используйте кнопки меню.", get_main_keyboard())
            return

        # handle callback query (inline buttons)
        if 'callback_query' in update:
            callback = update['callback_query']
            cb_id = callback.get('id')
            data = callback.get('data', '')
            message = callback.get('message', {})
            chat = message.get('chat', {})
            chat_id = chat.get('id')

            # if it's quiz answer like "quiz_А"
            if data.startswith('quiz_'):
                answer = data.split('_', 1)[1].strip().upper()
                # verify state
                state = user_states.get(chat_id)
                if not state or 'current_question' not in state:
                    bot_obj.answer_callback(cb_id, text="Сессия не найдена или время вышло.")
                    return

                # cancel timer
                timer_manager.cancel_timer(f"quiz_{chat_id}")

                correct = state['current_question'].get('answer', '').strip().upper()

                if chat_id not in user_scores:
                    user_scores[chat_id] = {'name': 'Аноним', 'correct': 0, 'incorrect': 0, 'total': 0}

                user_scores[chat_id]['total'] += 1

                if answer == correct:
                    user_scores[chat_id]['correct'] += 1
                    bot_obj.answer_callback(cb_id, text="✅ Правильно!")
                    bot_obj.send_message(chat_id, "✅ <b>Правильно!</b>", get_main_keyboard())
                else:
                    user_scores[chat_id]['incorrect'] += 1
                    bot_obj.answer_callback(cb_id, text=f"❌ Неверно. Правильный ответ: {correct}")
                    bot_obj.send_message(chat_id, f"❌ Неверно. Правильный ответ: <b>{correct}</b>", get_main_keyboard())

                # cleanup state
                if chat_id in user_states:
                    try:
                        del user_states[chat_id]
                    except Exception:
                        pass

                return

            # other callback handling placeholders (topics, difficulty etc.)
            # if you add topic/difficulty inline buttons in future, handle them here.

            # default callback acknowledgement
            if cb_id:
                bot_obj.answer_callback(cb_id)

    except Exception as e:
        logger.error(f"process_update error: {e}")

# -------------------------
# Flask app and webhook
# -------------------------
app = Flask(__name__)
bot_instance = TelegramBot(TOKEN)

@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"})

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json(force=True)
        # process update in background thread to return 200 quickly
        threading.Thread(target=process_update, args=(bot_instance, update), daemon=True).start()
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"Webhook handling error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# -------------------------
# Startup: set webhook then run Flask
# -------------------------
def set_telegram_webhook():
    # Choose webhook URL: explicit WEBHOOK_URL env var has priority
    url = WEBHOOK_URL
    if not url:
        if APP_NAME:
            url = f"https://{APP_NAME}.fly.dev/webhook"
        else:
            logger.error("Neither WEBHOOK_URL nor APP_NAME provided. Please set WEBHOOK_URL or APP_NAME.")
            return None

    # ensure url is safe
    url = url.rstrip('/')
    logger.info(f"Setting Telegram webhook to: {url}")

    try:
        result = bot_instance.set_webhook(url)
        logger.info(f"setWebhook result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        return None

# -------------------------
# Entrypoint
# -------------------------
if __name__ == "__main__":
    # Try to set webhook before starting server
    res = set_telegram_webhook()
    # If webhook couldn't be set, we still start server — Telegram won't push updates until webhook is set.
    logger.info(f"Starting Flask on 0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT)
