#!/usr/bin/env python3
"""压力测试：逐页爬取，找出不触发风控的最大数据量上限。"""

import time
from walmart_scraper import fetch_page, extract_items

KEYWORD = "laptop"
MAX_PAGES = 25

seen = set()
total = 0

print(f"{'页':>4} {'新增':>6} {'累计':>6} {'耗时':>6} 状态")
print("-" * 45)

for page in range(1, MAX_PAGES + 1):
    t0 = time.time()
    try:
        resp = fetch_page(KEYWORD, page, sort="best_match")
        items = extract_items(resp.text, page)
        new_ids = []
        for it in items:
            uid = it["usItemId"]
            if uid and uid not in seen:
                seen.add(uid)
                new_ids.append(it)
        total += len(new_ids)
        elapsed = time.time() - t0
        status = "OK"
        print(f"{page:>4} {len(new_ids):>6} {total:>6} {elapsed:>5.1f}s {status}")
    except RuntimeError as e:
        elapsed = time.time() - t0
        print(f"{page:>4} {'FAIL':>6} {total:>6} {elapsed:>5.1f}s {e}")
        print(f"\n>>> 第 {page} 页触发风控，安全上限约 {page - 1} 页 / {total} 条")
        break
    time.sleep(2)

print(f"\n>>> 最终结果：{page} 页，累计 {total} 条")
print(">>> 建议：设置最大页数为触发风控前1-2页")
