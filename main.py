import json
import time
import re
from pathlib import Path
import requests
from flask import Flask, request

# ================= CONFIG =================
BOT_TOKEN = "8357599246:AAF6ntHcf7HRBiXIz_ML2pUBcuxT7kE23UE"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

LIMIT_FILE = Path("limits.json")
MUTE_FILE = Path("mute.json")
SPAM_FILE = Path("spam.json")
ADMIN_FILE = Path("admin.json")
REPORT_FILE = Path("report.json")

# ================= UTILITIES =================
def api_request(method, params=None):
    if params is None:
        params = {}
    res = requests.post(f"{API_URL}{method}", data=params).json()
    if res.get("error_code") == 429:
        retry = res.get("parameters", {}).get("retry_after", 1)
        time.sleep(retry)
        return api_request(method, params)
    return res

def get_data(file_path):
    if not file_path.exists():
        file_path.write_text("{}")
    return json.loads(file_path.read_text())

def save_data(file_path, data):
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=4))

# ================= COOLDOWN =================
limits = get_data(LIMIT_FILE)
def check_cooldown(chat_id, user_id, command, cooldown=180):
    now = int(time.time())
    limits.setdefault(str(chat_id), {}).setdefault(str(user_id), {})
    last = limits[str(chat_id)][str(user_id)].get(command, 0)
    if now - last < cooldown:
        return cooldown - (now - last)
    limits[str(chat_id)][str(user_id)][command] = now
    save_data(LIMIT_FILE, limits)
    return 0

# ================= MUTE / UNMUTE =================
def mute_user(chat_id, user_id, minutes, name, username, reason=""):
    until = int(time.time()) + minutes*60
    api_request("restrictChatMember", {
        "chat_id": chat_id,
        "user_id": user_id,
        "permissions": json.dumps({
            "can_send_messages": False,
            "can_send_media_messages": False,
            "can_send_polls": False,
            "can_send_other_messages": False,
            "can_add_web_page_previews": False,
            "can_change_info": False,
            "can_invite_users": False,
            "can_pin_messages": False
        }),
        "until_date": until
    })
    mute = get_data(MUTE_FILE)
    mute.setdefault(str(chat_id), {})[str(user_id)] = {
        "name": name, "username": username, "until": until, "reason": reason
    }
    save_data(MUTE_FILE, mute)

def unmute_user(chat_id, user_id):
    api_request("restrictChatMember", {
        "chat_id": chat_id,
        "user_id": user_id,
        "permissions": json.dumps({
            "can_send_messages": True,
            "can_send_media_messages": True,
            "can_send_polls": True,
            "can_send_other_messages": True,
            "can_add_web_page_previews": True,
            "can_change_info": False,
            "can_invite_users": True,
            "can_pin_messages": False
        })
    })
    mute = get_data(MUTE_FILE)
    if str(chat_id) in mute and str(user_id) in mute[str(chat_id)]:
        del mute[str(chat_id)][str(user_id)]
    save_data(MUTE_FILE, mute)

# ================= SPAM DETECTION =================
def check_spam(chat_id, user_id, message_id, name, username):
    spam = get_data(SPAM_FILE)
    now = int(time.time())
    spam.setdefault(str(chat_id), {}).setdefault(str(user_id), [])
    spam[str(chat_id)][str(user_id)].append(now)
    spam[str(chat_id)][str(user_id)] = [t for t in spam[str(chat_id)][str(user_id)] if t > now-5]
    if len(spam[str(chat_id)][str(user_id)]) > 5:
        mute_user(chat_id, user_id, 5, name, username, "Spam")
        api_request("deleteMessage", {"chat_id": chat_id, "message_id": message_id})
        api_request("sendMessage", {
            "chat_id": chat_id,
            "parse_mode": "HTML",
            "text": f"🚨 <b>PHÁT HIỆN SPAM</b>\n━━━━━━━━━━━━━━\n🙍 Thành viên: <a href='tg://user?id={user_id}'>{name}</a>\n⏰ Thời gian cấm chat: <b>5 phút</b>\n📌 Lý do: <i>Spam tin nhắn</i>\n━━━━━━━━━━━━━━"
        })
        spam[str(chat_id)][str(user_id)] = []
    save_data(SPAM_FILE, spam)

# ================= PERMISSIONS =================
def has_permission(admin_bot, is_admin_group):
    return admin_bot or is_admin_group

# ================= FLASK BOT =================
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json
    message = update.get("message") or update.get("edited_message")
    if not message:
        return "ok"

    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    name = message["from"].get("first_name", "")
    username = message["from"].get("username", "")
    text = (message.get("text") or "").strip()
    reply = message.get("reply_to_message")

    check_spam(chat_id, user_id, message["message_id"], name, username)

    admins_bot = get_data(ADMIN_FILE)
    admins_response = api_request("getChatAdministrators", {"chat_id": chat_id})
    group_admins = admins_response.get("result", [])
    is_admin = any(a.get("user", {}).get("id") == user_id for a in group_admins)
    is_admin_bot = str(chat_id) in admins_bot and str(user_id) in admins_bot[str(chat_id)]

    # ================= COMMANDS =================
    # vipham
    m = re.match(r"^vipham(?:\s+(\d+))?(?:\s+(.+))?$", text, re.I)
    if m and reply:
        if not has_permission(is_admin_bot, is_admin):
            return "ok"
        minutes = int(m.group(1)) if m.group(1) else 5
        reason = m.group(2).strip() if m.group(2) else "Không có"
        target = reply["from"]
        mute_user(chat_id, target["id"], minutes, target.get("first_name",""), target.get("username",""), reason)
        msg = f"""🚫 <b>THÀNH VIÊN VI PHẠM</b>
Tự Nhìn Lại Hành Vi Của Mình Và Kiểm Điểm Lại Đi
━━━━━━━━━━━━━━
📛 Nhóm: <b>{message['chat'].get('title','')}</b>
🙍 Thành viên: <a href='tg://user?id={target['id']}'>{target.get('first_name','')}</a>
⏰ Thời gian cấm chat: <b>{minutes} phút</b>
📌 Lý do: <i>{reason}</i>
👮 Người báo cáo: <a href='tg://user?id={user_id}'>{name}</a>
━━━━━━━━━━━━━━"""
        api_request("sendMessage", {"chat_id": chat_id, "parse_mode": "HTML", "text": msg})
        return "ok"

    # mochanchat
    m = re.match(r"^mochanchat(?:\s+@?(\S+))?", text, re.I)
    if m:
        if not has_permission(is_admin_bot, is_admin):
            return "ok"
        mute = get_data(MUTE_FILE)
        target = None
        if reply:
            target = reply["from"]
        elif m.group(1) and str(chat_id) in mute:
            for uid, info in mute[str(chat_id)].items():
                if info.get("username","").lower() == m.group(1).lower():
                    target = {"id": int(uid), "first_name": info["name"]}
                    break
        if target:
            unmute_user(chat_id, target["id"])
            api_request("sendMessage", {"chat_id": chat_id, "parse_mode":"HTML", "text":
                f"🔓 <b>ĐÃ MỞ CHẶN CHAT</b>\n━━━━━━━━━━━━━━\n🙍 Thành viên: <a href='tg://user?id={target['id']}'>{target['first_name']}</a>\n👮 Người thực hiện: <a href='tg://user?id={user_id}'>{name}</a>\n━━━━━━━━━━━━━━"})
        else:
            api_request("sendMessage", {"chat_id": chat_id, "parse_mode":"HTML", "text":"⚠️ Không tìm thấy thành viên để mở chặn!"})
        return "ok"

    # addadmin
    if text.lower() == "addadmin":
        if not is_admin:
            api_request("sendMessage", {"chat_id": chat_id, "parse_mode":"HTML", "text":"⚠️ Bạn không có quyền thêm admin!"})
            return "ok"
        if not reply:
            api_request("sendMessage", {"chat_id": chat_id, "parse_mode":"HTML", "text":"⚠️ Vui lòng reply tin nhắn muốn thêm admin!"})
            return "ok"
        target_id = reply["from"]["id"]
        uname = (reply["from"].get("username") or reply["from"].get("first_name")).lower()
        admins_bot.setdefault(str(chat_id), {})[str(target_id)] = {"username": uname}
        save_data(ADMIN_FILE, admins_bot)
        api_request("sendMessage", {"chat_id": chat_id, "parse_mode":"HTML", "text":f"✅ Đã thêm <b>@{uname}</b> làm admin bot!"})
        return "ok"

    # removeadmin
    if text.lower() == "removeadmin":
        if not is_admin:
            api_request("sendMessage", {"chat_id": chat_id, "parse_mode":"HTML", "text":"⚠️ Bạn không có quyền xóa admin!"})
            return "ok"
        if not reply:
            api_request("sendMessage", {"chat_id": chat_id, "parse_mode":"HTML", "text":"⚠️ Vui lòng reply tin nhắn muốn xóa admin!"})
            return "ok"
        target_id = reply["from"]["id"]
        uname = (reply["from"].get("username") or reply["from"].get("first_name")).lower()
        if str(chat_id) in admins_bot and str(target_id) in admins_bot[str(chat_id)]:
            del admins_bot[str(chat_id)][str(target_id)]
            save_data(ADMIN_FILE, admins_bot)
            api_request("sendMessage", {"chat_id": chat_id, "parse_mode":"HTML", "text":f"✅ Đã xóa <b>@{uname}</b> khỏi admin bot!"})
        else:
            api_request("sendMessage", {"chat_id": chat_id, "parse_mode":"HTML", "text":"⚠️ Người dùng này không phải admin bot!"})
        return "ok"

    # baocao
    if text.lower() == "baocao" and reply:
        target = reply["from"]
        reports = get_data(REPORT_FILE)
        reports.setdefault(str(chat_id), {}).setdefault(str(target["id"]), [])
        if user_id not in reports[str(chat_id)][str(target["id"])]:
            reports[str(chat_id)][str(target["id"])].append(user_id)
        count = len(reports[str(chat_id)][str(target["id"])])
        need = 3
        if count >= need:
            mute_user(chat_id, target["id"], 10, target.get("first_name",""), target.get("username",""), "Bị Báo Cáo")
            del reports[str(chat_id)][str(target["id"])]
            api_request("sendMessage", {"chat_id": chat_id, "parse_mode":"HTML", "text":
                f"🚫 <b>THÀNH VIÊN BỊ CẤM CHAT</b>\n━━━━━━━━━━━━━━\n🙍 <a href='tg://user?id={target['id']}'>{target.get('first_name','')}</a>\n📌 Lý do: <i>Bị Báo Cáo</i>\n⏰ Thời gian cấm chat: <b>10 phút</b>\n━━━━━━━━━━━━━━"})
        else:
            api_request("sendMessage", {"chat_id": chat_id, "parse_mode":"HTML", "text":
                f"⚠️ <b>Report đã được ghi nhận</b>\n━━━━━━━━━━━━━━\n🙍 Thành viên: <a href='tg://user?id={target['id']}'>{target.get('first_name','')}</a>\n📊 Số lần báo cáo: {count}/{need}\n━━━━━━━━━━━━━━"})
        save_data(REPORT_FILE, reports)
        return "ok"

    # alladmin
    if text.lower() == "alladmin":
        admins = api_request("getChatAdministrators", {"chat_id": chat_id})
        msg = "📋 <b>DANH SÁCH QUẢN TRỊ VIÊN</b>\n\n"
        for a in admins.get("result", []):
            user = a.get("user", {})
            role = "👑" if a.get("status") == "creator" else "🛡️"
            uname = user.get("username","")
            msg += f"{role} {user.get('first_name','')} " + (f"(@{uname})" if uname else "") + "\n\n"
        api_request("sendMessage", {"chat_id": chat_id, "parse_mode":"HTML", "text":msg})
        return "ok"

    return "ok"

if __name__ == "__main__":
    app.run(port=5000)
