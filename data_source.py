import requests
import pandas as pd
import numpy as np

def fetch_real_data(stock_code, start_date, end_date, max_retries=3):
    """
    用新浪财经接口获取真实历史K线数据
    """
    market_prefix = "sh" if stock_code.startswith("6") else "sz"
    symbol = f"{market_prefix}{stock_code}"

    url = "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20_/CN_MarketDataService.getKLineData"
    params = {
        "symbol": symbol,
        "scale": "240",     # 240分钟 = 日线
        "ma": "no",
        "datalen": "1000",  # 拉取最多1000条历史记录
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://finance.sina.com.cn"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        text = r.text

        # 接口返回的是 jsonp 格式，需要去掉外层包裹的函数名，提取里面的JSON数组
        json_str = text[text.index("(") + 1: text.rindex(")")]
        import json
        raw_data = json.loads(json_str)

        if not raw_data:
            return None, f"接口返回空数据（股票代码可能不存在：{stock_code}）"

        df = pd.DataFrame(raw_data)
        df = df.rename(columns={
            "day": "Date", "open": "Open", "high": "High",
            "low": "Low", "close": "Close", "volume": "Volume"
        })
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)

        # 按用户选择的日期范围筛选
        df = df[(df.index >= pd.to_datetime(start_date)) & (df.index <= pd.to_datetime(end_date))]

        if len(df) == 0:
            return None, "该日期范围内没有数据"

        return df, f"成功获取真实数据（共{len(df)}条记录）"

    except Exception as e:
        return None, f"获取失败：{str(e)[:150]}"


def generate_mock_data(start_date, end_date):
    """备用：生成模拟数据"""
    days = (end_date - start_date).days
    dates = pd.date_range(start=start_date, periods=max(days, 30), freq="B")
    np.random.seed(42)
    price = 1500
    prices = [price]
    for _ in range(len(dates) - 1):
        price = max(price + np.random.normal(0, 15), 10)
        prices.append(price)
    df = pd.DataFrame({"Close": prices}, index=dates)
    df["Open"] = df["Close"].shift(1).fillna(df["Close"].iloc[0])
    df["High"] = df[["Open", "Close"]].max(axis=1) + np.random.uniform(0, 5, len(dates))
    df["Low"] = df[["Open", "Close"]].min(axis=1) - np.random.uniform(0, 5, len(dates))
    df["Volume"] = np.random.randint(1000000, 5000000, len(dates))
    return df


def get_stock_data(stock_code, start_date, end_date):
    """统一入口：优先真实数据，失败则降级为模拟数据"""
    df, msg = fetch_real_data(stock_code, start_date, end_date)
    if df is not None:
        return df, "real", msg
    else:
        mock_df = generate_mock_data(start_date, end_date)
        return mock_df, "mock", msg