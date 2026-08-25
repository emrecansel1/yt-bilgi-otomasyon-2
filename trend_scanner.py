import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
TREND_FILE = os.path.join(BASE, "trends.json")

RSS_URLS = {
    "TR": "https://trends.google.com/trending/rss?geo=TR",
    "US": "https://trends.google.com/trending/rss?geo=US",
    "GB": "https://trends.google.com/trending/rss?geo=GB",
    "DE": "https://trends.google.com/trending/rss?geo=DE"
}

def get_trends(country, url):
    try:
        response = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )
        response.raise_for_status()

        root = ET.fromstring(response.content)

        results = []

        for item in root.findall(".//item"):
            title = item.findtext("title")

            if not title:
                continue

            traffic = item.findtext(
                "{https://trends.google.com/trending/rss}approx_traffic"
            )

            results.append({
                "topic": title.strip(),
                "country": country,
                "source": "Google Trends",
                "traffic": traffic,
                "trend_score": 0
            })

        return results

    except Exception as e:
        print(f"[HATA] {country}: {e}")
        return []


def calculate_score(item):
    traffic = str(item.get("traffic") or "").upper()
    traffic = traffic.replace(",", "").replace(" ", "")

    score = 40

    try:
        if traffic.endswith("K+"):
            number = float(traffic[:-2]) * 1000
        elif traffic.endswith("M+"):
            number = float(traffic[:-2]) * 1000000
        elif traffic.endswith("+"):
            number = float(traffic[:-1])
        else:
            number = float(traffic)
    except ValueError:
        number = 0

    if number >= 1000000:
        score += 55
    elif number >= 500000:
        score += 50
    elif number >= 200000:
        score += 45
    elif number >= 100000:
        score += 40
    elif number >= 50000:
        score += 35
    elif number >= 20000:
        score += 30
    elif number >= 10000:
        score += 25
    elif number >= 5000:
        score += 20
    elif number >= 2000:
        score += 15
    elif number >= 1000:
        score += 10
    elif number >= 500:
        score += 5

    return min(score, 100)


def main():
    print("=" * 55)
    print("              GERCEK TREND AVCISI")
    print("=" * 55)
    print()

    all_trends = []

    for country, url in RSS_URLS.items():
        print(f"[TARAMA] {country} ...")

        trends = get_trends(country, url)

        for item in trends:
            item["trend_score"] = calculate_score(item)
            all_trends.append(item)

        print(f"[OK] {country}: {len(trends)} trend")

    all_trends.sort(
        key=lambda x: x.get("trend_score", 0),
        reverse=True
    )

    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Google Trends",
        "trends": all_trends
    }

    with open(TREND_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 55)
    print(f"TOPLAM TREND: {len(all_trends)}")
    print("=" * 55)
    print()

    for i, item in enumerate(all_trends[:15], 1):
        print(
            f"{i:02d}. "
            f"{item['topic']} | "
            f"{item['country']} | "
            f"{item.get('traffic')} | "
            f"PUAN {item['trend_score']}"
        )

    print()
    print("Trend verileri kaydedildi:")
    print(TREND_FILE)


if __name__ == "__main__":
    main()
