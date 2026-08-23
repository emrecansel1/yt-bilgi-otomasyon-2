import os
import json
import subprocess

OUT = os.path.expanduser("~/yt_bilgi_uzun/output")
MANIFEST = os.path.join(OUT, "visual_manifest.json")
OUTPUT = os.path.join(OUT, "einstein_visual_video.mp4")
CONCAT = os.path.join(OUT, "visual_concat.txt")

with open(MANIFEST, encoding="utf-8") as f:
    data = json.load(f)

items = []

for x in data:
    path = x.get("file")
    if path and os.path.exists(path):
        items.append((path, float(x.get("duration", 5))))

print("================================")
print("GÖRSELLİ VİDEO MOTORU")
print("================================")
print("Kullanılabilir görsel:", len(items))

if not items:
    raise SystemExit("HATA: Görsel bulunamadı.")

with open(CONCAT, "w", encoding="utf-8") as f:
    for path, duration in items:
        path = os.path.abspath(path).replace("'", "'\\''")
        f.write("file '" + path + "'\n")
        f.write("duration " + str(duration) + "\n")

    path = os.path.abspath(items[-1][0]).replace("'", "'\\''")
    f.write("file '" + path + "'\n")

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
    "-movflags", "+faststart",
    OUTPUT
]

print("FFmpeg başlıyor...")
print()

result = subprocess.run(cmd)

if result.returncode != 0:
    raise SystemExit("HATA: FFmpeg başarısız oldu.")

print()
print("================================")
print("VIDEO HAZIR")
print("================================")
print(OUTPUT)
print("Boyut:", round(os.path.getsize(OUTPUT) / 1024 / 1024, 2), "MB")
