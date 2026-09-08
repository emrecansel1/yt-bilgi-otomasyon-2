import os
import sys
import json
import re
import time
import random
import requests
from datetime import datetime

# =========================================================
# DİZİNLER
# =========================================================

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")
REPO_BASE = os.path.dirname(os.path.abspath(__file__))

os.makedirs(OUT, exist_ok=True)

TOPIC_FILE = os.path.join(OUT, "current_topic.txt")
TOPIC_HISTORY_FILE = os.path.join(
    REPO_BASE,
    "video_topic_history.json"
)
OUTPUT_FILE = os.path.join(
    OUT,
    "current_content.txt"
)

# =========================================================
# API ANAHTARLARI
# =========================================================

GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY",
    ""
).strip()

CEREBRAS_API_KEY = os.environ.get(
    "CEREBRAS_API_KEY",
    ""
).strip()

NVIDIA_API_KEY = os.environ.get(
    "NVIDIA_API_KEY",
    ""
).strip()

print("================================")
print("🔐 API KONTROLÜ")
print("================================")

if GEMINI_API_KEY:
    print("✅ GEMINI_API_KEY mevcut.")
else:
    print("⚠️ GEMINI_API_KEY bulunamadı.")

if CEREBRAS_API_KEY:
    print("✅ CEREBRAS_API_KEY mevcut.")
else:
    print("⚠️ CEREBRAS_API_KEY bulunamadı.")

if NVIDIA_API_KEY:
    print("✅ NVIDIA_API_KEY mevcut.")
else:
    print("⚠️ NVIDIA_API_KEY bulunamadı.")

print("================================")
print()

# =========================================================
# API URL + MODEL
# =========================================================

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.6-flash:generateContent"
)

CEREBRAS_URL = (
    "https://api.cerebras.ai/v1/chat/completions"
)

CEREBRAS_MODEL = "llama-3.3-70b"

NVIDIA_URL = (
    "https://integrate.api.nvidia.com/v1/chat/completions"
)

# ESKİ:
# meta/llama-3.3-70b-instruct
#
# YENİ:
NVIDIA_MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1.5"

# =========================================================
# BELGESEL AYARLARI
# =========================================================

BOLUM_SAYISI = 5
BOLUM_BASINA_KELIME = 1100
TOPLAM_HEDEF_KELIME = (
    BOLUM_SAYISI * BOLUM_BASINA_KELIME
)

METADATA_AYIRICI = "===METADATA_AYIRICI==="

# =========================================================
# ÖRNEK KONULAR
# =========================================================

ORNEK_KONULAR = """
- Semmelweis'in el yıkama önerisi yüzünden tıp dünyası tarafından reddedilmesi
- Nikola Tesla'nın sefalet ve yalnızlık içinde geçen son yılları
- Alan Turing'in savaşı kazandırıp sonrasında toplum tarafından dışlanması
- Rosalind Franklin'in DNA keşfindeki katkısının gölgede kalması
- Marie Curie'nin radyasyon araştırmalarının ağır bedeli
- Ludwig Boltzmann'ın bilim dünyası tarafından dışlanması
- Barbara McClintock'un keşfinin yıllarca kabul edilmemesi
- Galileo'nun fikirleri nedeniyle yargılanması
- Giordano Bruno'nun düşünceleri nedeniyle idam edilmesi
- Évariste Galois'nın genç yaşta trajik ölümü
- Vera Rubin'in karanlık madde çalışmalarının uzun süre yeterince tanınmaması
- Jocelyn Bell Burnell'in pulsar keşfindeki rolünün gölgede kalması
- Emmy Noether'in kadın olduğu için akademide karşılaştığı engeller
- Ada Lovelace'in çalışmalarının yıllar sonra anlaşılması
- Katherine Johnson'un NASA'daki olağanüstü bilimsel kariyeri
- Srinivasa Ramanujan'ın kısa ve zorlu hayatı
- Kurt Gödel'in hayatının son dönemindeki yalnızlığı
- Antoine Lavoisier'nin bilimsel başarıları ve trajik sonu
- Chien-Shiung Wu'nun fizik tarihindeki büyük deneysel katkıları
- Lise Meitner'in nükleer fisyonun anlaşılmasındaki rolü
"""

# =========================================================
# TTS KURALLARI
# =========================================================

NARRATION_KURALLARI = """
KURALLAR:

1. Bilgi uydurma.
2. Tarihleri ve olayları mümkün olduğunca doğru aktar.
3. Emin olunmayan bilgileri kesin gerçek gibi sunma.
4. Doğal, ciddi ve profesyonel Türkçe belgesel anlatımı kullan.
5. Gereksiz tekrar yapma.
6. Konuyu mantıklı ve kronolojik bir akışla anlat.
7. Bilimsel konuları herkesin anlayabileceği şekilde açıkla.
8. Önemli kişiler, tarihler, yerler ve olaylara yer ver.
9. Metin doğrudan TTS sistemine gönderilecek.
10. Film senaryosu gibi yazma.
11. Sahne numarası yazma.
12. Kamera hareketi yazma.
13. Müzik veya ses efekti yazma.
14. Parantez kullanma.
15. Köşeli parantez kullanma.
16. "Bölüm 1", "Sahne 1" gibi ifadeler kullanma.
17. İzleyici bölümlere ayrıldığını hissetmemeli.
18. Anlatım kesintisiz bir belgesel akışı gibi ilerlemeli.
19. Sadece seçilen konuyu anlat.
20. Metin doğrudan seslendirme sistemine gideceği için
    yalnızca anlatıcı tarafından okunabilecek cümleler yaz.
"""

# =========================================================
# GENEL HTTP YARDIMCISI
# =========================================================

def safe_json(response):
    try:
        return response.json()
    except Exception:
        return None


def print_response_error(service, response):
    print(
        f"❌ {service} HTTP {response.status_code}"
    )

    text = response.text.strip()

    if text:
        print(
            f"📥 {service} hata cevabı:"
        )
        print(text[:3000])


# =========================================================
# GEMINI
# =========================================================

def call_gemini(prompt):
    if not GEMINI_API_KEY:
        print("❌ Gemini anahtarı yok.")
        return None

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    # Gemini'de 429 için uzun retry yapmıyoruz.
    # Çünkü yedek sistemlerin amacı hızlı fallback.
    max_retries = 2

    for attempt in range(1, max_retries + 1):

        print(
            f"🤖 Gemini isteği "
            f"{attempt}/{max_retries}"
        )

        try:
            response = requests.post(
                GEMINI_URL,
                params={
                    "key": GEMINI_API_KEY
                },
                headers=headers,
                json=payload,
                timeout=180
            )

            print(
                "Gemini HTTP:",
                response.status_code
            )

            if response.ok:

                data = safe_json(response)

                if not data:
                    print(
                        "❌ Gemini JSON cevabı alınamadı."
                    )
                    return None

                try:
                    text = (
                        data[
                            "candidates"
                        ][0][
                            "content"
                        ][
                            "parts"
                        ][0][
                            "text"
                        ]
                    )

                    if text and text.strip():
                        return text.strip()

                except (
                    KeyError,
                    IndexError,
                    TypeError
                ):
                    print(
                        "❌ Gemini cevabı beklenen "
                        "formatta değil."
                    )

                    print(
                        json.dumps(
                            data,
                            ensure_ascii=False,
                            indent=2
                        )[:3000]
                    )

                    return None

            # -------------------------------------------------
            # 429
            # -------------------------------------------------

            if response.status_code == 429:

                print(
                    "⚠️ Gemini 429: "
                    "kota veya hız limiti."
                )

                print(
                    "➡️ Gemini bırakılıyor, "
                    "Cerebras fallback devreye girecek."
                )

                return None

            # -------------------------------------------------
            # Geçici sunucu hataları
            # -------------------------------------------------

            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                if attempt < max_retries:

                    wait_time = (
                        4 * attempt
                        + random.randint(1, 3)
                    )

                    print(
                        f"⏳ Gemini geçici hata. "
                        f"{wait_time} saniye bekleniyor..."
                    )

                    time.sleep(wait_time)
                    continue

                return None

            # -------------------------------------------------
            # Diğer hatalar
            # -------------------------------------------------

            print_response_error(
                "Gemini",
                response
            )

            return None

        except requests.exceptions.Timeout:

            print(
                "⚠️ Gemini timeout."
            )

            if attempt < max_retries:
                time.sleep(4)
                continue

            return None

        except requests.exceptions.RequestException as e:

            print(
                "⚠️ Gemini ağ hatası:",
                str(e)
            )

            if attempt < max_retries:
                time.sleep(4)
                continue

            return None

    return None


# =========================================================
# CEREBRAS
# =========================================================

def call_cerebras(prompt):
    if not CEREBRAS_API_KEY:
        print(
            "❌ CEREBRAS_API_KEY yok."
        )
        return None

    headers = {
        "Authorization": (
            f"Bearer {CEREBRAS_API_KEY}"
        ),
        "Content-Type": "application/json"
    }

    payload = {
        "model": CEREBRAS_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sen profesyonel Türkçe "
                    "tarih ve bilim belgeseli "
                    "yazarı olarak görev yapıyorsun."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 12000
    }

    # 401 kesin hatadır.
    # İkinci kez aynı hatayı üretmenin anlamı yok.
    max_retries = 2

    for attempt in range(1, max_retries + 1):

        print(
            f"🟢 Cerebras isteği "
            f"{attempt}/{max_retries}"
        )

        try:

            response = requests.post(
                CEREBRAS_URL,
                headers=headers,
                json=payload,
                timeout=180
            )

            print(
                "Cerebras HTTP:",
                response.status_code
            )

            if response.ok:

                data = safe_json(response)

                if not data:
                    print(
                        "❌ Cerebras JSON cevabı yok."
                    )
                    return None

                try:

                    text = (
                        data[
                            "choices"
                        ][0][
                            "message"
                        ][
                            "content"
                        ]
                    )

                    if text and text.strip():
                        return text.strip()

                except (
                    KeyError,
                    IndexError,
                    TypeError
                ):

                    print(
                        "❌ Cerebras cevabı "
                        "beklenen formatta değil."
                    )

                    print(
                        json.dumps(
                            data,
                            ensure_ascii=False,
                            indent=2
                        )[:3000]
                    )

                    return None

            # -------------------------------------------------
            # 401
            # -------------------------------------------------

            if response.status_code == 401:

                print(
                    "❌ Cerebras API key geçersiz."
                )

                print(
                    "ℹ️ GitHub Secrets → "
                    "CEREBRAS_API_KEY kontrol edilmeli."
                )

                return None

            # -------------------------------------------------
            # 429
            # -------------------------------------------------

            if response.status_code == 429:

                print(
                    "⚠️ Cerebras 429 / kota."
                )

                if attempt < max_retries:

                    wait_time = (
                        8 * attempt
                    )

                    print(
                        f"⏳ {wait_time} saniye bekleniyor..."
                    )

                    time.sleep(wait_time)
                    continue

                return None

            # -------------------------------------------------
            # Geçici hatalar
            # -------------------------------------------------

            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                if attempt < max_retries:

                    time.sleep(
                        5 * attempt
                    )

                    continue

                return None

            print_response_error(
                "Cerebras",
                response
            )

            return None

        except requests.exceptions.Timeout:

            print(
                "⚠️ Cerebras timeout."
            )

            if attempt < max_retries:
                time.sleep(5)
                continue

            return None

        except requests.exceptions.RequestException as e:

            print(
                "⚠️ Cerebras ağ hatası:",
                str(e)
            )

            if attempt < max_retries:
                time.sleep(5)
                continue

            return None

    return None


# =========================================================
# NVIDIA NIM
# =========================================================

def call_nvidia(prompt):
    if not NVIDIA_API_KEY:
        print(
            "❌ NVIDIA_API_KEY yok."
        )
        return None

    headers = {
        "Authorization": (
            f"Bearer {NVIDIA_API_KEY}"
        ),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "model": NVIDIA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sen profesyonel Türkçe "
                    "tarih ve bilim belgeseli "
                    "yazarı olarak görev yapıyorsun."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,

        # NVIDIA'nın güncel Nemotron Super
        # endpoint'i 16384'e kadar destekliyor.
        "max_tokens": 12000,

        "stream": False
    }

    max_retries = 2

    for attempt in range(1, max_retries + 1):

        print(
            f"🟩 NVIDIA isteği "
            f"{attempt}/{max_retries}"
        )

        print(
            "🧠 NVIDIA model:",
            NVIDIA_MODEL
        )

        try:

            response = requests.post(
                NVIDIA_URL,
                headers=headers,
                json=payload,
                timeout=300
            )

            print(
                "NVIDIA HTTP:",
                response.status_code
            )

            # -------------------------------------------------
            # 200
            # -------------------------------------------------

            if response.status_code == 200:

                data = safe_json(response)

                if not data:
                    print(
                        "❌ NVIDIA JSON cevabı yok."
                    )
                    return None

                try:

                    text = (
                        data[
                            "choices"
                        ][0][
                            "message"
                        ][
                            "content"
                        ]
                    )

                    if text and text.strip():
                        return text.strip()

                except (
                    KeyError,
                    IndexError,
                    TypeError
                ):

                    print(
                        "❌ NVIDIA cevabı "
                        "beklenen formatta değil."
                    )

                    print(
                        json.dumps(
                            data,
                            ensure_ascii=False,
                            indent=2
                        )[:3000]
                    )

                    return None

            # -------------------------------------------------
            # 202
            # -------------------------------------------------

            if response.status_code == 202:

                print(
                    "⏳ NVIDIA isteği 202 döndürdü."
                )

                data = safe_json(response)

                if data:

                    request_id = (
                        data.get("requestId")
                        or data.get("request_id")
                    )

                    if request_id:
                        print(
                            "ℹ️ NVIDIA requestId:",
                            request_id
                        )

                print(
                    "⚠️ Bu çalışma için "
                    "asenkron NVIDIA cevabı "
                    "alınamadı."
                )

                return None

            # -------------------------------------------------
            # 401
            # -------------------------------------------------

            if response.status_code == 401:

                print(
                    "❌ NVIDIA API key geçersiz."
                )

                return None

            # -------------------------------------------------
            # 404
            # -------------------------------------------------

            if response.status_code == 404:

                print(
                    "❌ NVIDIA model/endpoint bulunamadı."
                )

                print_response_error(
                    "NVIDIA",
                    response
                )

                return None

            # -------------------------------------------------
            # 410
            # -------------------------------------------------

            if response.status_code == 410:

                print(
                    "❌ NVIDIA modeli artık kullanılamıyor."
                )

                print(
                    "🧠 Kullanılan model:",
                    NVIDIA_MODEL
                )

                print_response_error(
                    "NVIDIA",
                    response
                )

                return None

            # -------------------------------------------------
            # 429
            # -------------------------------------------------

            if response.status_code == 429:

                print(
                    "⚠️ NVIDIA 429 / kota."
                )

                if attempt < max_retries:

                    wait_time = (
                        10 * attempt
                    )

                    print(
                        f"⏳ {wait_time} saniye bekleniyor..."
                    )

                    time.sleep(wait_time)
                    continue

                return None

            # -------------------------------------------------
            # Geçici sunucu hataları
            # -------------------------------------------------

            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                if attempt < max_retries:

                    wait_time = (
                        5 * attempt
                    )

                    print(
                        f"⏳ NVIDIA geçici hata. "
                        f"{wait_time} saniye bekleniyor..."
                    )

                    time.sleep(wait_time)
                    continue

                return None

            print_response_error(
                "NVIDIA",
                response
            )

            return None

        except requests.exceptions.Timeout:

            print(
                "⚠️ NVIDIA timeout."
            )

            if attempt < max_retries:

                print(
                    "⏳ NVIDIA tekrar deneniyor..."
                )

                time.sleep(6)
                continue

            print(
                "❌ NVIDIA timeout retry limiti doldu."
            )

            return None

        except requests.exceptions.RequestException as e:

            print(
                "⚠️ NVIDIA ağ hatası:",
                str(e)
            )

            if attempt < max_retries:
                time.sleep(6)
                continue

            return None

    return None


# =========================================================
# ANA AI FALLBACK
# =========================================================

def call_ai(prompt):

    # =====================================================
    # 1 — GEMINI
    # =====================================================

    if GEMINI_API_KEY:

        print()
        print("================================")
        print("🤖 ANA SİSTEM: GEMINI")
        print("================================")

        result = call_gemini(prompt)

        if result:

            print(
                "✅ İçerik Gemini tarafından üretildi."
            )

            return result

    else:

        print(
            "⚠️ Gemini anahtarı yok."
        )

    # =====================================================
    # 2 — CEREBRAS
    # =====================================================

    print()
    print("================================")
    print("⚠️ GEMINI BAŞARISIZ")
    print("🟢 CEREBRAS YEDEK SİSTEM DEVREDE")
    print("================================")

    if CEREBRAS_API_KEY:

        result = call_cerebras(prompt)

        if result:

            print(
                "✅ İçerik Cerebras tarafından üretildi."
            )

            return result

    else:

        print(
            "⚠️ Cerebras API key yok."
        )

    # =====================================================
    # 3 — NVIDIA
    # =====================================================

    print()
    print("================================")
    print("⚠️ CEREBRAS BAŞARISIZ")
    print("🟩 NVIDIA YEDEK SİSTEM DEVREDE")
    print("================================")

    if NVIDIA_API_KEY:

        result = call_nvidia(prompt)

        if result:

            print(
                "✅ İçerik NVIDIA tarafından üretildi."
            )

            return result

    else:

        print(
            "⚠️ NVIDIA API key yok."
        )

    # =====================================================
    # HEPSİ BAŞARISIZ
    # =====================================================

    raise RuntimeError(
        "Gemini, Cerebras ve NVIDIA "
        "başarılı bir cevap veremedi."
    )


# =========================================================
# HISTORY
# =========================================================

def load_history():

    if not os.path.exists(
        TOPIC_HISTORY_FILE
    ):
        return []

    try:

        with open(
            TOPIC_HISTORY_FILE,
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, list):
                return data

            return []

    except Exception as e:

        print(
            "⚠️ Konu geçmişi okunamadı:",
            str(e)
        )

        return []


def save_history(history):

    try:

        with open(
            TOPIC_HISTORY_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                history,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:

        print(
            "⚠️ Konu geçmişi kaydedilemedi:",
            str(e)
        )


# =========================================================
# KONU VALIDASYONU
# =========================================================

def is_valid_topic(topic):

    if not topic:
        return False

    topic = topic.strip()

    if len(topic) < 8:
        return False

    if len(topic) > 220:
        return False

    if len(topic.split()) < 2:
        return False

    if not re.search(
        r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}",
        topic
    ):
        return False

    return True


# =========================================================
# KONU + PLAN
# =========================================================

def generate_topic_and_outline(history):

    if history:

        avoid_list = "\n".join(
            f"- {t}"
            for t in history[-100:]
        )

    else:

        avoid_list = "(henüz yok)"

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe
bilgi/tarih/bilim YouTube kanalı için
30-45 dakikalık belgeseller hazırlayan
profesyonel editör ve araştırma yazarı olarak
görev yapıyorsun.

KANAL NİŞİ:

Kanal yalnızca bilim insanlarının,
mucitlerin ve kaşiflerin gerçek,
insani ve dramatik hikayelerine odaklanır.

Kuru bilgi anlatımı istemiyorum.

Hikayede mümkün olduğunca:

mücadele,
haksızlık,
yalnızlık,
reddedilme,
başarısızlık,
geç gelen tanınma,
bilimsel mücadele,
kişisel bedel,
trajedi
ve sonunda etkileyici bir sonuç

bulunmalıdır.

Ancak dramatik etki oluşturmak için
gerçek dışı olay uydurmak kesinlikle yasaktır.

ÖRNEK KONU TARZLARI:

{ORNEK_KONULAR}

DAHA ÖNCE KULLANILAN KONULAR:

{avoid_list}

Yeni ve farklı bir konu seç.

Konu:

- Gerçek bir bilim insanı,
  mucit veya kaşif hakkında olmalı.
- Gerçek ve doğrulanabilir olmalı.
- 30-45 dakikalık anlatımı doldurabilecek
  kadar zengin olmalı.
- Tek bir olay yerine kişinin hayatı,
  çalışmaları ve yaşadığı mücadeleleri
  anlatmaya uygun olmalı.
- Diktatör veya savaş suçlusu seçme.
- Propaganda üretme.
- Sadece bilimsel keşif anlatısı seçme;
  kişinin insani hikayesi de güçlü olmalı.

Bu istekte:

1. Konuyu seç.
2. Beş bölümlük kronolojik plan oluştur.

Her bölüm yaklaşık
{BOLUM_BASINA_KELIME} kelimelik anlatımı
taşıyabilecek kadar kapsamlı olmalı.

ÇIKTI FORMATI:

KONU: <konu>

BÖLÜM 1: <başlık> - <özet>

BÖLÜM 2: <başlık> - <özet>

BÖLÜM 3: <başlık> - <özet>

BÖLÜM 4: <başlık> - <özet>

BÖLÜM 5: <başlık> - <özet>

Sadece düz metin kullan.
Markdown kullanma.
"""

    raw = call_ai(prompt)

    if not raw:
        return "", []

    topic = ""
    bolumler = []

    for line in raw.splitlines():

        line = line.strip()

        if not line:
            continue

        clean_line = (
            line
            .replace("*", "")
            .replace("#", "")
            .strip()
        )

        upper = clean_line.upper()

        if upper.startswith("KONU:"):

            topic = (
                clean_line
                .split(":", 1)[1]
                .strip()
            )

        elif (
            upper.startswith("BÖLÜM")
            or upper.startswith("BOLUM")
        ):

            bolumler.append(
                clean_line
            )

    topic = re.sub(
        r"\s+",
        " ",
        topic
    ).strip()

    topic = (
        topic
        .strip('"')
        .strip("'")
    )

    # AI 5 bölüm yerine daha az üretirse
    # ana sistemin çökmesini önlemek için
    # eldeki plan korunur.
    if topic and not bolumler:

        bolumler = [
            f"BÖLÜM {i}: "
            f"{topic} - "
            f"Konunun kronolojik anlatımı"
            for i in range(
                1,
                BOLUM_SAYISI + 1
            )
        ]

    print()
    print("---- AI KONU HAM ÇIKTI ----")
    print(raw[:2500])
    print("---------------------------")
    print(
        "🎯 Üretilen konu:",
        repr(topic)
    )
    print(
        "📚 Bölüm sayısı:",
        len(bolumler)
    )
    print("---------------------------")
    print()

    return topic, bolumler


# =========================================================
# BÖLÜM ÜRETİMİ
# =========================================================

def generate_chapter(
    topic,
    outline_text,
    chapter_line,
    chapter_index,
    total_chapters,
    previous_tail,
    need_metadata
):

    devamlilik = ""

    if previous_tail:

        devamlilik = f"""

ÖNCEKİ BÖLÜMÜN SON KISMI:

\"\"\"
{previous_tail}
\"\"\"

Yeni anlatımı buradan doğal biçimde
devam ettir.

Önceki bölümde anlatılan olayları
tekrar etme.
"""

    metadata_talimati = ""

    if need_metadata:

        metadata_talimati = f"""

BU SON BÖLÜM.

Anlatım bittikten sonra aşağıdaki ayırıcıyı
EKLE:

{METADATA_AYIRICI}

BAŞLIK:
Merak uyandırıcı fakat yanıltıcı olmayan
YouTube başlığı.

AÇIKLAMA:
3-5 cümlelik YouTube açıklaması.

ETİKETLER:
15-25 Türkçe etiket.
Virgülle ayır.
"""

    prompt = f"""
Sen DAHİLER VE KEŞİFLER adlı YouTube kanalı için
profesyonel Türkçe tarih ve bilim belgeseli
anlatıcısısın.

GENEL KONU:

{topic}

GENEL BÖLÜM PLANI:

{outline_text}

ŞU ANDA YAZILACAK BÖLÜM:

{chapter_line}

Bu bölüm yaklaşık
{BOLUM_BASINA_KELIME} kelime olmalıdır.

Amaç, toplamda yaklaşık
{TOPLAM_HEDEF_KELIME} kelimelik
30-45 dakikalık doğal bir belgesel oluşturmaktır.

ANLATIM TARZI:

Kişinin yalnızca bilimsel başarılarını değil,
insani tarafını da anlat.

Okuyucu;

mücadeleyi,
hayal kırıklığını,
haksızlığı,
umudu,
başarıyı
ve kişisel bedeli

hissedebilmeli.

Ancak duygusal etki oluşturmak için
gerçek dışı ayrıntı ekleme.

KRİTİK KURALLAR:

- Bilgi uydurma.
- Tarihleri mümkün olduğunca doğru aktar.
- Emin olunmayan bilgileri kesin gerçek gibi sunma.
- Doğal ve ciddi Türkçe kullan.
- Gereksiz tekrar yapma.
- Kronolojik akışı koru.
- Bilimsel kavramları sade anlat.
- Önemli isimlere ve tarihlere yer ver.
- Sahne yazma.
- Kamera hareketi yazma.
- Müzik yazma.
- Ses efekti yazma.
- Parantez kullanma.
- Köşeli parantez kullanma.
- "Bölüm 1" gibi başlıkları anlatımın
  içinde kullanma.
- İzleyici bölümlere ayrıldığını
  fark etmemeli.
- Çıktı doğrudan TTS'e gönderilecek.
- Yalnızca anlatıcının okuyacağı
  doğal cümleler üret.

{NARRATION_KURALLARI}

{devamlilik}

Şimdi sadece bu bölümün
belgesel anlatımını üret.

{metadata_talimati}
"""

    raw = call_ai(prompt)

    if not raw:
        return ""

    return raw.strip()


# =========================================================
# METADATA AYIRMA
# =========================================================

def parse_chapter_with_metadata(raw_text):

    if not raw_text:
        return "", None

    if METADATA_AYIRICI in raw_text:

        narration, metadata = (
            raw_text.split(
                METADATA_AYIRICI,
                1
            )
        )

        return (
            narration.strip(),
            metadata.strip()
        )

    return (
        raw_text.strip(),
        None
    )


# =========================================================
# DEFAULT METADATA
# =========================================================

def default_metadata(topic):

    safe_title = topic[:95].strip()

    return (
        "BAŞLIK:\n"
        f"{safe_title}\n\n"
        "AÇIKLAMA:\n"
        f"{topic} hakkında gerçek olaylara "
        "dayanan kapsamlı bir bilim ve tarih "
        "belgeseli.\n\n"
        "ETİKETLER:\n"
        "tarih, bilim, bilim insanları, "
        "belgesel, keşif, mucitler, "
        "bilim tarihi, dahiler, "
        "tarihi olaylar"
    )


# =========================================================
# ANA
# =========================================================

def main():

    print("================================")
    print("🎬 30-45 DAKİKALIK BELGESEL MOTORU")
    print("================================")
    print(
        f"Hedef: "
        f"{BOLUM_SAYISI} bölüm x "
        f"{BOLUM_BASINA_KELIME} kelime"
    )
    print(
        f"Toplam hedef: "
        f"{TOPLAM_HEDEF_KELIME} kelime"
    )
    print("Ana AI: Gemini")
    print("1. Yedek AI: Cerebras")
    print(
        "2. Yedek AI: "
        "NVIDIA Nemotron Super 49B v1.5"
    )
    print("================================")
    print()

    history = load_history()

    topic = None
    bolumler = None

    # =====================================================
    # KONU DENEMELERİ
    # =====================================================

    print(
        "🧭 Konu + bölüm planı oluşturuluyor..."
    )

    for attempt in range(1, 3):

        print(
            f"🔄 Konu denemesi "
            f"{attempt}/2"
        )

        try:

            candidate_topic, candidate_bolumler = (
                generate_topic_and_outline(
                    history
                )
            )

            candidate_topic = (
                candidate_topic.strip()
                if candidate_topic
                else ""
            )

            if (
                candidate_topic
                and is_valid_topic(
                    candidate_topic
                )
                and candidate_topic not in history
                and len(candidate_bolumler) >= 3
            ):

                topic = candidate_topic

                # En fazla 5 bölüm.
                bolumler = candidate_bolumler[
                    :BOLUM_SAYISI
                ]

                break

            print(
                "⚠️ Geçersiz, tekrar veya "
                "eksik konu/plan geldi."
            )

        except Exception as e:

            print(
                "⚠️ Konu üretim hatası:",
                str(e)
            )

            if attempt < 2:
                time.sleep(5)

    if not topic:

        raise SystemExit(
            "❌ Geçerli konu üretilemedi."
        )

    # =====================================================
    # BÖLÜM PLANINI 5'E TAMAMLA
    # =====================================================

    if len(bolumler) < BOLUM_SAYISI:

        print(
            "⚠️ AI 5 bölüm üretmedi."
        )

        mevcut = len(bolumler)

        for i in range(
            mevcut + 1,
            BOLUM_SAYISI + 1
        ):

            bolumler.append(
                f"BÖLÜM {i}: "
                f"{topic} - "
                f"Konunun devamı ve "
                f"tarihsel sonuçları"
            )

    outline_text = "\n".join(
        bolumler
    )

    print()
    print(
        "🎯 Konu:",
        topic
    )

    for b in bolumler:

        print(
            "  -",
            b
        )

    # =====================================================
    # HISTORY
    # =====================================================

    if topic not in history:

        history.append(topic)

        save_history(
            history
        )

    # =====================================================
    # TOPIC FILE
    # =====================================================

    with open(
        TOPIC_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(topic)

    # =====================================================
    # BÖLÜMLER
    # =====================================================

    print()
    print(
        "✍️ Bölümler yazılıyor..."
    )

    script_parts = []

    previous_tail = None

    metadata_raw = None

    total = len(
        bolumler
    )

    for idx, chapter_line in enumerate(
        bolumler,
        1
    ):

        print()
        print(
            "================================"
        )

        print(
            f"📝 Bölüm "
            f"{idx}/{total}"
        )

        print(
            "================================"
        )

        is_last = (
            idx == total
        )

        chapter_success = False

        # Bölüm başına iki üretim denemesi.
        for chapter_attempt in range(1, 3):

            print(
                f"🔁 Bölüm üretim denemesi "
                f"{chapter_attempt}/2"
            )

            try:

                raw = generate_chapter(
                    topic=topic,
                    outline_text=outline_text,
                    chapter_line=chapter_line,
                    chapter_index=idx,
                    total_chapters=total,
                    previous_tail=previous_tail,
                    need_metadata=is_last
                )

                chapter_text, maybe_metadata = (
                    parse_chapter_with_metadata(
                        raw
                    )
                )

                # Çok kısa cevapları bölüm
                # olarak kabul etme.
                word_count = len(
                    chapter_text.split()
                ) if chapter_text else 0

                if word_count < 300:

                    print(
                        f"⚠️ Bölüm çok kısa: "
                        f"{word_count} kelime."
                    )

                    if chapter_attempt < 2:

                        time.sleep(3)
                        continue

                    break

                script_parts.append(
                    chapter_text
                )

                previous_tail = (
                    chapter_text[-800:]
                )

                if is_last:

                    metadata_raw = (
                        maybe_metadata
                    )

                print(
                    f"✅ Bölüm {idx}: "
                    f"{word_count} kelime"
                )

                chapter_success = True

                break

            except Exception as e:

                print(
                    f"❌ Bölüm {idx} üretilemedi:",
                    str(e)
                )

                if chapter_attempt < 2:

                    print(
                        "⏳ Bölüm tekrar deneniyor..."
                    )

                    time.sleep(4)

        if not chapter_success:

            print(
                f"⚠️ Bölüm {idx} "
                f"tamamlanamadı."
            )

    # =====================================================
    # EN AZ BİR BÖLÜM
    # =====================================================

    if not script_parts:

        raise SystemExit(
            "❌ Hiçbir bölüm üretilemedi."
        )

    # =====================================================
    # FULL SCRIPT
    # =====================================================

    full_script = "\n\n".join(
        script_parts
    )

    toplam_kelime = len(
        full_script.split()
    )

    print()
    print(
        "================================"
    )
    print(
        "📊 İÇERİK İSTATİSTİKLERİ"
    )
    print(
        "================================"
    )

    print(
        "📝 Toplam kelime:",
        toplam_kelime
    )

    print(
        "📚 Başarılı bölüm:",
        len(script_parts),
        "/",
        total
    )

    print(
        "🎯 Hedef kelime:",
        TOPLAM_HEDEF_KELIME
    )

    # =====================================================
    # METADATA
    # =====================================================

    if metadata_raw:

        metadata_text = (
            metadata_raw.strip()
        )

        print(
            "✅ AI metadata oluşturdu."
        )

    else:

        print(
            "⚠️ AI metadata oluşturamadı."
        )

        print(
            "➡️ Varsayılan metadata kullanılıyor."
        )

        metadata_text = (
            default_metadata(
                topic
            )
        )

    # =====================================================
    # FINAL CONTENT
    # =====================================================

    final_content = (
        full_script
        + "\n\n"
        + METADATA_AYIRICI
        + "\n\n"
        + metadata_text
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            final_content
        )

    # =====================================================
    # SON
    # =====================================================

    print()
    print(
        "================================"
    )
    print(
        "✅ İÇERİK OLUŞTURULDU"
    )
    print(
        "================================"
    )

    print(
        "📁",
        OUTPUT_FILE
    )

    print(
        "📝 Kelime sayısı:",
        toplam_kelime
    )

    print(
        "📚 Başarılı bölüm:",
        len(script_parts),
        "/",
        total
    )

    print(
        "🎯 Konu:",
        topic
    )

    print(
        "================================"
    )


if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\n🛑 İşlem kullanıcı tarafından "
            "durduruldu."
        )

        sys.exit(130)

    except SystemExit:

        raise

    except Exception as e:

        print()
        print(
            "================================"
        )

        print(
            "❌ BEKLENMEYEN HATA"
        )

        print(
            "================================"
        )

        print(
            type(e).__name__,
            ":",
            str(e)
        )

        sys.exit(1)
