"""公司影印機用：按順序列印版（不做騎馬釘、不補 MEMO 頁）。
輸出 book-seq-a4.pdf（每張 A4 一頁，A5 等比放大）＋ book-seq-a4-2up.pdf（A4 雙面裁切堆疊成 A5）。
用法：python scripts/build_seq.py [輸出資料夾]
"""
import os, sys, threading, http.server, functools, copy, shutil
from pypdf import PdfReader, PdfWriter, Transformation, PageObject
from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
idx = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
addon = open(os.path.join(ROOT, 'scripts', 'book_addon.html'), encoding='utf-8').read()
book = idx.replace('</body>', '<script>window.BOOK_SEQ=1</script>\n' + addon + '\n</body>', 1)
open(os.path.join(ROOT, 'book.html'), 'w', encoding='utf-8').write(book)

srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8766), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
threading.Thread(target=srv.serve_forever, daemon=True).start()
a5 = os.path.join(ROOT, 'book-seq-a5.pdf')
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge')
    pg = b.new_page(viewport={'width': 560, 'height': 800})
    pg.on('pageerror', lambda e: print('JS ERROR', e))
    pg.goto('http://127.0.0.1:8766/book.html')
    pg.wait_for_function("document.documentElement.dataset.ready==='1'", timeout=60000)
    pg.wait_for_load_state('networkidle')
    pg.wait_for_timeout(1500)
    pg.pdf(path=a5, width='148mm', height='210mm', print_background=True, prefer_css_page_size=True)
    b.close()
srv.shutdown()

r = PdfReader(a5)
n = len(r.pages)
W, H = 595.28, 841.89  # A4 直

one = PdfWriter()
for src in r.pages:
    s = PageObject.create_blank_page(width=W, height=H)
    k = min(W / float(src.mediabox.width), H / float(src.mediabox.height))
    s.merge_transformed_page(copy.copy(src), Transformation().scale(k, k))
    one.add_page(s)
f1 = os.path.join(ROOT, 'book-seq-a4.pdf'); one.write(f1)

# 裁切堆疊（cut & stack）：A4 橫向雙面、短邊翻頁；印完整疊從中間裁開，左半疊放在右半疊上面＝A5 依序
S = -(-n // 4)          # 紙張數
two = PdfWriter()
w = H / 2
def side(left, right):
    s = PageObject.create_blank_page(width=H, height=W)
    for j, x in ((left, 0), (right, w)):
        if j < n:
            src = copy.copy(r.pages[j])
            k = min(w / float(src.mediabox.width), W / float(src.mediabox.height))
            s.merge_transformed_page(src, Transformation().scale(k, k).translate(x, 0))
    two.add_page(s)
for i in range(S):
    a, b = 2 * i, 2 * S + 2 * i
    side(a, b)            # 正面
    side(b + 1, a + 1)    # 反面（短邊翻頁，左右對調）
f2 = os.path.join(ROOT, 'book-seq-a4-2up.pdf'); two.write(f2)
print('done', n, 'pages')

if len(sys.argv) > 1:
    d = sys.argv[1]; os.makedirs(d, exist_ok=True)
    shutil.copy(f1, os.path.join(d, '東京深度八日_小書_A4每頁一張_依序.pdf'))
    shutil.copy(f2, os.path.join(d, '東京深度八日_小書_A4雙面裁切成A5.pdf'))
    print('copied to', d)
