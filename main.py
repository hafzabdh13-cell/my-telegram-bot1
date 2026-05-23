import os
import sys
import subprocess
import importlib

# ================= التثبيت التلقائي للمكتبات المفقودة للنظام =================
def install_requirements():
    required = ["pyTelegramBotAPI", "Flask", "waitress"]
    for lib in required:
        try:
            importlib.import_module(lib.replace("pyTelegramBotAPI", "telebot"))
        except ImportError:
            print(f"🔄 جاري تثبيت المكتبة: {lib}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

install_requirements()

import telebot
import sqlite3
import ast
from datetime import datetime, timedelta
from flask import Flask, request
from telebot import types
from waitress import serve

# ================= دالة تثبيت مكتبات بوتات المستخدمين =================
def install_user_requirements(bot_dir):
    req_file = os.path.join(bot_dir, "requirements.txt")
    if os.path.exists(req_file):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
            return True, "✅ تم تثبيت مكتبات البوت من requirements.txt"
        except Exception as e:
            return False, f"❌ فشل تثبيت المكتبات: {str(e)}"
    return True, "ℹ️ لا يوجد ملف requirements.txt"

# ================= FLASK SERVER FOR 24/7 ACTIVE =================
app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "8790387996:AAFB6u4jHWrtsGPnECIxLWxiyJm8rgrV5Vs")

@app.route("/")
def home():
    return "🟢 Virtual Server Pro Is Running Successfully 24/7!"

@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        return "Invalid Request", 403

# البيانات الخاصة بك يا حافظ
ADMIN_ID = 7484089854
OWNER_USER = "@HAFZAbdh"  
OWNER_FULL_NAME = "حافظ عبده احمد عبدالرحمن احمد"
MY_JAIB_ACCOUNT = "784714890" 

bot = telebot.TeleBot(TOKEN, threaded=False)
BASE_DIR = "hosted_bots"
os.makedirs(BASE_DIR, exist_ok=True)
active_processes = {}

# ================= DATABASE SYSTEM =================
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

init_db()

# ================= CORE FUNCTIONS =================
def check_code_syntax(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        ast.parse(code)
        return True, "✅ الكود سليم ولا يحتوي على أخطاء برمجية."
    except SyntaxError as e:
        return False, f"❌ خطأ في الكود (Syntax Error) في السطر {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"⚠️ خطأ غير متوقع: {str(e)}"

def create_user_and_check_free(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT free_used FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        expire_time = datetime.now() + timedelta(days=1)
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

# ================= SMART KEYBOARDS =================
def start_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🎛️ فتح لوحة التحكم السحابية"))
    markup.add(types.KeyboardButton("💳 تفعيل حسابي وشحن الرصيد"))
    markup.add(types.KeyboardButton("🎁 تفعيل الخدمة المجانية اليومية"))
    return markup

def main_menu(user_id):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("📁 إدارة الملفات", callback_data="choose_files"),
        types.InlineKeyboardButton("📤 رفع كود جديد (bot.py)", callback_data="choose_upload"),
        types.InlineKeyboardButton("🚀 تشغيل سيرفر", callback_data="choose_run"),
        types.InlineKeyboardButton("🛑 إيقاف سيرفر", callback_data="choose_stop"),
        types.InlineKeyboardButton("🛡️ فحص الحماية والاستقرار", callback_data="protect"),
        types.InlineKeyboardButton("📊 حالة الخادم العام", callback_data="status")
    )
    owner_link = OWNER_USER.replace("@", "")
    m.add(types.InlineKeyboardButton("👑 الدعم الفني للمالك", url=f"https://t.me/{owner_link}"))
    return m

def bot_selector_menu(action):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("🤖 سيرفر 1", callback_data=f"{action}_1"),
        types.InlineKeyboardButton("🤖 سيرفر 2", callback_data=f"{action}_2"),
        types.InlineKeyboardButton("🤖 سيرفر 3", callback_data=f"{action}_3"),
        types.InlineKeyboardButton("🤖 سيرفر 4", callback_data=f"{action}_4")
    )
    m.add(types.InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back"))
    return m

def price_plans_keyboard():
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton("⭐ شحن تلقائي فوراً عبر نجوم تلجرام", callback_data="stars_shop_menu"))
    m.add(types.InlineKeyboardButton("📱 دفع يدوي (محفظة جيب باليمني)", callback_data="manual_menu_jaib"))
    m.add(types.InlineKeyboardButton("💸 حوالة يدوية (الامتياز / الكريمي)", callback_data="manual_menu_bank"))
    return m

def stars_packages_keyboard():
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        types.InlineKeyboardButton("✨ باقة شهر (30 يوم) ➔ 100 نجمة", callback_data="buy_stars_30"),
        types.InlineKeyboardButton("🔥 باقة ربع سنة (90 يوم) ➔ 300 نجمة", callback_data="buy_stars_90"),
        types.InlineKeyboardButton("👑 باقة سنة كاملة (365 يوم) ➔ 650 نجمة", callback_data="buy_stars_365")
    )
    m.add(types.InlineKeyboardButton("🔙 العودة لوسائل الدفع", callback_data="back_to_shop"))
    return m

def manual_packages_keyboard(method):
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        types.InlineKeyboardButton("🗓️ باقة أسبوع (7 أيام) ➔ 2$", callback_data=f"ask_send_{method}_7_2$"),
        types.InlineKeyboardButton("✨ باقة شهر (30 يوم) ➔ 4$", callback_data=f"ask_send_{method}_30_4$"),
        types.InlineKeyboardButton("🔥 باقة ربع سنة (90 يوم) ➔ 6$", callback_data=f"ask_send_{method}_90_6$"),
        types.InlineKeyboardButton("👑 باقة سنة كاملة (365 يوم) ➔ 10$", callback_data=f"ask_send_{method}_365_10$")
    )
    m.add(types.InlineKeyboardButton("🔙 العودة لوسائل الدفع", callback_data="back_to_shop"))
    return m

def admin_approval_keyboard(target_id, package_days, price):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("✅ قبول وتفعيل الاشتراك", callback_data=f"admin_accept_{package_days}_{target_id}"),
        types.InlineKeyboardButton("❌ رفض الطلب وإلغاء", callback_data=f"admin_reject_{target_id}")
    )
    return m

# ================= HANDLERS =================
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
⚙️ **أقوى منصة سحابية لتشغيل حتى 4 بوتات تلجرام معاً 24 ساعة دون انقطاع.**

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
    bot.send_message(message.chat.id, "💎 **لوحة التحكم بالخدمات السحابية المتعددة (الحد الأقصى: 4 بوتات):**", reply_markup=main_menu(message.chat.id), parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "💳 تفعيل حسابي وشحن الرصيد")
def open_shop(message):
    bot.send_message(message.chat.id, "⚙️ **يرجى اختيار وسيلة الدفع والشحن المناسبة لك:**", reply_markup=price_plans_keyboard())

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
        set_subscription(uid, days=1)
        cursor.execute("UPDATE users SET last_free_time=? WHERE user_id=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
        conn.commit()
        bot.send_message(uid, "🎁 **تهانينا! تم تفعيل السيرفرات بالخطة المجانية الصالحة لمدة 24 ساعة كاملة بنجاح!**", parse_mode="Markdown")
    else:
        bot.send_message(uid, "⚠️ **عذراً، باقتك المجانية لليوم نشطة بالفعل أو لم تمر 24 ساعة على تفعيلك السابق!**")
    conn.close()

# ================= CALLBACK QUERY HANDLER =================
@bot.callback_query_handler(func=lambda call: True)
def handle_call(call):
    uid = call.message.chat.id
    mid = call.message.message_id
    
    if call.data == "stars_shop_menu":
        bot.edit_message_text("⭐ **متجر شحن نجوم تلجرام التلقائي الفوري:**\nاختر الباقة المراد الاشتراك بها وسيتم تفعيلك تلقائياً:", uid, mid, reply_markup=stars_packages_keyboard())
        bot.answer_callback_query(call.id)

    elif call.data == "buy_stars_30":
        bot.send_invoice(uid, "اشتراك برو (شهري)", "تفعيل 4 بوتات لمدة 30 يوم تلقائياً.", "stars_30", "", "XTR", [types.LabeledPrice("باقة شهر", 100)])
        bot.answer_callback_query(call.id)

    elif call.data == "buy_stars_90":
        bot.send_invoice(uid, "اشتراك برو (ربع سنوي)", "تفعيل 4 بوتات لمدة 90 يوم تلقائياً.", "stars_90", "", "XTR", [types.LabeledPrice("باقة ربع سنة", 300)])
        bot.answer_callback_query(call.id)

    elif call.data == "buy_stars_365":
        bot.send_invoice(uid, "اشتراك برو (سنوي)", "تفعيل 4 بوتات لمدة 365 يوم تلقائياً.", "stars_365", "", "XTR", [types.LabeledPrice("باقة سنة", 650)])
        bot.answer_callback_query(call.id)
        
    elif call.data == "manual_menu_jaib":
        bot.edit_message_text("📱 **دفع يدوي عبر محفظة جيب:**\nاختر الباقة المراد الاشتراك بها لمعاينة السعر بالدولار وما يعادله باليمني:", uid, mid, reply_markup=manual_packages_keyboard("jaib"))
        bot.answer_callback_query(call.id)
        
    elif call.data == "manual_menu_bank":
        bot.edit_message_text("💸 **دفع يدوي عبر حوالة (الامتياز / الكريمي):**\nاختر الباقة المراد الاشتراك بها لمعاينة السعر وبيانات المستلم:", uid, mid, reply_markup=manual_packages_keyboard("bank"))
        bot.answer_callback_query(call.id)

    elif call.data == "back_to_shop":
        bot.edit_message_text("⚙️ **يرجى اختيار وسيلة الدفع والشحن المناسبة لك:**", uid, mid, reply_markup=price_plans_keyboard())
        bot.answer_callback_query(call.id)

    elif call.data.startswith("ask_send_"):
        parts = call.data.split("_")
        method, days, price = parts[2], int(parts[3]), parts[4]
        
        if method == "jaib":
            msg_text = f"📱 **بوابة محفظة جيب اليدوية:**\n━━━━━━━━━━━━━━━━━━━━\nرقم المحفظة: `{MY_JAIB_ACCOUNT}`\nالاسم المعتمد: **{OWNER_FULL_NAME}**\n📦 الباقة المختارة: `{days} يوم`\n💰 القيمة المطلوبة: **{price}** (أو ما يعادلها بالريال اليمني حسب الصرف)\n\n👇 **قم بالتحويل الآن ثم أرسل صورة السند هنا مباشرة لمراجعة الدفع:**"
        else:
            msg_text = f"💸 **بوابة الحوالات اليدوية (الامتياز / الكريمي):**\n━━━━━━━━━━━━━━━━━━━━\nالاسم الكامل للمستلم: `{OWNER_FULL_NAME}`\n📦 الباقة المختارة: `{days} يوم`\n💰 القيمة المطلوبة: **{price}**\n\n👇 **بعد إرسال الحوالة، أرسل صورة السند أو كود الحوالة هنا ليتم تفعيل حسابك:**"
            
        msg = bot.send_message(uid, msg_text, parse_mode="Markdown")
        bot.register_next_step_handler(msg, receive_manual_invoice, days, price)
        bot.answer_callback_query(call.id)

    elif call.data.startswith("admin_accept_"):
        parts = call.data.split("_")
        days, target_user = int(parts[2]), int(parts[3])
        set_subscription(target_user, days=days)
        bot.edit_message_caption(f"✅ **تم تفعيل الاشتراك باقة ({days} يوم) للمستخدم بنجاح.**", uid, mid)
        bot.send_message(target_user, f"🎉 **أهلاً بك! تم مراجعة السند وقبوله من قِبل المطور حافظ، وتم تفعيل اشتراكك السحابي لمدة {days} يوماً بنجاح!**")
        
    elif call.data.startswith("admin_reject_"):
        target_user = int(call.data.split("_")[2])
        bot.edit_message_caption("❌ **تم رفض السند وإلغاء الطلب.**", uid, mid)
        bot.send_message(target_user, "❌ **عذراً، تم مراجعة السند المرسل من قبلك وتبين أنه غير صالح أو مرفوض من قبل الإدارة.**")

    elif call.data.startswith(("choose_", "run_", "stop_", "upload_", "files_")) or call.data == "protect":
        if not is_sub_active(uid):
            bot.answer_callback_query(call.id, "⚠️ عذراً عزيزي، اشتراكك منتهي أو غير مفعّل! اشحن عبر النجوم أو أرسل سند التحويل اليدوي.", show_alert=True)
            return

    if call.data == "choose_run":
        bot.edit_message_text("🚀 **اختر رقم السيرفر السحابي المراد تشغيله:**", uid, mid, reply_markup=bot_selector_menu("run"))
    elif call.data == "choose_stop":
        bot.edit_message_text("🛑 **اختر رقم السيرفر السحابي المراد إيقافه:**", uid, mid, reply_markup=bot_selector_menu("stop"))
    elif call.data == "choose_upload":
        bot.edit_message_text("📤 **اختر السيرفر السحابي المراد رفع كودك إليه:**", uid, mid, reply_markup=bot_selector_menu("upload"))
    elif call.data == "choose_files":
        bot.edit_message_text("📁 **اختر السيرفر لمعاينة وحجم الملف المرفوع به:**", uid, mid, reply_markup=bot_selector_menu("files"))

    elif call.data.startswith("run_"):
        bot_num = call.data.split("_")[1]
        process_key = f"{uid}_{bot_num}"
        bot_dir = f"{BASE_DIR}/{uid}/bot{bot_num}"
        path = f"{bot_dir}/bot.py"
        
        if not os.path.exists(path):
            bot.answer_callback_query(call.id, f"❌ لم تقم برفع ملف الكود للسيرفر رقم {bot_num}!", show_alert=True)
            return
        if process_key in active_processes and active_processes[process_key].poll() is None:
            bot.answer_callback_query(call.id, f"⚠️ السيرفر {bot_num} يعمل بالفعل!", show_alert=True)
            return

        # فحص وتثبيت المكتبات التابع للبوت قبل التشغيل
        success, msg = install_user_requirements(bot_dir)
        if not success:
            bot.answer_callback_query(call.id, msg, show_alert=True)
            return

        try:
            optimized_env = os.environ.copy()
            optimized_env["PYTHONUNBUFFERED"] = "1"
            optimized_env["PYTHONDONTWRITEBYTECODE"] = "1"
            
            proc = subprocess.Popen(
                [sys.executable, "bot.py"],
                cwd=bot_dir,
                env=optimized_env
            )
            active_processes[process_key] = proc  
            bot.edit_message_text(f"🟢 **تم تشغيل السيرفر الفرعي رقم ({bot_num}) بنجاح!**", uid, mid, reply_markup=main_menu(uid), parse_mode="Markdown")
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ فشل تشغيل البوت: {str(e)}", show_alert=True)

    elif call.data.startswith("stop_"):
        bot_num = call.data.split("_")[1]
        process_key = f"{uid}_{bot_num}"
        if process_key in active_processes and active_processes[process_key].poll() is None:
            try:
                active_processes[process_key].terminate()  
                active_processes[process_key].wait(timeout=2)
            except:
                try:
                    active_processes[process_key].kill()
                except:
                    pass
            if process_key in active_processes:
                del active_processes[process_key]
            bot.edit_message_text(f"🛑 **تم إيقاف السيرفر رقم ({bot_num}) بنجاح.**", uid, mid, reply_markup=main_menu(uid), parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, f"⚠️ السيرفر رقم {bot_num} متوقف حالياً!", show_alert=True)

    elif call.data.startswith("upload_"):
        bot_num = call.data.split("_")[1]
        msg = bot.send_message(uid, f"📤 **أرسل الآن ملفك البرمجي (bot.py) أو ملف المكتبات (requirements.txt) للسيرفر رقم ({bot_num}).**")
        bot.register_next_step_handler(msg, save_bot_file, bot_num)

    elif call.data.startswith("files_"):
        bot_num = call.data.split("_")[1]
        path = f"{BASE_DIR}/{uid}/bot{bot_num}/bot.py"
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024
            bot.send_message(uid, f"📁 **ملفاتك على سيرفر ({bot_num}):**\n📄 الاسم: `bot.py`\n⚖️ الحجم: `{size:.2f} KB`", parse_mode="Markdown")
        else:
            bot.send_message(uid, f"📁 المجلد السحابي للسيرفر رقم ({bot_num}) فارغ.", parse_mode="Markdown")

    elif call.data == "back":
        bot.edit_message_text("🏠 **العودة إلى لوحة التحكم الرئيسية:**", uid, mid, reply_markup=main_menu(uid), parse_mode="Markdown")

# ================= TELEGRAM STARS AUTO-ACTIVATION SYSTEM =================
@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    uid = message.chat.id
    payload = message.successful_payment.invoice_payload
    
    if payload == "stars_30":
        set_subscription(uid, days=30)
        bot.send_message(uid, "🎉 **تم شحن حسابك تلقائياً بـ 100 نجمة وتفعيل الباقة الشهرية (30 يوم) بنجاح!**", parse_mode="Markdown")
    elif payload == "stars_90":
        set_subscription(uid, days=90)
        bot.send_message(uid, "🎉 **تم شحن حسابك تلقائياً بـ 300 نجمة وتفعيل الباقة الربع سنوية (90 يوم) بنجاح!**", parse_mode="Markdown")
    elif payload == "stars_365":
        set_subscription(uid, days=365)
        bot.send_message(uid, "🎉 **تم شحن حسابك تلقائياً بـ 650 نجمة وتفعيل الباقة السنوية (365 يوم) بنجاح!**", parse_mode="Markdown")

# ================= HANDLERS FOR MANUAL INVOICES =================
def receive_manual_invoice(message, package_days, price):
    uid = message.chat.id
    markup = admin_approval_keyboard(uid, package_days, price)
    
    if message.photo:
        bot.send_message(uid, "⏳ **تم استلام صورة السند بنجاح وجاري إرسالها للمطور (حافظ) للمراجعة والتفعيل...**")
        bot.send_photo(
            chat_id=ADMIN_ID, 
            photo=message.photo[-1].file_id, 
            caption=f"💰 **طلب شحن يدوي جديد:**\n👤 الاسم: {message.from_user.first_name}\n🆔 الأيدي: `{uid}`\n📦 الباقة المطلوبة: `{package_days} يوم`\n💵 القيمة المراد استلامها: **{price}**", 
            reply_markup=markup
        )
    elif message.text:
        bot.send_message(uid, "⏳ **تم استلام بيانات التحويل بنجاح وجاري إرسالها للمطور (حافظ) للمراجعة والتفعيل...**")
        bot.send_message(
            chat_id=ADMIN_ID, 
            text=f"💰 **طلب شحن يدوي (بيانات نصية):**\n📄 النص المرفق: {message.text}\n👤 الاسم: {message.from_user.first_name}\n🆔 الأيدي: `{uid}`\n📦 الباقة المطلوبة: `{package_days} يوم`\n💵 القيمة المراد استلامها: **{price}**", 
            reply_markup=markup
        )
    else:
        bot.send_message(uid, "❌ خطأ: لم تقم بإرسال صورة سند أو نص واضح، يرجى إعادة المحاولة من قائمة التفعيل.")

def save_bot_file(message, bot_num):
    uid = message.chat.id
    if not message.document:
        bot.send_message(uid, "❌ خطأ: يرجى إرسال ملف بصيغة مستند (Document).")
        return
    try:
        user_bot_path = f"{BASE_DIR}/{uid}/bot{bot_num}"
        os.makedirs(user_bot_path, exist_ok=True)
        file_path = f"{user_bot_path}/{message.document.file_name}"
        
        finfo = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(finfo.file_path) 
        with open(file_path, "wb") as f:
            f.write(downloaded)
        
        if message.document.file_name == "bot.py":
            is_ok, msg = check_code_syntax(file_path)
            if is_ok:
                bot.send_message(uid, f"✅ **تم حفظ وتثبيت كودك بنجاح في السيرفر {bot_num} باسم `bot.py`!**\n{msg}", parse_mode="Markdown")
            else:
                bot.send_message(uid, f"⚠️ **تنبيه برمجي:**\n{msg}\nيرجى إصلاح الكود وإعادة رفعه.")
        else:
            bot.send_message(uid, f"✅ تم حفظ الملف: `{message.document.file_name}` بنجاح.", parse_mode="Markdown")
            
    except Exception as e:
        bot.send_message(uid, f"❌ حدث خطأ أثناء حفظ الملف: {str(e)}")

@app.route("/set_webhook", methods=["GET", "POST"])
def setup_webhook_route():
    bot.remove_webhook()
    render_external_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_external_url:
        return "⚠️ خطأ: تأكد من تشغيل المشروع كـ Web Service in Render لتفعيل الرابط التلقائي.", 400
    success = bot.set_webhook(url=f"{render_external_url}/{TOKEN}")
    if success:
        return f"🟢 تم ربط البوت بالسيرفر بنجاح عبر الـ Webhook الخارجي!<br>الرابط: {render_external_url}", 200
    else:
        return "❌ فشل ربط البوت، تأكد من الـ Token الخاص بك.", 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    print(f"📡 جاري تشغيل المنصة عبر Waitress على المنفذ: {port}")
    serve(app, host='0.0.0.0', port=port)
