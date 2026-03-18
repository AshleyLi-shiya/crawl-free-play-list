#!/usr/bin/env python3
"""Fetch all free TV dramas and movies from Mango TV API"""
import requests
import json
import time
import re
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

BASE_URL = "https://pianku.api.mgtv.com/rider/list/pcweb/v3"

def fetch_all_items(channel_id, channel_name):
    """Fetch all free items for a given channel"""
    all_items = []
    page = 1
    
    while True:
        params = {
            'allowedRC': 1,
            'platform': 'pcweb',
            'channelId': channel_id,
            'pn': page,
            'pc': 80,
            'hudong': 1,
            '_support': 10000000,
            'kind': 'a1',
            'area': 'a1',
            'year': 'all',
            'chargeInfo': 'b1',
            'sort': 'c2'
        }
        
        if channel_id == 2:
            params['feature'] = 'all'
        elif channel_id == 3:
            params['edition'] = 'a1'
        
        try:
            resp = requests.get(BASE_URL, params=params, timeout=15)
            data = resp.json()
        except Exception as e:
            print(f"  [WARN] Page {page} failed: {e}, retrying...")
            time.sleep(2)
            try:
                resp = requests.get(BASE_URL, params=params, timeout=15)
                data = resp.json()
            except Exception as e2:
                print(f"  [ERROR] Page {page} failed again: {e2}, skipping")
                break
        
        hit_docs = data.get('data', {}).get('hitDocs', [])
        has_more = data.get('data', {}).get('hasMore', False)
        
        for item in hit_docs:
            # Skip trailers/previews - these are paid content with free previews only
            corner_text = item.get('rightCorner', {}).get('text', '')
            if corner_text == '预告':
                continue
            all_items.append({
                'clipId': item.get('clipId', ''),
                'title': item.get('title', ''),
                'kind': item.get('kind', []),
                'story': item.get('story', ''),
                'updateInfo': item.get('updateInfo', ''),
                'subtitle': item.get('subtitle', ''),
                'year': item.get('year', ''),
            })
        
        print(f"  {channel_name} page {page}: got {len(hit_docs)} items, total so far: {len(all_items)}, hasMore: {has_more}")
        
        if not has_more:
            break
        
        page += 1
        time.sleep(0.5)
    
    return all_items

def parse_episode_count(update_info):
    """Extract episode count from updateInfo string"""
    if not update_info:
        return 0
    # Match patterns like "全98集", "共60集", "更新至112集"
    m = re.search(r'(\d+)集', update_info)
    if m:
        return int(m.group(1))
    return 0

def main():
    print("=" * 60)
    print("Fetching Mango TV free content")
    print("=" * 60)
    
    # Fetch TV dramas (channelId=2)
    print("\n[1/2] Fetching free TV dramas (channelId=2)...")
    tv_dramas = fetch_all_items(2, "TV Dramas")
    print(f"\nTotal TV dramas fetched: {len(tv_dramas)}")
    
    # Fetch movies (channelId=3)
    print("\n[2/2] Fetching free movies (channelId=3)...")
    movies = fetch_all_items(3, "Movies")
    print(f"\nTotal movies fetched: {len(movies)}")
    
    # Filter short dramas (>50 episodes likely short dramas)
    short_dramas = []
    regular_dramas = []
    for d in tv_dramas:
        ep_count = parse_episode_count(d['updateInfo'])
        if ep_count > 50:
            short_dramas.append(d)
        else:
            regular_dramas.append(d)
    
    print(f"\n--- Summary ---")
    print(f"Total TV dramas: {len(tv_dramas)}")
    print(f"  Regular dramas (<=50 eps): {len(regular_dramas)}")
    print(f"  Likely short dramas (>50 eps): {len(short_dramas)}")
    print(f"Total movies: {len(movies)}")
    
    # Save to file
    output = {
        'platform': 'MangoTV',
        'tvDramas': {
            'all': tv_dramas,
            'regular': regular_dramas,
            'shortDramas': short_dramas,
        },
        'movies': movies,
        'stats': {
            'totalTvDramas': len(tv_dramas),
            'regularDramas': len(regular_dramas),
            'shortDramas': len(short_dramas),
            'totalMovies': len(movies),
        }
    }
    
    outpath = os.path.join(DATA_DIR, 'mgtv_data.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\nData saved to {outpath}")

if __name__ == '__main__':
    main()
