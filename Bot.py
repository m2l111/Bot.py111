from keep_alive import keep_alive
import sqlite3
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from keep_alive import keep_alive
import threading
import time
# ---------- Settings ----------
TOKEN = "YOUR_BOT_TOKEN"          # ⚠️ استبدل بتوكن البوت
ADMIN_ID = 7046655626             # ايديك
DEFAULT_USD_RATE = 13000          # سعر الصرف الافتراضي
bot = telebot.TeleBot(TOKEN)
# ---------- Database ----------
conn = sqlite3.connect("shop.db", check_same_thread=False)
c = conn.cursor()
# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS users
    (user_id INTEGER PRIMARY KEY, name TEXT, balance_usd REAL DEFAULT 0, date TEXT, banned INTEGER DEFAULT 0)''')
c.execute('''CREATE TABLE IF NOT EXISTS products
    (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price_usd REAL, stock INTEGER, code TEXT, category TEXT DEFAULT 'other')''')
c.execute('''CREATE TABLE IF NOT EXISTS coupons
    (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, code TEXT, used INTEGER DEFAULT 0, added_date TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS purchases
    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_name TEXT, amount_usd REAL, code TEXT, date TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS recharge_orders
    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount_syp INTEGER, amount_usd REAL, trx TEXT, status TEXT, date TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS settings
    (key TEXT PRIMARY KEY, value TEXT)''')
# Add missing columns if DB is older
c.execute("PRAGMA table_info(users)")
cols = [col[1] for col in c.fetchall()]
if 'banned' not in cols:
    c.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")
c.execute("PRAGMA table_info(products)")
cols = [col[1] for col in c.fetchall()]
if 'category' not in cols:
    c.execute("ALTER TABLE products ADD COLUMN category TEXT DEFAULT 'other'")
# Default settings
c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('usd_rate', ?)", (DEFAULT_USD_RATE,))
c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_recharge', 'manual')")  # or 'manual'
# Populate products if empty
c.execute("SELECT COUNT(*) FROM products")
if c.fetchone()[0] == 0:
    products_list = [
        # Free Fire Diamonds
        ("فري فاير - 100 جواهر", 0.95, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 200 جواهر", 1.80, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 500 جواهر", 4.50, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 1000 جواهر", 8.99, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 2000 جواهر", 16.99, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 4000 جواهر", 32.99, 0, "FF_DIAMOND", "freefire"),
        # PUBG UC
        ("ببجي - 60 UC", 0.99, 0, "PUBG_UC", "pubg"),
        ("ببجي - 120 UC", 1.99, 0, "PUBG_UC", "pubg"),
        ("ببجي - 300 UC", 4.99, 0, "PUBG_UC", "pubg"),
        ("ببجي - 600 UC", 9.99, 0, "PUBG_UC", "pubg"),
        ("ببجي - 1500 UC", 24.99, 0, "PUBG_UC", "pubg"),
        ("ببجي - 3000 UC", 49.99, 0, "PUBG_UC", "pubg"),
    ]
    for p in products_list:
        c.execute("INSERT INTO products (name, price_usd, stock, code, category) VALUES (?,?,?,?,?)", p)
conn.commit()
# ---------- Helper functions ----------
def get_setting(key):
    row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else None
def set_setting(key, value):
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
    conn.commit()
def get_usd_rate():
    rate = get_setting("usd_rate")
    return int(rate) if rate else DEFAULT_USD_RATE
def is_admin(uid):
    return uid == ADMIN_ID
# ---------- Auto recharge verification (dummy) ----------
def verify_transfer(trx, amount_syp):
    """
    Real implementation: call payment gateway API (Kham Cash / SyrTel Cash)
    and check if a transfer with given TRX and amount exists and is valid.
    Return True if valid, else False.
    """
    # Dummy logic: approve if amount is below 100,000 SYP
    return amount_syp < 100000
# ---------- Purchase from Mahd Store (dummy) ----------
from mahd_store import buy_product as mahd_buy
# ---------- Main Menu ----------
def main_menu(user_id, chat_id, message_id=None, edit=False):
    c.execute("SELECT name, banned FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if user and user[1]:
        bot.send_message(chat_id, "❌ أنت محظور من استخدام البوت.")
        return
    name = user[0] if user else "مستخدم"
    rate = get_usd_rate()
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("🎮 فري فاير", callback_data="cat_freefire"),
               InlineKeyboardButton("🔫 ببجي", callback_data="cat_pubg"))
    markup.add(InlineKeyboardButton("🛍️ جميع المنتجات", callback_data="products"))
    markup.row(InlineKeyboardButton("💰 رصيدي", callback_data="balance"),
               InlineKeyboardButton("💳 شحن الرصيد", callback_data="recharge"))
    markup.add(InlineKeyboardButton("📦 مشترياتي", callback_data="purchases"))
    if is_admin(user_id):
        markup.add(InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel"))
    text = f"👋 أهلاً {name}\n💵 سعر الصرف: 1$ = {rate:,} ل.س"
    if edit and message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)
# ---------- /start ----------
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    c.execute("INSERT OR IGNORE INTO users (user_id, name, date) VALUES (?,?,?)",
              (user_id, name, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    main_menu(user_id, message.chat.id)
# ---------- Callback Handler ----------
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    # Check ban
    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row and row[0] and not is_admin(user_id):
        bot.answer_callback_query(call.id, "❌ محظور")
        return
    # --- Categories ---
    if data == "cat_freefire":
        rows = c.execute("SELECT id, name, price_usd FROM products WHERE category='freefire' AND stock>0").fetchall()
        mark = InlineKeyboardMarkup()
        for i, n, p in rows:
            mark.add(InlineKeyboardButton(f"{n} - {p}$", callback_data=f"buy_{i}"))
        mark.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        bot.edit_message_text("🎮 فري فاير:", chat_id, msg_id, reply_markup=mark)
    elif data == "cat_pubg":
        rows = c.execute("SELECT id, name, price_usd FROM products WHERE category='pubg' AND stock>0").fetchall()
        mark = InlineKeyboardMarkup()
        for i, n, p in rows:
            mark.add(InlineKeyboardButton(f"{n} - {p}$", callback_data=f"buy_{i}"))
        mark.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        bot.edit_message_text("🔫 ببجي:", chat_id, msg_id, reply_markup=mark)
    elif data == "products":
        rows = c.execute("SELECT id, name, price_usd FROM products WHERE stock>0").fetchall()
        if not rows:
            bot.edit_message_text("📭 لا توجد منتجات", chat_id, msg_id)
            return
        mark = InlineKeyboardMarkup(row_width=2)
        for i, n, p in rows:
            mark.add(InlineKeyboardButton(f"{n} - {p}$", callback_data=f"buy_{i}"))
        mark.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        bot.edit_message_text("🛍️ المنتجات:", chat_id, msg_id, reply_markup=mark)
    # --- Buy product ---
    elif data.startswith("buy_"):
        pid = int(data.split("_")[1])
        prod = c.execute("SELECT name, price_usd, stock, code FROM products WHERE id=?", (pid,)).fetchone()
        if not prod or prod[2] <= 0:
            bot.answer_callback_query(call.id, "❌ المنتج غير متوفر")
            return
        bal = c.execute("SELECT balance_usd FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
        if bal < prod[1]:
            bot.answer_callback_query(call.id, f"💰 رصيدك {bal}$ غير كاف")
            return
        # Simulate buying from Mahd Store
        coupon_code = mahd_buy(prod[3])   # prod[3] is internal product code
        # Deduct balance, update stock, record purchase
        c.execute("UPDATE users SET balance_usd = balance_usd - ? WHERE user_id=?", (prod[1], user_id))
        c.execute("UPDATE products SET stock = stock - 1 WHERE id=?", (pid,))
        c.execute("INSERT INTO purchases (user_id, product_name, amount_usd, code, date) VALUES (?,?,?,?,?)",
                  (user_id, prod[0], prod[1], coupon_code, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        # Notify admin
        bot.send_message(ADMIN_ID, f"🔔 شراء جديد\nالمستخدم: {user_id}\nالمنتج: {prod[0]}\nالسعر: {prod[1]}$\nالكود المباع: {coupon_code}")
        bot.edit_message_text(
            f"✅ **تم الشراء**\n\n{prod[0]}\n💵 السعر: {prod[1]}$\n🎁 الكود: `{coupon_code}`\n💰 رصيدك المتبقي: {bal-prod[1]}$\n\n⚠️ استخدم الكود حالاً.",
            chat_id, msg_id, parse_mode="Markdown"
        )
    # --- Balance ---
    elif data == "balance":
        bal = c.execute("SELECT balance_usd FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
        rate = get_usd_rate()
        bot.edit_message_text(f"💰 رصيدك الحالي: {bal}$\n💱 يعادل: {bal*rate:,.0f} ل.س", chat_id, msg_id)
    # --- Recharge Request ---
    elif data == "recharge":
        msg = bot.send_message(chat_id, "💳 أرسل المبلغ بالليرة السورية (أقل مبلغ 50,000):")
        bot.register_next_step_handler(msg, recharge_amount)
    # --- Purchases history ---
    elif data == "purchases":
        rows = c.execute("SELECT product_name, amount_usd, code, date FROM purchases WHERE user_id=? ORDER BY id DESC LIMIT 10",
                         (user_id,)).fetchall()
        if not rows:
            bot.edit_message_text("📭 لا توجد مشتريات", chat_id, msg_id)
            return
        txt = "📦 آخر المشتريات:\n\n"
        for n, a, cd, dt in rows:
            txt += f"{n} - {a}$\nكود: `{cd}`\n{dt}\n---\n"
        bot.edit_message_text(txt, chat_id, msg_id, parse_mode="Markdown")
    # --- Back to main ---
    elif data == "back_to_main":
        main_menu(user_id, chat_id, msg_id, edit=True)
    # ======= ADMIN PANEL =======
    elif data == "admin_panel" and is_admin(user_id):
        mark = InlineKeyboardMarkup(row_width=2)
        mark.add(InlineKeyboardButton("📦 المنتجات", callback_data="adm_products"),
                 InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users"))
        mark.add(InlineKeyboardButton("💳 طلبات الشحن", callback_data="admin_orders"),
                 InlineKeyboardButton("📊 إحصائيات", callback_data="stats"))
        mark.add(InlineKeyboardButton("💱 تغيير سعر الصرف", callback_data="change_rate"))
        mark.add(InlineKeyboardButton("📢 بث للجميع", callback_data="broadcast"))
        mark.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        bot.edit_message_text("⚙️ لوحة تحكم الأدمن:", chat_id, msg_id, reply_markup=mark)
    elif data == "adm_products" and is_admin(user_id):
        rows = c.execute("SELECT id, name, price_usd, stock FROM products").fetchall()
        mark = InlineKeyboardMarkup()
        for pid, n, p, s in rows:
            mark.add(InlineKeyboardButton(f"{n} | {p}$ | مخزون:{s}", callback_data=f"admprod_{pid}"))
        mark.add(InlineKeyboardButton("➕ إضافة منتج", callback_data="add_product"))
        mark.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel"))
        bot.edit_message_text("📦 تعديل المنتجات:", chat_id, msg_id, reply_markup=mark)
    elif data.startswith("admprod_") and is_admin(user_id):
        pid = int(data.split("_")[1])
        prod = c.execute("SELECT name, price_usd, stock, code, category FROM products WHERE id=?", (pid,)).fetchone()
        if not prod: return
        n, p, s, cd, cat = prod
        mark = InlineKeyboardMarkup()
        mark.add(InlineKeyboardButton("✏️ اسم", callback_data=f"editprod_name_{pid}"),
                 InlineKeyboardButton("💵 سعر", callback_data=f"editprod_price_{pid}"))
        mark.add(InlineKeyboardButton("📦 مخزون", callback_data=f"editprod_stock_{pid}"),
                 InlineKeyboardButton("🎫 رفع أكواد", callback_data=f"editprod_codes_{pid}"))
        mark.add(InlineKeyboardButton("❌ حذف", callback_data=f"deleteprod_{pid}"))
        mark.add(InlineKeyboardButton("🔙 للمنتجات", callback_data="adm_products"))
        bot.edit_message_text(f"🛠 {n}\nالسعر: {p}$ | المخزون: {s}\nالكود الداخلي: {cd}\nالفئة: {cat}",
                              chat_id, msg_id, reply_markup=mark)
    elif data.startswith("editprod_") and is_admin(user_id):
        _, field, pid_str = data.split("_")
        pid = int(pid_str)
        if field == "codes":
            msg = bot.send_message(chat_id, "🎫 أرسل الأكواد (كل كود في سطر، أو مفصولة بفاصلة):")
            bot.register_next_step_handler(msg, lambda m, p=pid: add_codes(m, p))
        else:
            prompts = {"name": "✏️ أرسل الاسم الجديد:", "price": "💵 أرسل السعر الجديد:", "stock": "📦 أرسل المخزون الجديد:"}
            msg = bot.send_message(chat_id, prompts[field])
            bot.register_next_step_handler(msg, lambda m, f=field, p=pid: edit_product(m, f, p))
        bot.delete_message(chat_id, msg_id)
    elif data.startswith("deleteprod_") and is_admin(user_id):
        pid = int(data.split("_")[1])
        c.execute("DELETE FROM products WHERE id=?", (pid,))
        c.execute("DELETE FROM coupons WHERE product_id=?", (pid,))
        conn.commit()
        bot.answer_callback_query(call.id, "تم الحذف")
        call.data = "adm_products"
        handle_callback(call)
    elif data == "add_product" and is_admin(user_id):
        msg = bot.send_message(chat_id, "➕ أدخل: الاسم, الفئة, السعر بالدولار, المخزون, الكود الداخلي\nمثال: ببجي 60 يو سي, pubg, 0.99, 50, PUBG_UC")
        bot.register_next_step_handler(msg, add_new_product)
    elif data == "admin_users" and is_admin(user_id):
        rows = c.execute("SELECT user_id, name, balance_usd, banned FROM users LIMIT 50").fetchall()
        txt = "👥 المستخدمون:\n\n"
        for uid, n, b, ban in rows:
            status = "🚫" if ban else "✅"
            txt += f"{status} {uid} - {n}: {b}$\n"
        mark = InlineKeyboardMarkup()
        mark.add(InlineKeyboardButton("تعديل رصيد/حظر", callback_data="admin_user_modify"))
        mark.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel"))
        bot.edit_message_text(txt, chat_id, msg_id, reply_markup=mark)
    elif data == "admin_user_modify" and is_admin(user_id):
        msg = bot.send_message(chat_id, "أدخل: id balance/ban القيمة\nمثال: 123456 balance 50\nأو: 123456 ban 1")
        bot.register_next_step_handler(msg, modify_user)
    elif data == "admin_orders" and is_admin(user_id):
        rows = c.execute("SELECT id, user_id, amount_syp, trx FROM recharge_orders WHERE status='pending'").fetchall()
        if not rows:
            bot.edit_message_text("لا طلبات معلقة", chat_id, msg_id)
            return
        for oid, uid, amt, trx in rows:
            mark = InlineKeyboardMarkup()
            mark.row(InlineKeyboardButton("✅ قبول", callback_data=f"approve_{oid}"),
                     InlineKeyboardButton("❌ رفض", callback_data=f"reject_{oid}"))
            bot.send_message(chat_id, f"طلب #{oid}\nمستخدم: {uid}\nمبلغ: {amt:,} ليرة\nTRX: {trx}", reply_markup=mark)
    elif data == "stats" and is_admin(user_id):
        users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        purchases = c.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
        total = c.execute("SELECT SUM(amount_usd) FROM purchases").fetchone()[0] or 0
        bot.edit_message_text(f"📊 إحصائيات:\n👥 مستخدمين: {users}\n🛒 مشتريات: {purchases}\n💵 إجمالي المبيعات: {total}$",
                              chat_id, msg_id)
    elif data == "change_rate" and is_admin(user_id):
        msg = bot.send_message(chat_id, f"💱 السعر الحالي: {get_usd_rate()} ليرة\nأرسل السعر الجديد:")
        bot.register_next_step_handler(msg, change_rate)
    elif data == "broadcast" and is_admin(user_id):
        msg = bot.send_message(chat_id, "📢 أرسل الرسالة التي تريد بثها:")
        bot.register_next_step_handler(msg, broadcast)
    elif data.startswith("approve_") and is_admin(user_id):
        oid = int(data.split("_")[1])
        row = c.execute("SELECT user_id, amount_usd FROM recharge_orders WHERE id=?", (oid,)).fetchone()
        if row:
            c.execute("UPDATE users SET balance_usd = balance_usd + ? WHERE user_id=?", (row[1], row[0]))
            c.execute("UPDATE recharge_orders SET status='approved' WHERE id=?", (oid,))
            conn.commit()
            bot.send_message(row[0], f"✅ تم إضافة {row[1]:.2f}$ إلى رصيدك")
            bot.edit_message_text("✅ تم القبول", chat_id, msg_id)
    elif data.startswith("reject_") and is_admin(user_id):
        oid = int(data.split("_")[1])
        row = c.execute("SELECT user_id FROM recharge_orders WHERE id=?", (oid,)).fetchone()
        if row:
            c.execute("UPDATE recharge_orders SET status='rejected' WHERE id=?", (oid,))
            conn.commit()
            bot.send_message(row[0], "❌ تم رفض طلبك")
            bot.edit_message_text("❌ تم الرفض", chat_id, msg_id)
# ---------- Step handlers ----------
def recharge_amount(message):
    try:
        amount = int(message.text.strip())
        if amount < 50000:
            bot.send_message(message.chat.id, "❌ أقل مبلغ 50,000")
            return
    except:
        bot.send_message(message.chat.id, "❌ رقم غير صحيح")
        return
    bot.send_message(message.chat.id, f"💰 المبلغ: {amount:,} ل.س\n📱 أرسل رقم الحوالة (TRX):")
    bot.register_next_step_handler(message, lambda m: receive_trx(m, amount))
def receive_trx(message, amount):
    trx = message.text.strip()
    user_id = message.from_user.id
    if c.execute("SELECT id FROM recharge_orders WHERE trx=?", (trx,)).fetchone():
        bot.send_message(message.chat.id, "❌ رقم الحوالة مستخدم سابقاً")
        return
    # Auto-verify recharge if enabled
    auto = get_setting("auto_recharge")
    if auto == "auto" and verify_transfer(trx, amount):
        usd = amount / get_usd_rate()
        c.execute("UPDATE users SET balance_usd = balance_usd + ? WHERE user_id=?", (usd, user_id))
        c.execute("INSERT INTO recharge_orders (user_id, amount_syp, amount_usd, trx, status, date) VALUES (?,?,?,?,?,?)",
                  (user_id, amount, usd, trx, 'approved', datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ تم التحقق التلقائي! أضيف {usd:.2f}$ إلى رصيدك.")
        bot.send_message(ADMIN_ID, f"🔔 شحن تلقائي: {user_id} المبلغ {amount:,} ل.س - TRX: {trx}")
    else:
        # Manual approval pending
        usd = amount / get_usd_rate()
        c.execute("INSERT INTO recharge_orders (user_id, amount_syp, amount_usd, trx, status, date) VALUES (?,?,?,?,?,?)",
                  (user_id, amount, usd, trx, 'pending', datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        bot.send_message(message.chat.id, "✅ تم تسجيل طلبك، سيتم المراجعة قريباً")
        bot.send_message(ADMIN_ID, f"📥 طلب شحن جديد\nالمستخدم: {user_id}\nالمبلغ: {amount:,} ل.س\nTRX: {trx}")
def add_codes(message, pid):
    codes = [c.strip() for c in message.text.replace(",", "\n").split("\n") if c.strip()]
    for cd in codes:
        c.execute("INSERT INTO coupons (product_id, code, added_date) VALUES (?,?,?)",
                  (pid, cd, datetime.now().strftime("%Y-%m-%d %H:%M")))
    c.execute("UPDATE products SET stock = stock + ? WHERE id=?", (len(codes), pid))
    conn.commit()
    bot.send_message(message.chat.id, f"✅ تم إضافة {len(codes)} كود")
def edit_product(message, field, pid):
    val = message.text.strip()
    if field == "price": val = float(val)
    elif field == "stock": val = int(val)
    c.execute(f"UPDATE products SET {field}=? WHERE id=?", (val, pid))
    conn.commit()
    bot.send_message(message.chat.id, "✅ تم التعديل")
def add_new_product(message):
    try:
        parts = [x.strip() for x in message.text.split(",")]
        name, cat, price, stock, code = parts[0], parts[1], float(parts[2]), int(parts[3]), parts[4]
        c.execute("INSERT INTO products (name, price_usd, stock, code, category) VALUES (?,?,?,?,?)",
                  (name, price, stock, code, cat))
        conn.commit()
        bot.send_message(message.chat.id, "✅ تم إضافة المنتج")
    except:
        bot.send_message(message.chat.id, "❌ تنسيق خطأ. استخدم: الاسم, الفئة, السعر, المخزون, الكود الداخلي")
def modify_user(message):
    try:
        parts = message.text.split()
        uid = int(parts[0])
        action = parts[1]
        if action == "balance":
            c.execute("UPDATE users SET balance_usd=? WHERE user_id=?", (float(parts[2]), uid))
        elif action == "ban":
            c.execute("UPDATE users SET banned=? WHERE user_id=?", (int(parts[2]), uid))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ تم تعديل المستخدم {uid}")
    except:
        bot.send_message(message.chat.id, "❌ خطأ في الصيغة")
def change_rate(message):
    try:
        rate = int(message.text.strip())
        set_setting("usd_rate", rate)
        bot.send_message(message.chat.id, f"✅ السعر الجديد: {rate} ل.س")
    except:
        bot.send_message(message.chat.id, "❌ رقم غير صالح")
def broadcast(message):
    users = c.execute("SELECT user_id FROM users WHERE banned=0").fetchall()
    cnt = 0
    for (uid,) in users:
        try:
            bot.send_message(uid, message.text)
            cnt += 1
        except:
            pass
    bot.send_message(message.chat.id, f"📢 تم الإرسال إلى {cnt} مستخدم")
# ---------- Run ----------
if __name__ == "__main__":
    keep_alive()
    print("🚀 البوت المتكامل يعمل...")
    keep_alive()
bot.infinity_polling()