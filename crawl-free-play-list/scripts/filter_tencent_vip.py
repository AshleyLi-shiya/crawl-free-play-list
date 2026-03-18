#!/usr/bin/env python3
"""
Filter out VIP/paid content from tencent_details.json by checking each item's
vid field via the float_vinfo2 API. Items with vid=null are VIP (paid).
"""
import requests
import json
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://v.qq.com/',
}

INPUT_PATH = os.path.join(DATA_DIR, 'tencent_details.json')
OUTPUT_PATH = os.path.join(DATA_DIR, 'tencent_details.json')


def check_vip_status(cid):
    """Check if a CID is VIP by looking at the vid field in float_vinfo2.
    Returns True if the content is FREE, False if VIP/paid.
    """
    url = f'https://node.video.qq.com/x/api/float_vinfo2?cid={cid}'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        vid = data.get('c', {}).get('vid')
        # VIP content has vid=null or empty, free content has a vid value
        is_free = vid is not None and vid != '' and vid != 'null'
        return is_free
    except Exception as e:
        # On error, keep the item (don't remove it)
        return True


def filter_items(items, category_name):
    """Filter a list of items, removing VIP content."""
    total = len(items)
    free_items = []
    vip_count = 0
    error_count = 0

    print(f"\n{'='*60}")
    print(f"Checking {category_name}: {total} items")
    print(f"{'='*60}")

    # Use thread pool for concurrent requests (5 threads)
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_idx = {}
        for idx, item in enumerate(items):
            cid = item.get('cid', '')
            if not cid:
                results[idx] = True  # Keep items without CID
                continue
            future = executor.submit(check_vip_status, cid)
            future_to_idx[future] = idx

        done_count = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                is_free = future.result()
                results[idx] = is_free
            except Exception:
                results[idx] = True  # Keep on error

            done_count += 1
            if done_count % 100 == 0:
                print(f"  Progress: {done_count}/{total} checked...")

    # Build filtered list maintaining original order
    for idx, item in enumerate(items):
        is_free = results.get(idx, True)
        if is_free:
            free_items.append(item)
        else:
            vip_count += 1

    print(f"\n  Results for {category_name}:")
    print(f"    Total:   {total}")
    print(f"    Free:    {len(free_items)}")
    print(f"    VIP:     {vip_count}")
    print(f"    Removed: {vip_count} ({vip_count/total*100:.1f}%)")

    return free_items


def main():
    print("Loading tencent_details.json...")
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    movies = data.get('movies', [])
    tv_dramas = data.get('tvDramas', [])

    print(f"Loaded: {len(movies)} movies, {len(tv_dramas)} TV dramas")

    # Filter movies
    free_movies = filter_items(movies, "Movies")

    # Filter TV dramas
    free_tv = filter_items(tv_dramas, "TV Dramas")

    # Save filtered data
    data['movies'] = free_movies
    data['tvDramas'] = free_tv

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"FINAL RESULTS")
    print(f"{'='*60}")
    print(f"Movies:    {len(movies)} -> {len(free_movies)} (removed {len(movies)-len(free_movies)})")
    print(f"TV Dramas: {len(tv_dramas)} -> {len(free_tv)} (removed {len(tv_dramas)-len(free_tv)})")
    print(f"\nSaved to: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
