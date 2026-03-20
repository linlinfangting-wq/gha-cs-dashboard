#!/usr/bin/env python3
"""GHA 客服数据 Dashboard v2 — 视觉 + 图表 + 洞察全升级"""

from collections import Counter
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
IVORY  = '#FAFAF8'
PALETTE = [GOLD, BLUE, CORAL, GREEN, PURPLE, '#B7CBD5', '#C4A882', '#7A9898', '#E8C880', '#9090B8']

STATUS_COLOR = {
    '已解决 / Resolved':    GREEN,
    '处理中 / In Progress': GOLD,
    '待处理 / Pending':     BLUE,
    '已升级 / Escalated':   CORAL,
}

# ── 全局样式 ──
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.main {{ background: #F4F4F1; }}
.block-container {{ padding-top: 0 !important; padding-bottom: 2rem; }}

.hero {{
  background: linear-gradient(135deg, {NAVY} 0%, #2A2A5A 60%, {PURPLE} 100%);
  border-radius: 0 0 24px 24px;
  padding: 36px 40px 32px;
  margin: -1rem -1rem 2rem;
  color: white;
}}
.hero h1 {{ font-size: 2rem; font-weight: 700; margin: 0 0 4px; color: white; }}
.hero p  {{ font-size: 0.9rem; opacity: 0.6; margin: 0; color: white; }}
.hero .gold {{ color: {GOLD}; }}

.kpi-wrap {{ display: flex; gap: 16px; margin-top: 20px; flex-wrap: wrap; }}
.kpi {{
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 14px; padding: 16px 22px;
  flex: 1; min-width: 120px;
  backdrop-filter: blur(8px);
}}
.kpi-val {{ font-size: 2rem; font-weight: 700; color: {GOLD}; line-height: 1; }}
.kpi-lbl {{ font-size: 0.72rem; color: rgba(255,255,255,0.6); margin-top: 4px; }}
.kpi-sub {{ font-size: 0.78rem; color: rgba(255,255,255,0.85); margin-top: 2px; font-weight: 500; }}

.card {{
  background: white; border-radius: 16px;
  padding: 20px 22px; margin-bottom: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}}
.card-title {{
  font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; color: #bbb; margin-bottom: 2px;
}}
.card-subtitle {{ font-size: 1rem; font-weight: 600; color: {NAVY}; margin-bottom: 12px; }}

.insight {{
  background: linear-gradient(135deg, #FEFCF7 0%, #FFF8EE 100%);
  border-left: 3px solid {GOLD}; border-radius: 0 10px 10px 0;
  padding: 10px 14px; margin-top: 8px; font-size: 0.82rem; color: #555; line-height: 1.6;
}}
.insight b {{ color: {NAVY}; }}

.divider {{ height: 1px; background: #EBEBEB; margin: 24px 0; }}
</style>
""", unsafe_allow_html=True)


# ── 数据加载 ──
@st.cache_data(ttl=300)
def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), 'records.csv')
    df = pd.read_csv(csv_path, encoding='utf-8')
    df = df[df['id'].notna() & (df['id'].astype(str).str.strip() != '')]
    CHANNEL_MAP  = {'微信':'微信 / WeChat','小红书':'小红书 / Xiaohongshu','微信群':'微信群 / WeChat Group','电话':'电话 / Phone','邮件':'邮件 / Email','其他':'其他 / Other'}
    PLATFORM_MAP = {'微信小程序':'微信小程序 / WeChat Mini Program','中文小程序或官网':'中文小程序或官网 / CN Mini Program','GHA英文app':'GHA英文app / GHA App','GHA英文平台':'GHA英文平台 / GHA Platform','英文app':'GHA英文app / GHA App','全平台':'全平台 / All Platforms','其他':'其他 / Other'}
    CATEGORY_MAP = {'技术bug':'技术bug / Tech Bug','需求':'需求 / Feature Request','客服':'客服 / Support','功能':'功能 / Function','价格优势':'价格优势 / Pricing','会员权益反馈':'会员权益 / Benefits','酒店规则和数据不一致':'数据不一致 / Data Mismatch','其他':'其他 / Other'}
    STATUS_MAP   = {'已解决':'已解决 / Resolved','处理中':'处理中 / In Progress','待处理':'待处理 / Pending','已升级':'已升级 / Escalated'}
    df['channel']  = df['channel'].map(lambda x: CHANNEL_MAP.get(str(x).strip(), str(x)) if pd.notna(x) else '')
    df['platform'] = df['platform'].map(lambda x: PLATFORM_MAP.get(str(x).strip(), str(x)) if pd.notna(x) else '')
    df['category'] = df['category'].map(lambda x: CATEGORY_MAP.get(str(x).strip(), str(x)) if pd.notna(x) else '')
    df['status']   = df['status'].map(lambda x: STATUS_MAP.get(str(x).strip(), str(x)) if pd.notna(x) else '')
    df['date']     = pd.to_datetime(df['date'], errors='coerce')
    return df


# ── 洞察文字生成 ──
def insight_category(df):
    top = df['category'].value_counts()
    if top.empty: return ''
    name, cnt = top.index[0], top.iloc[0]
    pct = cnt / len(df) * 100
    unresolved = df[(df['category'] == name) & (~df['status'].str.contains('Resolved', na=False))]
    ur = len(unresolved)
    return (f'<b>{name}</b> 是最高频问题类别，占总量 <b>{pct:.0f}%</b>（{cnt} 条）。'
            f'其中仍有 <b>{ur}</b> 条未解决，建议优先跟进。')

def insight_channel(df):
    top = df['channel'].value_counts()
    if top.empty: return ''
    name, cnt = top.index[0], top.iloc[0]
    pct = cnt / len(df) * 100
    # 该渠道解决率
    ch_df = df[df['channel'] == name]
    res = ch_df['status'].str.contains('Resolved', na=False).sum()
    rate = res / len(ch_df) * 100 if len(ch_df) else 0
    return (f'<b>{name}</b> 是主要咨询渠道，占比 <b>{pct:.0f}%</b>。'
            f'该渠道解决率为 <b>{rate:.0f}%</b>，'
            + ('表现良好。' if rate >= 70 else '仍有提升空间，需加强响应。'))

def insight_status(df):
    total = len(df)
    resolved = df['status'].str.contains('Resolved', na=False).sum()
    pending  = df['status'].str.contains('Pending', na=False).sum()
    escalated= df['status'].str.contains('Escalated', na=False).sum()
    rate = resolved / total * 100 if total else 0
    msg = f'整体解决率 <b>{rate:.0f}%</b>（{resolved}/{total}）。'
    if escalated > 0:
        msg += f' 有 <b>{escalated}</b> 条已升级，需重点关注。'
    if pending > 0:
        msg += f' <b>{pending}</b> 条待处理，建议尽快跟进。'
    return msg

def insight_trend(df):
    trend = df.dropna(subset=['date']).copy()
    if trend.empty: return ''
    trend['month'] = trend['date'].dt.to_period('M').astype(str)
    monthly = trend.groupby('month').size()
    if len(monthly) < 2: return f'当前共 <b>{len(df)}</b> 条记录，数据持续积累中。'
    last, prev = monthly.iloc[-1], monthly.iloc[-2]
    diff = last - prev
    direction = f'上升 <b>+{diff}</b>' if diff > 0 else (f'下降 <b>{diff}</b>' if diff < 0 else '持平')
    peak = monthly.idxmax()
    return (f'最近一个月咨询量较上月{direction}。'
            f'历史峰值出现在 <b>{peak}</b>（{monthly.max()} 条）。')

def insight_sankey(df):
    top_ch = df['channel'].value_counts().index[0] if not df['channel'].value_counts().empty else ''
    top_cat = df['category'].value_counts().index[0] if not df['category'].value_counts().empty else ''
    if not top_ch or not top_cat: return ''
    flow = df[(df['channel'] == top_ch) & (df['category'] == top_cat)]
    return (f'最主要的问题路径是 <b>{top_ch} → {top_cat}</b>，共 <b>{len(flow)}</b> 条。'
            f'优化该渠道的 {top_cat} 处理流程可带来最大效益。')


# ── 数据加载 ──
df_raw = load_data()

# ── 侧边栏 ──
with st.sidebar:
    st.markdown(f'<div style="font-size:1.1rem;font-weight:700;color:{NAVY};margin-bottom:16px">筛选 / Filter</div>', unsafe_allow_html=True)
    valid_dates = df_raw['date'].dropna()
    if not valid_dates.empty:
        date_range = st.date_input('日期范围 / Date Range',
                                   value=(valid_dates.min().date(), valid_dates.max().date()),
                                   min_value=valid_dates.min().date(), max_value=valid_dates.max().date())
    else:
        date_range = None
    sel_channel  = st.multiselect('渠道 / Channel',  sorted(df_raw['channel'].dropna().unique()), default=[])
    sel_category = st.multiselect('类别 / Category', sorted(df_raw['category'].dropna().unique()), default=[])
    sel_status   = st.multiselect('状态 / Status',   sorted(df_raw['status'].dropna().unique()),   default=[])
    st.markdown('---')
    if st.button('🔄 刷新数据 / Refresh', use_container_width=True):
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

# ── KPI 数据 ──
total     = len(df)
resolved  = df['status'].str.contains('Resolved', na=False).sum()
pending   = df['status'].str.contains('Pending',  na=False).sum()
escalated = df['status'].str.contains('Escalated',na=False).sum()
rate      = f'{resolved/total*100:.1f}%' if total else '—'

# ── Hero Banner ──
st.markdown(f"""
<div class="hero">
  <h1>GHA 客服数据 <span class="gold">Dashboard</span></h1>
  <p>Customer Service Analytics · GHA Discovery</p>
  <div class="kpi-wrap">
    <div class="kpi">
      <div class="kpi-val">{total}</div>
      <div class="kpi-lbl">总咨询量 · Total</div>
    </div>
    <div class="kpi">
      <div class="kpi-val">{resolved}</div>
      <div class="kpi-lbl">已解决 · Resolved</div>
      <div class="kpi-sub">解决率 {rate}</div>
    </div>
    <div class="kpi">
      <div class="kpi-val">{pending}</div>
      <div class="kpi-lbl">待处理 · Pending</div>
    </div>
    <div class="kpi">
      <div class="kpi-val">{escalated}</div>
      <div class="kpi-lbl">已升级 · Escalated</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════
# 板块 1：问题类别 + 渠道来源
# ═══════════════════════════════════════
col_a, col_b = st.columns([3, 2], gap='medium')

with col_a:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Issue Distribution</div><div class="card-subtitle">问题类别分布</div>', unsafe_allow_html=True)
    cat_df = df['category'].value_counts().reset_index()
    cat_df.columns = ['category', 'count']
    cat_df['short'] = cat_df['category'].str.split('/').str[0].str.strip()
    fig = go.Figure(go.Bar(
        y=cat_df['short'][::-1], x=cat_df['count'][::-1],
        orientation='h', text=cat_df['count'][::-1],
        textposition='outside', textfont=dict(size=12, color=NAVY),
        marker=dict(
            color=cat_df['count'][::-1],
            colorscale=[[0, BLUE], [0.5, GOLD], [1, CORAL]],
            showscale=False,
            line=dict(width=0),
        ),
        hovertemplate='%{y}<br>咨询量: <b>%{x}</b><extra></extra>',
    ))
    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=0, r=50, t=8, b=0), height=300,
        yaxis=dict(title='', tickfont=dict(size=12, color='#444')),
        xaxis=dict(title='', showgrid=True, gridcolor='#F0F0F0', zeroline=False),
        bargap=0.35,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f'<div class="insight">💡 {insight_category(df)}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_b:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Channel Source</div><div class="card-subtitle">渠道来源分布</div>', unsafe_allow_html=True)
    ch_df = df['channel'].value_counts().reset_index()
    ch_df.columns = ['channel', 'count']
    ch_df['short'] = ch_df['channel'].str.split('/').str[0].str.strip()
    fig = go.Figure(go.Pie(
        labels=ch_df['short'], values=ch_df['count'],
        hole=0.6, marker=dict(colors=PALETTE[:len(ch_df)], line=dict(color='white', width=2)),
        textinfo='percent', textfont=dict(size=11),
        hovertemplate='%{label}<br><b>%{value}</b> 条 (%{percent})<extra></extra>',
        pull=[0.04] + [0] * (len(ch_df) - 1),
    ))
    fig.add_annotation(text=f'<b>{total}</b><br><span style="font-size:11px">总计</span>',
                       x=0.5, y=0.5, font_size=18, showarrow=False, font_color=NAVY)
    fig.update_layout(
        showlegend=True, paper_bgcolor='white',
        legend=dict(orientation='v', x=1.02, y=0.5, font=dict(size=10)),
        margin=dict(l=0, r=80, t=8, b=0), height=300,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f'<div class="insight">💡 {insight_channel(df)}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════
# 板块 2：桑基图（渠道 → 类别 → 状态）
# ═══════════════════════════════════════
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Flow Analysis</div><div class="card-subtitle">问题流向图：渠道 → 类别 → 处理状态</div>', unsafe_allow_html=True)

df_s = df.copy()
df_s['ch_short']  = df_s['channel'].str.split('/').str[0].str.strip()
df_s['cat_short'] = df_s['category'].str.split('/').str[0].str.strip()
df_s['st_short']  = df_s['status'].str.split('/').str[0].str.strip()

channels   = df_s['ch_short'].dropna().unique().tolist()
categories = df_s['cat_short'].dropna().unique().tolist()
statuses   = df_s['st_short'].dropna().unique().tolist()
all_nodes  = channels + categories + statuses
node_idx   = {n: i for i, n in enumerate(all_nodes)}

sources, targets, values, link_colors = [], [], [], []
# ch → cat
for (ch, cat), grp in df_s.groupby(['ch_short', 'cat_short']):
    if pd.notna(ch) and pd.notna(cat) and ch in node_idx and cat in node_idx:
        sources.append(node_idx[ch]); targets.append(node_idx[cat])
        values.append(len(grp)); link_colors.append('rgba(218,159,89,0.25)')
# cat → status
for (cat, st), grp in df_s.groupby(['cat_short', 'st_short']):
    if pd.notna(cat) and pd.notna(st) and cat in node_idx and st in node_idx:
        sources.append(node_idx[cat]); targets.append(node_idx[st])
        values.append(len(grp))
        sc = STATUS_COLOR.get(df_s[df_s['st_short'] == st]['status'].iloc[0], BLUE) if len(df_s[df_s['st_short'] == st]) else BLUE
        r, g, b = int(sc[1:3],16), int(sc[3:5],16), int(sc[5:7],16)
        link_colors.append(f'rgba({r},{g},{b},0.3)')

node_colors = (
    [GOLD]   * len(channels) +
    [BLUE]   * len(categories) +
    [STATUS_COLOR.get(
        df_s[df_s['st_short'] == s]['status'].iloc[0] if len(df_s[df_s['st_short'] == s]) else '',
        GREEN
    ) for s in statuses]
)

fig = go.Figure(go.Sankey(
    arrangement='snap',
    node=dict(
        label=all_nodes, color=node_colors,
        pad=20, thickness=18,
        line=dict(color='white', width=0.5),
        hovertemplate='%{label}<br>流量: <b>%{value}</b><extra></extra>',
    ),
    link=dict(
        source=sources, target=targets, value=values,
        color=link_colors,
        hovertemplate='%{source.label} → %{target.label}<br><b>%{value}</b> 条<extra></extra>',
    ),
))
fig.update_layout(
    paper_bgcolor='white', font=dict(size=12, color=NAVY),
    margin=dict(l=10, r=10, t=10, b=10), height=340,
)
st.plotly_chart(fig, use_container_width=True)
st.markdown(f'<div class="insight">💡 {insight_sankey(df)}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════
# 板块 3：处理状态 + 月度趋势
# ═══════════════════════════════════════
col_c, col_d = st.columns([2, 3], gap='medium')

with col_c:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Status Breakdown</div><div class="card-subtitle">处理状态分布</div>', unsafe_allow_html=True)
    st_df = df['status'].value_counts().reset_index()
    st_df.columns = ['status', 'count']
    st_df['short'] = st_df['status'].str.split('/').str[0].str.strip()
    st_df['pct']   = (st_df['count'] / total * 100).round(1)
    colors = [STATUS_COLOR.get(s, NAVY) for s in st_df['status']]
    fig = go.Figure(go.Bar(
        x=st_df['short'], y=st_df['count'],
        marker_color=colors, marker_line_width=0,
        text=[f'{v}<br>{p}%' for v, p in zip(st_df['count'], st_df['pct'])],
        textposition='outside', textfont=dict(size=11),
        hovertemplate='%{x}<br><b>%{y}</b> 条<extra></extra>',
    ))
    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=0, r=0, t=8, b=8), height=300,
        xaxis=dict(tickfont=dict(size=11), tickangle=-15),
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0', zeroline=False),
        bargap=0.4,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f'<div class="insight">💡 {insight_status(df)}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_d:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Monthly Trend</div><div class="card-subtitle">每月咨询量趋势</div>', unsafe_allow_html=True)
    trend = df.dropna(subset=['date']).copy()
    trend['month'] = trend['date'].dt.to_period('M').astype(str)
    monthly = trend.groupby(['month','status']).size().reset_index(name='count')
    pivot = monthly.pivot(index='month', columns='status', values='count').fillna(0)

    fig = go.Figure()
    for col_name in pivot.columns:
        short = col_name.split('/')[0].strip()
        color = STATUS_COLOR.get(col_name, BLUE)
        r,g,b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
        fig.add_trace(go.Bar(
            name=short, x=pivot.index, y=pivot[col_name],
            marker_color=color, marker_line_width=0,
            hovertemplate=f'{short}<br>%{{x}}: <b>%{{y}}</b> 条<extra></extra>',
        ))
    total_by_month = pivot.sum(axis=1)
    fig.add_trace(go.Scatter(
        x=total_by_month.index, y=total_by_month.values,
        mode='lines+markers+text', name='总计',
        text=total_by_month.values.astype(int),
        textposition='top center', textfont=dict(size=11, color=NAVY),
        line=dict(color=NAVY, width=2, dash='dot'),
        marker=dict(color=NAVY, size=6),
    ))
    fig.update_layout(
        barmode='stack', plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=0, r=0, t=8, b=0), height=300,
        legend=dict(orientation='h', y=-0.15, font=dict(size=10)),
        xaxis=dict(tickangle=-20, showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0', zeroline=False),
        bargap=0.3,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f'<div class="insight">💡 {insight_trend(df)}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════
# 板块 4：热力图（平台 × 类别）
# ═══════════════════════════════════════
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="card-title">Platform × Category Heatmap</div><div class="card-subtitle">平台与问题类别交叉热力图</div>', unsafe_allow_html=True)

df_h = df[(df['platform'].str.strip() != '') & (df['category'].str.strip() != '')].copy()
df_h['pl_short']  = df_h['platform'].str.split('/').str[0].str.strip()
df_h['cat_short'] = df_h['category'].str.split('/').str[0].str.strip()
heat = df_h.groupby(['pl_short','cat_short']).size().unstack(fill_value=0)

if not heat.empty:
    fig = go.Figure(go.Heatmap(
        z=heat.values, x=heat.columns.tolist(), y=heat.index.tolist(),
        colorscale=[[0,'#F4F4F1'],[0.3, BLUE],[0.7, GOLD],[1, CORAL]],
        text=heat.values, texttemplate='%{text}', textfont=dict(size=12),
        hovertemplate='平台: %{y}<br>类别: %{x}<br>数量: <b>%{z}</b><extra></extra>',
        showscale=True,
        colorbar=dict(thickness=12, len=0.8, title=dict(text='数量', side='right')),
    ))
    fig.update_layout(
        paper_bgcolor='white', plot_bgcolor='white',
        margin=dict(l=0, r=0, t=8, b=0), height=260,
        xaxis=dict(tickangle=-20, tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=11)),
    )
    st.plotly_chart(fig, use_container_width=True)
    # 洞察
    max_val = heat.values.max()
    max_pos = [(heat.index[r], heat.columns[c]) for r in range(heat.shape[0]) for c in range(heat.shape[1]) if heat.values[r][c] == max_val]
    if max_pos:
        pl, cat = max_pos[0]
        st.markdown(f'<div class="insight">💡 <b>{pl}</b> 平台的 <b>{cat}</b> 问题最集中（<b>{int(max_val)}</b> 条），是需要重点优化的平台-问题组合。</div>', unsafe_allow_html=True)
else:
    st.info('暂无足够数据生成热力图')
st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════
# 板块 5：关键词 + 数据明细
# ═══════════════════════════════════════
col_e, col_f = st.columns([1, 2], gap='medium')

with col_e:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Top Keywords</div><div class="card-subtitle">高频关键词 Top 10</div>', unsafe_allow_html=True)
    all_kw = []
    for kw in df['keywords'].dropna():
        all_kw.extend([k.strip() for k in str(kw).split(',') if k.strip()])
    if all_kw:
        top = Counter(all_kw).most_common(10)
        kw_df = pd.DataFrame(top, columns=['keyword','count']).sort_values('count')
        fig = go.Figure(go.Bar(
            y=kw_df['keyword'], x=kw_df['count'], orientation='h',
            text=kw_df['count'], textposition='outside',
            marker=dict(color=kw_df['count'], colorscale=[[0,BLUE],[1,PURPLE]], showscale=False, line=dict(width=0)),
            hovertemplate='%{y}: <b>%{x}</b> 次<extra></extra>',
        ))
        fig.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            margin=dict(l=0,r=40,t=8,b=0), height=300,
            yaxis=dict(tickfont=dict(size=11)), xaxis=dict(showgrid=True, gridcolor='#F0F0F0'),
            bargap=0.3,
        )
        st.plotly_chart(fig, use_container_width=True)
        top1 = top[0][0] if top else ''
        st.markdown(f'<div class="insight">💡 "<b>{top1}</b>" 是出现最频繁的关键词，共 <b>{top[0][1]}</b> 次，反映用户核心诉求。</div>', unsafe_allow_html=True)
    else:
        st.info('暂无关键词数据')
    st.markdown('</div>', unsafe_allow_html=True)

with col_f:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Records</div><div class="card-subtitle">数据明细</div>', unsafe_allow_html=True)
    show = df[['id','date','channel','category','status','description','notes']].copy()
    show['date'] = show['date'].dt.strftime('%Y-%m-%d')
    show.columns = ['ID','日期/Date','渠道/Channel','类别/Category','状态/Status','描述/Desc','备注/Notes']
    st.dataframe(show, use_container_width=True, height=320,
                 column_config={
                     '描述/Desc':  st.column_config.TextColumn(width='large'),
                     '备注/Notes': st.column_config.TextColumn(width='medium'),
                 })
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f'<p style="text-align:right;color:#ccc;font-size:0.72rem;margin-top:8px">共 {len(df)} 条记录 · 数据每5分钟刷新 · GHA Discovery Customer Service</p>', unsafe_allow_html=True)
