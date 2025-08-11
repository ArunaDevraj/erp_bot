🤖 ERPNext Telegram Bot with OTP Verification, Leave Application & Location-Based Check-In/Out

This project integrates a Telegram bot with your ERPNext instance, enabling employees to:

    Link their Telegram account to ERPNext via OTP email verification

    Apply for leave directly through Telegram

    Perform location-restricted check-in and check-out

The bot communicates with ERPNext through its REST API and uses the python-telegram-bot library.
🚀 Features

    /start — Displays the main menu

    /help — Lists all available commands

    /id — Starts OTP verification to link your Telegram ID with your Employee record

    /resend_otp — Resend OTP if verification is pending

    /apply_leave — Apply for leave with an interactive date picker and real-time balance check

    /checkinout — Location-based employee check-in/out

    /cancel — Cancel any ongoing process and return to the main menu

📦 Prerequisites

    Frappe / ERPNext Version: 12+

    Python: 3.8+

    Installed ERPNext REST API enabled

    python-telegram-bot v20+

    ERPNext Email Notification configuration (for sending OTPs)

⚖️ Step 1: Install Dependencies

Inside your bench environment, run:

./env/bin/pip install python-telegram-bot aiohttp requests --upgrade

🤖 Step 2: Create a Telegram Bot

    Open Telegram and search for @BotFather

    Use /newbot and follow the prompts

    Save the Telegram Bot Token you receive — you’ll need it for configuration

⚙️ Step 3: Configure ERPNext
A. Add Custom Fields to Employee

Add the following custom fields in the Employee doctype:

    custom_telegram_id (Data) — To store the linked Telegram ID

    custom_allowed_latitude (Float) — Allowed check-in latitude

    custom_allowed_longitude (Float) — Allowed check-in longitude

    custom_allowed_radius (Float) — Allowed check-in radius in meters

🧠 Step 4: Configure the Bot Script

Update these variables in your Python script (erp_bot.py):

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ERP_URL = "https://your-erpnext-url"
ERP_API_KEY = "your-api-key"
ERP_API_SECRET = "your-api-secret"

Ensure the API key and secret belong to a user with access to the Employee, Leave Application, and Employee Checkin document types.
🛠 Step 5: Running the Bot
A. Manual Run (Testing)

python3 erp_com.py

B. Run as a Background Service

Create a virtual environment for the bot:

python3 -m venv erpbot-env
source erpbot-env/bin/activate
pip install python-telegram-bot aiohttp requests

Create /etc/systemd/system/erpbot.service:

[Unit]
Description=ERPNext Telegram Bot Service
After=network.target

[Service]
ExecStart=/home/your-username/erpbot-env/bin/python /home/your-username/Telegram-bot-for-ERPNext/erp_com.py
WorkingDirectory=/home/your-username/Telegram-bot-for-ERPNext
Restart=always
User=your-username

[Install]
WantedBy=multi-user.target

Enable and start:

sudo systemctl daemon-reload
sudo systemctl enable erpbot.service
sudo systemctl start erpbot.service
sudo systemctl status erpbot.service

👨‍💼 Step 6: Linking Telegram to ERPNext

    In Telegram, type /id and enter your Employee ID when prompted

    You will receive an OTP on your registered email

    Enter the OTP in Telegram to link your account

    Your Telegram ID will be stored in the custom_telegram_id field

📍 Step 7: Location-Based Check-In/Out

    Admin must set custom_allowed_latitude, custom_allowed_longitude, and custom_allowed_radius for each employee

    When /checkinout is used, the bot verifies your current GPS location against the allowed location & radius before recording attendance

✅ How It Works

    OTP Linking: /id sends OTP via ERPNext’s email system; once verified, the Telegram ID is saved

    Leave Application: /apply_leave fetches leave policy, balance, and uses inline keyboards for selecting dates & reason

    Check-In/Out: /checkinout ensures the GPS location matches allowed parameters before creating an Employee Checkin record

📜 License

MIT License — free to use, modify, and distribute
