"""
Telegram-бот для вступления в женский клуб КЕБШ "Любины подружки"
Зависимости: pip install python-telegram-bot==20.7
Запуск: python kebsh_bot.py
"""

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
CHANNEL_URL = "https://t.me/+IEmmVJtWhb5iNzcy"

# ─── Состояния диалога ───────────────────────────────────────────────────────

KNOWS_LYUBA, EXPECTATIONS, NAME, PHONE, EMAIL, SUBSCRIBE = range(6)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─── Вспомогательные функции ─────────────────────────────────────────────────

def build_data_summary(data: dict) -> str:
    """Собирает анкету в читаемый текст для администратора."""
    return (
        "🌸 <b>Новая заявка в клуб «Любины подружки»</b>\n\n"
        f"👤 <b>Имя:</b> {data.get('name', '—')}\n"
        f"📞 <b>Телефон:</b> {data.get('phone', '—')}\n"
        f"📧 <b>Почта:</b> {data.get('email', '—')}\n"
        f"💜 <b>Знакома с Любой:</b> {data.get('knows_lyuba', '—')}\n"
        f"✨ <b>Ожидания:</b> {data.get('expectations', '—')}\n"
        f"🆔 <b>Telegram ID:</b> <code>{data.get('user_id', '—')}</code>\n"
        f"🔗 <b>Username:</b> @{data.get('username', 'нет')}"
    )


# ─── Обработчики ─────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Приветствие и первый вопрос."""
    context.user_data.clear()
    context.user_data["user_id"] = update.effective_user.id
    context.user_data["username"] = update.effective_user.username or ""

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

    keyboard = [
        [InlineKeyboardButton("🤝 Оффлайн встречи", callback_data="exp_offline")],
        [InlineKeyboardButton("💌 Онлайн рекомендации и поддержка", callback_data="exp_online_support")],
        [InlineKeyboardButton("💻 Онлайн встречи", callback_data="exp_online_meet")],
        [InlineKeyboardButton("🎁 Секретные подарки и бонусы", callback_data="exp_gifts")],
    ]
    await query.message.reply_text(
        "✨ <b>Что вы ждёте от участия в клубе?</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    return EXPECTATIONS


async def expectations_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ожидания от клуба."""
    query = update.callback_query
    await query.answer()

    mapping = {
        "exp_offline": "Оффлайн встречи",
        "exp_online_support": "Онлайн рекомендации и поддержка",
        "exp_online_meet": "Онлайн встречи",
        "exp_gifts": "Секретные подарки и бонусы",
    }
    answer = mapping.get(query.data, query.data)
    context.user_data["expectations"] = answer
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"Отлично! Выбрано: <b>{answer}</b>", parse_mode="HTML")

    await query.message.reply_text(
        "👤 <b>Как вас зовут?</b>\nНапишите своё имя (или имя и фамилию).",
        parse_mode="HTML"
    )
    return NAME


async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает имя пользователя."""
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        "📞 <b>Ваш номер телефона</b>\nНапример: +7 999 123 45 67",
        parse_mode="HTML"
    )
    return PHONE


async def phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает телефон пользователя."""
    context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text(
        "📧 <b>Ваша электронная почта</b>",
        parse_mode="HTML"
    )
    return EMAIL


async def email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает email и предлагает подписаться на канал."""
    context.user_data["email"] = update.message.text.strip()

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

    # Подтверждение пользователю
    await query.message.reply_text(
        "💜 <b>Спасибо! Ваша заявка отправлена.</b>\n\n"
        "Мы проверим данные и пришлём ссылку в закрытую группу. "
        "Обычно это занимает до 24 часов 🌸",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

    # Отправка анкеты администратору
    summary = build_data_summary(context.user_data)
    keyboard = [
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"approve_{query.from_user.id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{query.from_user.id}"),
        ]
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
                f"Ссылка на закрытую группу: {CHANNEL_URL}"
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
            EXPECTATIONS:  [CallbackQueryHandler(expectations_handler, pattern="^exp_")],
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


if __name__ == "__main__":
    main()
