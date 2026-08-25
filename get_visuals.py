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
MANIFEST = os.path.join(OUT, "visual_manifest.json")

os.makedirs(VISUALS, exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": "YTBilgiUzun/6.0"
})


def clean_text(text):
    text = re.sub(r"===.*?===", " ", text)
    text = re.sub(r"\[\s*\d+:\d+\s*-\s*\d+:\d+\s*\]", " ", text)

    text = re.sub(
        r"\([^)]*(ses efekti|geçiş müziği|müzik|ambiyans|efekt)[^)]*\)",
        " ",
        text,
        flags=re.I
    )

    text = re.sub(
        r"^\s*(DIŞ SES|ANLATICI|SES)\s*[:\-]\s*",
        "",
        text,
        flags=re.I
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_topic():

    with open(CONTENT, "r", encoding="utf-8") as f:
        text = f.read()

    lines = [
        clean_text(x)
        for x in text.splitlines()
    ]

    lines = [
        x for x in lines
        if len(x) > 20
    ]

    for line in lines:

        low = line.lower()

        if any(x in low for x in [
            "ses efekti",
            "geçiş müziği",
            "müzik:",
            "ambiyans"
        ]):
            continue

        if len(line) >= 20:
            return line[:150]

    return "tarih bilim"


def get_scenes(text):

    blocks = re.split(
        r"\n\s*\n",
        text
    )

    scenes = []

    for block in blocks:

        block = clean_text(block)

        if len(block) < 50:
            continue

        if block.lower() in [
            "senaryo",
            "giriş",
            "bölüm",
            "sonuç"
        ]:
            continue

        scenes.append(block)

    if len(scenes) < 10:

        sentences = re.split(
            r"(?<=[.!?])\s+",
            clean_text(text)
        )

        scenes = [
            s.strip()
            for s in sentences
            if len(s.strip()) >= 50
        ]

    return scenes


def clean_scene(scene):

    scene = clean_text(scene)

    scene = re.sub(
        r"^(sahne|scene)\s*\d+\s*[:\-]\s*",
        "",
        scene,
        flags=re.I
    )

    return scene.strip()


def make_queries(topic, scene):

    scene = clean_scene(scene)

    scene_short = scene[:350]

    tr = (
        f"{topic[:70]} "
        f"{scene_short[:100]} "
        f"tarih fotoğrafı"
    )

    en = (
        f"{topic[:70]} "
        f"{scene_short[:120]} "
        f"historical photograph"
    )

    return tr[:180], en[:180]


def pexels_search(query):

    key = os.environ.get("PEXELS_API_KEY")

    if not key:
        print("      Pexels API key yok.")
        return []

    url = "https://api.pexels.com/v1/search"

    headers = {
        "Authorization": key
    }

    params = {
        "query": query,
        "per_page": 30,
        "orientation": "landscape"
    }

    try:

        r = session.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        r.raise_for_status()

        data = r.json()

        results = []

        for photo in data.get("photos", []):

            src = photo.get("src", {})

            image = (
                src.get("large2x")
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

        r = session.get(
            url,
            params=params,
            timeout=30
        )

        r.raise_for_status()

        data = r.json()

        results = []

        pages = (
            data
            .get("query", {})
            .get("pages", {})
        )

        for page in pages.values():

            info = page.get(
                "imageinfo",
                []
            )

            if not info:
                continue

            item = info[0]

            url2 = item.get("url")
            mime = item.get("mime", "")

            if (
                url2
                and mime.startswith("image/")
            ):
                results.append(url2)

        return results

    except Exception as e:

        print("      Wikimedia hata:", e)

        return []


def unsplash_search(query):

    url = (
        "https://source.unsplash.com/1600x900/?"
        + requests.utils.quote(query)
    )

    try:

        r = session.get(
            url,
            timeout=30,
            allow_redirects=True
        )

        if (
            r.status_code == 200
            and
            r.headers.get(
                "content-type",
                ""
            ).startswith("image/")
        ):
            return [r.url]

    except Exception:
        pass

    return []


def download_image(url, path):

    try:

        r = session.get(
            url,
            timeout=40,
            stream=True
        )

        r.raise_for_status()

        ctype = r.headers.get(
            "content-type",
            ""
        ).lower()

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


def image_duration(index):

    values = [
        5, 7, 6, 8,
        7, 6, 9, 8
    ]

    return values[
        index % len(values)
    ]


def main():

    print("================================")
    print("🧠 GELİŞMİŞ GÖRSEL MOTORU")
    print("================================")

    with open(
        CONTENT,
        "r",
        encoding="utf-8"
    ) as f:

        content = f.read()

    topic = get_topic()

    scenes = get_scenes(
        content
    )

    print("Konu:", topic)
    print("Sahne sayısı:", len(scenes))
    print()
    print("Kaynak sırası:")
    print("1️⃣ Pexels")
    print("2️⃣ Wikimedia Commons")
    print("3️⃣ Unsplash")
    print("♻️ Aynı görsel tekrar: KAPALI")
    print()

    for file in os.listdir(VISUALS):

        path = os.path.join(
            VISUALS,
            file
        )

        if os.path.isfile(path):

            try:
                os.remove(path)
            except:
                pass

    manifest = []

    used_urls = set()
    used_hashes = set()

    success = 0

    for i, scene in enumerate(
        scenes,
        1
    ):

        scene = clean_scene(scene)

        if (
            len(scene) < 40
            or
            "ses efekti" in scene.lower()
            or
            "geçiş müziği" in scene.lower()
        ):
            continue

        tr, en = make_queries(
            topic,
            scene
        )

        print(
            f"[{i}/{len(scenes)}]"
        )

        print(
            "🎬 SAHNE:",
            scene[:120]
        )

        sources = [
            (
                "Pexels",
                pexels_search,
                en
            ),
            (
                "Wikimedia Commons",
                wikimedia_search,
                en
            ),
            (
                "Wikimedia Commons TR",
                wikimedia_search,
                tr
            ),
            (
                "Unsplash",
                unsplash_search,
                en
            )
        ]

        selected = None
        selected_source = None

        for source_name, search, query in sources:

            print(
                "   🔎",
                source_name
            )

            urls = search(query)

            for url in urls:

                if not url:
                    continue

                if url in used_urls:
                    continue

                filename = (
                    f"visual_{success + 1:03d}.jpg"
                )

                path = os.path.join(
                    VISUALS,
                    filename
                )

                if not download_image(
                    url,
                    path
                ):
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

        if selected:

            duration = image_duration(
                success
            )

            manifest.append({

                "scene": i,

                "scene_text": scene,

                "query_tr": tr,

                "query_en": en,

                "file": selected,

                "duration": duration,

                "source": selected_source

            })

            success += 1

            print(
                f"   ✅ {selected_source} "
                f"| {duration} saniye"
            )

        else:

            print(
                "   ⚠️ Görsel bulunamadı"
            )

        print()

        time.sleep(0.2)

    with open(
        MANIFEST,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            manifest,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("================================")
    print("✅ GÖRSEL ARAMA BİTTİ")
    print("================================")
    print(
        f"Başarılı: {success} / {len(scenes)}"
    )
    print(
        "Manifest:",
        MANIFEST
    )


if __name__ == "__main__":
    main()
