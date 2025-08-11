import sys
import math
import logging
import random
import time
import requests
import json
import aiohttp
from datetime import datetime, timedelta
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    InlineKeyboardButton, 
    KeyboardButton, 
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    ContextTypes,
    ConversationHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters
)
from telegram.error import BadRequest

# === Configuration ===
BOT_TOKEN = "Your Bot father Token"
ERP_URL = "Your Site name"
ERP_API_KEY = "Your API Key"
ERP_API_SECRET = "Your API Secret Key"

HEADERS = {
    "Authorization": f"token {ERP_API_KEY}:{ERP_API_SECRET}",
    "Content-Type": "application/json"
}

# === Logging ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === OTP Storage ===
otp_storage = {}

# === States ===
ASK_EMPLOYEE_ID, ASK_OTP = range(2)
LEAVE_TYPE_SELECTION, SELECT_FROM_DATE, SELECT_TO_DATE, LEAVE_REASON = range(100, 104)
CHECKINOUT_SELECTION = range(10, 11)

# === Helper Functions ===
def fetch_employee_by_employee_id(employee_id):
    try:
        url = f"{ERP_URL}/api/resource/Employee?fields=[\"name\",\"user_id\"]&filters=[[\"employee_id\",\"=\",\"{employee_id}\"],[\"status\",\"=\",\"Active\"]]"
        res = requests.get(url, headers=HEADERS)
        data = res.json().get("data", [])
        if data and data[0].get("user_id"):
            return data[0]["name"], data[0]["user_id"]
    except Exception:
        logger.exception("Failed to fetch employee by employee_id")
    return None

def update_telegram_id(emp_docname, telegram_id):
    try:
        url = f"{ERP_URL}/api/resource/Employee/{emp_docname}"
        data = {"custom_telegram_id": telegram_id}
        res = requests.put(url, headers=HEADERS, json=data)
        return res.status_code == 200
    except Exception:
        logger.exception("Failed to update Telegram ID")
        return False

def send_otp_email(recipient_email, otp):
    payload = {
        "recipients": recipient_email,
        "sender": "yourexample@gmail.com",
        "subject": "OTP Verification - ERP Telegram Link",
        "content": f"Your OTP for linking Telegram to ERP is: {otp}",
        "communication_medium": "Email",
        "send_email": 1
    }
    try:
        res = requests.post(
            f"{ERP_URL}/api/method/frappe.core.doctype.communication.email.make",
            headers=HEADERS, 
            json=payload
        )
        return res.status_code == 200
    except Exception:
        logger.exception("Failed to send OTP email")
        return False

def get_employee_by_telegram_id(telegram_id):
    try:
        url = f"{ERP_URL}/api/resource/Employee?fields=[\"name\"]&filters=[[\"custom_telegram_id\",\"=\",\"{telegram_id}\"]]"
        res = requests.get(url, headers=HEADERS)
        data = res.json().get("data", [])
        if data:
            return data[0]["name"]
    except Exception:
        logger.exception("Failed to get employee by telegram_id")
    return None

# === Menu System ===
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main menu with working buttons."""
    context.user_data.clear()
    
    reply_keyboard = [
        ["/id", "/resend_otp"],
        ["/apply_leave", "/checkinout"],
        ["/help", "/cancel"]
    ]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    
    try:
        if update.callback_query:
            await update.callback_query.answer()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="👋 Welcome! Use the buttons below:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "👋 Welcome! Use the buttons below:",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error showing main menu: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="👋 Welcome! Use the buttons below:",
            reply_markup=reply_markup
        )
    
    return ConversationHandler.END

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command that shows the main menu."""
    return await show_main_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help menu."""
    keyboard = [
        [KeyboardButton("/start")],
        [KeyboardButton("/id")],
        [KeyboardButton("/resend_otp")],
        [KeyboardButton("/apply_leave")],
        [KeyboardButton("/checkinout")],
        [KeyboardButton("/cancel")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    help_text = (
        "ℹ️ <b>Help Menu</b>\n"
        "Choose a command to use:\n\n"
        "/start - Show main menu\n"
        "/id - Verify your employee ID\n"
        "/resend_otp - Resend OTP\n"
        "/apply_leave - Request leave\n"
        "/checkinout - Log checkin/checkout\n"
        "/help - Show this help\n"
        "/cancel - Cancel current operation"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# === Cancel Handler ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels and ends the conversation."""
    context.user_data.clear()
    
    try:
        if update.callback_query:
            await update.callback_query.answer()
            try:
                await update.callback_query.edit_message_text("❌ Operation cancelled.")
            except BadRequest:
                pass
        else:
            await update.message.reply_text("❌ Operation cancelled.")
    except Exception as e:
        logger.error(f"Error in cancel handler: {e}")
    
    # Always show main menu after cancellation
    return await show_main_menu(update, context)

# === OTP Verification ===
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the OTP verification process."""
    context.user_data.clear()
    keyboard = [[KeyboardButton("❌ Cancel")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🪪 Please enter your *Employee ID*:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    return ASK_EMPLOYEE_ID

async def handle_employee_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle employee ID input."""
    if update.message.text.strip().lower() == "❌ cancel":
        return await cancel(update, context)
    
    input_emp_id = update.message.text.strip()
    result = fetch_employee_by_employee_id(input_emp_id)
    if not result:
        await update.message.reply_text("❌ Employee ID not found.")
        return await show_main_menu(update, context)

    emp_docname, email = result
    otp = random.randint(100000, 999999)
    otp_storage[emp_docname] = (otp, time.time(), email)
    context.user_data["emp_docname"] = emp_docname

    if send_otp_email(email, otp):
        keyboard = [[KeyboardButton("❌ Cancel")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"📨 OTP sent to your email: {email}\n\nPlease enter the OTP.",
            reply_markup=reply_markup
        )
        return ASK_OTP
    else:
        await update.message.reply_text("❌ Failed to send OTP.")
        return await show_main_menu(update, context)

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle OTP verification."""
    if update.message.text.strip().lower() == "❌ cancel":
        return await cancel(update, context)
    
    emp_docname = context.user_data.get("emp_docname")
    entered_otp = update.message.text.strip()

    if not emp_docname or emp_docname not in otp_storage:
        await update.message.reply_text("❌ Session expired. Please start again using /id.")
        return await show_main_menu(update, context)

    otp, timestamp, _ = otp_storage[emp_docname]
    if time.time() - timestamp > 300:
        await update.message.reply_text("⌛ OTP expired. Please restart with /id.")
        otp_storage.pop(emp_docname, None)
        return await show_main_menu(update, context)

    if str(otp) != entered_otp:
        keyboard = [[KeyboardButton("❌ Cancel")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "❌ Incorrect OTP. Try again.",
            reply_markup=reply_markup
        )
        return ASK_OTP

    telegram_id = update.effective_user.id
    if update_telegram_id(emp_docname, telegram_id):
        await update.message.reply_text("✅ Telegram ID successfully linked!")
    else:
        await update.message.reply_text("❌ Failed to link Telegram ID. Contact admin.")

    otp_storage.pop(emp_docname, None)
    return await show_main_menu(update, context)

async def resend_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resend OTP to user."""
    for emp_docname, (otp, timestamp, email) in otp_storage.items():
        if context.user_data.get("emp_docname") == emp_docname:
            if send_otp_email(email, otp):
                await update.message.reply_text(f"📨 OTP resent to {email}")
                return
    await update.message.reply_text("❌ No OTP session found. Use /id to start.")

# === Leave Application ===
async def apply_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start leave application process."""
    keyboard = [[KeyboardButton("❌ Cancel")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    telegram_id = update.effective_user.id
    employee = get_employee_by_telegram_id(telegram_id)

    if not employee:
        await update.message.reply_text(
            "❌ You're not linked to an Employee in ERP.",
            reply_markup=reply_markup
        )
        return await show_main_menu(update, context)

    context.user_data["employee"] = employee
    try:
        async with aiohttp.ClientSession() as session:
            assignment_url = f"{ERP_URL}/api/resource/Leave Policy Assignment?filters=[[\"employee\",\"=\",\"{employee}\"], [\"docstatus\",\"=\",1]]&fields=[\"leave_policy\"]"
            async with session.get(assignment_url, headers=HEADERS, timeout=5) as res:
                data = await res.json()
                assignments = data.get("data", [])

            if not assignments:
                await update.message.reply_text("❌ No leave policy assigned to your profile.")
                return await show_main_menu(update, context)

            leave_policy = assignments[0]["leave_policy"]

            policy_url = f"{ERP_URL}/api/resource/Leave Policy/{leave_policy}"
            async with session.get(policy_url, headers=HEADERS, timeout=5) as res:
                data = await res.json()
                policy_data = data.get("data", {})
                leave_types = policy_data.get("leave_policy_details", [])

            if not leave_types:
                await update.message.reply_text("❌ No leave types found in your leave policy.")
                return await show_main_menu(update, context)

            keyboard = [
                [InlineKeyboardButton(lt["leave_type"], callback_data=f"leave_type:{lt['leave_type']}")]
                for lt in leave_types
            ]
#            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🗂 Select Leave Type:", reply_markup=reply_markup)

            return LEAVE_TYPE_SELECTION

    except Exception as e:
        logger.exception("Failed in apply_leave")
        await update.message.reply_text("❌ Could not fetch leave types from leave policy.")
        return await show_main_menu(update, context)



async def handle_leave_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leave type selection."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        return await cancel(update, context)

    _, leave_type = query.data.split(":")
    context.user_data["leave_type"] = leave_type

    employee = context.user_data.get("employee")
    try:
        res = requests.get(
            f"{ERP_URL}/api/method/late_minutes.real_bal.get_real_time_leave_balance",
            headers=HEADERS,
            params={
                "employee": employee,
                "leave_type": leave_type,
                "from_date": datetime.today().strftime("%Y-%m-%d")
            }
        )

        balance = "N/A"
        if res.status_code == 200:
            balance = res.json().get("message", "N/A")

        # Clear previous keyboard and show balance
        await query.edit_message_text(
            f"✔ {leave_type} selected.\nLeave Balance: {balance}\n\n📅 Please select FROM date:",
            reply_markup=None
        )

        # Then show the date picker
        return await show_date_picker(update, context, "from")

    except Exception as e:
        logger.exception("Failed to fetch real-time leave balance")
        await query.edit_message_text("❌ Failed to fetch leave balance. Please try again later.")
        return await show_main_menu(update, context)


async def show_date_picker(update, context, which, offset=0):
    """Show date picker for leave dates."""
    base_date = datetime.today()
    start_date = base_date + timedelta(days=offset)
    keyboard = []

    for i in range(7):
        date = start_date + timedelta(days=i)
        label = date.strftime("%a %d %b")
        value = date.strftime("%Y-%m-%d")
        keyboard.append([InlineKeyboardButton(label, callback_data=f"{which}:{value}")])

    prev_offset = offset - 7
    next_offset = offset + 7
    nav_buttons = [
        InlineKeyboardButton("⬅️ Previous", callback_data=f"nav:{which}:{prev_offset}"),
        InlineKeyboardButton("➡️ Next", callback_data=f"nav:{which}:{next_offset}")
    ]

    keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(f"📅 Select {which.replace('_', ' ').title()} Date:", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_reply_markup(reply_markup=reply_markup)

    return SELECT_FROM_DATE if which == "from" else SELECT_TO_DATE

async def handle_calendar_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle calendar navigation."""
    query = update.callback_query
    await query.answer()

    _, which, offset = query.data.split(":")
    offset = int(offset)

    return await show_date_picker(update, context, which, offset)


async def handle_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle date selection for leave."""
    query = update.callback_query
    await query.answer()
    which, date = query.data.split(":")
    context.user_data[f"{which}_date"] = date

    if which == "from":
        return await show_date_picker(query, context, "to")
    else:
        await query.edit_message_text("📝 Enter Reason for Leave:")
        return LEAVE_REASON







async def submit_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Submit leave application."""
    if update.message.text.strip().lower() == "❌ cancel":
        return await cancel(update, context)

    context.user_data["description"] = update.message.text

    payload = {
        "employee": context.user_data["employee"],
        "leave_type": context.user_data["leave_type"],
        "from_date": context.user_data["from_date"],
        "to_date": context.user_data["to_date"],
        "description": context.user_data["description"]
    }

    try:
        res = requests.post(f"{ERP_URL}/api/resource/Leave Application", headers=HEADERS, json=payload)
        if res.status_code == 200:
            await update.message.reply_text("✅ Leave Application Submitted!")
        else:
            await update.message.reply_text("❌ Failed to submit leave.")
    except Exception:
        logger.exception("Error while submitting leave")
        await update.message.reply_text("❌ Server error while submitting leave.")

    return await show_main_menu(update, context)
    
    
    
    
    
    
    
    

# === Checkin/Checkout ===




async def checkinout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start checkin/checkout process."""
    telegram_id = update.effective_user.id
    employee = get_employee_by_telegram_id(telegram_id)
    if not employee:
        await update.message.reply_text("❌ You're not linked to an Employee in ERP.")
        return await show_main_menu(update, context)

    # Get employee's location restrictions first
    try:
        url = f"{ERP_URL}/api/resource/Employee/{employee}"
        res = requests.get(url, headers=HEADERS)
        if res.status_code != 200:
            await update.message.reply_text("❌ Could not fetch your employee details.")
            return await show_main_menu(update, context)

        emp_data = res.json().get("data", {})
        allowed_lat = emp_data.get("custom_allowed_latitude")
        allowed_long = emp_data.get("custom_allowed_longitude")
        allowed_radius = emp_data.get("custom_allowed_radius", 0)

        if None in [allowed_lat, allowed_long]:
            await update.message.reply_text("❌ Your location restrictions are not configured.")
            return await show_main_menu(update, context)

        context.user_data.update({
            "employee": employee,
            "allowed_lat": float(allowed_lat),
            "allowed_long": float(allowed_long),
            "allowed_radius": float(allowed_radius)
        })

    except Exception as e:
        logger.error(f"Error fetching employee restrictions: {e}")
        await update.message.reply_text("❌ Error fetching your location restrictions.")
        return await show_main_menu(update, context)

    keyboard = [
        [KeyboardButton(text="📍 Share Location", request_location=True)],
        [KeyboardButton(text="❌ Cancel")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📍 Please share your current location to proceed with check-in/check-out:",
        reply_markup=reply_markup
    )
    return CHECKINOUT_SELECTION


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in meters using Haversine formula"""
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi/2)**2 + 
         math.cos(phi1) * math.cos(phi2) * 
         math.sin(delta_lambda/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location shared by user"""
    user_location = update.message.location
    if not user_location:
        await update.message.reply_text("❌ Location not received. Please share your location to continue.")
        return await show_main_menu(update, context)

    current_lat = user_location.latitude
    current_long = user_location.longitude
    
    allowed_lat = context.user_data.get("allowed_lat")
    allowed_long = context.user_data.get("allowed_long")
    allowed_radius = context.user_data.get("allowed_radius", 0)

    # Validate location
    distance = calculate_distance(
        allowed_lat, allowed_long,
        current_lat, current_long
    )

    if allowed_radius == 0:
        # Exact location match required
        if not (math.isclose(allowed_lat, current_lat, abs_tol=1e-6) and 
                math.isclose(allowed_long, current_long, abs_tol=1e-6)):
            await update.message.reply_text(
                f"❌ You must be at the exact designated location!\n"
                f"Required location: {allowed_lat:.6f}, {allowed_long:.6f}\n"
                f"Your location: {current_lat:.6f}, {current_long:.6f}"
            )
            return await show_main_menu(update, context)
    elif distance > allowed_radius:
        await update.message.reply_text(
            f"❌ You're too far from your designated location!\n"
            f"Allowed location: {allowed_lat:.6f}, {allowed_long:.6f}\n"
            f"Allowed radius: {allowed_radius:.2f} meters\n"
            f"Your location: {current_lat:.6f}, {current_long:.6f}\n"
            f"Distance: {distance:.2f} meters"
        )
        return await show_main_menu(update, context)

    context.user_data.update({
        "latitude": current_lat,
        "longitude": current_long
    })

    keyboard = [
        [InlineKeyboardButton("🟢 Checkin", callback_data="log_type:IN")],
        [InlineKeyboardButton("🔴 Checkout", callback_data="log_type:OUT")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ Location verified! Please choose:",
        reply_markup=reply_markup
    )
    return CHECKINOUT_SELECTION














async def get_employee_location_restrictions(employee_name):
    """Fetch employee's allowed location and radius from ERP"""
    try:
        url = f"{ERP_URL}/api/resource/Employee/{employee_name}"
        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200:
            data = res.json().get("data", {})
            return {
                "latitude": float(data.get("custom_allowed_latitude", 0)),
                "longitude": float(data.get("custom_allowed_longitude", 0)),
                "radius": float(data.get("custom_allowed_radius", 0))
            }
    except Exception as e:
        logger.error(f"Error fetching employee location restrictions: {e}")
    return None

def validate_location(allowed_loc, current_lat, current_long):
    """Validate if current location is within allowed radius"""
    if allowed_loc["radius"] <= 0:
        return True  # No restriction
    
    # Calculate distance between points using Haversine formula
    lat1, lon1 = math.radians(allowed_loc["latitude"]), math.radians(allowed_loc["longitude"])
    lat2, lon2 = math.radians(current_lat), math.radians(current_long)
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = 6371 * c * 1000  # Distance in meters
    
    return distance <= allowed_loc["radius"]

async def handle_log_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle checkin/checkout button selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        return await cancel(update, context)
    
    try:
        _, log_type = query.data.split(":")
        employee = context.user_data.get("employee")
        latitude = context.user_data.get("latitude")
        longitude = context.user_data.get("longitude")

        checkin_data = {
            "employee": employee,
            "log_type": log_type,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "latitude": latitude,
            "longitude": longitude,
            "geolocation": f"{latitude},{longitude}",
        }

        response = requests.post(
            f"{ERP_URL}/api/resource/Employee Checkin",
            headers=HEADERS,
            json=checkin_data
        )

        await query.edit_message_reply_markup(reply_markup=None)
        
        if response.status_code == 200:
            action = "Checked IN" if log_type == "IN" else "Checked OUT"
            await query.edit_message_text(
                f"✅ {action} successfully at {checkin_data['time']}\n"
                f"Location: {latitude:.6f}, {longitude:.6f}"
            )
        else:
            error_msg = "❌ Failed to record checkin/checkout."
            try:
                error_data = response.json()
                if "exception" in error_data:
                    error_msg += "\n\nServer error: " + error_data.get("exception", "Unknown error")
            except:
                error_msg += f"\n\nStatus: {response.status_code}"
            
            await query.edit_message_text(error_msg)
            
    except Exception as e:
        logger.error(f"Checkin/checkout error: {e}")
        await query.edit_message_text("❌ Error processing your request. Please try again.")
    
    return ConversationHandler.END


# === Main Application ===
def main() -> None:
    """Run the bot."""
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # OTP Verification
    otp_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("id", id_command)],
        states={
            ASK_EMPLOYEE_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_employee_id),
                MessageHandler(filters.Regex(r'^❌ Cancel$'), cancel)
            ],
            ASK_OTP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp),
                MessageHandler(filters.Regex(r'^❌ Cancel$'), cancel)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Leave Application
    leave_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("apply_leave", apply_leave)],
        states={
            LEAVE_TYPE_SELECTION: [CallbackQueryHandler(handle_leave_type_selection, pattern="^leave_type:")],
            SELECT_FROM_DATE: [
                CallbackQueryHandler(handle_date_selection, pattern=r'^(from:|cancel$)'),
                CallbackQueryHandler(handle_calendar_navigation, pattern=r'^nav:from:'),
                MessageHandler(filters.Regex(r'^❌ Cancel$'), cancel)
            ],
            SELECT_TO_DATE: [
                CallbackQueryHandler(handle_date_selection, pattern=r'^(to:|cancel$)'),
                CallbackQueryHandler(handle_calendar_navigation, pattern=r'^nav:to:'),
                MessageHandler(filters.Regex(r'^❌ Cancel$'), cancel)
            ],
            LEAVE_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, submit_leave),
                MessageHandler(filters.Regex(r'^❌ Cancel$'), cancel)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Checkin/Checkout
    checkinout_handler = ConversationHandler(
        entry_points=[CommandHandler("checkinout", checkinout_command)],
        states={
            CHECKINOUT_SELECTION: [
                MessageHandler(filters.LOCATION, handle_location),
                CallbackQueryHandler(handle_log_type_selection, pattern="^(log_type:|cancel)"),
                MessageHandler(filters.Regex(r'^❌ Cancel$'), cancel)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("resend_otp", resend_otp))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(otp_conv_handler)
    application.add_handler(leave_conv_handler)
    application.add_handler(checkinout_handler)
    application.add_handler(MessageHandler(filters.Regex(r'^❌ Cancel$'), cancel))

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
