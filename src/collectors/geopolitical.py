import datetime
from typing import List, Dict, Any

# 확장된 주요 관심 관찰 지역 (6대 글로벌 핫스팟)
MONITORING_REGIONS = ["동유럽", "중동", "대만해협", "한반도", "홍해·아덴만", "남중국해"]


def fetch_geopolitical_indicators(
    target_date: str = None,
    news_events: List[Dict[str, Any]] = None,
    market_records: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    수집된 뉴스 강도와 시장 변동성(VIX, 유가)을 기반으로
    지정학적 위험 지표(GPR Index 및 Conflict Intensity Index)를 동적으로 추산·갱신합니다.
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # 1. 뉴스 기반 위험도 밀도 계산 (뉴스 기사당 위험 키워드 빈도)
    risk_keyword_count = 0
    total_news = len(news_events) if news_events else 1
    if news_events:
        for n in news_events:
            kws = n.get("keywords", "")
            if kws and kws != "general":
                risk_keyword_count += len(kws.split(","))

    # 2. 시장 변동성(VIX) 및 유가 변동성 반영
    vix_val = 15.0
    oil_chg = 0.0
    if market_records:
        for m in market_records:
            if m.get("category") == "volatility":
                vix_val = m.get("price", 15.0)
            elif m.get("category") == "oil":
                oil_chg = m.get("change_7d", 0.0)

    # GPR 동적 지표 산출 (100 기준선: 역사적 평균치)
    # 뉴스 위험도 밀도와 VIX/유가 스트레스를 가중 결합
    news_stress = min(50.0, (risk_keyword_count / total_news) * 15.0)
    market_stress = max(0.0, (vix_val - 15.0) * 1.5) + max(0.0, oil_chg * 0.8)
    dynamic_gpr = round(100.0 + news_stress + market_stress, 1)

    # Conflict Intensity Index (0~100 척도)
    intensity_idx = round(min(100.0, max(20.0, 45.0 + (risk_keyword_count * 0.8) + (market_stress * 0.5))), 1)

    records = [
        {
            "date": target_date,
            "indicator_name": "GPR_Daily",
            "value": dynamic_gpr,
            "source": "Dynamic Geopolitical Risk Index (NLP & Market Synthesized)",
            "notes": f"뉴스 키워드 밀도 및 시장 변동성 결합 추산 (기준선: 100)"
        },
        {
            "date": target_date,
            "indicator_name": "Conflict_Intensity_Index",
            "value": intensity_idx,
            "source": "Multi-regional Conflict Intensity Tracker",
            "notes": f"6대 글로벌 핫스팟 활동성 종합 강도 지수"
        }
    ]
    return records


def fetch_regional_conflict_status(target_date: str = None, news_events: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    확장된 6대 관찰 대상 지역별 무력 충돌 및 긴장 상태를 평가합니다.
    수집된 뉴스 키워드를 바탕으로 지역별 이벤트 빈도를 동적으로 집계합니다.
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # 지역별 정밀 검색 키워드 매핑
    region_keywords = {
        "동유럽": ["ukraine", "russia", "우크라이나", "러시아", "동유럽", "nato", "벨라루스", "쿠르스크", "돈바스"],
        "중동": ["israel", "iran", "gaza", "lebanon", "middle east", "syria", "이란", "이스라엘", "가자", "중동", "레바논", "헤즈볼라"],
        "대만해협": ["taiwan", "china", "taipei", "beijing", "대만", "중국", "대만해협", "라이칭더"],
        "한반도": ["north korea", "south korea", "pyongyang", "kim jong", "북한", "미사일", "평양", "한반도", "nll", "군사분계선"],
        "홍해·아덴만": ["red sea", "houthi", "yemen", "bab el-mandeb", "홍해", "후티", "예멘", "아덴만", "상선 공격"],
        "남중국해": ["south china sea", "philippines", "spratly", "second thomas shoal", "남중국해", "필리핀", "스프래틀리"]
    }

    # 실제 무력 교전·타격·사상자를 나타내는 고강도 키워드
    high_intensity_keywords = [
        "strike", "attack", "killed", "casualty", "casualties", "missile", "invasion",
        "bomb", "shelling", "clash", "clashes", "intercepted", "drone", "blockade",
        "공습", "타격", "사상자", "사망", "교전", "포격", "미사일 발사", "격추", "피격", "침공", "봉쇄"
    ]

    results = []

    for region in MONITORING_REGIONS:
        keywords = region_keywords.get(region, [])
        incident_count = 0
        intensity_score = 0.0
        high_intensity_hits = 0

        if news_events:
            for n in news_events:
                text = (n.get("title", "") + " " + n.get("summary", "")).lower()
                if any(kw in text for kw in keywords):
                    incident_count += 1
                    if any(hk in text for hk in high_intensity_keywords):
                        intensity_score += 1.5
                        high_intensity_hits += 1
                    else:
                        intensity_score += 0.5

        # 확장된 수집량(50건) 및 교전 강도를 반영한 충돌 수준 판정
        if intensity_score >= 8.0 and high_intensity_hits >= 3:
            level = "심각"
        elif intensity_score >= 4.5 and high_intensity_hits >= 1:
            level = "높음"
        elif intensity_score >= 1.5:
            level = "보통"
        else:
            level = "낮음"

        results.append({
            "date": target_date,
            "region": region,
            "incident_count": incident_count,
            "casualties": 0,
            "conflict_level": level,
            "source": "Global Media Monitoring & Intensity Aggregate",
            "notes": f"최근 48시간 보도 {incident_count}건 (교전·타격 신호 {high_intensity_hits}건)"
        })

    return results
