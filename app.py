import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

# --- 1. UI 全局配置：iOS 17 原生质感适配 ---
st.set_page_config(page_title="Alpha Sniper", layout="wide")
st.markdown("""
    <style>
    /* 全局背景：纯黑适配 OLED 屏幕 */
    .main { background-color: #000000; color: #FFFFFF; }
    
    /* 灵动岛风格置顶汇总 */
    .dynamic-island {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        border-radius: 25px;
        padding: 12px 20px;
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        text-align: center;
        font-weight: 600;
        color: #30D158; /* Apple 绿色 */
    }

    /* 苹果风格卡片 */
    .apple-card { 
        padding: 18px; border-radius: 20px; margin-bottom: 15px;
        background-color: #1C1C1E; 
        border: 1px solid #2C2C2E;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
    }

    /* 收益大数字 */
    .profit-hero {
        font-size: 42px; font-weight: 800; color: #30D158;
        letter-spacing: -1px; margin: 10px 0;
    }

    /* 买入标签 */
    .buy-pill { 
        background-color: #30D158; color: #000000;
        padding: 4px 12px; border-radius: 50px;
        font-size: 12px; font-weight: 700; text-transform: uppercase;
    }

    /* 概念小胶囊 */
    .pill {
        background-color: #3A3A3C; color: #AEAEB2;
        padding: 3px 10px; border-radius: 12px;
        font-size: 10px; margin-right: 5px; display: inline-block;
    }

    /* 隐藏所有网页痕迹 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心逻辑（保持你的 180D/50% 破解算法） ---
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

# --- 3. 页面渲染 ---
st.write("") # 留出刘海屏空间
default_tickers = "BTDR, NIO, RCAT, KTOS, ABSI, TER, LAES, DVLT, INO, PLTR, IONQ, NVNI, CLSK"
ticker_list = list(dict.fromkeys([t.strip().upper() for t in default_tickers.split(",")]))

# 预计算：找出所有“可以买入”的标的用于灵动岛显示
buying_now = []
all_results = []

for ticker in ticker_list:
    try:
        t_obj = yf.Ticker(ticker)
        data = t_obj.history(period="1y")
        if data.empty: continue
        profit, trades = run_strategy(data.tail(180))
        info = t_obj.info
        
        is_odd = len(trades) % 2 != 0
        if is_odd: buying_now.append(ticker)
        
        all_results.append({
            "ticker": ticker, "profit": profit, "trades": trades, 
            "is_odd": is_odd, "info": info, "data": data.tail(180)
        })
    except: continue

# --- 灵动岛置顶 ---
if buying_now:
    st.markdown(f"""<div class='dynamic-island'>🏝️ 今日头号猎物: {", ".join(buying_now)}</div>""", unsafe_allow_html=True)

# --- 列表渲染 ---
for res in all_results:
    with st.container():
        # 头部：代码 + 买入标签
        buy_tag = "<span class='buy-pill'>BUY</span>" if res['is_odd'] else ""
        st.markdown(f"#### {res['ticker']} {buy_tag}", unsafe_allow_html=True)
        
        # 核心卡片
        st.markdown(f"""
            <div class='apple-card'>
                <div style='color: #8E8E93; font-size: 12px;'>180天累计收益</div>
                <div class='profit-hero'>{res['profit']*100:.1f}%</div>
                <div style='margin-bottom: 10px;'>
                    <span class='pill'>{res['info'].get('sector', 'N/A')}</span>
                    <span class='pill'>Target: ${res['info'].get('targetMeanPrice', 'N/A')}</span>
                </div>
                <div style='color: #8E8E93; font-size: 11px;'>
                    信号追踪: {len(res['trades'])} Trace | 营收增速: {res['info'].get('revenueGrowth', 0)*100:.1f}%
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 迷你 K 线图 (适配手机宽度)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=res['data'].index, y=res['data']['Close'], line=dict(color='#30D158', width=2), fill='tozeroy', fillcolor='rgba(48, 209, 88, 0.1)'))
        fig.update_layout(template="plotly_dark", xaxis_visible=False, yaxis_visible=False, height=120, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"mini_{res['ticker']}")
        
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
