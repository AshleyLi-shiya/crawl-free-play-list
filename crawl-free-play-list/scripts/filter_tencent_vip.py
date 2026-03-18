#!/usr/bin/env python3
"""
Filter out VIP/paid content from tencent_details.json.

Strategy: Query the Tencent MVL listing API and classify each item using
two signals from the response:

1. all_ids F-value (primary): Each episode has an F field:
   - F:0/F:2 = free (possibly with ads)
   - F:7 = VIP-only
   If >50% of episodes are F:7, the item is VIP.

2. mark_label text (secondary): Position "2" of the latest_mark_label
   JSON contains a badge. Text containing "VIP" or "会员" indicates VIP.

An item is classified as VIP (removed) if EITHER signal triggers.
An item is classified as free (kept) if BOTH signals say free.

Note: The listing API's ipay=免费 filter parameter is broken — it
returns ALL content regardless of payment type.
"""
import requests
import json
import time
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Content-Type': 'application/json',
    'Referer': 'https://v.qq.com/',
    'Origin': 'https://v.qq.com',
}

MVL_URL = ('https://pbaccess.video.qq.com/trpc.multi_vector_layout.'
           'mvl_controller.MVLPageHTTPService/getMVLPage?&vversion_platform=2')

INPUT_PATH = os.path.join(DATA_DIR, 'tencent_details.json')
OUTPUT_PATH = os.path.join(DATA_DIR, 'tencent_details.json')

VIP_KEYWORDS = ['VIP', 'vip', '会员']
VIP_F_THRESHOLD = 0.5  # If >50% of episodes are F:7, item is VIP


def is_vip_by_mark_label(mark_label_str):
    """Check if an item is VIP based on its latest_mark_label JSON."""
    if not mark_label_str:
        return False
    try:
        mark_data = json.loads(mark_label_str)
        tag2 = mark_data.get('2', {}).get('info', {})
        tag_text = tag2.get('text', '')
        for kw in VIP_KEYWORDS:
            if kw in tag_text:
                return True
    except (json.JSONDecodeError, AttributeError):
        pass
    return False


def is_vip_by_f_values(all_ids_raw):
    """Check if an item is VIP based on episode F values in all_ids.
    F:7 = VIP, F:0/F:2 = free. Returns True/False/None."""
    try:
        all_ids = json.loads(all_ids_raw) if isinstance(all_ids_raw, str) else all_ids_raw
    except (json.JSONDecodeError, TypeError):
        return None

    if not all_ids or not isinstance(all_ids, list):
        return None

    total = len(all_ids)
    vip_count = sum(1 for ep in all_ids if isinstance(ep, dict) and ep.get('F') == 7)

    return (vip_count / total) > VIP_F_THRESHOLD


def fetch_free_cids(channel_id, channel_name, filter_params):
    """Scan listing API to classify CIDs using mark_label + all_ids F values."""
    free_cids = set()
    vip_cids = set()
    page_ctx = None
    page_num = 0

    vip_by_label = 0
    vip_by_f = 0
    vip_by_both = 0

    print(f"\n{'='*60}")
    print(f"Scanning {channel_name} (channel={channel_id})")
    print(f"{'='*60}")

    while True:
        body = {
            'page_params': {
                'channel_id': channel_id,
                'filter_params': filter_params,
                'page_type': 'operation',
                'page_id': 'channel_list'
            }
        }
        if page_ctx:
            body['page_context'] = page_ctx

        try:
            resp = requests.post(MVL_URL, json=body, headers=HEADERS, timeout=15)
            data = resp.json()
        except Exception as e:
            print(f"  Page {page_num} error: {e}")
            time.sleep(2)
            page_num += 1
            if page_num > 3:
                break
            continue

        if data.get('ret') != 0:
            print(f"  Page {page_num}: ret={data.get('ret')}, msg={data.get('msg')}")
            break

        modules = data.get('data', {}).get('modules', {})
        ncards = modules.get('normal', {}).get('cards', [])
        cards = []
        if ncards:
            cards = (ncards[0].get('children_list', {})
                     .get('poster_card', {}).get('cards', []))

        for c in cards:
            p = c.get('params', {})
            cid = p.get('cid', '')
            if not cid:
                continue

            label_vip = is_vip_by_mark_label(p.get('latest_mark_label', ''))
            f_vip = is_vip_by_f_values(p.get('all_ids', '[]'))

            if label_vip and f_vip:
                vip_by_both += 1
            elif label_vip:
                vip_by_label += 1
            elif f_vip:
                vip_by_f += 1

            if label_vip or f_vip:
                vip_cids.add(cid)
            else:
                free_cids.add(cid)

        has_next = data.get('data', {}).get('has_next_page', False)

        if page_num % 20 == 0:
            print(f"  Page {page_num}: free={len(free_cids)}, vip={len(vip_cids)}")

        if not has_next or not cards:
            break

        page_ctx = data.get('data', {}).get('page_context', {})
        page_num += 1
        time.sleep(0.15)

        if page_num > 500:
            break

    print(f"  Done: {page_num+1} pages, free={len(free_cids)}, vip={len(vip_cids)}")
    print(f"  VIP breakdown: label_only={vip_by_label}, f_only={vip_by_f}, both={vip_by_both}")
    return free_cids, vip_cids


def main():
    print("Loading tencent_details.json...")
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    movies = data.get('movies', [])
    tv_dramas = data.get('tvDramas', [])
    orig_tv = len(tv_dramas)
    orig_mv = len(movies)
    print(f"Loaded: {orig_tv} TV dramas, {orig_mv} movies")

    # Scan listing API to classify CIDs
    tv_free, tv_vip = fetch_free_cids(
        '100113', 'TV Dramas',
        'sort=75&itype=-1&iarea=-1&iyear=-1&theater=-1&award=-1'
    )
    mv_free, mv_vip = fetch_free_cids(
        '100173', 'Movies',
        'sort=75&itype=-1&iarea=-1&iyear=-1'
    )

    # Keep items that are in the free set
    final_tv = [item for item in tv_dramas if item.get('cid', '') in tv_free]
    final_mv = [item for item in movies if item.get('cid', '') in mv_free]

    # Save
    data['tvDramas'] = final_tv
    data['movies'] = final_mv

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"FINAL RESULTS")
    print(f"{'='*60}")
    print(f"TV Dramas: {orig_tv} -> {len(final_tv)} (removed {orig_tv - len(final_tv)})")
    print(f"Movies:    {orig_mv} -> {len(final_mv)} (removed {orig_mv - len(final_mv)})")
    print(f"\nSaved to: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
