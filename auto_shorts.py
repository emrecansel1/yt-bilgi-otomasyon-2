import os
import re
import json
import time
import requests
import hashlib

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")
VISUALS = os.path.join(OUT, "shorts_visuals")
CONTENT = os.path.join(OUT, "shorts_script.txt")
MANIFEST = os.path.join(OUT, "shorts_visual_manifest.json")

os.makedirs(VISUALS, exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": "YTBilgiUzunShorts/1.0"
})


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_scenes(text):
    text = clean_text(text)

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    scenes = [
        s.strip()
        for s in sentences
        if len(s.strip()) >= 15
    ]

    return scenes


def make_queries(scene):
    scene_short = scene[:200]

    tr = f"{scene_short[:100]} haber görsel"
    en = f"{scene_short[:120]} news photo"

    return tr[:180], en[:180]


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


def main():
    print("================================")
    print("🧠 SHORTS GÖRSEL MOTORU")
    print("================================")

    with open(CONTENT, "r", encoding="utf-8") as f:
        content = f.read()

    scenes = get_scenes(content)

    print("Cümle sayısı:", len(scenes))
    print()

    for file in os.listdir(VISUALS):
        path = os.path.join(VISUALS, file)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except:
                pass

    manifest = []
    used_urls = set()
    used_hashes = set()
    success = 0
    last_good_path = None

    for i, scene in enumerate(scenes, 1):

        if len(scene) < 15:
            continue

        tr, en = make_queries(scene)

        print(f"[{i}/{len(scenes)}]")
        print("🎬 CÜMLE:", scene[:100])

        sources = [
            ("Pexels", pexels_search, en),
            ("Wikimedia Commons", wikimedia_search, en),
            ("Wikimedia Commons TR", wikimedia_search, tr),
        ]

        selected = None
        selected_source = None

        for source_name, search, query in sources:
            print("   🔎", source_name)

            urls = search(query)

            for url in urls:
                if not url or url in used_urls:
                    continue

                filename = f"shorts_visual_{success + 1:03d}.jpg"
                path = os.path.join(VISUALS, filename)

                if not download_image(url, path):
                    continue

                h = image_hash(path)

                if h in used_hashes:
                    try:
                        os.remove(path)
                    except:
                        pass
                    continue

                used_urls.add(url)

                if h:
                    used_hashes.add(h)

                selected = path
                selected_source = source_name
                break

            if selected:
                break

        # --- HİÇ GÖRSEL BULUNAMAZSA: cümleyi atlama, önceki görseli tekrar kullan ---
        if not selected and last_good_path:
            selected = last_good_path
            selected_source = "Tekrar kullanılan görsel (yeni bulunamadı)"
            print("   ♻️ Yeni görsel bulunamadı, bir önceki görsel tekrar kullanılıyor.")

        if selected:
            manifest.append({
                "scene": i,
                "scene_text": scene,
                "query_tr": tr,
                "query_en": en,
                "file": selected,
                "source": selected_source
            })

            if selected != last_good_path:
                success += 1

            last_good_path = selected

            print(f"   ✅ {selected_source}")

        else:
            # İlk cümle için bile hiç görsel bulunamadıysa, gerçekten atlanacak
            # tek durum budur (elimizde tekrar kullanılacak önceki görsel yok).
            print("   ⚠️ Görsel bulunamadı ve tekrar kullanılacak önceki görsel yok.")

        print()
        time.sleep(0.2)

    # --- GÜVENLİK KONTROLÜ: manifest uzunluğu cümle sayısıyla eşleşmeli ---
    if len(manifest) != len(scenes):
        print(f"⚠️ UYARI: manifest ({len(manifest)}) ile cümle sayısı ({len(scenes)}) uyuşmuyor.")
        print("   Bu durum sadece ilk cümlede hiç görsel bulunamazsa oluşur.")

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("================================")
    print("✅ SHORTS GÖRSEL ARAMA BİTTİ")
    print("================================")
    print(f"Başarılı (benzersiz): {success} / {len(scenes)}")
    print(f"Toplam manifest kaydı: {len(manifest)}")
    print("Manifest:", MANIFEST)


if __name__ == "__main__":
    main()
