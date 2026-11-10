import datetime
import urllib.parse
from typing import List, Dict, Any
import feedparser

# 모니터링 대상 주요 검색 키워드
SEARCH_QUERIES = [
    "war OR conflict OR military strike OR troops deployment",
    "Ukraine Russia war",
    "Middle East Israel Iran Gaza conflict",
    "Taiwan Strait China military",
    "North Korea missile nuclear"
]

RSS_FEEDS = [
    # Google News RSS (키워드 검색 기반)
    "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en",
    # BBC World News RSS
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    # Al Jazeera World RSS
    "https://www.aljazeera.com/xml/rss/all.xml"
]

# 위험 관련 가중 키워드 (간이 감성/위험도 필터링용)
RISK_KEYWORDS = [
    "war", "strike", "attack", "invasion", "casualty", "troops",
    "missile", "nuclear", "escalation", "sanction", "mobilization",
    "전쟁", "공습", "미사일", "핵", "군사", "충돌", "동원령"
]


def fetch_news_events(target_date: str = None, max_items: int = 20) -> List[Dict[str, Any]]:
    """
    주요 국제 뉴스 RSS 및 검색 피드를 분석하여 
    분쟁/군사 관련 최신 뉴스를 수집합니다.
    """
    if target_date is None:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")

    records = []
    seen_titles = set()

    # 1. 키워드 기반 Google News RSS 수집
    for query in SEARCH_QUERIES:
        encoded_query = urllib.parse.quote(query)
        feed_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)

                summary = entry.get("summary", "").strip()
                link = entry.get("link", "")
                source = entry.get("source", {}).get("title", "Google News")

                # 위험 키워드 추출
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
            print(f"Failed to fetch news for query '{query}': {e}")
            continue

    # 2. 일반 월드 뉴스 피드 수집
    general_feeds = [
        ("http://feeds.bbci.co.uk/news/world/rss.xml", "BBC World"),
        ("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera")
    ]
    for url, source_name in general_feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                text = (title + " " + summary).lower()

                # 군사/분쟁 관련 키워드가 1개 이상 포함된 경우만 수집
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


if __name__ == "__main__":
    import json
    news = fetch_news_events()
    print(f"Fetched {len(news)} relevant news items:")
    print(json.dumps(news[:2], indent=2, ensure_ascii=False))
