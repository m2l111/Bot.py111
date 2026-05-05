import sqlite3
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

# ========== الإعدادات الأساسية ==========
TOKEN = "8695956195:AAHiB1yHZeivaa7t3RQZh28_HuQjogvTYEE"
ADMIN_ID = 7046655626
DEFAULT_USD_RATE = 13000

bot = telebot.TeleBot(TOKEN)

# ========== قاعدة البيانات ==========
conn = sqlite3.connect("shop.db", check_same_thread=False)
c = conn.cursor()

# إنشاء الجداول
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

# إعدادات افتراضية
c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('usd_rate', ?)", (DEFAULT_USD_RATE,))

# ========== هجرة قاعدة البيانات (إضافة أعمدة إذا كانت مفقودة) ==========
c.execute("PRAGMA table_info(users)")
columns = [col[1] for col in c.fetchall()]
if 'banned' not in columns:
    c.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")
    print("✅ تم إضافة عمود banned")

c.execute("PRAGMA table_info(products)")
columns = [col[1] for col in c.fetchall()]
if 'category' not in columns:
    c.execute("ALTER TABLE products ADD COLUMN category TEXT DEFAULT 'other'")
    print("✅ تم إضافة عمود category")

conn.commit()

# إدراج منتجات افتراضية إذا كانت القائمة فارغة
c.execute("SELECT COUNT(*) FROM products")
if c.fetchone()[0] == 0:
    products_default = [
        ("ببجي - 60 UC", 0.99, 0, "PUBG_UC", "pubg"),
        ("ببجي - 120 UC", 1.99, 0, "PUBG_UC", "pubg"),
        ("ببجي - 300 UC", 4.99, 0, "PUBG_UC", "pubg"),
        ("ببجي - 600 UC", 9.99, 0, "PUBG_UC", "pubg"),
        ("ببجي - 1500 UC", 24.99, 0, "PUBG_UC", "pubg"),
        ("ببجي - 3000 UC", 49.99, 0, "PUBG_UC", "pubg"),
        ("فري فاير - 100 جواهر", 1.50, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 200 جواهر", 2.80, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 500 جواهر", 6.99, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 1000 جواهر", 13.50, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 2000 جواهر", 26.99, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 4000 جواهر", 52.99, 0, "FF_DIAMOND", "freefire"),
    ]
    for p in products_default:
        c.execute("INSERT INTO products (name, price_usd, stock, code, category) VALUES (?,?,?,?,?)", p)
    conn.commit()

# ========== دوال مساعدة ==========
def get_setting(key):
    row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else None

def set_setting(key, value):
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
    conn.commit()

def get_usd_rate():
    rate = get_setting("usd_rate")
    return int(rate) if rate else DEFAULT_USD_RATE

def is_admin(user_id):
    return user_id == ADMIN_ID

def main_menu(user_id, chat_id, message_id=None, edit=False):
    """إرسال أو تعديل القائمة الرئيسية"""
    c.execute("SELECT name, banned FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if user and user[1]:
        bot.send_message(chat_id, "❌ أنت محظور من استخدام البوت.")
        return
    name = user[0] if user else "مستخدم"
    usd_rate = get_usd_rate()

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("🎮 فري فاير", callback_data="cat_freefire"),
               InlineKeyboardButton("🔫 ببجي", callback_data="cat_pubg"))
    markup.add(InlineKeyboardButton("🛍️ جميع المنتجات", callback_data="products"))
    markup.add(InlineKeyboardButton("💰 رصيدي", callback_data="balance"),
               InlineKeyboardButton("💳 شحن الرصيد", callback_data="recharge"))
    markup.add(InlineKeyboardButton("📦 مشترياتي", callback_data="purchases"))
    if is_admin(user_id):
        markup.add(InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel"))
    text = f"👋 مرحباً {name}\n💵 سعر الصرف: 1$ = {usd_rate:,} ليرة"
    if edit and message_id:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup)

# ========== أمر البداية ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    c.execute("INSERT OR IGNORE INTO users (user_id, name, date) VALUES (?,?,?)",
              (user_id, name, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    main_menu(user_id, message.chat.id)

# ========== معالج الأزرار الرئيسي ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    # التحقق من الحظر
    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row and row[0] and not is_admin(user_id):
        bot.answer_callback_query(call.id, "❌ أنت محظور.")
        return

    # --- الفئات ---
    if data == "cat_freefire":
        show_category(chat_id, msg_id, "freefire", "فري فاير")
    elif data == "cat_pubg":
        show_category(chat_id, msg_id, "pubg", "ببجي")
    elif data == "products":
        show_products(chat_id, msg_id)
    elif data.startswith("buy_"):
        process_buy(call)
    elif data == "balance":
        show_balance(call)
    elif data == "recharge":
        start_recharge(call)
    elif data == "purchases":
        show_purchases(call)
    elif data == "back_to_main":
        main_menu(user_id, chat_id, msg_id, edit=True)
    # --- لوحة الأدمن ---
    elif data == "admin_panel":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "⛔ غير مسموح")
            return
        admin_panel(call)
    elif data.startswith("adm_") or data.startswith("editprod_") or data.startswith("deleteprod_") or data == "add_product" or data == "admin_users" or data == "admin_orders" or data == "broadcast" or data == "stats" or data == "change_rate":
        handle_admin(call)
    elif data.startswith("approve_") or data.startswith("reject_"):
        handle_recharge_approval(call)

# ========== عرض فئة ==========
def show_category(chat_id, msg_id, category, cat_name):
    rows = c.execute("SELECT id, name, price_usd FROM products WHERE category=? AND stock>0", (category,)).fetchall()
    if not rows:
        bot.edit_message_text(f"🎮 لا توجد منتجات في {cat_name} حالياً.", chat_id, msg_id)
        return
    markup = InlineKeyboardMarkup()
    for pid, name, price in rows:
        markup.add(InlineKeyboardButton(f"{name} - {price}$", callback_data=f"buy_{pid}"))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    bot.edit_message_text(f"🎮 منتجات {cat_name}:", chat_id, msg_id, reply_markup=markup)

# ========== عرض جميع المنتجات ==========
def show_products(chat_id, msg_id):
    rows = c.execute("SELECT id, name, price_usd FROM products WHERE stock>0").fetchall()
    if not rows:
        bot.edit_message_text("📭 المخزون فارغ حالياً.", chat_id, msg_id)
        return
    markup = InlineKeyboardMarkup(row_width=2)
    for pid, name, price in rows:
        markup.add(InlineKeyboardButton(f"{name} - {price}$", callback_data=f"buy_{pid}"))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    bot.edit_message_text("🛍️ جميع المنتجات:", chat_id, msg_id, reply_markup=markup)

# ========== شراء منتج (شحن تلقائي) ==========
def process_buy(call):
    user_id = call.from_user.id
    pid = int(call.data.split("_")[1])
    prod = c.execute("SELECT name, price_usd, stock, code FROM products WHERE id=?", (pid,)).fetchone()
    if not prod or prod[2] <= 0:
        bot.answer_callback_query(call.id, "❌ المنتج غير متوفر حالياً.")
        return
    bal = c.execute("SELECT balance_usd FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
    if bal < prod[1]:
        bot.answer_callback_query(call.id, f"💸 رصيدك غير كافٍ. المطلوب {prod[1]}$ ولديك {bal}$")
        return

    # سحب كود غير مستخدم من المخزون
    coupon = c.execute("SELECT id, code FROM coupons WHERE product_id=? AND used=0 LIMIT 1", (pid,)).fetchone()
    if not coupon:
        bot.answer_callback_query(call.id, "⚠️ نفدت الأكواد، جاري توفيرها قريباً.")
        return

    # خصم الرصيد وتحديث الكود كمستخدم
    c.execute("UPDATE users SET balance_usd = balance_usd - ? WHERE user_id=?", (prod[1], user_id))
    c.execute("UPDATE coupons SET used=1 WHERE id=?", (coupon[0],))
    c.execute("UPDATE products SET stock = stock - 1 WHERE id=?", (pid,))
    c.execute("INSERT INTO purchases (user_id, product_name, amount_usd, code, date) VALUES (?,?,?,?,?)",
              (user_id, prod[0], prod[1], coupon[1], datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()

    bot.edit_message_text(
        f"✅ **تم الشحن بنجاح!**\n\n"
        f"🎮 المنتج: {prod[0]}\n"
        f"💵 السعر: {prod[1]}$\n"
        f"🎁 الكود: `{coupon[1]}`\n"
        f"💰 رصيدك المتبقي: {bal - prod[1]}$\n\n"
        f"⚠️ يرجى استخدام الكود قبل انتهاء صلاحيته.",
        call.message.chat.id, call.message.message_id, parse_mode="Markdown"
    )

# ========== الرصيد ==========
def show_balance(call):
    bal = c.execute("SELECT balance_usd FROM users WHERE user_id=?", (call.from_user.id,)).fetchone()[0]
    usd_rate = get_usd_rate()
    bot.edit_message_text(
        f"💰 رصيدك الحالي: {bal}$\n"
        f"💱 يعادل: {bal * usd_rate:,.0f} ليرة\n"
        f"سعر الصرف: {usd_rate} ل.س",
        call.message.chat.id, call.message.message_id
    )

# ========== شحن الرصيد ==========
def start_recharge(call):
    msg = bot.send_message(call.message.chat.id, "💳 أرسل المبلغ بالليرة السورية (الحد الأدنى 50,000 ل.س):")
    bot.register_next_step_handler(msg, receive_amount)

def receive_amount(msg):
    try:
        amount_syp = int(msg.text.strip())
        if amount_syp < 50000:
            bot.send_message(msg.chat.id, "❌ الحد الأدنى 50,000 ليرة.")
            return
    except:
        bot.send_message(msg.chat.id, "❌ أرسل رقماً صحيحاً.")
        return
    usd_rate = get_usd_rate()
    usd_amount = amount_syp / usd_rate
    bot.send_message(msg.chat.id, f"💰 {amount_syp:,} ليرة ≈ {usd_amount:.2f}$\n📱 أرسل رقم التحويل (TRX):")
    bot.register_next_step_handler(msg, lambda m: receive_trx(m, amount_syp, usd_amount))

def receive_trx(msg, amount_syp, usd_amount):
    trx = msg.text.strip()
    user_id = msg.from_user.id
    if c.execute("SELECT id FROM recharge_orders WHERE trx=?", (trx,)).fetchone():
        bot.send_message(msg.chat.id, "❌ رقم التحويل مستخدم من قبل.")
        return
    c.execute("INSERT INTO recharge_orders (user_id, amount_syp, amount_usd, trx, status, date) VALUES (?,?,?,?,?,?)",
              (user_id, amount_syp, usd_amount, trx, 'pending', datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    bot.send_message(msg.chat.id, "✅ تم استلام طلب الشحن، جاري المراجعة.")
    bot.send_message(ADMIN_ID, f"📥 طلب شحن جديد\nالمستخدم: {user_id}\nالمبلغ: {amount_syp:,} ل.س\nالقيمة: {usd_amount:.2f}$\nTRX: {trx}")

# ========== المشتريات ==========
def show_purchases(call):
    rows = c.execute("SELECT product_name, amount_usd, code, date FROM purchases WHERE user_id=? ORDER BY id DESC LIMIT 10",
                     (call.from_user.id,)).fetchall()
    if not rows:
        bot.edit_message_text("📭 لا توجد مشتريات بعد.", call.message.chat.id, call.message.message_id)
        return
    text = "📦 آخر مشترياتك:\n\n"
    for name, amt, code, dt in rows:
        text += f"🎮 {name} - {amt}$\n🎫 `{code}`\n📅 {dt}\n---\n"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# ========== لوحة الأدمن ==========
def admin_panel(call):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("📦 المنتجات", callback_data="adm_products"),
               InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users"))
    markup.add(InlineKeyboardButton("💳 طلبات الشحن", callback_data="admin_orders"),
               InlineKeyboardButton("📊 إحصائيات", callback_data="stats"))
    markup.add(InlineKeyboardButton("💱 تغيير سعر الصرف", callback_data="change_rate"))
    markup.add(InlineKeyboardButton("📢 بث للجميع", callback_data="broadcast"))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    bot.edit_message_text("⚙️ لوحة تحكم الأدمن:", call.message.chat.id, call.message.message_id, reply_markup=markup)

def handle_admin(call):
    user_id = call.from_user.id
    if not is_admin(user_id): return
    data = call.data
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    if data == "adm_products":
        rows = c.execute("SELECT id, name, price_usd, stock, category FROM products").fetchall()
        if not rows:
            bot.edit_message_text("لا توجد منتجات.", chat_id, msg_id)
            return
        markup = InlineKeyboardMarkup()
        for pid, name, price, stock, cat in rows:
            btn = f"{name} | {price}$ | مخزون:{stock}"
            markup.add(InlineKeyboardButton(btn, callback_data=f"admprod_{pid}"))
        markup.add(InlineKeyboardButton("➕ إضافة منتج", callback_data="add_product"))
        markup.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel"))
        bot.edit_message_text("📦 إدارة المنتجات (اضغط للتعديل):", chat_id, msg_id, reply_markup=markup)

    elif data.startswith("admprod_"):
        pid = int(data.split("_")[1])
        prod = c.execute("SELECT name, price_usd, stock, code, category FROM products WHERE id=?", (pid,)).fetchone()
        if not prod:
            bot.answer_callback_query(call.id, "غير موجود")
            return
        name, price, stock, code, cat = prod
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✏️ تعديل الاسم", callback_data=f"editprod_name_{pid}"),
                   InlineKeyboardButton("💵 تعديل السعر", callback_data=f"editprod_price_{pid}"))
        markup.add(InlineKeyboardButton("📦 تعديل المخزون", callback_data=f"editprod_stock_{pid}"),
                   InlineKeyboardButton("🎫 رفع أكواد", callback_data=f"editprod_codes_{pid}"))
        markup.add(InlineKeyboardButton("❌ حذف المنتج", callback_data=f"deleteprod_{pid}"))
        markup.add(InlineKeyboardButton("🔙 للمنتجات", callback_data="adm_products"))
        text = f"🛠 المنتج: {name}\nالسعر: {price}$\nالمخزون: {stock}\nالكود الداخلي: {code}\nالفئة: {cat}"
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup)

    elif data.startswith("editprod_"):
        _, field, pid_str = data.split("_")
        pid = int(pid_str)
        if field == "codes":
            msg = bot.send_message(chat_id, "🎫 أرسل الأكواد (كل كود في سطر، أو مفصولة بفواصل):")
            bot.register_next_step_handler(msg, lambda m, p=pid: add_coupons(m, p))
        else:
            prompts = {
                "name": "✏️ أرسل الاسم الجديد:",
                "price": "💵 أرسل السعر الجديد بالدولار:",
                "stock": "📦 أرسل الكمية الجديدة (المخزون):"
            }
            msg = bot.send_message(chat_id, prompts[field])
            bot.register_next_step_handler(msg, lambda m, f=field, p=pid: save_product_edit(m, f, p))
        bot.delete_message(chat_id, msg_id)

    elif data.startswith("deleteprod_"):
        pid = int(data.split("_")[1])
        c.execute("DELETE FROM products WHERE id=?", (pid,))
        c.execute("DELETE FROM coupons WHERE product_id=?", (pid,))
        conn.commit()
        bot.answer_callback_query(call.id, "تم الحذف")
        call.data = "adm_products"
        handle_admin(call)

    elif data == "add_product":
        msg = bot.send_message(chat_id, "➕ أدخل بيانات المنتج:\nالاسم, الفئة, السعر بالدولار, المخزون, الكود الداخلي\nمثال: ببجي 60 يو سي, pubg, 0.99, 50, PUBG_UC")
        bot.register_next_step_handler(msg, save_new_product)

    elif data == "admin_users":
        rows = c.execute("SELECT user_id, name, balance_usd, banned FROM users LIMIT 50").fetchall()
        text = "👥 المستخدمون:\n\n"
        for uid, name, bal, banned in rows:
            status = "🚫" if banned else "✅"
            text += f"{status} {uid} - {name}: {bal}$\n"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("تعديل رصيد / حظر", callback_data="admin_user_modify"))
        markup.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel"))
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup)

    elif data == "admin_user_modify":
        msg = bot.send_message(chat_id, "أدخل ID المستخدم ثم الإجراء (مثال: `123456 balance 50` أو `123456 ban 0/1`):")
        bot.register_next_step_handler(msg, modify_user)

    elif data == "admin_orders":
        rows = c.execute("SELECT id, user_id, amount_syp, trx FROM recharge_orders WHERE status='pending'").fetchall()
        if not rows:
            bot.edit_message_text("لا توجد طلبات معلقة.", chat_id, msg_id)
            return
        for oid, uid, amt, trx in rows:
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("✅ قبول", callback_data=f"approve_{oid}"),
                       InlineKeyboardButton("❌ رفض", callback_data=f"reject_{oid}"))
            bot.send_message(chat_id, f"طلب #{oid}\nمستخدم: {uid}\nمبلغ: {amt:,} ليرة\nTRX: {trx}", reply_markup=markup)

    elif data == "stats":
        users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        purchases = c.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
        total = c.execute("SELECT SUM(amount_usd) FROM purchases").fetchone()[0] or 0
        bot.edit_message_text(f"📊 إحصائيات:\n👥 المستخدمين: {users}\n🛒 المشتريات: {purchases}\n💵 الإجمالي: {total}$",
                              chat_id, msg_id)

    elif data == "change_rate":
        msg = bot.send_message(chat_id, f"💱 السعر الحالي: {get_usd_rate()} ليرة\nأرسل السعر الجديد:")
        bot.register_next_step_handler(msg, lambda m: update_rate(m))

    elif data == "broadcast":
        msg = bot.send_message(chat_id, "📢 أرسل الرسالة التي تريد بثها:")
        bot.register_next_step_handler(msg, broadcast_message)

def add_coupons(message, product_id):
    codes_raw = message.text.strip().replace(",", "\n").split("\n")
    codes = [c.strip() for c in codes_raw if c.strip()]
    for code in codes:
        c.execute("INSERT INTO coupons (product_id, code, added_date) VALUES (?,?,?)",
                  (product_id, code, datetime.now().strftime("%Y-%m-%d %H:%M")))
    c.execute("UPDATE products SET stock = stock + ? WHERE id=?", (len(codes), product_id))
    conn.commit()
    bot.send_message(message.chat.id, f"✅ تم إضافة {len(codes)} كود للمنتج.")

def save_product_edit(message, field, pid):
    new_val = message.text.strip()
    if field == "price":
        new_val = float(new_val)
    elif field == "stock":
        new_val = int(new_val)
    c.execute(f"UPDATE products SET {field} = ? WHERE id=?", (new_val, pid))
    conn.commit()
    bot.send_message(message.chat.id, "✅ تم التعديل.")

def save_new_product(message):
    try:
        parts = [x.strip() for x in message.text.split(",")]
        name, cat, price, stock, code = parts[0], parts[1], float(parts[2]), int(parts[3]), parts[4]
        c.execute("INSERT INTO products (name, price_usd, stock, code, category) VALUES (?,?,?,?,?)",
                  (name, price, stock, code, cat))
        conn.commit()
        bot.send_message(message.chat.id, "✅ تم إضافة المنتج.")
    except:
        bot.send_message(message.chat.id, "❌ تنسيق خاطئ.")

def modify_user(message):
    try:
        parts = message.text.split()
        uid = int(parts[0])
        action = parts[1]
        if action == "balance":
            new_bal = float(parts[2])
            c.execute("UPDATE users SET balance_usd=? WHERE user_id=?", (new_bal, uid))
        elif action == "ban":
            ban_status = int(parts[2])
            c.execute("UPDATE users SET banned=? WHERE user_id=?", (ban_status, uid))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ تم تعديل المستخدم {uid}.")
    except:
        bot.send_message(message.chat.id, "❌ خطأ في الصيغة.")

def update_rate(message):
    try:
        new_rate = int(message.text.strip())
        set_setting("usd_rate", new_rate)
        bot.send_message(message.chat.id, f"✅ تم تحديث سعر الصرف إلى {new_rate} ليرة.")
    except:
        bot.send_message(message.chat.id, "❌ رقم غير صالح.")

def broadcast_message(message):
    users = c.execute("SELECT user_id FROM users WHERE banned=0").fetchall()
    count = 0
    for (uid,) in users:
        try:
            bot.send_message(uid, message.text)
            count += 1
        except:
            pass
    bot.send_message(message.chat.id, f"📢 تم إرسال البث إلى {count} مستخدم.")

def handle_recharge_approval(call):
    if not is_admin(call.from_user.id): return
    data = call.data
    oid = int(data.split("_")[1])
    row = c.execute("SELECT user_id, amount_usd FROM recharge_orders WHERE id=?", (oid,)).fetchone()
    if not row: return
    uid, usd_amount = row
    if data.startswith("approve_"):
        c.execute("UPDATE users SET balance_usd = balance_usd + ? WHERE user_id=?", (usd_amount, uid))
        c.execute("UPDATE recharge_orders SET status='approved' WHERE id=?", (oid,))
        bot.send_message(uid, f"✅ تمت الموافقة على الشحن وإضافة {usd_amount:.2f}$ لرصيدك.")
        bot.edit_message_text(f"✅ تم قبول طلب #{oid}", call.message.chat.id, call.message.message_id)
    else:
        c.execute("UPDATE recharge_orders SET status='rejected' WHERE id=?", (oid,))
        bot.send_message(uid, "❌ تم رفض طلب الشحن الخاص بك.")
        bot.edit_message_text(f"❌ تم رفض طلب #{oid}", call.message.chat.id, call.message.message_id)
    conn.commit()

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    print("🚀 البوت الاحترافي يعمل...")
    bot.infinity_polling()