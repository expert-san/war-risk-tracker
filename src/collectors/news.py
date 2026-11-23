import datetime
import urllib.parse
from typing import List, Dict, Any, Tuple
import feedparser

# 모니터링 대상 주요 검색 쿼리 (영문 및 한국어)
SEARCH_QUERIES_EN = [
    "war OR conflict OR military strike OR troops deployment",
    "Ukraine Russia war front line",
    "Middle East Israel Iran Lebanon Gaza strike",
    "Taiwan Strait China military drills",
    "North Korea missile nuclear ICBM test",
    "Red Sea Houthi ship attack maritime",
    "South China Sea confrontation Philippines China",
    "USFK OR \"US Forces Korea\" dependents OR family evacuation OR NEO OR ordered departure",
    "\"US embassy\" Seoul evacuation OR \"leave South Korea\" OR \"Do Not Travel\""
]

SEARCH_QUERIES_KO = [
    "우크라이나 러시아 전쟁 전선",
    "이스라엘 이란 중동 공습 충돌",
    "대만해협 중국 군사훈련 봉쇄",
    "북한 미사일 핵실험 도발",
    "홍해 후티 공격 상선",
    "주한미군 가족 철수 OR 소개작전 OR 비전투원 대피",
    "주한 미국대사관 철수 OR 자국민 대피 OR 여행경보"
]

RSS_FEEDS = [
    # BBC World News RSS
    ("http://feeds.bbci.co.uk/news/world/rss.xml", "BBC World"),
    # Al Jazeera World RSS
    ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera"),
    # France 24 World RSS
    ("https://www.france24.com/en/rss", "France 24"),
    # 연합뉴스 국제 RSS
    ("https://www.yonhapnewstv.co.kr/category/news/international/feed/", "연합뉴스TV 국제")
]

# 위험 관련 가중 키워드 (분쟁/위기 필터링용)
RISK_KEYWORDS = [
    "war", "strike", "attack", "invasion", "casualty", "troops",
    "missile", "nuclear", "escalation", "sanction", "mobilization",
    "drone", "blockade", "carrier", "airspace", "adiz", "houthi",
    "usfk", "non-combatant evacuation", "ordered departure", "evacuate", "dependents",
    "전쟁", "공습", "미사일", "핵", "군사", "충돌", "동원령",
    "항모", "방공식별구역", "격추", "침공", "해상봉쇄", "계엄", "사상자", "후티", "도발",
    "주한미군", "미군 가족", "비전투원", "소개작전", "자국민 철수", "철수령", "대피령"
]

# 군사적 움직임 분류용 키워드 매핑 (evacuation을 최우선 검사)
MILITARY_EVENT_TYPES = {
    "evacuation": [
        "non-combatant evacuation", "ordered departure", "dependents leave", "families leave",
        "family evacuation", "evacuate south korea", "leave south korea",
        "주한미군 가족 철수", "미군 가족 철수", "미군 가족 대피", "미군가족 철수",
        "비전투원 소개", "소개작전 발령", "자국민 철수령", "주한 미국대사관 철수"
    ],
    "troop_movement": ["troop movement", "forces move", "convoy", "병력 이동", "부대 이동", "전진 배치"],
    "exercise": ["military drill", "joint exercise", "war games", "courageous channel", "군사훈련", "연합훈련", "합동훈련", "기동훈련"],
    "mobilization": ["mobilization", "call-up", "reserve", "동원령", "예비군", "징집"],
    "deployment": ["deployed", "missile battery", "carrier strike group", "air defense", "항모전단", "미사일 배치", "사드", "패트리어트"],
    "combat_action": ["air strike", "missile strike", "intercepted", "artillery", "공습", "미사일 발사", "포격", "요격", "교전"]
}

# 정례 훈련 오탐 방지용 키워드 (실제 철수 vs 정례 소개훈련 구분)
DRILL_EXCLUSION_KEYWORDS = [
    "exercise", "drill", "training", "simulation", "courageous channel", "annual", "routine",
    "훈련", "연습", "모의", "정례", "연례"
]

# 부정문·부인·가짜뉴스 오탐 방지용 키워드 ("철수 계획 없어", "fake orders" 등 제외)
NEGATION_EXCLUSION_KEYWORDS = [
    "no plan", "no plans", "not planning", "deny", "denies", "denied", "fake", "hoax",
    "false alarm", "rumor", "misinformation", "ruled out", "unlikely", "not evacuating",
    "계획 없", "계획없", "사실무근", "부인", "가짜", "허위", "루머", "오보", "고려 안", "검토 안", "추진 안"
]


def fetch_news_events(target_date: str = None, max_items: int = 50) -> List[Dict[str, Any]]:
    """
    글로벌 RSS 및 Google News(영문/한국어) 검색 피드를 취합하여
    분쟁/군사 관련 최신 뉴스를 다각도로 수집합니다.
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    records = []
    seen_titles = set()

    # 1. 키워드 기반 Google News RSS 수집 (영문 - 최근 48시간 이내 기사만 제한)
    for query in SEARCH_QUERIES_EN:
        encoded_query = urllib.parse.quote(f"{query} when:2d")
        feed_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:4]:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                summary = entry.get("summary", "").strip()
                link = entry.get("link", "")
                source = entry.get("source", {}).get("title", "Google News (EN)")

                matched_keywords = [kw for kw in RISK_KEYWORDS if kw in (title + " " + summary).lower()]
                records.append({
                    "date": target_date,
                    "title": title,
                    "link": link,
                    "source": source,
                    "summary": summary[:250],
                    "keywords": ", ".join(matched_keywords) if matched_keywords else "general"
                })
        except Exception as e:
            print(f"Failed to fetch news for EN query '{query}': {e}")
            continue

    # 2. 키워드 기반 Google News RSS 수집 (한국어 - 최근 48시간 이내 기사만 제한)
    for query in SEARCH_QUERIES_KO:
        encoded_query = urllib.parse.quote(f"{query} when:2d")
        feed_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                summary = entry.get("summary", "").strip()
                link = entry.get("link", "")
                source = entry.get("source", {}).get("title", "Google News (KR)")

                matched_keywords = [kw for kw in RISK_KEYWORDS if kw in (title + " " + summary).lower()]
                records.append({
                    "date": target_date,
                    "title": title,
                    "link": link,
                    "source": source,
                    "summary": summary[:250],
                    "keywords": ", ".join(matched_keywords) if matched_keywords else "general"
                })
        except Exception as e:
            print(f"Failed to fetch news for KO query '{query}': {e}")
            continue

    # 3. 주요 외신 공식 RSS 피드
    for url, source_name in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                text = (title + " " + summary).lower()

                matched_keywords = [kw for kw in RISK_KEYWORDS if kw in text]
                if not matched_keywords or title in seen_titles:
                    continue

                seen_titles.add(title)
                records.append({
                    "date": target_date,
                    "title": title,
                    "link": entry.get("link", ""),
                    "source": source_name,
                    "summary": summary[:250],
                    "keywords": ", ".join(matched_keywords)
                })
        except Exception as e:
            print(f"Failed to fetch feed '{source_name}': {e}")
            continue

    # 미군 가족 철수 / 비전투원 소개(NEO) 관련 핵심 기사는 잘리지 않도록 최상단 우선 배치
    evac_kws = MILITARY_EVENT_TYPES["evacuation"]
    records.sort(
        key=lambda r: 0 if any(k in (r["title"] + " " + r["summary"]).lower() for k in evac_kws) else 1
    )

    return records[:max_items]


def extract_military_events(news_records: List[Dict[str, Any]], target_date: str = None) -> List[Dict[str, Any]]:
    """
    수집된 뉴스 기사에서 군사적 움직임(미군가족/비전투원 철수, 병력 이동, 군사훈련, 동원, 무기 배치 등)을
    분류하여 military_events 테이블용 레코드로 추출합니다.
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    events = []
    region_map = {
        "동유럽": ["ukraine", "russia", "우크라이나", "러시아", "벨라루스", "nato", "폴란드"],
        "중동": ["israel", "iran", "gaza", "lebanon", "syria", "이스라엘", "이란", "가자", "레바논", "중동"],
        "대만해협": ["taiwan", "china", "대만", "중국"],
        "한반도": ["north korea", "south korea", "pyongyang", "usfk", "seoul", "북한", "평양", "한미", "비무장지대", "주한미군", "한국", "서울"],
        "홍해·아덴만": ["red sea", "houthi", "yemen", "홍해", "후티", "예멘", "아덴만"],
        "남중국해": ["south china sea", "philippines", "남중국해", "필리핀"]
    }

    for item in news_records:
        text = (item.get("title", "") + " " + item.get("summary", "")).lower()

        # 1. 지역 판별
        detected_region = "기타/글로벌"
        for region, kws in region_map.items():
            if any(k in text for k in kws):
                detected_region = region
                break

        # 2. 군사 이벤트 유형 판별
        detected_event_type = None
        for etype, kws in MILITARY_EVENT_TYPES.items():
            if any(k in text for k in kws):
                detected_event_type = etype
                break

        if detected_event_type:
            # 부정문·부인·가짜뉴스 기사 오탐 방지 (예: "철수 계획 없어", "fake orders")
            is_negated = any(nk in text for nk in NEGATION_EXCLUSION_KEYWORDS)
            if is_negated and detected_event_type in ("evacuation", "mobilization"):
                continue

            # 정례 소개훈련(Courageous Channel 등) 오탐 방지: 훈련 키워드 동반 시 exercise로 분류
            is_routine_drill = any(dk in text for dk in DRILL_EXCLUSION_KEYWORDS)
            if detected_event_type == "evacuation" and is_routine_drill:
                detected_event_type = "exercise"

            # 중요도(심각도) 판정
            if detected_event_type == "evacuation":
                severity = "심각"
            elif any(crit in text for crit in ["nuclear", "icbm", "missile strike", "핵", "미사일 발사", "사상자", "침공"]):
                severity = "심각"
            elif is_routine_drill or any(mod in text for mod in ["방문"]):
                severity = "보통"
            else:
                severity = "중요"

            events.append({
                "date": target_date,
                "region": detected_region,
                "event_type": detected_event_type,
                "description": item.get("title", "")[:200],
                "severity": severity,
                "source": item.get("source", "News Monitor")
            })

    return events


if __name__ == "__main__":
    import json
    news = fetch_news_events()
    print(f"Fetched {len(news)} news items.")
    evs = extract_military_events(news)
    print(f"Extracted {len(evs)} military events:")
    print(json.dumps(evs[:3], indent=2, ensure_ascii=False))
