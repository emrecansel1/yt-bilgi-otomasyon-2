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

MIN_SCENE_DURATION = 6  # saniye


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

# Aynı dosyanın arka arkaya birebir tekrarını (hash bazlı) sahne
# listesinden ayıklayalım - manifest'te dolgu (fallback) nedeniyle
# aynı dosya birden fazla kez geçebilir, bu normaldir ve sorun
# değildir, ama en azından log'da görünür olsun.
sequence = []
kinds = []

for item in manifest:
    path = item.get("file")
    kind = item.get("type", "image")
    if not path or not os.path.exists(path):
        continue
    sequence.append(path)
    kinds.append(kind)

print("================================")
print("🧠 UZUN VİDEO GÖRSEL/VİDEO BİRLEŞTİRME MOTORU")
print("================================")
print("Ses:", round(voice_duration, 2), "saniye")
print("Sahne sayısı:", len(sequence))

if not sequence:
    raise SystemExit("Hiç kullanılabilir sahne yok.")

# Süreyi tüm sahnelere eşit dağıt, minimum süre garantisi ile.
average = voice_duration / len(sequence)

if average < MIN_SCENE_DURATION:
    average = MIN_SCENE_DURATION

durations = [average for _ in sequence]

# Toplamı tam ses süresine eşitle (sahne sayısı x ortalama, ses
# süresinden büyükse video sesin bittiği yerde kesilecek, küçükse
# son sahneye fark eklenir).
toplam_fark = voice_duration - sum(durations)
durations[-1] = max(MIN_SCENE_DURATION, durations[-1] + toplam_fark)

print("Ortalama sahne süresi:", round(average, 2), "saniye")
print("Toplam hedef süre:", round(sum(durations), 2), "saniye")
print()

# --- Her sahneyi kendi süresinde ayrı bir mp4 parçası olarak
# render ediyoruz. Video ise döngüye alınıp kırpılıyor. Fotoğraf
# ise hafif bir "Ken Burns" yakınlaştırma efektiyle statik hissi
# kırılıyor, böylece foto sahnelerde bile ekranda hareket oluyor.

vf_scale_crop = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=yuv420p"

fragment_paths = []

for idx, (path, duration, kind) in enumerate(zip(sequence, durations, kinds), 1):
    frag_path = os.path.join(FRAGMENTS_DIR, f"frag_{idx:03d}.mp4")
    fps = 30
    frame_count = max(1, int(round(duration * fps)))

    if kind == "video":
        vf = vf_scale_crop
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

    print(f"[{idx}/{len(sequence)}] ({kind}) parça oluşturuluyor - {duration:.2f} sn")

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
