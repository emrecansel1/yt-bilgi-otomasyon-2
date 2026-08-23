import os
import subprocess

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")

voice = os.path.join(OUT, "einstein_voice.wav")
video = os.path.join(OUT, "einstein_video.mp4")

if not os.path.exists(voice):
    raise SystemExit("Ses dosyasi bulunamadi: " + voice)

print("🎬 1920x1080 video oluşturuluyor...")

cmd = [
    "ffmpeg", "-y",
    "-f", "lavfi",
    "-i", "color=c=black:s=1920x1080:r=30",
    "-i", voice,
    "-map", "0:v",
    "-map", "1:a",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "23",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "128k",
    "-shortest",
    "-movflags", "+faststart",
    video
]

subprocess.run(cmd, check=True)

print("================================")
print("✅ VIDEO HAZIR")
print(video)
print("================================")
