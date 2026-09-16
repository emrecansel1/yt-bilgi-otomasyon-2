import os
import subprocess
import sys
import json
import re
from datetime import datetime

import bg_music

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

REPO_BASE = os.path.dirname(os.path.abspath(__file__))

CONTENT = os.path.join(OUT, "current_content.txt")
TOPIC_FILE = os.path.join(OUT, "current_topic.txt")

VOICE = os.path.join(OUT, "current_voice.wav")
VIDEO_NO_AUDIO = os.path.join(OUT, "current_video_no_audio.mp4")
FINAL = os.path.join(OUT, "current_final.mp4")
THUMBNAIL = os.path.join(OUT, "current_thumbnail.jpg")
MUSIC_FILE = os.path.join(OUT, "current_bg_music.mp3")

HEDEF_SAAT = 14

def run(cmd, name):
    print()
    print("=" * 60)
    print(f"🚀 {name}")
    print("=" * 60)

    try:
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True
        )
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ {name} ÇALIŞTIRILAMADI")
        print("=" * 60)
        print(f"❌ Hata türü: {type(e).__name__}")
        print(f"❌ Hata: {e}")
        print("=" * 60)
        raise SystemExit(1)

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        print()
        print("=" * 60)
        print(f"❌ {name} BAŞARISIZ")
        print(f"❌ Exit code: {result.returncode}")
        print("=" * 60)

        if result.stdout:
            print("📤 STDOUT:")
            print(result.stdout)

        if result.stderr:
            print("📥 STDERR:")
            print(result.stderr)

        print("=" * 60)

        raise SystemExit(1)

    print()
    print(f"✅ {name} BAŞARILI")
    print("=" * 60)

def run_optional(cmd, name):
    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    try:
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True
        )

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:
            print()
            print(
                f"⚠️ {name} başarısız oldu "
                f"(exit code {result.returncode}), "
                f"devam ediliyor..."
            )

            if result.stderr:
                print("📥 STDERR:")
                print(result.stderr)

            return False

        return True

    except Exception as e:
        print(
            f"⚠️ {name} çalıştırılamadı: "
            f"{type(e).__name__}: {e}"
        )
        return False

def add_music_credit(content_path, track):
    try:
        with open(content_path, encoding="utf-8") as f:
            text = f.read()

        credit = bg_music.license_credit(track)

        if "ETİKETLER:" in text:
            text = text.replace(
                "ETİKETLER:",
                credit.strip() + "\n\nETİKETLER:",
                1
            )
        else:
            text = text.rstrip() + "\n" + credit

        with open(content_path, "w", encoding="utf-8") as f:
            f.write(text)

        print("✅ Müzik ataf metni açıklamaya eklendi.")

    except Exception as e:
        print("⚠️ Müzik atıf metni eklenemedi:", str(e))

def main():

    tetikleyici = os.environ.get(
        "GITHUB_EVENT_NAME",
        ""
    )

    simdi_saat = datetime.now().hour

    # Elle tetiklenirse saat kontrolü YOK.
    # Schedule ile çalışırsa sadece HEDEF_SAAT'te devam eder.
    if tetikleyici == "workflow_dispatch":
        print(
            "🖐️ Elle tetiklendi, "
            "saat filtresi ATLANDI."
        )

    elif simdi_saat != HEDEF_SAAT:
        print(
            f"⏭️ Saat {simdi_saat}:00, "
            f"hedef saat {HEDEF_SAAT}:00 değil, "
            f"bu run atlanıyor."
        )
        return

    os.makedirs(
        OUT,
        exist_ok=True
    )

    print("================================")
    print(
        "🤖 TAM OTOMATİK UZUN VİDEO "
        "SİSTEMİ (1 SAATLİK BELGESEL)"
    )
    print("================================")

    print()
    print(
        "🧠✍️ 1/6 KONU + BÖLÜM PLANI + "
        "İÇERİK OLUŞTURULUYOR..."
    )

    run(
        [
            sys.executable,
            os.path.join(
                REPO_BASE,
                "generate_content.py"
            )
        ],
        "İÇERİK MOTORU"
    )

    if not os.path.exists(CONTENT):
        raise SystemExit(
            "❌ current_content.txt oluşmadı."
        )

    topic = ""

    if os.path.exists(TOPIC_FILE):
        with open(
            TOPIC_FILE,
            encoding="utf-8"
        ) as f:
            topic = f.read().strip()

    print()
    print("🎯 Konu:", topic)

    print()
    print("🎙️ 2/6 SES OLUŞTURULUYOR...")

    run(
        [
            sys.executable,
            os.path.join(
                REPO_BASE,
                "voiceover.py"
            ),
            CONTENT,
            VOICE
        ],
        "SES MOTORU"
    )

    if not os.path.exists(VOICE):
        raise SystemExit(
            "❌ current_voice.wav oluşmadı."
        )

    print()
    print(
        "🖼️ 3/6 GÖRSELLER/VİDEOLAR "
        "BULUNUYOR..."
    )

    run(
        [
            sys.executable,
            os.path.join(
                REPO_BASE,
                "get_visuals.py"
            )
        ],
        "GÖRSEL MOTORU"
    )

    MANIFEST = os.path.join(
        OUT,
        "visual_manifest.json"
    )

    if not os.path.exists(MANIFEST):
        raise SystemExit(
            "❌ visual_manifest.json oluşmadı."
        )

    with open(
        MANIFEST,
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    valid = [
        x
        for x in data
        if x.get("file")
        and os.path.exists(x["file"])
    ]

    print()
    print(
        "✅ Kullanılabilir sahne:",
        len(valid)
    )

    if not valid:
        raise SystemExit(
            "❌ Hiç kullanılabilir "
            "görsel/video bulunamadı."
        )

    print()
    print(
        "🎬 4/6 GÖRSELLİ/VİDEOLU "
        "FİNAL VİDEO OLUŞTURULUYOR..."
    )

    temp_script = os.path.join(
        BASE,
        "_auto_visual.py"
    )

    unique_visual_script = os.path.join(
        REPO_BASE,
        "unique_visual_video.py"
    )

    with open(
        unique_visual_script,
        encoding="utf-8"
    ) as f:
        code = f.read()

    code = code.replace(
        'VOICE = os.path.join(OUT, "einstein_voice.wav")',
        'VOICE = os.path.join(OUT, "current_voice.wav")'
    )

    code = code.replace(
        'VIDEO = os.path.join(OUT, "einstein_unique.mp4")',
        'VIDEO = os.path.join(OUT, "current_video_no_audio.mp4")'
    )

    with open(
        temp_script,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(code)

    try:
        run(
            [
                sys.executable,
                temp_script
            ],
            "GÖRSELLİ/VİDEOLU VİDEO MOTORU"
        )

    finally:
        if os.path.exists(temp_script):
            os.remove(temp_script)

    if not os.path.exists(
        VIDEO_NO_AUDIO
    ):
        raise SystemExit(
            "❌ Görsel/video birleşimi "
            "oluşmadı."
        )

    print()
    print(
        "🎵 5/6a ARKA PLAN MÜZİĞİ İNDİRİLİYOR..."
    )

    music_track = bg_music.download_music(MUSIC_FILE)

    if music_track:
        add_music_credit(CONTENT, music_track)

    print()
    print(
        "🔊 5/6b SES VİDEOYA EKLENİYOR..."
    )

    if music_track and os.path.exists(MUSIC_FILE):

        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                VIDEO_NO_AUDIO,
                "-i",
                VOICE,
                "-stream_loop",
                "-1",
                "-i",
                MUSIC_FILE,
                "-filter_complex",
                "[2:a]volume=0.10[bg];"
                "[1:a][bg]amix=inputs=2:duration=first:"
                "dropout_transition=2:weights=1 1[amix];"
                "[amix]loudnorm=I=-14:TP=-1.5:LRA=11[aout]",
                "-map",
                "0:v:0",
                "-map",
                "[aout]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-shortest",
                "-movflags",
                "+faststart",
                FINAL
            ],
            "FİNAL VİDEO (MÜZİKLİ)"
        )

    else:

        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                VIDEO_NO_AUDIO,
                "-i",
                VOICE,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-af",
                "loudnorm=I=-14:TP=-1.5:LRA=11",
                "-b:a",
                "128k",
                "-shortest",
                "-movflags",
                "+faststart",
                FINAL
            ],
            "FİNAL VİDEO (MÜZİKSİZ)"
        )

    if not os.path.exists(FINAL):
        raise SystemExit(
            "❌ Final video oluşmadı."
        )

    print()
    print("================================")
    print("✅ FINAL VIDEO HAZIR")
    print("================================")
    print("📁", FINAL)
    print(
        "📦 Boyut:",
        round(
            os.path.getsize(FINAL)
            / 1024
            / 1024,
            2
        ),
        "MB"
    )
    print("================================")

    print()
    print(
        "🖼️ 6/6a THUMBNAIL "
        "OLUŞTURULUYOR..."
    )

    thumb_ok = run_optional(
        [
            sys.executable,
            os.path.join(
                REPO_BASE,
                "thumbnail_generator.py"
            )
        ],
        "THUMBNAIL MOTORU"
    )

    if (
        thumb_ok
        and os.path.exists(THUMBNAIL)
    ):
        print(
            "✅ Thumbnail hazır:",
            THUMBNAIL
        )
    else:
        print(
            "⚠️ Thumbnail oluşturulamadı, "
            "video thumbnail'siz devam edecek."
        )

    print()
    print(
        "📤 6/6b YOUTUBE'A YÜKLENİYOR..."
    )

    run(
        [
            sys.executable,
            os.path.join(
                REPO_BASE,
                "upload_youtube.py"
            )
        ],
        "YOUTUBE YÜKLEYİCİ"
    )

    if os.path.exists(
        VIDEO_NO_AUDIO
    ):
        os.remove(
            VIDEO_NO_AUDIO
        )

    if os.path.exists(MUSIC_FILE):
        os.remove(MUSIC_FILE)

    print()
    print("================================")
    print("🎉 OTOMATİK VİDEO HAZIR")
    print("================================")
    print("🎯 Konu:", topic)
    print("📁 Video:", FINAL)

    print(
        "🖼️ Thumbnail:",
        (
            THUMBNAIL
            if os.path.exists(THUMBNAIL)
            else "yok"
        )
    )

    print(
        "💾 Boyut:",
        round(
            os.path.getsize(FINAL)
            / 1024
            / 1024,
            2
        ),
        "MB"
    )

    print("================================")

if __name__ == "__main__":
    main()
