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
session.headers.update({
    "User-Agent": "YTBilgiUzunShorts/1.0"
})

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
        json.dump(
            {"urls": urls_list, "hashes": hashes_list},
            f,
            ensure_ascii=False,
            indent=2
        )


def get_topic():
    if os.path.exists(TOPIC_FILE):
        with open(TOPIC_FILE, encoding="utf-8") as f:
            return f.read().strip()
    return ""


def get_scenes():
    # Ses motorunun (voiceover.py) ürettiği GERÇEK cümle listesini birebir
    # kullanıyoruz, böylece görsel ile ses arasında asla sahne uyuşmazlığı olmaz.
    if not os.path.exists(DURATIONS_FILE):
        raise FileNotFoundError(
            "shorts_scene_durations.json bulunamadı. "
            "Önce voiceover.py çalıştırılmalı."
        )

    with open(DURATIONS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    scenes = [item["text"] for item in data]

    return scenes


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
                timeout=30
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


def generate_visual_query(scene, topic):
    """
    Cümlenin ham/kelimesi kelimesine çevirisi yerine, Gemini'den bu cümlenin
    GÖRSEL OLARAK neyi somut şekilde gösterebileceğini kısa İngilizce anahtar
    kelimeyle isteriz. Böylece "Dünya Titanik'i ararken biz nükleer füzelerin
    peşindeydik" gibi bir cümle, alakasız bir stok fotoğraf yerine gerçekten
    "nuclear submarine cold war" gibi somut bir sorguya dönüşür.
    """
    prompt = f"""
Konu: {topic}
Cümle (Türkçe): {scene}

Bu cümlenin anlattığı olayı/nesneyi/yeri stok fotoğraf sitesinde
aratmak için 3-6 kelimelik SOMUT, GÖRSEL OLARAK ARANABİLİR bir
İngilizce arama sorgusu yaz.

KURALLAR:
- Soyut kavram yazma (örn. "mystery", "secret" gibi tek başına
  soyut kelimeler kullanma).
- Cümlede geçen somut özel isim, nesne, yer, olay varsa onu
  kullan (örn. "Titanic wreck submarine", "nuclear missile
  cold war submarine", "ancient Egyptian artifact").
- Sadece sorguyu yaz, başka hiçbir açıklama ekleme.
- Tırnak işareti kullanma.
"""

    raw = call_gemini_with_retry(prompt)

    if not raw:
        return None

    query = raw.strip().strip('"').strip()
    query = " ".join(query.split())

    if not query or len(query) < 3:
        return None

    return query[:180]


def make_queries(scene, topic):
    scene_short = scene[:200]

    tr = f"{scene_short[:100]} haber görsel"
    en = f"{scene_short[:120]} news photo"
    topic_en = f"{topic[:100]} history photo" if topic else ""

    return tr[:180], en[:180], topic_en[:180]


def pexels_search(query):
    key = os.environ.get("PEXELS_API_KEY")

    if not key:
        print("      Pexels API key yok.")
        return []

    url = "https://api.pexels.com/v1/search"

    headers = {"Authorization": key}

    params = {
        "query": query,
        "per_page": 30,
        "orientation": "portrait"
    }

    try:
        r = session.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        results = []

        for photo in data.get("photos", []):
            src = photo.get("src", {})

            image = (
                src.get("portrait")
                or src.get("large2x")
                or src.get("large")
                or src.get("original")
            )

            if image:
                results.append(image)

        return results

    except Exception as e:
        print("      Pexels hata:", e)
        return []


def wikimedia_search(query):
    url = "https://commons.wikimedia.org/w/api.php"

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 50,
        "prop": "imageinfo",
        "iiprop": "url|mime"
    }

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

        if not os.path.exists(path):
            return False

        if os.path.getsize(path) < 10000:
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


def image_hash(path):
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

            filename = f"shorts_visual_{success + 1:03d}.jpg"
            path = os.path.join(visuals_dir, filename)

            if not download_image(url, path):
                continue

            h = image_hash(path)

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
    print("🧠 SHORTS GÖRSEL MOTORU (HER CÜMLE FARKLI GÖRSEL)")
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

    manifest = []

    # Geçmiş run'lardan gelen kalıcı liste + bu run'a özel liste birleşiyor
    used_urls, used_hashes = load_used_visuals()

    success = 0
    last_good_path = None

    for i, scene in enumerate(scenes, 1):

        tr, en_fallback, topic_en = make_queries(scene, topic)

        print(f"[{i}/{len(scenes)}]")
        print("🎬 CÜMLE:", scene[:100])

        # Öncelik: Gemini'den gelen somut, akıllı görsel sorgusu
        smart_query = generate_visual_query(scene, topic)

        if smart_query:
            print("   🧠 Akıllı sorgu:", smart_query)

        # 1. Öncelik: akıllı sorgu (varsa), yoksa ham cümle çevirisi
        sources = []

        if smart_query:
            sources.append(("Pexels (akıllı sorgu)", pexels_search, smart_query))
            sources.append(("Wikimedia (akıllı sorgu)", wikimedia_search, smart_query))

        sources.append(("Pexels (cümle)", pexels_search, en_fallback))
        sources.append(("Wikimedia (cümle EN)", wikimedia_search, en_fallback))
        sources.append(("Wikimedia (cümle TR)", wikimedia_search, tr))

        selected, selected_source, url, h = try_sources(
            sources, used_urls, used_hashes, success, VISUALS
        )

        # 2. Bulunamazsa: konunun genel haliyle arama
        if not selected and topic_en:
            sources2 = [
                ("Pexels (konu geneli)", pexels_search, topic_en),
                ("Wikimedia (konu geneli)", wikimedia_search, topic_en),
            ]
            selected, selected_source, url, h = try_sources(
                sources2, used_urls, used_hashes, success, VISUALS
            )

        # 3. Hâlâ bulunamazsa: rastgele genel görsel havuzundan dene
        if not selected:
            generic_sources = [
                ("Pexels (genel havuz)", pexels_search, q)
                for q in GENERIC_FALLBACK_QUERIES_EN
            ]
            selected, selected_source, url, h = try_sources(
                generic_sources, used_urls, used_hashes, success, VISUALS
            )

        # 4. Son çare: bir önceki görseli tekrar kullan (nadiren olmalı)
        if not selected and last_good_path:
            selected = last_good_path
            selected_source = "Tekrar kullanılan görsel (hiçbir kaynak bulunamadı)"
            print("   ♻️ Hiçbir yeni görsel bulunamadı, bir önceki görsel kullanılıyor.")
        elif selected:
            used_urls.add(url)
            if h:
                used_hashes.add(h)
            success += 1
            last_good_path = selected

        manifest.append({
            "scene": i,
            "scene_text": scene,
            "smart_query": smart_query,
            "query_tr": tr,
            "query_en": en_fallback,
            "file": selected,
            "source": selected_source or "YOK"
        })

        if selected:
            print(f"   ✅ {selected_source}")
        else:
            print("   ⚠️ Hiç görsel bulunamadı.")

        print()
        time.sleep(0.2)

    # İlk sahne(ler)de hiç görsel bulunamadıysa, sonradan bulunan ilk görselle geriye doldur
    fallback = None
    for item in manifest:
        if item["file"]:
            fallback = item["file"]
            break

    for item in manifest:
        if not item["file"] and fallback:
            item["file"] = fallback
            item["source"] = "Geriye doğru doldurulan görsel"

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Kalıcı görsel geçmişini bir sonraki run için repo'ya kaydet
    save_used_visuals(used_urls, used_hashes)

    print("================================")
    print("✅ SHORTS GÖRSEL ARAMA BİTTİ")
    print("================================")
    print(f"Benzersiz görsel: {success} / {len(scenes)}")
    print(f"Toplam manifest kaydı: {len(manifest)} (sahne sayısıyla birebir aynı)")
    print(f"Kalıcı görsel geçmişi: {len(used_urls)} url / {len(used_hashes)} hash")
    print("Manifest:", MANIFEST)


if __name__ == "__main__":
    main()
