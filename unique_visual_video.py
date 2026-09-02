import os
import json
import subprocess
import shutil
import hashlib

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

MANIFEST = os.path.join(OUT, "visual_manifest.json")
VOICE = os.path.join(OUT, "einstein_voice.wav")
CONCAT = os.path.join(OUT, "unique_visuals.txt")
VIDEO = os.path.join(OUT, "einstein_unique.mp4")
FRAGMENTS_DIR = os.path.join(OUT, "video_fragments")

SCENE_DURATION = 7  # saniye - her görsel tam 7 saniyede bir değişir


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


shutil.rmtree(FRAGMENTS_DIR, ignore_errors=True)
os.makedirs(FRAGMENTS_DIR, exist_ok=True)

voice_cmd = [
    "ffprobe", "-v", "error",
    "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1",
    VOICE
]

voice_duration = float(subprocess.check_output(voice_cmd).decode().strip())

with open(MANIFEST, encoding="utf-8") as f:
    manifest = json.load(f)

image_files = []
for item in manifest:
    path = item.get("file")
    if not path or not os.path.exists(path):
        continue
    image_files.append(path)

print("================================")
print("🧠 UZUN VİDEO GÖRSEL BİRLEŞTİRME MOTORU (SABİT 7 SN)")
print("================================")
print("Ses:", round(voice_duration, 2), "saniye")
print("Benzersiz görsel sayısı:", len(image_files))

if not image_files:
    raise SystemExit("Hiç kullanılabilir görsel yok.")

# Ses süresini tam olarak 7 saniyelik dilimlere böl.
# Görsel sayısı yetmezse baştan döngüye alınıp tekrar kullanılır,
# böylece "her 7 saniyede bir görsel değişsin" kuralı her zaman
# sağlanır.
num_scenes = max(1, int(voice_duration // SCENE_DURATION))
if voice_duration % SCENE_DURATION > 0.5:
    num_scenes += 1

sequence = [image_files[i % len(image_files)] for i in range(num_scenes)]
durations = [SCENE_DURATION for _ in sequence]

# Toplam süreyi tam ses süresine oturt (son sahneye farkı ekle).
toplam_fark = voice_duration - sum(durations)
durations[-1] = max(1.0, durations[-1] + toplam_fark)

print("Sahne sayısı (7 sn dilim):", len(sequence))
print("Toplam hedef süre:", round(sum(durations), 2), "saniye")
print()

fragment_paths = []

for idx, (path, duration) in enumerate(zip(sequence, durations), 1):
    frag_path = os.path.join(FRAGMENTS_DIR, f"frag_{idx:03d}.mp4")
    fps = 30
    frame_count = max(1, int(round(duration * fps)))

    # Ken Burns: yavaş yakınlaştırma efekti, statik fotoğrafa hareket katar.
    vf = (
        "scale=2400:-1,"
        f"zoompan=z='min(zoom+0.0006,1.08)':d={frame_count}:s=1920x1080:fps={fps},"
        "format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", path,
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-r", str(fps),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-an",
        frag_path
    ]

    print(f"[{idx}/{len(sequence)}] parça oluşturuluyor - {duration:.2f} sn")

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if result.returncode != 0 or not os.path.exists(frag_path):
        print(f"   ⚠️ Parça oluşturulamadı ({path}), bu sahne atlanıyor.")
        continue

    fragment_paths.append(frag_path)

if not fragment_paths:
    raise SystemExit("❌ Hiçbir parça oluşturulamadı.")

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
print("✅ UZUN VİDEO GÖRSEL BİRLEŞTİRME TAMAMLANDI")
print("================================")
print("Dosya:", VIDEO)
print("Sahne:", len(fragment_paths))
print("Ses hedefi:", round(voice_duration, 2), "sn")
print("================================")
