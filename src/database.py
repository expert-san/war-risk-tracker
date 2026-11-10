import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "wwri.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """SQLite 데이터베이스 연결 반환 (디렉토리 자동 생성)"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """문서 기획서에 정의된 7개 데이터 테이블 스키마 초기화"""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. market_data: 방산주, 유가, 금, 달러, VIX
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        symbol TEXT NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL, -- defense, oil, gold, fx, volatility
        price REAL,
        change_1d REAL,
        change_7d REAL,
        change_30d REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date, symbol)
    )
    """)

    # 2. geopolitical_data: GPR, AI-GPR 등 위험지수
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS geopolitical_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        indicator_name TEXT NOT NULL,
        value REAL,
        source TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date, indicator_name)
    )
    """)

    # 3. conflict_data: 지역별 무력충돌, 사망자, 공격 횟수
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conflict_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        region TEXT NOT NULL, -- 동유럽, 중동, 대만해협, 한반도 등
        incident_count INTEGER DEFAULT 0,
        casualties INTEGER DEFAULT 0,
        conflict_level TEXT, -- 낮음, 보통, 높음, 심각
        source TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4. military_events: 병력 이동, 군사훈련, 동원, 무기 배치
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS military_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        region TEXT NOT NULL,
        event_type TEXT NOT NULL, -- troop_movement, exercise, mobilization, deployment
        description TEXT NOT NULL,
        severity TEXT, -- 보통, 중요, 심각
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 5. news_events: 주요 국제뉴스, 출처, 발생 일자
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        title TEXT NOT NULL,
        link TEXT,
        source TEXT,
        summary TEXT,
        keywords TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date, title)
    )
    """)

    # 6. risk_scores: 종합 위험점수 (WWRI) 및 항목별 평가
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS risk_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL UNIQUE,
        wwri_score REAL NOT NULL,
        conflict_score REAL,    -- 가중치 30%
        military_score REAL,    -- 가중치 25%
        geopolitical_score REAL,-- 가중치 20%
        market_score REAL,      -- 가중치 15%
        defense_score REAL,     -- 가중치 10%
        score_change_7d REAL,
        score_change_30d REAL,
        risk_level TEXT NOT NULL, -- 안정(0-19), 관심(20-39), 주의(40-59), 경계(60-79), 심각(80-100)
        summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 7. alerts: 경고 발생 일자, 원인, 위험 수준
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        alert_level TEXT NOT NULL, -- 일반, 관심, 주의, 경계, 긴급
        title TEXT NOT NULL,
        description TEXT,
        triggers TEXT, -- 발생 원인 및 지표 정보 (JSON 형태)
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def save_market_data(records: List[Dict[str, Any]], db_path: str = DB_PATH) -> None:
    """시장 데이터 일괄 저장 (UPSERT)"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for r in records:
        cursor.execute("""
        INSERT INTO market_data (date, symbol, name, category, price, change_1d, change_7d, change_30d)
        VALUES (:date, :symbol, :name, :category, :price, :change_1d, :change_7d, :change_30d)
        ON CONFLICT(date, symbol) DO UPDATE SET
            price = excluded.price,
            change_1d = excluded.change_1d,
            change_7d = excluded.change_7d,
            change_30d = excluded.change_30d
        """, r)
    conn.commit()
    conn.close()


def save_news_events(records: List[Dict[str, Any]], db_path: str = DB_PATH) -> None:
    """주요 뉴스 이벤트 저장"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    for r in records:
        cursor.execute("""
        INSERT INTO news_events (date, title, link, source, summary, keywords)
        VALUES (:date, :title, :link, :source, :summary, :keywords)
        ON CONFLICT(date, title) DO NOTHING
        """, r)
    conn.commit()
    conn.close()


def save_risk_score(score_data: Dict[str, Any], db_path: str = DB_PATH) -> None:
    """종합 위험도 점수 저장"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO risk_scores (
        date, wwri_score, conflict_score, military_score,
        geopolitical_score, market_score, defense_score,
        score_change_7d, score_change_30d, risk_level, summary
    ) VALUES (
        :date, :wwri_score, :conflict_score, :military_score,
        :geopolitical_score, :market_score, :defense_score,
        :score_change_7d, :score_change_30d, :risk_level, :summary
    ) ON CONFLICT(date) DO UPDATE SET
        wwri_score = excluded.wwri_score,
        conflict_score = excluded.conflict_score,
        military_score = excluded.military_score,
        geopolitical_score = excluded.geopolitical_score,
        market_score = excluded.market_score,
        defense_score = excluded.defense_score,
        score_change_7d = excluded.score_change_7d,
        score_change_30d = excluded.score_change_30d,
        risk_level = excluded.risk_level,
        summary = excluded.summary
    """, score_data)
    conn.commit()
    conn.close()


def save_alert(alert_data: Dict[str, Any], db_path: str = DB_PATH) -> None:
    """경고 발생 내역 저장"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO alerts (date, alert_level, title, description, triggers)
    VALUES (:date, :alert_level, :title, :description, :triggers)
    """, alert_data)
    conn.commit()
    conn.close()


def get_latest_risk_score(db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """가장 최근 위험도 점수 조회"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM risk_scores ORDER BY date DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_recent_risk_history(days: int = 30, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """최근 N일간의 위험도 점수 이력 조회"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM risk_scores ORDER BY date ASC LIMIT ?
    """, (days,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_alerts(limit: int = 5, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """최근 발생한 경고 목록 조회"""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print("Database schema successfully initialized.")
