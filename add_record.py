#!/usr/bin/env python3
"""
GHA 客服数据录入工具（支持同步到 Lark 多维表格）

用法:
  python3 add_record.py --channel "微信" --category "技术bug" \
      --description "问题描述" --description_en "Issue description" \
      --status "已解决" --notes "处理备注" --notes_en "Resolution notes"

完整参数见 --help
"""

import csv
import argparse
import json
import os
import time
import requests
from datetime import datetime

CSV_PATH   = os.path.join(os.path.dirname(__file__), 'records.csv')
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '.lark_bitable_token')

APP_ID     = 'cli_a928c46386e19e1b'
APP_SECRET = 'g4aokTDTmXInQpIBUpLhFQNCDSgoIYjV'
BASE_URL   = 'https://open.larksuite.com/open-apis'

CHANNELS   = ['微信', '小红书', '微信群', '电话', '邮件', '其他']
PLATFORMS  = ['微信小程序', '中文小程序或官网', 'GHA英文app', 'GHA英文平台', '全平台', '其他']
CATEGORIES = ['技术bug', '需求', '客服', '功能', '价格优势', '会员权益反馈', '酒店规则和数据不一致', '其他']
STATUSES   = ['已解决', '处理中', '待处理', '已升级']

CHANNEL_MAP = {
    '微信': '微信 / WeChat', '小红书': '小红书 / Xiaohongshu',
    '微信群': '微信群 / WeChat Group', '电话': '电话 / Phone',
    '邮件': '邮件 / Email', '其他': '其他 / Other',
}
PLATFORM_MAP = {
    '微信小程序': '微信小程序 / WeChat Mini Program',
    '中文小程序或官网': '中文小程序或官网 / CN Mini Program or Website',
    'GHA英文app': 'GHA英文app / GHA English App',
    'GHA英文平台': 'GHA英文平台 / GHA English Platform',
    '全平台': '全平台 / All Platforms', '其他': '其他 / Other',
}
CATEGORY_MAP = {
    '技术bug': '技术bug / Technical Bug', '需求': '需求 / Feature Request',
    '客服': '客服 / Customer Service', '功能': '功能 / Function',
    '价格优势': '价格优势 / Price Competitiveness',
    '会员权益反馈': '会员权益反馈 / Membership Benefits',
    '酒店规则和数据不一致': '酒店规则和数据不一致 / Data Inconsistency',
    '其他': '其他 / Other',
}
STATUS_MAP = {
    '已解决': '已解决 / Resolved', '处理中': '处理中 / In Progress',
    '待处理': '待处理 / Pending', '已升级': '已升级 / Escalated',
}


# ── CSV 操作 ──
def get_next_id():
    if not os.path.exists(CSV_PATH):
        return 1
    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return 1
    return max((int(r['id']) for r in rows if r.get('id', '').isdigit()), default=0) + 1


def write_csv(row):
    file_exists = os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0
    with open(CSV_PATH, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ── Lark 操作 ──
def get_lark_token():
    resp = requests.post(f'{BASE_URL}/auth/v3/app_access_token/internal',
                         json={'app_id': APP_ID, 'app_secret': APP_SECRET}, timeout=10)
    data = resp.json()
    return data.get('app_access_token')


def sync_to_lark(record):
    if not os.path.exists(TOKEN_FILE):
        print('⚠️  未找到 .lark_bitable_token，跳过 Lark 同步（请先运行 setup_lark_bitable.py）')
        return

    with open(TOKEN_FILE) as f:
        cfg = json.load(f)
    app_token = cfg['app_token']
    table_id  = cfg['table_id']

    token = get_lark_token()
    if not token:
        print('⚠️  Lark Token 获取失败，跳过同步')
        return

    date_ts = None
    try:
        date_ts = int(datetime.strptime(record['date'], '%Y-%m-%d').timestamp() * 1000)
    except Exception:
        pass

    fields = {'标题 / Title': f'#{record["id"]}'}
    if str(record['id']).isdigit():
        fields['ID'] = int(record['id'])
    if date_ts:
        fields['日期 / Date'] = date_ts
    if record.get('time'):
        fields['时间 / Time'] = record['time']
    if record.get('channel'):
        fields['渠道 / Channel'] = CHANNEL_MAP.get(record['channel'], record['channel'])
    if record.get('platform'):
        fields['平台 / Platform'] = PLATFORM_MAP.get(record['platform'], record['platform'])
    if record.get('category'):
        fields['问题类别 / Category'] = CATEGORY_MAP.get(record['category'], record['category'])
    if record.get('subcategory'):
        fields['子类别 / Subcategory (CN)'] = record['subcategory']
    if record.get('subcategory_en'):
        fields['Subcategory (EN)'] = record['subcategory_en']
    if record.get('keywords'):
        fields['关键词 / Keywords (CN)'] = record['keywords']
    if record.get('keywords_en'):
        fields['Keywords (EN)'] = record['keywords_en']
    if record.get('description'):
        fields['描述 / Description (CN)'] = record['description']
    if record.get('description_en'):
        fields['Description (EN)'] = record['description_en']
    if record.get('status'):
        fields['处理状态 / Status'] = STATUS_MAP.get(record['status'], record['status'])
    if record.get('assignee'):
        fields['负责人 / Assignee'] = record['assignee']
    if record.get('notes'):
        fields['备注 / Notes (CN)'] = record['notes']
    if record.get('notes_en'):
        fields['Notes (EN)'] = record['notes_en']

    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    resp = requests.post(
        f'{BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records',
        headers=headers, json={'fields': fields}, timeout=10
    )
    result = resp.json()
    if result.get('code') == 0:
        print('✅ 已同步至 Lark 多维表格')
    else:
        print(f'⚠️  Lark 同步失败: {result.get("msg")}')


# ── 主函数 ──
def add_record(date, time_, channel, platform, category, subcategory, subcategory_en,
               keywords, keywords_en, description, description_en,
               status, assignee, notes, notes_en):
    next_id = get_next_id()
    row = {
        'id': next_id, 'date': date, 'time': time_,
        'channel': channel, 'platform': platform,
        'category': category, 'subcategory': subcategory,
        'keywords': keywords, 'description': description,
        'status': status, 'assignee': assignee, 'notes': notes,
    }
    write_csv(row)
    print(f'✅ CSV 已录入  ID={next_id} | {date} | {channel} | {category} | {status}')

    # 补充英文字段供 Lark 同步
    row.update({
        'subcategory_en': subcategory_en, 'keywords_en': keywords_en,
        'description_en': description_en, 'notes_en': notes_en,
    })
    sync_to_lark(row)
    return next_id


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='添加客服记录（同步至 Lark）')
    p.add_argument('--date',           default=datetime.now().strftime('%Y-%m-%d'))
    p.add_argument('--time',           default=datetime.now().strftime('%H:%M'))
    p.add_argument('--channel',        required=True, choices=CHANNELS)
    p.add_argument('--platform',       default='', choices=PLATFORMS + [''])
    p.add_argument('--category',       required=True, choices=CATEGORIES)
    p.add_argument('--subcategory',    default='')
    p.add_argument('--subcategory_en', default='')
    p.add_argument('--keywords',       default='')
    p.add_argument('--keywords_en',    default='')
    p.add_argument('--description',    default='')
    p.add_argument('--description_en', default='')
    p.add_argument('--status',         default='已解决', choices=STATUSES)
    p.add_argument('--assignee',       default='')
    p.add_argument('--notes',          default='')
    p.add_argument('--notes_en',       default='')
    args = p.parse_args()

    add_record(
        date=args.date, time_=args.time,
        channel=args.channel, platform=args.platform,
        category=args.category,
        subcategory=args.subcategory, subcategory_en=args.subcategory_en,
        keywords=args.keywords, keywords_en=args.keywords_en,
        description=args.description, description_en=args.description_en,
        status=args.status, assignee=args.assignee,
        notes=args.notes, notes_en=args.notes_en,
    )
