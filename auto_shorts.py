import os
import subprocess
import sys
import json
from datetime import datetime

import bg_music

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

REPO_BASE = os.path.dirname(os.path.abspath(__file__))

CONTENT_JSON = os.path.join(REPO_BASE, "shorts_content.json")

SCRIPT_TEXT = os.path.join(OUT, "shorts_script.txt")
VOICE = os.path.join(OUT, "shorts_voice.wav")
VIDEO_NO_AUDIO = os.path.join(OUT, "shorts_video_no_audio.mp4")
FINAL = os.path.join(OUT, "shorts_final.mp4")
META_FILE = os.path.join(OUT, "shorts_meta.json")
MUSIC_FILE = os.path.join(OUT, "shorts_bg_music.mp3")

# Workflow cron'u 00:15/08:15/16:15 UTC'de tetikleniyor.
# Job env'inde TZ=Europe/Istanbul ayarlı, bu da 03:xx/11:xx/19:xx
# Istanbul saatine denk gelir.
HEDEF_SAATLER = {3, 11, 19}

def run(cmd, name):
    print()
    print("=" * 40)
    print(name)
    print("=" * 40)

    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise SystemExit(f"❌ HATA: {name}")

def main():

    tetikleyici = os.environ.get("GITHUB_EVENT_NAME", "")
    simdi_saat = datetime.now().hour

    if tetikleyici != "workflow_dispatch" and simdi_saat not in HEDEF_SAATLER:
        print(f"⏭️ Saat {simdi_saat}:00 hedef saatlerden ({sorted(HEDEF_SAATLER)}) "
              f"biri değil, bu run atlanıyor.")
        return

    if tetikleyici == "workflow_dispatch":
        print("🖐️ Elle tetiklendi, saat filtresi atlanıyor.")

    os.makedirs(OUT, exist_ok=True)

    print("================================")
    print("🤖 TAM OTOMATİK SHORTS SİSTEMİ")
    print("================================")

    print()
    print("🧠✍️ 1/5 KONU + METİN ÜRETİLİYOR (TEK YAPAY ZEKA İSTEĞİ)...")

    run(
        [sys.executable, os.path.join(REPO_BASE, "shorts_content.py")],
        "SHORTS KONU + İÇERİK MOTORU"
    )

    if not os.path.exists(CONTENT_JSON):
        raise SystemExit("❌ shorts_content.json oluşmadı.")

    with open(CONTENT_JSON, encoding="utf-8") as f:
        data = json.load(f)

    contents = data.get("contents", [])

    if not contents:
        raise SystemExit("❌ shorts_content.json içinde içerik yok.")

    item = contents[0]

    topic = item.get("topic", "").strip()
    script_text = item.get("script", "").strip()
    title = item.get("title", "").strip()
    description = item.get("description", "").strip()
    tags = item.get("tags", "").strip()

    if not script_text:
        raise SystemExit("❌ Shorts metni boş.")

    with open(SCRIPT_TEXT, "w", encoding="utf-8") as f:
        f.write(script_text)

    print()
    print("🎵 Arka plan müziği indiriliyor...")

    music_track = bg_music.download_music(MUSIC_FILE)

    if music_track:
        description = (
            description + bg_music.license_credit(music_track)
        ).strip()

    meta = {"title": title, "description": description, "tags": tags}

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print()
    print("🎯 Konu:", topic)
    print("🎬 Başlık:", title)
    print("📝 Kelime sayısı:", len(script_text.split()))

    print()
    print("🎙️ 2/5 SES OLUŞTURULUYOR...")

    run(
        [sys.executable, os.path.join(REPO_BASE, "voiceover.py"), SCRIPT_TEXT, VOICE],
        "SES MOTORU"
    )

    if not os.path.exists(VOICE):
        raise SystemExit("❌ shorts_voice.wav oluşmadı.")

    print()
    print("🖼️ 3/5 GÖRSELLER BULUNUYOR VE VİDEO OLUŞTURULUYOR...")

    run(
        [sys.executable, os.path.join(REPO_BASE, "shorts_get_visuals.py")],
        "GÖRSEL MOTORU"
    )

    run(
        [sys.executable, os.path.join(REPO_BASE, "shorts_visual_video.py")],
        "GÖRSELLİ VİDEO MOTORU"
    )

    if not os.path.exists(VIDEO_NO_AUDIO):
        raise SystemExit("❌ shorts_video_no_audio.mp4 oluşmadı.")

    print()
    print("🔊 4/5 SES VİDEOYA EKLENİYOR...")

    if music_track and os.path.exists(MUSIC_FILE):

        run(
            [
                "ffmpeg", "-y",
                "-i", VIDEO_NO_AUDIO,
                "-i", VOICE,
                "-stream_loop", "-1",
                "-i", MUSIC_FILE,
                "-filter_complex",
                "[2:a]volume=0.10[bg];"
                "[1:a][bg]amix=inputs=2:duration=first:"
                "dropout_transition=2:weights=1 1[amix];"
                "[amix]loudnorm=I=-14:TP=-1.5:LRA=11[aout]",
                "-map", "0:v:0",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                "-movflags", "+faststart",
                FINAL
            ],
            "FİNAL VİDEO (MÜZİKLİ)"
        )

    else:

        run(
            [
                "ffmpeg", "-y",
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
            "FİNAL VİDEO (MÜZİKSİZ)"
        )

    if not os.path.exists(FINAL):
        raise SystemExit("❌ shorts_final.mp4 oluşmadı.")

    print()
    print("📤 5/5 YOUTUBE SHORTS'A YÜKLENİYOR...")

    run(
        [sys.executable, os.path.join(REPO_BASE, "upload_youtube_shorts.py")],
        "YOUTUBE SHORTS YÜKLEYİCİ"
    )

    if os.path.exists(VIDEO_NO_AUDIO):
        os.remove(VIDEO_NO_AUDIO)

    if os.path.exists(MUSIC_FILE):
        os.remove(MUSIC_FILE)

    print()
    print("================================")
    print("🎉 SHORTS VİDEO HAZIR")
    print("================================")
    print("🎯 Konu:", topic)
    print("🎬 Başlık:", title)
    print("📁 Dosya:", FINAL)
    print("💾 Boyut:", round(os.path.getsize(FINAL) / 1024 / 1024, 2), "MB")
    print("================================")

if __name__ == "__main__":
    main()
