import datetime
from typing import List, Dict, Any
import yfinance as yf

# 확장된 추적 대상 금융 자산 정의
TARGET_ASSETS = [
    # 1. 미국 주요 방산주 (US Defense)
    {"symbol": "LMT", "name": "Lockheed Martin", "category": "defense_us"},
    {"symbol": "RTX", "name": "RTX Corporation", "category": "defense_us"},
    {"symbol": "NOC", "name": "Northrop Grumman", "category": "defense_us"},
    {"symbol": "GD", "name": "General Dynamics", "category": "defense_us"},
    {"symbol": "ITA", "name": "iShares US Aerospace & Defense ETF", "category": "defense_us"},

    # 2. 한국 대표 방산주 (KR Defense) - 한반도 안보 및 글로벌 K-방산 수주 지표
    {"symbol": "012450.KS", "name": "한화에어로스페이스", "category": "defense_kr"},
    {"symbol": "064350.KS", "name": "현대로템", "category": "defense_kr"},
    {"symbol": "079550.KS", "name": "LIG넥스원", "category": "defense_kr"},

    # 3. 유럽 대표 방산주 (EU Defense) - NATO 방위비 및 동유럽 전선 지표
    {"symbol": "BA.L", "name": "BAE Systems (영국)", "category": "defense_eu"},
    {"symbol": "RHM.DE", "name": "Rheinmetall (독일)", "category": "defense_eu"},

    # 4. 에너지 / 전략 원자재 (Energy & Commodities)
    {"symbol": "CL=F", "name": "WTI Crude Oil Futures", "category": "oil"},
    {"symbol": "BZ=F", "name": "Brent Crude Oil Futures", "category": "oil"},
    {"symbol": "NG=F", "name": "Natural Gas Futures (천연가스)", "category": "energy"},
    {"symbol": "GC=F", "name": "Gold Futures (금)", "category": "gold"},
    {"symbol": "SI=F", "name": "Silver Futures (은)", "category": "commodities"},
    {"symbol": "HG=F", "name": "Copper Futures (구리)", "category": "commodities"},

    # 5. 환율, 금리 및 변동성 지표 (Macro & Volatility)
    {"symbol": "DX-Y.NYB", "name": "US Dollar Index (달러인덱스)", "category": "fx"},
    {"symbol": "KRW=X", "name": "USD/KRW (원/달러 환율)", "category": "fx_kr"},
    {"symbol": "^VIX", "name": "CBOE Volatility Index (공포지수)", "category": "volatility"},
    {"symbol": "^TNX", "name": "US 10Y Treasury Yield (미 국채 10년물 금리)", "category": "bonds"},

    # 6. 시장 벤치마크 (Benchmarks)
    {"symbol": "^GSPC", "name": "S&P 500 Index", "category": "benchmark"},
    {"symbol": "^KS11", "name": "KOSPI Index", "category": "benchmark_kr"}
]


def fetch_market_data(target_date: str = None) -> List[Dict[str, Any]]:
    """
    글로벌 및 국내 방산주, 에너지, 전략 원자재, 환율, 금리 및 VIX 데이터를
    yfinance로 조회하여 1일, 7일, 30일 변동률과 함께 반환합니다.
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
    print(json.dumps(data[:5], indent=2, ensure_ascii=False))
