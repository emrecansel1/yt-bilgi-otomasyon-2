import os
import json
import random
import subprocess
import hashlib
import textwrap

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

MANIFEST = os.path.join(OUT, "shorts_visual_manifest.json")
VOICE = os.path.join(OUT, "shorts_voice.wav")
CONCAT = os.path.join(OUT, "shorts_unique_visuals.txt")
VIDEO = os.path.join(OUT, "shorts_video_no_audio.mp4")

# Sistemde bulunan bir Türkçe karakter destekli font.
# GitHub Actions (ubuntu-latest) için workflow'a şunu eklemen gerekiyor:
#   sudo apt-get update && sudo apt-get install -y fonts-dejavu-core
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

voice_cmd = [
    "ffprobe", "-v", "error",
    "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1",
    VOICE
]

voice_duration = float(
    subprocess.check_output(voice_cmd).decode().strip()
)

with open(MANIFEST, encoding="utf-8") as f:
    manifest = json.load(f)


def file_hash(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def escape_drawtext(text):
    # ffmpeg drawtext için özel karakterleri kaçır
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\u2019")  # tek tırnağı kapalı tırnakla değiştir
    text = text.replace("%", "\\%")
    return text


def wrap_for_subtitle(text, width=28):
    lines = textwrap.wrap(text, width=width)
    return "\n".join(lines[:3])  # en fazla 3 satır


items = []
hashes = set()

for item in manifest:

    path = item.get("file")
    scene_text = item.get("scene_text", "")

    if not path:
        continue

    if not os.path.exists(path):
        continue

    try:
        h = file_hash(path)
    except Exception:
        continue

    if h in hashes:
        continue

    hashes.add(h)

    items.append((path, scene_text))

print("================================")
print("🧠 SHORTS DİKEY GÖRSEL MOTORU")
print("================================")
print("Ses:", round(voice_duration, 2), "saniye")
print("Benzersiz görsel:", len(items))
print()

if not items:
    raise SystemExit("Hiç görsel yok.")

random.seed(2026)

sequence = [path for path, _ in items]
scene_texts = [text for _, text in items]

average = voice_duration / len(sequence)

print("Ortalama görsel süresi:",
      round(average, 2),
      "saniye")

if average < 2.5:
    average = 2.5

durations = [
    average for _ in sequence
]

durations[-1] += voice_duration - sum(durations)

with open(CONCAT, "w", encoding="utf-8") as f:

    for path, duration in zip(sequence, durations):

        path_escaped = os.path.abspath(path)
        path_escaped = path_escaped.replace("'", "'\\''")

        f.write(f"file '{path_escaped}'\n")
        f.write(f"duration {duration:.3f}\n")

    last = os.path.abspath(sequence[-1])
    last = last.replace("'", "'\\''")

    f.write(f"file '{last}'\n")

print("Görsel geçişleri:", len(sequence))
print("Toplam süre:", round(sum(durations), 2))
print()

# --- Altyazı zamanlamasını hesapla ---

starts = []
cursor = 0.0

for duration in durations:
    starts.append(cursor)
    cursor += duration

drawtext_filters = []

for text, start, duration in zip(scene_texts, starts, durations):

    if not text:
        continue

    wrapped = wrap_for_subtitle(text)
    wrapped = escape_drawtext(wrapped)

    end = start + duration

    drawtext_filters.append(
        "drawtext=fontfile='" + FONT_PATH + "'"
        ":text='" + wrapped + "'"
        ":fontsize=58"
        ":fontcolor=white"
        ":borderw=4"
        ":bordercolor=black"
        ":box=1"
        ":boxcolor=black@0.45"
        ":boxborderw=20"
        ":line_spacing=8"
        ":x=(w-text_w)/2"
        ":y=h-h/3.2"
        f":enable='between(t,{start:.3f},{end:.3f})'"
    )

vf_base = (
    "scale=1080:1920:force_original_aspect_ratio=increase,"
    "crop=1080:1920,"
    "format=yuv420p"
)

if drawtext_filters:
    vf = vf_base + "," + ",".join(drawtext_filters)
else:
    vf = vf_base

print("🎬 Dikey (Shorts) video oluşturuluyor (altyazılı)...")

cmd = [
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", CONCAT,
    "-vf", vf,
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
print("✅ SHORTS DİKEY GÖRSELLİ VİDEO (ALTYAZILI)")
print("================================")
print("Dosya:", VIDEO)
print("Görsel:", len(sequence))
print("Ses hedefi:", round(voice_duration, 2), "sn")
print("================================")
