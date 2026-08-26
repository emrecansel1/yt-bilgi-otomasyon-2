import os
import subprocess
import sys
import json
import random

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

REPO_BASE = os.path.dirname(os.path.abspath(__file__))

CONTENT_JSON = os.path.join(REPO_BASE, "shorts_content.json")
TOPIC_FILE = os.path.join(OUT, "shorts_topic.txt")

SCRIPT_TEXT = os.path.join(OUT, "shorts_script.txt")
VOICE = os.path.join(OUT, "shorts_voice.wav")
VIDEO_NO_AUDIO = os.path.join(OUT, "shorts_video_no_audio.mp4")
FINAL = os.path.join(OUT, "shorts_final.mp4")
META_FILE = os.path.join(OUT, "shorts_meta.json")

TOPICS = [
    "Tuval kağıdı neden icat edildi",
    "Nikola Tesla'nın en tuhaf icadı",
    "Thomas Edison'ın başarısız olan icadı",
    "Fransız kaşiflerin unutulmuş keşfi",
    "Yazının icat edilme hikayesi",
    "İlk fotoğraf makinesinin icadı",
    "Antibiyotiğin tesadüfen keşfi",
    "İlk telefonun icat edilme hikayesi",
    "Uçağın icadından önce yapılan garip denemeler",
    "İlk bilgisayarın icat edilme hikayesi",
    "Buharlı makinenin icadı ve etkisi",
    "İlk aşının keşfedilme hikayesi",
    "Elektriğin keşfedilme süreci",
    "İlk otomobilin icadı",
    "Röntgenin tesadüfen keşfi",
    "İlk saatin icat edilme hikayesi",
    "Kağıt paranın icadı",
    "İlk matbaa makinesinin icadı",
    "Dinamitin icadı ve Nobel'in hikayesi",
    "İlk buzdolabının icadı",
]


def run(cmd, name):
    print()
    print("=" * 40)
    print(name)
    print("=" * 40)

    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise SystemExit(f"❌ HATA: {name}")


def main():

    os.makedirs(OUT, exist_ok=True)

    print("================================")
    print("🤖 TAM OTOMATİK SHORTS SİSTEMİ")
    print("================================")

    topic = random.choice(TOPICS)

    print()
    print("🧠 1/6 SHORTS KONUSU SEÇİLİYOR...")
    print("🎯 Seçilen konu:", topic)

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
