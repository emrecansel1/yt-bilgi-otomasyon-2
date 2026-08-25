import json
import os
import re
import html
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))

DECISION_FILE = os.path.join(BASE, "shorts_topics.json")
OUTPUT_FILE = os.path.join(BASE, "arastirma.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 TrendAvcisiResearch/3.0"
}

SOURCE_BLACKLIST = {
    "facebook",
    "instagram",
    "tiktok",
    "x.com",
    "twitter",
}

STOP_WORDS = {
    "bir", "bu", "şu", "ve", "ile", "için",
    "olan", "olarak", "daha", "son", "gibi",
    "çok", "adımı", "adım", "listeden",
    "çıkardı", "çıktı", "yeni", "resmi",
    "the", "and", "with", "from", "this",
    "news", "haber", "haberleri"
}


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize(text):
    return clean(text).lower()


def remove_source(title):
    title = clean(title)

    if " - " in title:
        parts = title.rsplit(" - ", 1)

        if len(parts) == 2 and len(parts[0]) > 10:
            return parts[0].strip()

    return title


def words(text):
    return [
        x.lower()
        for x in re.findall(
            r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+",
            normalize(text)
        )
        if len(x) >= 4 and x.lower() not in STOP_WORDS
    ]


def get_news_search(query):
    url = (
        "https://news.google.com/rss/search?"
        "q=" + quote(query) +
        "&hl=tr&gl=TR&ceid=TR:tr"
    )

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        root = ET.fromstring(response.content)

        results = []

        for item in root.findall(".//item"):
            title = clean(
                item.findtext("title", default="")
            )

            link = item.findtext(
                "link",
                default=""
            )

            published = item.findtext(
                "pubDate",
                default=""
            )

            source_node = item.find("source")
            source = ""

            if source_node is not None:
                source = clean(source_node.text)

            if not title:
                continue

            results.append({
                "title": title,
                "link": link,
                "published": published,
                "source": source
            })

        return results

    except Exception as e:
        print("[HATA] Arama:", e)
        return []


def extract_keywords(title):
    result = []

    for word in words(title):
        if word not in result:
            result.append(word)

    return result[:8]


def relevance_score(topic_keywords, title):
    title_words = set(words(title))
    keyword_set = set(
        x.lower()
        for x in topic_keywords
        if len(x) >= 4
    )

    common = keyword_set & title_words

    score = len(common) * 20

    important = {
        "iphone", "apple", "nvidia", "google",
        "suriye", "trump", "nasa", "mars",
        "einstein", "bitcoin", "tesla",
        "xiaomi", "android"
    }

    for word in common:
        if word in important:
            score += 15

    return score


def topic_related(topic_keywords, title):
    title_words = set(words(title))
    keyword_set = set(
        x.lower()
        for x in topic_keywords
        if len(x) >= 4
    )

    common = keyword_set & title_words

    return len(common) >= 1


def unique_sources(results):
    output = []
    seen_titles = set()
    seen_sources = set()

    for item in results:
        title_key = normalize(item.get("title"))
        source_key = normalize(item.get("source"))

        if not title_key:
            continue

        if title_key in seen_titles:
            continue

        if source_key in SOURCE_BLACKLIST:
            continue

        if source_key and source_key in seen_sources:
            continue

        seen_titles.add(title_key)

        if source_key:
            seen_sources.add(source_key)

        output.append(item)

    return output


def build_facts(topic, sources):
    facts = []

    for source in sources:
        title = remove_source(
            source.get("title", "")
        )

        if not title:
            continue

        facts.append({
            "source": source.get("source", ""),
            "title": title,
            "published": source.get("published", ""),
            "link": source.get("link", "")
        })

    return facts


def main():

    print("=" * 60)
    print("             KONUYU ARAŞTIR")
    print("=" * 60)

    try:
        with open(
            DECISION_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            decision = json.load(f)

    except Exception as e:
        print("[HATA] shorts_topics.json okunamadı:", e)
        return

    topics_list = decision.get(
        "topics",
        []
    )

    if not topics_list:
        print("[HATA] shorts_topics.json içinde konu yok.")
        return

    selected = topics_list[0]

    original_title = (
        selected.get("title")
        or selected.get("topic")
        or ""
    )

    if not original_title:
        print("[HATA] Seçilen konu yok.")
        return

    clean_topic = remove_source(
        original_title
    )

    keywords = extract_keywords(
        clean_topic
    )

    print()
    print("SEÇİLEN KONU:")
    print(clean_topic)

    print()
    print("ANAHTAR KELİMELER:")
    print(", ".join(keywords))

    if not keywords:
        print("[HATA] Anahtar kelime bulunamadı.")
        return

    query = " ".join(
        keywords[:6]
    )

    print()
    print("[ARAMA 1]", query)

    results = get_news_search(query)

    if len(results) < 5 and len(keywords) >= 2:

        query2 = " ".join(
            keywords[:4]
        )

        print("[ARAMA 2]", query2)

        results.extend(
            get_news_search(query2)
        )

    if len(results) < 5:

        print("[ARAMA 3]", clean_topic)

        results.extend(
            get_news_search(clean_topic)
        )

    results = unique_sources(results)

    print()
    print("Ham kaynak:", len(results))

    ranked = []

    for item in results:

        title = remove_source(
            item.get("title", "")
        )

        if not topic_related(
            keywords,
            title
        ):
            print(
                "[ELENDİ - ALAKASIZ]",
                title
            )
            continue

        score = relevance_score(
            keywords,
            title
        )

        item["relevance_score"] = score

        ranked.append(item)

    ranked.sort(
        key=lambda x: x.get(
            "relevance_score",
            0
        ),
        reverse=True
    )

    results = ranked[:5]

    source_count = len(results)

    if source_count >= 3:
        status = "verified_multiple_sources"
    elif source_count >= 2:
        status = "multiple_sources_found"
    elif source_count == 1:
        status = "single_source_only"
    else:
        status = "insufficient_sources"

    facts = build_facts(
        clean_topic,
        results
    )

    research = {
        "updated_at":
            datetime.now(timezone.utc).isoformat(),

        "topic":
            clean_topic,

        "original_title":
            original_title,

        "keywords":
            keywords,

        "search_query":
            query,

        "source_count":
            source_count,

        "sources":
            results,

        "facts":
            facts,

        "verification": {
            "status":
                status,

            "minimum_sources_target":
                2,

            "recommended_sources":
                3,

            "safe_for_script":
                source_count >= 2,

            "note":
                (
                    "Yalnızca konu ile alakalı "
                    "kaynaklar araştırmaya dahil edildi."
                )
        }
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            research,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 60)
    print("ARAŞTIRMA SONUCU")
    print("=" * 60)

    print("Konu:", clean_topic)
    print("Kaynak sayısı:", source_count)
    print("Durum:", status)

    print()

    for i, item in enumerate(
        results,
        1
    ):

        print(
            f"{i:02d}. "
            f"[{item.get('relevance_score', 0)}] "
            f"{item.get('source', '')} | "
            f"{remove_source(item.get('title', ''))}"
        )

    print()
    print("Kaydedildi:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
