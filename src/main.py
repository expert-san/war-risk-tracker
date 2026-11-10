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
    save_risk_score, save_alert, get_recent_risk_history,
    get_connection, DB_PATH
)
from src.collectors.market import fetch_market_data
from src.collectors.news import fetch_news_events
from src.collectors.geopolitical import fetch_geopolitical_indicators, fetch_regional_conflict_status
from src.analyzer import evaluate_wwri
from src.notifier import format_daily_briefing, send_telegram_alert


def run_pipeline(target_date: str = None) -> None:
    """
    일일 수집 -> 평가 -> 저장 -> 알림 파이프라인 총괄 실행
    """
    load_dotenv()
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    print(f"==================================================")
    print(f"🚀 [WWRI Pipeline] Starting Daily Run: {target_date}")
    print(f"==================================================")

    # 1. DB 초기화
    init_db(DB_PATH)

    # 2. 데이터 수집 (Market, News, Geopolitical)
    print("1/4 Collecting market data...")
    market_records = fetch_market_data(target_date)
    if market_records:
        save_market_data(market_records, DB_PATH)
        print(f"    - Saved {len(market_records)} market records.")

    print("2/4 Collecting international news...")
    news_records = fetch_news_events(target_date)
    if news_records:
        save_news_events(news_records, DB_PATH)
        print(f"    - Saved {len(news_records)} news records.")

    print("3/4 Assessing regional conflict status...")
    conflict_records = fetch_regional_conflict_status(target_date, news_records)
    # conflict records DB 저장
    conn = get_connection(DB_PATH)
    cursor = conn.cursor()
    for c in conflict_records:
        cursor.execute("""
        INSERT INTO conflict_data (date, region, incident_count, casualties, conflict_level, source, notes)
        VALUES (:date, :region, :incident_count, :casualties, :conflict_level, :source, :notes)
        """, c)
    conn.commit()
    conn.close()

    # 3. 과거 이력 조회 및 WWRI 계산
    history = get_recent_risk_history(35, DB_PATH)
    prev_7d = history[-7]["wwri_score"] if len(history) >= 7 else None
    prev_30d = history[0]["wwri_score"] if len(history) >= 30 else None

    print("4/4 Computing WWRI composite score & alerts...")
    score_data, alerts = evaluate_wwri(
        target_date=target_date,
        market_records=market_records,
        news_records=news_records,
        conflict_records=conflict_records,
        prev_7d_score=prev_7d,
        prev_30d_score=prev_30d
    )

    # DB에 점수 및 경고 저장
    save_risk_score(score_data, DB_PATH)
    for a in alerts:
        save_alert(a, DB_PATH)

    print(f"    - WWRI Score: {score_data['wwri_score']} ({score_data['risk_level']})")
    print(f"    - Generated {len(alerts)} alerts.")

    # 4. 텔레그램 알림 발송
    dashboard_url = os.environ.get("DASHBOARD_URL", "")
    briefing = format_daily_briefing(score_data, alerts, dashboard_url)
    send_telegram_alert(briefing)

    print("==================================================")
    print("✅ [WWRI Pipeline] Completed successfully.")
    print("==================================================")


if __name__ == "__main__":
    run_pipeline()
