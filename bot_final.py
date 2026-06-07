import json
import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ─────────────────────────────────────────────
# تنظیمات
# ─────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN")   # ← توکن ربات خودت رو اینجا بذار
DATA_FILE = "data.json"

logging.basicConfig(level=logging.INFO)

# ─────────────────────────────────────────────
# وضعیت‌های ConversationHandler
# ─────────────────────────────────────────────
WAITING_MESSAGE   = 1   # منتظر دریافت پیام VPN
WAITING_PRICE     = 2   # منتظر دریافت قیمت فروش


# ─────────────────────────────────────────────
# توابع کمکی JSON
# ─────────────────────────────────────────────
def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"messages": [], "saeed_account": 0, "sales_profit": 0}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# استخراج یوزرنیم و لینک از پیام
# ─────────────────────────────────────────────
def extract_info(text: str) -> dict:
    username_match = re.search(r"Username:\s*(\S+)", text)
    link_match = re.search(r"(https?://\S+)", text)
    return {
        "username": username_match.group(1) if username_match else "ناشناس",
        "link": link_match.group(1) if link_match else "لینکی یافت نشد",
        "raw": text,
    }


# ─────────────────────────────────────────────
# کیبورد اصلی
# ─────────────────────────────────────────────
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ اضافه کردن پیام",     callback_data="add_msg")],
        [InlineKeyboardButton("📩 دریافت ۱ کاربر",      callback_data="get_one")],
        [InlineKeyboardButton("🔢 تعداد پیام‌ها",        callback_data="count")],
        [InlineKeyboardButton("💰 فروش رفته",           callback_data="sales_menu")],
        [InlineKeyboardButton("📊 سود فروش",            callback_data="profit_menu")],
    ])


# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! 👋 به ربات مدیریت کاربران خوش اومدی.",
        reply_markup=main_keyboard()
    )


# ─────────────────────────────────────────────
# اضافه کردن پیام ─ شروع
# ─────────────────────────────────────────────
async def add_msg_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("پیام VPN رو بفرست 👇")
    return WAITING_MESSAGE


async def add_msg_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    info = extract_info(text)
    data = load_data()
    data["messages"].append(info)
    save_data(data)
    await update.message.reply_text(
        f"✅ ذخیره شد!\n👤 یوزرنیم: {info['username']}\n🔗 لینک: {info['link']}",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────
# دریافت ۱ کاربر
# ─────────────────────────────────────────────
async def get_one(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    if not data["messages"]:
        await query.message.reply_text("❌ هیچ پیامی ذخیره نشده.", reply_markup=main_keyboard())
        return

    msg = data["messages"][0]
    text = (
        f"👤 یوزرنیم: {msg['username']}\n"
        f"🔗 لینک: {msg['link']}\n\n"
        f"━━━━━━━━━━━━━━\n{msg['raw']}"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ فروخته شد",  callback_data="sold")],
        [InlineKeyboardButton("❌ کنسل",       callback_data="cancel_get")],
    ])
    await query.message.reply_text(text, reply_markup=keyboard)


# ─────────────────────────────────────────────
# فروخته شد ─ شروع
# ─────────────────────────────────────────────
async def sold_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("💵 چقدر فروختی؟ (عدد بنویس)")
    return WAITING_PRICE


async def sold_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد وارد کن.")
        return WAITING_PRICE

    data = load_data()
    if data["messages"]:
        data["messages"].pop(0)          # حذف اولین پیام

    profit = price - 100
    data["saeed_account"] = data.get("saeed_account", 0) + 100
    data["sales_profit"]  = data.get("sales_profit",  0) + profit
    save_data(data)

    await update.message.reply_text(
        f"✅ ثبت شد!\n"
        f"💰 قیمت فروش: {price:,.0f}\n"
        f"📈 سود این فروش: {profit:,.0f}\n"
        f"👤 حساب سعید: +100 (جمع: {data['saeed_account']:,.0f})",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────
# کنسل
# ─────────────────────────────────────────────
async def cancel_get(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("↩️ بازگشت به منو.", reply_markup=main_keyboard())
    return ConversationHandler.END

async def cancel_conv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("↩️ لغو شد.", reply_markup=main_keyboard())
    return ConversationHandler.END


# ─────────────────────────────────────────────
# تعداد پیام‌ها
# ─────────────────────────────────────────────
async def count_msgs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    n = len(data["messages"])
    await query.message.reply_text(f"📦 تعداد پیام‌های ذخیره‌شده: {n}", reply_markup=main_keyboard())


# ─────────────────────────────────────────────
# منوی فروش رفته (حساب سعید)
# ─────────────────────────────────────────────
async def sales_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تسویه شد",  callback_data="settle_saeed")],
        [InlineKeyboardButton("↩️ بازگشت",    callback_data="back_main")],
    ])
    await query.message.reply_text(
        f"👤 حساب سعید: {data.get('saeed_account', 0):,.0f} تومان\n(به ازای هر فروش +۱۰۰)",
        reply_markup=keyboard
    )


async def settle_saeed(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    data["saeed_account"] = 0
    save_data(data)
    await query.message.reply_text("✅ حساب سعید صفر شد.", reply_markup=main_keyboard())


# ─────────────────────────────────────────────
# منوی سود فروش
# ─────────────────────────────────────────────
async def profit_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تسویه شد",  callback_data="settle_profit")],
        [InlineKeyboardButton("↩️ بازگشت",    callback_data="back_main")],
    ])
    await query.message.reply_text(
        f"📊 سود فروش: {data.get('sales_profit', 0):,.0f} تومان\n(قیمت فروش منهای ۱۰۰)",
        reply_markup=keyboard
    )


async def settle_profit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    data["sales_profit"] = 0
    save_data(data)
    await query.message.reply_text("✅ سود فروش صفر شد.", reply_markup=main_keyboard())


# ─────────────────────────────────────────────
# بازگشت به منو اصلی
# ─────────────────────────────────────────────
async def back_main(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("منوی اصلی:", reply_markup=main_keyboard())


# ─────────────────────────────────────────────
# اجرا
# ─────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler برای اضافه کردن پیام
    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_msg_start, pattern="^add_msg$")],
        states={WAITING_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_msg_receive)]},
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    # ConversationHandler برای فروخته شد
    sold_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(sold_start, pattern="^sold$")],
        states={WAITING_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sold_price)]},
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_conv)
    app.add_handler(sold_conv)
    app.add_handler(CallbackQueryHandler(get_one,        pattern="^get_one$"))
    app.add_handler(CallbackQueryHandler(count_msgs,     pattern="^count$"))
    app.add_handler(CallbackQueryHandler(sales_menu,     pattern="^sales_menu$"))
    app.add_handler(CallbackQueryHandler(settle_saeed,   pattern="^settle_saeed$"))
    app.add_handler(CallbackQueryHandler(profit_menu,    pattern="^profit_menu$"))
    app.add_handler(CallbackQueryHandler(settle_profit,  pattern="^settle_profit$"))
    app.add_handler(CallbackQueryHandler(cancel_get,     pattern="^cancel_get$"))
    app.add_handler(CallbackQueryHandler(back_main,      pattern="^back_main$"))

    print("ربات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()
