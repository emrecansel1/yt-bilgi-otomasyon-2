import os
import json
import requests
import re
import time
import random

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")
REPO_BASE = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# API ANAHTARLARI
# =========================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "").strip()

if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY bulunamadı.")

if not CEREBRAS_API_KEY:
    print("⚠️ CEREBRAS_API_KEY bulunamadı.")

# =========================================================
# DOSYALAR
# =========================================================

TOPIC_FILE = os.path.join(OUT, "current_topic.txt")
TOPIC_HISTORY_FILE = os.path.join(REPO_BASE, "video_topic_history.json")
OUTPUT_FILE = os.path.join(OUT, "current_content.txt")

# =========================================================
# API ADRESLERİ
# =========================================================

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.6-flash:generateContent"
)

CEREBRAS_URL = (
    "https://api.cerebras.ai/v1/chat/completions"
)

CEREBRAS_MODEL = "llama-3.3-70b"

# =========================================================
# GENEL AYARLAR
# =========================================================

MAX_HISTORY = 30

# Yaklaşık 15 dakikalık video
BOLUM_SAYISI = 2
BOLUM_BASINA_KELIME = 1100

METADATA_AYIRICI = "===METADATA_AYIRICI==="

# =========================================================
# NİŞ: DRAMATİK BİLİM İNSANI HİKAYELERİ
# =========================================================

ORNEK_KONULAR = """
- Semmelweis'in el yıkama önerisi yüzünden tımarhaneye kapatılması
- Nikola Tesla'nın sefalet içinde otel odasında ölümü
- Alan Turing'in savaşı kazandırıp sonra devlet tarafından yok edilmesi
- Rosalind Franklin'in DNA keşfindeki payının çalınması
- Marie Curie'nin kendi keşfettiği radyasyondan ölümü
- Ludwig Boltzmann'ın bilim camiası tarafından dışlanıp intihar etmesi
- Barbara McClintock'un keşfinin 30 yıl sonra kabul edilmesi
- Galileo'nun kilise tarafından yargılanıp susturulması
- Giordano Bruno'nun fikirleri yüzünden diri diri yakılması
- Évariste Galois'nın 20 yaşında düelloda ölmesi
- Vera Rubin'in karanlık madde keşfinin yıllarca göz ardı edilmesi
- Jocelyn Bell Burnell'in pulsar keşfinde göz ardı edilmesi
- Rosalind Franklin'in erken yaşta kanserden ölmesi
- Emmy Noether'in kadın olduğu için üniversitede maaş alamaması
- Ada Lovelace'in ilk programcı olarak tanınmadan ölmesi
- Katherine Johnson'un ırkçılığa rağmen NASA'da yükselmesi
- Srinivasa Ramanujan'ın İngiltere'de yalnızlıktan hastalanması
- Kurt Gödel'in paranoyadan açlıktan ölmesi
- John Nash'in şizofreniyle mücadelesi
- Antoine Lavoisier'in kimyayı bilim yapıp sonra idam edilmesi
"""

# =========================================================
# ANLATIM KURALLARI
# =========================================================

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


# =========================================================
# GEMINI
# =========================================================

def call_gemini(prompt, max_retries=2):

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY bulunamadı.")
        return None

    for attempt in range(1, max_retries + 1):

        print(f"🤖 Gemini isteği {attempt}/{max_retries}")

        try:

            response = requests.post(
                GEMINI_URL,
                params={"key": GEMINI_API_KEY},
                json={
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                },
                timeout=180
            )

            print("Gemini HTTP:", response.status_code)

            if response.ok:

                data = response.json()

                try:
                    return (
                        data["candidates"][0]
                        ["content"]["parts"][0]["text"]
                    )

                except (KeyError, IndexError, TypeError):

                    print(
                        "❌ Gemini cevabı beklenen formatta değil."
                    )

                    return None

            if response.status_code == 429:

                print("⚠️ Gemini 429 / kota hatası.")
                print("🔄 Cerebras'a geçilecek.")

                return None

            if response.status_code in {500, 502, 503, 504}:

                if attempt >= max_retries:
                    return None

                wait_time = (
                    5 * attempt
                    + random.randint(0, 3)
                )

                print(
                    f"⏳ {wait_time} saniye bekleniyor..."
                )

                time.sleep(wait_time)

                continue

            print("❌ Gemini kalıcı hata:")
            print(response.text[:2000])

            return None

        except requests.exceptions.Timeout:

            print("⚠️ Gemini timeout.")

            if attempt >= max_retries:
                return None

            time.sleep(5)

        except requests.exceptions.RequestException as e:

            print("⚠️ Gemini ağ hatası:", str(e))

            if attempt >= max_retries:
                return None

            time.sleep(5)

    return None


# =========================================================
# CEREBRAS
# =========================================================

def call_cerebras(prompt, max_retries=2):

    if not CEREBRAS_API_KEY:
        print("❌ CEREBRAS_API_KEY bulunamadı.")
        return None

    headers = {
        "Authorization": f"Bearer {CEREBRAS_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": CEREBRAS_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sen profesyonel Türkçe tarih ve bilim "
                    "belgeseli yazarı olarak görev yapıyorsun."
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

    for attempt in range(1, max_retries + 1):

        print(f"🟢 Cerebras isteği {attempt}/{max_retries}")

        try:

            response = requests.post(
                CEREBRAS_URL,
                headers=headers,
                json=payload,
                timeout=180
            )

            print("Cerebras HTTP:", response.status_code)

            if response.ok:

                data = response.json()

                try:
                    return (
                        data["choices"][0]
                        ["message"]["content"]
                    )

                except (KeyError, IndexError, TypeError):

                    print(
                        "❌ Cerebras cevabı beklenen formatta değil."
                    )

                    return None

            if response.status_code == 401:

                print("❌ Cerebras API key geçersiz.")
                print(
                    "⚠️ GitHub Secrets bölümündeki "
                    "CEREBRAS_API_KEY değerini kontrol et."
                )

                return None

            if response.status_code == 429:

                print("⚠️ Cerebras 429 / kota hatası.")

                if attempt >= max_retries:
                    return None

                wait_time = 10 * attempt

                print(
                    f"⏳ {wait_time} saniye bekleniyor..."
                )

                time.sleep(wait_time)

                continue

            if response.status_code in {500, 502, 503, 504}:

                if attempt >= max_retries:
                    return None

                time.sleep(5 * attempt)

                continue

            print("❌ Cerebras kalıcı hata:")
            print(response.text[:2000])

            return None

        except requests.exceptions.Timeout:

            print("⚠️ Cerebras timeout.")

            if attempt >= max_retries:
                return None

            time.sleep(5)

        except requests.exceptions.RequestException as e:

            print("⚠️ Cerebras ağ hatası:", str(e))

            if attempt >= max_retries:
                return None

            time.sleep(5)

    return None


# =========================================================
# ANA AI SİSTEMİ
# GEMINI → CEREBRAS
# =========================================================

def call_ai(prompt):

    # Önce Gemini
    if GEMINI_API_KEY:

        result = call_gemini(prompt)

        if result:

            print(
                "✅ İçerik Gemini tarafından üretildi."
            )

            return result

    # Gemini başarısızsa Cerebras
    print()
    print("================================")
    print("⚠️ GEMINI BAŞARISIZ")
    print("🟢 CEREBRAS YEDEK SİSTEM DEVREDE")
    print("================================")

    result = call_cerebras(prompt)

    if result:

        print(
            "✅ İçerik Cerebras tarafından üretildi."
        )

        return result

    raise SystemExit(
        "❌ Gemini ve Cerebras başarısız oldu."
    )


# =========================================================
# GEÇMİŞ
# =========================================================

def load_history():

    if os.path.exists(TOPIC_HISTORY_FILE):

        try:

            with open(
                TOPIC_HISTORY_FILE,
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except Exception:

            return []

    return []


def save_history(history):

    history = history[-MAX_HISTORY:]

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


# =========================================================
# KONU KONTROLÜ
# =========================================================

def is_valid_topic(topic):

    if not topic:
        return False

    if len(topic) < 8 or len(topic) > 220:
        return False

    if not re.search(
        r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}",
        topic
    ):
        return False

    if len(topic.split()) < 2:
        return False

    return True


# =========================================================
# KONU + BÖLÜM PLANI
# =========================================================

def generate_topic_and_outline(history):

    avoid_list = (
        "\n".join(
            f"- {t}"
            for t in history
        )
        if history
        else "(henüz yok)"
    )

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe bilgi/tarih/bilim
YouTube kanalı için yaklaşık 15 dakikalık belgesel
hazırlayan editör ve senaristsin.

KANALIN NİŞİ:

Kanal artık SADECE bilim insanlarının, mucitlerin ve
kaşiflerin İNSANİ VE DRAMATİK HİKAYELERİNE odaklanıyor.
Kuru bilgi anlatımı değil; bir bilim insanının yaşadığı
haksızlık, trajedi, mücadele, görmezden gelinme, ölüm,
yalnızlık veya geç kabul görme hikayesi anlatılacak.

Amaç izleyicide GERÇEK BİR DUYGUSAL BAĞ kurmak: üzüntü,
hayranlık, öfke (haksızlığa karşı) veya ilham.

ÖRNEK KONU TARZLARI (birebir kopyalama, ilham al,
farklı isimler/olaylar sec):
{ORNEK_KONULAR}

Bu tek istekte HEM konuyu seç HEM bölüm planını oluştur.

SEÇİLEN KONU yaklaşık 15 dakikalık anlatımı doldurabilecek
kadar zengin olmalı VE yukarıdaki nişe (dramatik bilim
insanı hikayesi) birebir uymalı.

Daha önce kullanılan konular:
{avoid_list}

Konuyu {BOLUM_SAYISI} bölümde anlat.

Her bölüm yaklaşık {BOLUM_BASINA_KELIME} kelime olsun.

Toplam yaklaşık
{BOLUM_SAYISI * BOLUM_BASINA_KELIME}
kelimelik bir belgesel oluştur.

KURALLAR:
- Güçlü açılış ve merak unsuru kullan.
- Anlatım boyunca kişinin insani tarafını (korkuları,
  umutları, çektiği acı) hissettir.
- Son bölüm güçlü, duygusal bir kapanışla bitsin.
- Konu tekrarı yapma.
- Gerçek ve doğrulanabilir konu seç.
- Diktatör veya savaş suçlusu önerme.
- Propaganda veya kışkırtıcı içerik üretme.
- Sadece bilim insanı/mucit/kaşif hikayesi seç, başka
  konu türüne (savaş tarihi, genel merak, günlük eşyalar
  vb.) kayma.

ÇIKTI FORMATI:

KONU: <konu>
BÖLÜM 1: <başlık> - <özet>
BÖLÜM 2: <başlık> - <özet>
"""

    raw = call_ai(prompt)

    if not raw:
        return "", []

    topic = ""
    bolumler = []

    for line in raw.strip().splitlines():

        line = line.strip()

        if not line:
            continue

        if line.upper().startswith("KONU:"):

            topic = line.split(
                ":",
                1
            )[1].strip()

        elif (
            line.upper().startswith("BÖLÜM")
            or line.upper().startswith("BOLUM")
        ):

            bolumler.append(line)

    topic = re.sub(
        r"\s+",
        " ",
        topic
    ).strip().strip('"').strip()

    if not bolumler and topic:

        bolumler = [
            f"BÖLÜM 1: {topic} - Konunun genel anlatımı"
        ]

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
BİR ÖNCEKİ BÖLÜMÜN SON KISMI:

\"\"\"{previous_tail}\"\"\"

Buradan doğal şekilde devam et.
Tekrar yapma.
"""

    metadata_talimati = ""

    if need_metadata:

        metadata_talimati = f"""

BU SON BÖLÜM.

Metni bitirdikten sonra:

{METADATA_AYIRICI}

BAŞLIK:
Merak uyandırıcı ama yanıltıcı olmayan YouTube başlığı.

AÇIKLAMA:
3-5 cümlelik açıklama.

ETİKETLER:
15-25 Türkçe etiket, virgülle ayrılmış.
"""

    prompt = f"""
Sen DAHİLER VE KEŞİFLER adlı YouTube kanalı için
profesyonel Türkçe tarih/bilim belgeseli anlatıcısısın.

Kanalın nişi: bilim insanlarının/mucitlerin/kaşiflerin
insani ve dramatik hikayeleri. Anlatımda kişinin
duygusal/insani tarafını (mücadele, haksızlık, acı,
zafer) hissettir, sadece kuru olay/tarih sıralaması
yapma.

GENEL KONU:

{topic}

BÖLÜM PLANI:

{outline_text}

YAZILACAK BÖLÜM:

{chapter_line}

{devamlilik}

Yaklaşık {BOLUM_BASINA_KELIME} kelimelik
akıcı ve kesintisiz belgesel anlatımı yaz.

İzleyici bunun bir bölüm olduğunu fark etmemeli.

{NARRATION_KURALLARI}

ÇIKTI SADECE SESLENDİRME METNİ OLMALI.

Başlık, bölüm numarası veya sahne açıklaması yazma.

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

    if METADATA_AYIRICI in raw_text:

        narration, metadata = raw_text.split(
            METADATA_AYIRICI,
            1
        )

        return (
            narration.strip(),
            metadata.strip()
        )

    return raw_text.strip(), None


# =========================================================
# VARSAYILAN METADATA
# =========================================================

def default_metadata(topic):

    return (
        f"BAŞLIK:\n"
        f"{topic[:95]}\n\n"
        f"AÇIKLAMA:\n"
        f"{topic} hakkında kapsamlı bir belgesel.\n\n"
        f"ETİKETLER:\n"
        f"tarih, bilim, belgesel, keşif, bilgi"
    )


# =========================================================
# ANA PROGRAM
# =========================================================

def main():

    print("================================")
    print("🎬 15 DAKİKALIK BELGESEL MOTORU")
    print("================================")

    print(
        f"Hedef: {BOLUM_SAYISI} bölüm x "
        f"{BOLUM_BASINA_KELIME} kelime"
    )

    print(
        f"Toplam hedef: "
        f"{BOLUM_SAYISI * BOLUM_BASINA_KELIME} kelime"
    )

    print("Ana AI: Gemini")
    print("Yedek AI: Cerebras")
    print()

    history = load_history()

    topic = None
    bolumler = None

    print(
        "🧭 Konu + bölüm planı oluşturuluyor..."
    )

    for attempt in range(2):

        try:

            candidate_topic, candidate_bolumler = (
                generate_topic_and_outline(
                    history
                )
            )

            if (
                candidate_topic
                and is_valid_topic(candidate_topic)
                and candidate_topic not in history
            ):

                topic = candidate_topic
                bolumler = candidate_bolumler

                break

            print(
                "⚠️ Geçersiz veya tekrar konu."
            )

        except Exception as e:

            print(
                "⚠️ Konu üretim hatası:",
                str(e)
            )

            if attempt < 1:
                time.sleep(5)

    if not topic:

        raise SystemExit(
            "❌ Geçerli konu üretilemedi."
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

    history.append(topic)

    save_history(history)

    os.makedirs(
        OUT,
        exist_ok=True
    )

    with open(
        TOPIC_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(topic)

    print()
    print(
        "✍️ Bölümler yazılıyor..."
    )

    script_parts = []
    previous_tail = None
    metadata_raw = None

    total = len(bolumler)

    for idx, chapter_line in enumerate(
        bolumler,
        1
    ):

        is_last = idx == total

        print(
            f"📝 Bölüm {idx}/{total}"
        )

        raw = generate_chapter(
            topic,
            outline_text,
            chapter_line,
            idx,
            total,
            previous_tail,
            need_metadata=is_last
        )

        chapter_text, maybe_metadata = (
            parse_chapter_with_metadata(
                raw
            )
        )

        if not chapter_text:

            print(
                f"⚠️ Bölüm {idx} boş geldi."
            )

            continue

        script_parts.append(
            chapter_text
        )

        previous_tail = (
            chapter_text[-500:]
        )

        if is_last:

            metadata_raw = maybe_metadata

        print(
            f"✅ Bölüm {idx}: "
            f"{len(chapter_text.split())} kelime"
        )

    if not script_parts:

        raise SystemExit(
            "❌ Hiçbir bölüm üretilemedi."
        )

    full_script = "\n\n".join(
        script_parts
    )

    toplam_kelime = len(
       
