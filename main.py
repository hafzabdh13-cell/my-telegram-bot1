import os
import sys
import time
import logging
import telebot
import sqlite3
import subprocess
import py_compile
import zipfile
import requests
from datetime import datetime, timedelta
from flask import Flask, request, send_from_directory, abort
from telebot import types
from waitress import serve

# ================= إعدادات التسجيل =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("VirtualServerPro")

# ================= FLASK SERVER =================
app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "8790387996:AAFB6u4jHWrtsGPnECIxLWxiyJm8rgrV5Vs")
ADMIN_ID = 7484089854
OWNER_USER = "@HAFZAbdh"
OWNER_FULL_NAME = "حافظ عبده احمد عبدالرحمن احمد"
MY_JAIB_ACCOUNT = "784714890"

bot = telebot.TeleBot(TOKEN, threaded=False)
BASE_DIR = "hosted_bots"
os.makedirs(BASE_DIR, exist_ok=True)
active_processes = {}

# ================= قاعدة البيانات =================
DB_NAME = "hosting_pro.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, 
        stars INTEGER DEFAULT 0, 
        expire TEXT,
        free_used INTEGER DEFAULT 0,
        last_free_time TEXT
    )
    """)
    conn.commit()
    conn.close()
    logger.info("Database ready.")

init_db()

# ================= دوال الاشتراك =================
def create_user_and_check_free(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT free_used FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        expire_time = datetime.now() + timedelta(hours=1)
        expire_str = expire_time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO users (user_id, stars, expire, free_used, last_free_time) VALUES (?, ?, ?, ?, ?)", 
                       (user_id, 0, expire_str, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    conn.close()

def is_sub_active(user_id):
    if user_id == ADMIN_ID: 
        return True
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT expire FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if not user or not user[0]: 
        return False
    try:
        return datetime.now() < datetime.strptime(user[0], "%Y-%m-%d %H:%M:%S")
    except: 
        return False

def set_subscription(user_id, days=0, hours=0):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT expire FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    current_expire = None
    if user and user[0]:
        try: current_expire = datetime.strptime(user[0], "%Y-%m-%d %H:%M:%S")
        except: pass
    if current_expire and current_expire > datetime.now():
        expire_time = current_expire + timedelta(days=days, hours=hours)
    else:
        expire_time = datetime.now() + timedelta(days=days, hours=hours)
    cursor.execute("UPDATE users SET expire=? WHERE user_id=?", (expire_time.strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()
    conn.close()

def get_remaining_time(user_id):
    if user_id == ADMIN_ID:
        return "♾️ وصول مطور غير محدود"
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT expire FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if not user or not user[0]: 
        return "❌ غير مشترك"
    try:
        rem = datetime.strptime(user[0], "%Y-%m-%d %H:%M:%S") - datetime.now()
        if rem.total_seconds() < 0:
            return "❌ منتهي الصلاحية"
        hours_total = rem.seconds // 3600
        minutes_total = (rem.seconds % 3600) // 60
        if rem.days > 0:
            return f"⏳ متبقي {rem.days} يوم و {hours_total} ساعة"
        else:
            return f"⏳ متبقي {hours_total} ساعة و {minutes_total} دقيقة"
    except:
        return "❌ خطأ في النظام"

# ================= لوحات المفاتيح =================
def start_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🎛️ فتح لوحة التحكم السحابية"))
    markup.add(types.KeyboardButton("💳 تفعيل حسابي وشحن الرصيد"))
    markup.add(types.KeyboardButton("🎁 تفعيل الخدمة المجانية اليومية"))
    return markup

def main_menu(user_id):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("📁 إدارة الملفات", callback_data="files"),
        types.InlineKeyboardButton("📤 رفع ملف لسيرفر", callback_data="upload"),
        types.InlineKeyboardButton("🌐 رفع موقع ويب", callback_data="webup"),
        types.InlineKeyboardButton("🚀 تشغيل سيرفر", callback_data="run"),
        types.InlineKeyboardButton("🛑 إيقاف سيرفر", callback_data="stop"),
        types.InlineKeyboardButton("🌐 رابط الموقع", callback_data="link"),
        types.InlineKeyboardButton("🔄 تحديث", callback_data="refresh")
    )
    owner_link = OWNER_USER.replace("@", "")
    m.add(types.InlineKeyboardButton("👑 الدعم الفني", url=f"https://t.me/{owner_link}"))
    return m

def bot_selector_menu(action):
    m = types.InlineKeyboardMarkup(row_width=2)
    for i in range(1, 5):
        m.add(types.InlineKeyboardButton(f"🤖 سيرفر {i}", callback_data=f"{action}_{i}"))
    m.add(types.InlineKeyboardButton("🔙 العودة", callback_data="back"))
    return m

def payment_methods_keyboard():
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        types.InlineKeyboardButton("⭐ شحن تلقائي عبر نجوم تلجرام", callback_data="stars_shop"),
        types.InlineKeyboardButton("📱 محفظة جيب (JAIB)", callback_data="pay_jaib"),
        types.InlineKeyboardButton("🏦 بنك الكريمي الإسلامي", callback_data="pay_bank"),
        types.InlineKeyboardButton("💱 شبكة الامتياز للصرافة", callback_data="pay_emtiaz")
    )
    return m

def stars_packages_keyboard():
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        types.InlineKeyboardButton("✨ باقة شهر (30 يوم) - 100 نجمة", callback_data="buy_stars_30"),
        types.InlineKeyboardButton("🔥 باقة ربع سنة (90 يوم) - 300 نجمة", callback_data="buy_stars_90"),
        types.InlineKeyboardButton("👑 باقة سنة (365 يوم) - 650 نجمة", callback_data="buy_stars_365")
    )
    m.add(types.InlineKeyboardButton("🔙 العودة", callback_data="back_to_shop"))
    return m

def manual_packages_keyboard(method):
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        types.InlineKeyboardButton("🗓️ باقة أسبوع (7 أيام) - 2USD", callback_data=f"order_{method}_7"),
        types.InlineKeyboardButton("✨ باقة شهر (30 يوم) - 4USD", callback_data=f"order_{method}_30"),
        types.InlineKeyboardButton("🔥 باقة ربع سنة (90 يوم) - 6USD", callback_data=f"order_{method}_90"),
        types.InlineKeyboardButton("👑 باقة سنة (365 يوم) - 10USD", callback_data=f"order_{method}_365")
    )
    m.add(types.InlineKeyboardButton("🔙 العودة", callback_data="back_to_shop"))
    return m

def admin_approval_keyboard(target_id, package_days, price):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("✅ قبول وتفعيل", callback_data=f"accept_{package_days}_{target_id}"),
        types.InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject_{target_id}")
    )
    return m

# ================= أمر البداية =================
@bot.message_handler(commands=["start"])
def start(message):
    uid = message.chat.id
    create_user_and_check_free(uid)
    is_active = is_sub_active(uid)
    status_icon = "🟢 مفعّل بنجاح" if is_active else "🔴 غير مفعل / منتهي"
    time_rem = get_remaining_time(uid)
    
    welcome = f"""
✨ **مرحباً بك في مجمع استضافات VIRTUAL SERVER PRO** ✨
━━━━━━━━━━━━━━━━━━━━
⚙️ **تشغيل بوتات + استضافة مواقع ويب + رفع أي ملفات بدون قيود.**

👤 **العضو:** {message.from_user.first_name}
🆔 **المعرف الخاص بك:** `{uid}`
🛡️ **حالة السيرفر:** {status_icon}
⏳ **فترة الصلاحية:** `{time_rem}`
━━━━━━━━━━━━━━━━━━━━
👇 **اختر من الأزرار بالأسفل لبدء إدارة وتفعيل خدماتك السحابية:**
"""
    bot.send_message(uid, welcome, parse_mode="Markdown", reply_markup=start_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "🎛️ فتح لوحة التحكم السحابية")
def open_panel(message):
    bot.send_message(message.chat.id, "💎 **لوحة التحكم بالخدمات السحابية:**", reply_markup=main_menu(message.chat.id))

@bot.message_handler(func=lambda msg: msg.text == "💳 تفعيل حسابي وشحن الرصيد")
def open_shop(message):
    shop_text = """💳 **بوابة شحن وتفعيل الاشتراك السحابي المتعدد:**
━━━━━━━━━━━━━━━━━━━━
💵 **الدفع اليدوي (بالريال اليمني أو بالدولار):**

💻 **طرق الدفع المحلية المتاحة:**
1️⃣ محفظة جيب (JAIB)
2️⃣ بنك الكريمي الإسلامي
3️⃣ شبكة الامتياز للصرافة 🌟

👤 **اسم المستلم المعتمد:** حافظ عبده احمد عبدالرحمن احمد
📱 **رقم الهاتف / الحساب:** 👈 784714890 👉

🌟 **الدفع التلقائي بالنجوم:**
تفعيل فوري آلي دون الحاجة لانتظار موافقة الإدارة!

👇 **اختر الخطة المناسبة لك من الأسفل:**"""
    bot.send_message(message.chat.id, shop_text, reply_markup=payment_methods_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "🎁 تفعيل الخدمة المجانية اليومية")
def active_free_day(message):
    uid = message.chat.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT last_free_time FROM users WHERE user_id=?", (uid,))
    row = cursor.fetchone()
    can_get_free = False
    if row and row[0]:
        try:
            last_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
            if datetime.now() - last_time >= timedelta(days=1):
                can_get_free = True
        except:
            can_get_free = True
    else:
        can_get_free = True
    if can_get_free:
        set_subscription(uid, hours=1)
        cursor.execute("UPDATE users SET last_free_time=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
        conn.commit()
        bot.send_message(uid, "🎁 **تهانينا! تم تفعيل فترة مجانية صالحة لمدة ساعة واحدة بنجاح لتجربة السيرفرات.**", parse_mode="Markdown")
    else:
        bot.send_message(uid, "⚠️ **عذراً، لقد استهلكت مكافأتك المجانية اليوم! يمكنك المحاولة مجدداً بعد مرور 24 ساعة.**")
    conn.close()

# ================= معالجة الأزرار =================
@bot.callback_query_handler(func=lambda call: True)
def handle_call(call):
    uid = call.message.chat.id
    mid = call.message.message_id
    data = call.data
    
    logger.info(f"Callback: {data} from user {uid}")

    # ---------- الدفع بالنجوم ----------
    if data == "stars_shop":
        bot.edit_message_text("⭐ **متجر شحن نجوم تلجرام التلقائي الفوري:**\nاختر الباقة المراد الاشتراك بها وسيتم تفعيلك تلقائياً:", uid, mid, reply_markup=stars_packages_keyboard())
    
    elif data == "buy_stars_30":
        bot.send_invoice(uid, "اشتراك برو (شهري)", "تفعيل 4 بوتات لمدة 30 يوم تلقائياً.", "stars_30", "", "XTR", [types.LabeledPrice("باقة شهر", 100)])
    
    elif data == "buy_stars_90":
        bot.send_invoice(uid, "اشتراك برو (ربع سنوي)", "تفعيل 4 بوتات لمدة 90 يوم تلقائياً.", "stars_90", "", "XTR", [types.LabeledPrice("باقة ربع سنة", 300)])
    
    elif data == "buy_stars_365":
        bot.send_invoice(uid, "اشتراك برو (سنوي)", "تفعيل 4 بوتات لمدة 365 يوم تلقائياً.", "stars_365", "", "XTR", [types.LabeledPrice("باقة سنة", 650)])

    # ---------- الدفع اليدوي ----------
    elif data == "pay_jaib":
        bot.edit_message_text("📱 **دفع يدوي عبر محفظة جيب (JAIB):**\n━━━━━━━━━━━━━━━━━━━━\n👤 المستلم: **حافظ عبده احمد عبدالرحمن احمد**\n📱 رقم الحساب: `784714890`\n\nاختر الباقة:", uid, mid, reply_markup=manual_packages_keyboard("jaib"))
    
    elif data == "pay_bank":
        bot.edit_message_text("🏦 **دفع يدوي عبر بنك الكريمي الإسلامي:**\n━━━━━━━━━━━━━━━━━━━━\n👤 المستلم: **حافظ عبده احمد عبدالرحمن احمد**\n📱 رقم الحساب: `784714890`\n\nاختر الباقة:", uid, mid, reply_markup=manual_packages_keyboard("bank"))
    
    elif data == "pay_emtiaz":
        bot.edit_message_text("💱 **دفع يدوي عبر شبكة الامتياز للصرافة:**\n━━━━━━━━━━━━━━━━━━━━\n👤 المستلم: **حافظ عبده احمد عبدالرحمن احمد**\n📱 رقم الحساب: `784714890`\n\nاختر الباقة:", uid, mid, reply_markup=manual_packages_keyboard("emtiaz"))
    
    elif data == "back_to_shop":
        shop_text = """💳 **بوابة شحن وتفعيل الاشتراك السحابي المتعدد:**
━━━━━━━━━━━━━━━━━━━━
💵 **الدفع اليدوي (بالريال اليمني أو بالدولار):**

💻 **طرق الدفع المحلية المتاحة:**
1️⃣ محفظة جيب (JAIB)
2️⃣ بنك الكريمي الإسلامي
3️⃣ شبكة الامتياز للصرافة 🌟

👤 **اسم المستلم المعتمد:** حافظ عبده احمد عبدالرحمن احمد
📱 **رقم الهاتف / الحساب:** 👈 784714890 👉

🌟 **الدفع التلقائي بالنجوم:**
تفعيل فوري آلي دون الحاجة لانتظار موافقة الإدارة!

👇 **اختر الخطة المناسبة لك من الأسفل:**"""
        bot.edit_message_text(shop_text, uid, mid, reply_markup=payment_methods_keyboard())

    # ---------- طلب شحن يدوي ----------
    elif data.startswith("order_"):
        parts = data.split("_")
        method = parts[1]
        days = int(parts[2])
        prices = {7: "2$", 30: "4$", 90: "6$", 365: "10$"}
        price = prices.get(days, "?")
        
        method_names = {"jaib": "محفظة جيب (JAIB)", "bank": "بنك الكريمي الإسلامي", "emtiaz": "شبكة الامتياز للصرافة"}
        method_name = method_names.get(method, method)
        
        text = f"""📱 **بوابة الدفع اليدوي - {method_name}:**
━━━━━━━━━━━━━━━━━━━━
👤 **اسم المستلم:** {OWNER_FULL_NAME}
📱 **رقم الحساب:** `{MY_JAIB_ACCOUNT}`
📦 **الباقة المختارة:** `{days} يوم`
💰 **القيمة المطلوبة:** **{price}** (أو ما يعادلها بالريال اليمني)

👇 **قم بالتحويل الآن ثم أرسل صورة السند أو كود الحوالة هنا مباشرة لمراجعة الدفع:**"""
        
        msg = bot.send_message(uid, text, parse_mode="Markdown")
        bot.register_next_step_handler(msg, receive_manual_invoice, days, price, method_name)

    # ---------- صلاحيات المطور ----------
    elif data.startswith("accept_"):
        parts = data.split("_")
        days = int(parts[1])
        target = int(parts[2])
        set_subscription(target, days=days)
        bot.edit_message_caption(f"✅ **تم تفعيل الاشتراك باقة ({days} يوم) للمستخدم بنجاح.**", uid, mid)
        bot.send_message(target, f"🎉 **أهلاً بك! تم مراجعة السند وقبوله من قِبل المطور حافظ، وتم تفعيل اشتراكك السحابي لمدة {days} يوماً بنجاح!**")
    
    elif data.startswith("reject_"):
        target = int(data.split("_")[1])
        bot.edit_message_caption("❌ **تم رفض السند وإلغاء الطلب.**", uid, mid)
        bot.send_message(target, "❌ **عذراً، تم مراجعة السند المرسل من قبلك وتبين أنه غير صالح أو مرفوض من قبل الإدارة.**")

    # ---------- الأزرار الرئيسية (بدون فحص اشتراك) ----------
    elif data == "run":
        bot.edit_message_text("🚀 اختر رقم السيرفر لتشغيله:", uid, mid, reply_markup=bot_selector_menu("run"))
    
    elif data == "stop":
        bot.edit_message_text("🛑 اختر رقم السيرفر لإيقافه:", uid, mid, reply_markup=bot_selector_menu("stop"))
    
    elif data == "upload":
        bot.edit_message_text("📤 اختر رقم السيرفر لرفع أي ملف إليه:", uid, mid, reply_markup=bot_selector_menu("upload"))
    
    elif data == "files":
        bot.edit_message_text("📁 اختر رقم السيرفر لعرض ملفاته:", uid, mid, reply_markup=bot_selector_menu("files"))
    
    elif data == "webup":
        msg = bot.send_message(uid, "🌐 أرسل ملفات الموقع (مضغوطة .zip أو أي ملفات HTML/CSS/JS). لا توجد قيود.")
        bot.register_next_step_handler(msg, receive_website_files)
    
    elif data == "link":
        web_dir = os.path.join(BASE_DIR, str(uid), "website")
        if os.path.isdir(web_dir) and os.listdir(web_dir):
            render_url = os.environ.get("RENDER_EXTERNAL_URL", "http://your-url.onrender.com")
            bot.send_message(uid, f"🌐 رابط موقعك: {render_url}/site/{uid}/")
        else:
            bot.send_message(uid, "📭 لم ترفع موقعًا بعد.")
    
    elif data == "back":
        bot.edit_message_text("🏠 القائمة الرئيسية:", uid, mid, reply_markup=main_menu(uid))
    
    elif data == "refresh":
        bot.edit_message_text("💎 **لوحة التحكم بالخدمات السحابية:**", uid, mid, reply_markup=main_menu(uid))

    # ---------- تشغيل سيرفر ----------
    elif data.startswith("run_"):
        bot_num = data.split("_")[1]
        process_key = f"{uid}_{bot_num}"
        path = f"{BASE_DIR}/{uid}/bot{bot_num}/bot.py"
        
        if not os.path.exists(path):
            bot.answer_callback_query(call.id, f"❌ لا يوجد bot.py في السيرفر {bot_num}!", show_alert=True)
            return
        if process_key in active_processes and active_processes[process_key].poll() is None:
            bot.answer_callback_query(call.id, "⚠️ السيرفر يعمل بالفعل!", show_alert=True)
            return
        
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as e:
            bot.send_message(uid, f"❌ خطأ برمجي:\n```{str(e)[:500]}```", parse_mode="Markdown")
            return
        
        try:
            proc = subprocess.Popen([sys.executable, path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            time.sleep(2)
            if proc.poll() is not None:
                _, stderr = proc.communicate()
                bot.send_message(uid, f"❌ فشل التشغيل:\n```{stderr[:2000]}```", parse_mode="Markdown")
                return
            active_processes[process_key] = proc
            bot.edit_message_text(f"🟢 تم تشغيل السيرفر {bot_num}.", uid, mid, reply_markup=main_menu(uid))
        except Exception as e:
            bot.send_message(uid, f"❌ خطأ: {str(e)}")

    # ---------- إيقاف سيرفر ----------
    elif data.startswith("stop_"):
        bot_num = data.split("_")[1]
        process_key = f"{uid}_{bot_num}"
        if process_key in active_processes and active_processes[process_key].poll() is None:
            active_processes[process_key].terminate()
            del active_processes[process_key]
            bot.edit_message_text(f"🛑 تم إيقاف السيرفر {bot_num}.", uid, mid, reply_markup=main_menu(uid))
        else:
            bot.answer_callback_query(call.id, "⚠️ السيرفر متوقف بالفعل.", show_alert=True)

    # ---------- رفع ملف للسيرفر ----------
    elif data.startswith("upload_"):
        bot_num = data.split("_")[1]
        msg = bot.send_message(uid, f"📤 أرسل أي ملف لرفعه للسيرفر {bot_num}. إذا كان ملف بايثون (.py) سيتم تحويله تلقائياً إلى bot.py.")
        bot.register_next_step_handler(msg, save_any_file, bot_num)

    # ---------- عرض الملفات ----------
    elif data.startswith("files_"):
        bot_num = data.split("_")[1]
        folder = f"{BASE_DIR}/{uid}/bot{bot_num}"
        if os.path.exists(folder):
            files = os.listdir(folder)
            if files:
                text = "\n".join([f"📄 {f} ({os.path.getsize(os.path.join(folder,f))/1024:.2f} KB)" for f in files])
                bot.send_message(uid, f"📁 ملفات السيرفر {bot_num}:\n{text}")
            else:
                bot.send_message(uid, "📭 المجلد فارغ.")
        else:
            bot.send_message(uid, "📭 لا يوجد مجلد بعد.")

    bot.answer_callback_query(call.id)

# ================= استقبال الملفات =================
def save_any_file(message, bot_num):
    uid = message.chat.id
    if not message.document:
        bot.send_message(uid, "❌ أرسل ملفًا كمستند.")
        return
    try:
        folder = os.path.join(BASE_DIR, str(uid), f"bot{bot_num}")
        os.makedirs(folder, exist_ok=True)
        file_info = bot.get_file(message.document.file_id)
        content = bot.download_file(file_info.file_path)
        original_name = message.document.file_name or "uploaded_file"
        ext = os.path.splitext(original_name)[1].lower()
        if ext == ".py":
            final_name = "bot.py"
            bot.send_message(uid, f"🔁 تم تحويل `{original_name}` تلقائياً إلى `{final_name}` ليصبح جاهزاً للتشغيل.")
        else:
            final_name = original_name
        with open(os.path.join(folder, final_name), "wb") as f:
            f.write(content)
        bot.send_message(uid, f"✅ تم رفع الملف بنجاح إلى السيرفر {bot_num}.")
    except Exception as e:
        bot.send_message(uid, f"❌ فشل: {str(e)}")

def receive_website_files(message):
    uid = message.chat.id
    if not message.document:
        bot.send_message(uid, "❌ أرسل ملفات الموقع كمستند.")
        return
    try:
        web_dir = os.path.join(BASE_DIR, str(uid), "website")
        os.makedirs(web_dir, exist_ok=True)
        file_info = bot.get_file(message.document.file_id)
        content = bot.download_file(file_info.file_path)
        name = message.document.file_name.lower()
        if name.endswith('.zip'):
            zip_path = os.path.join(web_dir, "temp.zip")
            with open(zip_path, "wb") as f:
                f.write(content)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(web_dir)
            os.remove(zip_path)
            bot.send_message(uid, "✅ تم استخراج الموقع بنجاح.")
        else:
            with open(os.path.join(web_dir, message.document.file_name), "wb") as f:
                f.write(content)
            bot.send_message(uid, f"✅ تم رفع `{message.document.file_name}`.")
    except Exception as e:
        bot.send_message(uid, f"❌ فشل رفع الموقع: {str(e)}")

# ================= الدفع اليدوي =================
def receive_manual_invoice(message, days, price, method_name):
    uid = message.chat.id
    markup = admin_approval_keyboard(uid, days, price)
    if message.photo:
        bot.send_message(uid, "⏳ **تم استلام صورة السند بنجاح وجاري إرسالها للمطور (حافظ) للمراجعة والتفعيل...**")
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id,
                       caption=f"💰 **طلب شحن يدوي جديد:**\n👤 الاسم: {message.from_user.first_name}\n🆔 الأيدي: `{uid}`\n🏦 طريقة الدفع: {method_name}\n📦 الباقة المطلوبة: `{days} يوم`\n💵 القيمة: **{price}**",
                       reply_markup=markup)
    elif message.text:
        bot.send_message(uid, "⏳ **تم استلام بيانات التحويل بنجاح وجاري إرسالها للمطور (حافظ) للمراجعة والتفعيل...**")
        bot.send_message(ADMIN_ID,
                         f"💰 **طلب شحن يدوي (بيانات نصية):**\n📄 النص: {message.text}\n👤 الاسم: {message.from_user.first_name}\n🆔 الأيدي: `{uid}`\n🏦 طريقة الدفع: {method_name}\n📦 الباقة: `{days} يوم`\n💵 القيمة: **{price}**",
                         reply_markup=markup)
    else:
        bot.send_message(uid, "❌ خطأ: لم تقم بإرسال صورة سند أو نص واضح، يرجى إعادة المحاولة من قائمة التفعيل.")

# ================= نظام النجوم =================
@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    uid = message.chat.id
    payload = message.successful_payment.invoice_payload
    if payload == "stars_30":
        set_subscription(uid, days=30)
        bot.send_message(uid, "🎉 **تم شحن حسابك تلقائياً بـ 100 نجمة وتفعيل الباقة الشهرية (30 يوم) بنجاح!**")
    elif payload == "stars_90":
        set_subscription(uid, days=90)
        bot.send_message(uid, "🎉 **تم شحن حسابك تلقائياً بـ 300 نجمة وتفعيل الباقة الربع سنوية (90 يوم) بنجاح!**")
    elif payload == "stars_365":
        set_subscription(uid, days=365)
        bot.send_message(uid, "🎉 **تم شحن حسابك تلقائياً بـ 650 نجمة وتفعيل الباقة السنوية (365 يوم) بنجاح!**")

# ================= خدمة عرض الموقع =================
@app.route('/site/<int:user_id>/')
@app.route('/site/<int:user_id>/<path:filename>')
def serve_website(user_id, filename='index.html'):
    web_dir = os.path.join(BASE_DIR, str(user_id), "website")
    if not os.path.isdir(web_dir):
        abort(404)
    try:
        return send_from_directory(web_dir, filename)
    except:
        abort(404)

# ================= Webhook =================
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Invalid Request", 403

@app.route("/")
def home():
    return "🟢 Virtual Server Pro Is Running Successfully 24/7!"

# ================= نقطة البداية =================
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.set_webhook(url=f"{render_url}/{TOKEN}")
            logger.info(f"✅ Webhook set to {render_url}/{TOKEN}")
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
    else:
        logger.warning("⚠️ RENDER_EXTERNAL_URL not set")
    logger.info(f"📡 Server running on port {port}")
    serve(app, host='0.0.0.0', port=port)