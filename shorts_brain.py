import json
import os
import re
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))

TREND_FILE = os.path.join(BASE, "trends.json")
NEWS_FILE = os.path.join(BASE, "news.json")
HISTORY_FILE = os.path.join(BASE, "shorts_history.json")
OUTPUT_FILE = os.path.join(BASE, "shorts_topics.json")

GOOD_WORDS = [
    "bilim", "science", "uzay", "space", "nasa",
    "astronomi", "astronomy", "fizik", "physics",
    "kimya", "chemistry", "biyoloji", "biology",
    "genetik", "genetics", "evrim", "evolution",
    "deney", "experiment", "araştırma", "research",
    "bilim insanı", "scientist",

    "teknoloji", "technology", "yapay zeka",
    "artificial intelligence", "ai", "robot", "robotics",
    "çip", "chip", "telefon", "iphone",
    "bilgisayar", "internet", "uydu", "satellite",
    "uzay teknolojisi", "apple", "tesla",

    "keşif", "discovery", "icat", "invention",
    "tarih", "history", "tarihi", "historical",
    "arkeoloji", "archaeology", "antik", "ancient",
    "medeniyet", "civilization", "kazı", "fossil",
    "fosil", "müze", "harabe",

    "dünya", "earth", "evren", "universe",
    "gezegen", "planet", "asteroit", "asteroid",
    "meteor", "ay", "moon", "mars",
    "deprem", "earthquake", "volkan", "volcano",
    "fırtına", "storm", "iklim", "climate",
    "okyanus", "ocean", "enerji", "energy",

    "doğa", "nature", "hayvan", "animal",
    "köpek", "kedi", "kuş", "balina",
    "köpekbalığı", "shark", "dinozor", "dinosaur",

    "beyin", "brain", "insan", "human",
    "vücut", "body", "hafıza", "memory",
    "uyku", "sleep", "psikoloji", "psychology",

    "gizem", "mystery", "keşfedildi", "discovered",
    "bulundu", "found", "ortaya çıktı",
    "yeni keşif", "new discovery",
    "ilk kez", "first time",
    "rekor", "record", "tarihte ilk"
]

BAD_WORDS = [
    "bahis", "casino", "kupon", "poker",
    "maç sonucu", "canlı skor", "oran",
    "magazin", "aşk", "dizi", "fragman",
    "ünlü", "şarkıcı", "oyuncu",
    "dedikodu", "ilişki", "sevgili",
    "moda", "kombin", "güzellik"
]


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def normalize(text):
    text = str(text or "").lower()
    text = text.replace("'", "'")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def traffic_number(value):
    text = normalize(value)
    text = text.replace(",", "").replace(" ", "")

    try:
        if text.endswith("m+"):
            return float(text[:-2]) * 1_000_000
        if text.endswith("k+"):
            return float(text[:-2]) * 1_000
        if text.endswith("+"):
            return float(text[:-1])
        return float(text)
    except Exception:
        return 0


def score_text(text):
    text = normalize(text)
    score = 0

    for word in GOOD_WORDS:
        if word in text:
            score += 8

    for word in BAD_WORDS:
        if word in text:
            score -= 20

    if len(text) < 8:
        score -= 20

    return score


SHORTS_BLOCK_WORDS = [
    "cansız bedeni", "cansız beden", "ölü bulundu", "öldü",
    "ölümü", "cinayet", "katil", "suikast", "tutuklandı",
    "gözaltına alındı", "hapis cezası", "şiddet", "saldırı",
    "kavga", "yaralama", "kaçırıldı",

    "soruşturma", "dava", "istifa etti", "milletvekili",
    "belediye başkanı", "bakan", "cumhurbaşkanı", "seçim",
    "parti", "chp", "ak parti", "mhp", "meclis",
    "yaptırım", "tarife", "hükümet", "başkanlık",

    "savaş", "savaşacak", "çatışma", "füze", "füzeleri",
    "asker", "askeri", "ordu", "troops", "missile",
    "missiles", "war", "warfare", "military", "sanctions",

    "magazin", "sevgili", "aşk", "boşanma", "evlendi",
    "ilişki", "ünlü", "oyuncu", "şarkıcı", "reality",
    "celebrity", "dating", "divorce", "married",
    "actress", "actor", "comedian",

    "maç", "maçı", "futbolcu", "futbol", "transfer",
    "hakem", "kadrosu", "lig", "şampiyon", "gol",
    "basketbol", "voleybol", "nba", "football",
    "soccer", "match", "player", "coach", "league",

    "dizi", "fragman", "bölüm", "kanal d", "masterchef",
    "reality show", "episode", "trailer", "season",
]

SHORTS_GOOD_WORDS = [
    "bilim", "bilimsel", "science", "scientific",
    "deney", "experiment", "araştırma", "research",
    "keşif", "keşfedildi", "discovery",

    "uzay", "astronomi", "astronomy", "gezegen",
    "planet", "yıldız", "star", "galaksi", "galaxy",
    "evren", "universe", "nasa", "ay tutulması",
    "güneş tutulması", "eclipse", "moon", "mars",
    "jupiter", "saturn", "black hole",

    "teknoloji", "technology", "yapay zeka", "yapay zekâ",
    "artificial intelligence", "ai", "robot", "robotics",
    "çip", "chip", "işlemci", "processor",
    "bilgisayar", "computer", "internet",
    "iphone", "apple", "android", "google",
    "nvidia", "samsung", "xiaomi", "tesla",
    "gadget", "software", "hardware",

    "tarih", "tarihi", "history", "historical",
    "antik", "ancient", "medeniyet", "civilization",
    "mısır", "egypt", "roma", "roman", "osmanlı",
    "ottoman", "einstein", "newton", "napoleon",
    "dahi", "genius",

    "beyin", "brain", "insan vücudu", "human body",
    "biyoloji", "biology", "dna", "genetik", "genetics",
    "hücre", "cell", "evrim", "evolution",
    "psikoloji", "psychology",

    "doğa", "nature", "hayvan", "animal",
    "fosil", "fossil", "arkeoloji", "archaeology",
    "dinozor", "dinosaur", "okyanus", "ocean",
    "volkan", "volcano", "deprem", "earthquake",

    "ekonomi", "economy", "ekonomik", "economic",
    "finans", "finance", "borsa", "stock",
    "nvidia stock", "bitcoin", "kripto", "crypto",
    "altın", "gold", "enflasyon", "inflation",

    "gta 6", "gta vi", "playstation", "xbox",
    "steam", "gaming", "video game",

    "neden", "nasıl", "why", "how",
    "ilk kez", "ilk defa", "first time",
    "rekor", "record", "gizem", "mystery",
    "şaşırtıcı", "surprising", "sızıntı", "leak",
    "yeni", "new",
]

def shorts_topic_allowed(item):
    topic = item.get("topic") or item.get("title") or ""
    text = normalize(topic)

    hard_block = [
        "trump", "putin", "zelenskiy", "zelensky",
        "cumhurbaşkanı", "başkan", "bakan",
        "milletvekili", "belediye başkanı", "hükümet",
        "meclis", "chp", "ak parti", "mhp",
        "seçim", "parti", "siyasi", "siyaset",
        "soruşturma", "istifa", "dava",

        "savaş", "war", "warfare", "çatışma",
        "füze", "missile", "missiles", "asker",
        "military", "troops", "ordu", "sanctions",
        "yaptırım",

        "cinayet", "katil", "öldü", "ölü bulundu",
        "cansız beden", "suikast", "tutuklandı",
        "gözaltına alındı", "hapis", "şiddet",
        "saldırı", "yaralama", "kaçırıldı",

        "magazin", "sevgili", "aşk", "boşanma",
        "evlendi", "ilişki", "dedikodu",
        "celebrity", "dating", "divorce",
        "married", "actress", "actor",

        "maç", "maçı", "futbol", "futbolcu",
        "football", "soccer", "basketbol",
        "basketball", "voleybol", "transfer",
        "hakem", "lig", "league", "match",
        "player", "coach",

        "dizi", "fragman", "bölüm", "episode",
        "trailer", "masterchef", "reality show",
    ]

    for word in hard_block:
        if normalize(word) in text:
            return False

    knowledge_words = [
        "bilim", "science", "scientific",
        "fizik", "physics", "kimya", "chemistry",
        "biyoloji", "biology", "genetik", "genetics",
        "deney", "experiment", "araştırma", "research",

        "uzay", "space", "nasa", "astronomi",
        "astronomy", "gezegen", "planet",
        "galaksi", "galaxy", "evren", "universe",
        "asteroit", "asteroid", "meteor",
        "mars", "jupiter", "saturn",
        "black hole", "kara delik",
        "eclipse", "tutulma",

        "teknoloji", "technology",
        "yapay zeka", "artificial intelligence",
        "robot", "robotics", "çip", "chip",
        "işlemci", "processor", "telefon",
        "iphone", "android", "apple",
        "google", "nvidia", "samsung",
        "xiaomi", "tesla", "bilgisayar",
        "computer", "internet", "uydu",
        "satellite", "yazılım", "software",
        "donanım", "hardware",

        "tarih", "history", "historical",
        "antik", "ancient", "arkeoloji",
        "archaeology", "medeniyet",
        "civilization", "osmanlı", "ottoman",
        "roma", "roman", "mısır", "egypt",
        "kazı", "fosil", "fossil",
        "dinozor", "dinosaur",
        "einstein", "newton",

        "doğa", "nature", "hayvan", "animal",
        "köpek", "kedi", "kuş", "balina",
        "köpekbalığı", "shark",
        "okyanus", "ocean", "volkan",
        "volcano", "deprem", "earthquake",
        "iklim", "climate",

        "beyin", "brain", "insan vücudu",
        "human body", "hafıza", "memory",
        "uyku", "sleep", "psikoloji",
        "psychology", "dna", "hücre", "cell",
        "evrim", "evolution",
    ]

    has_knowledge_topic = any(
        normalize(word) in text
        for word in knowledge_words
    )

    if not has_knowledge_topic:
        return False

    return True


def candidate_score(item):
    topic = item.get("topic") or item.get("title") or ""
    text = normalize(topic)

    if not shorts_topic_allowed(item):
        return 0

    score = 20

    relevance = score_text(topic)
    score += relevance

    traffic = traffic_number(item.get("traffic"))

    if traffic >= 1_000_000:
        score += 35
    elif traffic >= 500_000:
        score += 30
    elif traffic >= 200_000:
        score += 25
    elif traffic >= 100_000:
        score += 20
    elif traffic >= 50_000:
        score += 15
    elif traffic >= 20_000:
        score += 10
    elif traffic >= 10_000:
        score += 7
    elif traffic >= 5_000:
        score += 5

    if item.get("type") == "news":
        score += 15

    words = re.findall(
        r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+",
        text
    )

    if len(words) >= 5:
        score += 5

    curiosity_patterns = [
        "neden", "nasıl", "ilk kez", "ilk defa",
        "keşfedildi", "bulundu", "rekor",
        "gizem", "sızıntı", "yeni",
        "tarihi", "şaşırtıcı"
    ]

    if any(x in text for x in curiosity_patterns):
        score += 8

    if len(text) < 8:
        score -= 20

    return max(0, min(100, score))


def history_keys():
    data = load_json(HISTORY_FILE, [])

    if not isinstance(data, list):
        return set()

    result = set()

    for item in data:
        if isinstance(item, str):
            result.add(normalize(item))
        elif isinstance(item, dict):
            topic = item.get("topic")
            if topic:
                result.add(normalize(topic))

    return result


def save_history(selected):
    history = load_json(HISTORY_FILE, [])

    if not isinstance(history, list):
        history = []

    for item in selected:
        history.append({
            "topic": item.get("topic"),
            "score": item.get("score"),
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    history = history[-200:]

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(
            history,
            f,
            ensure_ascii=False,
            indent=2
        )


def similar(a, b):
    a_words = set(
        x for x in re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+", normalize(a))
        if len(x) >= 4
    )

    b_words = set(
        x for x in re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+", normalize(b))
        if len(x) >= 4
    )

    if not a_words or not b_words:
        return False

    common = a_words & b_words

    return len(common) >= 2


def main():
    print("=" * 55)
    print("          SHORTS 5 KONU SECIM MOTORU")
    print("=" * 55)

    trends_data = load_json(TREND_FILE, {})
    news_data = load_json(NEWS_FILE, {})

    trends = trends_data.get("trends", [])
    news = news_data.get("news", [])

    candidates = []

    for item in trends:
        candidates.append({
            "type": "trend",
            "topic": item.get("topic", ""),
            "country": item.get("country", ""),
            "source": item.get("source", ""),
            "traffic": item.get("traffic", ""),
            "score": candidate_score(item)
        })

    for item in news:
        candidates.append({
            "type": "news",
            "topic": item.get("title", ""),
            "country": item.get("country", ""),
            "source": item.get("source", ""),
            "link": item.get("link", ""),
            "published": item.get("published", ""),
            "score": candidate_score(item)
        })

    history = history_keys()

    def is_in_history(topic):
        for old_topic in history:
            if similar(topic, old_topic):
                return True
        return False

    fresh = []
    backup_candidates = []

    for item in candidates:
        topic = normalize(item.get("topic"))

        if not topic:
            continue

        if is_in_history(topic):
            continue

        if item["score"] >= 70:
            fresh.append(item)
        elif item["score"] >= 45:
            backup_
