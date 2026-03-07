import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

# --- 1. UI 深度适配 ---
st.set_page_config(page_title="Alpha Sniper Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #FFFFFF; }
    .portfolio-island { background: #1C1C1E; border-radius: 20px; padding: 20px; margin-bottom: 15px; border: 1px solid #2C2C2E; }
    .dynamic-island {
        background: rgba(255, 59, 48, 0.15); backdrop-filter: blur(15px);
        border-radius: 15px; padding: 12px; margin-bottom: 25px;
        border: 1px solid rgba(255, 59, 48, 0.3); text-align: center;
        color: #FF3B30; font-weight: 700; font-size: 14px;
    }
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #2C2C2E !important; color: #FFFFFF !important; 
        border: 1px solid #3A3A3C !important; border-radius: 10px !important;
    }
    .apple-card { padding: 10px; border-radius: 12px; margin-bottom: 8px; background-color: #1C1C1E; border: 1px solid #2C2C2E; min-height: 320px; }
    .profit-hero { font-size: 26px; font-weight: 800; color: #FF3B30; margin: 2px 0; }
    
    /* 标签样式优化 */
    .concept-tag {
        display: inline-block; background: rgba(255, 59, 48, 0.1);
        color: #FF3B30; border: 0.5px solid #FF3B30;
        padding: 2px 8px; border-radius: 6px; font-size: 10px; font-weight: 600; margin: 2px;
    }

    .f-table { width: 100%; font-size: 10px; color: #AEAEB2; border-collapse: collapse; margin-top: 5px; }
    .f-table td { border-bottom: 0.5px solid #3A3A3C; padding: 4px 0; }
    .f-val { color: #FFFFFF; font-weight: 600; text-align: right; }
    .buy-pill { background-color: #FF3B30; color: #FFF; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 800; }
    #MainMenu, footer, header, .stDeployButton { visibility: hidden; display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 智能概念识别函数 ---
def get_detailed_concepts(info):
    summary = info.get('longBusinessSummary', '').lower()
    industry = info.get('industry', '').lower()
    concepts = []
    
    # 定义核心关键词映射
    mapping = {
        "AI算力": ["artificial intelligence", " ai ", "computing", "gpu", "data center", "hpc"],
        "数字资产": ["bitcoin", "crypto", "digital asset", "mining", "blockchain"],
        "大数据": ["big data", "analytics", "software as a service", "data solution", "cloud"],
        "国防科技": ["defense", "aerospace", "military", "weapon", "national security"],
        "新能源": ["electric vehicle", "battery", "solar", "renewable", "clean energy"],
        "半导体": ["semiconductor", " chip ", "foundry", "wafer"],
        "生物医药": ["biopharmaceutical", "biotech", "drug", "clinical", "therapy"]
    }
    
    for label, keys in mapping.items():
        if any(k in summary or k in industry for k in keys):
            concepts.append(label)
    
    # 默认兜底
    if not concepts:
        concepts.append(info.get('sector', '科技成长'))
    
    return concepts[:4] # 最多显示4个核心概念

# --- 3. 策略引擎 (保持不变) ---
def run_strategy(df):
    df = df.copy()
    df['High_15'] = df['High'].rolling(15).max()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, 0.001))))
    h_l, h_c, l_c = df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()
    df['ATR'] = pd.concat([h_l, h_c, l_c], axis=1).max(axis=1).rolling(14).mean()
    fund, pos, b_price, max_p, trades = 1.0, 0, 0.0, 0.0, []
    for i in range(15, len(df)):
        p, atr, rsi = df['Close'].iloc[i], df['ATR'].iloc[i], df['RSI'].iloc[i]
        if pos == 0 and p >= df['High_15'].iloc[i-1] and rsi > 50:
            pos, b_price, max_p = 1, p, p
            trades.append({'date': df.index[i], 'type': 'buy', 'price': b_price})
        elif pos == 1:
            if p > max_p: max_p = p
            if p < (max_p - atr * 2.2):
                pos, fund = 0, fund * (p / b_price)
                trades.append({'date': df.index[i], 'type': 'sell', 'price': p})
    return fund - 1, trades

# --- 4. 持仓管理 ---
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}

with st.container():
    st.markdown("<div class='portfolio-island'>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin-top:0;'>💼 持仓与成本管理</h3>", unsafe_allow_html=True)
    p_col1, p_col2, p_col3 = st.columns([1.5, 1.5, 1])
    with p_col1:
        new_ticker = st.text_input("代码 (Ticker)", placeholder="输入如 BTDR").upper()
    with p_col2:
        new_cost = st.number_input("持有成本 (Price)", min_value=0.0, step=0.01, format="%.2f")
    with p_col3:
        st.write("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("确认录入", use_container_width=True):
            if new_ticker:
                st.session_state.portfolio[new_ticker] = new_cost
                st.toast(f"✅ {new_ticker} 录入成功")
    st.markdown("</div>", unsafe_allow_html=True)

# --- 5. 数据抓取与汇总 ---
ticker_list = ["BTDR", "NIO", "RCAT", "KTOS", "ABSI", "TER", "LAES", "DVLT", "INO", "PLTR", "IONQ", "NVNI", "CLSK"]
processed_data, buying_now = [], []

for ticker in ticker_list:
    try:
        t_obj = yf.Ticker(ticker)
        raw_data = t_obj.history(period="1y")
        if raw_data.empty: continue
        info = t_obj.info
        test_df = raw_data.tail(180)
        profit, trades = run_strategy(test_df)
        is_odd = (len(trades) % 2 != 0)
        if is_odd: buying_now.append(ticker)
        processed_data.append({
            "ticker": ticker, "profit": profit, "trades": trades, 
            "is_odd": is_odd, "info": info, "df": test_df,
            "concepts": get_detailed_concepts(info)
        })
    except: continue

if buying_now:
    st.markdown(f"<div class='dynamic-island'>🏝️ 今日建议买入: {', '.join(buying_now)}</div>", unsafe_allow_html=True)

# --- 6. 列表渲染 ---
for item in processed_data:
    with st.container():
        buy_label = "<span class='buy-pill'>BUY</span>" if item['is_odd'] else ""
        st.markdown(f"##### {item['ticker']} {buy_label}", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 4])
        with col1:
            # 渲染概念标签
            concept_html = "".join([f"<span class='concept-tag'>{c}</span>" for c in item['concepts']])
            st.markdown(f"""
                <div class='apple-card'>
                    <div style='color:#8E8E93; font-size:10px;'>180D策略收益</div>
                    <div class='profit-hero'>{item['profit']*100:.1f}%</div>
                    <div style='margin: 5px 0;'>{concept_html}</div>
                    <table class='f-table'>
                        <tr><td>营收增速</td><td class='f-val'>{item['info'].get('revenueGrowth',0)*100:.1f}%</td></tr>
                        <tr><td>自由现金流</td><td class='f-val'>${item['info'].get('freeCashflow',0)/1e6:.1f}M</td></tr>
                        <tr><td>机构目标价</td><td class='f-val' style='color:#FF3B30;'>${item['info'].get('targetMeanPrice','N/A')}</td></tr>
                    </table>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            fig = go.Figure(data=[go.Candlestick(
                x=item['df'].index, open=item['df']['Open'], high=item['df']['High'],
                low=item['df']['Low'], close=item['df']['Close'],
                increasing_line_color='#FF3B30', decreasing_line_color='#34C759',
                increasing_fillcolor='#FF3B30', decreasing_fillcolor='#34C759'
            )])
            for t in item['trades']:
                is_buy = t['type'] == 'buy'
                fig.add_trace(go.Scatter(
                    x=[t['date']], y=[t['price']], mode='markers+text',
                    marker=dict(symbol="triangle-up" if is_buy else "triangle-down", size=10, color="#FF3B30" if is_buy else "#34C759"),
                    text=["B" if is_buy else "S"], textposition="top center", showlegend=False
                ))
            if item['ticker'] in st.session_state.portfolio:
                cost = st.session_state.portfolio[item['ticker']]
                fig.add_hline(y=cost, line_dash="dash", line_color="#FFFFFF", line_width=1, annotation_text=f"持仓: {cost}", annotation_font_size=10)
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=320, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
            fig.update_yaxes(showgrid=False, side="right", tickfont=dict(size=10))
            fig.update_xaxes(showgrid=False, tickfont=dict(size=10))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"v12_{item['ticker']}")
        st.divider()
