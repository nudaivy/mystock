import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import json
import os

# --- 1. 核心性能：行情高速缓存 (TTL 60s) ---
@st.cache_data(ttl=60)
def fetch_master_data(tickers):
    data_dict = {}
    try:
        # 抓取大盘基准 QQQ
        qqq = yf.Ticker("QQQ").history(period="5d")
        qqq_chg = ((qqq['Close'].iloc[-1] - qqq['Close'].iloc[-2]) / qqq['Close'].iloc[-2]) * 100
    except:
        qqq_chg = 0.0

    for ticker in tickers:
        try:
            t_obj = yf.Ticker(ticker)
            df = t_obj.history(period="1y")
            if not df.empty:
                data_dict[ticker] = {"df": df, "info": t_obj.info}
        except: continue
    return data_dict, qqq_chg

# --- 2. 永久存储：持仓与价格记忆 ---
DB_FILE = "portfolio_db.json"
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_db()

# --- 3. UI 深度定制：iOS 17 黑暗动态风格 ---
st.set_page_config(page_title="Alpha Sniper Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #FFFFFF; }
    .portfolio-island { background: #1C1C1E; border-radius: 20px; padding: 20px; margin-bottom: 15px; border: 1px solid #2C2C2E; }
    
    /* 输入框统一背景 */
    div[data-baseweb="input"] { background-color: #2C2C2E !important; border-radius: 10px !important; }
    input { background-color: #2C2C2E !important; color: #FFFFFF !important; border: none !important; }
    .stTextInput>div>div, .stNumberInput>div>div { background-color: #2C2C2E !important; border: 1px solid #3A3A3C !important; border-radius: 10px !important; height: 45px !important; }

    /* 呼吸感：大涨个股边框 */
    .card-hot { border: 1.5px solid rgba(255, 59, 48, 0.6) !important; box-shadow: 0 0 20px rgba(255, 59, 48, 0.2); }
    
    .pnl-pill { padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 700; margin-left: 8px; border: 1px solid rgba(255,255,255,0.1); }
    .rs-tag { background: #3A3A3C; color: #AEAEB2; padding: 2px 8px; border-radius: 6px; font-size: 10px; margin-left: 8px; vertical-align: middle; }
    .rs-strong { color: #FF3B30; font-weight: 800; border: 0.5px solid #FF3B30; }

    .apple-card { padding: 10px; border-radius: 12px; margin-bottom: 8px; background-color: #1C1C1E; border: 1px solid #2C2C2E; min-height: 320px; transition: all 0.3s ease; }
    .profit-hero { font-size: 26px; font-weight: 800; color: #FF3B30; margin: 2px 0; }
    .concept-tag { display: inline-block; background: rgba(255, 59, 48, 0.1); color: #FF3B30; border: 0.5px solid #FF3B30; padding: 2px 8px; border-radius: 6px; font-size: 10px; font-weight: 600; margin: 2px; }
    .f-table { width: 100%; font-size: 10px; color: #AEAEB2; border-collapse: collapse; margin-top: 5px; }
    .f-table td { border-bottom: 0.5px solid #3A3A3C; padding: 4px 0; }
    .f-val { color: #FFFFFF; font-weight: 600; text-align: right; }
    #MainMenu, footer, header, .stDeployButton { visibility: hidden; display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 智能概念与高级策略 ---
def get_concepts(info):
    summary = info.get('longBusinessSummary', '').lower()
    mapping = {"AI算力": ["ai ", "computing", "gpu"], "数字资产": ["bitcoin", "crypto", "mining"], "大数据": ["big data", "analytics", "cloud"]}
    concepts = [k for k, v in mapping.items() if any(x in summary for x in v)]
    return concepts[:3] if concepts else ["科技成长"]

def run_pro_strategy(df):
    df = df.copy()
    df['High_15'] = df['High'].rolling(15).max()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, 0.001))))
    df['ATR'] = pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1).rolling(14).mean()
    
    fund, pos, b_price, max_p, trades = 1.0, 0, 0.0, 0.0, []
    for i in range(15, len(df)):
        p, atr, rsi = df['Close'].iloc[i], df['ATR'].iloc[i], df['RSI'].iloc[i]
        if pos == 0 and p >= df['High_15'].iloc[i-1] and rsi > 50:
            pos, b_price, max_p = 1, p, p
            trades.append({'date': df.index[i], 'type': 'buy', 'price': p})
        elif pos == 1:
            max_p = max(max_p, p)
            if p < (max_p - atr * 2.2):
                pos, fund = 0, fund * (p / b_price)
                trades.append({'date': df.index[i], 'type': 'sell', 'price': p})
    
    # 实时计算红色警报止损线
    current_atr = df['ATR'].iloc[-1]
    alert_line = max_p - current_atr * 2.2 if pos == 1 else None
    return fund - 1, trades, alert_line

# --- 5. 持仓管理与永久保存 ---
with st.container():
    st.markdown("<div class='portfolio-island'>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin-top:0;'>💼 永久资产看板</h3>", unsafe_allow_html=True)
    p_col1, p_col2, p_col3 = st.columns([1.5, 1.5, 1])
    with p_col1: new_ticker = st.text_input("代码", placeholder="BTDR").upper()
    with p_col2: new_cost = st.number_input("持有成本", min_value=0.0, step=0.01, format="%.2f")
    with p_col3:
        st.write("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("保存持仓", use_container_width=True):
            if new_ticker:
                st.session_state.portfolio[new_ticker] = new_cost
                save_db(st.session_state.portfolio)
                st.rerun()
    if st.button("清空所有记录", type="secondary"):
        st.session_state.portfolio = {}; save_db({}); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- 6. 数据处理循环 ---
ticker_list = ["BTDR", "NIO", "RCAT", "KTOS", "ABSI", "TER", "LAES", "DVLT", "INO", "PLTR", "IONQ", "NVNI", "CLSK"]
all_data, qqq_chg = fetch_master_data(ticker_list)
processed_results, portfolio_display = [], []

for ticker, data in all_data.items():
    df, info = data['df'], data['info']
    curr_p = df['Close'].iloc[-1]
    day_chg = ((curr_p - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
    profit, trades, alert_line = run_pro_strategy(df)
    
    # 计算 RS 强弱标签
    rs_val = day_chg - qqq_chg
    rs_class = "rs-strong" if rs_val > 0 else ""

    # 处理顶部动态标签 (永久保存后的盈亏)
    if ticker in st.session_state.portfolio:
        cost = st.session_state.portfolio[ticker]
        pnl_p = ((curr_p - cost) / cost) * 100
        pnl_v = curr_p - cost
        clr = "#FF3B30" if pnl_p >= 0 else "#34C759"
        portfolio_display.append(f"""
            <div style='background:#2C2C2E; padding:8px 15px; border-radius:15px; border:1px solid #3A3A3C; margin-bottom:10px; display:inline-block; margin-right:10px;'>
                <b>{ticker}</b> <span style='color:#8E8E93;'>@{cost}</span>
                <span class='pnl-pill' style='background:{clr}22; color:{clr};'>{pnl_p:+.2f}% (${pnl_v:+.2f})</span>
            </div>
        """)

    processed_results.append({
        "ticker": ticker, "profit": profit, "trades": trades, "day_chg": day_chg,
        "info": info, "df": df.tail(120), "curr_p": curr_p, "alert": alert_line,
        "concepts": get_concepts(info), "rs": rs_val, "rs_class": rs_class
    })

# 顶部渲染
if portfolio_display: st.markdown(f"<div>{''.join(portfolio_display)}</div>", unsafe_allow_html=True)

# --- 7. 列表渲染 ---
for item in processed_results:
    with st.container():
        st.markdown(f"##### {item['ticker']} <span class='rs-tag {item['rs_class']}'>RS: {item['rs']:+.1f}%</span>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 4])
        with col1:
            hot_style = "card-hot" if item['day_chg'] > 5 else ""
            tags = "".join([f"<span class='concept-tag'>{c}</span>" for c in item['concepts']])
            st.markdown(f"""
                <div class='apple-card {hot_style}'>
                    <div style='color:#8E8E93; font-size:10px;'>180D策略收益</div>
                    <div class='profit-hero'>{item['profit']*100:.1f}%</div>
                    <div style='margin: 8px 0;'>{tags}</div>
                    <table class='f-table'>
                        <tr><td>最新价格</td><td class='f-val'>${item['curr_p']:.2f}</td></tr>
                        <tr><td>今日涨跌</td><td class='f-val' style='color:{"#FF3B30" if item['day_chg']>=0 else "#34C759"};'>{item['day_chg']:+.2f}%</td></tr>
                        <tr><td>风险警报线</td><td class='f-val' style='color:#FF3B30;'>{f"${item['alert']:.2f}" if item['alert'] else "N/A"}</td></tr>
                    </table>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            fig = go.Figure(data=[go.Candlestick(x=item['df'].index, open=item['df']['Open'], high=item['df']['High'], low=item['df']['Low'], close=item['df']['Close'], increasing_line_color='#FF3B30', decreasing_line_color='#34C759', increasing_fillcolor='#FF3B30', decreasing_fillcolor='#34C759')])
            if item['alert']:
                fig.add_hline(y=item['alert'], line_dash="dot", line_color="#FF3B30", line_width=2, annotation_text="止损线", annotation_position="bottom left")
            if item['ticker'] in st.session_state.portfolio:
                fig.add_hline(y=st.session_state.portfolio[item['ticker']], line_dash="dash", line_color="#FFFFFF", line_width=1, annotation_text="成本")
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=320, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"v_final_{item['ticker']}")
        st.divider()
