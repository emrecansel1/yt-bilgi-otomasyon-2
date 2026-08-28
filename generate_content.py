import os
import json
import requests
import re
import time
import random

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")
REPO_BASE = os.path.dirname(os.path.abspath(__file__))

# ================================
# API ANAHTARLARI
# ================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY bulunamadı.")

if not CEREBRAS_API_KEY:
    print("⚠️ CEREBRAS_API_KEY bulunamadı.")

if not GROQ_API_KEY:
    print("⚠️ GROQ_API_KEY bulunamadı.")

# ================================
# DOSYALAR
# ================================

TOPIC_FILE = os.path.join(OUT, "current_topic.txt")
TOPIC_HISTORY_FILE = os.path.join(REPO_BASE, "video_topic_history.json")
OUTPUT_FILE = os.path.join(OUT, "current_content.txt")

# ================================
# API ADRESLERİ
# ================================

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.6-flash:generateContent"
)

CEREBRAS_URL = (
    "https://api.cerebras.ai/v1/chat/completions"
)

GROQ_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

# ================================
# MODELLER
# ================================

CEREBRAS_MODEL = "llama-3.3-70b"

GROQ_MODEL = "openai/gpt-oss-120b"

# ================================
# GENEL AYARLAR
# ================================

MAX_HISTORY = 30

# 15 dakikalık video
BOLUM_SAYISI = 2
BOLUM_BASINA_KELIME = 1100

METADATA_AYIRICI = "===METADATA_AYIRICI==="

# ================================
# ANLATIM KURALLARI
# ================================

NARRATION_KURALLARI = """
KURALLAR:
1. Bilgi uydurma.
2. Tarihleri ve olayları mümkün olduğunca doğru aktar.
3. Doğrulanamayan bilgileri kesin gerçek gibi sunma.
4. Doğal, ciddi ve profesyonel Türkçe belgesel anlatımı kullan.
5. Gereksiz tekrar yapma.
6. Konuyu mantıklı bir akışla anlat.
7. Bilimsel konuları herkesin anlayabileceği şekilde açıkla.
8. Önemli kişiler, tarihler, yerler ve olaylara yer ver.
9. Metin doğrudan TTS sistemine gönderilecek.

ÖNEMLİ:
Bu bir film senaryosu değildir.
Sahne yazma.
Kamera hareketi yazma.
Karakter hareketi yazma.
Müzik veya ses efekti yazma.
Parantez veya köşeli parantez kullanma.

"[Hüzünlü müzik]", "(kamera yaklaşır)", "Sahne 1",
"Bölüm 1" gibi ifadeler kesinlikle yazma.

İzleyici bölümlere ayrıldığını fark etmemeli.
Anlatım kesintisiz tek bir belgesel akışı gibi hissettirmeli.

Sadece seçilen konuyu doğrudan anlat.
Metin doğrudan TTS sistemine gönderileceği için
okuyucu yalnızca gerçek anlatım cümlelerini görmelidir.
"""
