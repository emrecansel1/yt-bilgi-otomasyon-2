import os
import json
import subprocess
import textwrap
import shutil

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

MANIFEST = os.path.join(OUT, "shorts_visual_manifest.json")
DURATIONS_FILE = os.path.join(OUT, "shorts_scene_durations.json")
VOICE = os.path.join(OUT, "shorts_voice.wav")
CONCAT = os.path.join(OUT, "shorts_unique_visuals.txt")
VIDEO = os.path.join(OUT, "shorts_video_no_audio.mp4")
FRAGMENTS_DIR = os.path.join(OUT, "shorts_fragments")

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


def build_drawtext(text):
    if not text:
        return None

    wrapped = wrap_for_subtitle(text)
    wrapped = escape_drawtext(wrapped)

    return (
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
    )


shutil.rmtree(FRAGMENTS_DIR, ignore_errors=True)
os.makedirs(FRAGMENTS_DIR, exist_ok=True)

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
print("🧠 SHORTS DİKEY GÖRSEL/VİDEO MOTORU (BİREBİR SAHNE EŞLEMESİ)")
print("================================")
print("Ses:", round(voice_duration, 2), "saniye")
print("Manifest kaydı:", len(manifest))
print("Sahne süre kaydı:", len(real_durations))
print()

sequence = [item["file"] for item in manifest]
kinds = [item.get("type", "image") for item in manifest]

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
print("Toplam hedef süre:", round(sum(durations), 2), "sn")
print()

# --- Her sahneyi kendi tam süresinde, kendi altyazısıyla birlikte
# ayrı bir mp4 parçası olarak render ediyoruz. Video klipse gerekirse
# döngüye alınıp kırpılıyor, fotoğrafsa Ken Burns'süz statik kare olarak
# tutuluyor. Böylece video/fotoğraf karışımı hiçbir senkron sorunu
# yaratmadan aynı akışta birleştirilebiliyor.

vf_scale_crop = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p"

fragment_paths = []

for idx, (path, duration, text, kind) in enumerate(
    zip(sequence, durations, scene_texts, kinds), 1
):
    frag_path = os.path.join(FRAGMENTS_DIR, f"frag_{idx:03d}.mp4")

    drawtext = build_drawtext(text)

    vf = vf_scale_crop
    if drawtext:
        vf = vf + "," + drawtext

    if kind == "video":
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", path,
            "-t", f"{duration:.3f}",
            "-vf", vf,
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-an",
            frag_path
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", path,
            "-t", f"{duration:.3f}",
            "-vf", vf,
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-an",
            frag_path
        ]

    print(f"[{idx}/{len(sequence)}] ({kind}) parça oluşturuluyor - {duration:.2f} sn")

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if result.returncode != 0 or not os.path.exists(frag_path):
        raise SystemExit(f"❌ Parça oluşturulamadı: {path} (sahne {idx})")

    fragment_paths.append(frag_path)

print()
print("🎬 Parçalar birleştiriliyor...")

with open(CONCAT, "w", encoding="utf-8") as f:
    for frag in fragment_paths:
        frag_escaped = os.path.abspath(frag).replace("'", "'\\''")
        f.write(f"file '{frag_escaped}'\n")

cmd = [
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", CONCAT,
    "-c", "copy",
    VIDEO
]

result = subprocess.run(cmd)

if result.returncode != 0:
    raise SystemExit("FFmpeg parçaları birleştiremedi.")

shutil.rmtree(FRAGMENTS_DIR, ignore_errors=True)

print()
print("================================")
print("✅ SHORTS DİKEY GÖRSELLİ/VİDEOLU (KESİN SENKRON)")
print("================================")
print("Dosya:", VIDEO)
print("Sahne:", len(sequence))
print("Ses hedefi:", round(voice_duration, 2), "sn")
print("================================")
