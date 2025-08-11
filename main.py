#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
from flask import Flask, request, jsonify  # Оставил импорт на случай, если понадобится вебхук

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Ensure UTF-8 output
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    # Some Python builds may not have reconfigure — ignore if not available
    pass

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

# State management with cleanup
user_states = {}
user_scores = {}

# ====== Полный список вопросов (взято из твоего файла) ======
quiz_questions = [
    # Лекция 1
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

    # Лекция 2
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

    # Лекция 3
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

    # Лекция 4
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

    # Лекция 5
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

    # Лекция 6
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

    # Лекция 7
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

    # Лекция 8
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

    # Лекция 9
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

    # Лекция 10
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

    # Лекция 11
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

    # Лекция 12
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

# ====== Таймеры для вопросов и сессий ======
class TimerManager:
    """Улучшенный менеджер таймеров"""
    def __init__(self):
        self.timers = {}
        self.lock = threading.Lock()
    
    def set_timer(self, key, delay, callback, *args):
        """Установить таймер с автоматической очисткой"""
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
        """Отменить таймер"""
        with self.lock:
            if key in self.timers:
                try:
                    self.timers[key].cancel()
                except Exception:
                    pass
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

# ====== Класс бота ======
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
            for chat_id, state in list(user_states.items()):
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
                    [{'text': '📖 Лекция 3: Рынок и рыночный механизм', 'callback_data':
