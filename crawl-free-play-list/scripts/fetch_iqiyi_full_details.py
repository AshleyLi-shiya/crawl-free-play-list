#!/usr/bin/env python3
"""
Re-fetch iQIYI TV dramas with full fields (actors, year, region, episodes),
and re-fetch movies with full fields too, then combine everything into a detail Excel.
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
    'Accept': 'application/json',
    'Referer': 'https://www.iqiyi.com/',
    'Origin': 'https://www.iqiyi.com',
}

BASE_URL = 'https://mesh.if.iqiyi.com/portal/lw/videolib/data'

# Region tags from iQIYI
REGION_TAGS = {'内地', '中国香港', '中国台湾', '美国', '韩国', '日本', '欧洲', '印度', '泰国',
               '丹麦', '英国', '法国', '德国', '意大利', '西班牙', '加拿大', '澳大利亚',
               '俄罗斯', '巴西', '墨西哥', '马来西亚', '新加坡', '菲律宾', '越南', '朝鲜',
               '伊朗', '土耳其', '以色列', '阿根廷', '瑞典', '挪威', '荷兰', '比利时',
               '波兰', '捷克', '匈牙利', '奥地利', '瑞士', '芬兰', '爱尔兰', '新西兰',
               '南非', '埃及', '尼日利亚', '肯尼亚', '哥伦比亚', '智利', '秘鲁'}

# Genre tags (exclude region, language, production tags)
SKIP_TAGS = {'普通话', '粤语', '国语', '英语', '日语', '韩语', '独播', '网络电影', '原创',
             '自制', '文学改编', '当代', '院线', 'VIP', '付费', '免费'}


def fetch_page(channel_id, filter_dict, page_id=1, session=''):
    params = {
        'uid': '', 'passport_id': '', 'ret_num': '60',
        'pcv': '17.032.24766', 'version': '17.032.24766',
        'device_id': '9b41ee32883e04ea763ab16a4b4f5d1e',
        'channel_id': str(channel_id), 'page_id': str(page_id),
        'session': session, 'token': '', 'os': '',
        'conduit_id': '', 'vip': '0', 'auth': '',
        'recent_selected_tag': '',
        'filter': json.dumps(filter_dict),
    }
    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
    return resp.json()


def extract_full_item(raw, category):
    """Extract all useful fields from a raw API item."""
    title = raw.get('title', '')
    
    # Skip episode entries like "逐玉第8集"
    if re.search(r'第\d+集', title):
        return None
    
    # Tags -> split into genre, region
    tag_raw = raw.get('tag', '')
    tags = [t.strip() for t in tag_raw.split(';') if t.strip()] if tag_raw else []
    
    regions = [t for t in tags if t in REGION_TAGS]
    genres = [t for t in tags if t not in REGION_TAGS and t not in SKIP_TAGS]
    
    # Contributors (actors)
    contributors = raw.get('contributor', [])
    actors = ','.join([c.get('name', '') for c in contributors if isinstance(c, dict) and c.get('name')]) if contributors else ''
    
    # Date/year
    date_obj = raw.get('date', {})
    year = ''
    if isinstance(date_obj, dict) and date_obj.get('year'):
        year = str(date_obj['year'])
    
    # Episodes
    episodes = ''
    dq = raw.get('dq_updatestatus', '')
    if dq:
        episodes = dq
    elif raw.get('current_period'):
        episodes = str(raw['current_period'])
    
    return {
        'title': title,
        'year': year,
        'actors': actors,
        'region': ','.join(regions) if regions else '',
        'genre': ','.join(genres[:6]) if genres else '',
        'episodes': episodes,
        'description': raw.get('description', ''),
        'score': raw.get('sns_score', 0) or raw.get('hot_score', 0),
        'entity_id': raw.get('entity_id', 0),
        'album_id': raw.get('album_id', 0),
    }


def fetch_all_iqiyi(channel_id, filter_dict, label, extra_filters=None):
    """Fetch all items with full fields, using genre-split for large datasets."""
    all_items = {}
    
    def _fetch_batch(filt, batch_label):
        page = 1
        session = ''
        while True:
            try:
                data = fetch_page(channel_id, filt, page, session)
            except Exception as e:
                print(f"    Page {page} error: {e}")
                time.sleep(2)
                try:
                    data = fetch_page(channel_id, filt, page, session)
                except:
                    break
            
            if data.get('code') != 0:
                break
            
            items = data.get('data', [])
            has_next = data.get('has_next', 0)
            session = data.get('session', session)
            
            if page == 1:
                ext = data.get('extension', {})
                max_r = ext.get('max_result_num', 0)
                fetch_r = ext.get('result_num', 0)
                print(f"  [{batch_label}] max={max_r}, fetchable={fetch_r}")
            
            new_count = 0
            for raw in items:
                item = extract_full_item(raw, label)
                if item is None:
                    continue
                eid = item['entity_id'] or item['title']
                if eid not in all_items:
                    all_items[eid] = item
                    new_count += 1
            
            if not has_next or not items:
                break
            page += 1
            time.sleep(0.15)
            if page > 50:
                break
        
        print(f"  [{batch_label}] total unique so far: {len(all_items)}")
    
    # Base queries with 3 sort modes
    for mode_name, mode_val in [('最热', '11'), ('最新', '4'), ('高分', '8')]:
        filt = {**filter_dict, 'mode': mode_val}
        _fetch_batch(filt, f"{label}-{mode_name}")
        time.sleep(0.3)
    
    # If extra genre filters provided, also query those
    if extra_filters:
        for ef_name, ef_dict in extra_filters:
            filt = {**filter_dict, **ef_dict, 'mode': '11'}
            _fetch_batch(filt, f"{label}-{ef_name}")
            time.sleep(0.2)
    
    return list(all_items.values())


def main():
    # === iQIYI TV Dramas (channel_id=2) ===
    print("=" * 60)
    print("Fetching iQIYI TV dramas with full fields")
    print("=" * 60)
    
    tv_dramas = fetch_all_iqiyi(2, {"is_purchase": "0"}, "电视剧")
    print(f"\nTotal iQIYI TV dramas: {len(tv_dramas)}")
    
    # === iQIYI Movies (channel_id=1) with genre split ===
    print("\n" + "=" * 60)
    print("Fetching iQIYI movies with full fields (genre-split)")
    print("=" * 60)
    
    GENRES = [
        ('动作', {'three_category_id_v2': '7086834452347833'}),
        ('悬疑', {'three_category_id_v2': '5836257895783433'}),
        ('家庭', {'three_category_id_v2': '2375714428805633'}),
        ('青春', {'three_category_id_v2': '8902937931540733'}),
        ('犯罪', {'three_category_id_v2': '7655570038367133'}),
        ('冒险', {'three_category_id_v2': '2094956382110833'}),
        ('惊悚', {'three_category_id_v2': '8391958286555633'}),
        ('历史', {'three_category_id_v2': '7174270529747133'}),
        ('奇幻', {'three_category_id_v2': '8035796650176933'}),
        ('战争', {'three_category_id_v2': '4705204050526533'}),
        ('武侠', {'three_category_id_v2': '7045121828267433'}),
        ('警匪', {'three_category_id_v2': '7245663290192433'}),
        ('科幻', {'three_category_id_v2': '2771984357569433'}),
        ('伦理', {'three_category_id_v2': '6015140879820833'}),
        ('少儿', {'three_category_id_v2': '2679735285084233'}),
        ('枪战', {'three_category_id_v2': '8201844980650933'}),
        ('恐怖', {'three_category_id_v2': '7128547076428333'}),
        ('玄幻', {'three_category_id_v2': '2951669507454533'}),
        ('戏曲', {'three_category_id_v2': '8795447707948733'}),
        ('运动', {'three_category_id_v2': '3341522109436533'}),
        ('动画', {'three_category_id_v2': '7821618368840933'}),
        ('音乐', {'three_category_id_v2': '1247067081091833'}),
        ('传记', {'three_category_id_v2': '5002807580023233'}),
        ('歌舞', {'three_category_id_v2': '3567732878487833'}),
        ('灾难', {'three_category_id_v2': '3281359670859033'}),
        ('悲剧', {'three_category_id_v2': '5156021256933833'}),
        ('魔幻', {'three_category_id_v2': '4150907449765833'}),
        ('西部', {'three_category_id_v2': '3727363882180333'}),
        ('史诗', {'three_category_id_v2': '7455830742289933'}),
        ('其他', {'three_category_id_v2': '1535330033'}),
        ('喜剧', {'three_category_id_v2': '3842875764248933'}),
        ('爱情', {'three_category_id_v2': '8732878771828133'}),
        ('剧情', {'three_category_id_v2': '3797954476777933'}),
    ]
    
    movies = fetch_all_iqiyi(1, {"is_purchase": "0"}, "电影", extra_filters=GENRES)
    print(f"\nTotal iQIYI movies: {len(movies)}")
    
    # Save
    output = {
        'tvDramas': tv_dramas,
        'movies': movies,
    }
    outpath = os.path.join(DATA_DIR, 'iqiyi_full_details.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved to: {outpath}")
    
    # Show samples
    if tv_dramas:
        d = tv_dramas[0]
        print(f"\nTV drama sample: {d['title']} | {d['year']} | {d['actors'][:50]} | {d['region']} | {d['episodes']} | {d['genre']}")
    if movies:
        m = movies[0]
        print(f"Movie sample: {m['title']} | {m['year']} | {m['actors'][:50]} | {m['region']} | {m['genre']}")


if __name__ == '__main__':
    main()
