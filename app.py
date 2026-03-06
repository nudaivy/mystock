import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

# --- 1. UI 深度适配：iOS 17 窄边框质感 ---
st.set_page_config(page_title="Alpha Sniper Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #FFFFFF; }
    
    /* 灵动岛 */
    .dynamic-island {
        background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(15px);
        border-radius: 20px; padding: 10px; margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2); text-align: center;
        color: #FF3B30; font-weight: 600; font-size: 14px;
    }

    /* 极窄苹果信息卡片 (宽度优化) */
    .apple-card { 
        padding: 10px; border-radius: 12px; margin-bottom: 8px;
        background-color: #1C1C1E; border: 1px solid #2C2C2E;
        min-height: 280px; /* 保持与K线图对齐 */
    }

    .profit-hero { font-size: 28px; font-weight: 800; color: #FF3B30; margin: 2px 0; }
    
    /* 业务摘要小字 */
    .business-summary {
        font-size: 10px; color: #8E8E93; line-height: 1.3;
        margin-top: 8px; border-top: 0.5px solid #3A3A3C; padding-top: 8px;
    }

    .f-table { width: 100%; font-size: 10px; color: #AEAEB2; border-collapse: collapse; }
    .f-table td { border-bottom: 0.5px solid #3A3A3C; padding: 4px 0; }
    .f-val { color: #FFFFFF; font-weight: 600; text-align: right; }

    .buy-pill { background-color: #FF3B30; color: #FFF; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 800; }

    #MainMenu, footer, header, .stDeployButton { visibility: hidden; display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 策略引擎 ---
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

# --- 3. 数据渲染 ---
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
        if len(trades) % 2 != 0: buying_now.append(ticker)
        
        processed_data.append({
            "ticker": ticker, "profit": profit, "trades": trades, 
            "is_odd": (len(trades) % 2 != 0), "info": info, "df": test_df
        })
    except: continue

if buying_now:
    st.markdown(f"<div class='dynamic-island'>🏝️ 建议买入清单: {', '.join(buying_now)}</div>", unsafe_allow_html=True)

for item in processed_data:
    with st.container():
        buy_label = "<span class='buy-pill'>BUY</span>" if item['is_odd'] else ""
        st.markdown(f"##### {item['ticker']} {buy_label}", unsafe_allow_html=True)
        
        # --- 核心改动：调整列宽比例为 1:4 ---
        col1, col2 = st.columns([1, 4])
        
        with col1:
            # 详尽的板块与业务信息
            st.markdown(f"""
                <div class='apple-card'>
                    <div style='color:#8E8E93; font-size:10px;'>半年收益</div>
                    <div class='profit-hero'>{item['profit']*100:.1f}%</div>
                    <table class='f-table'>
                        <tr><td>板块</td><td class='f-val'>{item['info'].get('sector','N/A')}</td></tr>
                        <tr><td>行业</td><td class='f-val'>{item['info'].get('industry','N/A')}</td></tr>
                        <tr><td>营收增速</td><td class='f-val'>{item['info'].get('revenueGrowth',0)*100:.1f}%</td></tr>
                        <tr><td>目标价</td><td class='f-val' style='color:#FF3B30;'>${item['info'].get('targetMeanPrice','N/A')}</td></tr>
                    </table>
                    <div class='business-summary'>
                        <b>业务详述:</b><br>{item['info'].get('longBusinessSummary', '暂无业务描述')[:120]}...
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            # 专业 K 线图 (占据 80% 宽度)
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

            fig.update_layout(
                template="plotly_dark", xaxis_rangeslider_visible=False,
                height=300, margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False
            )
            fig.update_yaxes(showgrid=False, side="right", tickfont=dict(size=10))
            fig.update_xaxes(showgrid=False, tickfont=dict(size=10))
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"v8_{item['ticker']}")
        st.divider()
