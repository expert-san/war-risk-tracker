import datetime
from typing import Dict, List, Any, Tuple


def calculate_market_scores(market_records: List[Dict[str, Any]]) -> Tuple[float, float, List[Dict[str, Any]]]:
    """
    금융/원자재/방산주 데이터를 기반으로
    1) 금융·에너지 시장 점수 (15% 가중치)
    2) 방위산업 및 군수생산 점수 (10% 가중치)
    를 0~100점 척도로 계산하고, 감지된 이상 징후를 반환합니다.
    """
    market_score = 30.0  # 기본 기준점
    defense_score = 30.0 # 기본 기준점
    triggers = []

    # 지표별 파싱
    oil_change_7d = 0.0
    gold_change_7d = 0.0
    vix_price = 15.0
    defense_changes = []
    sp500_change = 0.0

    for m in market_records:
        symbol = m.get("symbol")
        cat = m.get("category")
        c7 = m.get("change_7d", 0.0)
        c30 = m.get("change_30d", 0.0)
        price = m.get("price", 0.0)

        if cat == "oil":
            oil_change_7d = c7
            if c7 >= 7.0:
                market_score += 15.0
                triggers.append(f"국제유가 7일간 급등 ({c7:+.1f}%)")
            elif c7 >= 3.0:
                market_score += 8.0
        elif cat == "gold":
            gold_change_7d = c7
            if c7 >= 4.0:
                market_score += 10.0
                triggers.append(f"안전자산(금) 7일간 매수세 증가 ({c7:+.1f}%)")
        elif cat == "volatility":
            vix_price = price
            if price >= 25.0:
                market_score += 20.0
                triggers.append(f"공포지수(VIX) 급등 ({price:.1f})")
            elif price >= 20.0:
                market_score += 10.0
        elif cat == "defense":
            defense_changes.append(c7)
        elif cat == "benchmark":
            sp500_change = c7

    # 방산주 상대 강도 평가
    if defense_changes:
        avg_defense_change = sum(defense_changes) / len(defense_changes)
        relative_strength = avg_defense_change - sp500_change
        if relative_strength >= 5.0:
            defense_score += 25.0
            triggers.append(f"방산주가 시장 대비 7일간 큰 폭 초과 상승 (+{relative_strength:.1f}%p)")
        elif relative_strength >= 2.0:
            defense_score += 15.0
            triggers.append(f"방산주 섹터 상대 강세 지속 (+{relative_strength:.1f}%p)")
        elif relative_strength <= -3.0:
            defense_score -= 10.0

    return min(100.0, max(0.0, market_score)), min(100.0, max(0.0, defense_score)), triggers


def evaluate_wwri(
    target_date: str,
    market_records: List[Dict[str, Any]],
    news_records: List[Dict[str, Any]],
    conflict_records: List[Dict[str, Any]],
    prev_7d_score: float = None,
    prev_30d_score: float = None
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    기획서의 5대 핵심 축을 가중 합산하여 세계 전쟁 위험 종합지수(WWRI)를 계산합니다.
    1. 실제 무력충돌 및 확전 (30%)
    2. 군사적 동원 및 배치 (25%)
    3. 지정학적 위험지수 (20%)
    4. 금융·에너지 시장 (15%)
    5. 방위산업 및 군수생산 (10%)
    """
    # 1) 금융 및 방산 점수 계산
    market_score, defense_score, market_triggers = calculate_market_scores(market_records)

    # 2) 무력충돌 및 군사 점수 추산 (수집된 지역/뉴스 기반)
    conflict_score = 35.0
    military_score = 30.0
    geopolitical_score = 40.0
    triggers = list(market_triggers)

    # 분쟁 지역 상태 점검
    severe_regions = []
    if conflict_records:
        for c in conflict_records:
            if c.get("conflict_level") == "심각":
                conflict_score += 15.0
                severe_regions.append(c.get("region"))
            elif c.get("conflict_level") == "높음":
                conflict_score += 8.0

    if severe_regions:
        triggers.append(f"무력충돌 심각 지역 감지: {', '.join(severe_regions)}")

    # 뉴스 내 긴급 키워드 감지 (강대국 직접 충돌 등)
    emergency_detected = False
    for n in news_records:
        t = (n.get("title", "") + " " + n.get("summary", "")).lower()
        if "world war" in t or "direct confrontation" in t or "nuclear strike" in t:
            emergency_detected = True
            triggers.append("⚠️ 강대국 간 직접 교전 또는 핵 위험 관련 긴급 보도 감지")
            military_score += 30.0
            conflict_score += 25.0
            break

    # 5대 지표 가중 합산
    wwri = (
        (conflict_score * 0.30) +
        (military_score * 0.25) +
        (geopolitical_score * 0.20) +
        (market_score * 0.15) +
        (defense_score * 0.10)
    )
    wwri = round(min(100.0, max(0.0, wwri)), 1)

    # 위험 수준 구분
    if wwri >= 80.0:
        level = "심각"
    elif wwri >= 60.0:
        level = "경계"
    elif wwri >= 40.0:
        level = "주의"
    elif wwri >= 20.0:
        level = "관심"
    else:
        level = "안정"

    # 변화량 계산
    score_change_7d = round(wwri - prev_7d_score, 1) if prev_7d_score is not None else 0.0
    score_change_30d = round(wwri - prev_30d_score, 1) if prev_30d_score is not None else 0.0

    # 경고(Alert) 수준 판단
    alerts = []
    if emergency_detected:
        alert_level = "긴급"
    elif wwri >= 60.0 or (score_change_7d >= 15.0):
        alert_level = "경계"
    elif len(triggers) >= 2 or wwri >= 40.0 or (score_change_7d >= 7.0):
        alert_level = "주의"
    elif len(triggers) >= 1 or wwri >= 25.0:
        alert_level = "관심"
    else:
        alert_level = "일반"

    if alert_level != "일반":
        alerts.append({
            "date": target_date,
            "alert_level": alert_level,
            "title": f"WWRI [{alert_level}] 단계 진입 ({wwri}점)",
            "description": f"7일 전 대비 변화: {score_change_7d:+.1f}점 / 감지된 요인: {len(triggers)}건",
            "triggers": "\n".join(triggers) if triggers else "지표 정례 점검"
        })

    score_result = {
        "date": target_date,
        "wwri_score": wwri,
        "conflict_score": round(conflict_score, 1),
        "military_score": round(military_score, 1),
        "geopolitical_score": round(geopolitical_score, 1),
        "market_score": round(market_score, 1),
        "defense_score": round(defense_score, 1),
        "score_change_7d": score_change_7d,
        "score_change_30d": score_change_30d,
        "risk_level": level,
        "summary": f"종합 지수 {wwri}점 ({level} 단계). 주요 감지: {triggers[0] if triggers else '특이 사항 없음'}"
    }

    return score_result, alerts
