"""每天抓 Open-Meteo 預報，寫入 weather.json（GitHub Actions 排程執行）。
格式：{"updated": ISO 時間, "days": {"1": [[溫度, 降雨機率, 天氣代碼] 或 null, x3], ...}}
"""
import json, urllib.request, urllib.parse, datetime, sys, os

# 每天 早 / 午 / 晚 的地點（與 index.html 的 WXP 相同）
P = {
 1: [(25.08, 121.23), (25.08, 121.23), (35.78447, 140.3514)],
 2: [(36.3726, 140.452), (36.758, 139.5988), (36.83269, 139.71864)],
 3: [(36.4977, 138.92), (36.3404, 138.6344), (36.6371, 138.50784)],
 4: [(36.399, 138.5725), (35.9047, 138.4306), (35.65878, 138.65102)],
 5: [(35.504, 138.6567), (35.5237, 138.7468), (35.4703, 138.7501)],
 6: [(35.2443, 139.0208), (35.1468, 138.959), (34.96855, 139.09723)],
 7: [(35.251, 139.1535), (35.6251, 139.7756), (35.62187, 139.73676)],
 8: [(35.6608, 139.7412), (35.6624, 139.6993), (35.78447, 140.3514)],
}
HOUR = [8, 12, 18]                       # 代表溫度的時間
WIN = [range(6, 11), range(11, 16), range(17, 22)]  # 降雨機率取最大值的時段
TRIP_END = datetime.date(2026, 12, 12)

def main():
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
    if today > TRIP_END:
        print('trip over, skip'); return
    pts = [p for d in sorted(P) for p in P[d]]
    q = urllib.parse.urlencode({
        'latitude': ','.join(str(p[0]) for p in pts),
        'longitude': ','.join(str(p[1]) for p in pts),
        'hourly': 'temperature_2m,precipitation_probability,weather_code',
        'timezone': 'Asia/Tokyo', 'forecast_days': 16,
    })
    req = urllib.request.Request('https://api.open-meteo.com/v1/forecast?' + q,
                                 headers={'User-Agent': 'tokyo261205-weather'})
    data = json.load(urllib.request.urlopen(req, timeout=60))
    if isinstance(data, dict):
        data = [data]
    days, i = {}, 0
    for d in sorted(P):
        date = f'2026-12-{4 + d:02d}'
        row = []
        for k in range(3):
            h = data[i]['hourly']; i += 1
            idx = {int(t[11:13]): j for j, t in enumerate(h['time']) if t.startswith(date)}
            if HOUR[k] not in idx or h['temperature_2m'][idx[HOUR[k]]] is None:
                row.append(None); continue
            pp = [h['precipitation_probability'][idx[x]] for x in WIN[k] if x in idx and h['precipitation_probability'][idx[x]] is not None]
            wc = [h['weather_code'][idx[x]] for x in WIN[k] if x in idx and h['weather_code'][idx[x]] is not None]
            row.append([round(h['temperature_2m'][idx[HOUR[k]]], 1), max(pp) if pp else None, max(wc) if wc else None])
        days[str(d)] = row
    out = {'updated': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec='minutes'), 'days': days}
    path = os.path.join(os.path.dirname(__file__), '..', 'weather.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False)
    print(json.dumps(out, ensure_ascii=False))

if __name__ == '__main__':
    main()
