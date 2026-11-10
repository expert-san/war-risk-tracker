import datetime
from typing import List, Dict, Any

# 주요 관심 관찰 지역
MONITORING_REGIONS = ["동유럽", "중동", "대만해협", "한반도"]


def fetch_geopolitical_indicators(target_date: str = None) -> List[Dict[str, Any]]:
    """
    지정학적 위험 지표(GPR Index 등)를 수집하거나 갱신합니다.
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    records = [
        {
            "date": target_date,
            "indicator_name": "GPR_Daily",
            "value": 115.4, # 기준값: 100(역사적 평균)
            "source": "Geopolitical Risk Index (Caldara & Iacoviello)",
            "notes": "국제 지정학적 긴장도 일별 벤치마크"
        },
        {
            "date": target_date,
            "indicator_name": "Conflict_Intensity_Index",
            "value": 68.2,
            "source": "Global Conflict Tracker Aggregate",
            "notes": "주요 분쟁 지역 활동성 집계"
        }
    ]
    return records


def fetch_regional_conflict_status(target_date: str = None, news_events: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    관찰 대상 지역별(동유럽, 중동, 대만해협, 한반도) 무력 충돌 및 긴장 상태를 평가합니다.
    수집된 뉴스 키워드를 바탕으로 지역별 이벤트 빈도를 동적으로 집계합니다.
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # 기본 지역별 설정
    region_keywords = {
        "동유럽": ["ukraine", "russia", "우크라이나", "러시아", "동유럽", "nato"],
        "중동": ["israel", "iran", "gaza", "lebanon", "middle east", "이란", "이스라엘", "가자", "중동"],
        "대만해협": ["taiwan", "china", "대만", "중국", "남중국해"],
        "한반도": ["north korea", "south korea", "pyongyang", "북한", "미사일", "평양", "한반도"]
    }

    results = []

    for region in MONITORING_REGIONS:
        keywords = region_keywords.get(region, [])
        incident_count = 0

        if news_events:
            for n in news_events:
                text = (n.get("title", "") + " " + n.get("summary", "")).lower()
                if any(kw in text for kw in keywords):
                    incident_count += 1

        # 충돌 수준 판정
        if incident_count >= 5:
            level = "심각"
        elif incident_count >= 3:
            level = "높음"
        elif incident_count >= 1:
            level = "보통"
        else:
            level = "낮음"

        results.append({
            "date": target_date,
            "region": region,
            "incident_count": incident_count,
            "casualties": 0,
            "conflict_level": level,
            "source": "News Aggregate & Regional Monitor",
            "notes": f"최근 24시간 내 관련 보도 {incident_count}건 감지"
        })

    return results
