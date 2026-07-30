
import os
import logging
import asyncio
import random
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationFactory
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, BigInteger, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from deep_translator import GoogleTranslator
import pytz
import qrcode
from PIL import Image
import io

# --- Configuration --- #
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# Topic IDs (These should be set via environment variables or a config menu)
TOPIC_BEKA_ID = os.getenv("TOPIC_BEKA_ID")
TOPIC_SHIFTS_ID = os.getenv("TOPIC_SHIFTS_ID")
TOPIC_DETOURS_ID = os.getenv("TOPIC_DETOURS_ID")
TOPIC_SOS_ID = os.getenv("TOPIC_SOS_ID")
TOPIC_KOUSKOUS_ID = os.getenv("TOPIC_KOUSKOUS_ID")

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Setup --- #
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False)
    driver_id = Column(String, unique=True, nullable=False)
    language_code = Column(String, default='en')
    specialty = Column(String)
    karma_points = Column(Integer, default=0)
    is_banned = Column(Boolean, default=False)
    warnings = Column(Integer, default=0)
    registered_at = Column(DateTime, default=datetime.utcnow)

class ShiftSwap(Base):
    __tablename__ = 'shift_swaps'
    id = Column(Integer, primary_key=True)
    offering_driver_id = Column(String, ForeignKey('users.driver_id'))
    requesting_driver_id = Column(String, ForeignKey('users.driver_id'), nullable=True)
    shift_type = Column(String) # Früh, Tag, Mittel, Geteilt, Spät, Nacht, Frei
    status = Column(String, default='SEARCHING') # SEARCHING, IN_PROGRESS, COMPLETED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)

class GPXRoute(Base):
    __tablename__ = 'gpx_routes'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    line_type = Column(String)
    file_id = Column(String)
    uploaded_by = Column(String, ForeignKey('users.driver_id'))
    created_at = Column(DateTime, default=datetime.utcnow)

class KafeneioMessage(Base):
    __tablename__ = 'kafeneio_messages'
    id = Column(Integer, primary_key=True)
    driver_id = Column(String, ForeignKey('users.driver_id'))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database Engine & Session
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized.")

# --- Localization / Translation --- #
LANGUAGES = {
    'en': 'English',
    'de': 'Deutsch',
    'el': 'Ελληνικά',
    'tr': 'Türkçe',
    'sr': 'Српски',
    'es': 'Español',
    'it': 'Italiano',
    'ar': 'العربية',
}

async def translate_text(text, target_lang, source_lang='auto'):
    if target_lang == 'en' and source_lang == 'en': return text
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        return await asyncio.to_thread(translator.translate, text)
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text

async def get_localized_text(user_language_code, key, **kwargs):
    messages = {
        "welcome": "Welcome colleague! 🚌 This is our independent and anonymous space.",
        "choose_language": "🌐 Please choose your language / Παρακαλώ επιλέξτε γλώσσα:",
        "choose_specialty": "🛠️ What do you drive?",
        "registration_complete": "✅ Done! You are now {driver_id}. Keep it secret!",
        "back": "🔙 Back",
        "cancel": "❌ Cancel",
        "main_menu": "🏠 Main Menu",
        "change_shift": "🔄 Change Shift",
        "detour_gpx": "🚧 Detour / GPX",
        "announcements": "📢 Beka (Announcements)",
        "sos_help": "🆘 SOS Help",
        "kafeneio": "☕ Kafeneio / Kous-Kous",
        "my_profile_qr": "🏆 My Profile & QR",
        "kom": "🚌 KOM (Bus)",
        "strab": "🚋 STRAB (Tram)",
        "comp": "🚌/🚋 COMP (Double)",
        "already_registered": "You are already one of us! Your ID: {driver_id}.",
        "error_occurred": "Oops! Something went wrong. Try again.",
        "shift_type_prompt": "Which shift are you offering/looking for?",
        "shift_posted": "✅ Shift posted in the group!",
        "proxy_chat_started": "🤝 Proxy chat started with another driver. You are anonymous.",
        "proxy_chat_ended": "🛑 Chat ended. Identity protected.",
        "karma_update": "⭐ Karma updated! Current: {points}",
        "spam_warning": "⚠️ Slow down! Don't spam.",
        "racism_warning": "🚫 No racism or profanity allowed. Warning {count}/3.",
        "banned": "❌ You have been banned for repeated violations.",
    }
    text = messages.get(key, key)
    translated = await translate_text(text, user_language_code)
    return translated.format(**kwargs) if kwargs else translated

# --- Helper Functions --- #
async def generate_driver_id():
    async with AsyncSessionLocal() as session:
        while True:
            driver_id = f"Driver #{random.randint(1000, 9999)}"
            result = await session.execute(select(User).filter_by(driver_id=driver_id))
            if not result.scalar_one_or_none():
                return driver_id

async def get_main_menu_keyboard(user_language_code):
    buttons = [
        [KeyboardButton(await get_localized_text(user_language_code, "change_shift")), KeyboardButton(await get_localized_text(user_language_code, "detour_gpx"))],
        [KeyboardButton(await get_localized_text(user_language_code, "announcements")), KeyboardButton(await get_localized_text(user_language_code, "sos_help"))],
        [KeyboardButton(await get_localized_text(user_language_code, "kafeneio")), KeyboardButton(await get_localized_text(user_language_code, "my_profile_qr"))],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- Moderation & Anti-Spam --- #
USER_LAST_MESSAGE_TIME = {}
PROFANITY_LIST = ["racist_word1", "bad_word2"] # Expand this list or use a library

async def is_spam(user_id):
    now = datetime.now()
    if user_id in USER_LAST_MESSAGE_TIME:
        last_time = USER_LAST_MESSAGE_TIME[user_id]
        if (now - last_time).total_seconds() < 2: # Max 1 msg per 2 seconds
            return True
    USER_LAST_MESSAGE_TIME[user_id] = now
    return False

async def check_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    text = update.message.text or ""
    # Simple profanity check (should be more advanced for 100+ languages)
    for word in PROFANITY_LIST:
        if word in text.lower():
            user.warnings += 1
            if user.warnings >= 3:
                user.is_banned = True
                await update.message.reply_text(await get_localized_text(user.language_code, "banned"))
            else:
                await update.message.reply_text(await get_localized_text(user.language_code, "racism_warning", count=user.warnings))
            return False
    return True

# --- Handlers --- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).filter_by(telegram_user_id=user_id))
        user = result.scalar_one_or_none()

        if user:
            msg = await get_localized_text(user.language_code, "already_registered", driver_id=user.driver_id)
            await update.message.reply_text(msg, reply_markup=await get_main_menu_keyboard(user.language_code))
            return

    # Registration Start
    buttons = [[InlineKeyboardButton(name, callback_data=f"lang_{code}")] for code, name in LANGUAGES.items()]
    await update.message.reply_text("🌐 Choose Language:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    async with AsyncSessionLocal() as session:
        if data.startswith("lang_"):
            lang = data.split("_")[1]
            # Temporary store lang in context
            context.user_data['reg_lang'] = lang
            buttons = [
                [InlineKeyboardButton("🚌 KOM", callback_data="spec_KOM")],
                [InlineKeyboardButton("🚋 STRAB", callback_data="spec_STRAB")],
                [InlineKeyboardButton("🚌/🚋 COMP", callback_data="spec_COMP")]
            ]
            await query.edit_message_text("🛠️ Specialty:", reply_markup=InlineKeyboardMarkup(buttons))

        elif data.startswith("spec_"):
            spec = data.split("_")[1]
            lang = context.user_data.get('reg_lang', 'en')
            driver_id = await generate_driver_id()
            new_user = User(telegram_user_id=user_id, driver_id=driver_id, language_code=lang, specialty=spec)
            session.add(new_user)
            await session.commit()
            
            msg = await get_localized_text(lang, "registration_complete", driver_id=driver_id)
            await query.edit_message_text(msg)
            await query.message.reply_text("🏠", reply_markup=await get_main_menu_keyboard(lang))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).filter_by(telegram_user_id=user_id))
        user = result.scalar_one_or_none()
        if not user or user.is_banned: return

        if await is_spam(user_id):
            await update.message.reply_text(await get_localized_text(user.language_code, "spam_warning"))
            return

        if not await check_moderation(update, context, user):
            await session.commit()
            return

        # Main Menu Routing
        if text == await get_localized_text(user.language_code, "my_profile_qr"):
            qr_data = f"https://t.me/{context.bot.username}?start=ref_{user.driver_id}"
            qr = qrcode.make(qr_data)
            buf = io.BytesIO()
            qr.save(buf, format='PNG')
            buf.seek(0)
            await update.message.reply_photo(photo=buf, caption=f"🏆 {user.driver_id}\n⭐ Karma: {user.karma_points}")

        elif text == await get_localized_text(user.language_code, "kafeneio"):
            context.user_data['state'] = 'WAITING_KOUSKOUS'
            await update.message.reply_text("☕ Type your anonymous message:")

        elif context.user_data.get('state') == 'WAITING_KOUSKOUS':
            # Post to Kafeneio Topic
            translated_msg = f"🗣️ **{user.driver_id}**:\n{text}"
            # Logic to send to TOPIC_KOUSKOUS_ID goes here
            await update.message.reply_text("✅ Posted anonymously!")
            context.user_data['state'] = None

# --- Cleanup Task --- #
async def cleanup_db():
    while True:
        await asyncio.sleep(86400) # Run daily
        async with AsyncSessionLocal() as session:
            # Delete old swaps and logs (logic here)
            limit = datetime.utcnow() - timedelta(days=15)
            # await session.execute(delete(ShiftSwap).where(ShiftSwap.created_at < limit))
            await session.commit()

async def main() -> None:
    await init_db()
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    asyncio.create_task(cleanup_db())
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
