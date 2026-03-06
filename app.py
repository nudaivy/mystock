import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

# --- 1. UI 深度适配：iOS 17 风格 + 红涨绿跌定制 ---
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

    /* 苹果信息卡片 */
    .apple-card { 
        padding: 16px; border-radius: 18px; margin-bottom: 12px;
        background-color: #1C1C1E; border: 1px solid #2C2C2E;
    }

    .profit-hero { font-size: 36px; font-weight: 800; color: #FF3B30; margin: 5px 0; }
    
    /* 概念标签 */
    .pill {
        background-color: #3A3A3C; color: #FF3B30; border: 0.5px solid #FF3B30;
        padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-right: 5px;
    }

    /* 财务数据表 */
    .f-table { width: 100%; font-size: 12px; color: #AEAEB2; border-collapse: collapse; margin-top: 10px; }
    .f-table td { border-bottom: 0.5px solid #3A3A3C; padding: 6px 0; }
    .f-val { color: #FFFFFF; font-weight: 600; text-align: right; }

    .buy-pill { background-color: #FF3B30; color: #FFF; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 800; }

    /* 隐藏杂项 */
    #MainMenu, footer, header, .stDeployButton { visibility: hidden; display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心策略引擎 ---
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

# --- 3. 页面渲染逻辑 ---
ticker_list = ["BTDR", "NIO", "RCAT", "KTOS", "ABSI", "TER", "LAES", "DVLT", "INO", "PLTR", "IONQ", "NVNI", "CLSK"]
processed_data = []
buying_now = []

for ticker in ticker_list:
    try:
        t_obj = yf.Ticker(ticker)
        raw_data = t_obj.history(period="1y")
        if raw_data.empty: continue
        info = t_obj.info
        test_df = raw_data.tail(180)
        profit, trades = run_strategy(test_df)
        
        is_odd = len(trades) % 2 != 0
        if is_odd: buying_now.append(ticker)
        
        summary = info.get('longBusinessSummary', '').lower()
        tags = []
        if any(x in summary for x in ["bitcoin", "crypto"]): tags.append("加密矿业")
        if any(x in summary for x in ["ai", "intelligence"]): tags.append("AI算力")
        if "defense" in summary: tags.append("国防科技")
        
        processed_data.append({
            "ticker": ticker, "profit": profit, "trades": trades, 
            "is_odd": is_odd, "info": info, "df": test_df, "tags": tags
        })
    except: continue

# 置顶灵动岛
if buying_now:
    st.markdown(f"<div class='dynamic-island'>🏝️ 建议买入清单: {', '.join(buying_now)}</div>", unsafe_allow_html=True)

# 股票卡片循环
for item in processed_data:
    with st.container():
        buy_label = "<span class='buy-pill'>BUY</span>" if item['is_odd'] else ""
        st.markdown(f"### {item['ticker']} {buy_label}", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1.2])
        
        with col1:
            st.markdown(f"""
                <div class='apple-card'>
                    <div style='color:#8E8E93; font-size:11px;'>180D 累计收益</div>
                    <div class='profit-hero'>{item['profit']*100:.1f}%</div>
                    <div style='margin-bottom:8px;'>
                        {"".join([f"<span class='pill'>{t}</span>" for t in item['tags']])}
                    </div>
                    <table class='f-table'>
                        <tr><td>板块</td><td class='f-val'>{item['info'].get('sector','N/A')}</td></tr>
                        <tr><td>营收增速</td><td class='f-val'>{item['info'].get('revenueGrowth',0)*100:.1f}%</td></tr>
                        <tr><td>现金流</td><td class='f-val'>${item['info'].get('freeCashflow',0)/1e6:.1f}M</td></tr>
                        <tr><td>目标价</td><td class='f-val' style='color:#FF3B30;'>${item['info'].get('targetMeanPrice','N/A')}</td></tr>
                    </table>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            # 修改颜色：红涨 (FF3B30) 绿跌 (34C759)
            fig = go.Figure(data=[go.Candlestick(
                x=item['df'].index, open=item['df']['Open'], high=item['df']['High'],
                low=item['df']['Low'], close=item['df']['Close'],
                increasing_line_color='#FF3B30', decreasing_line_color='#34C759',
                increasing_fillcolor='#FF3B30', decreasing_fillcolor='#34C759'
            )])
            
            # 标注买卖点
            for t in item['trades']:
                is_buy = t['type'] == 'buy'
                color = "#FF3B30" if is_buy else "#34C759"
                symbol = "triangle-up" if is_buy else "triangle-down"
                label = "B" if is_buy else "S"
                
                fig.add_trace(go.Scatter(
                    x=[t['date']], y=[t['price']],
                    mode='markers+text',
                    marker=dict(symbol=symbol, size=12, color=color, line=dict(width=1, color='white')),
                    text=[label], textposition="top center",
                    name="信号"
                ))

            fig.update_layout(
                template="plotly_dark", xaxis_rangeslider_visible=False,
                height=300, margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                yaxis=dict(showgrid=False, font=dict(size=10), side="right"),
                xaxis=dict(showgrid=False, font=dict(size=10)),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"v6_{item['ticker']}")
        
        st.divider()
