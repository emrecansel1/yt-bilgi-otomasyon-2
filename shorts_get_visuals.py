import os
import json
import time
import requests
import hashlib

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")
VISUALS = os.path.join(OUT, "shorts_visuals")
DURATIONS_FILE = os.path.join(OUT, "shorts_scene_durations.json")
MANIFEST = os.path.join(OUT, "shorts_visual_manifest.json")
TOPIC_FILE = os.path.join(OUT, "shorts_topic.txt")

REPO_BASE = os.path.dirname(os.path.abspath(__file__))
USED_VISUALS_FILE = os.path.join(REPO_BASE, "shorts_used_visuals.json")
MAX_USED = 3000

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

os.makedirs(VISUALS, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "YTBilgiUzunShorts/1.0"})

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
    urls_list = list(used_urls)[-MAX_USED:]
    hashes_list = list(used_hashes)[-MAX_USED:]

    with open(USED_VISUALS_FILE, "w", encoding="utf-8") as f:
        json.dump({"urls": urls_list, "hashes": hashes_list}, f, ensure_ascii=False, indent=2)


def get_topic():
    if os.path.exists(TOPIC_FILE):
        with open(TOPIC_FILE, encoding="utf-8") as f:
            return f.read().strip()
    return ""


def get_scenes():
    if not os.path.exists(DURATIONS_FILE):
        raise FileNotFoundError(
            "shorts_scene_durations.json bulunamadı. Önce voiceover.py çalıştırılmalı."
        )

    with open(DURATIONS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    return [item["text"] for item in data]


def call_gemini_with_retry(prompt, max_retries=3):
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
                timeout=45
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
    """
    Sahne başına ayrı Gemini isteği atmak yerine, TÜM sahneleri TEK
    istekte gönderip hepsinin görsel sorgusunu birlikte alıyoruz.
    """
    numbered = "\n".join(f"{i}: {s[:200]}" for i, s in enumerate(scenes, 1))

    prompt = f"""
Konu: {topic}

Aşağıda numaralandırılmış {len(scenes)} adet Türkçe cümle var
(bir YouTube Shorts videosunun sahneleri). Her sahne için, o
sahnenin anlattığı olayı/nesneyi/yeri stok video/fotoğraf
sitesinde aratmak için 3-6 kelimelik SOMUT, GÖRSEL OLARAK
ARANABİLİR bir İngilizce arama sorgusu yaz.

SAHNELER:
{numbered}

KURALLAR:
- Soyut kavram yazma.
- Cümlede geçen somut özel isim, nesne, yer, olay varsa onu kullan.
- Tırnak işareti kullanma.

ÇIKTI FORMATI (tam olarak bunu kullan, başka hiçbir şey yazma):
1: <sorgu>
2: <sorgu>
...
{len(scenes)}: <sorgu>
"""

    raw = call_gemini_with_retry(prompt, max_retries=3)

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


def make_queries(scene, topic):
    scene_short = scene[:200]
    tr = f"{scene_short[:100]} haber görsel"
    en = f"{scene_short[:120]} news photo"
    topic_en = f"{topic[:100]} history photo" if topic else ""
    return tr[:180], en[:180], topic_en[:180]


def pexels_video_search(query):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": key}
    params = {"query": query, "per_page": 15, "orientation": "portrait"}
    try:
        r = session.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = []
        for video in data.get("videos", []):
            files = video.get("video_files", [])
            portrait_files = [f for f in files if (f.get("height") or 0) > (f.get("width") or 0)]
            candidates = portrait_files if portrait_files else files
            candidates = sorted(candidates, key=lambda f: abs((f.get("width") or 0) - 720))
            if candidates:
                link = candidates[0].get("link")
                if link:
                    results.append(link)
        return results
    except Exception as e:
        print("      Pexels video hata:", e)
        return []


def pexels_search(query):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": key}
    params = {"query": query, "per_page": 30, "orientation": "portrait"}
    try:
        r = session.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = []
        for photo in data.get("photos", []):
            src = photo.get("src", {})
            image = src.get("portrait") or src.get("large2x") or src.get("large") or src.get("original")
            if image:
                results.append(image)
        return results
    except Exception as e:
        print("      Pexels hata:", e)
        return []


def pixabay_video_search(query):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    url = "https://pixabay.com/api/videos/"
    params = {"key": key, "q": query, "per_page": 20, "safesearch": "true"}
    try:
        r = session.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = []
        for hit in data.get("hits", []):
            videos = hit.get("videos", {})
            candidate = videos.get("medium") or videos.get("small") or videos.get("large") or videos.get("tiny")
            if candidate and candidate.get("url"):
                results.append(candidate["url"])
        return results
    except Exception as e:
        print("      Pixabay video hata:", e)
        return []


def pixabay_search(query):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    url = "https://pixabay.com/api/"
    params = {"key": key, "q": query, "image_type": "photo", "orientation": "vertical", "per_page": 30, "safesearch": "true"}
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


def download_video(url, path):
    try:
        r = session.get(url, timeout=60, stream=True)
        r.raise_for_status()
        ctype = r.headers.get("content-type", "").lower()
        if not ctype.startswith("video/"):
            return False
        with open(path, "wb") as f:
            for chunk in r.iter_content(65536):
                if chunk:
                    f.write(chunk)
        if not os.path.exists(path) or os.path.getsize(path) < 200000:
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
    for source_name, search, query, kind in sources:
        if not query:
            continue
        print("   🔎", source_name, "-", query[:60])
        urls = search(query)
        for url in urls:
            if not url or url in used_urls:
                continue
            ext = "mp4" if kind == "video" else "jpg"
            filename = f"shorts_visual_{success + 1:03d}.{ext}"
            path = os.path.join(visuals_dir, filename)
            ok = download_video(url, path) if kind == "video" else download_image(url, path)
            if not ok:
                continue
            h = file_hash(path)
            if h in used_hashes:
                try:
                    os.remove(path)
                except:
                    pass
                continue
            return path, source_name, url, h, kind
    return None, None, None, None, None


def main():
    print("================================")
    print("🧠 SHORTS GÖRSEL/VİDEO MOTORU (TOPLU AKILLI SORGU)")
    print("================================")

    topic = get_topic()
    scenes = get_scenes()

    print("Konu:", topic)
    print("Cümle sayısı (ses ile birebir aynı):", len(scenes))
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
    last_good_kind = "image"

    for i, scene in enumerate(scenes, 1):
        tr, en_fallback, topic_en = make_queries(scene, topic)
        smart_query = smart_queries[i - 1]

        print(f"[{i}/{len(scenes)}]")
        print("🎬 CÜMLE:", scene[:100])

        if smart_query:
            print("   🧠 Akıllı sorgu:", smart_query)

        sources = []

        if smart_query:
            sources.append(("Pexels Video (akıllı sorgu)", pexels_video_search, smart_query, "video"))
            sources.append(("Pixabay Video (akıllı sorgu)", pixabay_video_search, smart_query, "video"))

        sources.append(("Pexels Video (cümle)", pexels_video_search, en_fallback, "video"))
        sources.append(("Pixabay Video (cümle)", pixabay_video_search, en_fallback, "video"))

        if smart_query:
            sources.append(("Pexels Foto (akıllı sorgu)", pexels_search, smart_query, "image"))
            sources.append(("Pixabay Foto (akıllı sorgu)", pixabay_search, smart_query, "image"))
            sources.append(("Wikimedia Foto (akıllı sorgu)", wikimedia_search, smart_query, "image"))

        sources.append(("Pexels Foto (cümle)", pexels_search, en_fallback, "image"))
        sources.append(("Pixabay Foto (cümle)", pixabay_search, en_fallback, "image"))
        sources.append(("Wikimedia Foto (cümle EN)", wikimedia_search, en_fallback, "image"))
        sources.append(("Wikimedia Foto (cümle TR)", wikimedia_search, tr, "image"))

        selected, selected_source, url, h, kind = try_sources(sources, used_urls, used_hashes, success, VISUALS)

        if not selected and topic_en:
            sources2 = [
                ("Pexels Video (konu geneli)", pexels_video_search, topic_en, "video"),
                ("Pixabay Video (konu geneli)", pixabay_video_search, topic_en, "video"),
                ("Pexels Foto (konu geneli)", pexels_search, topic_en, "image"),
                ("Pixabay Foto (konu geneli)", pixabay_search, topic_en, "image"),
                ("Wikimedia Foto (konu geneli)", wikimedia_search, topic_en, "image"),
            ]
            selected, selected_source, url, h, kind = try_sources(sources2, used_urls, used_hashes, success, VISUALS)

        if not selected:
            generic_sources = []
            for q in GENERIC_FALLBACK_QUERIES_EN:
                generic_sources.append(("Pexels Foto (genel havuz)", pexels_search, q, "image"))
                generic_sources.append(("Pixabay Foto (genel havuz)", pixabay_search, q, "image"))
            selected, selected_source, url, h, kind = try_sources(generic_sources, used_urls, used_hashes, success, VISUALS)

        if not selected and last_good_path:
            selected = last_good_path
            kind = last_good_kind
            selected_source = "Tekrar kullanılan sahne (hiçbir kaynak bulunamadı)"
            print("   ♻️ Hiçbir yeni içerik bulunamadı, bir önceki sahne kullanılıyor.")
        elif selected:
            used_urls.add(url)
            if h:
                used_hashes.add(h)
            success += 1
            last_good_path = selected
            last_good_kind = kind

        manifest.append({
            "scene": i,
            "scene_text": scene,
            "smart_query": smart_query,
            "query_tr": tr,
            "query_en": en_fallback,
            "file": selected,
            "type": kind or "image",
            "source": selected_source or "YOK"
        })

        if selected:
            print(f"   ✅ [{kind}] {selected_source}")
        else:
            print("   ⚠️ Hiç içerik bulunamadı.")

        print()
        time.sleep(0.2)

    fallback = None
    fallback_kind = "image"
    for item in manifest:
        if item["file"]:
            fallback = item["file"]
            fallback_kind = item["type"]
            break

    for item in manifest:
        if not item["file"] and fallback:
            item["file"] = fallback
            item["type"] = fallback_kind
            item["source"] = "Geriye doğru doldurulan sahne"

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    save_used_visuals(used_urls, used_hashes)

    video_count = sum(1 for m in manifest if m["type"] == "video")

    print("================================")
    print("✅ SHORTS GÖRSEL/VİDEO ARAMA BİTTİ")
    print("================================")
    print(f"Benzersiz içerik: {success} / {len(scenes)}")
    print(f"Video sahne: {video_count} / {len(manifest)}")
    print(f"Kalıcı geçmiş: {len(used_urls)} url / {len(used_hashes)} hash")
    print("Manifest:", MANIFEST)


if __name__ == "__main__":
    main()
