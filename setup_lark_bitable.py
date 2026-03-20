#!/usr/bin/env python3
"""
GHA 客服数据 → Lark 多维表格一键建表 + 导入脚本

功能：
  1. 创建双语多维表格（字段名中英双语 + 下拉选项双语）
  2. 导入 records.csv 现有数据
  3. 将表格 token 写入 .lark_bitable_token（供后续同步脚本使用）

用法：
  python3 setup_lark_bitable.py
"""

import csv
import json
import os
import sys
import time
import requests
from datetime import datetime

# ── 配置 ──
APP_ID     = 'cli_a928c46386e19e1b'
APP_SECRET = 'g4aokTDTmXInQpIBUpLhFQNCDSgoIYjV'
BASE_URL   = 'https://open.larksuite.com/open-apis'
CSV_PATH   = os.path.join(os.path.dirname(__file__), 'records.csv')
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '.lark_bitable_token')

# ── 双语下拉选项 ──
CHANNEL_OPTIONS = [
    '微信 / WeChat',
    '小红书 / Xiaohongshu',
    '微信群 / WeChat Group',
    '电话 / Phone',
    '邮件 / Email',
    '其他 / Other',
]

PLATFORM_OPTIONS = [
    '微信小程序 / WeChat Mini Program',
    '中文小程序或官网 / CN Mini Program or Website',
    'GHA英文app / GHA English App',
    'GHA英文平台 / GHA English Platform',
    '全平台 / All Platforms',
    '其他 / Other',
]

CATEGORY_OPTIONS = [
    '技术bug / Technical Bug',
    '需求 / Feature Request',
    '客服 / Customer Service',
    '功能 / Function',
    '价格优势 / Price Competitiveness',
    '会员权益反馈 / Membership Benefits',
    '酒店规则和数据不一致 / Data Inconsistency',
    '其他 / Other',
]

STATUS_OPTIONS = [
    '已解决 / Resolved',
    '处理中 / In Progress',
    '待处理 / Pending',
    '已升级 / Escalated',
]

# ── 旧值 → 双语值 映射 ──
CHANNEL_MAP = {
    '微信': '微信 / WeChat',
    '小红书': '小红书 / Xiaohongshu',
    '微信群': '微信群 / WeChat Group',
    '电话': '电话 / Phone',
    '邮件': '邮件 / Email',
    '其他': '其他 / Other',
}

PLATFORM_MAP = {
    '微信小程序': '微信小程序 / WeChat Mini Program',
    '中文小程序或官网': '中文小程序或官网 / CN Mini Program or Website',
    'GHA英文app': 'GHA英文app / GHA English App',
    'GHA英文平台': 'GHA英文平台 / GHA English Platform',
    '英文app': 'GHA英文app / GHA English App',
    '全平台': '全平台 / All Platforms',
    '其他': '其他 / Other',
}

CATEGORY_MAP = {
    '技术bug': '技术bug / Technical Bug',
    '需求': '需求 / Feature Request',
    '客服': '客服 / Customer Service',
    '功能': '功能 / Function',
    '价格优势': '价格优势 / Price Competitiveness',
    '会员权益反馈': '会员权益反馈 / Membership Benefits',
    '酒店规则和数据不一致': '酒店规则和数据不一致 / Data Inconsistency',
    '其他': '其他 / Other',
}

STATUS_MAP = {
    '已解决': '已解决 / Resolved',
    '处理中': '处理中 / In Progress',
    '待处理': '待处理 / Pending',
    '已升级': '已升级 / Escalated',
}


# ── API 工具函数 ──
def get_token():
    resp = requests.post(f'{BASE_URL}/auth/v3/app_access_token/internal',
                         json={'app_id': APP_ID, 'app_secret': APP_SECRET})
    data = resp.json()
    if data.get('code') != 0:
        print(f'❌ 获取 Token 失败: {data}')
        sys.exit(1)
    return data['app_access_token']


def api(token, method, path, **kwargs):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    resp = requests.request(method, f'{BASE_URL}{path}', headers=headers, **kwargs)
    return resp.json()


# ── 建表 ──
def create_bitable(token):
    data = api(token, 'POST', '/bitable/v1/apps',
               json={'name': 'GHA 客服数据 / Customer Service Records'})
    if data.get('code') != 0:
        print(f'❌ 创建多维表格失败: {data}')
        sys.exit(1)
    app_token = data['data']['app']['app_token']
    print(f'✅ 多维表格已创建  app_token: {app_token}')
    return app_token


def get_default_table(token, app_token):
    data = api(token, 'GET', f'/bitable/v1/apps/{app_token}/tables')
    table_id = data['data']['items'][0]['table_id']
    print(f'✅ 默认表格  table_id: {table_id}')
    return table_id


def get_default_field_id(token, app_token, table_id):
    """获取默认 Title 字段 ID，用于重命名"""
    data = api(token, 'GET', f'/bitable/v1/apps/{app_token}/tables/{table_id}/fields')
    fields = data['data']['items']
    return fields[0]['field_id'] if fields else None


def rename_title_field(token, app_token, table_id, field_id):
    api(token, 'PUT',
        f'/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}',
        json={'field_name': '标题 / Title', 'type': 1})
    print('  ✅ 标题 / Title（默认字段已重命名）')


def make_select(name, options):
    return {
        'field_name': name,
        'type': 3,
        'property': {'options': [{'name': o} for o in options]},
    }


def setup_fields(token, app_token, table_id):
    fields = [
        {'field_name': 'ID', 'type': 2},
        {'field_name': '日期 / Date', 'type': 5,
         'property': {'date_formatter': 'yyyy/MM/dd'}},
        {'field_name': '时间 / Time', 'type': 1},
        make_select('渠道 / Channel', CHANNEL_OPTIONS),
        make_select('平台 / Platform', PLATFORM_OPTIONS),
        make_select('问题类别 / Category', CATEGORY_OPTIONS),
        {'field_name': '子类别 / Subcategory (CN)', 'type': 1},
        {'field_name': 'Subcategory (EN)', 'type': 1},
        {'field_name': '关键词 / Keywords (CN)', 'type': 1},
        {'field_name': 'Keywords (EN)', 'type': 1},
        {'field_name': '描述 / Description (CN)', 'type': 1},
        {'field_name': 'Description (EN)', 'type': 1},
        make_select('处理状态 / Status', STATUS_OPTIONS),
        {'field_name': '负责人 / Assignee', 'type': 1},
        {'field_name': '备注 / Notes (CN)', 'type': 1},
        {'field_name': 'Notes (EN)', 'type': 1},
    ]
    for f in fields:
        data = api(token, 'POST',
                   f'/bitable/v1/apps/{app_token}/tables/{table_id}/fields',
                   json=f)
        if data.get('code') != 0:
            print(f'  ⚠️  {f["field_name"]} 创建失败: {data.get("msg")}')
        else:
            print(f'  ✅ {f["field_name"]}')
        time.sleep(0.15)


# ── 数据导入 ──
def to_date_ts(date_str):
    if not date_str or not date_str.strip():
        return None
    try:
        return int(datetime.strptime(date_str.strip(), '%Y-%m-%d').timestamp() * 1000)
    except Exception:
        return None


def build_records(rows):
    records = []
    for row in rows:
        rid = row.get('id', '').strip()
        if not rid:
            continue

        channel  = CHANNEL_MAP.get(row.get('channel', '').strip(),  row.get('channel', ''))
        platform = PLATFORM_MAP.get(row.get('platform', '').strip(), row.get('platform', ''))
        category = CATEGORY_MAP.get(row.get('category', '').strip(), row.get('category', ''))
        status   = STATUS_MAP.get(row.get('status', '').strip(),   row.get('status', ''))
        date_ts  = to_date_ts(row.get('date', ''))

        fields = {
            '标题 / Title': f'#{rid}',
        }

        if rid.isdigit():
            fields['ID'] = int(rid)
        if date_ts:
            fields['日期 / Date'] = date_ts
        if row.get('time', '').strip():
            fields['时间 / Time'] = row['time'].strip()
        if channel:
            fields['渠道 / Channel'] = channel
        if platform:
            fields['平台 / Platform'] = platform
        if category:
            fields['问题类别 / Category'] = category
        if row.get('subcategory', '').strip():
            fields['子类别 / Subcategory (CN)'] = row['subcategory'].strip()
        if row.get('keywords', '').strip():
            fields['关键词 / Keywords (CN)'] = row['keywords'].strip()
        if row.get('description', '').strip():
            fields['描述 / Description (CN)'] = row['description'].strip()
        if status:
            fields['处理状态 / Status'] = status
        if row.get('assignee', '').strip():
            fields['负责人 / Assignee'] = row['assignee'].strip()
        if row.get('notes', '').strip():
            fields['备注 / Notes (CN)'] = row['notes'].strip()

        records.append({'fields': fields})
    return records


def import_records(token, app_token, table_id, records):
    BATCH = 500
    total = 0
    for i in range(0, len(records), BATCH):
        batch = records[i:i + BATCH]
        data = api(token, 'POST',
                   f'/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create',
                   json={'records': batch})
        if data.get('code') != 0:
            print(f'❌ 导入失败: {data.get("msg")}')
        else:
            total += len(batch)
            print(f'  ✅ 已导入 {total}/{len(records)} 条')
        time.sleep(0.3)


# ── 主流程 ──
if __name__ == '__main__':
    print('🚀 开始创建 GHA 客服多维表格...\n')

    token = get_token()
    print(f'✅ Token 获取成功\n')

    app_token = create_bitable(token)
    time.sleep(1)

    table_id = get_default_table(token, app_token)
    time.sleep(0.5)

    # 重命名默认 Title 字段
    default_fid = get_default_field_id(token, app_token, table_id)
    print('\n📋 配置双语字段...')
    if default_fid:
        rename_title_field(token, app_token, table_id, default_fid)
        time.sleep(0.2)

    setup_fields(token, app_token, table_id)
    time.sleep(0.5)

    print('\n📥 导入数据...')
    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    records = build_records(rows)
    print(f'  共 {len(records)} 条记录')
    import_records(token, app_token, table_id, records)

    # 保存 token 供后续脚本使用
    with open(TOKEN_FILE, 'w') as f:
        json.dump({'app_token': app_token, 'table_id': table_id}, f)
    print(f'\n✅ 完成！配置已保存至 .lark_bitable_token')
    print(f'🔗 表格链接：https://ujpie70e7wvs.jp.larksuite.com/base/{app_token}')
