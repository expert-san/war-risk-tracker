import datetime
from typing import List, Dict, Any
import yfinance as yf

# 추적 대상 금융 자산 정의
TARGET_ASSETS = [
    # 1. 방산주 (Defense)
    {"symbol": "LMT", "name": "Lockheed Martin", "category": "defense"},
    {"symbol": "RTX", "name": "RTX Corporation", "category": "defense"},
    {"symbol": "NOC", "name": "Northrop Grumman", "category": "defense"},
    {"symbol": "GD", "name": "General Dynamics", "category": "defense"},
    {"symbol": "ITA", "name": "iShares US Aerospace & Defense ETF", "category": "defense"},
    
    # 2. 에너지 / 원자재 (Oil & Gold)
    {"symbol": "CL=F", "name": "WTI Crude Oil Futures", "category": "oil"},
    {"symbol": "GC=F", "name": "Gold Futures", "category": "gold"},
    
    # 3. 환율 및 시장 불안 (FX & Volatility)
    {"symbol": "DX-Y.NYB", "name": "US Dollar Index", "category": "fx"},
    {"symbol": "^VIX", "name": "CBOE Volatility Index", "category": "volatility"},
    {"symbol": "^GSPC", "name": "S&P 500 Index (Benchmark)", "category": "benchmark"}
]


def fetch_market_data(target_date: str = None) -> List[Dict[str, Any]]:
    """
    주요 방산주, 원자재, 환율 및 VIX 데이터를 yfinance로 조회하여
    1일, 7일, 30일 변동률과 함께 반환합니다.
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    records = []

    for asset in TARGET_ASSETS:
        symbol = asset["symbol"]
        try:
            ticker = yf.Ticker(symbol)
            # 60일치 과거 데이터를 가져와 1일/7일/30일 변동률 계산
            hist = ticker.history(period="60d")
            
            if hist.empty or len(hist) < 2:
                continue

            current_close = float(hist["Close"].iloc[-1])
            prev_1d_close = float(hist["Close"].iloc[-2])
            prev_7d_close = float(hist["Close"].iloc[-6]) if len(hist) >= 6 else prev_1d_close
            prev_30d_close = float(hist["Close"].iloc[-22]) if len(hist) >= 22 else float(hist["Close"].iloc[0])

            change_1d = ((current_close - prev_1d_close) / prev_1d_close) * 100
            change_7d = ((current_close - prev_7d_close) / prev_7d_close) * 100
            change_30d = ((current_close - prev_30d_close) / prev_30d_close) * 100

            records.append({
                "date": target_date,
                "symbol": symbol,
                "name": asset["name"],
                "category": asset["category"],
                "price": round(current_close, 2),
                "change_1d": round(change_1d, 2),
                "change_7d": round(change_7d, 2),
                "change_30d": round(change_30d, 2)
            })
        except Exception as e:
            print(f"[{symbol}] Failed to fetch market data: {e}")
            continue

    return records


if __name__ == "__main__":
    import json
    data = fetch_market_data()
    print(f"Fetched {len(data)} market records:")
    print(json.dumps(data[:3], indent=2, ensure_ascii=False))
