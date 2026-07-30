# Telegram Bot Architecture Design

## 1. Overview

This document outlines the architecture for a full-featured, professional Telegram Bot designed for an anonymous group of bus and tram drivers. The bot prioritizes anonymity, ease of use for low-tech users, and multilingual support. It will be developed in Python using `python-telegram-bot` and will utilize PostgreSQL for data persistence.

## 2. Core Components

### 2.1. Telegram Bot API Interaction

-   **`python-telegram-bot` (v20+ async):** This library will be the primary interface for interacting with the Telegram Bot API. It supports asynchronous operations, which is crucial for handling multiple users and external API calls (like translation) efficiently.
-   **Handlers:** Different types of handlers (e.g., `CommandHandler`, `MessageHandler`, `CallbackQueryHandler`) will be used to process various user inputs and interactions.

### 2.2. Database (PostgreSQL)

-   **ORM:** `SQLAlchemy` (async) will be used as the Object-Relational Mapper to interact with the PostgreSQL database. This provides an abstraction layer, making database operations more Pythonic and less error-prone.
-   **Connection:** The database connection URL will be read from an environment variable (`DATABASE_URL`).
-   **Schema Design:**
    -   **Users:** Stores `telegram_user_id` (unique identifier from Telegram), `driver_id` (randomly generated `Driver #XXXX`), `language_code` (preferred language), `specialty` (KOM, STRAB, COMP), `karma_points`, `is_banned`.
    -   **Shift Swaps:** Stores details of shift offers/requests, current status (searching, in-progress, completed, cancelled), `offering_driver_id`, `requesting_driver_id`, `shift_details`.
    -   **Proxy Chats:** Stores logs of anonymous proxy conversations between drivers for shift swaps.
    -   **GPX Routes:** Stores metadata for uploaded GPX files (title, line, type) and a reference to the file storage.
    -   **Announcements (Beka):** Stores announcement text, `driver_id` of poster, `specialty_target`, original map reference.
    -   **Kafeneio Messages:** Stores anonymous messages posted to the Kafeneio topic.
    -   **Karma Transactions:** Logs karma point changes.
    -   **Moderation Logs:** Records warnings and bans for anti-spam/anti-racism.

### 2.3. Anonymity and Security

-   **Driver ID Generation:** Upon registration, each user's `telegram_user_id` will be mapped to a randomly generated `Driver #XXXX` ID. This ID will be the only public identifier.
-   **Proxy Chat:** All communication for shift swaps will be routed through the bot, acting as a proxy. Drivers will only see `Driver #XXXX` IDs. The bot will mediate messages without revealing identities.
-   **Block Feature:** A `❌ Ακύρωση & Block` button will be available in private proxy chats to immediately terminate a conversation and protect the user's identity.
-   **Data Retention Policy:** A scheduled cleanup function will delete completed shift swaps and old proxy chat logs after 15 days to minimize data footprint and enhance privacy.
-   **No PII Logging:** The bot will explicitly avoid logging or storing real Telegram names, phone numbers, IP addresses, or personal device data.

### 2.4. User Interface (GUI)

-   **`ReplyKeyboardMarkup`:** Persistent menu at the bottom of the private chat for main navigation.
-   **`InlineKeyboardMarkup`:** Used for all interactive processes (questions, confirmations, selections) within sub-menus. Always includes `🔙 Πίσω / Back` and `❌ Ακύρωση / Cancel` buttons.
-   **Emojis:** Extensive use of emojis on all buttons for clarity and user-friendliness.
-   **Short Text:** Button text will be concise (1-3 words max).

### 2.5. Multilingual Support

-   **`deep-translator`:** Integrated for automatic translation of user-generated content (Beka, Kafeneio, shift requests) and bot responses.
-   **Asynchronous Translation:** Translation calls will be handled asynchronously to prevent blocking the bot.
-   **Language Selection:** Users select their preferred language during initial setup.
-   **Tone:** Informal, friendly, and collegiate.

### 2.6. Features Breakdown

#### 2.6.1. Registration and Profile

-   `/start` command initiates registration.
-   User selects native language and specialty (KOM, STRAB, COMP).
-   `🏆 Το Προφίλ μου & QR` button displays user's `Driver #XXXX` and generates a QR code for peer-to-peer invites.

#### 2.6.2. Peer-to-Peer Invite System (QR Code)

-   Bot generates a unique referral link embedded in a QR code.
-   New registrations via referral link award Karma Points to the referrer.

#### 2.6.3. Shift Exchange (3 Stages)

-   `🔄 Αλλαγή Βάρδιας` button.
-   **Stage 1 (🟢 ΑΝΑΖΗΤΕΙΤΑΙ):** Driver offers/requests a shift (Früh, Tag, Mittel, Geteilt, Spät, Nacht, Frei / Ρεπό) via buttons.
-   **Stage 2 (🟡 ΣΕ ΕΠΕΞΕΡΓΑΣΙΑ):** When a match is found, a private proxy chat is initiated between the two drivers.
-   **Stage 3 (✅ Ολοκληρώθηκε / ❌ Ακύρωση):** Drivers confirm or cancel the swap. If confirmed, the status changes to `🔴 ΒΡΕΘΗΚΕ`. If cancelled, it returns to Stage 1.

#### 2.6.4. Kafeneio / General Chat

-   `☕ Καφενείο / Kous-Kous` button.
-   User types message, bot translates it, and posts it anonymously to the `☕ Καφενείο` topic.

#### 2.6.5. GPX Route Management

-   `🚧 Παράκαμψη / GPX` button.
-   Allows uploading `.gpx` files with line title and type.
-   Other drivers can `[Λήψη]` (Download) the GPX files.

#### 2.6.6. Gamification (Karma & Badges)

-   Karma points awarded for invites, Beka uploads, shift swaps, and help.
-   Ability to send `Εικονικού Καφέ ☕` (Virtual Coffee).
-   Badges (🥉, 🥈, 🥇) based on Karma points.

#### 2.6.7. Announcements (Beka Simplified)

-   `📢 Beka (Ανακοινώσεις)` button.
-   Allows uploading announcements with vehicle type (KOM/STRAB).
-   Targeted delivery to relevant specialty topics, along with original map.

#### 2.6.8. Content Moderation & Anti-Spam

-   **Anti-Spam:** Rate limiting (e.g., max 3 messages/minute), duplicate message prevention, external URL blocking.
-   **Anti-Racism:** Automatic detection of profanity/racism in all languages. Immediate deletion, warning, and 3-strike auto-ban system.

#### 2.6.9. Topic Routing

-   Automatic classification and routing of messages to specific Telegram topics (`TOPIC_BEKA_ID`, `TOPIC_SHIFTS_ID`, `TOPIC_DETOURS_ID`, `TOPIC_SOS_ID`, `TOPIC_KOUSKOUS_ID`).

## 3. Deployment Considerations

-   **Environment Variables:** `TELEGRAM_BOT_TOKEN`, `DATABASE_URL`, `DEEP_TRANSLATOR_API_KEY` (if required by `deep-translator` for higher limits/quality).
-   **`Procfile`:** `worker: python main.py` for Render deployment.
-   **`runtime.txt`:** `python-3.11.6`.
-   **`requirements.txt`:** `python-telegram-bot`, `SQLAlchemy`, `asyncpg` (or other PostgreSQL driver), `deep-translator`, `pytz`, `qrcode`, `Pillow`.

## 4. Next Steps

Proceed with implementing the core bot infrastructure, starting with database setup and user registration.
