import os
import subprocess
import sys
import re

BASE = os.path.expanduser("~/yt_bilgi_uzun")
MODEL = "tr_TR-dfki-medium"

os.environ["PIPER_VOICE_PATH"] = os.path.join(BASE, "models")


def clean_text(text):
    import re

    # Tüm senaryo/metadata başlıklarını ve satırlarını kaldır
    bad_patterns = [
        r'(?im)^.*seslendirme metni.*$',
        r'(?im)^.*metadata.*$',
        r'(?im)^.*senaryo.*$',
        r'(?im)^.*başlık\s*:.*$',
        r'(?im)^.*açıklama\s*:.*$',
        r'(?im)^.*etiketler\s*:.*$',
        r'(?im)^.*tags\s*:.*$',
        r'(?im)^.*title\s*:.*$',
        r'(?im)^.*description\s*:.*$',
        r'(?im)^.*kamera.*$',
        r'(?im)^.*müzik.*$',
        r'(?im)^.*ses efekti.*$',
        r'(?im)^.*sahne\s*\d*.*$',
        r'(?im)^.*scene\s*\d*.*$',
        r'(?im)^.*görsel\s*:.*$',
        r'(?im)^.*görüntü\s*:.*$',
        r'(?im)^.*yönetmen.*$',
    ]

    for pattern in bad_patterns:
        text = re.sub(pattern, '', text)

    # Parantez içlerini kaldır
    text = re.sub(r'\[[^\]]*\]', ' ', text)
    text = re.sub(r'\([^)]*\)', ' ', text)
    text = re.sub(r'\{[^}]*\}', ' ', text)

    # Markdown ve gereksiz semboller
    text = re.sub(r'[*_`~#]+', ' ', text)
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)

    # Boşlukları düzelt
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n+', ' ', text)

    return text.strip()

def create_voice(text_file, output_wav):
    if not os.path.isfile(text_file):
        raise FileNotFoundError(f"Senaryo bulunamadı: {text_file}")

    raw_file = output_wav.replace(".wav", ".raw")

    print("🎙️ Piper Türkçe ses oluşturuyor...")

    with open(text_file, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        raise RuntimeError("Senaryo dosyası boş.")

    # TTS'ye göndermeden ÖNCE temizle
    text = clean_text(text)

    if not text:
        raise RuntimeError("Temizleme sonrası seslendirilecek metin kalmadı.")

    print("🧹 TTS metni temizlendi.")
    print("📝 Karakter sayısı:", len(text))

    subprocess.run(
        [
            "/usr/local/piper",
            "-m", MODEL,
            "-f", raw_file,
            "--",
            text
        ],
        check=True
    )

    print("🔊 WAV oluşturuluyor...")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f", "f32le",
            "-ar", "22050",
            "-ac", "1",
            "-i", raw_file,
            "-c:a", "pcm_s16le",
            output_wav
        ],
        check=True
    )

    os.remove(raw_file)

    print(f"✅ Ses hazır: {output_wav}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Kullanım:")
        print("python voiceover.py senaryo.txt ses.wav")
        sys.exit(1)

    create_voice(sys.argv[1], sys.argv[2])
