import os
import re
import json
import time
import requests
import hashlib

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")
VISUALS = os.path.join(OUT, "visuals")
CONTENT = os.path.join(OUT, "current_content.txt")
TOPIC_FILE = os.path.join(OUT, "current_topic.txt")
MANIFEST = os.path.join(OUT, "visual_manifest.json")

REPO_BASE = os.path.dirname(os.path.abspath(__file__))
USED_VISUALS_FILE = os.path.join(REPO_BASE, "video_used_visuals.json")
MAX_USED = 5000

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

WORDS_PER_SCENE = 130

os.makedirs(VISUALS, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "YTBilgiUzun/9.0"})

GENERIC_FALLBACK_QUERIES_EN = [
    "old vintage photo history",
    "ancient artifact museum",
    "historical document archive",
    "black and white history photo",
    "science laboratory vintage",
    "old map exploration",
    "antique object closeup",
    "historic building architecture",
    "dramatic sky abstract",
    "old book library",
]


def load_used_visuals():
    if os.path.exists(USED_VISUALS_FILE):
        try:
            with open(USED_VISUALS_FILE, encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("urls", [])), set(data.get("hashes", []))
        except Exception:
            return set(), set()
    return set(), set()


def save_used_visuals(used_urls, used_hashes):
    with open(USED_VISUALS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"urls": list(used_urls)[-MAX_USED:], "hashes": list(used_hashes)[-MAX_USED:]},
            f, ensure_ascii=False, indent=2
        )


def clean_text(text):
    text = re.sub(r"===.*?===", " ", text)
    text = re.sub(r"\[\s*\d+:\d+\s*-\s*\d+:\d+\s*\]", " ", text)
    text = re.sub(
        r"\([^)]*(ses efekti|geçiş müziği|müzik|ambiyans|efekt)[^)]*\)",
        " ", text, flags=re.I
    )
    text = re.sub(r"^\s*(DIŞ SES|ANLATICI|SES)\s*[:\-]\s*", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_topic():
    if os.path.exists(TOPIC_FILE):
        with open(TOPIC_FILE, encoding="utf-8") as f:
            t = f.read().strip()
            if t:
                return t

    with open(CONTENT, "r", encoding="utf-8") as f:
        text = f.read()

    if "=== SESLENDİRME METNİ ===" in text:
        text = text.split("=== SESLENDİRME METNİ ===", 1)[1]
    if "=== METADATA ===" in text:
        text = text.split("=== METADATA ===", 1)[0]

    for line in [clean_text(x) for x in text.splitlines()]:
        if len(line) >= 20:
            return line[:150]

    return "tarih bilim"


def get_narration_text():
    with open(CONTENT, "r", encoding="utf-8") as f:
        text = f.read()

    if "=== SESLENDİRME METNİ ===" in text:
        text = text.split("=== SESLENDİRME METNİ ===", 1)[1]
    if "=== METADATA ===" in text:
        text = text.split("=== METADATA ===", 1)[0]

    return clean_text(text)


def chunk_into_scenes(text, words_per_scene=WORDS_PER_SCENE):
    sentences = re.split(r"(?<=[.!?])\s+", text)

    scenes = []
    current = []
    current_words = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        current.append(sentence)
        current_words += len(sentence.split())

        if current_words >= words_per_scene:
            scenes.append(" ".join(current))
            current = []
            current_words = 0

    if current:
        scenes.append(" ".join(current))

    return [s for s in scenes if len(s) > 20]


def call_gemini_with_retry(prompt, max_retries=3, timeout=60):
    if not GEMINI_API_KEY:
        return None

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-3.6-flash:generateContent"
    )

    delay = 3

    for attempt in range(1, max_retries + 1):
        try:
            response = session.post(
                url,
                params={"key": GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=timeout
            )

            if response.status_code in (429, 503):
                time.sleep(delay)
                delay = min(delay * 2, 20)
                continue

            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

        except Exception:
            time.sleep(delay)
            delay = min(delay * 2, 20)

    return None


def generate_visual_queries_batch(scenes, topic):
    numbered = "\n".join(f"{i}: {s[:180]}" for i, s in enumerate(scenes, 1))

    prompt = f"""
Konu: {topic}

Aşağıda numaralandırılmış {len(scenes)} adet Türkçe belgesel
metni parçası var. Her parça için, o parçanın anlattığı
olayı/nesneyi/yeri/kişiyi/dönemi stok fotoğraf sitesinde
aratmak için 3-6 kelimelik SOMUT, GÖRSEL OLARAK ARANABİLİR bir
İngilizce arama sorgusu yaz.

METİN PARÇALARI:
{numbered}

KURALLAR:
- Soyut kavram yazma.
- Metinde geçen somut özel isim, nesne, yer, olay, dönem varsa
  onu kullan.
- Tırnak işareti kullanma.

ÇIKTI FORMATI (tam olarak bunu kullan, başka hiçbir şey yazma):
1: <sorgu>
2: <sorgu>
...
{len(scenes)}: <sorgu>
"""

    raw = call_gemini_with_retry(prompt, max_retries=3, timeout=90)

    if not raw:
        return [None] * len(scenes)

    results = [None] * len(scenes)

    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue

        num_part, query_part = line.split(":", 1)
        num_part = num_part.strip()

        if not num_part.isdigit():
            continue

        idx = int(num_part)

        if 1 <= idx <= len(scenes):
            query = query_part.strip().strip('"').strip()
            query = " ".join(query.split())
            if query and len(query) >= 3:
                results[idx - 1] = query[:180]

    return results


def make_fallback_query(topic, scene):
    scene_short = scene[:250]
    en = f"{topic[:70]} {scene_short[:120]} historical documentary"
    return en[:180]


def pexels_search(query):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": key}
    params = {"query": query, "per_page": 30, "orientation": "landscape"}
    try:
        r = session.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = []
        for photo in data.get("photos", []):
            src = photo.get("src", {})
            image = src.get("large2x") or src.get("large") or src.get("original")
            if image:
                results.append(image)
        return results
    except Exception as e:
        print("      Pexels hata:", e)
        return []


def pixabay_search(query):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    url = "https://pixabay.com/api/"
    params = {"key": key, "q": query, "image_type": "photo", "orientation": "horizontal", "per_page": 30, "safesearch": "true"}
    try:
        r = session.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = []
        for hit in data.get("hits", []):
            image = hit.get("largeImageURL") or hit.get("webformatURL")
            if image:
                results.append(image)
        return results
    except Exception as e:
        print("      Pixabay foto hata:", e)
        return []


def wikimedia_search(query):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": 50, "prop": "imageinfo", "iiprop": "url|mime"}
    try:
        r = session.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = []
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            info = page.get("imageinfo", [])
            if not info:
                continue
            item = info[0]
            url2 = item.get("url")
            mime = item.get("mime", "")
            if url2 and mime.startswith("image/"):
                results.append(url2)
        return results
    except Exception as e:
        print("      Wikimedia hata:", e)
        return []


def download_image(url, path):
    try:
        r = session.get(url, timeout=40, stream=True)
        r.raise_for_status()
        ctype = r.headers.get("content-type", "").lower()
        if not ctype.startswith("image/"):
            return False
        with open(path, "wb") as f:
            for chunk in r.iter_content(65536):
                if chunk:
                    f.write(chunk)
        if not os.path.exists(path) or os.path.getsize(path) < 10000:
            if os.path.exists(path):
                os.remove(path)
            return False
        return True
    except Exception:
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            pass
        return False


def file_hash(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                data = f.read(1024 * 1024)
                if not data:
                    break
                h.update(data)
        return h.hexdigest()
    except:
        return None


def try_sources(sources, used_urls, used_hashes, success, visuals_dir):
    for source_name, search, query in sources:
        if not query:
            continue
        print("   🔎", source_name, "-", query[:60])
        urls = search(query)
        for url in urls:
            if not url or url in used_urls:
                continue
            filename = f"visual_{success + 1:03d}.jpg"
            path = os.path.join(visuals_dir, filename)
            ok = download_image(url, path)
            if not ok:
                continue
            h = file_hash(path)
            if h in used_hashes:
                try:
                    os.remove(path)
                except:
                    pass
                continue
            return path, source_name, url, h
    return None, None, None, None


def main():
    print("================================")
    print("🧠 UZUN VİDEO GÖRSEL MOTORU (SADECE RESİM, TOPLU AKILLI SORGU)")
    print("================================")

    topic = get_topic()
    narration = get_narration_text()
    scenes = chunk_into_scenes(narration)

    print("Konu:", topic)
    print("Sahne sayısı:", len(scenes))
    print()

    for file in os.listdir(VISUALS):
        path = os.path.join(VISUALS, file)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except:
                pass

    print("🧠 Tüm sahneler için akıllı sorgular TEK istekte alınıyor...")
    smart_queries = generate_visual_queries_batch(scenes, topic)
    print("✅ Akıllı sorgu üretildi:", sum(1 for q in smart_queries if q), "/", len(scenes))
    print()

    manifest = []
    used_urls, used_hashes = load_used_visuals()
    success = 0
    last_good_path = None

    for i, scene in enumerate(scenes, 1):
        print(f"[{i}/{len(scenes)}]")
        print("🎬 SAHNE:", scene[:100])

        smart_query = smart_queries[i - 1]
        fallback_query = make_fallback_query(topic, scene)

        if smart_query:
            print("   🧠 Akıllı sorgu:", smart_query)

        sources = []

        if smart_query:
            sources.append(("Pexels Foto (akıllı sorgu)", pexels_search, smart_query))
            sources.append(("Pixabay Foto (akıllı sorgu)", pixabay_search, smart_query))
            sources.append(("Wikimedia Foto (akıllı sorgu)", wikimedia_search, smart_query))

        sources.append(("Pexels Foto (genel)", pexels_search, fallback_query))
        sources.append(("Pixabay Foto (genel)", pixabay_search, fallback_query))
        sources.append(("Wikimedia Foto (genel)", wikimedia_search, fallback_query))

        selected, selected_source, url, h = try_sources(sources, used_urls, used_hashes, success, VISUALS)

        if not selected:
            generic_sources = []
            for q in GENERIC_FALLBACK_QUERIES_EN:
                generic_sources.append(("Pexels Foto (genel havuz)", pexels_search, q))
                generic_sources.append(("Pixabay Foto (genel havuz)", pixabay_search, q))
            selected, selected_source, url, h = try_sources(generic_sources, used_urls, used_hashes, success, VISUALS)

        if not selected and last_good_path:
            selected = last_good_path
            selected_source = "Tekrar kullanılan sahne (hiçbir kaynak bulunamadı)"
            print("   ♻️ Hiçbir yeni içerik bulunamadı, bir önceki sahne kullanılıyor.")
        elif selected:
            used_urls.add(url)
            if h:
                used_hashes.add(h)
            success += 1
            last_good_path = selected

        manifest.append({
            "scene": i,
            "scene_text": scene[:300],
            "smart_query": smart_query,
            "file": selected,
            "type": "image",
            "source": selected_source or "YOK"
        })

        if selected:
            print(f"   ✅ [image] {selected_source}")
        else:
            print("   ⚠️ Hiç içerik bulunamadı.")

        print()
        time.sleep(0.2)

    fallback = None
    for item in manifest:
        if item["file"]:
            fallback = item["file"]
            break

    for item in manifest:
        if not item["file"] and fallback:
            item["file"] = fallback
            item["type"] = "image"
            item["source"] = "Geriye doğru doldurulan sahne"

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    save_used_visuals(used_urls, used_hashes)

    print("================================")
    print("✅ GÖRSEL ARAMA BİTTİ")
    print("================================")
    print(f"Benzersiz içerik: {success} / {len(scenes)}")
    print("Manifest:", MANIFEST)


if __name__ == "__main__":
    main()
