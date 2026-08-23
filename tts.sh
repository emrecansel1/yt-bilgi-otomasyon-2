#!/data/data/com.termux/files/usr/bin/bash

set -e

BASE="$HOME/yt_bilgi_uzun"
MODEL="tr_TR-dfki-medium"
export PIPER_VOICE_PATH="$BASE/models"

TEXT_FILE="$1"
OUTPUT_FILE="$2"

if [ -z "$TEXT_FILE" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Kullanim: ./tts.sh metin.txt ses.wav"
    exit 1
fi

if [ ! -f "$TEXT_FILE" ]; then
    echo "HATA: Metin dosyasi bulunamadi: $TEXT_FILE"
    exit 1
fi

piper \
    -m "$MODEL" \
    -i "$TEXT_FILE" \
    -f "$OUTPUT_FILE"

ffmpeg -y \
    -f f32le \
    -ar 22050 \
    -ac 1 \
    -i "$OUTPUT_FILE" \
    -c:a pcm_s16le \
    "${OUTPUT_FILE%.wav}.converted.wav" \
    >/dev/null 2>&1

mv "${OUTPUT_FILE%.wav}.converted.wav" "$OUTPUT_FILE"

echo "TTS TAMAM: $OUTPUT_FILE"
