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

SCENE_DURATION = 7  # saniye - her görsel/video tam 7 saniyede bir değişir

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

visual_items = []
for item in manifest:
    path = item.get("file")
    if not path or not os.path.exists(path):
        continue
    visual_items.append((path, item.get("type", "image")))

print("================================")
print("🧠 UZUN VİDEO GÖRSEL/VİDEO BİRLEŞTİRME MOTORU (SABİT 7 SN)")
print("================================")
print("Ses:", round(voice_duration, 2), "saniye")
print("Benzersiz içerik sayısı:", len(visual_items))

if not visual_items:
    raise SystemExit("Hiç kullanılabilir görsel/video yok.")

# Ses süresini tam olarak 7 saniyelik dilimlere böl.
# İçerik sayısı yetmezse baştan döngüye alınıp tekrar kullanılır,
# böylece "her 7 saniyede bir görsel/video değişsin" kuralı her
# zaman sağlanır.
num_scenes = max(1, int(voice_duration // SCENE_DURATION))
if voice_duration % SCENE_DURATION > 0.5:
    num_scenes += 1

sequence = [visual_items[i % len(visual_items)] for i in range(num_scenes)]
durations = [SCENE_DURATION for _ in sequence]

# Toplam süreyi tam ses süresine oturt (son sahneye farkı ekle).
toplam_fark = voice_duration - sum(durations)
durations[-1] = max(1.0, durations[-1] + toplam_fark)

print("Sahne sayısı (7 sn dilim):", len(sequence))
print("Toplam hedef süre:", round(sum(durations), 2), "saniye")
print()

fragment_paths = []

for idx, ((path, vtype), duration) in enumerate(zip(sequence, durations), 1):
    frag_path = os.path.join(FRAGMENTS_DIR, f"frag_{idx:03d}.mp4")
    fps = 30

    if vtype == "video":
        # Gerçek video klibi: kırp/ölçekle, gerekirse döngüye al.
        vf = (
            "scale=1920:1080:force_original_aspect_ratio=increase,"
            "crop=1920:1080,format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
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
    else:
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

    print(f"[{idx}/{len(sequence)}] parça oluşturuluyor ({vtype}) - {duration:.2f} sn")

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
print("✅ UZUN VİDEO GÖRSEL/VİDEO BİRLEŞTİRME TAMAMLANDI")
print("================================")
print("Dosya:", VIDEO)
print("Sahne:", len(fragment_paths))
print("Ses hedefi:", round(voice_duration, 2), "sn")
print("================================")
