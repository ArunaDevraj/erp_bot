🤖 ERPNext Telegram Bot — OTP Verification, Leave Application & Location-Based Check-In/Out

This project integrates a Telegram bot with your ERPNext instance, enabling employees to:

    Link their Telegram account to ERPNext via OTP email verification

    Apply for leave directly through Telegram

    Perform location-restricted check-in and check-out

The bot communicates with ERPNext through its REST API and uses the python-telegram-bot library.
🚀 Features
Command	Description
/start	Displays the main menu
/help	: Lists all available commands
/id	Initiates OTP verification to link Telegram ID with Employee record
/resend_otp	Resends OTP if verification is pending
/apply_leave	Apply for leave with an interactive date picker and real-time balance check
/checkinout	Perform location-based employee check-in/out
/cancel	Cancel any ongoing process and return to the main menu
📦 Prerequisites

    ERPNext / Frappe Version: v12+

    Python: 3.8+

    ERPNext REST API enabled

    python-telegram-bot v20+

    ERPNext Email Notification is configured for sending OTPs

⚖️ Step 1: Telegram Integration with ERPNext


A. Install the ERPNext Telegram App

Inside the Frappe bench environment, run:

./env/bin/pip install python-telegram-bot --upgrade

This ensures the package is installed in the correct environment (not globally).
B. Get the Integration App

bench get-app erpnext_telegram_integration https://github.com/yrestom/erpnext_telegram.git

C. Install the App on Your Site

bench --site [your.site.name] install-app erpnext_telegram_integration

D. Build and Restart

bench build
bench restart

⚙️ Step 2: Install Bot Dependencies

Inside your bench environment, run:

./env/bin/pip install python-telegram-bot aiohttp requests --upgrade

🤖 Step 3: Create a Telegram Bot

    Open Telegram and search for @BotFather

    Use /newbot and follow the prompts

    Save the Bot Token — you will need it later

⚙️ Step 4: Configure ERPNext
A. Telegram Settings

    Go to Telegram Settings in ERPNext

    Create a new record and set:

        Bot Username

        Bot Token (from BotFather)

B. Telegram User Settings

    Go to Telegram User Settings in ERPNext

    Create a new entry:

        Party → Employee

        Employee → Select the employee

        Telegram Settings → Choose the settings created above

        (Optional) Check Is Group Chat if this is for a group

    Click Generate Telegram Token → copy it

    Send this token to the bot in a private message

    Return to ERPNext and click Get Chat ID

    Save the record once successful

🧩 Step 5: Custom Fields in Employee Doctype

Add the following custom fields in Employee:
Field Name	Type	Description
custom_telegram_id	Data	Stores linked Telegram ID
custom_allowed_latitude	Float	Allowed check-in latitude
custom_allowed_longitude	Float	Allowed check-in longitude
custom_allowed_radius	Float	Allowed check-in radius (meters)


🛠 Step 6: Bot Script Configuration

Create and edit erp_com.py:

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ERP_URL = "https://your-erpnext-url"
ERP_API_KEY = "your-api-key"
ERP_API_SECRET = "your-api-secret"

Ensure the API key and secret belong to a user with access to Employee, Leave Application, and Employee Checkin doctypes.


▶️ Step 7: Running the Bot


A. Manual Run (Testing)

python3 erp_com.py

B. Run as a Background Service

    Create a virtual environment:

python3 -m venv erpbot-env
source erpbot-env/bin/activate
pip install python-telegram-bot aiohttp requests

Create a systemd service file:
/etc/systemd/system/erpbot.service

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

Enable & start the service:

    sudo systemctl daemon-reload
    sudo systemctl enable erpbot.service
    sudo systemctl start erpbot.service
    sudo systemctl status erpbot.service

🔑 Step 8: Linking Telegram to ERPNext

    In Telegram, type /id and enter your Employee ID when prompted

    You will receive an OTP on your registered email

    Enter the OTP in Telegram

    Your Telegram ID will be saved in custom_telegram_id

📍 Step 9: Location-Based Check-In/Out

    Admin must set:

        custom_allowed_latitude

        custom_allowed_longitude

        custom_allowed_radius

    When /checkinout is used, the bot:

        Captures your GPS location

        Verifies it is within the allowed radius

        Records attendance if valid

✅ How It Works

    OTP Verification → /id sends an OTP via ERPNext email; once verified, saves Telegram ID

    Leave Application → /apply_leave fetches policy, balance, and uses inline keyboards for date selection

    Check-In/Out → /checkinout verifies GPS location before creating an Employee Checkin record

📜 License

MIT License — free to use, modify, and distribute.
