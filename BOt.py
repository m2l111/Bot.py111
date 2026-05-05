import sqlite3
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from keep_alive import keep_alive

# ---------- الإعدادات الأساسية ----------
TOKEN = "8695956195:AAHiB1yHZeivaa7t3RQZh28_HuQjogvTYEE"  # ⚠️ استبدل بتوكنك
MAIN_ADMIN_ID = 7046655626   # الأدمن الرئيسي (أنت)
DEFAULT_USD_RATE = 13000

bot = telebot.TeleBot(TOKEN)

# ---------- قاعدة البيانات ----------
conn = sqlite3.connect("shop.db", check_same_thread=False)
c = conn.cursor()

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
c.execute('''CREATE TABLE IF NOT EXISTS admins
    (user_id INTEGER PRIMARY KEY, permissions TEXT DEFAULT '')''')
c.execute('''CREATE TABLE IF NOT EXISTS payment_methods
    (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, number TEXT, active INTEGER DEFAULT 1)''')

# تحديث الأعمدة القديمة
c.execute("PRAGMA table_info(users)")
cols = [col[1] for col in c.fetchall()]
if 'banned' not in cols:
    c.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")
c.execute("PRAGMA table_info(products)")
cols = [col[1] for col in c.fetchall()]
if 'category' not in cols:
    c.execute("ALTER TABLE products ADD COLUMN category TEXT DEFAULT 'other'")

# إعدادات افتراضية
c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('usd_rate', ?)", (DEFAULT_USD_RATE,))

# طرق دفع افتراضية إن لم توجد
c.execute("SELECT COUNT(*) FROM payment_methods")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO payment_methods (name, number, active) VALUES ('سيريتل كاش', '55347208', 1)")
    c.execute("INSERT INTO payment_methods (name, number, active) VALUES ('شام كاش', 'لم يحدد', 1)")

# منتجات افتراضية إن لم توجد
c.execute("SELECT COUNT(*) FROM products")
if c.fetchone()[0] == 0:
    products_list = [
        ("فري فاير - 100 جواهر", 0.95, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 200 جواهر", 1.80, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 500 جواهر", 4.50, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 1000 جواهر", 8.99, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 2000 جواهر", 16.99, 0, "FF_DIAMOND", "freefire"),
        ("فري فاير - 4000 جواهر", 32.99, 0, "FF_DIAMOND", "freefire"),
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

# ---------- دوال مساعدة ----------
def get_setting(key):
    row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else None

def set_setting(key, value):
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
    conn.commit()

def get_usd_rate():
    return int(get_setting("usd_rate") or DEFAULT_USD_RATE)

def is_main_admin(uid):
    return uid == MAIN_ADMIN_ID

def get_admin_permissions(uid):
    row = c.execute("SELECT permissions FROM admins WHERE user_id=?", (uid,)).fetchone()
    return row[0].split(',') if row else None

def is_admin(uid):
    return is_main_admin(uid) or get_admin_permissions(uid) is not None

# ---------- القائمة الرئيسية ----------
def main_menu(user_id, chat_id, message_id=None, edit=False):
    c.execute("SELECT name, banned FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()
    if user and user[1]:
        if not edit:
            bot.send_message(chat_id, "❌ أنت محظور من استخدام البوت.")
        return
    name = user[0] if user else "مستخدم"
    rate = get_usd_rate()

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("🎮 فري فاير", callback_data="cat_freefire"),
               InlineKeyboardButton("🔫 ببجي", callback_data="cat_pubg"))
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

# ---------- معالج الأزرار ----------
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    data = call.data
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row and row[0] and not is_admin(user_id):
        bot.answer_callback_query(call.id, "❌ محظور")
        return

    # --- أزرار الفئات ---
    if data == "cat_freefire":
        rows = c.execute("SELECT id, name, price_usd FROM products WHERE category='freefire' AND stock>0").fetchall()
        if not rows:
            bot.edit_message_text("🎮 لا توجد منتجات فري فاير متاحة حالياً.", chat_id, msg_id)
            return
        mark = InlineKeyboardMarkup()
        for pid, name, price in rows:
            mark.add(InlineKeyboardButton(f"{name} - {price}$", callback_data=f"buy_{pid}"))
        mark.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        bot.edit_message_text("🎮 منتجات فري فاير:", chat_id, msg_id, reply_markup=mark)

    elif data == "cat_pubg":
        rows = c.execute("SELECT id, name, price_usd FROM products WHERE category='pubg' AND stock>0").fetchall()
        if not rows:
            bot.edit_message_text("🔫 لا توجد منتجات ببجي متاحة حالياً.", chat_id, msg_id)
            return
        mark = InlineKeyboardMarkup()
        for pid, name, price in rows:
            mark.add(InlineKeyboardButton(f"{name} - {price}$", callback_data=f"buy_{pid}"))
        mark.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        bot.edit_message_text("🔫 منتجات ببجي:", chat_id, msg_id, reply_markup=mark)

    # --- شراء منتج (من المخزون) ---
    elif data.startswith("buy_"):
        pid = int(data.split("_")[1])
        prod = c.execute("SELECT name, price_usd, stock FROM products WHERE id=?", (pid,)).fetchone()
        if not prod or prod[2] <= 0:
            bot.answer_callback_query(call.id, "❌ المنتج غير متوفر")
            return
        bal = c.execute("SELECT balance_usd FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
        if bal < prod[1]:
            bot.answer_callback_query(call.id, f"💰 رصيدك {bal}$ غير كاف")
            return

        # سحب كود من المخزون
        coupon = c.execute("SELECT id, code FROM coupons WHERE product_id=? AND used=0 LIMIT 1", (pid,)).fetchone()
        if not coupon:
            bot.answer_callback_query(call.id, "⚠️ نفذت الأكواد لهذا المنتج. جاري توفيرها قريباً.")
            return

        c.execute("UPDATE users SET balance_usd = balance_usd - ? WHERE user_id=?", (prod[1], user_id))
        c.execute("UPDATE coupons SET used=1 WHERE id=?", (coupon[0],))
        c.execute("UPDATE products SET stock = stock - 1 WHERE id=?", (pid,))
        c.execute("INSERT INTO purchases (user_id, product_name, amount_usd, code, date) VALUES (?,?,?,?,?)",
                  (user_id, prod[0], prod[1], coupon[1], datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()

        bot.send_message(MAIN_ADMIN_ID, f"🔔 شراء جديد\n👤 {user_id}\n🎮 {prod[0]}\n💵 {prod[1]}$\n🎫 {coupon[1]}")
        bot.edit_message_text(
            f"✅ **تم الشراء**\n\n{prod[0]}\n💵 السعر: {prod[1]}$\n🎁 الكود: `{coupon[1]}`\n💰 رصيدك المتبقي: {bal-prod[1]}$",
            chat_id, msg_id, parse_mode="Markdown"
        )

    # --- الرصيد ---
    elif data == "balance":
        bal = c.execute("SELECT balance_usd FROM users WHERE user_id=?", (user_id,)).fetchone()[0]
        rate = get_usd_rate()
        bot.edit_message_text(f"💰 رصيدك: {bal}$\n💱 يعادل: {bal*rate:,.0f} ل.س", chat_id, msg_id)

    # --- شحن الرصيد (قائمة طرق الدفع المفعلة) ---
    elif data == "recharge":
        methods = c.execute("SELECT id, name, number FROM payment_methods WHERE active=1").fetchall()
        if not methods:
            bot.edit_message_text("🚫 لا توجد طرق دفع متاحة حالياً.", chat_id, msg_id)
            return
        mark = InlineKeyboardMarkup()
        for mid, name, number in methods:
            mark.add(InlineKeyboardButton(f"💳 {name}", callback_data=f"paymethod_{mid}"))
        mark.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
        bot.edit_message_text("اختر طريقة الدفع:", chat_id, msg_id, reply_markup=mark)

    elif data.startswith("paymethod_"):
        mid = int(data.split("_")[1])
        method = c.execute("SELECT name, number FROM payment_methods WHERE id=? AND active=1", (mid,)).fetchone()
        if not method:
            bot.answer_callback_query(call.id, "الطريقة غير متاحة")
            return
        name, number = method
        text = (
            f"💳 **{name}**\n\n"
            f"📱 رقم الحساب: `{number}`\n\n"
            "📝 *تعليمات:*\n"
            "1. قم بتحويل المبلغ إلى الرقم أعلاه.\n"
            "2. بعد التحويل، أرسل رقم العملية (TRX).\n\n"
            "⚠️ *تنبيه: نحن غير مسؤولين عن أخطاء التحويل. تأكد من الرقم والمبلغ.*"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ تم التحويل، أرسل TRX", callback_data="send_trx"))
        markup.add(InlineKeyboardButton("🔙 طرق الدفع", callback_data="recharge"))
        bot.edit_message_text(text, chat_id, msg_id, parse_mode="Markdown", reply_markup=markup)

    elif data == "send_trx":
        msg = bot.send_message(chat_id, "📱 أرسل رقم العملية (TRX) الخاص بالتحويل:")
        bot.register_next_step_handler(msg, process_recharge_trx)

    # --- مشترياتي ---
    elif data == "purchases":
        rows = c.execute("SELECT product_name, amount_usd, code, date FROM purchases WHERE user_id=? ORDER BY id DESC LIMIT 10",
                         (user_id,)).fetchall()
        if not rows:
            bot.edit_message_text("📭 لا توجد مشتريات", chat_id, msg_id)
            return
        txt = "📦 آخر المشتريات:\n\n"
        for n, a, cd, dt in rows:
            txt += f"{n} - {a}$\n🎫 `{cd}`\n{dt}\n---\n"
        bot.edit_message_text(txt, chat_id, msg_id, parse_mode="Markdown")

    # --- رجوع ---
    elif data == "back_to_main":
        main_menu(user_id, chat_id, msg_id, edit=True)

    # --- لوحة التحكم (عامة) ---
    elif data == "admin_panel" and is_admin(user_id):
        show_admin_panel(call)

    else:
        # تفويض أي callback آخر لدوال الإدارة
        handle_admin_actions(call)

# ---------- عرض لوحة التحكم حسب الصلاحيات ----------
def show_admin_panel(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    perms = get_admin_permissions(user_id)
    is_main = is_main_admin(user_id)

    markup = InlineKeyboardMarkup(row_width=2)
    if is_main or (perms and 'add_products' in perms):
        markup.add(InlineKeyboardButton("📦 المنتجات", callback_data="adm_products"))
    if is_main or (perms and 'view_users' in perms):
        markup.add(InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users"))
    if is_main or (perms and 'view_orders' in perms):
        markup.add(InlineKeyboardButton("💳 طلبات الشحن", callback_data="admin_orders"))
    if is_main or (perms and 'view_stats' in perms):
        markup.add(InlineKeyboardButton("📊 إحصائيات", callback_data="stats"))
    if is_main:
        markup.add(InlineKeyboardButton("💱 تغيير سعر الصرف", callback_data="change_rate"))
        markup.add(InlineKeyboardButton("📱 طرق الدفع", callback_data="manage_payment_methods"))
        markup.add(InlineKeyboardButton("👑 إدارة المشرفين", callback_data="manage_admins"))
        markup.add(InlineKeyboardButton("📢 بث للجميع", callback_data="broadcast"))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main"))
    bot.edit_message_text("⚙️ لوحة التحكم:", chat_id, msg_id, reply_markup=markup)

# ---------- دوال الإدارة الكاملة ----------
def handle_admin_actions(call):
    user_id = call.from_user.id
    data = call.data
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    perms = get_admin_permissions(user_id)
    is_main = is_main_admin(user_id)

    can_add_products = is_main or (perms and 'add_products' in perms)
    can_edit_products = is_main
    can_view_users = is_main or (perms and 'view_users' in perms)
    can_view_orders = is_main or (perms and 'view_orders' in perms)
    can_view_stats = is_main or (perms and 'view_stats' in perms)

    # --- إدارة المنتجات ---
    if data == "adm_products" and can_add_products:
        rows = c.execute("SELECT id, name, price_usd, stock FROM products").fetchall()
        mark = InlineKeyboardMarkup()
        for pid, n, p, s in rows:
            mark.add(InlineKeyboardButton(f"{n} - {p}$ | مخزون:{s}", callback_data=f"admprod_{pid}"))
        if can_add_products:
            mark.add(InlineKeyboardButton("➕ إضافة منتج", callback_data="add_product"))
        mark.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel"))
        bot.edit_message_text("📦 المنتجات:", chat_id, msg_id, reply_markup=mark)

    elif data.startswith("admprod_") and can_edit_products:
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
        bot.edit_message_text(f"🛠 {n}\nالسعر: {p}$ | المخزون: {s}\nكود داخلي: {cd}\nفئة: {cat}",
                              chat_id, msg_id, reply_markup=mark)

    elif data.startswith("editprod_") and can_edit_products:
        _, field, pid_str = data.split("_")
        pid = int(pid_str)
        if field == "codes":
            msg = bot.send_message(chat_id, "🎫 أرسل الأكواد (كل كود سطر، أو مفصولة بفاصلة):")
            bot.register_next_step_handler(msg, lambda m, p=pid: add_codes(m, p))
        else:
            prompts = {"name": "✏️ أرسل الاسم الجديد:", "price": "💵 أرسل السعر الجديد:", "stock": "📦 أرسل المخزون:"}
            msg = bot.send_message(chat_id, prompts[field])
            bot.register_next_step_handler(msg, lambda m, f=field, p=pid: edit_product(m, f, p))
        bot.delete_message(chat_id, msg_id)

    elif data.startswith("deleteprod_") and can_edit_products:
        pid = int(data.split("_")[1])
        c.execute("DELETE FROM products WHERE id=?", (pid,))
        c.execute("DELETE FROM coupons WHERE product_id=?", (pid,))
        conn.commit()
        bot.answer_callback_query(call.id, "تم الحذف")
        call.data = "adm_products"
        handle_admin_actions(call)

    elif data == "add_product" and can_add_products:
        msg = bot.send_message(chat_id, "➕ أدخل: الاسم, الفئة, السعر, المخزون, الكود الداخلي\nمثال: ببجي 60, pubg, 0.99, 50, PUBG_UC")
        bot.register_next_step_handler(msg, add_new_product)

    # --- إدارة المستخدمين ---
    elif data == "admin_users" and can_view_users:
        rows = c.execute("SELECT user_id, name, balance_usd, banned FROM users LIMIT 50").fetchall()
        txt = "👥 المستخدمون:\n\n"
        for uid, n, b, ban in rows:
            status = "🚫" if ban else "✅"
            txt += f"{status} {uid} - {n}: {b}$\n"
        mark = InlineKeyboardMarkup()
        if is_main:
            mark.add(InlineKeyboardButton("تعديل رصيد/حظر", callback_data="admin_user_modify"))
        mark.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel"))
        bot.edit_message_text(txt, chat_id, msg_id, reply_markup=mark)

    elif data == "admin_user_modify" and is_main:
        msg = bot.send_message(chat_id, "أدخل: id balance/ban القيمة\nمثال: 123456 balance 50\nأو: 123456 ban 1")
        bot.register_next_step_handler(msg, modify_user)

    # --- طلبات الشحن ---
    elif data == "admin_orders" and can_view_orders:
        rows = c.execute("SELECT id, user_id, amount_syp, trx FROM recharge_orders WHERE status='pending'").fetchall()
        if not rows:
            bot.edit_message_text("لا طلبات معلقة", chat_id, msg_id)
            return
        for oid, uid, amt, trx in rows:
            if is_main:
                mark = InlineKeyboardMarkup()
                mark.row(InlineKeyboardButton("✅ قبول", callback_data=f"approve_{oid}"),
                         InlineKeyboardButton("❌ رفض", callback_data=f"reject_{oid}"))
                bot.send_message(chat_id, f"طلب #{oid}\nمستخدم: {uid}\nمبلغ: {amt:,} ليرة\nTRX: {trx}", reply_markup=mark)
            else:
                bot.send_message(chat_id, f"طلب #{oid}\nمستخدم: {uid}\nمبلغ: {amt:,} ليرة\nTRX: {trx}")

    elif data.startswith("approve_") and is_main:
        oid = int(data.split("_")[1])
        row = c.execute("SELECT user_id, amount_usd FROM recharge_orders WHERE id=?", (oid,)).fetchone()
        if row:
            c.execute("UPDATE users SET balance_usd = balance_usd + ? WHERE user_id=?", (row[1], row[0]))
            c.execute("UPDATE recharge_orders SET status='approved' WHERE id=?", (oid,))
            conn.commit()
            bot.send_message(row[0], f"✅ تم إضافة {row[1]:.2f}$ إلى رصيدك")
            bot.edit_message_text("✅ تم القبول", chat_id, msg_id)

    elif data.startswith("reject_") and is_main:
        oid = int(data.split("_")[1])
        row = c.execute("SELECT user_id FROM recharge_orders WHERE id=?", (oid,)).fetchone()
        if row:
            c.execute("UPDATE recharge_orders SET status='rejected' WHERE id=?", (oid,))
            conn.commit()
            bot.send_message(row[0], "❌ تم رفض طلبك")
            bot.edit_message_text("❌ تم الرفض", chat_id, msg_id)

    # --- إحصائيات ---
    elif data == "stats" and can_view_stats:
        users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        purchases = c.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
        total = c.execute("SELECT SUM(amount_usd) FROM purchases").fetchone()[0] or 0
        bot.edit_message_text(f"📊 إحصائيات:\n👥 المستخدمين: {users}\n🛒 المشتريات: {purchases}\n💵 المبيعات: {total}$",
                              chat_id, msg_id)

    # --- طرق الدفع (للرئيسي فقط) ---
    elif data == "manage_payment_methods" and is_main:
        rows = c.execute("SELECT id, name, number, active FROM payment_methods").fetchall()
        txt = "📱 طرق الدفع الحالية:\n\n"
        for mid, name, number, active in rows:
            status = "✅" if active else "❌"
            txt += f"{status} {mid}. {name}: {number}\n"
        mark = InlineKeyboardMarkup()
        mark.add(InlineKeyboardButton("➕ إضافة طريقة", callback_data="add_payment_method"),
                 InlineKeyboardButton("🔄 تفعيل/تعطيل", callback_data="toggle_payment_method"))
        mark.add(InlineKeyboardButton("✏️ تعديل رقم", callback_data="edit_payment_number"),
                 InlineKeyboardButton("❌ حذف طريقة", callback_data="delete_payment_method"))
        mark.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel"))
        bot.edit_message_text(txt, chat_id, msg_id, reply_markup=mark)

    elif data == "add_payment_method" and is_main:
        msg = bot.send_message(chat_id, "أدخل اسم الطريقة والرقم مفصولين بفاصلة:\nمثال: سيريتل كاش, 0999999999")
        bot.register_next_step_handler(msg, add_payment_method)

    elif data == "toggle_payment_method" and is_main:
        msg = bot.send_message(chat_id, "أرسل ID الطريقة التي تريد تفعيلها/تعطيلها:")
        bot.register_next_step_handler(msg, toggle_payment_method)

    elif data == "edit_payment_number" and is_main:
        msg = bot.send_message(chat_id, "أرسل ID الطريقة ثم الرقم الجديد:\nمثال: 1 0999888777")
        bot.register_next_step_handler(msg, edit_payment_number)

    elif data == "delete_payment_method" and is_main:
        msg = bot.send_message(chat_id, "أرسل ID الطريقة التي تريد حذفها:")
        bot.register_next_step_handler(msg, delete_payment_method)

    # --- إدارة المشرفين ---
    elif data == "manage_admins" and is_main:
        rows = c.execute("SELECT user_id, permissions FROM admins").fetchall()
        txt = "👑 المشرفون:\n\n"
        for uid, p in rows:
            txt += f"🆔 {uid}: {p}\n"
        mark = InlineKeyboardMarkup()
        mark.add(InlineKeyboardButton("➕ إضافة مشرف", callback_data="add_admin"),
                 InlineKeyboardButton("❌ حذف مشرف", callback_data="remove_admin"))
        mark.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="admin_panel"))
        bot.edit_message_text(txt, chat_id, msg_id, reply_markup=mark)

    elif data == "add_admin" and is_main:
        msg = bot.send_message(chat_id, "أدخل ID المستخدم:")
        bot.register_next_step_handler(msg, add_admin_step1)

    elif data == "remove_admin" and is_main:
        msg = bot.send_message(chat_id, "أرسل ID المشرف الذي تريد حذفه:")
        bot.register_next_step_handler(msg, remove_admin)

    # --- تغيير سعر الصرف ---
    elif data == "change_rate" and is_main:
        msg = bot.send_message(chat_id, f"السعر الحالي: {get_usd_rate()} ل.س\nأرسل السعر الجديد:")
        bot.register_next_step_handler(msg, change_rate)

    # --- بث ---
    elif data == "broadcast" and is_main:
        msg = bot.send_message(chat_id, "📢 أرسل الرسالة:")
        bot.register_next_step_handler(msg, broadcast)

# ---------- دوال الإجراءات ----------
def process_recharge_trx(message):
    trx = message.text.strip()
    user_id = message.from_user.id
    c.execute("INSERT INTO recharge_orders (user_id, amount_syp, amount_usd, trx, status, date) VALUES (?,?,?,?,?,?)",
              (user_id, 0, 0, trx, 'pending', datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    bot.send_message(message.chat.id, "✅ تم استلام طلبك، جاري المراجعة.")
    bot.send_message(MAIN_ADMIN_ID, f"📥 طلب شحن جديد\n👤 {user_id}\n🔢 TRX: {trx}")

def add_codes(message, pid):
    codes = [c.strip() for c in message.text.replace(",", "\n").split("\n") if c.strip()]
    for cd in codes:
        c.execute("INSERT INTO coupons (product_id, code, added_date) VALUES (?,?,?)",
                  (pid, cd, datetime.now().strftime("%Y-%m-%d %H:%M")))
    c.execute("UPDATE products SET stock = stock + ? WHERE id=?", (len(codes), pid))
    conn.commit()
    bot.send_message(message.chat.id, f"✅ تم إضافة {len(codes)} كود.")

def edit_product(message, field, pid):
    val = message.text.strip()
    if field == "price": val = float(val)
    elif field == "stock": val = int(val)
    c.execute(f"UPDATE products SET {field}=? WHERE id=?", (val, pid))
    conn.commit()
    bot.send_message(message.chat.id, "✅ تم التعديل.")

def add_new_product(message):
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
            c.execute("UPDATE users SET balance_usd=? WHERE user_id=?", (float(parts[2]), uid))
        elif action == "ban":
            c.execute("UPDATE users SET banned=? WHERE user_id=?", (int(parts[2]), uid))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ تم تعديل المستخدم {uid}.")
    except:
        bot.send_message(message.chat.id, "❌ خطأ في الصيغة.")

def add_payment_method(message):
    try:
        name, number = message.text.split(",")
        name = name.strip()
        number = number.strip()
        c.execute("INSERT INTO payment_methods (name, number, active) VALUES (?,?,1)", (name, number))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ تم إضافة طريقة {name}.")
    except:
        bot.send_message(message.chat.id, "❌ خطأ في الإدخال.")

def toggle_payment_method(message):
    try:
        mid = int(message.text.strip())
        current = c.execute("SELECT active FROM payment_methods WHERE id=?", (mid,)).fetchone()
        if not current:
            bot.send_message(message.chat.id, "❌ معرف غير موجود.")
            return
        new_status = 0 if current[0] else 1
        c.execute("UPDATE payment_methods SET active=? WHERE id=?", (new_status, mid))
        conn.commit()
        state = "تفعيل" if new_status else "تعطيل"
        bot.send_message(message.chat.id, f"✅ تم {state} الطريقة.")
    except:
        bot.send_message(message.chat.id, "❌ خطأ.")

def edit_payment_number(message):
    try:
        mid, new_number = message.text.split()
        mid = int(mid)
        c.execute("UPDATE payment_methods SET number=? WHERE id=?", (new_number.strip(), mid))
        conn.commit()
        bot.send_message(message.chat.id, "✅ تم تحديث الرقم.")
    except:
        bot.send_message(message.chat.id, "❌ خطأ.")

def delete_payment_method(message):
    try:
        mid = int(message.text.strip())
        c.execute("DELETE FROM payment_methods WHERE id=?", (mid,))
        conn.commit()
        bot.send_message(message.chat.id, "✅ تم حذف الطريقة.")
    except:
        bot.send_message(message.chat.id, "❌ خطأ.")

def add_admin_step1(message):
    try:
        uid = int(message.text.strip())
        msg = bot.send_message(message.chat.id, "أرسل الصلاحيات مفصولة بفاصلة:\nمثال: add_products,view_orders\nالصلاحيات: add_products, view_users, view_orders, view_stats")
        bot.register_next_step_handler(msg, lambda m, u=uid: add_admin_finish(m, u))
    except:
        bot.send_message(message.chat.id, "❌ ID غير صحيح.")

def add_admin_finish(message, uid):
    perms = message.text.strip()
    c.execute("INSERT OR REPLACE INTO admins (user_id, permissions) VALUES (?,?)", (uid, perms))
    conn.commit()
    bot.send_message(message.chat.id, f"✅ تم إضافة المشرف {uid} بصلاحيات: {perms}")

def remove_admin(message):
    try:
        uid = int(message.text.strip())
        c.execute("DELETE FROM admins WHERE user_id=?", (uid,))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ تم حذف المشرف {uid}.")
    except:
        bot.send_message(message.chat.id, "❌ خطأ.")

def change_rate(message):
    try:
        rate = int(message.text.strip())
        set_setting("usd_rate", rate)
        bot.send_message(message.chat.id, f"✅ السعر الجديد: {rate} ل.س")
    except:
        bot.send_message(message.chat.id, "❌ رقم غير صالح.")

def broadcast(message):
    users = c.execute("SELECT user_id FROM users WHERE banned=0").fetchall()
    cnt = 0
    for (uid,) in users:
        try:
            bot.send_message(uid, message.text)
            cnt += 1
        except:
            pass
    bot.send_message(message.chat.id, f"📢 تم الإرسال إلى {cnt} مستخدم.")

# ---------- تشغيل البوت ----------
if __name__ == "__main__":
    keep_alive()
    print("🚀 البوت النهائي يعمل...")
    bot.infinity_polling()