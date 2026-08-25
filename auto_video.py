import os
import subprocess
import sys
import json
import random

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

CONTENT = os.path.join(OUT, "current_content.txt")
VOICE = os.path.join(OUT, "current_voice.wav")
VIDEO_NO_AUDIO = os.path.join(OUT, "current_video_no_audio.mp4")
FINAL = os.path.join(OUT, "current_final.mp4")
THUMBNAIL = os.path.join(OUT, "current_thumbnail.jpg")

TOPICS = [
    "Nikola Tesla'nın en şaşırtıcı icatları ve hayatındaki bilinmeyen olaylar",
    "Albert Einstein'ın hayatındaki en şaşırtıcı olaylar ve bilimsel keşifleri",
    "Antik Mısır'ın çözülemeyen gizemleri",
    "Dünya tarihindeki en gizemli kayıp şehirler",
    "İnsan beyninin bilinmeyen özellikleri",
    "Uzay hakkında bilim insanlarını şaşırtan gerçekler",
    "Tarihin en ilginç icatlarının ortaya çıkış hikâyeleri",
    "Okyanusların keşfedilmemiş gizemleri",
    "Dünyanın en sıra dışı doğal olayları",
    "Tarihte yaşanmış en şaşırtıcı bilimsel deneyler"
]


def run(cmd, name):
    print()
    print("=" * 40)
    print(name)
    print("=" * 40)

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
        raise SystemExit(
            f"❌ HATA: {name} (exit code {result.returncode})"
        )

def main():

    topic = random.choice(TOPICS)

    print("================================")
    print("🤖 TAM OTOMATİK VİDEO SİSTEMİ")
    print("================================")
    print("🎯 Otomatik konu:", topic)

    # --------------------------------------------------
    # 1. İÇERİK
    # --------------------------------------------------

    print()
    print("🧠 1/6 İÇERİK OLUŞTURULUYOR...")

    run(
        [
            sys.executable,
            "generate_content.py",
            topic
        ],
        "İÇERİK MOTORU"
    )

    if not os.path.exists(CONTENT):
        raise SystemExit("❌ current_content.txt oluşmadı.")

    # --------------------------------------------------
    # 2. SES
    # --------------------------------------------------

    print()
    print("🎙️ 2/6 SES OLUŞTURULUYOR...")

    run(
        [
            sys.executable,
            "voiceover.py",
            CONTENT,
            VOICE
        ],
        "SES MOTORU"
    )

    if not os.path.exists(VOICE):
        raise SystemExit("❌ current_voice.wav oluşmadı.")

    # --------------------------------------------------
    # 3. GÖRSELLER
    # --------------------------------------------------

    print()
    print("🖼️ 3/6 GÖRSELLER BULUNUYOR...")

    run(
        [
            sys.executable,
            "get_visuals.py"
        ],
        "GÖRSEL MOTORU"
    )

    MANIFEST = os.path.join(OUT, "visual_manifest.json")

    if not os.path.exists(MANIFEST):
        raise SystemExit("❌ visual_manifest.json oluşmadı.")

    with open(MANIFEST, encoding="utf-8") as f:
        data = json.load(f)

    valid = [
        x for x in data
        if x.get("file") and os.path.exists(x["file"])
    ]

    print()
    print("✅ Kullanılabilir görsel:", len(valid))

    if not valid:
        raise SystemExit("❌ Hiç kullanılabilir görsel bulunamadı.")

    # --------------------------------------------------
    # 4. GÖRSELLİ VİDEO
    # --------------------------------------------------

    print()
    print("🎬 4/6 GÖRSELLİ VİDEO OLUŞTURULUYOR...")

    temp_script = os.path.join(BASE, "_auto_visual.py")

    with open(
        "unique_visual_video.py",
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

    with open(temp_script, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        run(
            [
                sys.executable,
                temp_script
            ],
            "GÖRSELLİ VİDEO MOTORU"
        )
    finally:
        if os.path.exists(temp_script):
            os.remove(temp_script)

    if not os.path.exists(VIDEO_NO_AUDIO):
        raise SystemExit("❌ Görsel video oluşmadı.")

    # --------------------------------------------------
    # 5. SES + VİDEO
    # --------------------------------------------------

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

    # --------------------------------------------------
    # THUMBNAIL
    # --------------------------------------------------

    print()
    print("🖼️ THUMBNAIL OLUŞTURULUYOR...")

    run(
        [
            sys.executable,
            "thumbnail_generator.py"
        ],
        "THUMBNAIL MOTORU"
    )

    if not os.path.exists(THUMBNAIL):
        raise SystemExit("❌ Thumbnail oluşturulamadı.")

    print("✅ Thumbnail hazır:", THUMBNAIL)

    # --------------------------------------------------
    # 6. YOUTUBE'A YÜKLE
    # --------------------------------------------------

    print()
    print("📤 6/6 YOUTUBE'A YÜKLENİYOR...")

    run(
        [
            sys.executable,
            "upload_youtube.py"
        ],
        "YOUTUBE YÜKLEYİCİ"
    )

    # --------------------------------------------------
    # TEMİZLİK
    # --------------------------------------------------

    if os.path.exists(VIDEO_NO_AUDIO):
        os.remove(VIDEO_NO_AUDIO)

    print()
    print("================================")
    print("🎉 OTOMATİK VİDEO HAZIR")
    print("================================")
    print("🎯 Konu:", topic)
    print("📁 Video:", FINAL)
    print("🖼️ Thumbnail:", THUMBNAIL)
    print(
        "💾 Boyut:",
        round(os.path.getsize(FINAL) / 1024 / 1024, 2),
        "MB"
    )
    print("================================")


if __name__ == "__main__":
    main()
