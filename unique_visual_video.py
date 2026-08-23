import os
import json
import random
import subprocess
import hashlib

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

MANIFEST = os.path.join(OUT, "visual_manifest.json")
VOICE = os.path.join(OUT, "einstein_voice.wav")
CONCAT = os.path.join(OUT, "unique_visuals.txt")
VIDEO = os.path.join(OUT, "einstein_unique.mp4")

# -------------------------------------------------
# SES SÜRESİ
# -------------------------------------------------

voice_cmd = [
    "ffprobe", "-v", "error",
    "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1",
    VOICE
]

voice_duration = float(
    subprocess.check_output(voice_cmd).decode().strip()
)

# -------------------------------------------------
# MANIFEST
# -------------------------------------------------

with open(MANIFEST, encoding="utf-8") as f:
    manifest = json.load(f)

# -------------------------------------------------
# BENZERSİZ DOSYALAR
# -------------------------------------------------

def file_hash(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


images = []
hashes = set()

for item in manifest:

    path = item.get("file")

    if not path:
        continue

    if not os.path.exists(path):
        continue

    try:
        h = file_hash(path)
    except Exception:
        continue

    # Aynı dosyanın kopyasını da kullanma.
    if h in hashes:
        continue

    hashes.add(h)

    images.append(path)

print("================================")
print("🧠 TEK KULLANIMLIK GÖRSEL MOTORU")
print("================================")
print("Ses:", round(voice_duration, 2), "saniye")
print("Benzersiz görsel:", len(images))
print()

if not images:
    raise SystemExit("Hiç görsel yok.")

# -------------------------------------------------
# GÖRSELLERİ TEK TEK KULLAN
# -------------------------------------------------

random.seed(2026)

sequence = []

# Her görsel sadece bir kez.
for path in images:
    sequence.append(path)

# -------------------------------------------------
# GÖRSEL BAŞINA SÜRE
# -------------------------------------------------

# Görsel sayısı azsa süreleri otomatik uzat.
average = voice_duration / len(sequence)

print("Ortalama görsel süresi:",
      round(average, 2),
      "saniye")

if average < 5:
    average = 5

# Her görselin süresini eşit dağıt.
durations = [
    average for _ in sequence
]

# Toplam süreyi tam ses süresine eşitle.
durations[-1] += voice_duration - sum(durations)

# -------------------------------------------------
# CONCAT DOSYASI
# -------------------------------------------------

with open(CONCAT, "w", encoding="utf-8") as f:

    for path, duration in zip(sequence, durations):

        path = os.path.abspath(path)
        path = path.replace("'", "'\\''")

        f.write(f"file '{path}'\n")
        f.write(f"duration {duration:.3f}\n")

    # FFmpeg son frame'i ister.
    last = os.path.abspath(sequence[-1])
    last = last.replace("'", "'\\''")

    f.write(f"file '{last}'\n")

print("Görsel geçişleri:", len(sequence))
print("Toplam süre:", round(sum(durations), 2))
print()

# -------------------------------------------------
# GÖRSELLERDEN VİDEO
# -------------------------------------------------

print("🎬 Görsel video oluşturuluyor...")

cmd = [
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", CONCAT,
    "-vf",
    "scale=1920:1080:force_original_aspect_ratio=increase,"
    "crop=1920:1080,"
    "format=yuv420p",
    "-r", "30",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "23",
    "-an",
    VIDEO
]

result = subprocess.run(cmd)

if result.returncode != 0:
    raise SystemExit("FFmpeg video oluşturamadı.")

print()
print("================================")
print("✅ BENZERSİZ GÖRSELLİ VİDEO")
print("================================")
print("Dosya:", VIDEO)
print("Görsel:", len(sequence))
print("Ses hedefi:", round(voice_duration, 2), "sn")
print("================================")
