"""
Telegram-бот для вступления в женский клуб КЕБШ "Любины подружки"
Зависимости: pip install python-telegram-bot==21.9
Запуск: python kebsh_bot.py
"""

import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)

# ─── Настройки ───────────────────────────────────────────────────────────────

import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
CHANNEL_URL = "https://t.me/poidemvmesteru"

# ─── Состояния диалога ───────────────────────────────────────────────────────

KNOWS_LYUBA, EXPECTATIONS, NAME, PHONE, EMAIL, SUBSCRIBE = range(6)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Варианты ожиданий
EXPECTATIONS_OPTIONS = {
    "exp_offline":        "🤝 Оффлайн встречи",
    "exp_online_support": "💌 Онлайн рекомендации и поддержка",
    "exp_online_meet":    "💻 Онлайн встречи",
    "exp_gifts":          "🎁 Секретные подарки и бонусы",
}


# ─── Вспомогательные функции ─────────────────────────────────────────────────

def build_expectations_keyboard(selected: set) -> InlineKeyboardMarkup:
    """Строит клавиатуру с отметками выбранных пунктов."""
    keyboard = []
    for key, label in EXPECTATIONS_OPTIONS.items():
        check = "✅ " if key in selected else ""
        keyboard.append([InlineKeyboardButton(f"{check}{label}", callback_data=key)])
    keyboard.append([InlineKeyboardButton("➡️ Готово", callback_data="exp_done")])
    return InlineKeyboardMarkup(keyboard)


def format_phone(raw: str) -> str:
    """Приводит телефон к формату +7 (999) 999-99-99."""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("7") and len(digits) == 11:
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    return raw


def is_valid_phone(raw: str) -> bool:
    """Проверяет, что введён российский номер (10–11 цифр)."""
    digits = re.sub(r"\D", "", raw)
    return len(digits) in (10, 11)


def is_valid_email(email: str) -> bool:
    """Простая проверка формата email."""
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


def build_data_summary(data: dict) -> str:
    """Собирает анкету в читаемый текст для администратора."""
    expectations = data.get("expectations", set())
    exp_text = ", ".join(
        EXPECTATIONS_OPTIONS[k].split(" ", 1)[1]
        for k in expectations
    ) if expectations else "—"

    return (
        "🌸 <b>Новая заявка в клуб «Любины подружки»</b>\n\n"
        f"👤 <b>Имя:</b> {data.get('name', '—')}\n"
        f"📞 <b>Телефон:</b> {data.get('phone', '—')}\n"
        f"📧 <b>Почта:</b> {data.get('email', '—')}\n"
        f"💜 <b>Знакома с Любой:</b> {data.get('knows_lyuba', '—')}\n"
        f"✨ <b>Ожидания:</b> {exp_text}\n"
        f"🆔 <b>Telegram ID:</b> <code>{data.get('user_id', '—')}</code>\n"
        f"🔗 <b>Username:</b> @{data.get('username', 'нет')}"
    )


# ─── Обработчики ─────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Приветствие и первый вопрос."""
    context.user_data.clear()
    context.user_data["user_id"] = update.effective_user.id
    context.user_data["username"] = update.effective_user.username or ""
    context.user_data["expectations"] = set()

    welcome_text = (
        "🌸 <b>Добро пожаловать в женский клуб КЕБШ «Любины подружки»</b>\n\n"
        "Это пространство, где можно быть собой — громкой, уставшей, смешной, "
        "красивой и настоящей. 💜\n\n"
        "Ответьте на пару вопросов, и после проверки мы пришлём ссылку в закрытую группу."
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML")

    keyboard = [
        [InlineKeyboardButton("✅ Да", callback_data="knows_yes")],
        [InlineKeyboardButton("❌ Нет", callback_data="knows_no")],
    ]
    await update.message.reply_text(
        "💬 <b>Знакомы ли вы лично с Любой?</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    return KNOWS_LYUBA


async def knows_lyuba_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ответ о знакомстве с Любой."""
    query = update.callback_query
    await query.answer()

    answer = "Да" if query.data == "knows_yes" else "Нет"
    context.user_data["knows_lyuba"] = answer
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"Ответ принят: <b>{answer}</b>", parse_mode="HTML")

    context.user_data["expectations"] = set()
    await query.message.reply_text(
        "✨ <b>Что вы ждёте от участия в клубе?</b>\n"
        "<i>Можно выбрать несколько вариантов, затем нажмите «Готово»</i>",
        reply_markup=build_expectations_keyboard(set()),
        parse_mode="HTML"
    )
    return EXPECTATIONS


async def expectations_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор ожиданий — мультиселект."""
    query = update.callback_query
    await query.answer()

    if query.data == "exp_done":
        selected = context.user_data.get("expectations", set())
        if not selected:
            await query.answer("Выберите хотя бы один вариант!", show_alert=True)
            return EXPECTATIONS

        exp_text = "\n".join(f"• {EXPECTATIONS_OPTIONS[k]}" for k in selected)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"Выбрано:\n{exp_text}", parse_mode="HTML")
        await query.message.reply_text(
            "👤 <b>Как вас зовут?</b>\nНапишите своё имя (или имя и фамилию).",
            parse_mode="HTML"
        )
        return NAME

    # Переключаем выбор пункта
    selected = context.user_data.get("expectations", set())
    if query.data in selected:
        selected.discard(query.data)
    else:
        selected.add(query.data)
    context.user_data["expectations"] = selected

    await query.edit_message_reply_markup(
        reply_markup=build_expectations_keyboard(selected)
    )
    return EXPECTATIONS


async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает имя пользователя."""
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        "📞 <b>Ваш номер телефона</b>\n"
        "Введите в формате: <code>+7 999 999-99-99</code> или <code>89991234567</code>",
        parse_mode="HTML"
    )
    return PHONE


async def phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает и валидирует телефон."""
    raw = update.message.text.strip()

    if not is_valid_phone(raw):
        await update.message.reply_text(
            "⚠️ Номер не распознан. Введите российский номер, например:\n"
            "<code>+7 999 123-45-67</code> или <code>89991234567</code>",
            parse_mode="HTML"
        )
        return PHONE

    context.user_data["phone"] = format_phone(raw)
    await update.message.reply_text(
        "📧 <b>Ваша электронная почта</b>\n"
        "Введите адрес в формате: <code>name@example.com</code>",
        parse_mode="HTML"
    )
    return EMAIL


async def email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает и валидирует email, затем предлагает подписаться на канал."""
    raw = update.message.text.strip()

    if not is_valid_email(raw):
        await update.message.reply_text(
            "⚠️ Адрес не похож на email. Убедитесь, что он содержит <b>@</b> и домен.\n"
            "Например: <code>name@mail.ru</code>",
            parse_mode="HTML"
        )
        return EMAIL

    context.user_data["email"] = raw.lower()

    keyboard = [
        [InlineKeyboardButton("📣 Перейти на канал", url=CHANNEL_URL)],
        [InlineKeyboardButton("✅ Я подписалась!", callback_data="subscribed")],
    ]
    await update.message.reply_text(
        f"🎉 <b>Последний шаг!</b>\n\n"
        f"Подпишитесь на наш Telegram-канал, чтобы завершить заявку:\n{CHANNEL_URL}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    return SUBSCRIBE


async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершает анкету и отправляет данные администратору."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    await query.message.reply_text(
        "💜 <b>Спасибо! Ваша заявка отправлена.</b>\n\n"
        "Мы проверим данные и пришлём ссылку в закрытую группу. "
        "Обычно это занимает до 24 часов 🌸",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

    summary = build_data_summary(context.user_data)
    user_id = query.from_user.id
    username = context.user_data.get("username", "")
    # Кнопка «Написать» — по username если есть, иначе по tg://user?id=
    if username:
        write_url = f"https://t.me/{username}"
    else:
        write_url = f"tg://user?id={user_id}"
    keyboard = [
        [InlineKeyboardButton("💬 Написать участнице", url=write_url)],
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}"),
        ],
    ]
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=summary,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    logger.info(f"Новая заявка от пользователя {query.from_user.id}")
    return ConversationHandler.END


# ─── Обработка решений администратора ───────────────────────────────────────

async def admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Администратор принимает или отклоняет заявку."""
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != ADMIN_CHAT_ID:
        await query.answer("⛔ У вас нет прав администратора.", show_alert=True)
        return

    action, user_id = query.data.split("_", 1)
    user_id = int(user_id)

    if action == "approve":
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 <b>Поздравляем! Ваша заявка одобрена.</b>\n\n"
                "Добро пожаловать в клуб «Любины подружки»! 💜\n"
                "Администратор скоро добавит вас в закрытую группу 🌸"
            ),
            parse_mode="HTML"
        )
        await query.edit_message_text(
            query.message.text + "\n\n✅ <b>Заявка одобрена</b>",
            parse_mode="HTML",
            reply_markup=None
        )
    elif action == "reject":
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "😔 <b>К сожалению, на этот раз не получилось.</b>\n\n"
                "Если у вас есть вопросы, напишите нам напрямую."
            ),
            parse_mode="HTML"
        )
        await query.edit_message_text(
            query.message.text + "\n\n❌ <b>Заявка отклонена</b>",
            parse_mode="HTML",
            reply_markup=None
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена анкеты."""
    await update.message.reply_text(
        "Анкета отменена. Чтобы начать заново — напишите /start 🌸",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# ─── Запуск бота ─────────────────────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            KNOWS_LYUBA:   [CallbackQueryHandler(knows_lyuba_handler, pattern="^knows_")],
            EXPECTATIONS:  [CallbackQueryHandler(expectations_handler, pattern="^(exp_offline|exp_online_support|exp_online_meet|exp_gifts|exp_done)$")],
            NAME:          [MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler)],
            PHONE:         [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_handler)],
            EMAIL:         [MessageHandler(filters.TEXT & ~filters.COMMAND, email_handler)],
            SUBSCRIBE:     [CallbackQueryHandler(subscribe_handler, pattern="^subscribed$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(admin_decision, pattern="^(approve|reject)_"))

    logger.info("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass  # отключаем логи пингов

def run_ping_server():
    server = HTTPServer(("0.0.0.0", 10000), PingHandler)
    server.serve_forever()

threading.Thread(target=run_ping_server, daemon=True).start()
if __name__ == "__main__":
    main()
