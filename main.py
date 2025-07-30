import telebot
import requests
import time
from flask import Flask
import threading

# === TOKEN BOT TELEGRAM ===
TELEGRAM_BOT_TOKEN = "8253965521:AAElcdJVeJTHa-CEAI8BsAdOV7Az6Unftkg"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# === DANH SÁCH CỔNG PROXY ===
PROXY_SOURCES = {
    "1": "0q159x3l1vimi2inghp8245ea5z231lis1mp4d21",
    "2": "7tm8h1nhocal2d6kaxf87003y1xef72ankxyzc0f",
    "3": "uwsgsbg2z5rl5xasls6qy8rggo9rs8zcswm10lua",
}

# === LẤY DANH SÁCH PROXY ===
def get_proxies(api_key):
    try:
        headers = {"Authorization": f"Token {api_key}"}
        url = "https://proxy.webshare.io/api/v2/proxy/list/?mode=direct"
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        return res.json().get("results", [])
    except:
        return []

# === LẤY QUỐC GIA IP ===
def get_country(ip):
    try:
        res = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        data = res.json()
        country = data.get("country", "❓")
        region = data.get("region", "")
        return f"🌍 <b>{country}</b> - {region}"
    except:
        return "🌍 <i>Không xác định</i>"

# === KIỂM TRA TỐC ĐỘ PROXY ===
def test_proxy_speed(proxy):
    try:
        proxies = {
            "http": f"http://{proxy['username']}:{proxy['password']}@{proxy['proxy_address']}:{proxy['port']}",
            "https": f"http://{proxy['username']}:{proxy['password']}@{proxy['proxy_address']}:{proxy['port']}"
        }
        start = time.time()
        res = requests.get("https://www.google.com", proxies=proxies, timeout=5)
        if res.status_code == 200:
            speed = round((time.time() - start) * 1000)
            return f"⚡ <b>Tốc độ:</b> <code>{speed}ms</code>"
    except:
        return "⚠️ <i>Timeout hoặc lỗi</i>"

# === /start ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    welcome = (
        "🎉 <b>CHÀO MỪNG ĐẾN KING TOOL PROXY</b> 🎉\n\n"
        "🤖 <b>Bot hỗ trợ lấy proxy từ nhiều nguồn chất lượng!</b>\n\n"
        "📌 <b>Lệnh sử dụng:</b>\n"
        "🔹 <code>/get_proxy số_lượng cổng</code> – Lấy proxy\n"
        "🔹 <code>/ds_proxy</code> – Danh sách cổng hoạt động\n"
        "🔹 <code>/ping</code> – Kiểm tra bot\n\n"
        "📥 Ví dụ: <code>/get_proxy 5 1</code>\n"
        "💡 Tối đa <b>10 proxy</b> mỗi lần yêu cầu."
    )
    bot.reply_to(message, welcome)

# === /get_proxy ===
@bot.message_handler(commands=['get_proxy'])
def handle_getproxy(message):
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "⚠️ Nhập đúng cú pháp: <code>/get_proxy số_lượng cổng</code>")
        return

    try:
        amount = min(int(args[1]), 10)
        port = args[2]
        api_key = PROXY_SOURCES.get(port)
        if not api_key:
            bot.reply_to(message, "❌ Cổng không tồn tại. Dùng <code>/ds_proxy</code> để kiểm tra.")
            return

        bot.reply_to(message, f"⏳ <b>Đang lấy {amount} proxy từ cổng {port}...</b>")

        proxies = get_proxies(api_key)
        if not proxies:
            bot.send_message(message.chat.id, "⚠️ Không tìm thấy proxy từ API hoặc lỗi kết nối.")
            return

        for idx, proxy in enumerate(proxies[:amount], 1):
            ip = proxy["proxy_address"]
            country = get_country(ip)
            speed = test_proxy_speed(proxy)
            msg = (
                f"<b>🎯 PROXY #{idx}</b>\n"
                f"<pre>━━━━━━━━━━━━━━━━━━━━━━</pre>\n"
                f"🔐 <b>Tài khoản:</b> <code>{proxy['username']}</code>\n"
                f"🔑 <b>Mật khẩu:</b> <code>{proxy['password']}</code>\n"
                f"🌐 <b>IP:</b> <code>{ip}</code>\n"
                f"📦 <b>Cổng:</b> <code>{proxy['port']}</code>\n"
                f"{country}\n"
                f"{speed}\n"
                f"<pre>━━━━━━━━━━━━━━━━━━━━━━</pre>"
            )
            bot.send_message(message.chat.id, msg)
            time.sleep(1.5)

    except ValueError:
        bot.reply_to(message, "❌ Số lượng phải là số nguyên.")

# === /ds_proxy ===
@bot.message_handler(commands=['ds_proxy'])
def handle_ds_proxy(message):
    msg = "<b>📡 DANH SÁCH TRẠNG THÁI CỔNG:</b>\n\n"
    for port, api_key in PROXY_SOURCES.items():
        proxies = get_proxies(api_key)
        status = "✅ <b>Hoạt động</b>" if proxies else "❌ <b>Lỗi hoặc không phản hồi</b>"
        msg += f"🔌 <b>Cổng {port}:</b> {status}\n"
    bot.reply_to(message, msg)

# === /ping ===
@bot.message_handler(commands=['ping'])
def handle_ping(message):
    bot.reply_to(message, "✅ Bot đang hoạt động tốt!")

# === FLASK UPTIMEROBOT ===
app = Flask('')

@app.route('/')
def home():
    return "Bot Đang Hoạt Động!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# === KHỞI ĐỘNG BOT ===
keep_alive()
bot.polling(none_stop=True)
