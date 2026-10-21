"""ギルド用の AION2 相場ページを作る（GitHub Actions で毎時実行）。

1. 公開中のページから、これまでの値動き（history.json）と日本語名（names.json）を受け取る
   - 初回だけは seed/ の中身を使う
2. Aion2Market から今の最安値を取り込み、値動きに足す（8日より古い分は捨てる）
3. site/ に index.html・history.json・names.json を書き出す（GitHub Pages がこれを公開する）

外部ライブラリは使わない（GitHub Actions の Python だけで動くように）。
"""
import json
import os
import statistics as st
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path

BASE = Path(__file__).resolve().parent
SITE = BASE / 'site'
SEED = BASE / 'seed'
SITE_URL = os.environ.get('SITE_URL', '').rstrip('/')   # 公開中のページの URL（Actions が渡す）
SERVER = 11503  # バイゼル（AS・天族）
API = 'https://aion2.exchange/api'
SECTIONS = ['materials', 'consumables', 'accessories', 'weapons', 'armor', 'skins', 'other']
SELL_FEE, LIST_FEE = 0.10, 0.02  # 出典: Space4Games「AION 2 Marketplace」2026/10/12
KEEP_DAYS = 8
NAMES_PER_RUN = 80
JST = timezone(timedelta(hours=9))
UA = {'User-Agent': 'aion2-guild-market-page/1.0 (hourly)'}
SKILL_JA = {'Jewelcrafting': '細工', 'Blacksmithing': '鍛冶', 'Tailoring': '裁縫', 'Alchemy': '錬金'}  # 公式の表記は未確認


def get(url, as_json=True, tries=5):
    waits = [5, 15, 30, 60]
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                body = r.read().decode('utf-8')
            return json.loads(body) if as_json else body
        except urllib.error.HTTPError as e:
            if e.code == 404 or i == tries - 1:
                raise
        except Exception:
            if i == tries - 1:
                raise
        time.sleep(waits[min(i, len(waits) - 1)])


def load_previous(name):
    """公開中のページから前回の分を受け取る。まだ公開前（404）なら seed を使う。"""
    if SITE_URL:
        try:
            return get(f'{SITE_URL}/{name}?t={int(time.time())}')
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise  # 一時的な不調で記録を消さないよう、ここで止める
    p = SEED / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}


def hour_iso(s):
    t = datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc)
    return t.replace(minute=0, second=0, microsecond=0)


def fetch_items():
    items = []
    for sec in SECTIONS:
        off = 0
        while True:
            j = get(f'{API}/items?server={SERVER}&sort=name&order=asc&window=24h&limit=50&offset={off}&section={sec}')
            items += j['items']
            off += 50
            time.sleep(0.5)
            if off >= j['total'] or not j['items']:
                break
    return items


def main():
    history = load_previous('history.json')       # {key: [[UNIX秒(1時間単位), 最安値, 出品数], ...]}
    names = load_previous('names.json')           # {key: 日本語名}
    for attempt in range(3):  # 相場サイトがときどき止まるので、少し待って取り直す
        try:
            items = fetch_items()
            break
        except Exception as e:
            if attempt == 2:
                raise
            print(f'取り込みに失敗、2分後にやり直し: {e}')
            time.sleep(120)
    captured = max(i['captured_at'] for i in items if i.get('captured_at'))
    now = hour_iso(captured)
    stamp = int(now.timestamp())
    cutoff = int((now - timedelta(days=KEEP_DAYS)).timestamp())
    for it in items:
        if not (it['listed'] and it['price']):
            continue
        pts = [p for p in history.get(str(it['item_key']), []) if p[0] >= cutoff and p[0] != stamp]
        pts.append([stamp, round(it['price']), it['listings'] or 0])
        history[str(it['item_key'])] = sorted(pts)
    history = {k: [p for p in v if p[0] >= cutoff] for k, v in history.items()}
    history = {k: v for k, v in history.items() if v}

    # 日本語名（足りない分だけ、1回に少しずつ取りに行く）
    missing = [str(i['item_key']) for i in items if i['listed'] and str(i['item_key']) not in names][:NAMES_PER_RUN]
    for k in missing:
        try:
            html = get(f'https://aion2.th.gl/ja/db/inventory/it_{k}', as_json=False, tries=1)
            s = html.find('<title>')
            title = unescape(html[s + 7:html.find('</title>', s)]) if s >= 0 else ''
            names[k] = title.split(' – ')[0].strip() if ' – ' in title else ''
        except Exception:
            pass
        time.sleep(0.3)

    crafts = get(f'{API}/crafts?server={SERVER}&sort=name&order=asc')

    # 分析（品目ごと）
    t0 = now - timedelta(days=7)
    rows, hist_out = [], {}
    for it in items:
        k = str(it['item_key'])
        if not (it['listed'] and it['price']) or k not in history:
            continue
        pts = [p for p in history[k] if p[0] >= int(t0.timestamp())]
        if not pts:
            continue
        p72 = [p[1] for p in pts if p[0] > stamp - 72 * 3600]
        prev = [p[1] for p in pts if p[0] <= stamp - 23 * 3600]
        low72 = sorted(p72)
        price = it['price']
        rows.append(dict(
            k=int(k), ja=names.get(k) or it['name'], en=it['name'], sec=it['category']['section_id'], cat=it['category']['name'],
            now=price, lst=it['listings'], a24=prev[-1] if prev else None, f7=pts[0][1], m72=st.median(p72),
            mn=min(p[1] for p in pts), mx=max(p[1] for p in pts), q20=low72[int(len(low72) * 0.2)],
            c24=(price / prev[-1] - 1) if prev else None, c7=price / pts[0][1] - 1,
        ))
        hist_out[k] = [x for p in pts for x in (round((p[0] - t0.timestamp()) / 3600, 2), p[1], p[2])]
    rows.sort(key=lambda r: (r['sec'], r['cat'], r['ja']))

    craft_rows = []
    for t in crafts.get('targets', []):
        mp = t.get('market_price')
        net = mp * (1 - SELL_FEE - LIST_FEE) - t['cost'] if mp else None
        craft_rows.append([names.get(str(t['target_key'])) or t['name'], SKILL_JA.get(t['skill'], t['skill']),
                           round(t['cost']), mp, t.get('listings'), round(net) if net is not None else None])
    craft_rows.sort(key=lambda r: r[5] if r[5] is not None else -1e18, reverse=True)

    data = dict(stamp=now.astimezone(JST).strftime('%m/%d %H:%M'), built=datetime.now(JST).strftime('%m/%d %H:%M'),
                capturedIso=now.strftime('%Y-%m-%dT%H:%M:%SZ'), t0Iso=t0.strftime('%Y-%m-%dT%H:%M:%SZ'),
                items=rows, hist=hist_out, crafts=craft_rows)
    html = (BASE / 'template.html').read_text(encoding='utf-8')
    html = html.replace('/*DATA*/null', json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
    icon = BASE / 'icon64.b64'
    if icon.exists():
        uri = 'data:image/png;base64,' + icon.read_text().strip()
        html = html.replace('<!--ICON-->', f'<link rel="icon" href="{uri}"><link rel="apple-touch-icon" href="{uri}">')

    SITE.mkdir(exist_ok=True)
    (SITE / 'index.html').write_text(html, encoding='utf-8')
    (SITE / 'history.json').write_text(json.dumps(history, separators=(',', ':')), encoding='utf-8')
    (SITE / 'names.json').write_text(json.dumps(names, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'ok data={data["stamp"]} items={len(rows)} names+={len(missing)}')


if __name__ == '__main__':
    sys.exit(main())
