#!/usr/bin/env python3
"""ส่งแจ้งเตือนตู้ที่ระดับความเสี่ยงเพิ่มขึ้นเป็น "สูง/วิกฤต" ทางอีเมลและ LINE

ค่าเริ่มต้นเป็น dry-run (พิมพ์ข้อความ ไม่ส่งจริง) ใช้ --send เพื่อส่งจริง
ตัวแปรสภาพแวดล้อม:
  อีเมล: SMTP_HOST, SMTP_PORT(587), SMTP_USER, SMTP_PASS, MAIL_FROM, MAIL_TO (คั่นด้วย ,)
  LINE : LINE_CHANNEL_TOKEN (Messaging API), LINE_TO (userId/groupId)
สถานะรอบก่อนเก็บที่ data/last_levels.json เพื่อแจ้งเฉพาะตู้ที่แย่ลง ไม่แจ้งซ้ำ
"""
import json, os, pathlib, smtplib, sys, urllib.request
from email.message import EmailMessage

ROOT = pathlib.Path(__file__).resolve().parent.parent
RANK = {"normal": 0, "watch": 1, "high": 2, "critical": 3}
TH = {"critical": "วิกฤต", "high": "สูง", "watch": "เฝ้าระวัง", "normal": "ปกติ"}

def build_message(items, generated):
    lines = [f"แจ้งเตือนตู้ ATM ออมสินที่เสี่ยงน้ำท่วม ({generated})", f"พบ {len(items)} ตู้ที่ระดับเพิ่มขึ้น", ""]
    for a in items[:25]:
        lines.append(f"[{TH[a['level']]}] {a['name']} ({a['id']}) - {a['reasons'][0]}")
    if len(items) > 25:
        lines.append(f"… และอีก {len(items) - 25} ตู้ (ดูในแอป)")
    return "\n".join(lines)

def send_email(text):
    to = [x.strip() for x in os.environ.get("MAIL_TO", "").split(",") if x.strip()]
    if not (os.environ.get("SMTP_HOST") and to):
        print("ข้ามอีเมล: ยังไม่ตั้งค่า SMTP_HOST / MAIL_TO"); return
    m = EmailMessage()
    m["Subject"] = "แจ้งเตือนตู้ ATM เสี่ยงน้ำท่วม"
    m["From"] = os.environ.get("MAIL_FROM", os.environ.get("SMTP_USER", ""))
    m["To"] = ", ".join(to)
    m.set_content(text)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", 587))) as s:
        s.starttls()
        if os.environ.get("SMTP_USER"):
            s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.send_message(m)
    print("ส่งอีเมลแล้ว")

def send_line(text):
    tok, to = os.environ.get("LINE_CHANNEL_TOKEN"), os.environ.get("LINE_TO")
    if not (tok and to):
        print("ข้ามLINE: ยังไม่ตั้งค่า LINE_CHANNEL_TOKEN / LINE_TO"); return
    body = json.dumps({"to": to, "messages": [{"type": "text", "text": text[:4900]}]}).encode()
    req = urllib.request.Request("https://api.line.me/v2/bot/message/push", body,
        {"Content-Type": "application/json", "Authorization": f"Bearer {tok}"})
    urllib.request.urlopen(req, timeout=30).read()
    print("ส่ง LINE แล้ว")

def main():
    send = "--send" in sys.argv
    d = json.loads((ROOT / "web/data/status.json").read_text("utf-8"))
    state_f = ROOT / "data/last_levels.json"
    prev = json.loads(state_f.read_text("utf-8")) if state_f.exists() else {}
    items = [a for a in d["atms"] if RANK[a["level"]] >= 2 and RANK[a["level"]] > RANK[prev.get(a["id"], "normal")]]
    items.sort(key=lambda a: -RANK[a["level"]])
    if not items:
        print("ไม่มีตู้ที่ระดับเสี่ยงเพิ่มขึ้น"); 
    else:
        text = build_message(items, d["generated_at"])
        if send:
            for fn in (send_email, send_line):
                try: fn(text)
                except Exception as e: print("ส่งไม่สำเร็จ:", fn.__name__, e, file=sys.stderr)
        else:
            print("--- DRY RUN (ใช้ --send เพื่อส่งจริง) ---\n" + text)
    if send or not state_f.exists():
        state_f.write_text(json.dumps({a["id"]: a["level"] for a in d["atms"]}), "utf-8")

if __name__ == "__main__":
    main()
