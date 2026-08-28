import os
import subprocess
import sys
import json
import re
import time
import requests
from datetime import datetime

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

REPO_BASE = os.path.dirname(os.path.abspath(__file__))

CONTENT_JSON = os.path.join(REPO_BASE, "shorts_content.json")
TOPIC_FILE = os.path.join(OUT, "shorts_topic.txt")
TOPIC_HISTORY_FILE = os.path.join(REPO_BASE, "shorts_topic_history.json")

SCRIPT_TEXT = os.path.join(OUT, "shorts_script.txt")
VOICE = os.path.join(OUT, "shorts_voice.wav")
VIDEO_NO_AUDIO = os.path.join(OUT, "shorts_video_no_audio.mp4")
FINAL = os.path.join(OUT, "shorts_final.mp4")
META_FILE = os.path.join(OUT, "shorts_meta.json")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

MAX_HISTORY = 60

# Shorts'un günde kaç kez üretileceğini belirleyen hedef saatler (Europe/Istanbul)
HEDEF_SAATLER = {9, 12, 15, 18, 21}


def load_history():
    if os.path.exists(TOPIC_HISTORY_FILE):
        try:
            with open(TOPIC_HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history):
    history = history[-MAX_HISTORY:]
    with open(TOPIC_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def is_valid_topic(topic):
    if not topic:
        return False

    if len(topic) < 8 or len(topic) > 200:
        return False

    # Saçma/anlamsız çıktı belirtileri: çok fazla rakam, tuhaf tekrar, boşluk yokluğu
    if not re.search(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}", topic):
        return False

    word_count = len(topic.split())
    if word_count < 2:
        return False

    return True


def call_gemini_with_retry(prompt, max_retries=5):
    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-3.6-flash:generateContent"
    )

    delay = 5

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                url,
                params={"key": GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=60
            )

            if response.status_code in (429, 503):
                print(f"   ⏳ Gemini meşgul (HTTP {response.status_code}), "
                      f"{delay} sn bekleyip tekrar denenecek "
                      f"({attempt}/{max_retries})...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue

            response.raise_for_status()

            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

        except requests.exceptions.RequestException as e:
            print(f"   ⚠️ Gemini isteği hatası: {e}, "
                  f"{delay} sn bekleyip tekrar denenecek "
                  f"({attempt}/{max_retries})...")
            time.sleep(delay)
            delay = min(delay * 2, 60)

    raise RuntimeError("Gemini API'ye ulaşılamadı (tüm denemeler başarısız).")


def generate_topic(history):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY bulunamadı.")

    avoid_list = "\n".join(f"- {t}" for t in history) if history else "(henüz yok)"

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe bilgi/tarih/bilim YouTube
kanalı için Shorts konu bulan bir editörsün.

GÖREV:
İzleyicinin "vay be, bunu bilmiyordum" diyeceği, çarpıcı, meraklandırıcı,
GERÇEK ve DOĞRULANABİLİR TEK BİR konu öner. Konu; tarih, bilim, icatlar,
keşifler, gizemli olaylar, insan vücudu, uzay, hayvanlar, eski
uygarlıklar, teknoloji tarihi gibi alanlardan olabilir.

KESİNLİKLE ŞU DAHA ÖNCE KULLANILAN KONULARI TEKRAR ÖNERME
(bunlara çok benzer/aynı konuları da önerme):
{avoid_list}

KURALLAR:
- Siyasi propaganda, savaş suçluları, diktatörler, hakaret veya
  kışkırtıcı içerik ÖNERME.
- Sadece gerçek, doğrulanabilir bir olay/bilgi olsun. Uydurma,
  anlamsız veya saçma bir şey ÜRETME.
- Konu tek cümle/başlık halinde, kısa ve net olsun (en az 3-4 kelime).
- Sadece konuyu yaz, başka hiçbir açıklama, numaralandırma veya
  yorum ekleme.

ÇIKTI:
Sadece konunun kendisini yaz, tek satır.
"""

    raw = call_gemini_with_retry(prompt)

    topic = re.sub(r"^[\-\*\d\.\)\s]+", "", raw.strip())
    topic = re.sub(r"\s+", " ", topic).strip()
    topic = topic.strip('"').strip()

    return topic


def run(cmd, name):
    print()
    print("=" * 40)
    print(name)
    print("=" * 40)

    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise SystemExit(f"❌ HATA: {name}")


def main():

    simdi_saat = datetime.now().hour
    if simdi_saat not in HEDEF_SAATLER:
        print(f"⏭️ Saat {simdi_saat}:00 hedef saatlerden ({sorted(HEDEF_SAATLER)}) "
              f"biri değil, bu run atlanıyor.")
        return

    os.makedirs(OUT, exist_ok=True)

    print("================================")
    print("🤖 TAM OTOMATİK SHORTS SİSTEMİ")
    print("================================")

    print()
    print("🧠 1/6 SHORTS KONUSU BULUNUYOR (YAPAY ZEKA)...")

    history = load_history()

    topic = None

    for attempt in range(4):
        try:
            candidate = generate_topic(history)

            if candidate and candidate not in history and is_valid_topic(candidate):
                topic = candidate
                break

            print(f"   ⚠️ Geçersiz/tekrar konu geldi ({candidate!r}), "
                  f"yeniden deneniyor...")

        except Exception as e:
            print("   ⚠️ Konu üretim hatası:", e)
            time.sleep(5)

    if not topic:
        raise SystemExit("❌ Yapay zeka geçerli bir konu üretemedi.")

    print("🎯 Seçilen konu:", topic)

    history.append(topic)
    save_history(history)

    with open(TOPIC_FILE, "w", encoding="utf-8") as f:
        f.write(topic)

    print()
    print("✍️ 2/6 SHORTS METNİ YAZILIYOR...")

    run(
        [
            sys.executable,
            os.path.join(REPO_BASE, "shorts_content.py"),
            topic
        ],
        "SHORTS İÇERİK MOTORU"
    )

    if not os.path.exists(CONTENT_JSON):
        raise SystemExit("❌ shorts_content.json oluşmadı.")

    with open(CONTENT_JSON, encoding="utf-8") as f:
        data = json.load(f)

    contents = data.get("contents", [])

    if not contents:
        raise SystemExit("❌ shorts_content.json içinde içerik yok.")

    item = contents[0]

    script_text = item.get("script", "").strip()
    title = item.get("title", "").strip()
    description = item.get("description", "").strip()
    tags = item.get("tags", "").strip()

    if not script_text:
        raise SystemExit("❌ Shorts metni boş.")

    with open(SCRIPT_TEXT, "w", encoding="utf-8") as f:
        f.write(script_text)

    meta = {
        "title": title,
        "description": description,
        "tags": tags
    }

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print()
    print("🎬 Başlık:", title)
    print("📝 Kelime sayısı:", len(script_text.split()))

    print()
    print("🎙️ 3/6 SES OLUŞTURULUYOR...")

    run(
        [
            sys.executable,
            os.path.join(REPO_BASE, "voiceover.py"),
            SCRIPT_TEXT,
            VOICE
        ],
        "SES MOTORU"
    )

    if not os.path.exists(VOICE):
        raise SystemExit("❌ shorts_voice.wav oluşmadı.")

    print()
    print("🖼️ 4/6 GÖRSELLER BULUNUYOR VE VİDEO OLUŞTURULUYOR...")

    run(
        [
            sys.executable,
            os.path.join(REPO_BASE, "shorts_get_visuals.py")
        ],
        "GÖRSEL MOTORU"
    )

    run(
        [
            sys.executable,
            os.path.join(REPO_BASE, "shorts_visual_video.py")
        ],
        "GÖRSELLİ VİDEO MOTORU"
    )

    if not os.path.exists(VIDEO_NO_AUDIO):
        raise SystemExit("❌ shorts_video_no_audio.mp4 oluşmadı.")

    print()
    print("🔊 5/6 SES VİDEOYA EKLENİYOR...")

    run(
        [
            "ffmpeg",
            "-y",
            "-i", VIDEO_NO_AUDIO,
            "-i", VOICE,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            FINAL
        ],
        "FİNAL VİDEO"
    )

    if not os.path.exists(FINAL):
        raise SystemExit("❌ shorts_final.mp4 oluşmadı.")

    print()
    print("📤 6/6 YOUTUBE SHORTS'A YÜKLENİYOR...")

    run(
        [
            sys.executable,
            os.path.join(REPO_BASE, "upload_youtube_shorts.py")
        ],
        "YOUTUBE SHORTS YÜKLEYİCİ"
    )

    if os.path.exists(VIDEO_NO_AUDIO):
        os.remove(VIDEO_NO_AUDIO)

    print()
    print("================================")
    print("🎉 SHORTS VİDEO HAZIR")
    print("================================")
    print("🎯 Konu:", topic)
    print("🎬 Başlık:", title)
    print("📁 Dosya:", FINAL)
    print(
        "💾 Boyut:",
        round(os.path.getsize(FINAL) / 1024 / 1024, 2),
        "MB"
    )
    print("================================")


if __name__ == "__main__":
    main()
