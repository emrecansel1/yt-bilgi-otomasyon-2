import os
import json
import subprocess

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

MANIFEST = os.path.join(OUT, "visual_manifest.json")
AUDIO = os.path.join(OUT, "einstein_voice.wav")
OUTPUT = os.path.join(OUT, "einstein_auto_video.mp4")

with open(MANIFEST, encoding="utf-8") as f:
    manifest = json.load(f)

# Sadece gerçekten mevcut dosyaları al
items = []

for item in manifest:
    path = item.get("file")

    if path and os.path.exists(path):
        items.append(path)

if not items:
    raise RuntimeError("Kullanılabilir görsel bulunamadı.")

# Görsel tekrarlarını engelle
unique = []
seen = set()

for path in items:
    real = os.path.realpath(path)

    if real not in seen:
        seen.add(real)
        unique.append(path)

items = unique

# Ses süresini öğren
cmd_duration = [
    "ffprobe",
    "-v", "error",
    "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1",
    AUDIO
]

audio_duration = float(
    subprocess.check_output(cmd_duration).decode().strip()
)

# Her görsele eşit süre dağıt.
# Böylece kaç görsel bulunduysa tamamı video boyunca yayılır.
duration_per_image = audio_duration / len(items)

print("================================")
print("🧠 OTOMATİK GÖRSEL ZAMANLAMA")
print("================================")
print("Benzersiz görsel:", len(items))
print("Ses süresi:", round(audio_duration, 2), "sn")
print("Görsel başına:", round(duration_per_image, 2), "sn")
print()

concat = os.path.join(OUT, "auto_visual_concat.txt")

with open(concat, "w", encoding="utf-8") as f:

    for path in items:
        safe = os.path.abspath(path).replace("'", "'\\''")

        f.write(f"file '{safe}'\n")
        f.write(f"duration {duration_per_image:.6f}\n")

    # concat demuxer son dosyanın süresini doğru uygulamak için
    safe = os.path.abspath(items[-1]).replace("'", "'\\''")
    f.write(f"file '{safe}'\n")

print("🎬 FFmpeg başlıyor...")

cmd = [
    "ffmpeg",
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", concat,
    "-i", AUDIO,

    "-map", "0:v:0",
    "-map", "1:a:0",

    "-vf",
    "scale=1920:1080:force_original_aspect_ratio=increase,"
    "crop=1920:1080,"
    "format=yuv420p",

    "-r", "30",

    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "23",

    "-c:a", "aac",
    "-b:a", "128k",

    "-shortest",
    "-movflags", "+faststart",

    OUTPUT
]

result = subprocess.run(cmd)

if result.returncode != 0:
    raise RuntimeError("FFmpeg video oluşturamadı.")

print()
print("================================")
print("✅ OTOMATİK VİDEO HAZIR")
print("================================")
print("Dosya:", OUTPUT)
print("Görsel:", len(items))
print("Ses:", round(audio_duration, 2), "sn")
