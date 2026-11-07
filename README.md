# ATM Flood – เฝ้าระวังตู้ ATM ออมสินในพื้นที่น้ำท่วม

เว็บแอป (PWA) แสดงตู้ ATM ที่ได้รับผลกระทบจากน้ำท่วม เรียงตามความรุนแรง พร้อมแผนที่ รายละเอียด และปุ่มสั่งการ

## รัน
```
python3 scripts/make_mock_atms.py   # สร้างตู้จำลอง (ข้ามได้ถ้ามีแล้ว)
python3 scripts/build_risk.py       # ดึงฝน/น้ำจริง + คำนวณความเสี่ยง -> web/data/status.json
python3 scripts/notify.py           # ดูข้อความแจ้งเตือน (dry-run); ใช้ --send เพื่อส่งจริง
cd web && python3 -m http.server 8000
```
## ข้อมูล
| ส่วน | สถานะ |
|---|---|
| ฝน 3 วัน, ปริมาณน้ำแม่น้ำ | จริง – Open-Meteo / GloFAS |
| ตำแหน่งตู้ ATM | **จำลอง** – แทนที่ `data/atms_mock.json` ด้วยไฟล์จริง (id, name, province, region, lat, lon) |
| พื้นที่น้ำท่วม | **จำลอง** – แทนที่ `data/flood_zones_mock.json` ด้วยข้อมูล GISTDA (ตอนนี้รองรับวงกลม lat/lon/radius_km) |
## เกณฑ์ระดับ
วิกฤต: อยู่ในพื้นที่น้ำท่วม · สูง: ห่าง ≤1 กม., น้ำแม่น้ำ ≥3 เท่า หรือฝน 3 วัน ≥120 มม. · เฝ้าระวัง: น้ำ ≥1.8 เท่า หรือฝน ≥60 มม.
## แจ้งเตือน
ตั้ง env ตามหัวไฟล์ `scripts/notify.py` (อีเมล SMTP, LINE Messaging API) หรือใส่เป็น GitHub Secrets ให้ `.github/workflows/refresh.yml` รันทุก 3 ชม.
