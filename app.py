import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import json
import os

# --- 1. 性能优化：引入缓存机制 ---
@st.cache_data(ttl=60) # 缓存60秒，避免频繁抓取
def fetch_stock_data(tickers):
    data_dict = {}
    qqq = yf.Ticker("QQQ").history(period="1y")
    qqq_change = ((qqq['Close'].iloc[-1] - qqq['Close'].iloc[-2]) / qqq['Close'].iloc[-2]) * 100
    
    for ticker in tickers:
        try:
            t_obj = yf.Ticker(ticker)
            df = t_obj.history(period="1y")
            if not df.empty:
                data_dict[ticker] = {"df": df, "info": t_obj.info}
        except: continue
    return data_dict, qqq_change

# --- 2. 存储逻辑 ---
DB_FILE = "portfolio_db.json"
def load_stored_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {}

def save_stored_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_stored_data()

# --- 3. UI 增强 (动效与呼吸感) ---
st.set_page_config(page_title="Alpha Sniper Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #FFFFFF; }
    .portfolio-island { background: #1C1C1E; border-radius: 20px; padding: 20px; border: 1px solid #2C2C2E; }
    
    /* 呼吸感：大涨个股边框高亮 */
    .card-hot { border: 1.5px solid rgba(255, 59, 48, 0.6) !important; box-shadow: 0 0 15px rgba(255, 59, 48, 0.2); }
    
    .pnl-pill { padding: 4px 10px; border-radius: 10px; font-size: 11px; font-weight: 700; margin-left: 5px; }
    .rs-tag { background: #3A3A3C; color: #AEAEB2; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 5px; }
    .rs-strong { color: #FF3B30; font-weight: 700; } /* 相对强弱高亮 */

    .dynamic-island { background: rgba(255, 59, 48, 0.1); border-radius: 15px; padding: 12px; margin-bottom: 20px; border: 1px solid rgba(255, 59, 48, 0.2); text-align: center; color: #FF3B30; font-weight: 700; }
    .apple-card { padding: 15px; border-radius: 18px; background-color: #1C1C1E; border: 1px solid #2C2C2E; min-height: 320px; transition: 0.3s; }
    .concept-tag { display: inline-block; background: rgba(255, 59, 48, 0.1); color: #FF3B30; border: 0.5px solid #FF3B30; padding: 2px 8px; border-radius: 6px; font-size: 10px; margin: 2px; }
    .f-table { width: 100%; font-size: 11px; color: #AEAEB2; margin-top: 10px; }
    .f-val { color: #FFFFFF; font-weight: 600; text-align: right; }
    
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. 增强型策略引擎 ---
def run_strategy_pro(df):
    df = df.copy()
    # 基础指标
    df['High_15'] = df['High'].rolling(15).max()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, 0.001))))
    # ATR 止损计算
    df['ATR'] = pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1).rolling(14).mean()
    
    pos, max_p, trades = 0, 0.0, []
    for i in range(15, len(df)):
        p, atr = df['Close'].iloc[i], df['ATR'].iloc[i]
        if pos == 0 and p >= df['High_15'].iloc[i-1] and df['RSI'].iloc[i] > 50:
            pos, max_p = 1, p
            trades.append({'date': df.index[i], 'type': 'buy', 'price': p, 'atr': atr})
        elif pos == 1:
            max_p = max(max_p, p)
            stop_price = max_p - atr * 2.2
            if p < stop_price:
                pos = 0
                trades.append({'date': df.index[i], 'type': 'sell', 'price': p})
    
    # 计算当前警报线
    last_atr = df['ATR'].iloc[-1]
    current_stop = max_p - last_atr * 2.2 if pos == 1 else None
    return trades, current_stop

# --- 5. 交互界面 ---
ticker_list = ["BTDR", "NIO", "RCAT", "KTOS", "ABSI", "TER", "LAES", "DVLT", "INO", "PLTR", "IONQ", "NVNI", "CLSK"]

with st.container():
    st.markdown("<div class='portfolio-island'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.5, 1.5, 1])
    with c1: t_in = st.text_input("代码", key="tk").upper()
    with c2: p_in = st.number_input("成本", min_value=0.0, step=0.01)
    with c3:
        st.write("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("同步持仓", use_container_width=True):
            if t_in: 
                st.session_state.portfolio[t_in] = p_in
                save_stored_data(st.session_state.portfolio)
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- 6. 核心渲染循环 ---
all_data, qqq_chg = fetch_stock_data(ticker_list)
buying_now, portfolio_pills = [], []

for ticker, data in all_data.items():
    df, info = data['df'], data['info']
    curr_p = df['Close'].iloc[-1]
    day_chg = ((curr_p - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
    trades, alert_line = run_strategy_pro(df)
    
    # 相对强弱计算 (RS)
    rs_val = day_chg - qqq_chg
    rs_class = "rs-strong" if rs_val > 0 else ""
    
    # 持仓标签
    if ticker in st.session_state.portfolio:
        cost = st.session_state.portfolio[ticker]
        pnl = ((curr_p - cost) / cost) * 100
        clr = "#FF3B30" if pnl >= 0 else "#34C759"
        portfolio_pills.append(f"<div style='background:#2C2C2E; padding:8px; border-radius:12px; display:inline-block; margin:5px; border:1px solid #3A3A3C;'><b>{ticker}</b> @{cost} <span class='pnl-pill' style='background:{clr}22; color:{clr};'>{pnl:.1f}%</span></div>")

    # 渲染卡片
    with st.container():
        is_hot = "card-hot" if day_chg > 5 else ""
        st.markdown(f"##### {ticker} <span class='rs-tag {rs_class}'>RS: {rs_val:+.1f}%</span>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 4])
        
        with col1:
            st.markdown(f"""
                <div class='apple-card {is_hot}'>
                    <div style='color:#8E8E93; font-size:10px;'>今日涨跌</div>
                    <div style='font-size:24px; font-weight:800; color:{"#FF3B30" if day_chg>=0 else "#34C759"};'>{day_chg:+.2f}%</div>
                    <table class='f-table'>
                        <tr><td>现价</td><td class='f-val'>${curr_p:.2f}</td></tr>
                        <tr><td>QQQ基准</td><td class='f-val'>{qqq_chg:+.1f}%</td></tr>
                        <tr><td>风险警报</td><td class='f-val' style='color:#FF3B30;'>{f"${alert_line:.2f}" if alert_line else "未持仓"}</td></tr>
                    </table>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            fig = go.Figure(data=[go.Candlestick(x=df.tail(120).index, open=df.tail(120)['Open'], high=df.tail(120)['High'], low=df.tail(120)['Low'], close=df.tail(120)['Close'], increasing_line_color='#FF3B30', decreasing_line_color='#34C759', increasing_fillcolor='#FF3B30', decreasing_fillcolor='#34C759')])
            
            # 绘制止损警报线 (红色虚线)
            if alert_line:
                fig.add_hline(y=alert_line, line_dash="dot", line_color="#FF3B30", line_width=2, annotation_text="风险线 (ATR Stop)")
            
            # 绘制成本线 (白色虚线)
            if ticker in st.session_state.portfolio:
                fig.add_hline(y=st.session_state.portfolio[ticker], line_dash="dash", line_color="#FFFFFF", line_width=1)

            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=300, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"v2_{ticker}")

# 顶部渲染
st.sidebar.markdown("### 📊 持仓状态")
st.sidebar.markdown("".join(portfolio_pills), unsafe_allow_html=True)
