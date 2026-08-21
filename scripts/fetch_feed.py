"""
Physical AI 블로그용 콘텐츠 피드 생성기.
- arXiv cs.RO(로보틱스) 최신 논문
- 로보틱스/Physical AI 관련 뉴스 (Google 뉴스 검색 RSS, 한국어)
표준 라이브러리만 사용 (pip install 불필요) — GitHub Actions에서 그대로 실행 가능.
"""
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ARXIV_URL = "https://rss.arxiv.org/rss/cs.RO"

# 뉴스 검색 키워드 — 필요하면 이 리스트만 수정해서 범위를 조정 가능
NEWS_QUERY = "Physical AI OR 휴머노이드 로봇 OR 로봇공학 OR 자율주행 로봇"
NEWS_URL = (
    "https://news.google.com/rss/search?q="
    + urllib.parse.quote(NEWS_QUERY)
    + "&hl=ko&gl=KR&ceid=KR:ko"
)

OUTPUT_PATH = "data/feed.json"
MAX_PAPERS = 8
MAX_NEWS = 8


def fetch_xml(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    # 태그 제거 + HTML 엔티티 복원 + 공백 정리
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_arxiv_papers(xml_bytes: bytes, limit: int) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        return []

    papers = []
    for item in channel.findall("item")[:limit]:
        title = clean_text(item.findtext("title", default=""))
        link = (item.findtext("link", default="") or "").strip()
        description = clean_text(item.findtext("description", default=""))
        pub_date = (item.findtext("pubDate", default="") or "").strip()
        categories = [c.text for c in item.findall("category") if c.text]

        # description 형식: "arXiv:ID Announce Type: new. Abstract: ..." 형태를 다듬어 요약만 추출
        abstract = description
        match = re.search(r"Abstract:\s*(.*)", description, flags=re.IGNORECASE)
        if match:
            abstract = match.group(1).strip()
        if len(abstract) > 220:
            abstract = abstract[:220].rsplit(" ", 1)[0] + "…"

        papers.append({
            "type": "paper",
            "title": title,
            "url": link,
            "snippet": abstract,
            "source": "arXiv cs.RO",
            "categories": categories[:3],
            "pub_date": pub_date,
        })
    return papers


def parse_news(xml_bytes: bytes, limit: int) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        return []

    news = []
    for item in channel.findall("item")[:limit]:
        title = clean_text(item.findtext("title", default=""))
        link = (item.findtext("link", default="") or "").strip()
        pub_date = (item.findtext("pubDate", default="") or "").strip()
        source_el = item.find("source")
        source = clean_text(source_el.text) if source_el is not None and source_el.text else "뉴스"

        news.append({
            "type": "news",
            "title": title,
            "url": link,
            "snippet": "",
            "source": source,
            "categories": [],
            "pub_date": pub_date,
        })
    return news


def main() -> None:
    papers = parse_arxiv_papers(fetch_xml(ARXIV_URL), MAX_PAPERS)
    news = parse_news(fetch_xml(NEWS_URL), MAX_NEWS)

    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "papers": papers,
        "news": news,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[fetch_feed] papers={len(papers)} news={len(news)} -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
