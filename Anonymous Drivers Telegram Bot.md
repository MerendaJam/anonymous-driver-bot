# Anonymous Drivers Telegram Bot

This is a full-featured Telegram Bot designed for an anonymous group of bus and tram drivers. It prioritizes anonymity, ease of use for low-tech users, and multilingual support. The bot is built with Python using `python-telegram-bot` and uses PostgreSQL for data persistence.

## Features

*   **Graphical User Interface (GUI):** All interactions are button-driven, with no typing required except for specific chat messages.
*   **Anti-Spy Protection:** Ensures complete anonymity for drivers, with proxy chats and a block feature against suspected corporate spies.
*   **Peer-to-Peer Invite System:** Secure QR code-based invitation system that rewards referrers with Karma Points.
*   **3-Stage Shift Exchange:** Facilitates anonymous shift swaps between drivers.
*   **Kafeneio / General Chat:** Anonymous general chat with automatic translation.
*   **GPX Route Management:** Allows sharing and downloading of GPX route files.
*   **Gamification:** Karma points and badges for active participation.
*   **Content Moderation:** Anti-spam and anti-racism filters with a 3-strike auto-ban system.
*   **Multilingual Support:** Automatic translation of all messages using `deep-translator`.
*   **Beka (Announcements) Simplified:** Targeted announcements to specific driver specialties.
*   **Topic Routing:** Automatic categorization of messages into Telegram topics.

## Deployment on Render.com

This section provides step-by-step instructions to deploy your Telegram Bot on Render.com.

### Prerequisites

1.  **Render Account:** Create an account on [Render.com](https://render.com/).
2.  **GitHub Account:** You will need a GitHub account to host your bot's code.
3.  **Telegram Bot Token:** Obtain a bot token from BotFather on Telegram.

### Step 1: Get Your Telegram Bot Token

1.  Open Telegram and search for `@BotFather`.
2.  Start a chat with BotFather and send the command `/newbot`.
3.  Follow the instructions to choose a name and a username for your bot. The username must end with 'bot' (e.g., `MyDriversBot`).
4.  BotFather will provide you with an **HTTP API Token**. This is your `TELEGRAM_BOT_TOKEN`. Keep it secure and do not share it.

### Step 2: Prepare Your Code for GitHub

1.  **Create a new GitHub Repository:** Create a new public or private repository on GitHub (e.g., `anonymous-drivers-bot`).
2.  **Upload Bot Files:** Upload the following files to the root of your GitHub repository:
    *   `main.py`
    *   `requirements.txt`
    *   `Procfile`
    *   `runtime.txt`

### Step 3: Set up PostgreSQL Database on Render

1.  In your Render dashboard, navigate to **Databases** and click **New PostgreSQL**.
2.  Choose a name for your database (e.g., `drivers-bot-db`).
3.  Select a region and a plan (the free tier is usually sufficient for testing).
4.  Click **Create Database**.
5.  Once the database is provisioned, go to its dashboard. You will find the **Internal Database URL** and **External Database URL**. Copy the **Internal Database URL**; this will be your `DATABASE_URL` environment variable.

### Step 4: Deploy the Bot on Render

1.  In your Render dashboard, navigate to **Web Services** and click **New Web Service**.
2.  Select **Build and deploy from a Git repository**.
3.  Connect your GitHub account and select the repository you created in Step 2.
4.  **Configuration:**
    *   **Name:** Choose a name for your web service (e.g., `drivers-telegram-bot`).
    *   **Region:** Select the same region as your PostgreSQL database.
    *   **Root Directory:** Leave empty if your files are in the root.
    *   **Runtime:** `Python 3`
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `python main.py`
    *   **Instance Type:** Choose a suitable instance type (the free tier is usually sufficient for testing).
5.  **Environment Variables:** Click **Advanced** to add environment variables:
    *   `TELEGRAM_BOT_TOKEN`: Paste the token you got from BotFather (Step 1).
    *   `DATABASE_URL`: Paste the Internal Database URL from your Render PostgreSQL database (Step 3).
    *   `DEEP_TRANSLATOR_API_KEY`: (Optional) If `deep-translator` requires an API key for higher usage limits or better quality, add it here. For basic usage, it might not be strictly necessary.
6.  Click **Create Web Service**.

Render will now build and deploy your bot. You can monitor the deployment logs in the Render dashboard. Once deployed, your bot should be live and responsive on Telegram.

## Local Development

To run the bot locally for development or testing:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/anonymous-drivers-bot.git
    cd anonymous-drivers-bot
    ```
2.  **Create a virtual environment and install dependencies:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
3.  **Set Environment Variables:** Create a `.env` file in the root directory with your `TELEGRAM_BOT_TOKEN` and a local `DATABASE_URL` (e.g., a local PostgreSQL instance or a SQLite file for testing).
    ```
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    DATABASE_URL="postgresql://user:password@host:port/database_name"
    # For local SQLite testing (not recommended for production):
    # DATABASE_URL="sqlite:///drivers_bot.db"
    ```
4.  **Run the bot:**
    ```bash
    python main.py
    ```

## Contributing

Feel free to fork the repository, make improvements, and submit pull requests.
