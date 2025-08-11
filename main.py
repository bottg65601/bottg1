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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set UTF-8 encoding for output
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

# State management with cleanup
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

            self.send_message(chat_id, text, self.get_main_keyboard())
            if chat_id in user_states:
                del user_states[chat_id]
                
        except Exception as e:
            logger.error(f"Single timeout error: {e}")

    def get_main_keyboard(self):
        """Get main keyboard markup"""
        return {
            'keyboard': [
                [{'text': '🖋️ Проверь себя'}, {'text': '📊 Моя статистика'}],
                [{'text': '🏆 Рейтинг'}, {'text': '📚 Словарь терминов'}],
                [{'text': '📈 Полезные ссылки'}, {'text': '📒 Курс лекций'}],
                [{'text': '📽️ Темы докладов'}, {'text': '📐 Формулы'}],
                [{'text': '🧮 Калькулятор'}, {'text': '📰 Новости'}],
                [{'text': '❓ Помощь'}]
            ],
            'resize_keyboard': True
        }

    def quiz_question(self, chat_id):
        """Show unified quiz mode selection menu with topic-based options"""
        text = "🖋️ <b>Проверь себя</b> - выберите режим викторины:\n\n"

        inline_keyboard = {
            'inline_keyboard': [
                [{'text': '🎮 Быстрая игра (5 вопросов)', 'callback_data': 'mode_quick'}],
                [{'text': '🟢 Легкий (10 вопросов)', 'callback_data': 'difficulty_easy'}],
                [{'text': '🟡 Средний (15 вопросов)', 'callback_data': 'difficulty_medium'}],
                [{'text': '🔴 Сложный (20 вопросов)', 'callback_data': 'difficulty_hard'}],
                [{'text': '🏆 Эксперт (все вопросы)', 'callback_data': 'difficulty_expert'}],
                [{'text': '📚 По темам', 'callback_data': 'mode_topics'}],
                [{'text': '🔀 Случайный вопрос', 'callback_data': 'mode_single'}]
            ]
        }

        self.send_message(chat_id, text, inline_keyboard)

    def show_topic_selection(self, chat_id):
        """Show topic selection menu"""
        text = "📚 <b>Выберите тему для изучения:</b>\n\n"
        
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

        inline_keyboard = {'inline_keyboard': []}
        
        for i, topic in enumerate(topics):
            inline_keyboard['inline_keyboard'].append(
                [{'text': f'{i+1}. {topic}', 'callback_data': f'topic_{i}'}]
            )
        
        inline_keyboard['inline_keyboard'].append(
            [{'text': '⬅️ Назад', 'callback_data': 'back_to_main_quiz'}]
        )

        self.send_message(chat_id, text, inline_keyboard)

    def start_topic_quiz(self, chat_id, topic_index):
        """Start quiz for specific topic"""
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

        if topic_index >= len(topics):
            return

        selected_topic = topics[topic_index]
        topic_questions = [q for q in quiz_questions if q.get('topic') == selected_topic]
        
        if not topic_questions:
            self.send_message(chat_id, f"❌ Вопросы по теме '{selected_topic}' не найдены.", self.get_main_keyboard())
            return

        user_states[chat_id] = {
            'mode': 'quiz_session',
            'difficulty': 'topic',
            'questions_count': len(topic_questions),
            'current_question_num': 1,
            'session_correct': 0,
            'session_questions': [],
            'topic_questions': topic_questions,
            'topic_name': selected_topic,
            'answered': False,
            'last_activity': time.time()
        }

        text = f"📚 Тема: <b>{selected_topic}</b>\n📝 Вопросов: {len(topic_questions)}\n\n🚀 Начинаем изучение!"
        self.send_message(chat_id, text)

        timer_manager.set_timer(f"start_quiz_{chat_id}", 1.0, self.quiz_question_session, chat_id)

    def check_quiz_answer(self, chat_id, username, user_answer):
        """Check quiz answer with improved validation"""
        try:
            if chat_id not in user_states or user_states[chat_id].get('mode') not in ['quiz', 'quiz_session']:
                return False

            if user_states[chat_id].get('answered', False):
                return False

            timer_manager.cancel_timer(f"quiz_{chat_id}")
            user_states[chat_id]['answered'] = True
            user_states[chat_id]['last_activity'] = time.time()

            start_time = user_states[chat_id].get('start_time', 0)
            current_time = time.time()
            response_time = round(current_time - start_time, 1) if start_time else 0

            if user_states[chat_id].get('mode') == 'quiz_session':
                return self._handle_session_quiz_answer(chat_id, username, user_answer, response_time)
            else:
                return self._handle_single_quiz_answer(chat_id, username, user_answer, response_time)
                
        except Exception as e:
            logger.error(f"Quiz answer error for chat {chat_id}: {e}")
            return False

    def _handle_single_quiz_answer(self, chat_id, username, user_answer, response_time):
        """Handle single quiz question answer"""
        try:
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
            time_limit = user_states[chat_id]['current_question']['time_limit']
            topic = user_states[chat_id]['current_question'].get('topic', 'Общие знания')

            time_bonus = ""
            if response_time <= time_limit * 0.5:
                time_bonus = " ⚡ Быстрый ответ!"
            elif response_time <= time_limit * 0.75:
                time_bonus = " 👍 Хорошая скорость!"

            user_scores[chat_id]['total'] += 1

            difficulty_emoji = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}
            emoji = difficulty_emoji.get(difficulty, '⚪')

            if user_answer == correct_answer:
                user_scores[chat_id]['correct'] += 1
                score = user_scores[chat_id]
                percentage = round((score['correct'] / score['total']) * 100, 1)

                text = (
                    f"✅ <b>Правильно!</b> {emoji}{time_bonus} 🎉\n"
                    f"📚 Тема: {topic}\n"
                    f"⏱️ Время ответа: {response_time}с из {time_limit}с\n\n"
                    f"📊 Ваша статистика:\n"
                    f"Правильных ответов: {score['correct']}\n"
                    f"Всего вопросов: {score['total']}\n"
                    f"Процент правильных: {percentage}%"
                )
            else:
                user_scores[chat_id]['incorrect'] += 1
                score = user_scores[chat_id]
                percentage = round((score['correct'] / score['total']) * 100, 1)

                text = (
                    f"❌ <b>Неверно.</b> Правильный ответ: <b>{correct_answer}</b>\n"
                    f"📚 Тема: {topic}\n"
                    f"⏱️ Время ответа: {response_time}с из {time_limit}с\n\n"
                    f"📊 Ваша статистика:\n"
                    f"Правильных ответов: {score['correct']}\n"
                    f"Всего вопросов: {score['total']}\n"
                    f"Процент правильных: {percentage}%"
                )

            self.send_message(chat_id, text, self.get_main_keyboard())
            if chat_id in user_states:
                del user_states[chat_id]
            return True
            
        except Exception as e:
            logger.error(f"Single quiz answer error: {e}")
            return False

    def _handle_session_quiz_answer(self, chat_id, username, user_answer, response_time):
        """Handle quiz session answer"""
        try:
            session = user_states[chat_id]

            if chat_id not in user_scores:
                user_scores[chat_id] = {
                    'name': username or "Аноним",
                    'correct': 0,
                    'incorrect': 0,
                    'total': 0
                }

            correct_answer = session['current_question']['answer']
            user_answer = user_answer.upper().strip()
            topic = session['current_question'].get('topic', 'Общие знания')

            user_scores[chat_id]['total'] += 1

            if user_answer == correct_answer:
                user_scores[chat_id]['correct'] += 1
                session['session_correct'] += 1
                result_emoji = "✅"
                result_text = "<b>Правильно!</b>"

                time_limit = session['current_question']['time_limit']
                if response_time <= time_limit * 0.5:
                    result_text += " ⚡"
                elif response_time <= time_limit * 0.75:
                    result_text += " 👍"
            else:
                user_scores[chat_id]['incorrect'] += 1
                result_emoji = "❌"
                result_text = f"<b>Неверно.</b> Правильный ответ: <b>{correct_answer}</b>"

            if session['current_question_num'] >= session['questions_count']:
                session_percentage = round((session['session_correct'] / session['questions_count']) * 100, 1)
                total_percentage = round((user_scores[chat_id]['correct'] / user_scores[chat_id]['total']) * 100, 1)

                session_name = session.get('topic_name', 'Викторина')

                final_text = (
                    f"{result_emoji} {result_text}\n"
                    f"📚 Тема: {topic}\n\n"
                    f"🏁 <b>{session_name} завершена!</b>\n\n"
                    f"📊 Результаты сессии:\n"
                    f"Правильных ответов: {session['session_correct']}/{session['questions_count']}\n"
                    f"Процент: {session_percentage}%\n\n"
                    f"📈 Общая статистика:\n"
                    f"Всего правильных: {user_scores[chat_id]['correct']}\n"
                    f"Общий процент: {total_percentage}%"
                )

                if session_percentage == 100:
                    final_text += "\n\n🏆 <b>Поздравляем! Идеальный результат!</b>"
                elif session_percentage >= 80:
                    final_text += "\n\n🥇 <b>Отличный результат!</b>"
                elif session_percentage >= 60:
                    final_text += "\n\n🥈 <b>Хороший результат!</b>"
                elif session_percentage >= 40:
                    final_text += "\n\n🥉 <b>Неплохо, но можно лучше!</b>"
                else:
                    final_text += "\n\n📚 <b>Рекомендуем повторить материал!</b>"

                self.send_message(chat_id, final_text, self.get_main_keyboard())
                if chat_id in user_states:
                    del user_states[chat_id]
            else:
                session['current_question_num'] += 1

                progress_text = (
                    f"{result_emoji} {result_text}\n"
                    f"📚 Тема: {topic}\n\n"
                    f"📊 Прогресс: {session['session_correct']}/{session['current_question_num'] - 1} правильных\n"
                    f"Следующий вопрос..."
                )

                self.send_message(chat_id, progress_text)

                timer_manager.set_timer(f"next_question_{chat_id}", 2.0, self.quiz_question_session, chat_id)

            return True
            
        except Exception as e:
            logger.error(f"Session quiz answer error: {e}")
            return False

    def start_quiz_with_difficulty(self, chat_id, difficulty):
        """Start quiz with selected difficulty"""
        try:
            difficulty_settings = {
                'easy': {'count': 10, 'name': 'Легкий', 'filter': ['easy']},
                'medium': {'count': 15, 'name': 'Средний', 'filter': ['easy', 'medium']},
                'hard': {'count': 20, 'name': 'Сложный', 'filter': ['easy', 'medium', 'hard']},
                'expert': {'count': len(quiz_questions), 'name': 'Эксперт', 'filter': ['easy', 'medium', 'hard']}
            }

            settings = difficulty_settings.get(difficulty, difficulty_settings['easy'])

            user_states[chat_id] = {
                'mode': 'quiz_session',
                'difficulty': difficulty,
                'questions_count': settings['count'],
                'current_question_num': 1,
                'session_correct': 0,
                'session_questions': [],
                'difficulty_filter': settings['filter'],
                'answered': False,
                'last_activity': time.time()
            }

            text = f"🎯 Режим: <b>{settings['name']}</b>\n📝 Вопросов: {settings['count']}\n\n🚀 Начинаем!"
            self.send_message(chat_id, text)

            timer_manager.set_timer(f"start_quiz_{chat_id}", 1.0, self.quiz_question_session, chat_id)
            
        except Exception as e:
            logger.error(f"Start quiz with difficulty error: {e}")

    def quiz_question_session(self, chat_id):
        """Send quiz question in session mode"""
        try:
            if chat_id not in user_states or user_states[chat_id]['mode'] != 'quiz_session':
                return

            session = user_states[chat_id]

            # Check if this is a topic-based quiz
            if 'topic_questions' in session:
                available_questions = session['topic_questions']
            else:
                available_questions = [q for q in quiz_questions if q['difficulty'] in session.get('difficulty_filter', ['easy', 'medium', 'hard'])]

            remaining_questions = [q for q in available_questions if q not in session['session_questions']]
            if not remaining_questions:
                remaining_questions = available_questions

            question = random.choice(remaining_questions)
            session['session_questions'].append(question)
            session['current_question'] = question
            session['start_time'] = time.time()
            session['answered'] = False
            session['last_activity'] = time.time()

            difficulty_emoji = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}
            emoji = difficulty_emoji.get(question['difficulty'], '⚪')

            topic_info = f"📚 {question.get('topic', 'Общие знания')}\n"

            text = (
                f"🎯 Вопрос {session['current_question_num']}/{session['questions_count']} {emoji}\n"
                f"{topic_info}\n"
                f"🧠 <b>{question['question']}</b>\n\n"
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

            text += f"\n⏰ У вас есть <b>{question['time_limit']}</b> секунд для ответа!"

            self.send_message(chat_id, text, inline_keyboard)

            timer_manager.set_timer(f"quiz_{chat_id}", question['time_limit'], self._question_timer_callback, chat_id)
            
        except Exception as e:
            logger.error(f"Quiz question session error: {e}")

    def start_quick_game(self, chat_id):
        """Start quick 5-question game"""
        try:
            text = "🎮 <b>Быстрая игра</b> - 5 случайных вопросов!\n\n🚀 Поехали!"
            self.send_message(chat_id, text)

            user_states[chat_id] = {
                'mode': 'quiz_session',
                'difficulty': 'quick',
                'questions_count': 5,
                'current_question_num': 1,
                'session_correct': 0,
                'session_questions': [],
                'difficulty_filter': ['easy', 'medium', 'hard'],
                'answered': False,
                'last_activity': time.time()
            }

            timer_manager.set_timer(f"start_quiz_{chat_id}", 1.0, self.quiz_question_session, chat_id)
            
        except Exception as e:
            logger.error(f"Start quick game error: {e}")

    def start_single_question(self, chat_id):
        """Start single random question"""
        try:
            question = random.choice(quiz_questions)

            difficulty_emoji = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}
            difficulty_text = {'easy': 'Легкий', 'medium': 'Средний', 'hard': 'Сложный'}

            user_states[chat_id] = {
                'mode': 'quiz',
                'current_question': question,
                'start_time': time.time(),
                'answered': False,
                'last_activity': time.time()
            }

            emoji = difficulty_emoji.get(question['difficulty'], '⚪')
            diff_name = difficulty_text.get(question['difficulty'], 'Обычный')
            topic = question.get('topic', 'Общие знания')

            text = (
                f"🧠 <b>Случайный вопрос</b> ({emoji} {diff_name})\n"
                f"📚 Тема: {topic}\n\n"
                f"<b>{question['question']}</b>\n\n"
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

            text += f"\n⏰ У вас есть <b>{question['time_limit']}</b> секунд для ответа!"

            self.send_message(chat_id, text, inline_keyboard)

            timer_manager.set_timer(f"quiz_{chat_id}", question['time_limit'], self._question_timer_callback, chat_id)
            
        except Exception as e:
            logger.error(f"Start single question error: {e}")

    def show_leaderboard(self, chat_id):
        """Show leaderboard"""
        try:
            if not user_scores:
                self.send_message(
                    chat_id, 
                    "🏆 Рейтинг пуст. Начните викторину, чтобы попасть в топ!",
                    self.get_main_keyboard()
                )
                return

            sorted_users = sorted(
                user_scores.items(),
                key=lambda x: (x[1]['correct'] / max(x[1]['total'], 1), x[1]['correct']),
                reverse=True
            )

            text = "🏆 <b>Топ-10 участников:</b>\n\n"
            for i, (user_id, score) in enumerate(sorted_users[:10], 1):
                percentage = round((score['correct'] / max(score['total'], 1)) * 100, 1)
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                text += f"{medal} {score['name']} - {percentage}% ({score['correct']}/{score['total']})\n"

            self.send_message(chat_id, text, self.get_main_keyboard())
            
        except Exception as e:
            logger.error(f"Show leaderboard error: {e}")

    def show_stats(self, chat_id):
        """Show user statistics"""
        try:
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
                f"📊 <b>Ваша статистика:</b>\n\n"
                f"👤 Имя: {score['name']}\n"
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

            self.send_message(chat_id, stats_text, self.get_main_keyboard())
            
        except Exception as e:
            logger.error(f"Show stats error: {e}")

    def show_dictionary(self, chat_id):
        """Show economics dictionary based on lecture content"""
        try:
            text = "📚 <b>Словарь экономических терминов:</b>\n\n"
            dictionary = {
                "Экономика": "Сфера человеческой деятельности по созданию материальных и культурных благ для удовлетворения потребностей людей",
                "Экономические ресурсы": "Ограниченные относительно потребности в них ресурсы (земля, труд, капитал)",
                "Альтернативные издержки": "Ценность благ, которые можно получить при наиболее выгодном использовании ресурса",
                "Рынок": "Совокупность отношений производства и обмена товаров при помощи денег на основе конкуренции",
                "Спрос": "Общественная потребность в товарах; желание потребителей приобрести товар в соответствии с покупательной способностью",
                "Предложение": "Совокупность товаров, предлагаемых продавцом на рынок для реализации",
                "Эластичность": "Мера реакции одной величины на изменение другой",
                "Конкуренция": "Экономическая состязательность, соперничество экономических субъектов за реализацию своих интересов",
                "Монополия": "Исключительное положение хозяйствующего субъекта, дающее возможность диктовать условия на рынке",
                "Издержки производства": "Затраты на приобретение производственных факторов",
                "Прибыль": "Разность между суммарной выручкой от реализации продукции и суммарными издержками",
                "Заработная плата": "Цена за труд; стоимостная оценка рабочей силы",
                "Земельная рента": "Доход, получаемый собственником земли от сдачи ее в аренду",
                "Валовой внутренний продукт": "Общая рыночная стоимость всех товаров и услуг, произведенных в стране за определенный период",
                "Инфляция": "Устойчивое повышение общего уровня цен на товары и услуги в экономике",
                "Дефляция": "Снижение общего уровня цен в экономике",
                "Безработица": "Социально-экономическое явление, при котором часть экономически активного населения не может найти работу",
                "Стагфляция": "Застой экономики с одновременной инфляцией",
                "Бюджетный дефицит": "Превышение расходов государственного бюджета над доходами",
                "Государственный долг": "Совокупность долговых обязательств государства перед физическими и юридическими лицами",
                "Денежно-кредитная политика": "Комплекс мер центрального банка по управлению денежной массой и процентными ставками",
                "Мировое хозяйство": "Система взаимосвязанных национальных экономик, основанная на международном разделении труда",
                "Фискальная политика": "Бюджетно-налоговая политика государства",
                "Олигополия": "Рыночная структура с господством нескольких крупных фирм",
                "Биржа": "Форма регулярно действующего оптового рынка товаров, сырья, финансовых средств",
                "Ликвидность": "Способность активов быстро превращаться в деньги",
                "Девальвация": "Ослабление национальной валюты относительно других валют"
            }

            for term, definition in dictionary.items():
                text += f"📌 <b>{term}</b>\n{definition}\n\n"

            self.send_message(chat_id, text, self.get_main_keyboard())
            
        except Exception as e:
            logger.error(f"Show dictionary error: {e}")

    def show_useful_links(self, chat_id):
        """Show useful links"""
        try:
            text = "📈 <b>Полезные ресурсы по экономике:</b>\n\n"
            links = {
                "📈 Центральный банк РФ": "https://cbr.ru - Официальный сайт ЦБ РФ",
                "📊 Росстат": "https://rosstat.gov.ru - Федеральная служба государственной статистики",
                "💼 Минэкономразвития": "https://economy.gov.ru - Министерство экономического развития РФ",
                "📰 РБК Экономика": "https://rbc.ru/economics - Экономические новости",
                "🌐 Всемирный банк": "https://worldbank.org - Международная финансовая организация",
                "📊 МВФ": "https://imf.org - Международный валютный фонд"
            }

            for name, link in links.items():
                text += f"{name}\n{link}\n\n"

            self.send_message(chat_id, text, self.get_main_keyboard())
            
        except Exception as e:
            logger.error(f"Show useful links error: {e}")

    def show_course(self, chat_id):
        """Show course menu with lecture selection"""
        try:
            text = "📚 <b>Курс лекций по экономической теории</b>\n\n"
            text += "Выберите лекцию для изучения:\n\n"
            
            inline_keyboard = {
                'inline_keyboard': [
                    [{'text': '📖 Лекция 1: Предмет и метод экономической теории', 'callback_data': 'lecture_1'}],
                    [{'text': '📖 Лекция 2: Экономические системы', 'callback_data': 'lecture_2'}],
                    [{'text': '📖 Лекция 3: Рынок и рыночный механизм', 'callback_data': 'lecture_3'}],
                    [{'text': '📖 Лекция 4: Конкуренция в рыночных отношениях', 'callback_data': 'lecture_4'}],
                    [{'text': '📖 Лекция 5: Предприятие в системе рынка', 'callback_data': 'lecture_5'}],
                    [{'text': '📖 Лекция 6: Рынки факторов производства', 'callback_data': 'lecture_6'}],
                    [{'text': '📖 Лекция 7: Макроэкономические показатели', 'callback_data': 'lecture_7'}],
                    [{'text': '📖 Лекция 8: Экономический рост и цикличность', 'callback_data': 'lecture_8'}],
                    [{'text': '📖 Лекция 9: Макроэкономические проблемы', 'callback_data': 'lecture_9'}],
                    [{'text': '📖 Лекция 10: Бюджетно-налоговая политика', 'callback_data': 'lecture_10'}],
                    [{'text': '📖 Лекция 11: Денежно-кредитная политика', 'callback_data': 'lecture_11'}],
                    [{'text': '📖 Лекция 12: Мировое хозяйство', 'callback_data': 'lecture_12'}],
                    [{'text': '📋 Содержание курса', 'callback_data': 'course_content'}]
                ]
            }
            
            self.send_message(chat_id, text, inline_keyboard)
            
        except Exception as e:
            logger.error(f"Show course error: {e}")

    def show_lecture_content(self, chat_id, lecture_num):
        """Show specific lecture content from file"""
        try:
            with open('attached_assets/Лекции фулл_1750968879163.txt', 'r', encoding='utf-8') as f:
                content = f.read()
                
            lectures = {
                1: {
                    'title': 'Предмет и метод экономической теории',
                    'start': 'Лекция 1 ПРЕДМЕТ И МЕТОД',
                    'end': 'Лекция 2 ЭКОНОМИЧЕСКАЯ СИСТЕМА'
                },
                2: {
                    'title': 'Экономические системы',
                    'start': 'Лекция 2 ЭКОНОМИЧЕСКАЯ СИСТЕМА',
                    'end': 'Лекция 3'
                },
                3: {
                    'title': 'Рынок и рыночный механизм',
                    'start': 'Лекция 3\nРЫНОК И РЫНОЧНЫЙ МЕХАНИЗМ',
                    'end': 'Лекция 4 КОНКУРЕНЦИЯ'
                },
                4: {
                    'title': 'Конкуренция в системе рыночных отношений',
                    'start': 'Лекция 4 КОНКУРЕНЦИЯ',
                    'end': 'Лекция 5 ПРЕДПРИЯТИЕ'
                },
                5: {
                    'title': 'Предприятие в системе рыночных отношений',
                    'start': 'Лекция 5 ПРЕДПРИЯТИЕ',
                    'end': 'Лекция 6 РЫНКИ ФАКТОРОВ'
                },
                6: {
                    'title': 'Рынки факторов производства',
                    'start': 'Лекция 6 РЫНКИ ФАКТОРОВ',
                    'end': 'Лекция 7 ВВЕДЕНИЕ В МАКРОЭКОНОМИКУ'
                },
                7: {
                    'title': 'Макроэкономические показатели',
                    'start': 'Лекция 7 ВВЕДЕНИЕ В МАКРОЭКОНОМИКУ',
                    'end': 'Лекция 8 ЭКОНОМИЧЕСКИЙ РОСТ'
                },
                8: {
                    'title': 'Экономический рост и цикличность',
                    'start': 'Лекция 8 ЭКОНОМИЧЕСКИЙ РОСТ',
                    'end': 'Лекция 9 МАКРОЭКОНОМИЧЕСКИЕ ПРОБЛЕМЫ'
                },
                9: {
                    'title': 'Макроэкономические проблемы',
                    'start': 'Лекция 9 МАКРОЭКОНОМИЧЕСКИЕ ПРОБЛЕМЫ',
                    'end': 'Лекция 10 ГОСУДАРСТВЕННОЕ РЕГУЛИРОВАНИЕ'
                },
                10: {
                    'title': 'Бюджетно-налоговая политика',
                    'start': 'Лекция 10 ГОСУДАРСТВЕННОЕ РЕГУЛИРОВАНИЕ',
                    'end': 'Лекция 11 ДЕНЕЖНО-КРЕДИТНАЯ'
                },
                11: {
                    'title': 'Денежно-кредитная политика',
                    'start': 'Лекция 11 ДЕНЕЖНО-КРЕДИТНАЯ',
                    'end': 'Лекция 12 МИРОВОЕ ХОЗЯЙСТВО'
                },
                12: {
                    'title': 'Мировое хозяйство',
                    'start': 'Лекция 12 МИРОВОЕ ХОЗЯЙСТВО',
                    'end': 'БИБЛИОГРАФИЧЕСКИЙ СПИСОК'
                }
            }
            
            if lecture_num in lectures:
                lecture_info = lectures[lecture_num]
                
                # Найти начало и конец лекции
                start_pos = content.find(lecture_info['start'])
                end_pos = content.find(lecture_info['end'])
                
                if start_pos != -1:
                    if end_pos != -1:
                        lecture_text = content[start_pos:end_pos]
                    else:
                        lecture_text = content[start_pos:]
                    
                    # Очистить текст и разбить на части
                    lecture_text = lecture_text.strip()
                    
                    # Разбить на части по 4000 символов (лимит Telegram)
                    parts = []
                    max_length = 4000
                    
                    while len(lecture_text) > max_length:
                        # Найти последний перенос строки в пределах лимита
                        split_pos = lecture_text.rfind('\n', 0, max_length)
                        if split_pos == -1:
                            split_pos = max_length
                        
                        parts.append(lecture_text[:split_pos])
                        lecture_text = lecture_text[split_pos:].strip()
                    
                    if lecture_text:
                        parts.append(lecture_text)
                    
                    # Отправить части
                    for i, part in enumerate(parts):
                        if i == 0:
                            header = f"📖 <b>Лекция {lecture_num}: {lecture_info['title']}</b>\n\n"
                            part = header + part
                        
                        if i == len(parts) - 1:  # Последняя часть
                            inline_keyboard = {
                                'inline_keyboard': [
                                    [{'text': '⬅️ Назад к курсу', 'callback_data': 'back_to_course'}],
                                    [{'text': '🏠 Главное меню', 'callback_data': 'main_menu'}]
                                ]
                            }
                            self.send_message(chat_id, part, inline_keyboard)
                        else:
                            self.send_message(chat_id, part)
                else:
                    self.send_message(chat_id, f"❌ Лекция {lecture_num} не найдена", self.get_main_keyboard())
            else:
                self.send_message(chat_id, "❌ Номер лекции не найден", self.get_main_keyboard())
                
        except FileNotFoundError:
            self.send_message(chat_id, "❌ Файл с лекциями не найден", self.get_main_keyboard())
        except Exception as e:
            logger.error(f"Lecture content error: {e}")
            self.send_message(chat_id, "❌ Ошибка при загрузке лекции", self.get_main_keyboard())

    def show_course_content(self, chat_id):
        """Show course table of contents"""
        try:
            content_text = (
                "📋 <b>Содержание курса лекций по экономической теории:</b>\n\n"
                
                "📖 <b>Лекция 1: Предмет и метод экономической теории</b>\n"
                "• Предмет и метод экономической науки\n"
                "• Функции экономической науки\n"
                "• Материальные потребности и экономические ресурсы\n"
                "• Экономический выбор и эффективность\n\n"

                "📖 <b>Лекция 2: Экономические системы</b>\n"
                "• Типы экономических систем\n"
                "• Модели смешанной экономики\n"
                "• Несовершенство рыночной системы\n\n"

                "📖 <b>Лекция 3: Рынок и рыночный механизм</b>\n"
                "• Структура и инфраструктура рынка\n"
                "• Рыночный механизм и его функционирование\n"
                "• Спрос, предложение, эластичность\n\n"

                "📖 <b>Лекция 4: Конкуренция в рыночных отношениях</b>\n"
                "• Виды и методы конкуренции\n"
                "• Типы рыночных структур\n"
                "• Монополизм и антимонопольное регулирование\n\n"

                "📖 <b>Лекция 5: Предприятие в системе рынка</b>\n"
                "• Функционирование предприятий\n"
                "• Издержки производства и прибыль\n"
                "• Концепции прибыли\n\n"

                "📖 <b>Лекция 6: Рынки факторов производства</b>\n"
                "• Рынок труда и заработная плата\n"
                "• Рынок земли и земельная рента\n"
                "• Формирование и распределение доходов\n\n"

                "📖 <b>Лекция 7: Макроэкономические показатели</b>\n"
                "• Система национальных счетов\n"
                "• Макроэкономическое равновесие\n\n"

                "📖 <b>Лекция 8: Экономический рост и цикличность</b>\n"
                "• Показатели экономического роста\n"
                "• Типы и фазы экономических циклов\n"
                "• Государственное регулирование экономики\n\n"

                "📖 <b>Лекция 9: Макроэкономические проблемы</b>\n"
                "• Безработица и ее виды\n"
                "• Инфляция: типы и последствия\n"
                "• Антиинфляционная политика\n\n"

                "📖 <b>Лекция 10: Бюджетно-налоговая политика</b>\n"
                "• Методы государственного регулирования\n"
                "• Бюджет и налоговая система\n"
                "• Бюджетный дефицит и госдолг\n\n"

                "📖 <b>Лекция 11: Денежно-кредитная политика</b>\n"
                "• Происхождение и функции денег\n"
                "• Кредит и банковская система\n"
                "• Основы денежно-кредитной политики\n\n"

                "📖 <b>Лекция 12: Мировое хозяйство</b>\n"
                "• Формирование мирового хозяйства\n"
                "• Международная валютная система\n"
                "• Международная экономическая интеграция"
            )
            
            inline_keyboard = {
                'inline_keyboard': [
                    [{'text': '⬅️ Назад к курсу', 'callback_data': 'back_to_course'}],
                    [{'text': '🏠 Главное меню', 'callback_data': 'main_menu'}]
                ]
            }
            
            self.send_message(chat_id, content_text, inline_keyboard)
            
        except Exception as e:
            logger.error(f"Show course content error: {e}")

    def show_presentation_topics(self, chat_id):
        """Show report topics based on lecture content"""
        try:
            text = (
                "📝 <b>Темы для докладов по экономической теории:</b>\n\n"
                
                "📖 <b>Основы экономической теории:</b>\n"
                "1. 📊 Методы экономических исследований и их применение\n"
                "2. 🔄 Экономические аспекты деятельности правоохранительных органов\n"
                "3. ⚖️ Проблема ограниченности ресурсов и безграничности потребностей\n"
                "4. 📈 Кривая производственных возможностей и экономический выбор\n"
                "5. 🌍 Сравнительный анализ экономических систем современности\n\n"

                "🏛️ <b>Модели смешанной экономики:</b>\n"
                "6. Американская либеральная модель экономики\n"
                "7. Японская патриархально-корпоративная модель\n"
                "8. Шведская социально-ориентированная модель\n"
                "9. Германская модель социального рыночного хозяйства\n"
                "10. Китайская двухуровневая модель развития\n\n"

                "🏪 <b>Рыночные отношения:</b>\n"
                "11. Рыночная инфраструктура и ее роль в экономике\n"
                "12. Биржи как институты рыночной инфраструктуры\n"
                "13. Эластичность спроса и предложения: теория и практика\n"
                "14. Равновесная цена и рыночное равновесие\n"
                "15. Факторы, влияющие на спрос и предложение\n\n"

                "🏢 <b>Конкуренция и монополизм:</b>\n"
                "16. Типы рыночных структур и их характеристики\n"
                "17. Монополистическая конкуренция в современной экономике\n"
                "18. Проблемы монополизма в российской экономике\n"
                "19. Антимонопольное регулирование: опыт разных стран\n"
                "20. Естественные монополии и методы их регулирования\n\n"

                "🏭 <b>Предприятие и производство:</b>\n"
                "21. Производственная функция и ее применение\n"
                "22. Классификация издержек производства\n"
                "23. Альтернативные и бухгалтерские издержки\n"
                "24. Концепции прибыли в экономической теории\n"
                "25. Эффективность производства и пути ее повышения\n\n"

                "💼 <b>Рынки факторов производства:</b>\n"
                "26. Особенности рынка труда в России\n"
                "27. Формы и системы заработной платы\n"
                "28. Земельная рента и ее виды\n"
                "29. Рынок капитала и инвестиционная деятельность\n"
                "30. Формирование доходов в рыночной экономике\n\n"

                "🏛️ <b>Макроэкономические вопросы:</b>\n"
                "31. Система национальных счетов и ВВП\n"
                "32. Экономический рост: типы и факторы\n"
                "33. Экономические циклы и их фазы\n"
                "34. Безработица как макроэкономическая проблема\n"
                "35. Инфляция: причины, виды и последствия\n"
                "36. Государственное регулирование экономики\n"
                "37. Бюджетно-налоговая политика государства\n"
                "38. Денежно-кредитная политика и ее инструменты\n"
                "39. Банковская система в рыночной экономике\n"
                "40. Международные экономические отношения и интеграция"
            )

            self.send_message(chat_id, text, self.get_main_keyboard())
            
        except Exception as e:
            logger.error(f"Show presentation topics error: {e}")

    def show_formulas(self, chat_id):
        """Show economic formulas"""
        try:
            text = "📐 <b>Основные экономические формулы:</b>\n\n"
            formulas = {
                "Темп инфляции": "((ИПЦ_текущий - ИПЦ_базовый) / ИПЦ_базовый) × 100%",
                "Реальный ВВП": "Номинальный ВВП / Дефлятор ВВП × 100",
                "Уровень безработицы": "(Количество безработных / Рабочая сила) × 100%",
                "Реальная процентная ставка": "Номинальная ставка - Темп инфляции",
                "Темп экономического роста": "((ВВП_текущий - ВВП_прошлый) / ВВП_прошлый) × 100%",
                "Индекс цен": "(Стоимость корзины в текущих ценах / Стоимость корзины в базовых ценах) × 100",
                "Эластичность спроса": "(ΔQ/Q) / (ΔP/P)",
                "Экономическая прибыль": "Общая выручка - Экономические издержки",
                "Предельные издержки": "ΔTC / ΔQ",
                "Коэффициент Джини": "Площадь между линией равенства и кривой Лоренца"
            }

            for formula_name, formula in formulas.items():
                text += f"🔹 <b>{formula_name}</b>\n<code>{formula}</code>\n\n"

            self.send_message(chat_id, text, self.get_main_keyboard())
            
        except Exception as e:
            logger.error(f"Show formulas error: {e}")

    def show_calculator(self, chat_id):
        """Show calculator options"""
        try:
            calc_text = (
                "🧮 <b>Экономический калькулятор:</b>\n\n"
                "<b>Доступные расчеты:</b>\n\n"
                "📊 Темп инфляции\n"
                "💰 Реальная процентная ставка\n"
                "📈 Темп роста ВВП\n"
                "💼 Уровень безработицы\n\n"
                "💡 Для выполнения расчетов отправьте команду:\n"
                "<code>/calc [тип расчета] [значения]</code>\n\n"
                "<b>Примеры:</b>\n"
                "• <code>/calc inflation 100 105</code> (инфляция)\n"
                "• <code>/calc real_rate 10 3</code> (реальная ставка)\n"
                "• <code>/calc growth 1000 1100</code> (рост ВВП)\n"
                "• <code>/calc unemployment 50 1000</code> (безработица)"
            )
            self.send_message(chat_id, calc_text, self.get_main_keyboard())
            
        except Exception as e:
            logger.error(f"Show calculator error: {e}")

    def handle_calculator(self, chat_id, command_parts):
        """Handle calculator commands"""
        try:
            if len(command_parts) < 2:
                self.send_message(chat_id, "❌ Неверный формат команды. Используйте <code>/calc [тип] [значения]</code>", self.get_main_keyboard())
                return

            calc_type = command_parts[1].lower()

            if calc_type == "inflation" and len(command_parts) >= 4:
                old_value = float(command_parts[2])
                new_value = float(command_parts[3])
                if old_value <= 0:
                    raise ValueError("Старое значение должно быть больше нуля")
                inflation_rate = ((new_value - old_value) / old_value) * 100
                result = f"📊 <b>Темп инфляции:</b> {inflation_rate:.2f}%"

            elif calc_type == "real_rate" and len(command_parts) >= 4:
                nominal_rate = float(command_parts[2])
                inflation_rate = float(command_parts[3])
                real_rate = nominal_rate - inflation_rate
                result = f"💰 <b>Реальная процентная ставка:</b> {real_rate:.2f}%"

            elif calc_type == "growth" and len(command_parts) >= 4:
                old_gdp = float(command_parts[2])
                new_gdp = float(command_parts[3])
                if old_gdp <= 0:
                    raise ValueError("Старое значение ВВП должно быть больше нуля")
                growth_rate = ((new_gdp - old_gdp) / old_gdp) * 100
                result = f"📈 <b>Темп роста ВВП:</b> {growth_rate:.2f}%"

            elif calc_type == "unemployment" and len(command_parts) >= 4:
                unemployed = float(command_parts[2])
                labor_force = float(command_parts[3])
                if labor_force <= 0:
                    raise ValueError("Рабочая сила должна быть больше нуля")
                if unemployed > labor_force:
                    raise ValueError("Количество безработных не может превышать рабочую силу")
                unemployment_rate = (unemployed / labor_force) * 100
                result = f"💼 <b>Уровень безработицы:</b> {unemployment_rate:.2f}%"

            else:
                result = "❌ Неизвестный тип расчета или недостаточно параметров"

            self.send_message(chat_id, result, self.get_main_keyboard())

        except ValueError as e:
            self.send_message(chat_id, f"❌ Ошибка: {str(e)}", self.get_main_keyboard())
        except ZeroDivisionError:
            self.send_message(chat_id, "❌ Ошибка: деление на ноль", self.get_main_keyboard())
        except Exception as e:
            logger.error(f"Calculator error: {e}")
            self.send_message(chat_id, "❌ Ошибка при выполнении расчета", self.get_main_keyboard())

    def show_news(self, chat_id):
        """Show news sources"""
        try:
            news_text = (
                "📰 <b>Источники экономических новостей:</b>\n\n"
                "🔸 <b>Российские источники:</b>\n"
                "• РБК Экономика - rbc.ru/economics\n"
                "• Ведомости - vedomosti.ru\n"
                "• Коммерсантъ - kommersant.ru\n"
                "• ТАСС Экономика - tass.ru/ekonomika\n\n"
                "🔸 <b>Международные источники:</b>\n"
                "• Bloomberg - bloomberg.com\n"
                "• Financial Times - ft.com\n"
                "• Reuters Economics - reuters.com\n"
                "• The Economist - economist.com\n\n"
                "📊 Регулярно следите за экономическими новостями для понимания текущих трендов!"
            )
            self.send_message(chat_id, news_text, self.get_main_keyboard())
            
        except Exception as e:
            logger.error(f"Show news error: {e}")

    def send_help(self, chat_id):
        """Send help message"""
        try:
            help_text = (
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
                "💡 <b>Как пользоваться:</b>\n"
                "• Используйте кнопки меню для навигации\n"
                "• В викторине отвечайте кнопками А, Б или В\n"
                "• Следите за таймером - у каждого вопроса есть лимит времени\n"
                "• Результаты автоматически сохраняются в статистике\n"
                "• Выбирайте подходящий уровень сложности или тему\n\n"
                "<b>Команды:</b>\n"
                "/start - начать работу с ботом\n"
                "/help - показать эту помощь\n"
                "/calc - экономический калькулятор"
            )
            self.send_message(chat_id, help_text, self.get_main_keyboard())
            
        except Exception as e:
            logger.error(f"Send help error: {e}")

    def send_start(self, chat_id, username):
        """Send start message"""
        try:
            user_name = username or "друг"
            welcome_text = (
                f"👋 Привет, <b>{user_name}</b>! Добро пожаловать в экономическую викторину!\n\n"
                f"🧠 Проверьте свои знания в области экономики\n"
                f"📊 Отслеживайте свою статистику и прогресс\n"
                f"🏆 Соревнуйтесь с другими участниками\n"
                f"🎯 Выбирайте подходящий уровень сложности или изучайте по темам\n"
                f"🎮 Играйте в быстрые игры или проходите полные сессии\n"
                f"⏰ Отвечайте быстро - время ограничено!\n\n"
                f"Бот основан на полном курсе лекций по экономической теории!\n\n"
                f"Используйте кнопки ниже для навигации по функциям бота!"
            )
            self.send_message(chat_id, welcome_text, self.get_main_keyboard())
            
        except Exception as e:
            logger.error(f"Send start error: {e}")

    def handle_callback_query(self, callback_query):
        """Handle callback query (inline keyboard buttons)"""
        try:
            query_id = callback_query['id']
            chat_id = callback_query['message']['chat']['id']
            data = callback_query['data']
            username = callback_query['from'].get('first_name', '')

            # Answer callback query
            try:
                answer_url = f"{self.api_url}/answerCallbackQuery"
                answer_data = urllib.parse.urlencode({'callback_query_id': query_id}).encode('utf-8')
                urllib.request.urlopen(urllib.request.Request(answer_url, data=answer_data), timeout=5)
            except:
                pass

            if data.startswith('quiz_'):
                answer = data.replace('quiz_', '')
                self.check_quiz_answer(chat_id, username, answer)
                return

            elif data.startswith('difficulty_'):
                difficulty = data.replace('difficulty_', '')
                self.start_quiz_with_difficulty(chat_id, difficulty)
                return

            elif data.startswith('topic_'):
                topic_index = int(data.replace('topic_', ''))
                self.start_topic_quiz(chat_id, topic_index)
                return

            elif data.startswith('lecture_'):
                lecture_num = int(data.replace('lecture_', ''))
                self.show_lecture_content(chat_id, lecture_num)
                return

            elif data == 'course_content':
                self.show_course_content(chat_id)
                return
            elif data == 'back_to_course':
                self.show_course(chat_id)
                return
            elif data == 'main_menu':
                self.send_message(chat_id, "🏠 Главное меню", self.get_main_keyboard())
                return

            elif data == 'mode_quick':
                self.start_quick_game(chat_id)
                return
            elif data == 'mode_single':
                self.start_single_question(chat_id)
                return
            elif data == 'mode_topics':
                self.show_topic_selection(chat_id)
                return
            elif data == 'back_to_main_quiz':
                self.quiz_question(chat_id)
                return
                
        except Exception as e:
            logger.error(f"Callback query error: {e}")

    def handle_message(self, chat_id, text, username):
        """Handle incoming message"""
        try:
            if self.check_quiz_answer(chat_id, username, text):
                return

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
            elif text == "/quick":
                self.start_quick_game(chat_id)
            elif text == "/single":
                self.start_single_question(chat_id)
            elif text.startswith("/calc"):
                command_parts = text.split()
                self.handle_calculator(chat_id, command_parts)
            else:
                self.send_message(
                    chat_id,
                    "🤔 Не понимаю команду. Используйте кнопки меню или /help для получения помощи.",
                    self.get_main_keyboard()
                )
                
        except Exception as e:
            logger.error(f"Handle message error: {e}")
    # Полная реализация всех методов здесь

# Создаем экземпляр бота
bot = TelegramBot(TOKEN)

# Создаем Flask приложение
app = Flask(__name__)

@app.route('/')
def home():
    return "Экономический бот работает! Используйте /set_webhook для настройки"

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    """Установка вебхука"""
    try:
        # Получаем URL вебхука из переменных окружения fly.io
        fly_app_name = os.getenv('FLY_APP_NAME')
        if not fly_app_name:
            return jsonify({'status': 'error', 'message': 'FLY_APP_NAME not set'}), 400
            
        webhook_url = f'https://{fly_app_name}.fly.dev/webhook'
        
        # Устанавливаем вебхук
        set_webhook_url = f'https://api.telegram.org/bot{TOKEN}/setWebhook'
        params = {'url': webhook_url}
        data = urllib.parse.urlencode(params).encode('utf-8')
        
        req = urllib.request.Request(set_webhook_url, data=data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('ok'):
                logger.info(f"Webhook установлен: {webhook_url}")
                return jsonify({'status': 'success', 'url': webhook_url}), 200
            else:
                logger.error(f"Ошибка установки webhook: {result.get('description')}")
                return jsonify({'status': 'error', 'message': result.get('description')}), 500
                
    except Exception as e:
        logger.error(f"Ошибка при установке webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработка входящих обновлений от Telegram"""
    try:
        update = request.json
        logger.info(f"Received update: {update}")
        
        # Обработка сообщений
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            username = message.get('from', {}).get('first_name', '')
            bot.handle_message(chat_id, text, username)
            
        # Обработка callback-запросов
        elif 'callback_query' in update:
            bot.handle_callback_query(update['callback_query'])
            
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Ошибка обработки обновления: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'ok', 'message': 'Bot is running'}), 200

def run_polling():
    """Режим поллинга для локальной разработки"""
    offset = 0
    consecutive_errors = 0
    max_consecutive_errors = 10
    base_retry_delay = 5
    max_retry_delay = 120
    last_heartbeat = time.time()
    last_cleanup = time.time()

    logger.info("🔄 Запуск в режиме поллинга...")
    logger.info("💡 Для остановки нажмите Ctrl+C")

    while bot.running:
        try:
            url = f"{bot.api_url}/getUpdates?offset={offset}&timeout=30"
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'TelegramBot/1.0')

            with urllib.request.urlopen(request, timeout=35) as response:
                data = json.loads(response.read().decode('utf-8'))

            if data['ok']:
                consecutive_errors = 0
                for update in data['result']:
                    offset = update['update_id'] + 1

                    try:
                        if 'message' in update:
                            message = update['message']
                            chat_id = message['chat']['id']
                            text = message.get('text', '')
                            username = message.get('from', {}).get('first_name', '')

                            bot.handle_message(chat_id, text, username)

                        elif 'callback_query' in update:
                            bot.handle_callback_query(update['callback_query'])
                    except Exception as e:
                        logger.error(f"Error processing update: {e}")
                        continue

            else:
                logger.error(f"API error: {data.get('description', 'Unknown error')}")
                consecutive_errors += 1

        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Error: {e}")
            retry_delay = min(base_retry_delay * (2 ** min(consecutive_errors, 5)), max_retry_delay)
            time.sleep(retry_delay)

        # Cleanup old states every 5 minutes
        current_time = time.time()
        if current_time - last_cleanup > 300:
            bot.cleanup_old_states()
            last_cleanup = current_time

        time.sleep(1)

if __name__ == "__main__":
    if not TOKEN:
        logger.error("Ошибка: Не найден токен бота!")
        logger.error("📝 Добавьте TELEGRAM_BOT_TOKEN в Secrets:")
        logger.error("1. Откройте вкладку Secrets (🔒)")
        logger.error("2. Добавьте ключ: TELEGRAM_BOT_TOKEN")
        logger.error("3. Вставьте токен от @BotFather")
        logger.error("4. Нажмите кнопку Run для перезапуска")
        exit(1)

    logger.info("🤖 Запуск экономического викторина-бота...")
    
    # Проверка подключения к Telegram API
    try:
        with urllib.request.urlopen(f"{bot.api_url}/getMe", timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        if data['ok']:
            logger.info(f"✅ Бот подключен: @{data['result']['username']}")
            logger.info(f"📝 Имя бота: {data['result']['first_name']}")
        else:
            logger.error("Ошибка подключения к боту")
            exit(1)

        # Очистка ожидающих обновлений
        try:
            clear_url = f"{bot.api_url}/getUpdates?offset=-1"
            urllib.request.urlopen(clear_url, timeout=5)
            logger.info("🧹 Очищены ожидающие обновления")
        except:
            pass

    except Exception as e:
        logger.error(f"Ошибка подключения: {e}")
        exit(1)
    

        
        # ---------- AIOHTTP health server for Fly.io ----------
async def handle_health(request):
    return web.Response(text="OK")

def start_health_server():
    app = web.Application()
    app.router.add_get("/health", handle_health)
    # run forever (blocks) in its own thread
    web.run_app(app, host="0.0.0.0", port=8080)

# ---------- Startup routine ----------
def build_bot_application(token: str) -> Application:
    app = Application.builder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))

    # CallbackQuery handlers
    app.add_handler(CallbackQueryHandler(callback_quiz_menu, pattern="^quiz_menu$"))
    app.add_handler(CallbackQueryHandler(callback_mode_start, pattern="^mode_"))
    app.add_handler(CallbackQueryHandler(callback_topic_select, pattern="^topic_"))
    app.add_handler(CallbackQueryHandler(callback_answer, pattern="^answer_"))
    app.add_handler(CallbackQueryHandler(callback_lectures_menu, pattern="^lectures$"))
    app.add_handler(CallbackQueryHandler(callback_show_lecture, pattern=r"^lecture_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(callback_show_stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(callback_leaderboard, pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(callback_help, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(callback_back_main, pattern="^back_main$"))

    # Shortcuts for some specific named patterns
    app.add_handler(CallbackQueryHandler(callback_mode_start, pattern="^mode_quick$"))
    app.add_handler(CallbackQueryHandler(callback_mode_start, pattern="^mode_easy$"))
    app.add_handler(CallbackQueryHandler(callback_mode_start, pattern="^mode_medium$"))
    app.add_handler(CallbackQueryHandler(callback_mode_start, pattern="^mode_hard$"))
    app.add_handler(CallbackQueryHandler(callback_mode_start, pattern="^mode_single$"))
    app.add_handler(CallbackQueryHandler(callback_quiz_menu, pattern="^back_main$"))

    return app

# ---------- Main ----------
def main():
    global lectures, quiz_questions

    # Load lectures
    lectures = load_lectures_from_file(LECTURE_FILE)
    # Generate quiz questions
    quiz_questions = make_quiz_questions_from_lectures(lectures)

    TOKEN = os.getenv(TELEGRAM_TOKEN_ENV)
    if not TOKEN:
        raise RuntimeError(f"Telegram token not found. Set env {TELEGRAM_TOKEN_ENV}")

    # start health server thread for Fly
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()
    logger.info("Started health server on :8080")

    # build bot and start polling
    app = build_bot_application(TOKEN)
    logger.info("Starting Telegram bot (polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()
