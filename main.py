#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
main.py
Telegram bot with:
 - lectures loaded from lecture.txt
 - automatic question generation from lecture headings
 - quiz with timers, per-user state, leaderboard & stats
 - simple aiohttp health endpoint for Fly.io smoke checks on :8080
"""

import os
import logging
import asyncio
import random
import time
import threading
import html
from typing import Dict, List, Any, Optional
from aiohttp import web

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- Globals ----------
LECTURE_FILE = "lecture.txt"
TELEGRAM_TOKEN_ENV = "TELEGRAM_TOKEN"   # set this in fly secrets / env
# Per-chat states and scores (kept in-memory)
user_states: Dict[int, Dict[str, Any]] = {}
user_scores: Dict[int, Dict[str, Any]] = {}
lectures: Dict[int, Dict[str, Any]] = {}
quiz_questions: List[Dict[str, Any]] = []

# ---------- Async Timer Manager (works with asyncio loop) ----------
class AsyncTimerManager:
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}

    async def _task(self, key: str, delay: float, coro, *args):
        try:
            await asyncio.sleep(delay)
            await coro(*args)
        except asyncio.CancelledError:
            # normal cancellation
            return
        except Exception as e:
            logger.exception("Timer task error: %s", e)
        finally:
            self.tasks.pop(key, None)

    def set_timer(self, key: str, delay: float, coro, *args):
        # cancel previous if exists
        self.cancel_timer(key)
        # schedule
        task = asyncio.create_task(self._task(key, delay, coro, *args))
        self.tasks[key] = task

    def cancel_timer(self, key: str):
        t = self.tasks.pop(key, None)
        if t and not t.done():
            t.cancel()

timer_manager = AsyncTimerManager()

# ---------- Lecture loader & question generator ----------
def load_lectures_from_file(filename: str = LECTURE_FILE) -> Dict[int, Dict[str, Any]]:
    """
    Parse lecture.txt into lectures dict:
    - file uses headings like "Лекция N. Title" and lines 'Вопрос X. ...'
    - we split file by 'Лекция' markers and collect sections & question headings
    """
    if not os.path.exists(filename):
        logger.warning("Lecture file %s not found", filename)
        return {}

    raw = open(filename, "r", encoding="utf-8").read()
    # Normalize newlines
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")

    lectures_out: Dict[int, Dict[str, Any]] = {}

    # Attempt simple parsing:
    # Find occurrences of "Лекция <num>." and split
    import re
    lec_pattern = re.compile(r"(Лекция\s+(\d+)\.\s*(.+))", re.IGNORECASE)
    matches = list(lec_pattern.finditer(raw))
    # if no matches, fallback: consider whole file as lecture 1
    if not matches:
        logger.warning("No lecture headers found, treating whole file as single lecture")
        lectures_out[1] = {
            "id": 1,
            "title": "Курс (отсутствуют заголовки)",
            "raw": raw,
            "questions_raw": []
        }
        return lectures_out

    # For each match, collect content until next match
    for i, m in enumerate(matches):
        header_full = m.group(1)
        num = int(m.group(2))
        title = m.group(3).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        block = raw[start:end].strip()

        # Extract question headings inside block: lines that start with "Вопрос"
        qlines = []
        for line in block.splitlines():
            line = line.strip()
            if line.startswith("Вопрос"):
                # e.g. "Вопрос 1. Предмет и метод экономической науки"
                qlines.append(line)
        lectures_out[num] = {
            "id": num,
            "title": title,
            "raw": block,
            "questions_raw": qlines
        }

    logger.info("Loaded %d lectures from %s", len(lectures_out), filename)
    return lectures_out

def make_quiz_questions_from_lectures(lectures_dict: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    For each lecture and each 'Вопрос ...' create a multiple-choice question:
    - question text: the heading (without "Вопрос N.")
    - correct answer: try to find the first sentence in the lecture raw text that seems to follow that heading,
      else use a short extract from the lecture intro or the lecture title
    - distractors: create 2 plausible distractors by sampling other lecture extracts or generic templates
    """
    import re
    questions: List[Dict[str, Any]] = []
    # collect candidate answer snippets from lecture texts: sentences
    sentence_re = re.compile(r"([А-ЯЁ][^\.!?]{20,200}[\.!?])", re.M)
    answer_pool = []
    for lec in lectures_dict.values():
        for s in sentence_re.findall(lec["raw"]):
            clean = " ".join(s.strip().split())
            if len(clean) > 40:
                answer_pool.append(clean)

    if not answer_pool:
        # fallback: use lecture titles
        for lec in lectures_dict.values():
            answer_pool.append(lec["title"])

    # Now build questions
    for lec_id, lec in lectures_dict.items():
        for qline in lec["questions_raw"]:
            # qline: "Вопрос 1. Предмет и метод экономической науки"
            # extract text after the dot
            parts = qline.split(".", 1)
            qtext = parts[1].strip() if len(parts) > 1 else qline

            # find candidate correct answer: search for qtext snippet in lec['raw']
            correct = None
            found_idx = lec["raw"].find(qtext)
            if found_idx != -1:
                # take substring after qtext up to next sentence.
                sub = lec["raw"][found_idx + len(qtext):]
                # find first sentence
                m = sentence_re.search(sub)
                if m:
                    correct = " ".join(m.group(1).strip().split())
            if not correct:
                # fallback: use first long sentence from that lecture
                for s in sentence_re.findall(lec["raw"]):
                    candid = " ".join(s.strip().split())
                    if len(candid) > 60:
                        correct = candid
                        break
            if not correct:
                # fallback to lecture title
                correct = lec["title"]

            # pick two distractors from answer_pool (not equal to correct)
            distractors = []
            tries = 0
            while len(distractors) < 2 and tries < 30:
                cand = random.choice(answer_pool)
                if cand != correct and cand not in distractors:
                    # shorten distractor to single sentence (if long)
                    distractors.append(cand if len(cand) <= 200 else cand[:197] + "...")
                tries += 1
            # If still not enough, make generic distractors
            while len(distractors) < 2:
                distractors.append("См. соответствующий раздел лекции")

            # Assemble options and shuffle
            options = [correct] + distractors
            random.shuffle(options)
            # find which option is correct letter
            correct_letter = "А"
            letters = ["А", "Б", "В", "Г"]
            # map options to letters; ensure at most 3 options
            options = options[:3]
            correct_index = options.index(correct)
            correct_letter = letters[correct_index]

            question = {
                "lecture_id": lec_id,
                "topic": lec["title"],
                "question": qtext,
                "options": [f"{letters[i]}) {options[i]}" for i in range(len(options))],
                "answer": correct_letter,
                "difficulty": "medium",
                "time_limit": 30
            }
            questions.append(question)

    logger.info("Generated %d quiz questions from lectures", len(questions))
    return questions

# ---------- Keyboards ----------
def get_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🖋️ Проверь себя", callback_data="quiz_menu")],
        [InlineKeyboardButton("📚 Курс лекций", callback_data="lectures")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats"), InlineKeyboardButton("🏆 Рейтинг", callback_data="leaderboard")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------- Helpers for formatting ----------
def format_question_text_for_user(question: Dict[str, Any], idx: int, total: int, time_limit: int, show_time=True) -> str:
    emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(question.get("difficulty"), "⚪")
    text = f"🎯 Вопрос {idx}/{total} {emoji}\n\n"
    text += f"📚 Тема: <b>{html.escape(question.get('topic',''))}</b>\n\n"
    text += f"🧠 <b>{html.escape(question['question'])}</b>\n\n"
    for opt in question["options"]:
        # options already contain letters "А) ...", ensure safe html
        text += f"{html.escape(opt)}\n\n"
    if show_time:
        text += f"⏰ У вас есть <b>{time_limit}</b> секунд на ответ."
    return text

def build_answer_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("А", callback_data="answer_A"),
        InlineKeyboardButton("Б", callback_data="answer_B"),
        InlineKeyboardButton("В", callback_data="answer_C")
    ]])

# ---------- Quiz flow (async) ----------
async def start_quiz_for_user(chat_id: int, bot, questions: List[Dict[str, Any]]):
    """
    Store state and start asking first question
    """
    if not questions:
        await bot.send_message(chat_id=chat_id, text="❌ Вопросы не найдены для выбранного режима", reply_markup=get_main_keyboard())
        return

    user_states[chat_id] = {
        "mode": "quiz_session",
        "questions": questions,
        "current_index": 0,
        "correct_answers": 0,
        "answered": False,
        "start_time": time.time()
    }
    await ask_next_question(chat_id, bot)

async def ask_next_question(chat_id: int, bot):
    state = user_states.get(chat_id)
    if not state:
        return
    if state["current_index"] >= len(state["questions"]):
        await finish_quiz(chat_id, bot)
        return

    q = state["questions"][state["current_index"]]
    state["current_question"] = q
    state["answered"] = False
    state["start_time_question"] = time.time()

    text = format_question_text_for_user(q, state["current_index"] + 1, len(state["questions"]), q["time_limit"])
    sent = await bot.send_message(chat_id=chat_id, text=text, reply_markup=build_answer_keyboard(), parse_mode="HTML")
    state["last_message_id"] = sent.message_id

    # set timer
    timer_manager.set_timer(f"timeout_{chat_id}", q["time_limit"], handle_timeout, chat_id, bot)

async def handle_timeout(chat_id: int, bot):
    """
    Called when user didn't answer in time.
    """
    state = user_states.get(chat_id)
    if not state:
        return
    if state.get("answered"):
        return
    state["answered"] = True

    q = state.get("current_question")
    if not q:
        return

    # Update score
    sc = user_scores.setdefault(chat_id, {"name": "Аноним", "correct": 0, "total": 0})
    sc["total"] += 1

    result_text = f"⏰ Время вышло! Правильный ответ: <b>{q['answer']}</b>"
    text = format_question_text_for_user(q, state["current_index"] + 1, len(state["questions"]), q["time_limit"], show_time=False)
    text += f"\n\n{result_text}"

    # edit message if possible
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=state.get("last_message_id"), text=text, parse_mode="HTML")
    except Exception as e:
        logger.debug("Couldn't edit message on timeout: %s", e)

    # proceed to next question after short pause
    state["current_index"] += 1
    await asyncio.sleep(1.5)
    await ask_next_question(chat_id, bot)

# ---------- Handlers ----------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "Аноним"
    await update.message.reply_text(f"🚀 Привет, {name}!\nЭтот бот содержит курс лекций и викторину по экономической теории.", reply_markup=get_main_keyboard())

async def callback_quiz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🎮 Быстрая игра (5)", callback_data="mode_quick")],
        [InlineKeyboardButton("🟢 Легкий (10)", callback_data="mode_easy"), InlineKeyboardButton("🟡 Средний (15)", callback_data="mode_medium")],
        [InlineKeyboardButton("🔴 Сложный (20)", callback_data="mode_hard")],
        [InlineKeyboardButton("📚 По темам", callback_data="mode_topics")],
        [InlineKeyboardButton("🔀 Случайный вопрос", callback_data="mode_single")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_main")]
    ]
    await query.edit_message_text("🖋️ Выберите режим викторины:", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_mode_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode = query.data  # e.g. mode_quick
    chat_id = query.message.chat_id

    # choose questions according to mode
    if mode == "mode_quick":
        pool = quiz_questions
        qlist = random.sample(pool, min(5, len(pool)))
        await start_quiz_for_user(chat_id, context.bot, qlist)
    elif mode == "mode_easy":
        pool = [q for q in quiz_questions if q.get("difficulty") == "easy" or q.get("difficulty") == "medium"]
        if not pool:
            pool = quiz_questions
        qlist = random.sample(pool, min(10, len(pool)))
        await start_quiz_for_user(chat_id, context.bot, qlist)
    elif mode == "mode_medium":
        pool = [q for q in quiz_questions if q.get("difficulty") in ("medium","hard")]
        if not pool:
            pool = quiz_questions
        qlist = random.sample(pool, min(15, len(pool)))
        await start_quiz_for_user(chat_id, context.bot, qlist)
    elif mode == "mode_hard":
        pool = [q for q in quiz_questions if q.get("difficulty") == "hard"]
        if not pool:
            pool = quiz_questions
        qlist = random.sample(pool, min(20, len(pool)))
        await start_quiz_for_user(chat_id, context.bot, qlist)
    elif mode == "mode_single":
        q = random.choice(quiz_questions) if quiz_questions else None
        if q:
            await start_quiz_for_user(chat_id, context.bot, [q])
        else:
            await query.edit_message_text("Вопросы пока недоступны.", reply_markup=get_main_keyboard())
    elif mode == "mode_topics":
        # show topics list
        topics = sorted({q.get("topic","Без темы") for q in quiz_questions})
        keyboard = []
        for i, t in enumerate(topics, start=1):
            keyboard.append([InlineKeyboardButton(f"{i}. {t}", callback_data=f"topic_{i-1}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="quiz_menu")])
        await query.edit_message_text("📚 Выберите тему:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text("Неизвестный режим.", reply_markup=get_main_keyboard())

async def callback_topic_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.split("_",1)[1])
    topics = sorted({q.get("topic","Без темы") for q in quiz_questions})
    if idx < 0 or idx >= len(topics):
        await query.edit_message_text("Тема не найдена", reply_markup=get_main_keyboard())
        return
    selected = topics[idx]
    pool = [q for q in quiz_questions if q.get("topic")==selected]
    if not pool:
        await query.edit_message_text("Вопросы по теме не найдены", reply_markup=get_main_keyboard())
        return
    qlist = random.sample(pool, min(15, len(pool)))
    await start_quiz_for_user(query.message.chat_id, context.bot, qlist)

async def callback_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles user's answer button presses (А/Б/В)
    """
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user = query.from_user
    if chat_id not in user_states:
        # maybe session expired
        await query.edit_message_text("Сессия не найдена или истекла. Начните заново.", reply_markup=get_main_keyboard())
        return

    state = user_states[chat_id]
    if state.get("answered"):
        # already answered
        return

    # cancel timer
    timer_manager.cancel_timer(f"timeout_{chat_id}")
    state["answered"] = True

    user_choice = query.data.replace("answer_", "")
    q = state.get("current_question")
    if not q:
        await query.edit_message_text("Ошибка: вопрос не найден.", reply_markup=get_main_keyboard())
        return

    is_correct = (user_choice == q["answer"])
    # update stats
    sc = user_scores.setdefault(chat_id, {"name": user.first_name or "Аноним", "correct": 0, "total": 0})
    sc["total"] += 1
    if is_correct:
        sc["correct"] += 1
        state["correct_answers"] = state.get("correct_answers", 0) + 1

    # compute response time
    rt = time.time() - state.get("start_time_question", time.time())
    bonus = ""
    if rt <= q["time_limit"] * 0.5:
        bonus = " ⚡ Быстрый ответ!"

    if is_correct:
        res_text = f"✅ <b>Правильно!</b>{bonus}\n⏱️ Время: {rt:.1f}s"
    else:
        res_text = f"❌ <b>Неверно.</b> Правильный ответ: <b>{q['answer']}</b>\n⏱️ Время: {rt:.1f}s"

    # try to edit message to show result
    try:
        await query.edit_message_text(res_text, parse_mode="HTML")
    except Exception as e:
        logger.debug("Unable to edit message with result: %s", e)
        # fallback send new message
        await context.bot.send_message(chat_id=chat_id, text=res_text, parse_mode="HTML")

    # move to next question after short pause
    state["current_index"] += 1
    await asyncio.sleep(1.2)
    await ask_next_question(chat_id, context.bot)

# ---------- Lectures handlers ----------
async def callback_lectures_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not lectures:
        await query.edit_message_text("❌ Лекции пока недоступны", reply_markup=get_main_keyboard())
        return
    keyboard = []
    for lid, lec in sorted(lectures.items()):
        keyboard.append([InlineKeyboardButton(f"📖 Лекция {lid}. {lec['title']}", callback_data=f"lecture_{lid}_0")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_main")])
    await query.edit_message_text("📚 Курс лекций — выберите лекцию:", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_show_lecture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # callback format: lecture_<id>_<section_index>
    try:
        _, lid_s, sec_s = query.data.split("_")
        lid = int(lid_s)
        sec = int(sec_s)
    except Exception:
        await query.edit_message_text("Неверные данные лекции")
        return
    lec = lectures.get(lid)
    if not lec:
        await query.edit_message_text("Лекция не найдена")
        return

    # Prepare content: try to split lecture raw text to sections by lines "Вопрос" or double newlines
    parts = []
    raw = lec.get("raw", "").strip()
    # split by occurrences of "Вопрос" to create sections
    import re
    split_parts = re.split(r"(?:\n\s*\n)+", raw)
    # fallback: if no parts, use the raw text as single part
    if not split_parts:
        split_parts = [raw]

    # Now clamp section index
    if sec < 0: sec = 0
    if sec >= len(split_parts):
        sec = len(split_parts) - 1

    section_text = split_parts[sec].strip()
    header = f"📖 <b>Лекция {lid}. {lec['title']}</b>\n\n"
    message_text = header + (section_text if section_text else "Содержимое секции пусто.")
    # Build navigation
    nav = []
    if sec > 0:
        nav.append(InlineKeyboardButton("⬅️ Предыдущая", callback_data=f"lecture_{lid}_{sec-1}"))
    if sec < len(split_parts) - 1:
        nav.append(InlineKeyboardButton("Следующая ➡️", callback_data=f"lecture_{lid}_{sec+1}"))
    kb = []
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton("📚 К списку лекций", callback_data="lectures")])
    kb.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_main")])
    await query.edit_message_text(message_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ---------- Stats & leaderboard ----------
async def callback_show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    sc = user_scores.get(chat_id)
    if not sc:
        await query.edit_message_text("📊 У вас пока нет статистики", reply_markup=get_main_keyboard())
        return
    perc = (sc["correct"] / max(sc["total"], 1)) * 100
    text = (f"📊 <b>Ваша статистика</b>\n\n"
            f"👤 {sc.get('name','Аноним')}\n"
            f"✅ Правильных: {sc['correct']}\n"
            f"📝 Всего: {sc['total']}\n"
            f"📈 Процент: {perc:.1f}%")
    await query.edit_message_text(text, reply_markup=get_main_keyboard(), parse_mode="HTML")

async def callback_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not user_scores:
        await query.edit_message_text("🏆 Рейтинг пуст", reply_markup=get_main_keyboard())
        return
    # sort by accuracy and correct count
    sorted_users = sorted(user_scores.items(), key=lambda kv: ((kv[1]["correct"] / max(kv[1]["total"],1)), kv[1]["correct"]), reverse=True)
    text = "🏆 <b>Топ игроков</b>\n\n"
    for i, (uid, sc) in enumerate(sorted_users[:10], start=1):
        perc = (sc["correct"] / max(sc["total"], 1)) * 100
        text += f"{i}. {html.escape(sc.get('name','Аноним'))} — {perc:.1f}% ({sc['correct']}/{sc['total']})\n"
    await query.edit_message_text(text, reply_markup=get_main_keyboard(), parse_mode="HTML")

# ---------- Misc handlers ----------
async def callback_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "❓ <b>Помощь</b>\n\n"
        "• /start — перезапустить бота\n"
        "• Кнопки меню — навигация\n"
        "• Викторина: выбирай режим и отвечай кнопками А/Б/В\n"
        "• Лекции: выбирай лекцию и листай разделы\n\n"
        "Если что-то сломалось — пришли лог ошибок."
    )
    await query.edit_message_text(text, reply_markup=get_main_keyboard(), parse_mode="HTML")

async def callback_back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🏠 Главное меню", reply_markup=get_main_keyboard())

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
