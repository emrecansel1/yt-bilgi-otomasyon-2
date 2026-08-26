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

os.makedirs(VISUALS, exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": "YTBilgiUzunShorts/1.0"
})


def get_scenes():
    # ARTIK KENDİ CÜMLE BÖLMEMİZİ YAPMIYORUZ.
    # voiceover.py'nin seslendirdiği GERÇEK cümle listesini birebir kullanıyoruz,
    # böylece görsel ve ses arasında asla sahne uyuşmazlığı olmaz.
    if not os.path.exists(DURATIONS_FILE):
        raise FileNotFoundError(
            "shorts_scene_durations.json bulunamadı. "
            "Önce voiceover.py çalıştırılmalı."
        )

    with open(DURATIONS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    scenes = [item["text"] for item in data]

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
    print("🧠 SHORTS GÖRSEL MOTORU (SES İLE BİREBİR AYNI SAHNELER)")
    print("================================")

    scenes = get_scenes()

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
    used_urls = set()
    used_hashes = set()
    success = 0
    last_good_path = None

    for i, scene in enumerate(scenes, 1):

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

        if not selected and last_good_path:
            selected = last_good_path
            selected_source = "Tekrar kullanılan görsel (yeni bulunamadı)"
            print("   ♻️ Yeni görsel bulunamadı, bir önceki görsel tekrar kullanılıyor.")

        # HER SAHNE İÇİN MUTLAKA BİR KAYIT OLUŞTURULUR (senkron garantisi)
        manifest.append({
            "scene": i,
            "scene_text": scene,
            "query_tr": tr,
            "query_en": en,
            "file": selected,
            "source": selected_source or "YOK"
        })

        if selected:
            if selected != last_good_path:
                success += 1
            last_good_path = selected
            print(f"   ✅ {selected_source}")
        else:
            print("   ⚠️ Hiç görsel bulunamadı (ilk sahne olabilir).")

        print()
        time.sleep(0.2)

    # Manifest'te dosyası olmayan (ilk sahnede hiç görsel bulunamadıysa) kayıtları
    # bir sonraki bulunan görselle geriye doğru doldur.
    fallback = None
    for item in reversed(manifest):
        if item["file"]:
            fallback = item["file"]
            break

    for item in manifest:
        if not item["file"] and fallback:
            item["file"] = fallback
            item["source"] = "Geriye doğru doldurulan görsel"

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("================================")
    print("✅ SHORTS GÖRSEL ARAMA BİTTİ")
    print("================================")
    print(f"Başarılı (benzersiz): {success} / {len(scenes)}")
    print(f"Toplam manifest kaydı: {len(manifest)} (sahne sayısıyla birebir aynı)")
    print("Manifest:", MANIFEST)


if __name__ == "__main__":
    main()
