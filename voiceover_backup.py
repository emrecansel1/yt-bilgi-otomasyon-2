import os
import subprocess
import sys

BASE = os.path.expanduser("~/yt_bilgi_uzun")
MODEL = "tr_TR-dfki-medium"

os.environ["PIPER_VOICE_PATH"] = os.path.join(BASE, "models")


def create_voice(text_file, output_wav):
    if not os.path.isfile(text_file):
        raise FileNotFoundError(f"Senaryo bulunamadı: {text_file}")

    raw_file = output_wav.replace(".wav", ".raw")

    print("🎙️ Piper Türkçe ses oluşturuyor...")

    with open(text_file, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        raise RuntimeError("Senaryo dosyası boş.")

    subprocess.run(
        [
            "piper",
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
