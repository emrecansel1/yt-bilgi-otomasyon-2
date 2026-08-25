import json
import os
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(BASE, "news.json")

FEEDS = {
    "TR": "https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr",
    "WORLD": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 TrendAvcisi/1.0"
}

BAD_WORDS = [
    "casino", "bet", "bahis", "poker"
]


def clean_text(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_news(url, country):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )
        response.raise_for_status()

        root = ET.fromstring(response.content)

        results = []
        seen = set()

        for item in root.findall(".//item"):
            title = clean_text(
                item.findtext("title", default="")
            )

            link = item.findtext("link", default="")
            pub_date = item.findtext("pubDate", default="")

            source_node = item.find("source")
            source = ""

            if source_node is not None:
                source = clean_text(source_node.text)

            if not title:
                continue

            key = title.lower()

            if key in seen:
                continue

            if any(x in key for x in BAD_WORDS):
                continue

            seen.add(key)

            results.append({
                "title": title,
                "link": link,
                "published": pub_date,
                "source": source,
                "country": country
            })

        return results

    except Exception as e:
        print("[HATA]", country, e)
        return []


def main():
    print("=" * 55)
    print("           GUNCEL GUNDEM TARAYICI")
    print("=" * 55)

    all_news = []

    for country, url in FEEDS.items():
        print()
        print("[TARAMA]", country)

        news = get_news(url, country)

        print("[OK]", country, len(news), "haber")

        all_news.extend(news[:30])

    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Google News RSS",
        "news": all_news
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 55)
    print("TOPLAM HABER:", len(all_news))
    print("=" * 55)

    for i, item in enumerate(all_news[:20], 1):
        print(
            f"{i:02d}. "
            f"[{item['country']}] "
            f"{item['title']}"
        )

    print()
    print("Kaydedildi:", OUTPUT)


if __name__ == "__main__":
    main()
