# Blinkit Stock Bot

A production-ready Telegram bot that monitors stock availability for specific products on Blinkit using a reusable, self-healing browser instance, async database persistence, and smart session recovery.

---

## Features
* **Efficient Reusable Browser**: Single Chromium instance running asynchronously to keep resources low.
* **Self-Healing Connection**: Re-spawns Chromium automatically if it crashes or is closed.
* **Auto-Pause & Recovery**: Detects session expirations, pauses tracking, sends a notification, and resumes automatically when it detects a fresh login.
* **Visual Verification**: Sends actual page screenshots along with restock alerts.
* **FastAPI Integrations**: Fully wrapped web application with `/ping`, `/version`, and `/health` endpoints for status monitoring.

---

## Telegram Commands
* `/start` - Initial guidance.
* `/list` - Shows all currently tracked products with stock status (`🟢 In Stock` / `🔴 Out of Stock`).
* `/remove <id>` - Untracks a product by ID.
* `/reload` - Force-reloads the browser context manually.
* `/health` - Returns bot, browser, database, and countdown statistics.
* `/loginstatus` - Detailed session status with relative login age.
* **Send Product Link** - Send any Blinkit product URL (containing `/prid/`) to automatically add it to tracking.

---

## Installation & Local Development

### 1. Set Up Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment Variables
Create a `.env` file in the root folder:
```env
TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
CHAT_ID="your-telegram-chat-id"
HEADLESS="false"
```

### 3. Log In Manually
First, run the login utility to complete the captcha/OTP manually and save the session context:
```bash
python blinkit/login.py
```
This saves `storage.json` and writes `last_login.json`.

### 4. Run the Project
* **Direct Script (standard local development)**:
  ```bash
  python main.py
  ```
* **FastAPI Web Server (simulating Render)**:
  ```bash
  uvicorn app:app --reload
  ```

---

## Cloud Deployment (e.g. Render)

### 1. Environment Variables
Configure these variables on your hosting platform:
* `TELEGRAM_BOT_TOKEN`
* `CHAT_ID`
* `HEADLESS=true`
* `BLINKIT_STORAGE` — Set this to the Base64-encoded string of your local `storage.json`.

#### Encoding `storage.json` to Base64 (Windows PowerShell):
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("storage.json"))
```
Copy the output string and paste it into the `BLINKIT_STORAGE` environment variable. On startup, the bot will automatically decode this back into `storage.json`.

### 2. Build & Start Commands
* **Build Command**:
  ```bash
  pip install -r requirements.txt && playwright install chromium
  ```
* **Start Command**:
  ```bash
  uvicorn app:app --host 0.0.0.0 --port $PORT
  ```
