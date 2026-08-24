import os
import subprocess
import sys
import re

PIPER_VOICE_PATH = os.environ.get("PIPER_VOICE_PATH", ".")
MODEL = os.path.join(PIPER_VOICE_PATH, "tr_TR-dfki-medium.onnx")

def clean_text(text):
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

    text = re.sub(r'\[[^\]]*\]', ' ', text)
    text = re.sub(r'\([^)]*\)', ' ', text)
    text = re.sub(r'\{[^}]*\}', ' ', text)
    text = re.sub(r'[*_`~#]+', ' ', text)
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n+', ' ', text)

    return text.strip()


def create_voice(text_file, output_wav):
    if not os.path.isfile(text_file):
        raise FileNotFoundError(f"Senaryo bulunamadı: {text_file}")

    if not os.path.isfile(MODEL):
        raise FileNotFoundError(f"Piper modeli bulunamadı: {MODEL}")

    piper = os.environ.get("PIPER_BIN", "/opt/piper/piper")

    if not os.path.isfile(piper):
        raise FileNotFoundError(f"Piper bulunamadı: {piper}")

    with open(text_file, "r", encoding="utf-8") as f:
        text = clean_text(f.read())

    if not text:
        raise RuntimeError("Temizleme sonrası seslendirilecek metin kalmadı.")

    print("🎙️ Piper Türkçe ses oluşturuyor...")
    print("📝 Karakter sayısı:", len(text))
    print("🤖 Model:", MODEL)
    print("🔧 Piper:", piper)

    os.makedirs(os.path.dirname(os.path.abspath(output_wav)), exist_ok=True)

    subprocess.run(
        [
            piper,
            "-m", MODEL,
            "-f", output_wav
        ],
        input=text + "\n",
        text=True,
        check=True
    )

    if not os.path.isfile(output_wav) or os.path.getsize(output_wav) == 0:
        raise RuntimeError("Piper WAV dosyası oluşturamadı.")

    print("🔊 WAV kontrolü...")

    subprocess.run(
        ["ffprobe", "-v", "error", output_wav],
        check=True
    )

    print(f"✅ Ses hazır: {output_wav}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Kullanım: python voiceover.py senaryo.txt ses.wav")
        sys.exit(1)

    create_voice(sys.argv[1], sys.argv[2])
