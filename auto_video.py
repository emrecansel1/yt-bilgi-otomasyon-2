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

CONTENT = os.path.join(OUT, "current_content.txt")
TOPIC_FILE = os.path.join(OUT, "current_topic.txt")
TOPIC_HISTORY_FILE = os.path.join(REPO_BASE, "video_topic_history.json")

VOICE = os.path.join(OUT, "current_voice.wav")
VIDEO_NO_AUDIO = os.path.join(OUT, "current_video_no_audio.mp4")
FINAL = os.path.join(OUT, "current_final.mp4")
THUMBNAIL = os.path.join(OUT, "current_thumbnail.jpg")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

MAX_HISTORY = 30

# Uzun video günde tek sefer, TR saatiyle bu saatte üretilsin.
HEDEF_SAAT = 17


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
    if len(topic) < 8 or len(topic) > 220:
        return False
    if not re.search(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}", topic):
        return False
    if len(topic.split()) < 2:
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
                      f"{delay} sn bekleyip tekrar denenecek ({attempt}/{max_retries})...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue

            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

        except requests.exceptions.RequestException as e:
            print(f"   ⚠️ Gemini isteği hatası: {e}, "
                  f"{delay} sn bekleyip tekrar denenecek ({attempt}/{max_retries})...")
            time.sleep(delay)
            delay = min(delay * 2, 60)

    raise RuntimeError("Gemini API'ye ulaşılamadı (tüm denemeler başarısız).")


def generate_topic(history):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY bulunamadı.")

    avoid_list = "\n".join(f"- {t}" for t in history) if history else "(henüz yok)"

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe bilgi/tarih/bilim YouTube
kanalı için 1 SAATLİK belgesel formatında uzun video konusu bulan
bir editörsün.

ÇOK ÖNEMLİ:
Bu bir Shorts konusu DEĞİL. Seçtiğin konu, en az 45-60 dakikalık
zengin, derinlemesine bir belgesel anlatımını doldurabilecek kadar
GENİŞ ve DERİN olmalı. Tek bir küçük ilginç bilgi veya kısa bir
olay YETERSİZDİR.

İyi örnekler (kapsam olarak):
- Bir tarihi kişinin tüm hayatı ve mirası (örn. bir bilim insanı,
  kaşif, hükümdar - diktatör/savaş suçlusu olmayan).
- Bir antik uygarlığın yükselişi ve çöküşü.
- Büyük bir tarihi olayın veya dönemin bütün boyutlarıyla anlatımı.
- Bir bilim dalının veya büyük keşfin baştan sona hikâyesi.
- Çözülmemiş büyük bir gizemin tüm açılardan incelenmesi.

KESİNLİKLE ŞU DAHA ÖNCE KULLANILAN KONULARI TEKRAR ÖNERME
(bunlara çok benzer/aynı konuları da önerme):
{avoid_list}

KURALLAR:
- Siyasi propaganda, savaş suçluları, diktatörler, hakaret veya
  kışkırtıcı içerik ÖNERME.
- Sadece gerçek, doğrulanabilir bir konu olsun. Uydurma, anlamsız
  veya saçma bir şey ÜRETME.
- Konu tek cümle/başlık halinde, kısa ve net olsun.
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

    result = subprocess.run(cmd, text=True, capture_output=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        raise SystemExit(f"❌ HATA: {name} (exit code {result.returncode})")


def run_optional(cmd, name):
    """run() ile aynı, ama başarısız olursa süreci durdurmaz — sadece uyarır."""
    print()
    print("=" * 40)
    print(name)
    print("=" * 40)

    try:
        result = subprocess.run(cmd, text=True, capture_output=True)

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:
            print(f"⚠️ {name} başarısız oldu (exit code {result.returncode}), devam ediliyor...")
            return False

        return True

    except Exception as e:
        print(f"⚠️ {name} çalıştırılamadı: {e}")
        return False


def main():

    tetikleyici = os.environ.get("GITHUB_EVENT_NAME", "")
    simdi_saat = datetime.now().hour

    if tetikleyici != "workflow_dispatch" and simdi_saat != HEDEF_SAAT:
        print(f"⏭️ Saat {simdi_saat}:00, hedef saat {HEDEF_SAAT}:00 değil, "
              f"bu run atlanıyor.")
        return

    if tetikleyici == "workflow_dispatch":
        print("🖐️ Elle tetiklendi, saat filtresi atlanıyor.")

    os.makedirs(OUT, exist_ok=True)

    print("================================")
    print("🤖 TAM OTOMATİK UZUN VİDEO SİSTEMİ (1 SAATLİK BELGESEL)")
    print("================================")

    print()
    print("🧠 0/7 KONU BULUNUYOR (YAPAY ZEKA)...")

    history = load_history()
    topic = None

    for attempt in range(4):
        try:
            candidate = generate_topic(history)

            if candidate and candidate not in history and is_valid_topic(candidate):
                topic = candidate
                break

            print(f"   ⚠️ Geçersiz/tekrar konu geldi ({candidate!r}), yeniden deneniyor...")

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
    print("🧠 1/7 İÇERİK OLUŞTURULUYOR (BÖLÜMLÜ BELGESEL SENARYOSU)...")

    run(
        [sys.executable, "generate_content.py", topic],
        "İÇERİK MOTORU"
    )

    if not os.path.exists(CONTENT):
        raise SystemExit("❌ current_content.txt oluşmadı.")

    print()
    print("🎙️ 2/7 SES OLUŞTURULUYOR...")

    run(
        [sys.executable, "voiceover.py", CONTENT, VOICE],
        "SES MOTORU"
    )

    if not os.path.exists(VOICE):
        raise SystemExit("❌ current_voice.wav oluşmadı.")

    print()
    print("🖼️ 3/7 GÖRSELLER/VİDEOLAR BULUNUYOR...")

    run(
        [sys.executable, "get_visuals.py"],
        "GÖRSEL MOTORU"
    )

    MANIFEST = os.path.join(OUT, "visual_manifest.json")

    if not os.path.exists(MANIFEST):
        raise SystemExit("❌ visual_manifest.json oluşmadı.")

    with open(MANIFEST, encoding="utf-8") as f:
        data = json.load(f)

    valid = [x for x in data if x.get("file") and os.path.exists(x["file"])]

    print()
    print("✅ Kullanılabilir sahne:", len(valid))

    if not valid:
        raise SystemExit("❌ Hiç kullanılabilir görsel/video bulunamadı.")

    print()
    print("🎬 4/7 GÖRSELLİ/VİDEOLU FİNAL VİDEO OLUŞTURULUYOR...")

    temp_script = os.path.join(BASE, "_auto_visual.py")

    with open("unique_visual_video.py", encoding="utf-8") as f:
        code = f.read()

    code = code.replace(
        'VOICE = os.path.join(OUT, "einstein_voice.wav")',
        'VOICE = os.path.join(OUT, "current_voice.wav")'
    )

    code = code.replace(
        'VIDEO = os.path.join(OUT, "einstein_unique.mp4")',
        'VIDEO = os.path.join(OUT, "current_video_no_audio.mp4")'
    )

    with open(temp_script, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        run([sys.executable, temp_script], "GÖRSELLİ/VİDEOLU VİDEO MOTORU")
    finally:
        if os.path.exists(temp_script):
            os.remove(temp_script)

    if not os.path.exists(VIDEO_NO_AUDIO):
        raise SystemExit("❌ Görsel/video birleşimi oluşmadı.")

    print()
    print("🔊 5/7 SES VİDEOYA EKLENİYOR...")

    run(
        [
            "ffmpeg", "-y",
            "-i", VIDEO_NO_AUDIO,
            "-i", VOICE,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            FINAL
        ],
        "FİNAL VİDEO"
    )

    if not os.path.exists(FINAL):
        raise SystemExit("❌ Final video oluşmadı.")

    print()
    print("================================")
    print("✅ FINAL VIDEO HAZIR")
    print("================================")
    print("📁", FINAL)
    print("📦 Boyut:", round(os.path.getsize(FINAL) / 1024 / 1024, 2), "MB")
    print("================================")

    print()
    print("🖼️ 6/7 THUMBNAIL OLUŞTURULUYOR...")

    thumb_ok = run_optional(
        [sys.executable, "thumbnail_generator.py"],
        "THUMBNAIL MOTORU"
    )

    if thumb_ok and os.path.exists(THUMBNAIL):
        print("✅ Thumbnail hazır:", THUMBNAIL)
    else:
        print("⚠️ Thumbnail oluşturulamadı, video thumbnail'siz devam edecek.")

    print()
    print("📤 7/7 YOUTUBE'A YÜKLENİYOR...")

    run(
        [sys.executable, "upload_youtube.py"],
        "YOUTUBE YÜKLEYİCİ"
    )

    if os.path.exists(VIDEO_NO_AUDIO):
        os.remove(VIDEO_NO_AUDIO)

    print()
    print("================================")
    print("🎉 OTOMATİK VİDEO HAZIR")
    print("================================")
    print("🎯 Konu:", topic)
    print("📁 Video:", FINAL)
    print("🖼️ Thumbnail:", THUMBNAIL if os.path.exists(THUMBNAIL) else "yok")
    print("💾 Boyut:", round(os.path.getsize(FINAL) / 1024 / 1024, 2), "MB")
    print("================================")


if __name__ == "__main__":
    main()
