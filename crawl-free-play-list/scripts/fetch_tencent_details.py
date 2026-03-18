#!/usr/bin/env python3
"""
Fetch Tencent Video free TV dramas and movies with full details via MVL API.
Fields: title, year, actors, region, episodes, genre
"""
import requests
import json
import time
import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Content-Type': 'application/json',
    'Referer': 'https://v.qq.com/',
    'Origin': 'https://v.qq.com',
}

MVL_URL = 'https://pbaccess.video.qq.com/trpc.multi_vector_layout.mvl_controller.MVLPageHTTPService/getMVLPage?&vversion_platform=2'


def fetch_tencent_page(channel_id, filter_params, page_index, page_context=None):
    body = {
        "page_params": {
            "page_type": "channel_operation",
            "page_id": "channel_list_second_page",
            "channel_id": channel_id,
            "filter_params": filter_params,
            "page": page_index,
        },
        "page_bypass_params": {
            "params": {
                "caller_id": "3000010",
                "platform_id": "2",
                "data_mode": "default",
                "user_mode": "default",
                "page_type": "channel_operation",
                "page_id": "channel_list_second_page",
                "channel_id": channel_id,
                "filter_params": filter_params,
            },
            "scene": "channel_operation"
        },
        "page_context": {
            "page_index": str(page_index),
        }
    }
    if page_context:
        body["page_context"].update(page_context)

    resp = requests.post(MVL_URL, json=body, headers=HEADERS, timeout=15)
    return resp.json()


def extract_tencent_items(data):
    """Extract items from MVL API response with full detail fields."""
    items = []
    card_list = data.get('data', {}).get('CardList', [])
    if not card_list:
        card_list = data.get('data', {}).get('card_list', [])

    for card in card_list:
        children = card.get('children_list', {}).get('list', {}).get('cards', [])
        for child in children:
            params = child.get('params', {})
            title = params.get('title', '')
            if not title:
                continue

            # Extract all available fields
            item = {
                'title': title,
                'cid': params.get('cid', child.get('id', '')),
                'genre': params.get('main_genre', ''),
                'sub_genre': params.get('sub_genre', ''),
                'description': params.get('second_title', ''),
                'area': params.get('areaName', params.get('area_name', '')),
                'year': params.get('year', params.get('publish_date', '')),
                'actors': params.get('leading_actor', params.get('director', '')),
                'episodes': params.get('episode_update', params.get('timeDuration', '')),
                'score': params.get('score', ''),
            }
            items.append(item)
    return items


def fetch_all_tencent(channel_id, channel_name, filter_params):
    """Fetch all items from a Tencent Video channel."""
    print(f"\nFetching Tencent {channel_name} (channel={channel_id})")
    all_items = []
    seen_cids = set()
    page_index = 0
    page_context = {}
    empty_count = 0

    while True:
        try:
            data = fetch_tencent_page(channel_id, filter_params, page_index, page_context)
        except Exception as e:
            print(f"  Page {page_index} error: {e}")
            time.sleep(2)
            try:
                data = fetch_tencent_page(channel_id, filter_params, page_index, page_context)
            except:
                break

        if data.get('ret') != 0:
            print(f"  Page {page_index}: ret={data.get('ret')}, msg={data.get('msg')}")
            break

        items = extract_tencent_items(data)

        new_count = 0
        for item in items:
            key = item['cid'] or item['title']
            if key not in seen_cids:
                seen_cids.add(key)
                all_items.append(item)
                new_count += 1

        print(f"  Page {page_index}: {len(items)} raw, {new_count} new, total unique: {len(all_items)}")

        if not items:
            empty_count += 1
            if empty_count >= 2:
                break
        else:
            empty_count = 0

        # Update page context from response
        resp_context = data.get('data', {}).get('page_context', {})
        if resp_context:
            page_context = resp_context

        has_next = data.get('data', {}).get('has_next_page', False)
        if not has_next and not items:
            break

        page_index += 1
        time.sleep(0.3)

        if page_index > 100:
            break

    return all_items


def main():
    # First, let's do a test fetch to see what fields are available
    print("=" * 60)
    print("Testing Tencent Video API field availability")
    print("=" * 60)

    test_data = fetch_tencent_page("100113", "sort=75&charge=1&iarea=-1&iyear=-1", 0)
    if test_data.get('ret') == 0:
        card_list = test_data.get('data', {}).get('CardList', [])
        if card_list:
            children = card_list[0].get('children_list', {}).get('list', {}).get('cards', [])
            if children:
                # Print all available params keys from first item
                params = children[0].get('params', {})
                print(f"Available params keys ({len(params)}):")
                for k, v in sorted(params.items()):
                    val_str = str(v)[:80]
                    print(f"  {k}: {val_str}")
    
    # Fetch TV Dramas - free filter: charge=1
    print("\n" + "=" * 60)
    print("[1] Fetching Tencent Video free TV Dramas")
    print("=" * 60)
    tv_dramas = fetch_all_tencent("100113", "TV Dramas", "sort=75&charge=1&iarea=-1&iyear=-1")

    # Fetch Movies - free filter: charge=1
    print("\n" + "=" * 60)
    print("[2] Fetching Tencent Video free Movies")
    print("=" * 60)
    movies = fetch_all_tencent("100173", "Movies", "sort=75&charge=1&iarea=-1&iyear=-1")

    # Save
    output = {
        'platform': 'TencentVideo',
        'tvDramas': tv_dramas,
        'movies': movies,
    }
    outpath = os.path.join(DATA_DIR, 'tencent_details.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to: {outpath}")
    print(f"Total: {len(tv_dramas)} TV dramas, {len(movies)} movies")

    # Show samples
    if tv_dramas:
        d = tv_dramas[0]
        print(f"\nTV sample: {d['title']} | year={d['year']} | actors={d.get('actors','')[:50]} | area={d['area']} | ep={d['episodes']} | genre={d['genre']}")
    if movies:
        m = movies[0]
        print(f"Movie sample: {m['title']} | year={m['year']} | actors={m.get('actors','')[:50]} | area={m['area']} | genre={m['genre']}")


if __name__ == '__main__':
    main()
