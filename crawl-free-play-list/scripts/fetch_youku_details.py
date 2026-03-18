#!/usr/bin/env python3
"""
Fetch detailed info for all Youku free movies and TV dramas.
Extracts: year, region, genre, actors, description from show pages.
"""
import json
import re
import sys
import time
import os
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

PROGRESS_FILE = os.path.join(DATA_DIR, 'youku_details_progress.json')


def save_progress(all_details):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False)
    print(f"  [progress] saved {len(all_details)} items", flush=True)


def fetch_show_detail(session, show_id):
    """Fetch detail page for a single show and extract info."""
    url = f'https://www.youku.com/show_page/id_{show_id}.html'
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return {'showId': show_id, 'error': f'HTTP {resp.status_code}'}

        match = re.search(r'__INITIAL_DATA__\s*=\s*({[\s\S]*?});\s*</script>', resp.text)
        if not match:
            return {'showId': show_id, 'error': 'no_initial_data'}

        data = json.loads(match.group(1))
        ml = data.get('moduleList', [])
        if not ml:
            return {'showId': show_id, 'error': 'empty_moduleList'}

        comp = ml[0].get('components', [{}])[0]
        items = comp.get('itemList', [])
        if not items:
            return {'showId': show_id, 'error': 'empty_itemList'}

        item0 = items[0]
        intro_sub = item0.get('introSubTitle', '')
        desc = item0.get('desc', '')

        # Parse introSubTitle: "地区·年份·题材1/题材2"
        parts = intro_sub.split('·')
        region = ''
        year = ''
        genre = ''
        for p in parts:
            p = p.strip()
            if re.match(r'^\d{4}$', p):
                year = p
            elif re.match(r'^(中国|美国|英国|法国|日本|韩国|印度|意大利|德国|加拿大|澳大利亚|西班牙|俄罗斯|泰国|中国香港|中国台湾|巴西|墨西哥|阿根廷|其他)', p):
                region = p
            else:
                if not region and not year:
                    region = p
                else:
                    genre = p if not genre else genre + ',' + p

        # Fallback: if region is empty but first part looks like region
        if not region and parts:
            first = parts[0].strip()
            if not re.match(r'^\d{4}$', first) and not any(g in first for g in ['剧情', '动作', '喜剧', '爱情']):
                region = first

        # Extract actors
        actors = []
        for item in items[1:]:
            sub = item.get('subtitle', '')
            name = item.get('title', '')
            if sub.startswith('饰') and name:
                actors.append(name)

        return {
            'showId': show_id,
            'year': year,
            'region': region,
            'genre': genre,
            'actors': ','.join(actors[:10]),
            'desc': desc,
            'introSubTitle': intro_sub,
        }

    except Exception as e:
        return {'showId': show_id, 'error': str(e)}


def process_batch(items, category_name, all_details):
    """Process a batch of items and fetch their details."""
    session = requests.Session()
    total = len(items)
    errors = 0

    for i, item in enumerate(items):
        show_id = item['showId']

        detail = fetch_show_detail(session, show_id)
        all_details[show_id] = detail

        if 'error' in detail:
            errors += 1

        if (i + 1) % 50 == 0 or i == total - 1:
            print(f"  [{category_name}] {i+1}/{total} done, {errors} errors", flush=True)

        # Save progress every 200 items
        if (i + 1) % 200 == 0:
            save_progress(all_details)

        time.sleep(0.15)

    # Final save for this batch
    save_progress(all_details)


def main():
    # Load raw data
    with open(os.path.join(DATA_DIR, 'youku_movies_raw.json'), 'r', encoding='utf-8') as f:
        movies = json.load(f)
    with open(os.path.join(DATA_DIR, 'youku_tv_raw.json'), 'r', encoding='utf-8') as f:
        tv_dramas = json.load(f)

    print(f"Movies: {len(movies)}, TV Dramas: {len(tv_dramas)}", flush=True)

    # Check for existing progress
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            all_details = json.load(f)
        print(f"Resuming from {len(all_details)} existing details", flush=True)
    except FileNotFoundError:
        all_details = {}

    # Filter out already fetched
    movies_todo = [m for m in movies if m['showId'] not in all_details]
    tv_todo = [t for t in tv_dramas if t['showId'] not in all_details]
    print(f"Remaining: {len(movies_todo)} movies, {len(tv_todo)} TV dramas", flush=True)

    # Fetch movies
    if movies_todo:
        print(f"\nFetching movie details...", flush=True)
        process_batch(movies_todo, "电影", all_details)

    # Fetch TV dramas
    if tv_todo:
        print(f"\nFetching TV drama details...", flush=True)
        process_batch(tv_todo, "电视剧", all_details)

    # Filter out UGC compilations (mark=合辑) and UGC title patterns
    ugc_title_patterns = ['精华版', '（全集）', '(全集)', '精编版', '精剪版', '切片', '混剪']
    def is_ugc(item):
        if item.get('mark') == '合辑':
            return True
        title = item.get('title', '')
        return any(pat in title for pat in ugc_title_patterns)

    movies = [m for m in movies if not is_ugc(m)]
    tv_dramas = [t for t in tv_dramas if not is_ugc(t)]
    print(f"After UGC filter: {len(movies)} movies, {len(tv_dramas)} TV dramas", flush=True)

    # Generate final combined data
    enriched = {'movies': [], 'tvDramas': []}

    for item in movies:
        detail = all_details.get(item['showId'], {})
        enriched['movies'].append({
            'title': item['title'],
            'subtitle': item.get('subtitle', ''),
            'rating': item.get('summary', ''),
            'showId': item['showId'],
            'mark': item.get('mark', ''),
            'year': detail.get('year', ''),
            'region': detail.get('region', ''),
            'genre': detail.get('genre', ''),
            'actors': detail.get('actors', ''),
            'desc': detail.get('desc', ''),
            'episodes': '',
        })

    for item in tv_dramas:
        detail = all_details.get(item['showId'], {})
        episodes = item.get('summary', '')
        enriched['tvDramas'].append({
            'title': item['title'],
            'subtitle': item.get('subtitle', ''),
            'episodes': episodes,
            'showId': item['showId'],
            'mark': item.get('mark', ''),
            'year': detail.get('year', ''),
            'region': detail.get('region', ''),
            'genre': detail.get('genre', ''),
            'actors': detail.get('actors', ''),
            'desc': detail.get('desc', ''),
        })

    output_file = os.path.join(DATA_DIR, 'youku_details.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    # Stats
    m_ok = sum(1 for m in enriched['movies'] if m['year'])
    t_ok = sum(1 for t in enriched['tvDramas'] if t['year'])
    m_err = sum(1 for v in all_details.values() if 'error' in v)
    print(f"\nFinal: {len(enriched['movies'])} movies ({m_ok} with year), {len(enriched['tvDramas'])} TV ({t_ok} with year)", flush=True)
    print(f"Errors: {m_err}", flush=True)
    print(f"Saved to {output_file}", flush=True)


if __name__ == '__main__':
    main()
