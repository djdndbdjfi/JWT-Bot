import requests
import json
import os
import tempfile
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# Constants
CHANNEL_LINK = "https://t.me/nr_codex"
BOT_VERSION = "1.0"
BOT_OWNER = "@nilay_vii"
LOGO_URL = "https://i.imgur.com/k3sA1bE.jpeg"  # Tumhara logo URL

# Fetch JWT token from the provided URL
def fetch_token(uid, password):
    url = f"https://ariflexlabs-jwt-gen.onrender.com/fetch-token?uid={uid}&password={password}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('JWT TOKEN'), None
        else:
            return None, f"❌ HTTP Error {response.status_code}"
    except requests.Timeout:
        return None, "⌛ Connection Timeout"
    except Exception as e:
        return None, f"⚠️ Error: {str(e)}"

# Count valid accounts in a JSON file
def count_valid_accounts(file_path):
    try:
        with open(file_path, 'r') as file:
            accounts = json.load(file)
        return sum(1 for account in accounts if account.get('uid') and account.get('password'))
    except:
        return 0

# Process JSON file and generate tokens
def process_json_file(file_path, max_tokens):
    try:
        with open(file_path, 'r') as file:
            accounts = json.load(file)

        tokens = []
        success = 0
        failed = 0

        for idx, account in enumerate(accounts[:max_tokens], 1):
            uid = account.get('uid')
            password = account.get('password')
            if uid and password:
                token, error = fetch_token(uid, password)
                if token:
                    tokens.append({"token": token})
                    success += 1
                else:
                    failed += 1
            else:
                failed += 1
            yield idx / max_tokens * 100, success, failed, tokens
        return
    except:
        yield 0, 0, 0, []

# Save tokens to a JSON file
def save_tokens(tokens, output_file='token_ind.json'):
    try:
        with open(output_file, 'w') as file:
            json.dump(tokens, file, indent=4)
        return output_file
    except Exception as e:
        return f"❌ Error saving tokens: {str(e)}"

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(
        photo=LOGO_URL,
        caption="✨ Welcome to Advanced Token Generator Bot ✨"
    )

    keyboard = [
        [
            InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK),
            InlineKeyboardButton("✅ Check", callback_data="check_channel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Please join our channel before starting the token generation process:\n"
        "Channel link and verification button below:",
        reply_markup=reply_markup
    )

# Check channel callback
async def check_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🇮🇳 IND Server", callback_data="select_ind")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "🌍 Please choose your server:\n\nOther servers will be available soon!",
        reply_markup=reply_markup
    )

# Server selection
async def select_ind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data['mode'] = 'json'
    await query.message.reply_text(
        "🔑 Advanced Token Generator Bot - IND Server\n\n"
        "📤 Please send me a JSON file containing UID/password pairs to begin"
    )

# Handle document
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('mode') != 'json':
        await update.message.reply_text("⚠️ Please use /start and select a server first.")
        return

    document = update.message.document
    if not document.file_name.endswith('.json'):
        await update.message.reply_text("❌ Invalid file type. Please upload a valid JSON file.")
        return

    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp_file:
        file = await document.get_file()
        await file.download_to_drive(tmp_file.name)

        valid_accounts = count_valid_accounts(tmp_file.name)
        if valid_accounts == 0:
            await update.message.reply_text("❌ No valid accounts found in the JSON file.")
            os.remove(tmp_file.name)
            context.user_data['mode'] = None
            return

        context.user_data['file_path'] = tmp_file.name
        context.user_data['valid_accounts'] = valid_accounts
        await update.message.reply_text(
            f"🔍 Found {valid_accounts} valid accounts\n\n"
            f"🔢 How many tokens would you like to generate? (Max {valid_accounts})"
        )
        context.user_data['mode'] = 'token_count'

# Handle token count input
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('mode') != 'token_count':
        await update.message.reply_text("⚠️ Please upload a JSON file first.")
        return

    try:
        max_tokens = int(update.message.text.strip())
        valid_accounts = context.user_data.get('valid_accounts', 0)
        if max_tokens <= 0 or max_tokens > valid_accounts:
            await update.message.reply_text(
                f"❌ Invalid number. Please enter a value between 1 and {valid_accounts}."
            )
            return
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number.")
        return

    file_path = context.user_data.get('file_path')
    if not file_path or not os.path.exists(file_path):
        await update.message.reply_text("❌ Error: File not found. Please start over with /start.")
        context.user_data['mode'] = None
        return

    start_time = time.time()
    processing_msg = await update.message.reply_text(
        "🔄 Processing token generation, please wait..."
    )
    progress_msg = await update.message.reply_text("📊 Progress: [          ] 0%")

    tokens = []
    success = 0
    failed = 0

    for progress, curr_success, curr_failed, new_tokens in process_json_file(file_path, max_tokens):
        success, failed = curr_success, curr_failed
        tokens = new_tokens
        bars = int(progress // 10)
        progress_bar = f"📊 Progress: [{'█' * bars}{' ' * (10 - bars)}] {int(progress)}%"
        await progress_msg.edit_text(progress_bar)
        time.sleep(0.1)

    end_time = time.time()
    processing_time = int(end_time - start_time)

    await processing_msg.edit_text("✅ Generation Complete!")
    await progress_msg.edit_text(
        f"📊 Final Results:\n"
        f"✔️ Success: {success}\n"
        f"✖️ Failed: {failed}\n"
        f"⏱️ Time Taken: {processing_time} seconds"
    )

    if tokens:
        output_file = save_tokens(tokens)
        if isinstance(output_file, str) and not output_file.startswith("❌"):
            await update.message.reply_document(
                document=open(output_file, 'rb'),
                caption="🔑 Your generated tokens file"
            )
            os.remove(output_file)

    os.remove(file_path)
    context.user_data.clear()

# Main
def main():
    application = Application.builder().token('YOUR_BOT_TOKEN_HERE').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(check_channel, pattern='check_channel'))
    application.add_handler(CallbackQueryHandler(select_ind, pattern='select_ind'))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()    main()
