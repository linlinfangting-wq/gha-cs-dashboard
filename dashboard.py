#!/usr/bin/env python3
"""GHA 客服数据 Dashboard v6 — 全页语言切换"""

from collections import Counter
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── 页面配置 ──
st.set_page_config(
    page_title='GHA CS Dashboard',
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

# ── 语言状态 ──
if 'lang' not in st.session_state:
    st.session_state.lang = 'zh'
lang = st.session_state.lang


def t(zh, en):
    """返回当前语言的文字"""
    return zh if lang == 'zh' else en


def disp(val):
    """从 'A / B' 格式取单语，如 '微信 / WeChat' → '微信' 或 'WeChat'"""
    if not isinstance(val, str) or ' / ' not in val:
        return val
    parts = val.split(' / ', 1)
    return parts[0].strip() if lang == 'zh' else parts[1].strip()


# ── 全局样式 ──
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.main {{ background: #F4F4F1; }}
.block-container {{ padding-top: 0 !important; padding-bottom: 2rem; }}
.hero {{
  background: linear-gradient(135deg, {NAVY} 0%, #2A2A5A 60%, {PURPLE} 100%);
  border-radius: 0 0 24px 24px; padding: 36px 40px 32px;
  margin: -1rem -1rem 2rem; color: white;
}}
.hero h1 {{ font-size: 2rem; font-weight: 700; margin: 0 0 4px; color: white; }}
.hero p  {{ font-size: 0.9rem; opacity: 0.6; margin: 0; color: white; }}
.hero .gold {{ color: {GOLD}; }}
.kpi-wrap {{ display: flex; gap: 16px; margin-top: 20px; flex-wrap: wrap; }}
.kpi {{
  background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);
  border-radius: 14px; padding: 16px 22px; flex: 1; min-width: 120px;
  backdrop-filter: blur(8px);
}}
.kpi-val {{ font-size: 2rem; font-weight: 700; color: {GOLD}; line-height: 1; }}
.kpi-lbl {{ font-size: 0.72rem; color: rgba(255,255,255,0.6); margin-top: 4px; }}
.card {{
  background: white; border-radius: 16px; padding: 20px 22px; margin-bottom: 16px;
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
</style>
""", unsafe_allow_html=True)


# ── 数据加载 ──
@st.cache_data(ttl=300)
def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), 'records.csv')
    df = pd.read_csv(csv_path, encoding='utf-8')
    df = df[df['id'].notna() & (df['id'].astype(str).str.strip() != '')]
    CHANNEL_MAP  = {'微信':'微信 / WeChat','小红书':'小红书 / Xiaohongshu','微信群':'微信群 / WeChat Group','电话':'电话 / Phone','邮件':'邮件 / Email','其他':'其他 / Other'}
    PLATFORM_MAP = {'微信小程序':'中文官网和小程序 / CN Website & Mini Program','中文小程序或官网':'中文官网和小程序 / CN Website & Mini Program','GHA英文app':'GHA英文平台 / GHA Platform','GHA英文平台':'GHA英文平台 / GHA Platform','英文app':'GHA英文平台 / GHA Platform','全平台':'全平台 / All Platforms','其他':'全平台 / All Platforms'}
    CATEGORY_MAP = {'技术bug':'技术bug / Tech Bug','需求':'需求 / Feature Request','客服':'客服 / Support','功能':'功能 / Function','价格优势':'价格优势 / Pricing','会员权益反馈':'会员权益 / Benefits','酒店规则和数据不一致':'数据不一致 / Data Mismatch','其他':'其他 / Other'}
    df['channel']  = df['channel'].map(lambda x: CHANNEL_MAP.get(str(x).strip(), str(x)) if pd.notna(x) else '')
    df['platform'] = df['platform'].map(lambda x: PLATFORM_MAP.get(str(x).strip(), str(x)) if pd.notna(x) else '')
    df['category'] = df['category'].map(lambda x: CATEGORY_MAP.get(str(x).strip(), str(x)) if pd.notna(x) else '')
    df['date']     = pd.to_datetime(df['date'], errors='coerce')
    return df


# ── 洞察文字（单语）──
def insight_category(df):
    top = df['category'].value_counts()
    if top.empty: return ''
    name, cnt = top.index[0], top.iloc[0]
    pct = cnt / len(df) * 100
    cat_s = name.split('/')[0].strip()
    if '技术' in cat_s or 'bug' in cat_s.lower():
        msg = t('技术问题在小红书等开放平台易演变为负面 UGC，建议快速响应并主动公告处理进展',
                'Tech issues on open platforms like Xiaohongshu can escalate into negative UGC; quick response and proactive updates recommended')
    elif '需求' in cat_s or 'Feature' in cat_s:
        msg = t('需求类咨询是产品迭代与内容选题的方向信号，可沉淀为 FAQ 或推文素材',
                'Feature requests signal product iteration directions; consider compiling into FAQ or social content')
    elif '会员' in cat_s or 'Benefits' in cat_s:
        msg = t('权益咨询量高反映信息透明度不足，建议通过内容科普（推文/短视频）降低重复咨询',
                'High benefits inquiry volume suggests insufficient transparency; address via educational content (posts/short videos)')
    elif '数据' in cat_s or 'Data' in cat_s:
        msg = t('数据不一致影响用户决策，需向酒店和平台团队同步跟进，并在内容端说明差异',
                'Data inconsistencies affect user decisions; sync follow-up with hotel and platform teams and clarify discrepancies in content')
    else:
        msg = t('建议通过自助内容（FAQ/教程）前置拦截，降低重复咨询率',
                'Self-service content (FAQ/tutorials) can proactively reduce repeat inquiry rates')
    disp_name = disp(name)
    return t(
        f'<b>{disp_name}</b> 是最高频问题，占 <b>{pct:.0f}%</b>（{cnt} 条）。{msg}。',
        f'<b>{disp_name}</b> is the top issue at <b>{pct:.0f}%</b> ({cnt} records). {msg}.'
    )


def insight_channel(df):
    top = df['channel'].value_counts()
    if top.empty: return ''
    name, cnt = top.index[0], top.iloc[0]
    pct = cnt / len(df) * 100
    ch_s = name.split('/')[0].strip()
    if '小红书' in ch_s:
        msg = t('小红书为开放平台，咨询公开可见，建议设定 24h 内响应 SLA 保护品牌形象',
                'Xiaohongshu is an open platform where inquiries are publicly visible; set a 24h response SLA to protect brand reputation')
    elif '微信群' in ch_s:
        msg = t('社群场景中问题对全体成员可见，优先处理可提升社群信任度',
                'Issues in group chats are visible to all members; prioritizing responses builds community trust')
    elif '微信' in ch_s:
        msg = t('私域核心阵地，响应质量直接影响用户留存与口碑传播',
                'A core private-domain channel; response quality directly impacts user retention and word-of-mouth')
    else:
        msg = t('建议持续跟踪该渠道响应速度与用户满意度',
                'Continuously monitor response speed and user satisfaction for this channel')
    disp_name = disp(name)
    return t(
        f'<b>{disp_name}</b> 是主要来源渠道（占 <b>{pct:.0f}%</b>，{cnt} 条）。{msg}。',
        f'<b>{disp_name}</b> is the top source channel ({pct:.0f}%, {cnt} records). {msg}.'
    )


def insight_ch_cat(df):
    top_ch  = df['channel'].value_counts().index[0]  if not df['channel'].value_counts().empty  else ''
    top_cat = df['category'].value_counts().index[0] if not df['category'].value_counts().empty else ''
    if not top_ch or not top_cat: return ''
    flow = df[(df['channel'] == top_ch) & (df['category'] == top_cat)]
    ch_s  = top_ch.split('/')[0].strip()   # for condition check
    ch_disp  = disp(top_ch)
    cat_disp = disp(top_cat)
    if '小红书' in ch_s:
        msg = t('该路径发生在开放平台，问题可见度高，建议提高响应优先级并在评论区主动引导私信',
                'This path occurs on an open platform with high visibility; increase response priority and proactively guide users to DM in comments')
    elif '微信群' in ch_s:
        msg = t('群内高频问题若积压可能引发集体不满，建议排查根本原因并统一回复',
                'Unresolved high-frequency group issues can trigger collective dissatisfaction; investigate root cause and issue unified responses')
    else:
        msg = t('优化该路径的标准应答模板可大幅提升整体响应效率',
                'Optimizing standard response templates for this path can significantly improve overall efficiency')
    return t(
        f'最高频路径：<b>{ch_disp} → {cat_disp}</b>（<b>{len(flow)}</b> 条）。{msg}。',
        f'Top path: <b>{ch_disp} → {cat_disp}</b> (<b>{len(flow)}</b> records). {msg}.'
    )


def insight_trend(df):
    trend = df.dropna(subset=['date']).copy()
    if trend.empty: return ''
    trend['month'] = trend['date'].dt.to_period('M').astype(str)
    monthly = trend.groupby('month').size()
    if len(monthly) < 2:
        return t(
            f'当前共 <b>{len(df)}</b> 条记录，数据积累中，建议持续记录以观察趋势规律。',
            f'Currently <b>{len(df)}</b> records. Data accumulating — continue logging to observe trend patterns.'
        )
    last, prev = monthly.iloc[-1], monthly.iloc[-2]
    diff = last - prev
    if diff > 0:
        zh_dir = f'上升 <b>+{diff}</b> 条'
        en_dir = f'increased by <b>+{diff}</b>'
        msg = t('咨询量增长可能与近期推广活动或新用户涌入相关，建议核查活动节点',
                'The increase may be linked to recent promotions or new user influx; cross-check with campaign timelines')
    elif diff < 0:
        zh_dir = f'下降 <b>{abs(diff)}</b> 条'
        en_dir = f'decreased by <b>{abs(diff)}</b>'
        msg = t('咨询量下滑可能是内容教育有效或社区活跃度下降，建议结合社媒数据交叉验证',
                'The decline may reflect effective content education or lower community activity; cross-validate with social media data')
    else:
        zh_dir = '持平'
        en_dir = 'remained flat'
        msg = t('咨询量稳定，可持续观察高频问题是否被内容/产品侧逐步消化',
                'Volume is stable; continue observing whether high-frequency issues are gradually resolved by content or product updates')
    peak = monthly.idxmax()
    return t(
        f'最近月咨询量较上月{zh_dir}。历史峰值在 <b>{peak}</b>（{monthly.max()} 条）。{msg}。',
        f'Latest month {en_dir} vs. prior month. Historical peak: <b>{peak}</b> ({monthly.max()} records). {msg}.'
    )


# ── 数据加载 ──
df_raw = load_data()

# ── 侧边栏 ──
with st.sidebar:
    # 语言切换按钮
    c1, c2 = st.columns(2)
    with c1:
        if st.button('中文', type='primary' if lang == 'zh' else 'secondary', use_container_width=True):
            if lang != 'zh':
                st.session_state.lang = 'zh'
                st.rerun()
    with c2:
        if st.button('English', type='primary' if lang == 'en' else 'secondary', use_container_width=True):
            if lang != 'en':
                st.session_state.lang = 'en'
                st.rerun()
    st.markdown('---')
    st.markdown(f'<div style="font-size:1.1rem;font-weight:700;color:{NAVY};margin-bottom:16px">{t("筛选", "Filter")}</div>', unsafe_allow_html=True)
    valid_dates = df_raw['date'].dropna()
    if not valid_dates.empty:
        date_range = st.date_input(t('日期范围', 'Date Range'),
                                   value=(valid_dates.min().date(), valid_dates.max().date()),
                                   min_value=valid_dates.min().date(), max_value=valid_dates.max().date())
    else:
        date_range = None
    # 渠道筛选 — 选项按当前语言显示，内部保留双语值用于过滤
    all_channels = sorted(df_raw['channel'].dropna().unique())
    ch_options = [disp(c) for c in all_channels]
    ch_disp_to_raw = dict(zip(ch_options, all_channels))
    sel_channel_disp = st.multiselect(t('渠道', 'Channel'), ch_options, default=[])
    sel_channel = [ch_disp_to_raw[d] for d in sel_channel_disp]
    # 类别筛选
    all_cats = sorted(df_raw['category'].dropna().unique())
    cat_options = [disp(c) for c in all_cats]
    cat_disp_to_raw = dict(zip(cat_options, all_cats))
    sel_category_disp = st.multiselect(t('类别', 'Category'), cat_options, default=[])
    sel_category = [cat_disp_to_raw[d] for d in sel_category_disp]
    st.markdown('---')
    if st.button(t('🔄 刷新数据', '🔄 Refresh Data'), use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── 筛选 ──
df = df_raw.copy()
if date_range and len(date_range) == 2:
    df = df[(df['date'].dt.date >= date_range[0]) & (df['date'].dt.date <= date_range[1])]
if sel_channel:  df = df[df['channel'].isin(sel_channel)]
if sel_category: df = df[df['category'].isin(sel_category)]
if df.empty:
    st.warning(t('当前筛选条件下无数据', 'No data for current filters'))
    st.stop()

# ── KPI ──
total    = len(df)
top_ch   = disp(df['channel'].value_counts().index[0])  if not df['channel'].value_counts().empty  else '—'
top_cat  = disp(df['category'].value_counts().index[0]) if not df['category'].value_counts().empty else '—'
trend_tmp = df.dropna(subset=['date'])
this_month_cnt = trend_tmp[trend_tmp['date'].dt.to_period('M') == pd.Timestamp.now().to_period('M')].shape[0]

# ── Hero Banner ──
st.markdown(f"""
<div class="hero">
  <h1>GHA 客服数据 <span class="gold">Dashboard</span></h1>
  <p>Customer Service Analytics · GHA Discovery</p>
  <div class="kpi-wrap">
    <div class="kpi"><div class="kpi-val">{total}</div><div class="kpi-lbl">{t('总咨询量', 'Total Inquiries')}</div></div>
    <div class="kpi"><div class="kpi-val">{this_month_cnt}</div><div class="kpi-lbl">{t('本月咨询', 'This Month')}</div></div>
    <div class="kpi"><div class="kpi-val">{top_ch}</div><div class="kpi-lbl">{t('最高频渠道', 'Top Channel')}</div></div>
    <div class="kpi"><div class="kpi-val">{top_cat}</div><div class="kpi-lbl">{t('最高频问题', 'Top Issue')}</div></div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════
# 板块 1：问题类别（树图）+ 渠道来源（甜甜圈）
# ═══════════════════════════════════════
col_a, col_b = st.columns([3, 2], gap='medium')

with col_a:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="card-title">Issue Distribution</div><div class="card-subtitle">{t("问题类别分布", "Issue Category Breakdown")}</div>', unsafe_allow_html=True)
    cat_df = df['category'].value_counts().reset_index()
    cat_df.columns = ['category', 'count']
    cat_df['short'] = cat_df['category'].apply(disp)
    fig = px.treemap(
        cat_df, path=['short'], values='count',
        color='count',
        color_continuous_scale=[[0, '#C8DFF0'], [0.5, GOLD], [1, CORAL]],
    )
    fig.update_traces(
        textinfo='label+value',
        textfont=dict(size=13, family='Inter, sans-serif'),
        hovertemplate=f'<b>%{{label}}</b><br>{t("咨询量", "Inquiries")}: %{{value}}<br>{t("占比", "Share")}: %{{percentRoot:.1%}}<extra></extra>',
        marker=dict(cornerradius=8),
    )
    fig.update_layout(
        paper_bgcolor='white',
        margin=dict(l=0, r=0, t=8, b=0), height=300,
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f'<div class="insight">💡 {insight_category(df)}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_b:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="card-title">Channel Source</div><div class="card-subtitle">{t("渠道来源分布", "Inquiry Channel Breakdown")}</div>', unsafe_allow_html=True)
    ch_df = df['channel'].value_counts().reset_index()
    ch_df.columns = ['channel', 'count']
    ch_df['short'] = ch_df['channel'].apply(disp)
    fig = go.Figure(go.Pie(
        labels=ch_df['short'], values=ch_df['count'],
        hole=0.6, marker=dict(colors=PALETTE[:len(ch_df)], line=dict(color='white', width=2)),
        textinfo='percent', textfont=dict(size=11),
        hovertemplate=f'%{{label}}<br><b>%{{value}}</b> {t("条", "records")} (%{{percent}})<extra></extra>',
        pull=[0.04] + [0] * (len(ch_df) - 1),
    ))
    fig.add_annotation(text=f'<b>{total}</b><br><span style="font-size:10px">{t("总计", "Total")}</span>',
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
# 板块 2：渠道 × 类别 气泡矩阵
# ═══════════════════════════════════════
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(f'<div class="card-title">Channel × Category Matrix</div><div class="card-subtitle">{t("各渠道问题类别分布", "Issue Distribution by Channel & Category")}</div>', unsafe_allow_html=True)

df_cc = df.copy()
df_cc['ch_short']  = df_cc['channel'].apply(disp)
df_cc['cat_short'] = df_cc['category'].apply(disp)
df_cc = df_cc[(df_cc['ch_short'] != '') & (df_cc['cat_short'] != '')]
cc_matrix = df_cc.groupby(['ch_short', 'cat_short']).size().reset_index(name='count')
max_count = cc_matrix['count'].max() if not cc_matrix.empty else 1

cat_colors = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(cc_matrix['cat_short'].unique())}
fig = go.Figure(go.Scatter(
    x=cc_matrix['ch_short'],
    y=cc_matrix['cat_short'],
    mode='markers+text',
    text=cc_matrix['count'],
    textfont=dict(size=12, color='white', family='Inter, sans-serif'),
    marker=dict(
        size=[max(28, int(20 + c / max_count * 56)) for c in cc_matrix['count']],
        color=[cat_colors.get(c, NAVY) for c in cc_matrix['cat_short']],
        opacity=0.82,
        line=dict(width=0),
    ),
    customdata=cc_matrix['count'],
    hovertemplate=f'<b>%{{x}}</b> · <b>%{{y}}</b><br>{t("数量", "Count")}: %{{customdata}}<extra></extra>',
))
fig.update_layout(
    paper_bgcolor='white', plot_bgcolor='white',
    margin=dict(l=0, r=0, t=8, b=20), height=320,
    xaxis=dict(tickfont=dict(size=11), showgrid=True, gridcolor='#F0F0F0', zeroline=False),
    yaxis=dict(tickfont=dict(size=11), showgrid=True, gridcolor='#F0F0F0', zeroline=False),
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)
st.markdown(f'<div class="insight">💡 {insight_ch_cat(df)}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════
# 板块 3：趋势
# ═══════════════════════════════════════
trend = df.dropna(subset=['date']).copy()
trend['month'] = trend['date'].dt.to_period('M').astype(str)
monthly_total = trend.groupby('month').size().reset_index(name='count')
monthly_total['cumulative'] = monthly_total['count'].cumsum()

trend_opts = [t('📅 每月新增', '📅 Monthly New'), t('📈 累计总量', '📈 Cumulative')]
trend_mode = st.radio(
    '', options=trend_opts,
    horizontal=True, label_visibility='collapsed', key='trend_mode',
)

if trend_mode == trend_opts[0]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="card-title">Monthly New Inquiries</div><div class="card-subtitle">{t("每月新增咨询量", "New Inquiries per Month")}</div>', unsafe_allow_html=True)
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=monthly_total['month'], y=monthly_total['count'],
        name=t('月新增', 'Monthly New'), marker_color=BLUE, marker_line_width=0,
        hovertemplate=f'%{{x}}<br>{t("新增", "New")}: <b>%{{y}}</b><extra></extra>',
    ))
    fig1.add_trace(go.Scatter(
        x=monthly_total['month'], y=monthly_total['count'],
        mode='lines+markers+text', name=t('月总计', 'Monthly'),
        text=monthly_total['count'],
        textposition='top center', textfont=dict(size=10, color=NAVY),
        line=dict(color=NAVY, width=2, dash='dot'), marker=dict(color=NAVY, size=5),
    ))
    fig1.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=0, r=0, t=8, b=0), height=300,
        legend=dict(orientation='h', y=-0.2, font=dict(size=9)),
        xaxis=dict(tickangle=-20, showgrid=False, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0', zeroline=False),
        bargap=0.35,
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown(f'<div class="insight">💡 {insight_trend(df)}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="card-title">Cumulative Total</div><div class="card-subtitle">{t("累计咨询量增长", "Cumulative Inquiry Growth")}</div>', unsafe_allow_html=True)
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=monthly_total['month'], y=monthly_total['count'],
        name=t('当月新增', 'Monthly New'), marker_color=BLUE, marker_line_width=0, opacity=0.35,
        hovertemplate=f'%{{x}}<br>{t("当月新增", "New")}: <b>%{{y}}</b><extra></extra>',
    ))
    fig2.add_trace(go.Scatter(
        x=monthly_total['month'], y=monthly_total['cumulative'],
        mode='lines+markers+text', name=t('累计总量', 'Cumulative'),
        text=monthly_total['cumulative'],
        textposition='top center', textfont=dict(size=10, color=GOLD),
        line=dict(color=GOLD, width=3),
        marker=dict(color=GOLD, size=8, line=dict(color='white', width=2)),
        fill='tozeroy', fillcolor='rgba(218,159,89,0.12)',
        hovertemplate=f'%{{x}}<br>{t("累计", "Cumulative")}: <b>%{{y}}</b><extra></extra>',
    ))
    fig2.update_layout(
        barmode='overlay', plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=0, r=0, t=8, b=0), height=300,
        legend=dict(orientation='h', y=-0.2, font=dict(size=9)),
        xaxis=dict(tickangle=-20, showgrid=False, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0', zeroline=False),
        bargap=0.3,
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown(f'<div class="insight">💡 {insight_trend(df)}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════
# 板块 4：热力图（平台 × 类别）
# ═══════════════════════════════════════
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(f'<div class="card-title">Platform × Category Heatmap</div><div class="card-subtitle">{t("平台与问题类别交叉热力图", "Platform vs. Category Heatmap")}</div>', unsafe_allow_html=True)

df_h = df[(df['platform'].str.strip() != '') & (df['category'].str.strip() != '')].copy()
df_h['pl_short']  = df_h['platform'].apply(disp)
df_h['cat_short'] = df_h['category'].apply(disp)
heat = df_h.groupby(['pl_short', 'cat_short']).size().unstack(fill_value=0)

if not heat.empty:
    fig = go.Figure(go.Heatmap(
        z=heat.values, x=heat.columns.tolist(), y=heat.index.tolist(),
        colorscale=[[0, '#F4F4F1'], [0.3, BLUE], [0.7, GOLD], [1, CORAL]],
        text=heat.values, texttemplate='%{text}', textfont=dict(size=12),
        hovertemplate=f'{t("平台", "Platform")}: %{{y}}<br>{t("类别", "Category")}: %{{x}}<br>{t("数量", "Count")}: <b>%{{z}}</b><extra></extra>',
        showscale=True,
        colorbar=dict(thickness=12, len=0.8, title=dict(text=t('数量', 'Count'), side='right')),
    ))
    fig.update_layout(
        paper_bgcolor='white', plot_bgcolor='white',
        margin=dict(l=0, r=0, t=8, b=0), height=260,
        xaxis=dict(tickangle=-20, tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=11)),
    )
    st.plotly_chart(fig, use_container_width=True)
    max_val = heat.values.max()
    max_pos = [(heat.index[r], heat.columns[c]) for r in range(heat.shape[0]) for c in range(heat.shape[1]) if heat.values[r][c] == max_val]
    if max_pos:
        pl, cat = max_pos[0]
        insight_txt = t(
            f'<b>{pl}</b> 平台的 <b>{cat}</b> 问题最集中（<b>{int(max_val)}</b> 条）。针对该组合定向制作解答内容，可有效减少重复咨询并提升平台口碑。',
            f'<b>{pl}</b> platform has the highest concentration of <b>{cat}</b> issues (<b>{int(max_val)}</b> records). Targeted content for this combination can reduce repeat inquiries and improve platform reputation.'
        )
        st.markdown(f'<div class="insight">💡 {insight_txt}</div>', unsafe_allow_html=True)
else:
    st.info(t('暂无足够数据生成热力图', 'Insufficient data for heatmap'))
st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════
# 板块 5：关键词气泡图 + 数据明细
# ═══════════════════════════════════════
col_e, col_f = st.columns([1, 2], gap='medium')

with col_e:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="card-title">Top Keywords</div><div class="card-subtitle">{t("高频关键词", "Top Keywords")}</div>', unsafe_allow_html=True)
    all_kw = []
    for kw in df['keywords'].dropna():
        all_kw.extend([k.strip() for k in str(kw).split(',') if k.strip()])
    if all_kw:
        top = Counter(all_kw).most_common(12)
        kw_df_b = pd.DataFrame(top, columns=['keyword', 'count'])
        n = len(kw_df_b)
        cols_n = 4
        x_pos = [i % cols_n for i in range(n)]
        y_pos = [-(i // cols_n) for i in range(n)]
        max_cnt = kw_df_b['count'].max()
        sizes = [max(32, int(24 + c / max_cnt * 52)) for c in kw_df_b['count']]
        rows_n = (n + cols_n - 1) // cols_n
        fig = go.Figure(go.Scatter(
            x=x_pos, y=y_pos,
            mode='markers+text',
            text=kw_df_b['keyword'],
            textposition='middle center',
            textfont=dict(size=11, color='white', family='Inter, sans-serif'),
            marker=dict(
                size=sizes,
                color=kw_df_b['count'],
                colorscale=[[0, BLUE], [0.5, GOLD], [1, PURPLE]],
                opacity=0.88,
                showscale=False,
                line=dict(width=0),
            ),
            customdata=kw_df_b['count'],
            hovertemplate=f'<b>%{{text}}</b><br>{t("出现", "Appeared")}: %{{customdata}} {t("次", "times")}<extra></extra>',
        ))
        fig.update_layout(
            paper_bgcolor='white', plot_bgcolor='white',
            xaxis=dict(visible=False, range=[-0.7, cols_n - 0.3]),
            yaxis=dict(visible=False, range=[-(rows_n - 0.3), 0.7]),
            margin=dict(l=0, r=0, t=8, b=0), height=300,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        top1, cnt1 = top[0]
        insight_txt = t(
            f'"<b>{top1}</b>" 是最高频关键词（<b>{cnt1}</b> 次），反映用户核心诉求，可作为内容选题方向优化社媒触达。',
            f'"<b>{top1}</b>" is the top keyword (<b>{cnt1}</b> occurrences), reflecting core user needs and suggesting content directions for social media reach optimization.'
        )
        st.markdown(f'<div class="insight">💡 {insight_txt}</div>', unsafe_allow_html=True)
    else:
        st.info(t('暂无关键词数据', 'No keyword data'))
    st.markdown('</div>', unsafe_allow_html=True)

with col_f:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="card-title">Records</div><div class="card-subtitle">{t("数据明细", "All Records")}</div>', unsafe_allow_html=True)
    show = df[['id', 'date', 'channel', 'platform', 'category', 'subcategory', 'keywords', 'description', 'notes']].sort_values('date', ascending=False).copy()
    show['date']     = show['date'].dt.strftime('%Y-%m-%d')
    show['channel']  = show['channel'].apply(disp)
    show['platform'] = show['platform'].apply(disp)
    show['category'] = show['category'].apply(disp)
    if lang == 'zh':
        col_names = ['ID', '日期', '渠道', '平台', '类别', '子类别', '关键词', '描述', '备注']
        col_cfg = {
            '描述':  st.column_config.TextColumn(width='large'),
            '备注':  st.column_config.TextColumn(width='medium'),
            '关键词': st.column_config.TextColumn(width='small'),
            '子类别': st.column_config.TextColumn(width='small'),
            '平台':  st.column_config.TextColumn(width='medium'),
        }
    else:
        col_names = ['ID', 'Date', 'Channel', 'Platform', 'Category', 'Sub-cat', 'Keywords', 'Description', 'Notes']
        col_cfg = {
            'Description': st.column_config.TextColumn(width='large'),
            'Notes':       st.column_config.TextColumn(width='medium'),
            'Keywords':    st.column_config.TextColumn(width='small'),
            'Sub-cat':     st.column_config.TextColumn(width='small'),
            'Platform':    st.column_config.TextColumn(width='medium'),
        }
    show.columns = col_names
    st.dataframe(show, use_container_width=True, height=320, column_config=col_cfg)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    f'<p style="text-align:right;color:#ccc;font-size:0.72rem;margin-top:8px">'
    f'{t(f"共 {len(df)} 条记录", f"{len(df)} records")} · '
    f'{t("数据每5分钟刷新", "Refreshes every 5 min")} · '
    f'GHA Discovery Customer Service</p>',
    unsafe_allow_html=True
)
