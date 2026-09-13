
import asyncio
import os
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 7464364112

CHANNEL_USERNAME = "@apnaxstore"
CHANNEL_LINK = "https://t.me/apnaxstore"

GROUP_ID = -1004462426006
GROUP_LINK = "https://t.me/+MRaSyFL47X40ZjU9"

UPI_ID = "rohitpalpersonal-2@okicici"

MIN_RECHARGE = 10
MAX_RECHARGE = 10000

DB_FILE = BASE_DIR / "apnastore.db"


# =========================================================
# DATABASE
# =========================================================

db = sqlite3.connect(DB_FILE, check_same_thread=False)
db.row_factory = sqlite3.Row
db.execute("PRAGMA journal_mode=WAL")
db.execute("PRAGMA foreign_keys=ON")


def init_db():
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        balance REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS wallet_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        type TEXT NOT NULL,
        description TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'Digital Products',
        price REAL NOT NULL,
        description TEXT DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        item TEXT NOT NULL,
        sold INTEGER NOT NULL DEFAULT 0,
        sold_to INTEGER,
        sold_at TEXT,
        FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        stock_id INTEGER,
        amount REAL NOT NULL,
        item TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS recharge_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        utr TEXT NOT NULL,
        screenshot_file_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        admin_note TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        reviewed_at TEXT
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)
    db.commit()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_user(user):
    db.execute("""
        INSERT INTO users(user_id, first_name, username, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            first_name=excluded.first_name,
            username=excluded.username
    """, (user.id, user.first_name or "", user.username or "", now()))
    db.commit()


def get_balance(user_id):
    row = db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()
    return float(row["balance"]) if row else 0.0


def get_setting(key):
    row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(key, value):
    db.execute("""
        INSERT INTO settings(key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))
    db.commit()


# =========================================================
# FSM STATES
# =========================================================

class RechargeStates(StatesGroup):
    waiting_amount = State()
    waiting_utr = State()
    waiting_screenshot = State()


class ProductStates(StatesGroup):
    waiting_name = State()
    waiting_category = State()
    waiting_price = State()
    waiting_description = State()


class StockStates(StatesGroup):
    waiting_product_id = State()
    waiting_items = State()


class WalletStates(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()


# =========================================================
# BOT
# =========================================================

dp = Dispatcher()


def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍️ SHOP NOW", callback_data="shop")],
        [InlineKeyboardButton(text="💰 WALLET", callback_data="wallet"),
         InlineKeyboardButton(text="📦 MY ORDERS", callback_data="orders")],
        [InlineKeyboardButton(text="🔥 TODAY'S DEALS", callback_data="deals")],
        [InlineKeyboardButton(text="🎁 REFER & EARN", callback_data="refer"),
         InlineKeyboardButton(text="💬 SUPPORT", callback_data="support")],
    ])


def join_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 JOIN OFFICIAL CHANNEL", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="👥 JOIN COMMUNITY GROUP", url=GROUP_LINK)],
        [InlineKeyboardButton(text="✅ VERIFY MEMBERSHIP", callback_data="verify_membership")],
    ])


def back_home_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 HOME", callback_data="home")]
    ])


# =========================================================
# START + VERIFY
# =========================================================

@dp.message(CommandStart())
async def start_handler(message: Message):
    ensure_user(message.from_user)

    text = (
        "🛍️ <b>WELCOME TO APNASTORE</b>\n\n"
        "Your Digital Store 🚀\n\n"
        "🎬 Entertainment\n"
        "🎟️ Coupons & Vouchers\n"
        "💎 Digital Products\n\n"
        "⚡ Fast Delivery • 💰 Best Deals\n"
        "🔐 Secure & Trusted Service\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔐 <b>JOIN TO CONTINUE</b>\n\n"
        "Join our official channel and community group.\n"
        "Then tap <b>VERIFY MEMBERSHIP</b>.\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await message.answer(text, reply_markup=join_keyboard(), parse_mode="HTML")


@dp.callback_query(F.data == "verify_membership")
async def verify_membership(callback: CallbackQuery):
    user_id = callback.from_user.id

    try:
        channel_member = await callback.bot.get_chat_member(
            chat_id=CHANNEL_USERNAME, user_id=user_id
        )
        group_member = await callback.bot.get_chat_member(
            chat_id=GROUP_ID, user_id=user_id
        )

        valid_status = {"member", "administrator", "creator"}
        valid_channel = channel_member.status in valid_status
        valid_group = group_member.status in valid_status

        if valid_channel and valid_group:
            await callback.message.edit_text(
                f"🎉 <b>VERIFICATION SUCCESSFUL!</b>\n\n"
                f"Welcome to <b>ApnaStore</b>, {callback.from_user.first_name}! 👋\n\n"
                "Your digital shopping experience starts here. 🛍️\n\n"
                "⚡ Fast Delivery\n"
                "💰 Best Deals\n"
                "🔐 Secure Service\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "<b>Choose an option below:</b>",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML"
            )
            await callback.answer("✅ Membership verified!")
        else:
            missing = []
            if not valid_channel:
                missing.append("📢 Channel")
            if not valid_group:
                missing.append("👥 Group")
            await callback.answer(
                "❌ Please join:\n\n" + "\n".join(missing),
                show_alert=True
            )

    except Exception as e:
        print("Verification error:", e)
        await callback.answer(
            "⚠️ Verification error. Make sure the bot is admin in the channel/group.",
            show_alert=True
        )


# =========================================================
# HOME
# =========================================================

@dp.callback_query(F.data == "home")
async def home_handler(callback: CallbackQuery):
    ensure_user(callback.from_user)
    await callback.message.edit_text(
        f"🏠 <b>APNASTORE</b>\n\n"
        f"Welcome back, {callback.from_user.first_name}! 👋\n\n"
        "🛍️ Your Digital Store\n"
        "⚡ Fast Delivery\n"
        "💰 Best Deals\n"
        "🔐 Secure Service\n\n"
        "<b>Choose an option below:</b>",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# =========================================================
# WALLET
# =========================================================

def wallet_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ ADD BALANCE", callback_data="add_balance")],
        [InlineKeyboardButton(text="📜 TRANSACTIONS", callback_data="transactions")],
        [InlineKeyboardButton(text="🏠 HOME", callback_data="home")]
    ])


@dp.callback_query(F.data == "wallet")
async def wallet_handler(callback: CallbackQuery):
    ensure_user(callback.from_user)
    balance = get_balance(callback.from_user.id)

    await callback.message.edit_text(
        "💰 <b>MY WALLET</b>\n\n"
        f"💳 Current Balance: <b>₹{balance:.2f}</b>\n\n"
        "Use <b>ADD BALANCE</b> to recharge your wallet.",
        reply_markup=wallet_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


def recharge_amount_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="₹50", callback_data="recharge_amt:50"),
         InlineKeyboardButton(text="₹100", callback_data="recharge_amt:100")],
        [InlineKeyboardButton(text="₹200", callback_data="recharge_amt:200"),
         InlineKeyboardButton(text="₹500", callback_data="recharge_amt:500")],
        [InlineKeyboardButton(text="₹1000", callback_data="recharge_amt:1000")],
        [InlineKeyboardButton(text="✏️ CUSTOM AMOUNT", callback_data="recharge_custom")],
        [InlineKeyboardButton(text="⬅️ BACK", callback_data="wallet")]
    ])


async def show_payment_instructions(message: Message, amount: float):
    qr_file_id = get_setting("upi_qr_file_id")

    text = (
        "💳 <b>ADD BALANCE</b>\n\n"
        f"💰 Amount: <b>₹{amount:.2f}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📲 <b>PAYMENT DETAILS</b>\n\n"
        f"UPI ID:\n<code>{UPI_ID}</code>\n\n"
        "1️⃣ Open your UPI app\n"
        "2️⃣ Send the exact amount\n"
        "3️⃣ Complete the payment\n"
        "4️⃣ Keep your UTR / Transaction ID ready\n"
        "5️⃣ Submit the payment proof below\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 SUBMIT PAYMENT", callback_data=f"submit_recharge:{amount}")],
        [InlineKeyboardButton(text="⬅️ BACK", callback_data="add_balance")]
    ])

    if qr_file_id:
        await message.answer_photo(
            photo=qr_file_id,
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query(F.data == "add_balance")
async def add_balance_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "💰 <b>ADD BALANCE</b>\n\n"
        "Select a recharge amount:\n\n"
        f"Minimum: ₹{MIN_RECHARGE}\n"
        f"Maximum: ₹{MAX_RECHARGE}",
        reply_markup=recharge_amount_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("recharge_amt:"))
async def fixed_recharge_amount(callback: CallbackQuery, state: FSMContext):
    amount = float(callback.data.split(":")[1])
    await state.update_data(recharge_amount=amount)
    await show_payment_instructions(callback.message, amount)
    await callback.answer()


@dp.callback_query(F.data == "recharge_custom")
async def custom_recharge(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RechargeStates.waiting_amount)
    await callback.message.edit_text(
        "✏️ <b>CUSTOM RECHARGE</b>\n\n"
        f"Enter amount between ₹{MIN_RECHARGE} and ₹{MAX_RECHARGE}.\n\n"
        "Example: <code>750</code>",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(RechargeStates.waiting_amount)
async def custom_amount_received(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("❌ Please enter a valid number.")
        return

    if amount < MIN_RECHARGE or amount > MAX_RECHARGE:
        await message.answer(
            f"❌ Amount must be between ₹{MIN_RECHARGE} and ₹{MAX_RECHARGE}."
        )
        return

    amount = round(amount, 2)
    await state.update_data(recharge_amount=amount)
    await state.clear()
    await show_payment_instructions(message, amount)


@dp.callback_query(F.data.startswith("submit_recharge:"))
async def submit_recharge_start(callback: CallbackQuery, state: FSMContext):
    amount = float(callback.data.split(":")[1])

    await state.update_data(recharge_amount=amount)
    await state.set_state(RechargeStates.waiting_utr)

    await callback.message.answer(
        f"🧾 <b>PAYMENT VERIFICATION</b>\n\n"
        f"Amount: <b>₹{amount:.2f}</b>\n\n"
        "Please send your <b>UTR / Transaction ID</b>.\n\n"
        "Example: <code>123456789012</code>",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(RechargeStates.waiting_utr)
async def recharge_utr_received(message: Message, state: FSMContext):
    utr = (message.text or "").strip()

    if len(utr) < 4 or len(utr) > 100:
        await message.answer("❌ Please send a valid UTR / Transaction ID.")
        return

    await state.update_data(utr=utr)
    await state.set_state(RechargeStates.waiting_screenshot)

    await message.answer(
        "📸 <b>NOW SEND PAYMENT SCREENSHOT</b>\n\n"
        "Send the screenshot/photo of your successful payment.",
        parse_mode="HTML"
    )


@dp.message(RechargeStates.waiting_screenshot, F.photo)
async def recharge_screenshot_received(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = float(data["recharge_amount"])
    utr = data["utr"]
    screenshot_file_id = message.photo[-1].file_id

    # Prevent the exact same UTR from being submitted again.
    existing = db.execute(
        "SELECT id, status FROM recharge_requests WHERE utr=?",
        (utr,)
    ).fetchone()

    if existing:
        await state.clear()
        await message.answer(
            "⚠️ This UTR has already been submitted.\n"
            f"Status: <b>{existing['status'].upper()}</b>",
            parse_mode="HTML"
        )
        return

    db.execute("""
        INSERT INTO recharge_requests
        (user_id, amount, utr, screenshot_file_id, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
    """, (
        message.from_user.id,
        amount,
        utr,
        screenshot_file_id,
        now()
    ))
    db.commit()

    request_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    await state.clear()

    await message.answer(
        "✅ <b>PAYMENT SUBMITTED</b>\n\n"
        f"🆔 Request: <code>#{request_id}</code>\n"
        f"💰 Amount: <b>₹{amount:.2f}</b>\n"
        f"🧾 UTR: <code>{utr}</code>\n\n"
        "⏳ Your payment is waiting for admin verification.\n"
        "Your wallet will be credited after approval.",
        reply_markup=back_home_keyboard(),
        parse_mode="HTML"
    )

    user = message.from_user
    username = f"@{user.username}" if user.username else "No username"

    admin_text = (
        "💳 <b>NEW RECHARGE REQUEST</b>\n\n"
        f"🆔 Request: <code>#{request_id}</code>\n"
        f"👤 User: <code>{user.id}</code>\n"
        f"📛 Name: {user.first_name or '-'}\n"
        f"🔗 Username: {username}\n"
        f"💰 Amount: <b>₹{amount:.2f}</b>\n"
        f"🧾 UTR: <code>{utr}</code>\n"
        f"🕐 Time: {now()}"
    )

    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ APPROVE", callback_data=f"approve_recharge:{request_id}"),
         InlineKeyboardButton(text="❌ REJECT", callback_data=f"reject_recharge:{request_id}")],
    ])

    await message.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=screenshot_file_id,
        caption=admin_text,
        reply_markup=admin_keyboard,
        parse_mode="HTML"
    )


@dp.message(RechargeStates.waiting_screenshot)
async def recharge_screenshot_invalid(message: Message):
    await message.answer("📸 Please send the payment screenshot as a photo.")


# =========================================================
# TRANSACTIONS
# =========================================================

@dp.callback_query(F.data == "transactions")
async def transactions_handler(callback: CallbackQuery):
    rows = db.execute("""
        SELECT * FROM wallet_transactions
        WHERE user_id=?
        ORDER BY id DESC LIMIT 10
    """, (callback.from_user.id,)).fetchall()

    if not rows:
        text = "📜 <b>TRANSACTIONS</b>\n\nNo transactions yet."
    else:
        lines = ["📜 <b>RECENT TRANSACTIONS</b>\n"]
        for row in rows:
            sign = "+" if row["amount"] >= 0 else ""
            lines.append(
                f"• {sign}₹{row['amount']:.2f} — {row['type']}\n"
                f"  {row['description'] or ''}\n"
                f"  <i>{row['created_at']}</i>\n"
            )
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ BACK", callback_data="wallet")],
            [InlineKeyboardButton(text="🏠 HOME", callback_data="home")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


# =========================================================
# ADMIN PANEL
# =========================================================

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 DASHBOARD", callback_data="admin_dashboard")],
        [InlineKeyboardButton(text="💳 PENDING PAYMENTS", callback_data="admin_payments")],
        [InlineKeyboardButton(text="🛍️ PRODUCTS", callback_data="admin_products")],
        [InlineKeyboardButton(text="📦 ADD STOCK", callback_data="admin_stock")],
        [InlineKeyboardButton(text="👥 USERS", callback_data="admin_users")],
        [InlineKeyboardButton(text="💰 WALLET ADJUST", callback_data="admin_wallet")],
        [InlineKeyboardButton(text="🖼️ PAYMENT QR", callback_data="admin_qr")],
    ])


def is_admin(user_id):
    return user_id == ADMIN_ID


@dp.message(Command("admin"))
async def admin_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Admin access denied.")
        return

    await message.answer(
        "🛠️ <b>APNASTORE ADMIN PANEL</b>\n\n"
        "Manage payments, products, stock, users, wallet and QR.",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("admin_"))
async def admin_access_guard(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    # Let the specific handlers process their callbacks.
    await callback.answer()


@dp.callback_query(F.data == "admin_dashboard")
async def admin_dashboard(callback: CallbackQuery):
    users = db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    products = db.execute("SELECT COUNT(*) c FROM products WHERE active=1").fetchone()["c"]
    pending = db.execute(
        "SELECT COUNT(*) c FROM recharge_requests WHERE status='pending'"
    ).fetchone()["c"]
    sold = db.execute("SELECT COUNT(*) c FROM stock WHERE sold=1").fetchone()["c"]
    stock_count = db.execute("SELECT COUNT(*) c FROM stock WHERE sold=0").fetchone()["c"]

    await callback.message.edit_text(
        "📊 <b>ADMIN DASHBOARD</b>\n\n"
        f"👥 Users: <b>{users}</b>\n"
        f"🛍️ Active Products: <b>{products}</b>\n"
        f"📦 Available Stock: <b>{stock_count}</b>\n"
        f"✅ Sold Items: <b>{sold}</b>\n"
        f"💳 Pending Payments: <b>{pending}</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# ADMIN PAYMENTS
# =========================================================

@dp.callback_query(F.data == "admin_payments")
async def admin_payments(callback: CallbackQuery):
    rows = db.execute("""
        SELECT r.*, u.first_name, u.username
        FROM recharge_requests r
        LEFT JOIN users u ON u.user_id=r.user_id
        WHERE r.status='pending'
        ORDER BY r.id ASC
        LIMIT 20
    """).fetchall()

    if not rows:
        text = "💳 <b>PENDING PAYMENTS</b>\n\n✅ No pending payment requests."
        keyboard = admin_keyboard()
    else:
        lines = ["💳 <b>PENDING PAYMENTS</b>\n"]
        buttons = []

        for r in rows:
            username = f"@{r['username']}" if r["username"] else "No username"
            lines.append(
                f"🆔 <b>#{r['id']}</b> • ₹{r['amount']:.2f}\n"
                f"👤 {r['first_name'] or '-'} ({username})\n"
                f"🧾 <code>{r['utr']}</code>\n"
                f"🕐 {r['created_at']}\n"
            )
            buttons.append([
                InlineKeyboardButton(
                    text=f"👁️ VIEW #{r['id']}",
                    callback_data=f"view_recharge:{r['id']}"
                )
            ])

        buttons.append([InlineKeyboardButton(text="⬅️ ADMIN", callback_data="admin_back")])
        text = "\n".join(lines)
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛠️ <b>APNASTORE ADMIN PANEL</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("view_recharge:"))
async def view_recharge(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])
    row = db.execute("""
        SELECT r.*, u.first_name, u.username
        FROM recharge_requests r
        LEFT JOIN users u ON u.user_id=r.user_id
        WHERE r.id=?
    """, (request_id,)).fetchone()

    if not row:
        await callback.answer("❌ Request not found.", show_alert=True)
        return

    username = f"@{row['username']}" if row["username"] else "No username"

    caption = (
        "💳 <b>RECHARGE REQUEST</b>\n\n"
        f"🆔 Request: <code>#{row['id']}</code>\n"
        f"👤 User ID: <code>{row['user_id']}</code>\n"
        f"📛 Name: {row['first_name'] or '-'}\n"
        f"🔗 Username: {username}\n"
        f"💰 Amount: <b>₹{row['amount']:.2f}</b>\n"
        f"🧾 UTR: <code>{row['utr']}</code>\n"
        f"📌 Status: <b>{row['status'].upper()}</b>\n"
        f"🕐 Created: {row['created_at']}"
    )

    buttons = []
    if row["status"] == "pending":
        buttons.append([
            InlineKeyboardButton(text="✅ APPROVE", callback_data=f"approve_recharge:{request_id}"),
            InlineKeyboardButton(text="❌ REJECT", callback_data=f"reject_recharge:{request_id}")
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ PENDING", callback_data="admin_payments")])

    await callback.message.answer_photo(
        photo=row["screenshot_file_id"],
        caption=caption,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("approve_recharge:"))
async def approve_recharge(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])

    # Atomic-ish protection: only the first admin action can change pending -> approved.
    db.execute("BEGIN IMMEDIATE")
    row = db.execute(
        "SELECT * FROM recharge_requests WHERE id=?",
        (request_id,)
    ).fetchone()

    if not row:
        db.rollback()
        await callback.answer("❌ Request not found.", show_alert=True)
        return

    if row["status"] != "pending":
        db.rollback()
        await callback.answer(
            f"⚠️ Already {row['status'].upper()}.",
            show_alert=True
        )
        return

    db.execute(
        "UPDATE users SET balance=balance+? WHERE user_id=?",
        (row["amount"], row["user_id"])
    )
    db.execute("""
        INSERT INTO wallet_transactions
        (user_id, amount, type, description, created_at)
        VALUES (?, ?, 'RECHARGE', ?, ?)
    """, (
        row["user_id"],
        row["amount"],
        f"Manual recharge #{request_id}",
        now()
    ))
    db.execute("""
        UPDATE recharge_requests
        SET status='approved', reviewed_at=?
        WHERE id=?
    """, (now(), request_id))
    db.commit()

    new_balance = get_balance(row["user_id"])

    await callback.answer("✅ Payment approved and wallet credited.")
    await callback.message.edit_caption(
        caption=(
            f"✅ <b>APPROVED</b>\n\n"
            f"🆔 Request: <code>#{request_id}</code>\n"
            f"👤 User: <code>{row['user_id']}</code>\n"
            f"💰 Credited: <b>₹{row['amount']:.2f}</b>\n"
            f"💳 New Balance: <b>₹{new_balance:.2f}</b>\n"
            f"🕐 {now()}"
        ),
        reply_markup=None,
        parse_mode="HTML"
    )

    try:
        await callback.bot.send_message(
            row["user_id"],
            "🎉 <b>PAYMENT APPROVED</b>\n\n"
            f"💰 Amount: <b>₹{row['amount']:.2f}</b>\n"
            f"🧾 Request: <code>#{request_id}</code>\n"
            f"💳 New Wallet Balance: <b>₹{new_balance:.2f}</b>\n\n"
            "Your wallet has been credited successfully. ✅",
            parse_mode="HTML"
        )
    except Exception as e:
        print("User notification error:", e)


@dp.callback_query(F.data.startswith("reject_recharge:"))
async def reject_recharge(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])
    row = db.execute(
        "SELECT * FROM recharge_requests WHERE id=?",
        (request_id,)
    ).fetchone()

    if not row:
        await callback.answer("❌ Request not found.", show_alert=True)
        return

    if row["status"] != "pending":
        await callback.answer(
            f"⚠️ Already {row['status'].upper()}.",
            show_alert=True
        )
        return

    db.execute("""
        UPDATE recharge_requests
        SET status='rejected', reviewed_at=?
        WHERE id=? AND status='pending'
    """, (now(), request_id))
    db.commit()

    await callback.answer("❌ Payment rejected.")
    await callback.message.edit_caption(
        caption=(
            "❌ <b>PAYMENT REJECTED</b>\n\n"
            f"🆔 Request: <code>#{request_id}</code>\n"
            f"💰 Amount: ₹{row['amount']:.2f}\n"
            f"🧾 UTR: <code>{row['utr']}</code>\n"
            f"🕐 {now()}"
        ),
        reply_markup=None,
        parse_mode="HTML"
    )

    try:
        await callback.bot.send_message(
            row["user_id"],
            "❌ <b>PAYMENT REJECTED</b>\n\n"
            f"🧾 Request: <code>#{request_id}</code>\n"
            f"💰 Amount: <b>₹{row['amount']:.2f}</b>\n\n"
            "Please contact support if you believe this was rejected by mistake.",
            parse_mode="HTML"
        )
    except Exception as e:
        print("User notification error:", e)


# =========================================================
# ADMIN QR MANAGEMENT
# =========================================================

@dp.callback_query(F.data == "admin_qr")
async def admin_qr(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    qr = get_setting("upi_qr_file_id")

    text = (
        "🖼️ <b>PAYMENT QR MANAGEMENT</b>\n\n"
        f"UPI ID:\n<code>{UPI_ID}</code>\n\n"
        f"Current QR: {'✅ SET' if qr else '❌ NOT SET'}\n\n"
        "You can add a new QR, replace the current QR, or remove it."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ ADD / CHANGE QR", callback_data="qr_change")],
        [InlineKeyboardButton(text="🗑️ REMOVE QR", callback_data="qr_remove")],
        [InlineKeyboardButton(text="⬅️ ADMIN", callback_data="admin_back")]
    ])

    if qr:
        await callback.message.answer_photo(
            photo=qr,
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    await callback.answer()


@dp.callback_query(F.data == "qr_change")
async def qr_change_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    await state.update_data(waiting_qr=True)
    await callback.message.answer(
        "🖼️ <b>SEND NEW PAYMENT QR</b>\n\n"
        "Send the QR image as a photo.\n"
        "The new QR will automatically replace the old one.",
        parse_mode="HTML"
    )
    await state.set_state("waiting_qr")
    await callback.answer()


@dp.message(F.photo)
async def generic_photo_handler(message: Message, state: FSMContext):
    current = await state.get_state()

    if current != "waiting_qr":
        return

    if not is_admin(message.from_user.id):
        return

    file_id = message.photo[-1].file_id
    set_setting("upi_qr_file_id", file_id)
    await state.clear()

    await message.answer(
        "✅ <b>PAYMENT QR UPDATED</b>\n\n"
        "The new QR is now active for customer payments.",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "qr_remove")
async def qr_remove(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    set_setting("upi_qr_file_id", "")
    await callback.answer("🗑️ QR removed.")
    await callback.message.edit_text(
        "🖼️ <b>PAYMENT QR</b>\n\n"
        "❌ QR removed successfully.\n\n"
        "Customers will now see the UPI ID without a QR.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ ADD / CHANGE QR", callback_data="qr_change")],
            [InlineKeyboardButton(text="⬅️ ADMIN", callback_data="admin_back")]
        ]),
        parse_mode="HTML"
    )


# =========================================================
# PRODUCTS
# =========================================================

def product_categories():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 ENTERTAINMENT", callback_data="cat:Entertainment")],
        [InlineKeyboardButton(text="🎟️ COUPONS & VOUCHERS", callback_data="cat:Coupons")],
        [InlineKeyboardButton(text="💎 DIGITAL PRODUCTS", callback_data="cat:Digital Products")],
        [InlineKeyboardButton(text="🏠 HOME", callback_data="home")]
    ])


@dp.callback_query(F.data == "shop")
async def shop_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛍️ <b>APNASTORE SHOP</b>\n\n"
        "Choose a category:",
        reply_markup=product_categories(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("cat:"))
async def category_handler(callback: CallbackQuery):
    category = callback.data.split(":", 1)[1]
    rows = db.execute("""
        SELECT p.*,
               (SELECT COUNT(*) FROM stock s WHERE s.product_id=p.id AND s.sold=0) AS available
        FROM products p
        WHERE p.active=1 AND p.category=?
        ORDER BY p.id DESC
    """, (category,)).fetchall()

    buttons = []
    for p in rows:
        buttons.append([
            InlineKeyboardButton(
                text=f"🛍️ {p['name']} • ₹{p['price']:.0f} • {p['available']} left",
                callback_data=f"product:{p['id']}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="⬅️ CATEGORIES", callback_data="shop")])

    if not rows:
        text = (
            f"📂 <b>{category.upper()}</b>\n\n"
            "No products are available in this category yet."
        )
    else:
        text = (
            f"📂 <b>{category.upper()}</b>\n\n"
            "Select a product:"
        )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("product:"))
async def product_details(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    p = db.execute("""
        SELECT p.*,
               (SELECT COUNT(*) FROM stock s WHERE s.product_id=p.id AND s.sold=0) AS available
        FROM products p WHERE p.id=? AND p.active=1
    """, (product_id,)).fetchone()

    if not p:
        await callback.answer("❌ Product unavailable.", show_alert=True)
        return

    text = (
        f"🛍️ <b>{p['name']}</b>\n\n"
        f"📂 Category: {p['category']}\n"
        f"💰 Price: <b>₹{p['price']:.2f}</b>\n"
        f"📦 Available: <b>{p['available']}</b>\n\n"
        f"{p['description'] or 'Premium digital product.'}\n\n"
        "⚡ Instant delivery after successful purchase."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 BUY NOW", callback_data=f"buy:{product_id}")],
        [InlineKeyboardButton(text="⬅️ BACK", callback_data=f"cat:{p['category']}")]
    ])

    await callback.message.edit_text(
        text, reply_markup=keyboard, parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("buy:"))
async def buy_product(callback: CallbackQuery):
    user_id = callback.from_user.id
    product_id = int(callback.data.split(":")[1])

    p = db.execute("""
        SELECT p.*,
               (SELECT COUNT(*) FROM stock s WHERE s.product_id=p.id AND s.sold=0) AS available
        FROM products p WHERE p.id=? AND p.active=1
    """, (product_id,)).fetchone()

    if not p or p["available"] <= 0:
        await callback.answer("❌ Out of stock.", show_alert=True)
        return

    balance = get_balance(user_id)
    if balance < p["price"]:
        await callback.answer(
            f"❌ Insufficient balance. Need ₹{p['price']:.2f}.",
            show_alert=True
        )
        return

    stock_item = db.execute("""
        SELECT * FROM stock
        WHERE product_id=? AND sold=0
        ORDER BY id ASC LIMIT 1
    """, (product_id,)).fetchone()

    if not stock_item:
        await callback.answer("❌ Out of stock.", show_alert=True)
        return

    db.execute("BEGIN IMMEDIATE")

    try:
        db.execute(
            "UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?",
            (p["price"], user_id, p["price"])
        )

        changed = db.execute("SELECT changes()").fetchone()[0]
        if changed != 1:
            db.rollback()
            await callback.answer("❌ Insufficient balance.", show_alert=True)
            return

        db.execute("""
            UPDATE stock
            SET sold=1, sold_to=?, sold_at=?
            WHERE id=? AND sold=0
        """, (user_id, now(), stock_item["id"]))

        if db.execute("SELECT changes()").fetchone()[0] != 1:
            db.rollback()
            await callback.answer("❌ Stock just sold out.", show_alert=True)
            return

        db.execute("""
            INSERT INTO orders(user_id, product_id, stock_id, amount, item, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id, product_id, stock_item["id"], p["price"],
            stock_item["item"], now()
        ))

        db.execute("""
            INSERT INTO wallet_transactions
            (user_id, amount, type, description, created_at)
            VALUES (?, ?, 'PURCHASE', ?, ?)
        """, (
            user_id, -p["price"], f"Purchase: {p['name']}", now()
        ))

        db.commit()

    except Exception as e:
        db.rollback()
        print("Purchase error:", e)
        await callback.answer("⚠️ Purchase failed. Try again.", show_alert=True)
        return

    new_balance = get_balance(user_id)

    await callback.message.edit_text(
        "🎉 <b>PURCHASE SUCCESSFUL</b>\n\n"
        f"🛍️ Product: <b>{p['name']}</b>\n"
        f"💰 Paid: <b>₹{p['price']:.2f}</b>\n"
        f"💳 Balance: <b>₹{new_balance:.2f}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📦 <b>YOUR DIGITAL ITEM</b>\n\n"
        f"<code>{stock_item['item']}</code>\n\n"
        "⚠️ Keep this information private.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 MY ORDERS", callback_data="orders")],
            [InlineKeyboardButton(text="🏠 HOME", callback_data="home")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer("✅ Delivered!")


# =========================================================
# ADMIN PRODUCT MANAGEMENT
# =========================================================

@dp.callback_query(F.data == "admin_products")
async def admin_products(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    rows = db.execute("""
        SELECT p.*,
               (SELECT COUNT(*) FROM stock s WHERE s.product_id=p.id AND s.sold=0) AS available
        FROM products p ORDER BY p.id DESC LIMIT 30
    """).fetchall()

    lines = ["🛍️ <b>PRODUCTS</b>\n"]
    buttons = []

    for p in rows:
        lines.append(
            f"#{p['id']} • <b>{p['name']}</b>\n"
            f"₹{p['price']:.2f} • {p['category']} • Stock: {p['available']}\n"
        )

    buttons.append([InlineKeyboardButton(text="➕ ADD PRODUCT", callback_data="add_product")])
    buttons.append([InlineKeyboardButton(text="⬅️ ADMIN", callback_data="admin_back")])

    await callback.message.edit_text(
        "\n".join(lines) if rows else "🛍️ <b>PRODUCTS</b>\n\nNo products yet.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "add_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    await state.set_state(ProductStates.waiting_name)
    await callback.message.answer(
        "➕ <b>ADD PRODUCT</b>\n\nSend product name:",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(ProductStates.waiting_name)
async def product_name_received(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(ProductStates.waiting_category)
    await message.answer(
        "📂 Send category exactly as one of:\n\n"
        "<code>Entertainment</code>\n"
        "<code>Coupons</code>\n"
        "<code>Digital Products</code>",
        parse_mode="HTML"
    )


@dp.message(ProductStates.waiting_category)
async def product_category_received(message: Message, state: FSMContext):
    category = message.text.strip()
    allowed = {"Entertainment", "Coupons", "Digital Products"}

    if category not in allowed:
        await message.answer("❌ Please use one of the listed categories.")
        return

    await state.update_data(category=category)
    await state.set_state(ProductStates.waiting_price)
    await message.answer("💰 Send product price (example: 129):")


@dp.message(ProductStates.waiting_price)
async def product_price_received(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        if price <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("❌ Enter a valid positive price.")
        return

    await state.update_data(price=round(price, 2))
    await state.set_state(ProductStates.waiting_description)
    await message.answer(
        "📝 Send product description.\n"
        "Or send <code>-</code> for no description.",
        parse_mode="HTML"
    )


@dp.message(ProductStates.waiting_description)
async def product_description_received(message: Message, state: FSMContext):
    data = await state.get_data()
    description = message.text.strip()
    if description == "-":
        description = ""

    db.execute("""
        INSERT INTO products(name, category, price, description, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data["name"], data["category"], data["price"], description, now()
    ))
    db.commit()
    product_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    await state.clear()
    await message.answer(
        "✅ <b>PRODUCT ADDED</b>\n\n"
        f"🆔 ID: <code>{product_id}</code>\n"
        f"🛍️ {data['name']}\n"
        f"💰 ₹{data['price']:.2f}\n\n"
        "Now use <b>ADD STOCK</b> from Admin Panel.",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# ADMIN STOCK
# =========================================================

@dp.callback_query(F.data == "admin_stock")
async def admin_stock_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    products = db.execute(
        "SELECT id, name FROM products WHERE active=1 ORDER BY id DESC"
    ).fetchall()

    if not products:
        await callback.answer("❌ Add a product first.", show_alert=True)
        return

    buttons = [
        [InlineKeyboardButton(
            text=f"#{p['id']} {p['name']}",
            callback_data=f"stock_product:{p['id']}"
        )]
        for p in products
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ ADMIN", callback_data="admin_back")])

    await callback.message.edit_text(
        "📦 <b>ADD STOCK</b>\n\nSelect product:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("stock_product:"))
async def stock_product_selected(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    p = db.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()

    if not p:
        await callback.answer("❌ Product not found.", show_alert=True)
        return

    await state.update_data(product_id=product_id)
    await state.set_state(StockStates.waiting_items)

    await callback.message.answer(
        f"📦 <b>STOCK FOR: {p['name']}</b>\n\n"
        "Send stock items, <b>one per line</b>.\n\n"
        "Example:\n"
        "<code>email1@example.com:password1\n"
        "email2@example.com:password2</code>",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(StockStates.waiting_items)
async def stock_items_received(message: Message, state: FSMContext):
    data = await state.get_data()
    raw = message.text or ""

    items = [x.strip() for x in raw.splitlines() if x.strip()]
    if not items:
        await message.answer("❌ No stock items detected.")
        return

    for item in items:
        db.execute(
            "INSERT INTO stock(product_id, item) VALUES (?, ?)",
            (data["product_id"], item)
        )
    db.commit()
    await state.clear()

    await message.answer(
        f"✅ <b>{len(items)} STOCK ITEM(S) ADDED</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# ADMIN USERS / WALLET
# =========================================================

@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    rows = db.execute("""
        SELECT * FROM users ORDER BY created_at DESC LIMIT 20
    """).fetchall()

    if not rows:
        text = "👥 <b>USERS</b>\n\nNo users yet."
    else:
        lines = ["👥 <b>RECENT USERS</b>\n"]
        for u in rows:
            uname = f"@{u['username']}" if u["username"] else "-"
            lines.append(
                f"🆔 <code>{u['user_id']}</code> • {u['first_name'] or '-'}\n"
                f"🔗 {uname} • 💰 ₹{u['balance']:.2f}\n"
            )
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_wallet")
async def admin_wallet_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Admin only.", show_alert=True)
        return

    await state.set_state(WalletStates.waiting_user_id)
    await callback.message.answer(
        "💰 <b>WALLET ADJUSTMENT</b>\n\n"
        "Send Telegram User ID:",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(WalletStates.waiting_user_id)
async def wallet_user_id_received(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("❌ Enter a numeric Telegram User ID.")
        return

    await state.update_data(user_id=user_id)
    await state.set_state(WalletStates.waiting_amount)

    await message.answer(
        "Send amount to add/subtract.\n\n"
        "Example:\n"
        "<code>500</code> = add ₹500\n"
        "<code>-100</code> = subtract ₹100",
        parse_mode="HTML"
    )


@dp.message(WalletStates.waiting_amount)
async def wallet_amount_received(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("❌ Enter a valid amount.")
        return

    data = await state.get_data()
    user_id = data["user_id"]

    existing = db.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if not existing:
        await message.answer("❌ User not found in database.")
        await state.clear()
        return

    db.execute(
        "UPDATE users SET balance=balance+? WHERE user_id=?",
        (amount, user_id)
    )
    db.execute("""
        INSERT INTO wallet_transactions
        (user_id, amount, type, description, created_at)
        VALUES (?, ?, 'ADMIN_ADJUSTMENT', ?, ?)
    """, (user_id, amount, "Admin wallet adjustment", now()))
    db.commit()

    new_balance = get_balance(user_id)
    await state.clear()

    await message.answer(
        "✅ <b>WALLET UPDATED</b>\n\n"
        f"👤 User: <code>{user_id}</code>\n"
        f"💰 Adjustment: <b>₹{amount:.2f}</b>\n"
        f"💳 New Balance: <b>₹{new_balance:.2f}</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


# =========================================================
# CUSTOMER ORDERS / OTHER
# =========================================================

@dp.callback_query(F.data == "orders")
async def orders_handler(callback: CallbackQuery):
    rows = db.execute("""
        SELECT o.*, p.name
        FROM orders o
        JOIN products p ON p.id=o.product_id
        WHERE o.user_id=?
        ORDER BY o.id DESC LIMIT 10
    """, (callback.from_user.id,)).fetchall()

    if not rows:
        text = "📦 <b>MY ORDERS</b>\n\nNo orders yet."
    else:
        lines = ["📦 <b>MY ORDERS</b>\n"]
        for o in rows:
            lines.append(
                f"🆔 Order #{o['id']}\n"
                f"🛍️ {o['name']}\n"
                f"💰 ₹{o['amount']:.2f}\n"
                f"🕐 {o['created_at']}\n"
            )
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 HOME", callback_data="home")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "deals")
async def deals_handler(callback: CallbackQuery):
    await callback.answer("🔥 Deals section coming soon!", show_alert=True)


@dp.callback_query(F.data == "refer")
async def refer_handler(callback: CallbackQuery):
    await callback.answer("🎁 Referral system coming soon!", show_alert=True)


@dp.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery):
    await callback.answer("💬 Support: @CR5PT", show_alert=True)


# =========================================================
# ID COMMAND
# =========================================================

@dp.message(Command("id"))
async def get_chat_id(message: Message):
    await message.answer(
        f"🆔 <b>Chat ID:</b>\n\n<code>{message.chat.id}</code>",
        parse_mode="HTML"
    )


# =========================================================
# START BOT
# =========================================================

async def main():
    init_db()

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found in .env")
        return

    bot = Bot(token=BOT_TOKEN)

    print("🤖 ApnaStore Bot is running...")
    print(f"💳 UPI: {UPI_ID}")
    print(f"👑 Admin ID: {ADMIN_ID}")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
