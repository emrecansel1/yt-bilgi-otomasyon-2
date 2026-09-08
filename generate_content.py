import os
import sys
import json
import re
import time
import random
import requests

BASE = os.path.expanduser("~/yt_bilgi_uzun")
OUT = os.path.join(BASE, "output")
REPO_BASE = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# GEMINI
# =========================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

if GEMINI_API_KEY:
    print("================================")
    print("✅ GEMINI_API_KEY mevcut.")
    print("================================")
else:
    print("❌ GEMINI_API_KEY bulunamadı.")

# Güncel Gemini modeli.
# Google'ın güncel model listesinde 2.5 Flash ve 2.5 Flash-Lite
# kullanılabilir modeller arasında yer alıyor.
GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)

TOPIC_FILE = os.path.join(OUT, "current_topic.txt")
TOPIC_HISTORY_FILE = os.path.join(
    REPO_BASE,
    "video_topic_history.json"
)
OUTPUT_FILE = os.path.join(
    OUT,
    "current_content.txt"
)

BOLUM_SAYISI = 5
BOLUM_BASINA_KELIME = 1100

METADATA_AYIRICI = "===METADATA_AYIRICI==="

ORNEK_KONULAR = """
- Semmelweis'in el yıkama önerisi yüzünden dışlanması
- Nikola Tesla'nın hayatının son dönemindeki yalnızlığı
- Alan Turing'in savaş dönemindeki çalışmaları ve sonrasında yaşadıkları
- Rosalind Franklin'in DNA araştırmalarındaki katkıları
- Marie Curie'nin radyasyon araştırmaları
- Ludwig Boltzmann'ın bilim dünyasındaki mücadelesi
- Barbara McClintock'un genetik keşfinin geç kabul edilmesi
- Galileo Galilei'nin bilimsel fikirleri nedeniyle yaşadığı baskılar
- Évariste Galois'nın kısa ve trajik hayatı
- Vera Rubin'in karanlık madde araştırmaları
- Jocelyn Bell Burnell'in pulsar keşfi
- Emmy Noether'in akademik hayattaki mücadelesi
- Ada Lovelace'in matematik ve bilgisayar tarihindeki rolü
- Katherine Johnson'un NASA'daki bilimsel çalışmaları
- Srinivasa Ramanujan'ın matematik yolculuğu
- Antoine Lavoisier'in bilimsel çalışmaları ve trajik sonu
"""

NARRATION_KURALLARI = """
KURALLAR:

1. Bilgi uydurma.
2. Tarihleri ve olayları mümkün olduğunca doğru aktar.
3. Emin olunmayan bilgileri kesin gerçek gibi sunma.
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

"[Hüzünlü müzik]"
"(kamera yaklaşır)"
"Sahne 1"
"Bölüm 1"

gibi ifadeler kesinlikle yazma.

İzleyici bölümlere ayrıldığını fark etmemeli.

Anlatım kesintisiz tek bir belgesel akışı gibi hissettirmeli.

Sadece seçilen konuyu doğrudan anlat.

Metin doğrudan TTS sistemine gönderileceği için
okuyucu yalnızca gerçek anlatım cümlelerini görmelidir.
"""


# =========================================================
# GEMINI API
# =========================================================

def call_gemini(prompt, max_retries=3):

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY bulunamadı.")
        return None

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
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
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 16000
        }
    }

    for attempt in range(1, max_retries + 1):

        print(
            f"🤖 Gemini isteği "
            f"{attempt}/{max_retries}"
        )

        print(
            f"🧠 Gemini model: {GEMINI_MODEL}"
        )

        try:

            response = requests.post(
                GEMINI_URL,
                headers=headers,
                json=payload,
                timeout=240
            )

            print(
                "Gemini HTTP:",
                response.status_code
            )

            # -------------------------------------------------
            # BAŞARILI
            # -------------------------------------------------

            if response.ok:

                data = response.json()

                try:

                    candidates = data.get(
                        "candidates",
                        []
                    )

                    if not candidates:
                        print(
                            "❌ Gemini candidate döndürmedi."
                        )
                        print(
                            response.text[:3000]
                        )
                        return None

                    content = candidates[0].get(
                        "content",
                        {}
                    )

                    parts = content.get(
                        "parts",
                        []
                    )

                    text_parts = []

                    for part in parts:

                        text = part.get(
                            "text"
                        )

                        if text:
                            text_parts.append(
                                text
                            )

                    result = "\n".join(
                        text_parts
                    ).strip()

                    if not result:

                        print(
                            "❌ Gemini boş cevap döndürdü."
                        )

                        print(
                            response.text[:3000]
                        )

                        return None

                    print(
                        "✅ Gemini başarılı."
                    )

                    return result

                except Exception as e:

                    print(
                        "❌ Gemini cevap ayrıştırma hatası:",
                        e
                    )

                    print(
                        response.text[:3000]
                    )

                    return None

            # -------------------------------------------------
            # 429
            # -------------------------------------------------

            if response.status_code == 429:

                print(
                    "⚠️ Gemini 429: kota veya hız limiti."
                )

                if attempt >= max_retries:

                    print(
                        "❌ Gemini retry limiti doldu."
                    )

                    return None

                wait_time = (
                    10 * attempt
                    + random.randint(1, 5)
                )

                print(
                    f"⏳ {wait_time} saniye bekleniyor..."
                )

                time.sleep(wait_time)

                continue

            # -------------------------------------------------
            # SUNUCU HATALARI
            # -------------------------------------------------

            if response.status_code in {
                500,
                502,
                503,
                504
            }:

                print(
                    "⚠️ Gemini sunucu hatası."
                )

                if attempt >= max_retries:

                    print(
                        "❌ Gemini retry limiti doldu."
                    )

                    return None

                wait_time = (
                    8 * attempt
                    + random.randint(1, 4)
                )

                print(
                    f"⏳ {wait_time} saniye bekleniyor..."
                )

                time.sleep(wait_time)

                continue

            # -------------------------------------------------
            # DİĞER HATALAR
            # -------------------------------------------------

            print(
                "❌ Gemini kalıcı hata:"
            )

            print(
                response.text[:4000]
            )

            return None

        except requests.exceptions.Timeout:

            print(
                "⚠️ Gemini timeout."
            )

            if attempt >= max_retries:
                return None

            wait_time = 10 * attempt

            print(
                f"⏳ {wait_time} saniye bekleniyor..."
            )

            time.sleep(wait_time)

        except requests.exceptions.RequestException as e:

            print(
                "⚠️ Gemini ağ hatası:",
                str(e)
            )

            if attempt >= max_retries:
                return None

            time.sleep(
                8 * attempt
            )

        except Exception as e:

            print(
                "❌ Beklenmeyen Gemini hatası:",
                str(e)
            )

            return None

    return None


# =========================================================
# SADECE GEMINI
# =========================================================

def call_ai(prompt):

    if not GEMINI_API_KEY:

        raise SystemExit(
            "❌ GEMINI_API_KEY bulunamadı."
        )

    print()
    print(
        "================================"
    )
    print(
        "🤖 ANA SİSTEM: GEMINI"
    )
    print(
        "================================"
    )

    result = call_gemini(
        prompt,
        max_retries=3
    )

    if result:

        print()
        print(
            "================================"
        )
        print(
            "✅ İÇERİK GEMINI TARAFINDAN ÜRETİLDİ"
        )
        print(
            "================================"
        )

        return result

    raise SystemExit(
        "❌ Gemini içerik üretemedi."
    )


# =========================================================
# GEÇMİŞ KONU
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
            e
        )

        return []


def save_history(history):

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
# KONU KONTROL
# =========================================================

def is_valid_topic(topic):

    if not topic:
        return False

    if len(topic) < 8:
        return False

    if len(topic) > 220:
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

    if history:

        avoid_list = "\n".join(
            f"- {t}"
            for t in history[-50:]
        )

    else:

        avoid_list = "(henüz yok)"

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe
bilgi/tarih/bilim YouTube kanalı için
30-45 dakikalık belgesel hazırlayan
profesyonel editör ve senaristsin.

KANAL NİŞİ:

Kanal SADECE bilim insanlarının,
mucitlerin ve kaşiflerin insani,
dramatik ve gerçek hikayelerine odaklanıyor.

Kuru bilgi anlatımı istemiyorum.

Bir insanın:

- mücadelesi
- haksızlığa uğraması
- yalnızlığı
- başarısızlıkları
- bilimsel keşfi
- geç tanınması
- dönemin baskıları
- kişisel fedakarlıkları
- hayatındaki önemli kırılma noktaları

anlatılmalı.

ÖRNEK KONU TARZLARI:

{ORNEK_KONULAR}

DAHA ÖNCE KULLANILAN KONULAR:

{avoid_list}

Daha önce kullanılan konuları tekrar seçme.

Bu istekte:

1. Yeni bir konu seç.
2. Konuyu 5 bölümlük plana ayır.

Toplam hedef yaklaşık:

5 x 1100 = 5500 kelime.

Konu 30-45 dakikalık belgeseli
doldurabilecek kadar zengin olmalıdır.

KURALLAR:

- Gerçek ve doğrulanabilir kişi seç.
- Bilim insanı, mucit veya kaşif seç.
- Savaş tarihi seçme.
- Genel tarih konusu seçme.
- Diktatör seçme.
- Savaş suçlusu seçme.
- Propaganda üretme.
- Uydurma olay üretme.
- Güçlü merak unsuru oluştur.
- İnsani ve dramatik tarafı güçlü olsun.
- Son bölüm güçlü bir kapanışa uygun olsun.
- Konu daha önce kullanılmamış olsun.

ÇIKTIYI TAM OLARAK ŞU FORMATTA VER:

KONU: <konu>

BÖLÜM 1: <başlık> - <özet>

BÖLÜM 2: <başlık> - <özet>

BÖLÜM 3: <başlık> - <özet>

BÖLÜM 4: <başlık> - <özet>

BÖLÜM 5: <başlık> - <özet>

Markdown kullanma.
Yalnızca düz metin kullan.
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

        clean_line = (
            line
            .replace("*", "")
            .replace("#", "")
            .strip()
        )

        upper = clean_line.upper()

        if upper.startswith("KONU:"):

            topic = clean_line.split(
                ":",
                1
            )[1].strip()

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
    ).strip().strip('"').strip()

    # Gemini bazen bölüm eksiltirse
    if len(bolumler) < BOLUM_SAYISI:

        print(
            f"⚠️ Gemini {len(bolumler)} bölüm verdi."
        )

    print()
    print(
        "---- GEMINI HAM ÇIKTI ----"
    )

    print(
        raw[:2500]
    )

    print(
        "---- ÜRETİLEN KONU:",
        repr(topic)
    )

    print(
        "---- BÖLÜM SAYISI:",
        len(bolumler)
    )

    print(
        "--------------------------"
    )
    print()

    return topic, bolumler


# =========================================================
# BÖLÜM ÜRET
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

Buradan doğal biçimde devam et.

Aynı bilgileri tekrar etme.
Yeni olaylara geç.
"""

    metadata_talimati = ""

    if need_metadata:

        metadata_talimati = f"""

BU SON BÖLÜMDÜR.

Anlatımı tamamladıktan sonra şu ayırıcıyı yaz:

{METADATA_AYIRICI}

BAŞLIK:
Merak uyandırıcı ama yanıltıcı olmayan YouTube başlığı.

AÇIKLAMA:
3-5 cümlelik YouTube açıklaması.

ETİKETLER:
15-25 Türkçe etiket, virgülle ayrılmış.
"""

    prompt = f"""
Sen DAHİLER VE KEŞİFLER adlı YouTube kanalı için
profesyonel Türkçe tarih ve bilim belgeseli
anlatıcısısın.

KONU:

{topic}

BÖLÜM PLANI:

{outline_text}

ŞU AN YAZILACAK BÖLÜM:

{chapter_line}

{devamlilik}

Yaklaşık {BOLUM_BASINA_KELIME} kelimelik
akıcı Türkçe belgesel anlatımı yaz.

Bu bölümün amacı:
- Hikayeyi ileri taşımak.
- Yeni bilgiler vermek.
- Kişinin insani tarafını göstermek.
- İzleyicinin merakını korumak.

ANLATIM KURALLARI:

{NARRATION_KURALLARI}

ÖNEMLİ:

Metin doğrudan TTS sistemine gidecek.

Bölüm numarası yazma.
Başlık yazma.
Sahne yazma.
Kamera talimatı yazma.
Müzik yazma.
Ses efekti yazma.
Parantez kullanma.
Köşeli parantez kullanma.

Sadece anlatıcı tarafından okunacak
gerçek belgesel metnini üret.

{metadata_talimati}
"""

    raw = call_ai(prompt)

    if not raw:
        return ""

    return raw.strip()


# =========================================================
# METADATA AYIR
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

    return (
        raw_text.strip(),
        None
    )


# =========================================================
# VARSAYILAN METADATA
# =========================================================

def default_metadata(topic):

    return (
        "BAŞLIK:\n"
        f"{topic[:95]}\n\n"
        "AÇIKLAMA:\n"
        f"{topic} hakkında kapsamlı bir belgesel.\n\n"
        "ETİKETLER:\n"
        "tarih, bilim, belgesel, keşif, "
        "bilim insanları, dahiler, bilgi"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "================================"
    )
    print(
        "🎬 30-45 DAKİKALIK BELGESEL MOTORU"
    )
    print(
        "================================"
    )

    print(
        f"Hedef: {BOLUM_SAYISI} bölüm x "
        f"{BOLUM_BASINA_KELIME} kelime"
    )

    print(
        f"Toplam hedef: "
        f"{BOLUM_SAYISI * BOLUM_BASINA_KELIME} kelime"
    )

    print(
        "🤖 KULLANILAN AI: GEMINI"
    )

    print(
        "🚫 Cerebras: DEVRE DIŞI"
    )

    print(
        "🚫 NVIDIA: DEVRE DIŞI"
    )

    print()

    if not GEMINI_API_KEY:

        raise SystemExit(
            "❌ GEMINI_API_KEY yok."
        )

    history = load_history()

    topic = None
    bolumler = None

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

            if (
                candidate_topic
                and is_valid_topic(
                    candidate_topic
                )
                and candidate_topic not in history
                and len(candidate_bolumler) >= 5
            ):

                topic = candidate_topic
                bolumler = candidate_bolumler[:5]

                break

            print(
                "⚠️ Geçersiz konu veya bölüm planı."
            )

        except SystemExit:

            if attempt >= 2:
                raise

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

    # -----------------------------------------------------
    # GEÇMİŞE EKLE
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # BÖLÜMLER
    # -----------------------------------------------------

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

        is_last = (
            idx == total
        )

        print()
        print(
            f"📝 Bölüm {idx}/{total}"
        )

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

        if not chapter_text:

            print(
                f"⚠️ Bölüm {idx} boş geldi."
            )

            continue

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
            f"{len(chapter_text.split())} kelime"
        )

    # -----------------------------------------------------
    # KONTROL
    # -----------------------------------------------------

    if not script_parts:

        raise SystemExit(
            "❌ Hiçbir bölüm üretilemedi."
        )

    full_script = "\n\n".join(
        script_parts
    )

    toplam_kelime = len(
        full_script.split()
    )

    print()
    print(
        f"📊 Toplam kelime: "
        f"{toplam_kelime}"
    )

    # -----------------------------------------------------
    # METADATA
    # -----------------------------------------------------

    if metadata_raw:

        metadata_text = (
            metadata_raw.strip()
        )

    else:

        print(
            "⚠️ Metadata üretilemedi."
        )

        print(
            "ℹ️ Varsayılan metadata kullanılıyor."
        )

        metadata_text = (
            default_metadata(
                topic
            )
        )

    final_content = (
        full_script
        + "\n\n"
        + METADATA_AYIRICI
        + "\n\n"
        + metadata_text
    )

    # -----------------------------------------------------
    # DOSYAYA YAZ
    # -----------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            final_content
        )

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
        "🤖 AI: GEMINI"
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
        "🎯 Konu:",
        topic
    )

    print(
        "================================"
    )


if __name__ == "__main__":
    main()
