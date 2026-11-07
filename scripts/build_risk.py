#!/usr/bin/env python3
"""คำนวณระดับความเสี่ยงน้ำท่วมของตู้ ATM แล้วเขียน web/data/status.json

แหล่งข้อมูลจริง (Open-Meteo, ฟรี ไม่ต้องใช้ key):
  - พยากรณ์ฝน 3 วัน            https://api.open-meteo.com/v1/forecast
  - ปริมาณน้ำในแม่น้ำ (GloFAS)  https://flood-api.open-meteo.com/v1/flood
ขอบเขตพื้นที่น้ำท่วม: ตอนนี้ใช้ data/flood_zones_mock.json (จำลอง)
เมื่อได้ข้อมูล GISTDA จริง ให้แทนไฟล์นี้ด้วยรูปแบบเดียวกัน (lat, lon, radius_km)
"""
import json, math, pathlib, statistics, sys, time, urllib.request, datetime as dt

ROOT = pathlib.Path(__file__).resolve().parent.parent
BATCH = 100
LEVELS = ["normal", "watch", "high", "critical"]

def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))

def batched(atms, base, params):
    out = []
    for i in range(0, len(atms), BATCH):
        chunk = atms[i:i + BATCH]
        lat = ",".join(str(a["lat"]) for a in chunk)
        lon = ",".join(str(a["lon"]) for a in chunk)
        res = get(f"{base}?latitude={lat}&longitude={lon}&{params}")
        out += res if isinstance(res, list) else [res]
    return out

def km(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))

def main():
    atms = json.loads((ROOT / "data/atms_mock.json").read_text("utf-8"))
    zones = json.loads((ROOT / "data/flood_zones_mock.json").read_text("utf-8"))
    src = {"rain": "Open-Meteo Forecast", "river": "Open-Meteo Flood (GloFAS)",
           "zones": "จำลอง (รอเชื่อม GISTDA)", "atms": "จำลอง"}
    try:
        rain = batched(atms, "https://api.open-meteo.com/v1/forecast",
                       "daily=precipitation_sum&forecast_days=3&timezone=Asia/Bangkok")
        flow = batched(atms, "https://flood-api.open-meteo.com/v1/flood",
                       "daily=river_discharge&past_days=30&forecast_days=3")
        live = True
    except Exception as e:
        print("ดึงข้อมูลออนไลน์ไม่สำเร็จ:", e, file=sys.stderr)
        rain = flow = None
        live = False
        src["rain"] = src["river"] = "ไม่สามารถดึงได้ (ใช้ค่า 0)"

    for i, a in enumerate(atms):
        rain3, ratio = 0.0, 1.0
        if live:
            r = [v or 0 for v in rain[i]["daily"]["precipitation_sum"]]
            rain3 = round(sum(r), 1)
            q = [v for v in flow[i]["daily"]["river_discharge"] if v is not None]
            if len(q) > 5:
                past, fut = q[:-3], q[-3:]
                med = statistics.median(past)
                if med > 0.5 and fut:
                    ratio = round(max(fut) / med, 2)
        nearest, dist = None, 1e9
        for z in zones:
            d = km(a["lat"], a["lon"], z["lat"], z["lon"]) - z["radius_km"]
            if d < dist:
                nearest, dist = z, d
        reasons, lvl = [], 0
        if dist <= 0:
            lvl = 3; reasons.append(f"อยู่ในพื้นที่น้ำท่วม: {nearest['name']}")
        elif dist <= 1:
            lvl = max(lvl, 2); reasons.append(f"อยู่ห่างพื้นที่น้ำท่วมไม่เกิน 1 กม. ({nearest['name']})")
        if ratio >= 3:
            lvl = max(lvl, 2); reasons.append(f"ปริมาณน้ำในแม่น้ำคาดว่าสูงเป็น {ratio} เท่าของปกติ")
        elif ratio >= 1.8:
            lvl = max(lvl, 1); reasons.append(f"ปริมาณน้ำในแม่น้ำเพิ่มขึ้น {ratio} เท่าของปกติ")
        if rain3 >= 120:
            lvl = max(lvl, 2); reasons.append(f"ฝนสะสม 3 วัน {rain3} มม. (หนักมาก)")
        elif rain3 >= 60:
            lvl = max(lvl, 1); reasons.append(f"ฝนสะสม 3 วัน {rain3} มม. (หนัก)")
        a.update(level=LEVELS[lvl], rain3d_mm=rain3, river_ratio=ratio,
                 dist_to_flood_km=None if dist > 1e8 else round(max(dist, 0), 1),
                 reasons=reasons or ["ไม่พบสัญญาณเสี่ยง"])

    counts = {l: sum(a["level"] == l for a in atms) for l in LEVELS}
    out = {"generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).isoformat(timespec="minutes"),
           "live_data": live, "sources": src, "counts": counts, "zones": zones, "atms": atms}
    (ROOT / "web/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "web/data/status.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    print("live =", live, counts)

if __name__ == "__main__":
    main()
