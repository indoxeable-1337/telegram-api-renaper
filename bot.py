#!/usr/bin/env python3
"""
Telegram Bot for identity queries (RENAPER), basic lookups, people search (CuitOnline),
IP geolocation, and a token-based usage system.

Author: indoxeable

Configuration:
  1. Set TELEGRAM_TOKEN to the bot token from @BotFather.
  2. Set RENAPER_API_BASE to the base URL of the RENAPER API (e.g., "http://ip:port/renaper").
  3. Set STAFF_IDS to a list of Telegram user IDs that can manage tokens.
  4. Install required packages:
         pip install python-telegram-bot aiohttp cuitonline

The bot uses a JSON file (tokens.json) to persist token balances.
"""

import os
import json
import base64
import io
import aiohttp
import traceback
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ==================== CONFIGURATION ====================
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"  # Obtain from @BotFather
RENAPER_API_BASE = "renaper api"  # Base URL of the RENAPER API
STAFF_IDS = [123456789, 987654321]  # Telegram IDs of staff users

# ==================== TOKEN MANAGEMENT ====================
TOKENS_FILE = "tokens.json"

def load_tokens():
    """Load token balances from the JSON file."""
    if not os.path.exists(TOKENS_FILE):
        return {}
    with open(TOKENS_FILE, "r") as f:
        return json.load(f)

def save_tokens(tokens):
    """Save token balances to the JSON file."""
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

def get_tokens(user_id):
    """Return the token balance for a given user ID."""
    return load_tokens().get(str(user_id), 0)

def add_tokens(user_id, amount):
    """Add tokens to a user and return the new balance."""
    tokens_data = load_tokens()
    uid = str(user_id)
    tokens_data[uid] = tokens_data.get(uid, 0) + amount
    save_tokens(tokens_data)
    return tokens_data[uid]

def remove_tokens(user_id, amount):
    """
    Remove tokens from a user if they have enough.
    Returns (new_balance, success).
    """
    tokens_data = load_tokens()
    uid = str(user_id)
    current = tokens_data.get(uid, 0)
    if current < amount:
        return current, False
    tokens_data[uid] = current - amount
    if tokens_data[uid] == 0:
        del tokens_data[uid]
    save_tokens(tokens_data)
    return tokens_data.get(uid, 0), True

def spend_tokens(user_id, amount=1):
    """Spend (consume) tokens. Returns (new_balance, success)."""
    return remove_tokens(user_id, amount)

def is_staff(user_id):
    """Check if a user is in the staff list."""
    return user_id in STAFF_IDS

# ==================== COMMAND: /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 <b>RENAPER BOT</b>\n"
        "Use <b>/commands</b> to see what I can do.\n"
        "Queries consume tokens."
    )
    await update.message.reply_text(text, parse_mode="HTML")

# ==================== COMMAND: /commands ====================
async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 <b>AVAILABLE COMMANDS</b>\n\n"
        "<b>🔍 Queries</b>\n"
        "  <code>/renaper &lt;dni&gt; &lt;sex&gt;</code>   Full data <b>(3 tokens)</b>\n"
        "  <code>/basic &lt;dni&gt; &lt;sex&gt;</code>     Name, DNI and birth date <b>(1 token)</b>\n"
        "  <code>/search &lt;full name&gt;</code>   Look up person in CUIT <b>(1 token)</b>\n\n"
        "<b>🌍 Geolocation</b>\n"
        "  <code>/geolocate &lt;ip&gt;</code>   Geolocate an IP address <b>(Free)</b>\n\n"
        "<b>💰 Tokens</b>\n"
        "  <code>/me</code>   Check your balance and Telegram ID\n"
        "  <code>/addtokens &lt;id&gt; &lt;amount&gt;</code>   Add tokens (Staff)\n"
        "  <code>/removetokens &lt;id&gt; &lt;amount&gt;</code>   Remove tokens (Staff)\n"
        "  <code>/staff</code>   List staff members\n\n"
        "<b>ℹ️ Help</b>\n"
        "  <code>/commands</code>   Show this message"
    )
    await update.message.reply_text(text, parse_mode="HTML")

# ==================== COMMAND: /me ====================
async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = get_tokens(user_id)
    text = (
        f"💰 <b>MY TOKENS</b>\n\n"
        f"• <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"• <b>Balance:</b> {balance} token(s)\n\n"
        f"<i>Give your ID to staff to receive tokens.</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")

# ==================== COMMAND: /staff ====================
async def staff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🛡️ <b>AUTHORIZED STAFF</b>\n"
    for uid in STAFF_IDS:
        text += f"• <code>{uid}</code>\n"
    await update.message.reply_text(text, parse_mode="HTML")

# ==================== COMMAND: /addtokens (STAFF ONLY) ====================
async def addtokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_staff(update.effective_user.id):
        await update.message.reply_text("❌ You do not have staff permissions.")
        return
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Usage: <code>/addtokens &lt;user_id&gt; &lt;amount&gt;</code>",
            parse_mode="HTML"
        )
        return
    if amount <= 0:
        await update.message.reply_text("❌ Amount must be positive.")
        return
    new_balance = add_tokens(user_id, amount)
    await update.message.reply_text(
        f"✅ Added <b>{amount}</b> token(s) to user <code>{user_id}</code>. "
        f"New balance: <b>{new_balance}</b>",
        parse_mode="HTML"
    )

# ==================== COMMAND: /removetokens (STAFF ONLY) ====================
async def removetokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_staff(update.effective_user.id):
        await update.message.reply_text("❌ You do not have staff permissions.")
        return
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Usage: <code>/removetokens &lt;user_id&gt; &lt;amount&gt;</code>",
            parse_mode="HTML"
        )
        return
    if amount <= 0:
        await update.message.reply_text("❌ Amount must be positive.")
        return
    new_balance, success = remove_tokens(user_id, amount)
    if not success:
        await update.message.reply_text(
            f"❌ User only has <b>{new_balance}</b> token(s).",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            f"✅ Removed <b>{amount}</b> token(s) from <code>{user_id}</code>. "
            f"Remaining balance: <b>{new_balance}</b>",
            parse_mode="HTML"
        )

# ==================== COMMAND: /renaper (FULL DATA - 3 TOKENS) ====================
async def renaper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        dni = context.args[0]
        sex = context.args[1].upper()
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Usage: <code>/renaper &lt;dni&gt; &lt;sex&gt;</code> (sex: M or F)",
            parse_mode="HTML"
        )
        return
    if not dni.isdigit() or len(dni) not in (7, 8):
        await update.message.reply_text("❌ Invalid DNI. Must be 7 or 8 digits.")
        return
    if sex not in ("M", "F"):
        await update.message.reply_text("❌ Invalid sex. Use M or F.")
        return

    user_id = update.effective_user.id
    balance = get_tokens(user_id)
    if balance < 3:
        await update.message.reply_text(f"❌ You need 3 tokens. Your balance: {balance}")
        return
    new_balance, ok = spend_tokens(user_id, 3)
    if not ok:
        await update.message.reply_text("❌ Error spending tokens.")
        return

    msg = await update.message.reply_text("🔄 Querying RENAPER...")
    url = f"{RENAPER_API_BASE}/{dni}/{sex}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Build a nicely formatted response
                    surname = data.get("apellido", "N/A")
                    names = data.get("nombres", "N/A")
                    birth = data.get("fechaNacimiento", "N/A")
                    gender = data.get("sexo", "N/A")
                    doc = data.get("numeroDocumento", "N/A")
                    cuil = data.get("cuil", "N/A")
                    exemplar = data.get("ejemplar", "N/A")
                    issue_date = data.get("emision", "N/A")
                    expiry = data.get("vencimiento", "N/A")
                    tr_id = data.get("idtramiteprincipal", "N/A")

                    street = data.get("calle", "")
                    number = data.get("numero", "")
                    floor = data.get("piso", "")
                    apt = data.get("departamento", "")
                    neighborhood = data.get("barrio", "0")
                    postal = data.get("cpostal", "")
                    city = data.get("ciudad", "").replace("_", " ")
                    province = data.get("provincia", "").replace("_", " ")
                    country = data.get("pais", "")

                    address = f"{street} {number}"
                    if floor: address += f", Floor {floor}"
                    if apt: address += f", Apt {apt}"

                    text = (
                        f"📄 <b>RENAPER REPORT</b>\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"<b>👤 Personal Data</b>\n"
                        f"• <b>Surname, Names:</b> {surname}, {names}\n"
                        f"• <b>DNI:</b> {doc}\n"
                        f"• <b>CUIL:</b> {cuil}\n"
                        f"• <b>Date of Birth:</b> {birth}\n"
                        f"• <b>Gender:</b> {gender}\n"
                        f"• <b>Specimen:</b> {exemplar}\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"<b>📅 Document</b>\n"
                        f"• <b>Issue Date:</b> {issue_date}\n"
                        f"• <b>Expiry Date:</b> {expiry}\n"
                        f"• <b>Processing ID:</b> {tr_id}\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"<b>🏠 Address</b>\n"
                        f"• <b>Street:</b> {address}\n"
                        f"• <b>Neighborhood:</b> {neighborhood if neighborhood != '0' else 'Not specified'}\n"
                        f"• <b>City:</b> {city}\n"
                        f"• <b>Province:</b> {province}\n"
                        f"• <b>Postal Code:</b> {postal}\n"
                        f"• <b>Country:</b> {country}\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"<b>ℹ️ Additional Info</b>\n"
                        f"• <b>Death Notice:</b> {data.get('mensaf','N/A')}\n"
                        f"• <b>Source:</b> {data.get('origenf','N/A')}\n"
                        f"• <b>Description:</b> {data.get('descripcionError','N/A')}"
                    )

                    pdf = data.get("pdf417", {})
                    if pdf and pdf.get("base64"):
                        img_data = pdf["base64"]
                        if img_data.startswith("data:"):
                            img_data = img_data.split(",", 1)[1]
                        img_bytes = base64.b64decode(img_data)
                        await msg.delete()
                        await update.message.reply_photo(
                            photo=io.BytesIO(img_bytes),
                            caption=text,
                            parse_mode="HTML"
                        )
                    else:
                        await msg.edit_text(text, parse_mode="HTML")
                elif resp.status == 404:
                    await msg.edit_text("🔍 Person not found.")
                else:
                    await msg.edit_text(f"⚠️ Server error (code {resp.status}).")
    except aiohttp.ClientError:
        await msg.edit_text("❌ Connection error.")
    except Exception as e:
        await msg.edit_text("❌ Unexpected error.")
        print(f"Error in renaper: {e}")

# ==================== COMMAND: /basic (REDUCED - 1 TOKEN) ====================
async def basic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        dni = context.args[0]
        sex = context.args[1].upper()
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ Usage: <code>/basic &lt;dni&gt; &lt;sex&gt;</code>",
            parse_mode="HTML"
        )
        return
    if not dni.isdigit() or len(dni) not in (7, 8):
        await update.message.reply_text("❌ Invalid DNI.")
        return
    if sex not in ("M", "F"):
        await update.message.reply_text("❌ Invalid sex.")
        return

    user_id = update.effective_user.id
    balance = get_tokens(user_id)
    if balance < 1:
        await update.message.reply_text(f"❌ You need 1 token. Balance: {balance}")
        return
    new_balance, ok = spend_tokens(user_id, 1)
    if not ok:
        await update.message.reply_text("❌ Error spending token.")
        return

    msg = await update.message.reply_text("🔄 Querying (basic)...")
    url = f"{RENAPER_API_BASE}/{dni}/{sex}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    surname = data.get("apellido", "N/A")
                    names = data.get("nombres", "N/A")
                    doc = data.get("numeroDocumento", "N/A")
                    birth = data.get("fechaNacimiento", "N/A")
                    text = (
                        f"📋 <b>BASIC REPORT</b>\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"• <b>Full Name:</b> {surname}, {names}\n"
                        f"• <b>DNI:</b> {doc}\n"
                        f"• <b>Date of Birth:</b> {birth}"
                    )
                    await msg.edit_text(text, parse_mode="HTML")
                elif resp.status == 404:
                    await msg.edit_text("🔍 Person not found.")
                else:
                    await msg.edit_text(f"⚠️ Server error ({resp.status}).")
    except aiohttp.ClientError:
        await msg.edit_text("❌ Connection error.")
    except Exception as e:
        await msg.edit_text("❌ Unexpected error.")
        print(f"Error in basic: {e}")

# ==================== COMMAND: /search (CUITONLINE - 1 TOKEN) ====================
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: <code>/search &lt;full name&gt;</code>",
            parse_mode="HTML"
        )
        return
    query = " ".join(context.args)
    user_id = update.effective_user.id
    balance = get_tokens(user_id)
    if balance < 1:
        await update.message.reply_text(f"❌ You need 1 token. Balance: {balance}")
        return
    new_balance, ok = spend_tokens(user_id, 1)
    if not ok:
        await update.message.reply_text("❌ Error spending token.")
        return

    msg = await update.message.reply_text("🔎 Searching CUIT database...")
    try:
        import cuitonline
        people = cuitonline.search(query)
        if not people:
            await msg.edit_text("🤷 No results found.")
            return

        # Build list of tuples with extracted data
        entries = []
        for p in people:
            parts = p.cuit.split("-")
            dni = parts[1] if len(parts) == 3 else "N/A"
            if p.monotributo:
                activity = f"Monotributo ({p.monotributo})"
            elif p.empleador:
                activity = "Employer"
            elif getattr(p, 'iva', None) or getattr(p, 'ganancias', None):
                activity = "Registered AFIP"
            else:
                activity = "No AFIP activity"
            province = p.provincia if p.provincia else "Unspecified"
            city = p.localidad if p.localidad else ""
            location = f"{city}, {province}" if city else province
            entries.append((p.nombre, p.cuit, dni, activity, location))

        items_per_page = 10
        total_pages = (len(entries) + items_per_page - 1) // items_per_page

        def build_text(page):
            start = page * items_per_page
            end = start + items_per_page
            text = f"🔍 <b>RESULTS FOR:</b> {query}\nPage {page+1} of {total_pages}\n\n"
            for i, (name, cuit, dni, act, loc) in enumerate(entries[start:end], start=start+1):
                text += (
                    f"<b>{i}. {name}</b>\n"
                    f"   🆔 DNI: {dni} | 🏷️ CUIT: {cuit}\n"
                    f"   💼 {act} | 📍 {loc}\n\n"
                )
            return text

        keyboard = []
        if total_pages > 1:
            keyboard = [[
                InlineKeyboardButton("⬅️ Previous", callback_data=f"search_0_{query}"),
                InlineKeyboardButton("➡️ Next", callback_data=f"search_1_{query}")
            ]]
        markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await msg.edit_text(build_text(0), parse_mode="HTML", reply_markup=markup)
        context.user_data['search_data'] = entries
        context.user_data['search_query'] = query

    except ImportError:
        await msg.edit_text("❌ The <code>cuitonline</code> library is not installed.", parse_mode="HTML")
    except Exception as e:
        await msg.edit_text("❌ Search error.")
        print(f"Error in search: {e}")

async def search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    if data[0] != "search":
        return
    page = int(data[1])
    q = data[2]
    entries = context.user_data.get('search_data')
    if not entries:
        await query.edit_message_text("⏰ Search expired.")
        return

    items_per_page = 10
    total_pages = (len(entries) + items_per_page - 1) // items_per_page
    if page < 0 or page >= total_pages:
        return

    start = page * items_per_page
    end = start + items_per_page
    text = f"🔍 <b>RESULTS FOR:</b> {q}\nPage {page+1} of {total_pages}\n\n"
    for i, (name, cuit, dni, act, loc) in enumerate(entries[start:end], start=start+1):
        text += (
            f"<b>{i}. {name}</b>\n"
            f"   🆔 DNI: {dni} | 🏷️ CUIT: {cuit}\n"
            f"   💼 {act} | 📍 {loc}\n\n"
        )

    nav = []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"search_{page-1}_{q}"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton("➡️ Next", callback_data=f"search_{page+1}_{q}"))
    if row:
        nav.append(row)
    markup = InlineKeyboardMarkup(nav) if nav else None
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)

# ==================== COMMAND: /geolocate (IP Geolocation) ====================
async def geolocate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: <code>/geolocate &lt;ip&gt;</code>\n"
            "Example: <code>/geolocate 8.8.8.8</code>",
            parse_mode="HTML"
        )
        return

    ip = context.args[0].strip()
    msg = await update.message.reply_text(f"🌍 Geolocating <code>{ip}</code>...", parse_mode="HTML")

    # Using free ip-api.com (no key needed, 45 req/min)
    url = f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await msg.edit_text(f"⚠️ Geolocation service error (code {resp.status}).")
                    return
                data = await resp.json()
                if data.get("status") != "success":
                    await msg.edit_text(f"❌ Could not geolocate IP.\nReason: {data.get('message', 'Unknown')}")
                    return

                text = (
                    f"🌍 <b>IP GEOLOCATION</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📌 <b>Queried IP:</b> <code>{data['query']}</code>\n\n"
                    f"<b>📍 Location</b>\n"
                    f"• Country: {data.get('country', 'N/A')} ({data.get('countryCode', '')})\n"
                    f"• Region: {data.get('regionName', 'N/A')}\n"
                    f"• City: {data.get('city', 'N/A')}\n"
                    f"• Postal Code: {data.get('zip', 'N/A')}\n\n"
                    f"<b>🌐 Network</b>\n"
                    f"• ISP: {data.get('isp', 'N/A')}\n"
                    f"• Organization: {data.get('org', 'N/A')}\n"
                    f"• AS: {data.get('as', 'N/A')}\n\n"
                    f"<b>🗺️ Coordinates</b>\n"
                    f"• Latitude: {data.get('lat', 'N/A')}\n"
                    f"• Longitude: {data.get('lon', 'N/A')}\n\n"
                    f"<b>🕐 Timezone</b>\n"
                    f"• {data.get('timezone', 'N/A')}"
                )
                await msg.edit_text(text, parse_mode="HTML")

    except aiohttp.ClientError:
        await msg.edit_text("❌ Could not connect to geolocation service.")
    except Exception as e:
        await msg.edit_text("❌ Unexpected error.")
        print(f"Error in geolocate: {e}")

# ==================== ERROR HANDLER ====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error: {context.error}")
    traceback.print_exc()

# ==================== MAIN ====================
def main():
    if not os.path.exists(TOKENS_FILE):
        save_tokens({})

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register all commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("commands", commands))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("staff", staff))
    app.add_handler(CommandHandler("addtokens", addtokens))
    app.add_handler(CommandHandler("removetokens", removetokens))
    app.add_handler(CommandHandler("renaper", renaper))
    app.add_handler(CommandHandler("basic", basic))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("geolocate", geolocate))
    app.add_handler(CallbackQueryHandler(search_callback, pattern="^search_"))
    app.add_error_handler(error_handler)

    print("Bot started. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
