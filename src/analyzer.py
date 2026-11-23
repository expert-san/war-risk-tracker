from typing import Dict, List, Any, Tuple


def calculate_market_scores(market_records: List[Dict[str, Any]]) -> Tuple[float, float, List[str]]:
    """
    확장된 금융/원자재/환율/글로벌 방산주 데이터를 기반으로
    1) 금융·에너지 시장 점수 (15% 가중치)
    2) 방위산업 및 군수생산 점수 (10% 가중치)
    를 0~100점 척도로 계산하고, 감지된 이상 징후를 반환합니다.
    """
    market_score = 25.0   # 기본 기준점
    defense_score = 25.0  # 기본 기준점
    triggers: List[str] = []

    oil_changes: List[float] = []
    defense_global_changes: List[float] = []
    defense_kr_changes: List[float] = []
    sp500_change = 0.0
    kospi_change = 0.0

    for m in market_records:
        cat = m.get("category", "")
        name = m.get("name", "")
        c7 = m.get("change_7d", 0.0) or 0.0
        price = m.get("price", 0.0) or 0.0

        if cat == "oil":
            oil_changes.append(c7)
        elif cat == "energy":  # 천연가스 등
            if c7 >= 10.0:
                market_score += 12.0
                triggers.append(f"천연가스({name}) 7일간 급등 ({c7:+.1f}%)")
            elif c7 >= 5.0:
                market_score += 6.0
        elif cat == "gold":
            if c7 >= 4.0:
                market_score += 10.0
                triggers.append(f"안전자산(금) 7일간 매수세 증가 ({c7:+.1f}%)")
            elif c7 >= 2.0:
                market_score += 5.0
        elif cat == "volatility":  # VIX
            if price >= 25.0:
                market_score += 22.0
                triggers.append(f"공포지수(VIX) 위험 수준 급등 ({price:.1f})")
            elif price >= 20.0:
                market_score += 12.0
                triggers.append(f"공포지수(VIX) 경계선 돌파 ({price:.1f})")
        elif cat == "fx_kr":  # 원/달러 환율
            if c7 >= 2.5:
                market_score += 10.0
                triggers.append(f"원/달러 환율 7일간 급등 ({price:,.1f}원, {c7:+.1f}%)")
            elif c7 >= 1.2:
                market_score += 5.0
        elif cat == "bonds":  # 미 국채 10년물 금리 (전쟁 위기 시 안전자산 선호로 금리 급락)
            if c7 <= -6.0:
                market_score += 8.0
                triggers.append(f"미 국채 10년물 금리 급락(안전자산 채권 쏠림, {c7:+.1f}%)")
        elif cat in ("defense", "defense_us", "defense_eu"):
            defense_global_changes.append(c7)
        elif cat == "defense_kr":
            defense_kr_changes.append(c7)
        elif cat == "benchmark":
            sp500_change = c7
        elif cat == "benchmark_kr":
            kospi_change = c7

    # 유가(WTI & 브렌트유 평균) 평가
    if oil_changes:
        avg_oil_7d = sum(oil_changes) / len(oil_changes)
        if avg_oil_7d >= 7.0:
            market_score += 18.0
            triggers.append(f"국제유가(WTI/브렌트 평균) 7일간 급등 ({avg_oil_7d:+.1f}%)")
        elif avg_oil_7d >= 3.0:
            market_score += 9.0

    # 미국/유럽 글로벌 방산주 상대 강도 평가 (S&P 500 대비)
    if defense_global_changes:
        avg_global_def = sum(defense_global_changes) / len(defense_global_changes)
        rel_global = avg_global_def - sp500_change
        if rel_global >= 5.0:
            defense_score += 25.0
            triggers.append(f"글로벌 방산주(미/유럽) 시장 대비 큰 폭 초과 상승 ({rel_global:+.1f}%p)")
        elif rel_global >= 2.0:
            defense_score += 15.0
            triggers.append(f"글로벌 방산주 섹터 상대 강세 ({rel_global:+.1f}%p)")
        elif rel_global <= -3.0:
            defense_score -= 8.0

    # 한국 방산주 상대 강도 평가 (KOSPI 대비)
    if defense_kr_changes:
        avg_kr_def = sum(defense_kr_changes) / len(defense_kr_changes)
        rel_kr = avg_kr_def - kospi_change
        if rel_kr >= 6.0:
            defense_score += 20.0
            triggers.append(f"국내 K-방산주 KOSPI 대비 급등 ({rel_kr:+.1f}%p)")
        elif rel_kr >= 2.5:
            defense_score += 10.0
            triggers.append(f"국내 K-방산주 상대 강세 ({rel_kr:+.1f}%p)")
        elif rel_kr <= -4.0:
            defense_score -= 5.0

    return min(100.0, max(0.0, market_score)), min(100.0, max(0.0, defense_score)), triggers


def evaluate_wwri(
    target_date: str,
    market_records: List[Dict[str, Any]],
    news_records: List[Dict[str, Any]],
    conflict_records: List[Dict[str, Any]],
    military_events: List[Dict[str, Any]] = None,
    geopolitical_records: List[Dict[str, Any]] = None,
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
    # 1) 금융·에너지 및 방산 점수 계산
    market_score, defense_score, market_triggers = calculate_market_scores(market_records)
    triggers = list(market_triggers)

    # 2) 실제 무력충돌 및 확전 점수 (30%) - 6대 핫스팟 기반
    conflict_score = 25.0
    severe_regions = []
    high_regions = []
    if conflict_records:
        for c in conflict_records:
            lvl = c.get("conflict_level")
            reg = c.get("region")
            if lvl == "심각":
                conflict_score += 15.0
                severe_regions.append(reg)
            elif lvl == "높음":
                conflict_score += 8.0
                high_regions.append(reg)
            elif lvl == "보통":
                conflict_score += 3.0

    if severe_regions:
        triggers.append(f"무력충돌 심각 지역 감지: {', '.join(severe_regions)}")
    elif len(high_regions) >= 2:
        triggers.append(f"복수 분쟁 지역 긴장 고조: {', '.join(high_regions)}")

    # 3) 군사적 동원 및 배치 점수 (25%) - 추출된 military_events 기반
    military_score = 20.0
    severe_mil_count = 0
    if military_events:
        for ev in military_events:
            sev = ev.get("severity", "보통")
            etype = ev.get("event_type", "")
            if sev == "심각":
                military_score += 10.0
                severe_mil_count += 1
            elif sev == "중요":
                military_score += 5.0
            else:
                military_score += 2.0

            if etype == "mobilization":
                military_score += 8.0

        if severe_mil_count >= 2:
            triggers.append(f"심각 수준의 군사 행동/배치 {severe_mil_count}건 감지")

    # 4) 지정학적 위험지수 점수 (20%) - 동적 GPR 지표 기반
    geopolitical_score = 35.0
    if geopolitical_records:
        for g in geopolitical_records:
            if g.get("indicator_name") == "GPR_Daily":
                gpr_val = g.get("value", 100.0)
                # GPR 100(평균) -> 30점, GPR 150 -> 80점 수준으로 매핑
                geopolitical_score = 30.0 + max(-15.0, (gpr_val - 100.0) * 1.0)
                if gpr_val >= 140.0:
                    triggers.append(f"지정학 위험지수(GPR) 급등 ({gpr_val:.1f})")

    # 5) 뉴스 내 긴급 키워드 감지 (강대국 직접 교전 / 핵 위협)
    emergency_detected = False
    for n in news_records:
        t = (n.get("title", "") + " " + n.get("summary", "")).lower()
        if any(kw in t for kw in ["world war", "direct confrontation", "nuclear strike", "핵 타격", "강대국 직접 교전"]):
            emergency_detected = True
            triggers.append("⚠️ 강대국 간 직접 교전 또는 핵 위험 관련 긴급 보도 감지")
            military_score += 30.0
            conflict_score += 25.0
            break

    # 각 세부 영역 0~100점 범위 제한
    conflict_score = min(100.0, max(0.0, conflict_score))
    military_score = min(100.0, max(0.0, military_score))
    geopolitical_score = min(100.0, max(0.0, geopolitical_score))

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
