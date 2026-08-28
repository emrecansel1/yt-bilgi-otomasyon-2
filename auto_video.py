import os
import subprocess
import sys
import json
from datetime import datetime

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

REPO_BASE = os.path.dirname(os.path.abspath(__file__))

CONTENT = os.path.join(OUT, "current_content.txt")
TOPIC_FILE = os.path.join(OUT, "current_topic.txt")

VOICE = os.path.join(OUT, "current_voice.wav")
VIDEO_NO_AUDIO = os.path.join(OUT, "current_video_no_audio.mp4")
FINAL = os.path.join(OUT, "current_final.mp4")
THUMBNAIL = os.path.join(OUT, "current_thumbnail.jpg")

HEDEF_SAAT = 17


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
        print(f"⏭️ Saat {simdi_saat}:00, hedef saat {HEDEF_SAAT}:00 değil, bu run atlanıyor.")
        return

    if tetikleyici == "workflow_dispatch":
        print("🖐️ Elle tetiklendi, saat filtresi atlanıyor.")

    os.makedirs(OUT, exist_ok=True)

    print("================================")
    print("🤖 TAM OTOMATİK UZUN VİDEO SİSTEMİ (1 SAATLİK BELGESEL)")
    print("================================")

    print()
    print("🧠✍️ 1/6 KONU + BÖLÜM PLANI + İÇERİK OLUŞTURULUYOR...")

    run([sys.executable, "generate_content.py"], "İÇERİK MOTORU")

    if not os.path.exists(CONTENT):
        raise SystemExit("❌ current_content.txt oluşmadı.")

    topic = ""
    if os.path.exists(TOPIC_FILE):
        with open(TOPIC_FILE, encoding="utf-8") as f:
            topic = f.read().strip()

    print()
    print("🎯 Konu:", topic)
    print()
    print("🎙️ 2/6 SES OLUŞTURULUYOR...")

    run([sys.executable, "voiceover.py", CONTENT, VOICE], "SES MOTORU")

    if not os.path.exists(VOICE):
        raise SystemExit("❌ current_voice.wav oluşmadı.")

    print()
    print("🖼️ 3/6 GÖRSELLER/VİDEOLAR BULUNUYOR...")

    run([sys.executable, "get_visuals.py"], "GÖRSEL MOTORU")

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
    print("🎬 4/6 GÖRSELLİ/VİDEOLU FİNAL VİDEO OLUŞTURULUYOR...")

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
    print("🔊 5/6 SES VİDEOYA EKLENİYOR...")

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
    print("🖼️ 6/6a THUMBNAIL OLUŞTURULUYOR...")

    thumb_ok = run_optional([sys.executable, "thumbnail_generator.py"], "THUMBNAIL MOTORU")

    if thumb_ok and os.path.exists(THUMBNAIL):
        print("✅ Thumbnail hazır:", THUMBNAIL)
    else:
        print("⚠️ Thumbnail oluşturulamadı, video thumbnail'siz devam edecek.")

    print()
    print("📤 6/6b YOUTUBE'A YÜKLENİYOR...")

    run([sys.executable, "upload_youtube.py"], "YOUTUBE YÜKLEYİCİ")

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
