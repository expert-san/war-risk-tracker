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
    "South China Sea confrontation Philippines China"
]

SEARCH_QUERIES_KO = [
    "우크라이나 러시아 전쟁 전선",
    "이스라엘 이란 중동 공습 충돌",
    "대만해협 중국 군사훈련 봉쇄",
    "북한 미사일 핵실험 도발",
    "홍해 후티 공격 상선"
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
    "전쟁", "공습", "미사일", "핵", "군사", "충돌", "동원령",
    "항모", "방공식별구역", "격추", "침공", "해상봉쇄", "계엄", "사상자", "후티", "도발"
]

# 군사적 움직임 분류용 키워드 매핑
MILITARY_EVENT_TYPES = {
    "troop_movement": ["troop movement", "forces move", "convoy", "병력 이동", "부대 이동", "전진 배치"],
    "exercise": ["military drill", "joint exercise", "war games", "군사훈련", "연합훈련", "합동훈련", "기동훈련"],
    "mobilization": ["mobilization", "call-up", "reserve", "동원령", "예비군", "징집"],
    "deployment": ["deployed", "missile battery", "carrier strike group", "air defense", "항모전단", "미사일 배치", "사드", "패트리어트"],
    "combat_action": ["air strike", "missile strike", "intercepted", "artillery", "공습", "미사일 발사", "포격", "요격", "교전"]
}


def fetch_news_events(target_date: str = None, max_items: int = 30) -> List[Dict[str, Any]]:
    """
    글로벌 RSS 및 Google News(영문/한국어) 검색 피드를 취합하여
    분쟁/군사 관련 최신 뉴스를 다각도로 수집합니다.
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    records = []
    seen_titles = set()

    # 1. 키워드 기반 Google News RSS 수집 (영문)
    for query in SEARCH_QUERIES_EN:
        encoded_query = urllib.parse.quote(query)
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

    # 2. 키워드 기반 Google News RSS 수집 (한국어)
    for query in SEARCH_QUERIES_KO:
        encoded_query = urllib.parse.quote(query)
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

    return records[:max_items]


def extract_military_events(news_records: List[Dict[str, Any]], target_date: str = None) -> List[Dict[str, Any]]:
    """
    수집된 뉴스 기사에서 군사적 움직임(병력 이동, 군사훈련, 동원, 무기 배치 등)을
    분류하여 military_events 테이블용 레코드로 추출합니다.
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    events = []
    region_map = {
        "동유럽": ["ukraine", "russia", "우크라이나", "러시아", "벨라루스", "nato", "폴란드"],
        "중동": ["israel", "iran", "gaza", "lebanon", "syria", "이스라엘", "이란", "가자", "레바논", "중동"],
        "대만해협": ["taiwan", "china", "대만", "중국"],
        "한반도": ["north korea", "south korea", "pyongyang", "북한", "평양", "한미", "비무장지대"],
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
            # 중요도(심각도) 판정
            severity = "중요"
            if any(crit in text for crit in ["nuclear", "icbm", "missile strike", "핵", "미사일 발사", "사상자", "침공"]):
                severity = "심각"
            elif any(mod in text for mod in ["drill", "exercise", "훈련", "방문"]):
                severity = "보통"

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
