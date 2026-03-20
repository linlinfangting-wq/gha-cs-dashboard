#!/usr/bin/env python3
"""
GHA 客服数据 Dashboard
Streamlit + Plotly，实时读取 Lark 多维表格

本地运行：streamlit run dashboard.py
"""

import json
import os
from collections import Counter
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ── 配置（从 Streamlit secrets 读取，本地和云端通用）──
def _secret(key, fallback=''):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, fallback)

APP_ID     = _secret('LARK_APP_ID')
APP_SECRET = _secret('LARK_APP_SECRET')
APP_TOKEN  = _secret('LARK_APP_TOKEN')
TABLE_ID   = _secret('LARK_TABLE_ID')
BASE_URL   = 'https://open.larksuite.com/open-apis'

# ── 品牌色 ──
GOLD   = '#DA9F59'
NAVY   = '#141432'
BLUE   = '#8BBCD9'
CORAL  = '#F69B6F'
GREEN  = '#5D8C6A'
PURPLE = '#300B5C'
PALETTE = [GOLD, BLUE, CORAL, GREEN, PURPLE, '#B7CBD5', '#C4A882', '#7A9898', '#E8C880', '#9090B8']

STATUS_COLOR = {
    '已解决 / Resolved':   GREEN,
    '处理中 / In Progress': GOLD,
    '待处理 / Pending':     BLUE,
    '已升级 / Escalated':   CORAL,
}

# ── 页面配置 ──
st.set_page_config(
    page_title='GHA 客服数据 Dashboard',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

st.markdown(f"""
<style>
  .main {{ background-color: #F9F9F7; }}
  .block-container {{ padding-top: 1.5rem; }}
  .metric-card {{
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    border-left: 4px solid {GOLD};
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
  }}
  .metric-value {{ font-size: 2.2rem; font-weight: 700; color: {NAVY}; line-height: 1.1; }}
  .metric-label {{ font-size: 0.82rem; color: #888; margin-top: 4px; }}
  h1, h2, h3 {{ color: {NAVY}; }}
  .section-title {{
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
    color: #aaa; text-transform: uppercase; margin-bottom: 8px;
  }}
</style>
""", unsafe_allow_html=True)


# ── Lark 数据加载 ──
def extract(value):
    if value is None:
        return ''
    if isinstance(value, dict):
        return value.get('text', '')
    if isinstance(value, list):
        return ' '.join(i.get('text', '') for i in value if isinstance(i, dict))
    return str(value) if value != '' else ''


def _get_token():
    r = requests.post(f'{BASE_URL}/auth/v3/app_access_token/internal',
                      json={'app_id': APP_ID, 'app_secret': APP_SECRET}, timeout=10)
    data = r.json()
    if data.get('code') != 0:
        raise RuntimeError(f'Lark 鉴权失败: {data.get("msg")}')
    return data['app_access_token']


@st.cache_data(ttl=300, show_spinner='正在读取 Lark 数据...')
def load_data():
    token = _get_token()
    app_token, table_id = APP_TOKEN, TABLE_ID
    headers = {'Authorization': f'Bearer {token}'}
    rows, page_token = [], None

    while True:
        params = {'page_size': 500}
        if page_token:
            params['page_token'] = page_token
        raw = requests.get(
            f'{BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records',
            headers=headers, params=params, timeout=15,
        )
        resp = raw.json()
        if resp.get('code') != 0:
            raise RuntimeError(f'Lark API 错误: {resp.get("msg")}')

        for item in resp['data']['items']:
            fld = item['fields']
            date_ts = fld.get('日期 / Date')
            date_str = (datetime.fromtimestamp(date_ts / 1000).strftime('%Y-%m-%d')
                        if date_ts else '')
            rows.append({
                'id':          extract(fld.get('ID', '')),
                'date':        date_str,
                'channel':     extract(fld.get('渠道 / Channel', '')),
                'platform':    extract(fld.get('平台 / Platform', '')),
                'category':    extract(fld.get('问题类别 / Category', '')),
                'subcategory': extract(fld.get('子类别 / Subcategory (CN)', '')),
                'keywords':    extract(fld.get('关键词 / Keywords (CN)', '')),
                'description': extract(fld.get('描述 / Description (CN)', '')),
                'status':      extract(fld.get('处理状态 / Status', '')),
                'assignee':    extract(fld.get('负责人 / Assignee', '')),
                'notes':       extract(fld.get('备注 / Notes (CN)', '')),
            })

        if not resp['data'].get('has_more'):
            break
        page_token = resp['data'].get('page_token')

    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    return df


# ── 主界面 ──
st.markdown(f'<h1 style="margin-bottom:0">GHA 客服数据 <span style="color:{GOLD}">Dashboard</span></h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#aaa;margin-top:2px;margin-bottom:1.5rem">Customer Service Analytics · GHA Discovery</p>', unsafe_allow_html=True)

try:
    df_raw = load_data()
except Exception as e:
    st.error(f'数据加载失败: {e}')
    st.stop()

if df_raw.empty:
    st.warning('暂无数据')
    st.stop()

# ── 侧边栏筛选器 ──
with st.sidebar:
    st.markdown(f'### 筛选 / Filter')

    # 日期范围
    valid_dates = df_raw['date'].dropna()
    min_d = valid_dates.min().date() if not valid_dates.empty else None
    max_d = valid_dates.max().date() if not valid_dates.empty else None
    if min_d and max_d:
        date_range = st.date_input('日期范围 / Date Range', value=(min_d, max_d),
                                   min_value=min_d, max_value=max_d)
    else:
        date_range = None

    # 渠道
    channels = ['全部 / All'] + sorted(df_raw['channel'].dropna().unique().tolist())
    sel_channel = st.multiselect('渠道 / Channel', channels[1:], default=[])

    # 类别
    categories = sorted(df_raw['category'].dropna().unique().tolist())
    sel_category = st.multiselect('问题类别 / Category', categories, default=[])

    # 状态
    statuses = sorted(df_raw['status'].dropna().unique().tolist())
    sel_status = st.multiselect('处理状态 / Status', statuses, default=[])

    st.markdown('---')
    if st.button('🔄 刷新数据 / Refresh'):
        st.cache_data.clear()
        st.rerun()

# ── 应用筛选 ──
df = df_raw.copy()
if date_range and len(date_range) == 2:
    df = df[(df['date'].dt.date >= date_range[0]) & (df['date'].dt.date <= date_range[1])]
if sel_channel:
    df = df[df['channel'].isin(sel_channel)]
if sel_category:
    df = df[df['category'].isin(sel_category)]
if sel_status:
    df = df[df['status'].isin(sel_status)]

if df.empty:
    st.warning('当前筛选条件下无数据')
    st.stop()

# ── KPI 卡片 ──
total     = len(df)
resolved  = len(df[df['status'].str.contains('Resolved|已解决', na=False)])
pending   = len(df[df['status'].str.contains('Pending|待处理', na=False)])
escalated = len(df[df['status'].str.contains('Escalated|已升级', na=False)])
resolve_rate = f'{resolved / total * 100:.1f}%' if total else '—'

c1, c2, c3, c4 = st.columns(4)
for col, val, label in [
    (c1, total,        '总咨询量<br><small>Total Inquiries</small>'),
    (c2, resolved,     f'已解决<br><small>Resolved · {resolve_rate}</small>'),
    (c3, pending,      '待处理<br><small>Pending</small>'),
    (c4, escalated,    '已升级<br><small>Escalated</small>'),
]:
    col.markdown(f'''
    <div class="metric-card">
      <div class="metric-value">{val}</div>
      <div class="metric-label">{label}</div>
    </div>
    ''', unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)

# ── 图表行 1：类别 + 渠道 ──
col_a, col_b = st.columns([3, 2])

with col_a:
    st.markdown('<div class="section-title">问题类别分布 · Category Distribution</div>', unsafe_allow_html=True)
    cat_counts = df['category'].value_counts().reset_index()
    cat_counts.columns = ['category', 'count']
    fig1 = px.bar(cat_counts, x='count', y='category', orientation='h',
                  color='count', color_continuous_scale=[[0, BLUE], [1, GOLD]],
                  text='count')
    fig1.update_traces(textposition='outside', marker_line_width=0)
    fig1.update_layout(
        coloraxis_showscale=False, plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=0, r=30, t=10, b=0), height=320,
        yaxis=dict(title='', tickfont=dict(size=12)),
        xaxis=dict(title='咨询量', showgrid=True, gridcolor='#f0f0f0'),
    )
    st.plotly_chart(fig1, use_container_width=True)

with col_b:
    st.markdown('<div class="section-title">渠道来源 · Channel Source</div>', unsafe_allow_html=True)
    ch_counts = df['channel'].value_counts().reset_index()
    ch_counts.columns = ['channel', 'count']
    fig2 = go.Figure(go.Pie(
        labels=ch_counts['channel'], values=ch_counts['count'],
        hole=0.55, marker_colors=PALETTE[:len(ch_counts)],
        textinfo='label+percent', textfont_size=11,
        hovertemplate='%{label}<br>%{value} 条 (%{percent})<extra></extra>',
    ))
    fig2.update_layout(
        showlegend=False, paper_bgcolor='white',
        margin=dict(l=0, r=0, t=10, b=0), height=320,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── 图表行 2：处理状态 + 每日趋势 ──
col_c, col_d = st.columns([2, 3])

with col_c:
    st.markdown('<div class="section-title">处理状态 · Status</div>', unsafe_allow_html=True)
    st_counts = df['status'].value_counts().reset_index()
    st_counts.columns = ['status', 'count']
    colors = [STATUS_COLOR.get(s, NAVY) for s in st_counts['status']]
    fig3 = go.Figure(go.Bar(
        x=st_counts['status'], y=st_counts['count'],
        marker_color=colors, text=st_counts['count'],
        textposition='outside',
    ))
    fig3.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=0, r=0, t=10, b=60), height=320,
        xaxis=dict(tickangle=-20, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
        showlegend=False,
    )
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    st.markdown('<div class="section-title">每月咨询量趋势 · Monthly Trend</div>', unsafe_allow_html=True)
    df_trend = df.dropna(subset=['date']).copy()
    df_trend['month'] = df_trend['date'].dt.to_period('M').astype(str)
    monthly = df_trend.groupby('month').size().reset_index(name='count')
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=monthly['month'], y=monthly['count'],
        mode='lines+markers+text', text=monthly['count'],
        textposition='top center', line=dict(color=GOLD, width=2.5),
        marker=dict(color=GOLD, size=8),
        fill='tozeroy', fillcolor='rgba(218,159,89,0.08)',
    ))
    fig4.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=0, r=0, t=10, b=0), height=320,
        xaxis=dict(showgrid=False, tickangle=-20),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title='咨询量'),
    )
    st.plotly_chart(fig4, use_container_width=True)

# ── 图表行 3：平台 + 关键词 ──
col_e, col_f = st.columns(2)

with col_e:
    st.markdown('<div class="section-title">平台分布 · Platform</div>', unsafe_allow_html=True)
    pl_counts = df[df['platform'] != ''].groupby('platform').size().reset_index(name='count')
    pl_counts = pl_counts.sort_values('count', ascending=True)
    fig5 = px.bar(pl_counts, x='count', y='platform', orientation='h',
                  color_discrete_sequence=[PURPLE], text='count')
    fig5.update_traces(textposition='outside')
    fig5.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=0, r=30, t=10, b=0), height=280,
        yaxis=dict(title='', tickfont=dict(size=11)),
        xaxis=dict(title='', showgrid=True, gridcolor='#f0f0f0'),
    )
    st.plotly_chart(fig5, use_container_width=True)

with col_f:
    st.markdown('<div class="section-title">高频关键词 Top 10 · Keywords</div>', unsafe_allow_html=True)
    all_kw = []
    for kw_str in df['keywords'].dropna():
        all_kw.extend([k.strip() for k in str(kw_str).split(',') if k.strip()])
    if all_kw:
        top_kw = Counter(all_kw).most_common(10)
        kw_df = pd.DataFrame(top_kw, columns=['keyword', 'count']).sort_values('count')
        fig6 = px.bar(kw_df, x='count', y='keyword', orientation='h',
                      color_discrete_sequence=[BLUE], text='count')
        fig6.update_traces(textposition='outside')
        fig6.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            margin=dict(l=0, r=30, t=10, b=0), height=280,
            yaxis=dict(title='', tickfont=dict(size=11)),
            xaxis=dict(title='', showgrid=True, gridcolor='#f0f0f0'),
        )
        st.plotly_chart(fig6, use_container_width=True)
    else:
        st.info('暂无关键词数据')

# ── 数据明细 ──
st.markdown('---')
st.markdown('<div class="section-title">数据明细 · Records</div>', unsafe_allow_html=True)

display_df = df[['id', 'date', 'channel', 'platform', 'category', 'status', 'description', 'notes']].copy()
display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
display_df.columns = ['ID', '日期/Date', '渠道/Channel', '平台/Platform',
                       '类别/Category', '状态/Status', '描述/Description', '备注/Notes']
st.dataframe(display_df, use_container_width=True, height=320,
             column_config={
                 '描述/Description': st.column_config.TextColumn(width='large'),
                 '备注/Notes':       st.column_config.TextColumn(width='large'),
             })

st.markdown(f'<p style="text-align:right;color:#ccc;font-size:0.75rem">共 {len(df)} 条 · 数据每5分钟自动刷新 · GHA Discovery</p>',
            unsafe_allow_html=True)
