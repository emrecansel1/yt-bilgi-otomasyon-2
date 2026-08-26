import os
import subprocess
import sys
import re
import json

PIPER_VOICE_PATH = os.environ.get("PIPER_VOICE_PATH", ".")
MODEL = os.path.join(PIPER_VOICE_PATH, "tr_TR-dfki-medium.onnx")

SILENCE_BETWEEN_SCENES = 0.25  # cümleler arası doğal duraklama (sn)


def clean_text(text):
    bad_patterns = [
        r'(?im)^.*seslendirme metni.*$',
        r'(?im)^.*metadata.*$',
        r'(?im)^.*senaryo.*$',
        r'(?im)^.*başlık\s*:.*$',
        r'(?im)^.*açıklama\s*:.*$',
        r'(?im)^.*etiketler\s*:.*$',
        r'(?im)^.*tags\s*:.*$',
        r'(?im)^.*title\s*:.*$',
        r'(?im)^.*description\s*:.*$',
        r'(?im)^.*kamera.*$',
        r'(?im)^.*müzik.*$',
        r'(?im)^.*ses efekti.*$',
        r'(?im)^.*sahne\s*\d*.*$',
        r'(?im)^.*scene\s*\d*.*$',
        r'(?im)^.*görsel\s*:.*$',
        r'(?im)^.*görüntü\s*:.*$',
        r'(?im)^.*yönetmen.*$',
    ]

    for pattern in bad_patterns:
        text = re.sub(pattern, '', text)

    text = re.sub(r'\[[^\]]*\]', ' ', text)
    text = re.sub(r'\([^)]*\)', ' ', text)
    text = re.sub(r'\{[^}]*\}', ' ', text)
    text = re.sub(r'[*_`~#]+', ' ', text)
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n+', ' ', text)

    return text.strip()


def split_scenes(text):
    text = re.sub(r'\s+', ' ', text).strip()

    sentences = re.split(r'(?<=[.!?])\s+', text)

    scenes = [
        s.strip()
        for s in sentences
        if len(s.strip()) >= 15
    ]

    return scenes


def get_wav_duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ])
    return float(out.decode().strip())


def get_wav_params(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate,channels",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]).decode().strip().splitlines()

    sample_rate = out[0] if len(out) > 0 else "22050"
    channels = out[1] if len(out) > 1 else "1"

    return sample_rate, channels


def synth_piper(piper, text, output_wav):
    subprocess.run(
        [
            piper,
            "-m", MODEL,
            "-f", output_wav
        ],
        input=text + "\n",
        text=True,
        check=True
    )


def create_voice(text_file, output_wav):
    if not os.path.isfile(text_file):
        raise FileNotFoundError(f"Senaryo bulunamadı: {text_file}")

    if not os.path.isfile(MODEL):
        raise FileNotFoundError(f"Piper modeli bulunamadı: {MODEL}")

    piper = os.environ.get("PIPER_BIN", "/opt/piper/piper")

    if not os.path.isfile(piper):
        raise FileNotFoundError(f"Piper bulunamadı: {piper}")

    with open(text_file, "r", encoding="utf-8") as f:
        raw = clean_text(f.read())

    if not raw:
        raise RuntimeError("Temizleme sonrası seslendirilecek metin kalmadı.")

    scenes = split_scenes(raw)

    if not scenes:
        scenes = [raw]

    print("🎙️ Piper Türkçe ses oluşturuyor (cümle cümle)...")
    print("🧩 Sahne sayısı:", len(scenes))
    print("🤖 Model:", MODEL)
    print("🔧 Piper:", piper)

    out_dir = os.path.dirname(os.path.abspath(output_wav))
    os.makedirs(out_dir, exist_ok=True)

    tmp_dir = os.path.join(out_dir, "_voice_scenes_tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    for f in os.listdir(tmp_dir):
        try:
            os.remove(os.path.join(tmp_dir, f))
        except:
            pass

    scene_files = []
    scene_durations = []

    for i, scene_text in enumerate(scenes, 1):
        scene_wav = os.path.join(tmp_dir, f"scene_{i:03d}.wav")

        print(f"   [{i}/{len(scenes)}] seslendiriliyor: {scene_text[:60]}")

        synth_piper(piper, scene_text, scene_wav)

        duration = get_wav_duration(scene_wav)

        scene_files.append(scene_wav)
        scene_durations.append({
            "scene": i,
            "text": scene_text,
            "duration": round(duration, 3)
        })

    # Sahneler arasına küçük sessizlik ekle (doğal duraklama)
    sample_rate, channels = get_wav_params(scene_files[0])

    silence_wav = os.path.join(tmp_dir, "silence.wav")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r={sample_rate}:cl=mono" if channels == "1"
                  else f"anullsrc=r={sample_rate}:cl=stereo",
            "-t", str(SILENCE_BETWEEN_SCENES),
            silence_wav
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    concat_list = os.path.join(tmp_dir, "concat_list.txt")

    with open(concat_list, "w", encoding="utf-8") as f:
        for i, scene_wav in enumerate(scene_files):
            path = os.path.abspath(scene_wav).replace("'", "'\\''")
            f.write(f"file '{path}'\n")

            if i < len(scene_files) - 1:
                silence_path = os.path.abspath(silence_wav).replace("'", "'\\''")
                f.write(f"file '{silence_path}'\n")
                # araya giren sessizlik süresini bir önceki sahnenin süresine ekle
                scene_durations[i]["duration"] = round(
                    scene_durations[i]["duration"] + SILENCE_BETWEEN_SCENES, 3
                )

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            output_wav
        ],
        check=True
    )

    if not os.path.isfile(output_wav) or os.path.getsize(output_wav) == 0:
        raise RuntimeError("Piper WAV dosyası oluşturamadı.")

    print("🔊 WAV kontrolü...")

    subprocess.run(
        ["ffprobe", "-v", "error", output_wav],
        check=True
    )

    durations_file = os.path.join(out_dir, "shorts_scene_durations.json")

    with open(durations_file, "w", encoding="utf-8") as f:
        json.dump(scene_durations, f, ensure_ascii=False, indent=2)

    print(f"✅ Ses hazır: {output_wav}")
    print(f"✅ Sahne süreleri kaydedildi: {durations_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Kullanım: python voiceover.py senaryo.txt ses.wav")
        sys.exit(1)

    create_voice(sys.argv[1], sys.argv[2])
