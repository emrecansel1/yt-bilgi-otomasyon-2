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
# AI SAĞLAYICILARI (ÇOKLU KEY + ÇOKLU SAĞLAYICI ZİNCİRİ)
# GEMINI -> CEREBRAS -> GROQ
# =========================================================

def _load_keys(prefix):
    keys = []

    primary = os.environ.get(prefix, "").strip()
    if primary:
        keys.append(primary)

    for i in range(2, 7):
        extra = os.environ.get(f"{prefix}_{i}", "").strip()
        if extra:
            keys.append(extra)

    return keys

GEMINI_API_KEYS = _load_keys("GEMINI_API_KEY")
CEREBRAS_API_KEYS = _load_keys("CEREBRAS_API_KEY")
GROQ_API_KEYS = _load_keys("GROQ_API_KEY")

GEMINI_MODEL = "gemini-3.6-flash"
CEREBRAS_MODEL = "llama-3.3-70b"
GROQ_MODEL = "llama-3.3-70b-versatile"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

if not (GEMINI_API_KEYS or CEREBRAS_API_KEYS or GROQ_API_KEYS):
    print("❌ Hiçbir AI key bulunamadı (Gemini/Cerebras/Groq).")
    raise SystemExit(1)

print("================================")
print(f"✅ Gemini key sayısı: {len(GEMINI_API_KEYS)}")
print(f"✅ Cerebras key sayısı: {len(CEREBRAS_API_KEYS)}")
print(f"✅ Groq key sayısı: {len(GROQ_API_KEYS)}")
print("================================")

# =========================================================
# DOSYALAR
# =========================================================

TOPIC_FILE = os.path.join(
    OUT,
    "current_topic.txt"
)

TOPIC_HISTORY_FILE = os.path.join(
    REPO_BASE,
    "video_topic_history.json"
)

OUTPUT_FILE = os.path.join(
    OUT,
    "current_content.txt"
)

# =========================================================
# BELGESEL AYARLARI
# =========================================================

BOLUM_SAYISI = 5
BOLUM_BASINA_KELIME = 1100

METADATA_AYIRICI = "===METADATA_AYIRICI==="

# =========================================================
# KONU ÖRNEKLERİ
# =========================================================

ORNEK_KONULAR = """
- Semmelweis'in el yıkama önerisi yüzünden dışlanması
- Nikola Tesla'nın son yılları ve yalnızlığı
- Alan Turing'in savaş dönemindeki çalışmaları ve gördüğü haksızlık
- Rosalind Franklin'in DNA araştırmalarındaki rolü
- Marie Curie'nin radyasyon araştırmaları
- Ludwig Boltzmann'ın bilim dünyasında yaşadığı mücadele
- Barbara McClintock'un keşfinin yıllarca kabul edilmemesi
- Galileo'nun bilimsel fikirleri nedeniyle yargılanması
- Évariste Galois'nın kısa ve trajik hayatı
- Vera Rubin'in karanlık madde araştırmaları
- Jocelyn Bell Burnell'in pulsar keşfi
- Emmy Noether'in akademik hayatta karşılaştığı engeller
- Ada Lovelace'in matematik ve bilgisayar tarihindeki yeri
- Katherine Johnson'un NASA'daki bilimsel çalışmaları
- Srinivasa Ramanujan'ın olağanüstü matematik hayatı
- Antoine Lavoisier'in bilimsel çalışmaları ve trajik sonu
- Isaac Newton'un simya takıntısı ve gizli çalışmaları
- Einstein'ın görelilik kuramına giden yalnız yılları
- Darwin'in kilise ile yaşadığı fikir çatışması
"""

# =========================================================
# ANLATIM KURALLARI
# =========================================================

NARRATION_KURALLARI = """
1. Bilgi uydurma.
2. Tarihleri ve olayları mümkün olduğunca doğru aktar.
3. Emin olunmayan bilgileri kesin gerçek gibi sunma.
4. Doğal, ciddi ve profesyonel Türkçe belgesel anlatımı kullan.
5. Gereksiz tekrar yapma.
6. Konuyu mantıklı ve kronolojik şekilde anlat.
7. Bilimsel konuları herkesin anlayabileceği şekilde açıkla.
8. Önemli kişiler, tarihler, yerler ve olaylara yer ver.
9. Metin doğrudan TTS sistemine gönderilecek.
10. Sadece anlatım metni üret.
11. Sahne açıklaması yazma.
12. Kamera hareketi yazma.
13. Müzik veya ses efekti yazma.
14. Parantez kullanma.
15. Köşeli parantez kullanma.
16. "Sahne 1" gibi ifadeler kullanma.
17. "Bölüm 1" gibi ifadeler kullanma.
18. Metin kesintisiz bir belgesel anlatımı gibi ilerlemeli.
19. Uydurma diyalog oluşturma.
20. Uydurma alıntı oluşturma.
21. Gerçek dışı dramatizasyon yapma.
22. Kişinin insani tarafını doğal biçimde hissettir.
"""

# =========================================================
# AI İSTEK MOTORU (ÇOKLU KEY + ÇOKLU SAĞLAYICI)
# =========================================================

_exhausted = {"gemini": set(), "cerebras": set(), "groq": set()}
_active_index = {"gemini": 0, "cerebras": 0, "groq": 0}

def call_gemini(prompt, max_retries=3):

    if not GEMINI_API_KEYS:
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
        ],
        "generationConfig": {
            "temperature": 0.7
        }
    }

    total_keys = len(GEMINI_API_KEYS)
    keys_tried = 0

    while keys_tried < total_keys:

        idx = _active_index["gemini"]

        if idx in _exhausted["gemini"]:
            _active_index["gemini"] = (idx + 1) % total_keys
            keys_tried += 1
            continue

        api_key = GEMINI_API_KEYS[idx]
        key_label = f"Gemini key {idx + 1}/{total_keys}"

        for attempt in range(1, max_retries + 1):

            print(f"🤖 {key_label} isteği {attempt}/{max_retries}")

            try:

                response = requests.post(
                    GEMINI_URL,
                    params={"key": api_key},
                    headers=headers,
                    json=payload,
                    timeout=180
                )

                print("Gemini HTTP:", response.status_code)

                if response.status_code == 200:

                    try:

                        data = response.json()
                        candidates = data.get("candidates", [])

                        if not candidates:
                            print("❌ Gemini candidates döndürmedi.")
                            return None

                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])

                        if not parts:
                            print("❌ Gemini parts döndürmedi.")
                            return None

                        text = parts[0].get("text", "")

                        if text.strip():
                            print("✅ Gemini cevap verdi.")
                            return text.strip()

                        print("❌ Gemini boş cevap verdi.")
                        return None

                    except Exception as e:

                        print("❌ Gemini cevap okunamadı:", str(e))
                        print(response.text[:3000])
                        return None

                if response.status_code == 429:

                    print(f"⚠️ {key_label}: kota veya hız limiti.")
                    _exhausted["gemini"].add(idx)
                    break

                if response.status_code in (500, 502, 503, 504):

                    print("⚠️ Gemini sunucu hatası:", response.status_code)

                    if attempt < max_retries:
                        wait_time = 8 * attempt + random.randint(1, 5)
                        print(f"⏳ {wait_time} saniye bekleniyor...")
                        time.sleep(wait_time)
                        continue

                    break

                print("❌ Gemini kalıcı hata:")
                print(response.text[:3000])
                return None

            except requests.exceptions.Timeout:

                print("⚠️ Gemini timeout.")

                if attempt < max_retries:
                    time.sleep(10 * attempt)
                    continue

                break

            except requests.exceptions.RequestException as e:

                print("⚠️ Gemini bağlantı hatası:", str(e))

                if attempt < max_retries:
                    time.sleep(10 * attempt)
                    continue

                break

        keys_tried += 1
        _active_index["gemini"] = (idx + 1) % total_keys

    print("❌ Tüm Gemini key'leri denendi.")
    return None

def _call_openai_compatible(provider, url, model, keys, prompt, max_retries=3):

    if not keys:
        return None

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7
    }

    total_keys = len(keys)
    keys_tried = 0

    while keys_tried < total_keys:

        idx = _active_index[provider]

        if idx in _exhausted[provider]:
            _active_index[provider] = (idx + 1) % total_keys
            keys_tried += 1
            continue

        api_key = keys[idx]
        key_label = f"{provider} key {idx + 1}/{total_keys}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        for attempt in range(1, max_retries + 1):

            print(f"🤖 {key_label} isteği {attempt}/{max_retries}")

            try:

                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=180
                )

                print(f"{provider} HTTP:", response.status_code)

                if response.status_code == 200:

                    try:

                        data = response.json()
                        text = data["choices"][0]["message"]["content"]

                        if text and text.strip():
                            print(f"✅ {provider} cevap verdi.")
                            return text.strip()

                        print(f"❌ {provider} boş cevap verdi.")
                        return None

                    except Exception as e:

                        print(f"❌ {provider} cevap okunamadı:", str(e))
                        print(response.text[:3000])
                        return None

                if response.status_code == 429:

                    print(f"⚠️ {key_label}: kota veya hız limiti.")
                    _exhausted[provider].add(idx)
                    break

                if response.status_code in (500, 502, 503, 504):

                    print(f"⚠️ {provider} sunucu hatası:", response.status_code)

                    if attempt < max_retries:
                        wait_time = 8 * attempt + random.randint(1, 5)
                        print(f"⏳ {wait_time} saniye bekleniyor...")
                        time.sleep(wait_time)
                        continue

                    break

                print(f"❌ {provider} kalıcı hata:")
                print(response.text[:3000])
                return None

            except requests.exceptions.Timeout:

                print(f"⚠️ {provider} timeout.")

                if attempt < max_retries:
                    time.sleep(10 * attempt)
                    continue

                break

            except requests.exceptions.RequestException as e:

                print(f"⚠️ {provider} bağlantı hatası:", str(e))

                if attempt < max_retries:
                    time.sleep(10 * attempt)
                    continue

                break

        keys_tried += 1
        _active_index[provider] = (idx + 1) % total_keys

    print(f"❌ Tüm {provider} key'leri denendi.")
    return None

def call_cerebras(prompt, max_retries=3):
    return _call_openai_compatible(
        "cerebras", CEREBRAS_URL, CEREBRAS_MODEL, CEREBRAS_API_KEYS, prompt, max_retries
    )

def call_groq(prompt, max_retries=3):
    return _call_openai_compatible(
        "groq", GROQ_URL, GROQ_MODEL, GROQ_API_KEYS, prompt, max_retries
    )

# =========================================================
# AI (SAĞLAYICI ZİNCİRİ: GEMINI -> CEREBRAS -> GROQ)
# =========================================================

def call_ai(prompt):

    for provider_name, fn in (
        ("Gemini", call_gemini),
        ("Cerebras", call_cerebras),
        ("Groq", call_groq)
    ):

        result = fn(prompt)

        if result:
            return result

        print(f"⚠️ {provider_name} içerik üretemedi, sıradaki sağlayıcıya geçiliyor.")

    raise RuntimeError(
        "Hiçbir AI sağlayıcısı (Gemini/Cerebras/Groq) içerik üretemedi."
    )

# =========================================================
# GEÇMİŞ
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

    except Exception as e:

        print(
            "⚠️ Konu geçmişi okunamadı:",
            str(e)
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
# KONU KONTROLÜ
# =========================================================

def is_valid_topic(topic):

    if not topic:
        return False

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
# KONU + BÖLÜM PLANI
# =========================================================

def generate_topic_and_outline(history):

    if history:

        avoid_list = "\n".join(
            f"- {topic}"
            for topic in history[-50:]
        )

    else:

        avoid_list = "(henüz konu yok)"

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe
YouTube kanalı için profesyonel belgesel
editörüsün.

KANAL NİŞİ:

Bilim insanlarının, mucitlerin ve
kaşiflerin gerçek ve dramatik hayat
hikayeleri.

Kuru bilgi anlatımı istemiyorum.

İzleyicide merak ve duygusal bağ
oluşturacak gerçek bir insan hikayesi
seç.

Mücadele, haksızlık, yalnızlık,
başarısızlık, geç tanınma, keşif,
zafer veya trajedi gibi gerçek
unsurlar kullanılabilir.

Konuyu seçerken hem çok tanınan
isimleri (Einstein, Tesla, Newton,
Darwin, Curie gibi) hem de daha az
bilinen ama çarpıcı hikayeleri
dengeli şekilde kullan. Tanınan bir
isim seçersen, herkesin bildiği
genel hikayeyi değil, az bilinen
ve şaşırtıcı bir yönünü anlat.

ÖRNEK KONU TARZLARI:

{ORNEK_KONULAR}

DAHA ÖNCE KULLANILAN KONULAR:

{avoid_list}

Daha önce kullanılan konulardan
birini kesinlikle seçme.

YENİ KONU:

Gerçek bir bilim insanı, mucit veya
kaşif seç.

Diktatör veya savaş suçlusu seçme.

Savaş tarihi seçme.

Genel tarih konusu seçme.

Günlük eşya konusu seçme.

Yaklaşık 30-45 dakikalık belgeseli
doldurabilecek kadar zengin bir
hikaye seç.

Bu istekte hem konuyu hem de
5 bölümlük planı oluştur.

HER BÖLÜM:

Yaklaşık 1100 kelimelik anlatımı
doldurabilecek içerik içermeli.

ÇIKTI TAM OLARAK ŞU FORMATTA OLSUN:

KONU: <konu>

BÖLÜM 1: <başlık> - <özet>
BÖLÜM 2: <başlık> - <özet>
BÖLÜM 3: <başlık> - <özet>
BÖLÜM 4: <başlık> - <özet>
BÖLÜM 5: <başlık> - <özet>

Markdown kullanma.
Yıldız kullanma.
Başka açıklama yazma.
"""

    return call_ai(prompt)

def parse_topic_outline(raw):

    topic = ""
    chapters = []

    for line in raw.splitlines():

        line = line.strip()

        if not line:
            continue

        clean = (
            line
            .replace("*", "")
            .replace("#", "")
            .strip()
        )

        upper = clean.upper()

        if upper.startswith("KONU:"):

            topic = (
                clean
                .split(":", 1)[1]
                .strip()
            )

        elif (
            upper.startswith("BÖLÜM")
            or upper.startswith("BOLUM")
        ):

            chapters.append(clean)

    topic = re.sub(
        r"\s+",
        " ",
        topic
    ).strip()

    return topic, chapters

# =========================================================
# BÖLÜM ÜRETİMİ (TÜM BÖLÜMLER TEK İSTEKTE - KOTA TASARRUFU)
# =========================================================

BOLUM_AYIRICI = "===BOLUM_AYIRICI==="

def generate_all_chapters(topic, outline_text, chapters):

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı
Türkçe YouTube kanalı için profesyonel
belgesel anlatıcısısın.

GENEL KONU:

{topic}

BÖLÜM PLANI:

{outline_text}

Bu belgeselin TÜM {len(chapters)} bölümünü
TEK SEFERDE, sırasıyla ve birbirinin
doğal devamı olacak şekilde yaz.

Her bölüm yaklaşık {BOLUM_BASINA_KELIME}
kelimelik akıcı bir Türkçe belgesel
anlatımı olmalı.

Bölümler arasında anlatım kopmasın,
aynı bilgiyi veya cümleyi tekrar etme.

Kişinin gerçek hayatını anlat.

Bilimsel çalışmalarını anlat.

Karşılaştığı gerçek sorunları anlat.

İnsan tarafını hissettir.

Dramatik anlatım kullan fakat
gerçeklerden ayrılma.

Uydurma diyalog oluşturma.

Uydurma alıntı oluşturma.

Bilgi uydurma.

{NARRATION_KURALLARI}

ÇOK ÖNEMLİ - ÇIKTI FORMATI:

Her bölümün SADECE seslendirme metnini yaz.

Bölüm başlığı yazma.

"Bölüm 1" yazma.

Sahne yazma.

Kamera yazma.

Müzik yazma.

Ses efekti yazma.

Parantez kullanma.

Köşeli parantez kullanma.

Her bölümden sonra, bir sonraki bölüm
başlamadan önce TAM OLARAK şu satırı
tek başına bir satıra yaz:

{BOLUM_AYIRICI}

Son bölümden sonra bu satırı yazma.

Toplam {len(chapters)} bölüm ve aralarında
{len(chapters) - 1} adet "{BOLUM_AYIRICI}"
satırı olmalı.

Metin doğrudan TTS sistemine
gönderilecektir.
"""

    return call_ai(prompt)

# =========================================================
# METADATA
# =========================================================

def generate_metadata(topic):

    prompt = f"""
Aşağıdaki Türkçe belgesel için
YouTube metadata oluştur.

KONU:

{topic}

Şu formatı kullan:

BAŞLIK:
Güçlü bir merak açığı (curiosity gap)
yaratan, tıklatmaya zorlayan ama
yanıltıcı olmayan YouTube başlığı yaz.

Video içeriğiyle tutarlı olsun,
gerçek olmayan bir iddia yazma.

Şu tarz kalıplardan ilham al (konuya
uyarlayarak, birebir kopyalama):

- "Bilim Dünyasının Yıllarca Sakladığı Gerçek"
- "Kimsenin Konuşmak İstemediği Hikaye"
- "Onu Çıldırtan Keşif"
- "Bilim İnsanlarının İnanmak İstemediği Şey"
- "Neden Yıllarca Unutulmaya Çalışıldı?"

60-90 karakter civarında, tek satır,
abartısız ama merak uyandıran bir
başlık yaz.

KISA_BASLIK:
Thumbnail (kapak görseli) üzerine
yazılacak, 2 ile 4 kelime arasında,
BÜYÜK HARFLE, çok kısa ve çok güçlü
bir merak/şok ifadesi yaz.

Örnek stil: "GİZLİ GERÇEK", "SAKLANAN
SIR", "ÇILDIRTAN KEŞİF", "YASAKLI
BİLGİ", "İNANILMAZ İTİRAF".

Konunun kişisine/olayına özel olsun,
jenerik olmasın. Noktalama işareti
kullanma.

AÇIKLAMA:
3-5 cümlelik açıklama. İlk cümle de
merak uyandırıcı olsun.

ETİKETLER:
15-25 Türkçe etiket, virgülle ayrılmış.

Sadece bu formatı yaz.
"""

    return call_ai(prompt)

def default_metadata(topic):

    return f"""
BAŞLIK:
{topic}

KISA_BASLIK:
GİZLİ GERÇEK

AÇIKLAMA:
{topic} hakkında gerçek olaylara dayanan
kapsamlı bir bilim ve tarih belgeseli.

ETİKETLER:
bilim, tarih, belgesel, bilim insanları,
keşif, mucitler, dahiler, bilgi,
bilim tarihi, tarih belgeseli
"""

# =========================================================
# ANA PROGRAM
# =========================================================

def main():

    os.makedirs(
        OUT,
        exist_ok=True
    )

    print("================================")
    print("🎬 30-45 DAKİKALIK BELGESEL MOTORU")
    print("================================")
    print(
        f"Hedef: {BOLUM_SAYISI} bölüm x "
        f"{BOLUM_BASINA_KELIME} kelime"
    )
    print(
        f"Toplam hedef: "
        f"{BOLUM_SAYISI * BOLUM_BASINA_KELIME} kelime"
    )
    print(
        "🧠 AI ZİNCİRİ: GEMINI -> CEREBRAS -> GROQ"
    )
    print("================================")
    print()

    history = load_history()

    topic = None
    chapters = []

    # =====================================================
    # KONU OLUŞTUR
    # =====================================================

    for attempt in range(1, 3):

        print(
            f"🔄 Konu denemesi "
            f"{attempt}/2"
        )

        try:

            raw = generate_topic_and_outline(
                history
            )

            if not raw:

                print(
                    "⚠️ AI boş cevap verdi."
                )
                continue

            print()
            print(
                "---- AI KONU CEVABI ----"
            )

            print(
                raw[:3000]
            )

            print(
                "----------------------------"
            )

            candidate_topic, candidate_chapters = (
                parse_topic_outline(raw)
            )

            if (
                is_valid_topic(candidate_topic)
                and candidate_topic not in history
                and len(candidate_chapters) >= 5
            ):

                topic = candidate_topic

                chapters = (
                    candidate_chapters[:5]
                )

                break

            print(
                "⚠️ Geçersiz konu veya bölüm planı."
            )

        except Exception as e:

            print(
                "⚠️ Konu üretim hatası:",
                str(e)
            )

            if attempt < 2:

                time.sleep(10)

    if not topic:

        raise SystemExit(
            "❌ İçerik üretilemedi."
        )

    # =====================================================
    # KONU GÖSTER
    # =====================================================

    print()
    print(
        "🎯 KONU:",
        topic
    )

    print()

    for chapter in chapters:

        print(
            "📌",
            chapter
        )

    # =====================================================
    # GEÇMİŞE KAYDET
    # =====================================================

    if topic not in history:

        history.append(
            topic
        )

        save_history(
            history
        )

    with open(
        TOPIC_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            topic
        )

    # =====================================================
    # BÖLÜMLERİ ÜRET (TEK İSTEKTE - KOTA TASARRUFU)
    # =====================================================

    print()
    print(
        "================================"
    )
    print(
        "✍️ BÖLÜMLER TEK İSTEKTE YAZILIYOR"
    )
    print(
        "================================"
    )

    outline_text = "\n".join(
        chapters
    )

    raw_chapters = None

    for attempt in range(1, 3):

        try:

            raw_chapters = generate_all_chapters(
                topic,
                outline_text,
                chapters
            )

            if raw_chapters:
                break

            print(
                "⚠️ AI boş cevap verdi, tekrar deneniyor..."
            )

        except Exception as e:

            print(
                "⚠️ Bölüm üretim hatası:",
                str(e)
            )

        if attempt < 2:
            time.sleep(10)

    if not raw_chapters:

        raise SystemExit(
            "❌ Bölümler üretilemedi."
        )

    script_parts = [
        part.strip()
        for part in raw_chapters.split(BOLUM_AYIRICI)
        if part.strip()
    ]

    if len(script_parts) < len(chapters):
        print(
            f"⚠️ Beklenen {len(chapters)} bölüm yerine "
            f"{len(script_parts)} bölüm geldi, yine de devam ediliyor."
        )

    for index, part in enumerate(script_parts, 1):
        word_count = len(part.split())
        print(
            f"✅ Bölüm {index}: {word_count} kelime"
        )

    # =====================================================
    # TAM METİN
    # =====================================================

    full_script = "\n\n".join(
        script_parts
    )

    total_words = len(
        full_script.split()
    )

    print()
    print(
        "================================"
    )
    print(
        "📊 TOPLAM KELİME:",
        total_words
    )
    print(
        "================================"
    )

    # =====================================================
    # METADATA
    # =====================================================

    metadata_text = None

    try:

        print()
        print(
            "🏷️ Metadata oluşturuluyor..."
        )

        metadata_text = generate_metadata(
            topic
        )

    except Exception as e:

        print(
            "⚠️ Metadata oluşturulamadı:",
            str(e)
        )

    if not metadata_text:

        metadata_text = default_metadata(
            topic
        )

    # =====================================================
    # DOSYAYA YAZ
    # =====================================================

    final_content = (
        full_script
        + "\n\n"
        + METADATA_AYIRICI
        + "\n\n"
        + metadata_text.strip()
    )

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
        "📁 Dosya:",
        OUTPUT_FILE
    )
    print(
        "📝 Kelime:",
        total_words
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
