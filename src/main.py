import os
import sys
import datetime
from dotenv import load_dotenv

# 상위 디렉토리를 sys.path에 추가하여 어디서든 실행 가능하도록 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database import (
    init_db, save_market_data, save_news_events,
    save_geopolitical_data, save_conflict_data, save_military_events,
    save_risk_score, save_alert, get_recent_risk_history,
    DB_PATH
)
from src.collectors.market import fetch_market_data
from src.collectors.news import fetch_news_events, extract_military_events
from src.collectors.geopolitical import fetch_geopolitical_indicators, fetch_regional_conflict_status
from src.analyzer import evaluate_wwri
from src.notifier import format_daily_briefing, send_telegram_alert


def run_pipeline(target_date: str = None) -> None:
    """
    일일 수집(시장·뉴스·군사이벤트·지정학지표·지역분쟁) -> 평가 -> 저장 -> 알림 파이프라인 총괄 실행
    """
    load_dotenv()
    if target_date is None:
        # GitHub Actions 서버는 UTC 기준이므로 한국 시간(KST, UTC+9)으로 날짜를 계산
        kst = datetime.timezone(datetime.timedelta(hours=9))
        target_date = datetime.datetime.now(kst).strftime("%Y-%m-%d")

    print("==================================================")
    print(f"🚀 [WWRI Pipeline] Starting Daily Run: {target_date}")
    print("==================================================")

    # 1. DB 초기화
    init_db(DB_PATH)

    # 2. 금융·방산·원자재·환율·금리 데이터 수집
    print("1/6 Collecting expanded global & KR market data...")
    market_records = fetch_market_data(target_date)
    if market_records:
        save_market_data(market_records, DB_PATH)
        print(f"    - Saved {len(market_records)} market records.")

    # 3. 국제 및 국내 분쟁 뉴스 수집
    print("2/6 Collecting international & Korean news...")
    news_records = fetch_news_events(target_date)
    if news_records:
        save_news_events(news_records, DB_PATH)
        print(f"    - Saved {len(news_records)} news records.")

    # 4. 뉴스 기반 군사적 움직임(military_events) 자동 추출 및 저장
    print("3/6 Extracting military events (movements, drills, deployments)...")
    military_events = extract_military_events(news_records, target_date)
    if military_events:
        save_military_events(military_events, DB_PATH)
        print(f"    - Saved {len(military_events)} military events.")

    # 5. 6대 글로벌 핫스팟 지역별 충돌 상태 평가 및 저장
    print("4/6 Assessing 6 global hotspot regions...")
    conflict_records = fetch_regional_conflict_status(target_date, news_records)
    if conflict_records:
        save_conflict_data(conflict_records, DB_PATH)
        print(f"    - Saved {len(conflict_records)} regional conflict records.")

    # 6. 동적 지정학 위험 지표(GPR 등) 추산 및 저장
    print("5/6 Computing dynamic geopolitical indicators (GPR)...")
    geopolitical_records = fetch_geopolitical_indicators(target_date, news_records, market_records)
    if geopolitical_records:
        save_geopolitical_data(geopolitical_records, DB_PATH)
        print(f"    - Saved {len(geopolitical_records)} geopolitical indicators.")

    # 7. 과거 이력 조회 및 WWRI 종합 위험지수 계산
    history = get_recent_risk_history(35, DB_PATH)
    prev_7d = history[-7]["wwri_score"] if len(history) >= 7 else None
    prev_30d = history[0]["wwri_score"] if len(history) >= 30 else None

    print("6/6 Computing WWRI composite score & alerts...")
    score_data, alerts = evaluate_wwri(
        target_date=target_date,
        market_records=market_records,
        news_records=news_records,
        conflict_records=conflict_records,
        military_events=military_events,
        geopolitical_records=geopolitical_records,
        prev_7d_score=prev_7d,
        prev_30d_score=prev_30d
    )

    # DB에 점수 및 경고 저장
    save_risk_score(score_data, DB_PATH)
    for a in alerts:
        save_alert(a, DB_PATH)

    print(f"    - WWRI Score: {score_data['wwri_score']} ({score_data['risk_level']})")
    print(f"    - Generated {len(alerts)} alerts.")

    # 8. 텔레그램 알림 발송
    dashboard_url = os.environ.get("DASHBOARD_URL", "")
    briefing = format_daily_briefing(score_data, alerts, dashboard_url)
    send_telegram_alert(briefing)

    print("==================================================")
    print("✅ [WWRI Pipeline] Completed successfully.")
    print("==================================================")


if __name__ == "__main__":
    run_pipeline()
