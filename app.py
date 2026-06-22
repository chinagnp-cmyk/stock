import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
from ta.trend import MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
from data_source import get_stock_data
from data_source import backtest_macd_strategy

# 网页标题和侧边栏（用户输入区）
st.set_page_config(page_title="股票趋势分析", layout="wide")
st.title("📊 股票趋势分析工具")

st.sidebar.header("参数设置")
ticker = st.sidebar.text_input("股票代码", "600519")
start_date = st.sidebar.date_input("开始日期", pd.to_datetime("2026-01-01"))
end_date = st.sidebar.date_input("结束日期", pd.to_datetime("2026-05-31"))
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
    bb = BollingerBands(close=df["Close"], window=20, window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_middle"] = bb.bollinger_mavg()
    df["BB_lower"] = bb.bollinger_lband()

    # 顶部关键指标卡片
    latest = df.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("最新收盘价", f"{latest['Close']:.2f}")
    col2.metric("RSI", f"{latest['RSI']:.1f}",
                "超买" if latest["RSI"]>70 else ("超卖" if latest["RSI"]<30 else "中性"))
    col3.metric("MACD柱", f"{latest['MACD_diff']:.2f}",
                "多头" if latest["MACD_diff"]>0 else "空头")
    bb_position = "贴近上轨(偏热)" if latest["Close"] > latest["BB_upper"]*0.98 else ("贴近下轨(偏冷)" if latest["Close"] < latest["BB_lower"]*1.02 else "通道中段")
    col4.metric("布林带位置", bb_position)

    st.divider()
    st.subheader("🔍 多指标信号汇总")

    signals = []

    if latest["MACD_diff"] > 0:
        signals.append(("MACD", "偏多", "MACD柱为正，短期动能向上"))
    else:
        signals.append(("MACD", "偏空", "MACD柱为负，短期动能向下"))

    if latest["RSI"] > 70:
        signals.append(("RSI", "偏空", "RSI超过70，短期涨幅可能过大"))
    elif latest["RSI"] < 30:
        signals.append(("RSI", "偏多", "RSI低于30，短期跌幅可能过大"))
    else:
        signals.append(("RSI", "中性", "RSI处于30-70中性区间"))

    if latest["Close"] > latest["BB_upper"]:
        signals.append(("布林带", "偏空", "股价突破上轨，处于通道外高位"))
    elif latest["Close"] < latest["BB_lower"]:
        signals.append(("布林带", "偏多", "股价突破下轨，处于通道外低位"))
    else:
        signals.append(("布林带", "中性", "股价位于布林带通道内"))

    bull_count = sum(1 for s in signals if s[1] == "偏多")
    bear_count = sum(1 for s in signals if s[1] == "偏空")
    neutral_count = sum(1 for s in signals if s[1] == "中性")

    cols = st.columns(3)
    for i, (name, status, reason) in enumerate(signals):
        color = "🟢" if status == "偏多" else ("🔴" if status == "偏空" else "⚪")
        cols[i].metric(f"{color} {name}", status)
        cols[i].caption(reason)

    st.info(f"当前 {len(signals)} 个指标中：{bull_count} 个偏多，{bear_count} 个偏空，{neutral_count} 个中性")

    st.warning(
        "⚠️ 以上仅为历史价格统计规律的客观展示，不构成任何投资建议。"
        "技术指标基于历史数据计算，无法预测未来走势，过往表现也不代表未来结果。"
        "实际投资决策涉及更多因素（基本面、市场环境、个人风险承受能力等），请独立判断并自行承担风险。"
    )

    # 画图并显示在网页上
    macd_panel = [
        mpf.make_addplot(df["BB_upper"], panel=0, color="gray", linestyle="--", width=0.8),
        mpf.make_addplot(df["BB_middle"], panel=0, color="gray", linestyle=":", width=0.8),
        mpf.make_addplot(df["BB_lower"], panel=0, color="gray", linestyle="--", width=0.8),
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

    st.divider()
    st.subheader("📈 策略回测：MACD金叉买入/死叉卖出")

    result = backtest_macd_strategy(df)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("策略收益率", f"{result['策略收益率']}%")
    col_b.metric("买入持有收益率", f"{result['买入持有收益率']}%")
    col_c.metric("交易次数", result["交易次数"])

    if result["策略收益率"] > result["买入持有收益率"]:
        st.success("这段时间内，金叉死叉策略跑赢了简单持有")
    else:
        st.info("这段时间内，简单持有反而比频繁交易表现更好")

    with st.expander("查看详细交易记录"):
        st.dataframe(result["交易记录"])
else:
    st.info("👈 在左侧输入股票代码，点击「开始分析」")
