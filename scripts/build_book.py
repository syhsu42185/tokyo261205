"""產生 A5 旅遊小書：book.html → book-a5.pdf（逐頁）＋ book-print-a4.pdf（A4 雙面對折騎馬釘排版）。
用法：python scripts/build_book.py   （需要 playwright＋Edge、pypdf；會自動起本機伺服器）
"""
import os, sys, threading, http.server, functools, copy
from pypdf import PdfReader, PdfWriter, Transformation, PageObject
from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
idx = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
addon = open(os.path.join(ROOT, 'scripts', 'book_addon.html'), encoding='utf-8').read()
book = idx.replace('</body>', addon + '\n</body>', 1).replace('<title>東京深度八日｜冬日旅遊小書</title>', '<title>旅遊小書（列印版）</title>', 1)
open(os.path.join(ROOT, 'book.html'), 'w', encoding='utf-8').write(book)

srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8766), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
threading.Thread(target=srv.serve_forever, daemon=True).start()
a5 = os.path.join(ROOT, 'book-a5.pdf')
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    pg = b.new_page(viewport={'width': 560, 'height': 800})
    pg.on('pageerror', lambda e: print('JS ERROR', e))
    pg.goto('http://127.0.0.1:8766/book.html')
    pg.wait_for_function("document.documentElement.dataset.ready==='1'", timeout=60000)
    pg.wait_for_load_state('networkidle')
    pg.wait_for_timeout(1500)
    print('pages', pg.evaluate('document.documentElement.dataset.pages'))
    pg.pdf(path=a5, width='148mm', height='210mm', print_background=True, prefer_css_page_size=True)
    b.close()
srv.shutdown()

# 騎馬釘拼版：A4 橫向，每張紙正反各放 2 頁 A5
r = PdfReader(a5)
n = len(r.pages)
assert n % 4 == 0, n
W, H = 595.28, 841.89  # A4 直
w = H / 2  # A5 寬 (pt) = 420.9
out = PdfWriter()
def side(left, right):
    s = PageObject.create_blank_page(width=H, height=W)
    for i, x in ((left, 0), (right, w)):
        pgx = copy.copy(r.pages[i])
        sx = w / float(pgx.mediabox.width); sy = W / float(pgx.mediabox.height)
        k = min(sx, sy)
        s.merge_transformed_page(pgx, Transformation().scale(k, k).translate(x, 0))
    out.add_page(s)
for i in range(n // 4):
    side(n - 1 - 2 * i, 2 * i)        # 正面
    side(2 * i + 1, n - 2 - 2 * i)    # 反面
out.write(os.path.join(ROOT, 'book-print-a4.pdf'))
print('done', n, 'A5 pages ->', n // 2, 'A4 sides')
