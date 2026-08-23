#!/data/data/com.termux/files/usr/bin/bash

cd ~/yt_bilgi_uzun || exit 1

while true
do
    echo "================================"
    echo "🚀 YENİ OTOMATİK VİDEO BAŞLIYOR"
    echo "🕒 $(date)"
    echo "================================"

    if python auto_video.py; then
        echo "================================"
        echo "📤 VİDEO HAZIR — YOUTUBE'A YÜKLENİYOR"
        echo "🕒 $(date)"
        echo "================================"

        if python upload_youtube.py; then
            echo "================================"
            echo "✅ VİDEO YOUTUBE'A YÜKLENDİ"
            echo "🕒 $(date)"
            echo "================================"
        else
            echo "❌ YOUTUBE YÜKLEME BAŞARISIZ"
        fi
    else
        echo "❌ VİDEO OLUŞTURMA BAŞARISIZ"
    fi

    echo "================================"
    echo "⏳ 3 SAAT BEKLENİYOR..."
    echo "================================"

    sleep 10800
done
