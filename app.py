import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import json
import os

# --- 1. 永久存储核心逻辑 ---
DB_FILE = "portfolio_db.json"

def load_stored_data():
    """从本地文件读取已保存的持仓数据"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_stored_data(data):
    """将持仓数据永久保存到本地文件"""
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

# 初始化：优先从本地文件加载，若没有则为空字典
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_stored_data()

# --- 2. UI 极致适配 ---
st.set_page_config(page_title="Alpha Sniper Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #FFFFFF; }
    .portfolio-island { background: #1C1C1E; border-radius: 20px; padding: 20px; margin-bottom: 15px; border: 1px solid #2C2C2E; }
    
    /* 统一输入框背景色 */
    div[data-baseweb="input"] { background-color: #2C2C2E !important; border-radius: 10px !important; }
    input { background-color: #2C2C2E !important; color: #FFFFFF !important; border: none !important; }
    .stTextInput>div>div, .stNumberInput>div>div { background-color: #2C2C2E !important; border: 1px solid #3A3A3C !important; border-radius: 10px !important; height: 45px !important; }

    /* 盈亏标签样式 */
    .pnl-pill { padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 700; margin-left: 8px; border: 1px solid rgba(255,255,255,0.1); }
    
    .dynamic-island { background: rgba(255, 59, 48, 0.15); backdrop-filter: blur(15px); border-radius: 15px; padding: 12px; margin-bottom: 25px; border: 1px solid rgba(255, 59, 48, 0.3); text-align: center; color: #FF3B30; font-weight: 700; font-size: 14px; }
    .apple-card { padding: 10px; border-radius: 12px; margin-bottom: 8px; background-color: #1C1C1E; border: 1px solid #2C2C2E; min-height: 280px; }
    .profit-hero { font-size: 26px; font-weight: 800; color: #FF3B30; margin: 2px 0; }
    .concept-tag { display: inline-block; background: rgba(255, 59, 48, 0.1); color: #FF3B30; border: 0.5px solid #FF3B30; padding: 2px 8px; border-radius: 6px; font-size: 10px; font-weight: 600; margin: 2px; }
    .f-table { width: 100%; font-size: 10px; color: #AEAEB2; border-collapse: collapse; margin-top: 5px; }
    .f-table td { border-bottom: 0.5px solid #3A3A3C; padding: 4px 0; }
    .f-val { color: #FFFFFF; font-weight: 600; text-align: right; }
    .buy-pill { background-color: #FF3B30; color: #FFF; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 800; }
    #MainMenu, footer, header, .stDeployButton { visibility: hidden; display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 策略引擎与概念识别 ---
def get_detailed_concepts(info):
    summary = info.get('longBusinessSummary', '').lower()
    industry = info.get('industry', '').lower()
    concepts = []
    mapping = {"AI算力": ["ai ", "computing", "gpu"], "数字资产": ["bitcoin", "crypto", "mining"], "大数据": ["big data", "analytics", "cloud"]}
    for label, keys in mapping.items():
        if any(k in summary or k in industry for k in keys): concepts.append(label)
    return concepts[:3] if concepts else ["科技成长"]

def run_strategy(df):
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
            trades.append({'date': df.index[i], 'type': 'buy', 'price': b_price})
        elif pos == 1:
            if p > max_p: max_p = p
            if p < (max_p - atr * 2.2):
                pos, fund = 0, fund * (p / b_price)
                trades.append({'date': df.index[i], 'type': 'sell', 'price': p})
    return fund - 1, trades

# --- 4. 持仓录入交互 ---
with st.container():
    st.markdown("<div class='portfolio-island'>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin-top:0;'>💼 永久资产看板</h3>", unsafe_allow_html=True)
    p_col1, p_col2, p_col3 = st.columns([1.5, 1.5, 1])
    with p_col1:
        new_ticker = st.text_input("代码", placeholder="如 BTDR").upper()
    with p_col2:
        new_cost = st.number_input("持有成本", min_value=0.0, step=0.01, format="%.2f")
    with p_col3:
        st.write("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("保存并更新", use_container_width=True):
            if new_ticker:
                st.session_state.portfolio[new_ticker] = new_cost
                save_stored_data(st.session_state.portfolio) # 保存到本地文件
                st.toast(f"✅ {new_ticker} 数据已永久保存")
                st.rerun()
    
    if st.button("清空所有持仓记录", type="secondary"):
        st.session_state.portfolio = {}
        save_stored_data({}) # 清空文件
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- 5. 实时盈亏展示与渲染 ---
ticker_list = ["BTDR", "NIO", "RCAT", "KTOS", "ABSI", "TER", "LAES", "DVLT", "INO", "PLTR", "IONQ", "NVNI", "CLSK"]
processed_data, buying_now, portfolio_display = [], [], []

for ticker in ticker_list:
    try:
        t_obj = yf.Ticker(ticker)
        raw_data = t_obj.history(period="1y")
        if raw_data.empty: continue
        curr_p = raw_data['Close'].iloc[-1]
        profit, trades = run_strategy(raw_data.tail(180))
        is_odd = (len(trades) % 2 != 0)
        if is_odd: buying_now.append(ticker)
        
        # 处理顶部永久盈亏标签
        if ticker in st.session_state.portfolio:
            cost = st.session_state.portfolio[ticker]
            pnl_p = ((curr_p - cost) / cost) * 100
            pnl_v = curr_p - cost
            color = "#FF3B30" if pnl_p >= 0 else "#34C759"
            portfolio_display.append(f"""
                <div style='background:#2C2C2E; padding:8px 15px; border-radius:15px; border:1px solid #3A3A3C; margin-bottom:10px; display:inline-block; margin-right:10px;'>
                    <b>{ticker}</b> <span style='color:#8E8E93;'>@{cost}</span>
                    <span class='pnl-pill' style='background:{color}33; color:{color};'>
                        {"+" if pnl_p >= 0 else ""}{pnl_p:.2f}% (${pnl_v:.2f})
                    </span>
                </div>
            """)

        processed_data.append({
            "ticker": ticker, "profit": profit, "trades": trades, "is_odd": is_odd, 
            "info": t_obj.info, "df": raw_data.tail(180), "curr_p": curr_p,
            "concepts": get_detailed_concepts(t_obj.info)
        })
    except: continue

# 渲染顶部信息
if portfolio_display:
    st.markdown(f"<div style='margin-bottom:20px;'>{''.join(portfolio_display)}</div>", unsafe_allow_html=True)
if buying_now:
    st.markdown(f"<div class='dynamic-island'>🏝️ 今日建议买入: {', '.join(buying_now)}</div>", unsafe_allow_html=True)

# 列表渲染
for item in processed_data:
    with st.container():
        buy_label = "<span class='buy-pill'>BUY</span>" if item['is_odd'] else ""
        st.markdown(f"##### {item['ticker']} {buy_label}", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 4])
        with col1:
            tags = "".join([f"<span class='concept-tag'>{c}</span>" for c in item['concepts']])
            st.markdown(f"<div class='apple-card'><div style='color:#8E8E93; font-size:10px;'>180D策略收益</div><div class='profit-hero'>{item['profit']*100:.1f}%</div><div style='margin: 8px 0;'>{tags}</div><table class='f-table'><tr><td>现价</td><td class='f-val'>${item['curr_p']:.2f}</td></tr><tr><td>营收增速</td><td class='f-val'>{item['info'].get('revenueGrowth',0)*100:.1f}%</td></tr><tr><td>目标价</td><td class='f-val' style='color:#FF3B30;'>${item['info'].get('targetMeanPrice','N/A')}</td></tr></table></div>", unsafe_allow_html=True)
        with col2:
            fig = go.Figure(data=[go.Candlestick(x=item['df'].index, open=item['df']['Open'], high=item['df']['High'], low=item['df']['Low'], close=item['df']['Close'], increasing_line_color='#FF3B30', decreasing_line_color='#34C759', increasing_fillcolor='#FF3B30', decreasing_fillcolor='#34C759')])
            if item['ticker'] in st.session_state.portfolio:
                fig.add_hline(y=st.session_state.portfolio[item['ticker']], line_dash="dash", line_color="#FFFFFF", line_width=1)
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=280, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"v16_{item['ticker']}")
