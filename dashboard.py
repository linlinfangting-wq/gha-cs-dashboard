#!/usr/bin/env python3
"""
GHA 客服数据 Dashboard
直接读取 records.csv，Plotly 图表
本地运行：streamlit run dashboard.py
"""

from collections import Counter
from datetime import datetime
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── 页面配置（必须第一行）──
st.set_page_config(
    page_title='GHA 客服数据 Dashboard',
    page_icon='📊',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ── 品牌色 ──
GOLD   = '#DA9F59'
NAVY   = '#141432'
BLUE   = '#8BBCD9'
CORAL  = '#F69B6F'
GREEN  = '#5D8C6A'
PURPLE = '#300B5C'
PALETTE = [GOLD, BLUE, CORAL, GREEN, PURPLE, '#B7CBD5', '#C4A882', '#7A9898', '#E8C880', '#9090B8']

STATUS_COLOR = {
    '已解决 / Resolved':    GREEN,
    '处理中 / In Progress': GOLD,
    '待处理 / Pending':     BLUE,
    '已升级 / Escalated':   CORAL,
}

st.markdown(f"""
<style>
  .main {{ background-color: #F9F9F7; }}
  .block-container {{ padding-top: 1.5rem; }}
  .metric-card {{
    background: white; border-radius: 12px;
    padding: 20px 24px; border-left: 4px solid {GOLD};
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
  }}
  .metric-value {{ font-size: 2.2rem; font-weight: 700; color: {NAVY}; line-height: 1.1; }}
  .metric-label {{ font-size: 0.82rem; color: #888; margin-top: 4px; }}
  .section-title {{
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
    color: #aaa; text-transform: uppercase; margin-bottom: 8px;
  }}
</style>
""", unsafe_allow_html=True)


# ── 数据加载 ──
@st.cache_data(ttl=300)
def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), 'records.csv')
    df = pd.read_csv(csv_path, encoding='utf-8')
    df = df[df['id'].notna() & (df['id'].astype(str).str.strip() != '')]

    # 双语值映射
    CHANNEL_MAP  = {'微信':'微信 / WeChat','小红书':'小红书 / Xiaohongshu','微信群':'微信群 / WeChat Group','电话':'电话 / Phone','邮件':'邮件 / Email','其他':'其他 / Other'}
    PLATFORM_MAP = {'微信小程序':'微信小程序 / WeChat Mini Program','中文小程序或官网':'中文小程序或官网 / CN Mini Program or Website','GHA英文app':'GHA英文app / GHA English App','GHA英文平台':'GHA英文平台 / GHA English Platform','英文app':'GHA英文app / GHA English App','全平台':'全平台 / All Platforms','其他':'其他 / Other'}
    CATEGORY_MAP = {'技术bug':'技术bug / Technical Bug','需求':'需求 / Feature Request','客服':'客服 / Customer Service','功能':'功能 / Function','价格优势':'价格优势 / Price Competitiveness','会员权益反馈':'会员权益反馈 / Membership Benefits','酒店规则和数据不一致':'酒店规则和数据不一致 / Data Inconsistency','其他':'其他 / Other'}
    STATUS_MAP   = {'已解决':'已解决 / Resolved','处理中':'处理中 / In Progress','待处理':'待处理 / Pending','已升级':'已升级 / Escalated'}

    df['channel']  = df['channel'].map(lambda x: CHANNEL_MAP.get(str(x).strip(), str(x)) if pd.notna(x) else '')
    df['platform'] = df['platform'].map(lambda x: PLATFORM_MAP.get(str(x).strip(), str(x)) if pd.notna(x) else '')
    df['category'] = df['category'].map(lambda x: CATEGORY_MAP.get(str(x).strip(), str(x)) if pd.notna(x) else '')
    df['status']   = df['status'].map(lambda x: STATUS_MAP.get(str(x).strip(), str(x)) if pd.notna(x) else '')
    df['date']     = pd.to_datetime(df['date'], errors='coerce')
    return df


# ── 标题 ──
st.markdown(f'<h1 style="margin-bottom:0">GHA 客服数据 <span style="color:{GOLD}">Dashboard</span></h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#aaa;margin-top:2px;margin-bottom:1.5rem">Customer Service Analytics · GHA Discovery</p>', unsafe_allow_html=True)

df_raw = load_data()
if df_raw.empty:
    st.warning('暂无数据')
    st.stop()

# ── 侧边栏筛选器 ──
with st.sidebar:
    st.markdown('### 筛选 / Filter')
    valid_dates = df_raw['date'].dropna()
    min_d = valid_dates.min().date() if not valid_dates.empty else None
    max_d = valid_dates.max().date() if not valid_dates.empty else None
    if min_d and max_d:
        date_range = st.date_input('日期范围 / Date Range', value=(min_d, max_d), min_value=min_d, max_value=max_d)
    else:
        date_range = None
    sel_channel  = st.multiselect('渠道 / Channel',  sorted(df_raw['channel'].dropna().unique()), default=[])
    sel_category = st.multiselect('类别 / Category', sorted(df_raw['category'].dropna().unique()), default=[])
    sel_status   = st.multiselect('状态 / Status',   sorted(df_raw['status'].dropna().unique()),   default=[])
    st.markdown('---')
    if st.button('🔄 刷新 / Refresh'):
        st.cache_data.clear()
        st.rerun()

# ── 筛选 ──
df = df_raw.copy()
if date_range and len(date_range) == 2:
    df = df[(df['date'].dt.date >= date_range[0]) & (df['date'].dt.date <= date_range[1])]
if sel_channel:  df = df[df['channel'].isin(sel_channel)]
if sel_category: df = df[df['category'].isin(sel_category)]
if sel_status:   df = df[df['status'].isin(sel_status)]
if df.empty:
    st.warning('当前筛选条件下无数据')
    st.stop()

# ── KPI 卡片 ──
total     = len(df)
resolved  = len(df[df['status'].str.contains('Resolved|已解决', na=False)])
pending   = len(df[df['status'].str.contains('Pending|待处理', na=False)])
escalated = len(df[df['status'].str.contains('Escalated|已升级', na=False)])
rate      = f'{resolved/total*100:.1f}%' if total else '—'

c1, c2, c3, c4 = st.columns(4)
for col, val, label in [
    (c1, total,     '总咨询量<br><small>Total Inquiries</small>'),
    (c2, resolved,  f'已解决<br><small>Resolved · {rate}</small>'),
    (c3, pending,   '待处理<br><small>Pending</small>'),
    (c4, escalated, '已升级<br><small>Escalated</small>'),
]:
    col.markdown(f'<div class="metric-card"><div class="metric-value">{val}</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)

# ── 图表行 1：类别 + 渠道 ──
col_a, col_b = st.columns([3, 2])
with col_a:
    st.markdown('<div class="section-title">问题类别分布 · Category Distribution</div>', unsafe_allow_html=True)
    cat_df = df['category'].value_counts().reset_index()
    cat_df.columns = ['category', 'count']
    fig = px.bar(cat_df, x='count', y='category', orientation='h', text='count',
                 color='count', color_continuous_scale=[[0, BLUE],[1, GOLD]])
    fig.update_traces(textposition='outside')
    fig.update_layout(coloraxis_showscale=False, plot_bgcolor='white', paper_bgcolor='white',
                      margin=dict(l=0,r=30,t=10,b=0), height=320,
                      yaxis=dict(title=''), xaxis=dict(title='咨询量', showgrid=True, gridcolor='#f0f0f0'))
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.markdown('<div class="section-title">渠道来源 · Channel Source</div>', unsafe_allow_html=True)
    ch_df = df['channel'].value_counts().reset_index()
    ch_df.columns = ['channel', 'count']
    fig = go.Figure(go.Pie(labels=ch_df['channel'], values=ch_df['count'],
                           hole=0.55, marker_colors=PALETTE[:len(ch_df)],
                           textinfo='label+percent', textfont_size=11))
    fig.update_layout(showlegend=False, paper_bgcolor='white', margin=dict(l=0,r=0,t=10,b=0), height=320)
    st.plotly_chart(fig, use_container_width=True)

# ── 图表行 2：状态 + 月度趋势 ──
col_c, col_d = st.columns([2, 3])
with col_c:
    st.markdown('<div class="section-title">处理状态 · Status</div>', unsafe_allow_html=True)
    st_df = df['status'].value_counts().reset_index()
    st_df.columns = ['status', 'count']
    colors = [STATUS_COLOR.get(s, NAVY) for s in st_df['status']]
    fig = go.Figure(go.Bar(x=st_df['status'], y=st_df['count'], marker_color=colors,
                           text=st_df['count'], textposition='outside'))
    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                      margin=dict(l=0,r=0,t=10,b=60), height=320,
                      xaxis=dict(tickangle=-20, tickfont=dict(size=10)),
                      yaxis=dict(showgrid=True, gridcolor='#f0f0f0'))
    st.plotly_chart(fig, use_container_width=True)

with col_d:
    st.markdown('<div class="section-title">每月咨询量趋势 · Monthly Trend</div>', unsafe_allow_html=True)
    trend = df.dropna(subset=['date']).copy()
    trend['month'] = trend['date'].dt.to_period('M').astype(str)
    monthly = trend.groupby('month').size().reset_index(name='count')
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly['month'], y=monthly['count'], mode='lines+markers+text',
                             text=monthly['count'], textposition='top center',
                             line=dict(color=GOLD, width=2.5), marker=dict(color=GOLD, size=8),
                             fill='tozeroy', fillcolor='rgba(218,159,89,0.08)'))
    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                      margin=dict(l=0,r=0,t=10,b=0), height=320,
                      xaxis=dict(showgrid=False, tickangle=-20),
                      yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title='咨询量'))
    st.plotly_chart(fig, use_container_width=True)

# ── 图表行 3：平台 + 关键词 ──
col_e, col_f = st.columns(2)
with col_e:
    st.markdown('<div class="section-title">平台分布 · Platform</div>', unsafe_allow_html=True)
    pl_df = df[df['platform'].str.strip() != '']['platform'].value_counts().reset_index()
    pl_df.columns = ['platform', 'count']
    fig = px.bar(pl_df.sort_values('count'), x='count', y='platform', orientation='h',
                 color_discrete_sequence=[PURPLE], text='count')
    fig.update_traces(textposition='outside')
    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                      margin=dict(l=0,r=30,t=10,b=0), height=280,
                      yaxis=dict(title=''), xaxis=dict(title='', showgrid=True, gridcolor='#f0f0f0'))
    st.plotly_chart(fig, use_container_width=True)

with col_f:
    st.markdown('<div class="section-title">高频关键词 Top 10 · Keywords</div>', unsafe_allow_html=True)
    all_kw = []
    for kw in df['keywords'].dropna():
        all_kw.extend([k.strip() for k in str(kw).split(',') if k.strip()])
    if all_kw:
        top = Counter(all_kw).most_common(10)
        kw_df = pd.DataFrame(top, columns=['keyword','count']).sort_values('count')
        fig = px.bar(kw_df, x='count', y='keyword', orientation='h',
                     color_discrete_sequence=[BLUE], text='count')
        fig.update_traces(textposition='outside')
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                          margin=dict(l=0,r=30,t=10,b=0), height=280,
                          yaxis=dict(title=''), xaxis=dict(title='', showgrid=True, gridcolor='#f0f0f0'))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('暂无关键词数据')

# ── 数据明细 ──
st.markdown('---')
st.markdown('<div class="section-title">数据明细 · Records</div>', unsafe_allow_html=True)
show = df[['id','date','channel','platform','category','status','description','notes']].copy()
show['date'] = show['date'].dt.strftime('%Y-%m-%d')
show.columns = ['ID','日期/Date','渠道/Channel','平台/Platform','类别/Category','状态/Status','描述/Description','备注/Notes']
st.dataframe(show, use_container_width=True, height=320,
             column_config={'描述/Description': st.column_config.TextColumn(width='large'),
                            '备注/Notes': st.column_config.TextColumn(width='large')})

st.markdown(f'<p style="text-align:right;color:#ccc;font-size:0.75rem">共 {len(df)} 条 · GHA Discovery</p>', unsafe_allow_html=True)
