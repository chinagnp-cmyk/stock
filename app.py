import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
from ta.trend import MACD
from ta.momentum import RSIIndicator
from data_source import get_stock_data

# 网页标题和侧边栏（用户输入区）
st.set_page_config(page_title="股票趋势分析", layout="wide")
st.title("📊 股票趋势分析工具")

st.sidebar.header("参数设置")
ticker = st.sidebar.text_input("股票代码", "600519")
start_date = st.sidebar.date_input("开始日期", pd.to_datetime("2024-01-01"))
end_date = st.sidebar.date_input("结束日期", pd.to_datetime("2024-12-31"))
run_btn = st.sidebar.button("开始分析")

if run_btn:
    df, source_type, status_msg = get_stock_data(ticker, start_date, end_date)

    if source_type == "real":
        st.success(f"✅ {status_msg}")
    else:
        st.warning(f"⚠️ 无法获取真实数据（{status_msg}），当前显示模拟数据")

    # 计算指标
    macd_calc = MACD(close=df["Close"])
    df["MACD"] = macd_calc.macd()
    df["MACD_signal"] = macd_calc.macd_signal()
    df["MACD_diff"] = macd_calc.macd_diff()
    df["RSI"] = RSIIndicator(close=df["Close"], window=14).rsi()

    # 顶部关键指标卡片
    latest = df.iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("最新收盘价", f"{latest['Close']:.2f}")
    col2.metric("RSI", f"{latest['RSI']:.1f}",
                "超买" if latest["RSI"]>70 else ("超卖" if latest["RSI"]<30 else "中性"))
    col3.metric("MACD柱", f"{latest['MACD_diff']:.2f}",
                "多头" if latest["MACD_diff"]>0 else "空头")

    # 画图并显示在网页上
    macd_panel = [
        mpf.make_addplot(df["MACD"], panel=2, color="blue", ylabel="MACD"),
        mpf.make_addplot(df["MACD_signal"], panel=2, color="orange"),
        mpf.make_addplot(df["MACD_diff"], panel=2, type="bar", color="gray", alpha=0.5),
        mpf.make_addplot(df["RSI"], panel=3, color="purple", ylabel="RSI"),
    ]
    fig, _ = mpf.plot(
        df, type="candle", mav=(5,20), volume=True,
        addplot=macd_panel, panel_ratios=(3,1,1,1),
        style="yahoo", figsize=(12,10), returnfig=True
    )
    st.pyplot(fig)
else:
    st.info("👈 在左侧输入股票代码，点击「开始分析」")