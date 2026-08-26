import os
import json
import subprocess
import textwrap

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

MANIFEST = os.path.join(OUT, "shorts_visual_manifest.json")
DURATIONS_FILE = os.path.join(OUT, "shorts_scene_durations.json")
VOICE = os.path.join(OUT, "shorts_voice.wav")
CONCAT = os.path.join(OUT, "shorts_unique_visuals.txt")
VIDEO = os.path.join(OUT, "shorts_video_no_audio.mp4")

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def escape_drawtext(text):
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\u2019")
    text = text.replace("%", "\\%")
    return text


def wrap_for_subtitle(text, width=28):
    lines = textwrap.wrap(text, width=width)
    return "\n".join(lines[:3])


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

with open(DURATIONS_FILE, encoding="utf-8") as f:
    scene_duration_data = json.load(f)

real_durations = [item["duration"] for item in scene_duration_data]
real_texts = [item["text"] for item in scene_duration_data]

print("================================")
print("🧠 SHORTS DİKEY GÖRSEL MOTORU (BİREBİR SAHNE EŞLEMESİ)")
print("================================")
print("Ses:", round(voice_duration, 2), "saniye")
print("Manifest kaydı:", len(manifest))
print("Sahne süre kaydı:", len(real_durations))
print()

# --- ÖNEMLİ: Artık hiçbir dedup/atlama yapmıyoruz. ---
# Her sahne (manifest'teki her kayıt) kendi sırasında, kendi görseliyle
# kullanılır — görsel aynı bile olsa. Böylece:
# sequence uzunluğu == real_durations uzunluğu == real_texts uzunluğu
# HER ZAMAN garanti edilir, altyazı asla kaymaz/üst üste binmez.

sequence = [item["file"] for item in manifest]

if len(sequence) != len(real_durations):
    raise SystemExit(
        f"❌ KRİTİK HATA: manifest sahne sayısı ({len(sequence)}) ile "
        f"ses sahne sayısı ({len(real_durations)}) uyuşmuyor. "
        f"shorts_get_visuals.py her sahne için mutlaka bir kayıt üretmeli."
    )

durations = list(real_durations)
scene_texts = list(real_texts)

# Toplam süreyi ses uzunluğuna kesin eşitle (yuvarlama farkını son sahneye ekle)
diff = voice_duration - sum(durations)
durations[-1] += diff

print("✅ Sahne sayıları birebir eşleşiyor, gerçek sürelerle devam ediliyor.")
print("Toplam görsel süresi:", round(sum(durations), 2), "sn")
print()

with open(CONCAT, "w", encoding="utf-8") as f:

    for path, duration in zip(sequence, durations):

        path_escaped = os.path.abspath(path)
        path_escaped = path_escaped.replace("'", "'\\''")

        f.write(f"file '{path_escaped}'\n")
        f.write(f"duration {duration:.3f}\n")

    last = os.path.abspath(sequence[-1])
    last = last.replace("'", "'\\''")

    f.write(f"file '{last}'\n")

print("Görsel geçişleri (sahne sayısı):", len(sequence))
print()

# --- Altyazı zamanlaması: kümülatif, üst üste binmesi imkansız ---

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

    # Küçük bir güvenlik payı: bitişten 0.02 sn önce kapat,
    # bir sonraki sahnenin başlangıcıyla asla çakışmasın.
    end = start + duration - 0.02

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

print("🎬 Dikey (Shorts) video oluşturuluyor (kesin senkron altyazılı)...")

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
print("✅ SHORTS DİKEY GÖRSELLİ VİDEO (KESİN SENKRON)")
print("================================")
print("Dosya:", VIDEO)
print("Görsel:", len(sequence))
print("Ses hedefi:", round(voice_duration, 2), "sn")
print("================================")
