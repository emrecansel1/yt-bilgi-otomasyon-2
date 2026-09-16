import os
import json
import requests
import re
import time
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.expanduser("~/yt_bilgi_uzun/output")

OUTPUT_FILE = os.path.join(BASE, "shorts_content.json")
TOPIC_FILE = os.path.join(OUT, "shorts_topic.txt")
TOPIC_HISTORY_FILE = os.path.join(BASE, "shorts_topic_history.json")

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
CEREBRAS_MODEL = "gpt-oss-120b"
GROQ_MODEL = "openai/gpt-oss-120b"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

if not (GEMINI_API_KEYS or CEREBRAS_API_KEYS or GROQ_API_KEYS):
    raise RuntimeError("Hiçbir AI key bulunamadı (Gemini/Cerebras/Groq).")

print(f"✅ Gemini key sayısı: {len(GEMINI_API_KEYS)}")
print(f"✅ Cerebras key sayısı: {len(CEREBRAS_API_KEYS)}")
print(f"✅ Groq key sayısı: {len(GROQ_API_KEYS)}")

MAX_HISTORY = 60

ORNEK_KONULAR = """
- Semmelweis'in el yıkama önerisi yüzünden tımarhaneye kapatılması
- Nikola Tesla'nın sefalet içinde otel odasında ölümü
- Alan Turing'in savaşı kazandırıp sonra devlet tarafından yok edilmesi
- Rosalind Franklin'in DNA keşfindeki payının çalınması
- Marie Curie'nin kendi keşfettiği radyasyondan ölümü
- Ludwig Boltzmann'ın bilim camiası tarafından dışlanıp intihar etmesi
- Barbara McClintock'un keşfinin 30 yıl sonra kabul edilmesi
- Galileo'nun kilise tarafından yargılanıp susturulması
- Évariste Galois'nın 20 yaşında düelloda ölmesi
- Vera Rubin'in karanlık madde keşfinin yıllarca göz ardı edilmesi
- Jocelyn Bell Burnell'in pulsar keşfinde göz ardı edilmesi
- Emmy Noether'in kadın olduğu için üniversitede maaş alamaması
- Ada Lovelace'in ilk programcı olarak tanınmadan ölmesi
- Katherine Johnson'un ırkçılığa rağmen NASA'da yükselmesi
- Srinivasa Ramanujan'ın İngiltere'de yalnızlıktan hastalanması
- Kurt Gödel'in paranoyadan açlıktan ölmesi
- Antoine Lavoisier'in kimyayı bilim yapıp sonra idam edilmesi
- Einstein'ın kimsenin bilmediği acı bir kararı
- Newton'un gizli simya çalışmaları
"""

def clean_text(text):
    text = re.sub(r"\[[^\]]*\]", "", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def load_history():
    if os.path.exists(TOPIC_HISTORY_FILE):
        try:
            with open(TOPIC_HISTORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_history(history):
    history = history[-MAX_HISTORY:]
    with open(TOPIC_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def is_valid_topic(topic):
    if not topic:
        return False

    topic = topic.strip()

    if len(topic) < 8 or len(topic) > 350:
        return False

    if len(topic.split()) < 2:
        return False

    return True

# =========================================================
# AI İSTEK MOTORU (ÇOKLU KEY + ÇOKLU SAĞLAYICI)
# =========================================================

_exhausted = {"gemini": set(), "cerebras": set(), "groq": set()}
_active_index = {"gemini": 0, "cerebras": 0, "groq": 0}

def call_gemini(prompt, max_retries=3):

    if not GEMINI_API_KEYS:
        return None

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
        delay = 5

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    GEMINI_URL,
                    params={"key": api_key},
                    json=payload,
                    timeout=120
                )

                if response.status_code == 429:
                    print(f"   ⚠️ {key_label}: kota doldu, sıradaki key'e geçiliyor.")
                    _exhausted["gemini"].add(idx)
                    break

                if response.status_code in (500, 502, 503, 504):
                    print(
                        f"   ⏳ Gemini hata (HTTP {response.status_code}, {key_label}), "
                        f"{delay} sn bekleyip tekrar denenecek ({attempt}/{max_retries})..."
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue

                response.raise_for_status()
                data = response.json()

                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError, TypeError):
                    print("   ⚠️ Gemini boş/geçersiz cevap döndürdü.")
                    time.sleep(delay)
                    delay = min(delay * 2, 60)

            except requests.exceptions.RequestException as e:
                print(
                    f"   ⚠️ Gemini isteği hatası: {e} ({key_label}), "
                    f"{delay} sn bekleyip tekrar denenecek ({attempt}/{max_retries})..."
                )
                time.sleep(delay)
                delay = min(delay * 2, 60)

        keys_tried += 1
        _active_index["gemini"] = (idx + 1) % total_keys

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
        delay = 5

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=120
                )

                if response.status_code == 429:
                    print(f"   ⚠️ {key_label}: kota doldu, sıradaki key'e geçiliyor.")
                    _exhausted[provider].add(idx)
                    break

                if response.status_code in (500, 502, 503, 504):
                    print(
                        f"   ⏳ {provider} hata (HTTP {response.status_code}, {key_label}), "
                        f"{delay} sn bekleyip tekrar denenecek ({attempt}/{max_retries})..."
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue

                response.raise_for_status()
                data = response.json()

                try:
                    return data["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError):
                    print(f"   ⚠️ {provider} boş/geçersiz cevap döndürdü.")
                    time.sleep(delay)
                    delay = min(delay * 2, 60)

            except requests.exceptions.RequestException as e:
                print(
                    f"   ⚠️ {provider} isteği hatası: {e} ({key_label}), "
                    f"{delay} sn bekleyip tekrar denenecek ({attempt}/{max_retries})..."
                )
                time.sleep(delay)
                delay = min(delay * 2, 60)

        keys_tried += 1
        _active_index[provider] = (idx + 1) % total_keys

    return None

def call_cerebras(prompt, max_retries=3):
    return _call_openai_compatible(
        "cerebras", CEREBRAS_URL, CEREBRAS_MODEL, CEREBRAS_API_KEYS, prompt, max_retries
    )

def call_groq(prompt, max_retries=3):
    return _call_openai_compatible(
        "groq", GROQ_URL, GROQ_MODEL, GROQ_API_KEYS, prompt, max_retries
    )

def call_gemini_with_retry(prompt, max_retries=5):

    for provider_name, fn in (
        ("Gemini", call_gemini),
        ("Cerebras", call_cerebras),
        ("Groq", call_groq)
    ):

        result = fn(prompt)

        if result:
            return result

        print(f"   ⚠️ {provider_name} içerik üretemedi, sıradaki sağlayıcıya geçiliyor.")

    raise RuntimeError(
        "Gemini API'ye ulaşılamadı (tüm sağlayıcılar ve key'ler başarısız)."
    )

def generate(avoid_list_text):

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe bilgi YouTube kanalının
Shorts konu bulan VE içerik yazan editörüsün.

Tek istekte hem konuyu seç hem de metni yaz.

KANAL NİŞİ:

Kanal sadece bilim insanlarının, mucitlerin ve kaşiflerin
İNSANİ VE DRAMATİK HİKAYELERİNE odaklanıyor.

Hikayelerde haksızlık, trajedi, mücadele, görmezden gelinme,
yalnızlık, başarısızlık veya geç gelen başarı gibi güçlü
insani unsurlar bulunabilir.

Konu seçerken hem tanınan isimleri (Einstein, Tesla, Newton
gibi, herkesin bilmediği bir yönüyle) hem de az bilinen
çarpıcı hikayeleri dengeli kullan.

ÖRNEK KONU TARZLARI:
{ORNEK_KONULAR}

DAHA ÖNCE KULLANILAN KONULAR:
{avoid_list_text}

KESİNLİKLE bu listedeki konuları veya çok benzerlerini seçme.

KONU:
Gerçek ve doğrulanabilir tek bir bilim insanı, mucit veya
kaşif hikayesi seç.

METİN:
40-75 kelime arasında Türkçe Shorts metni yaz.
İlk cümle çok güçlü bir soru, şaşırtıcı gerçek veya çarpıcı
iddia olsun.
İlk cümle 8-10 kelimeyi geçmesin.
Kısa ve vurucu cümleler kullan.
Doğrulanmamış bilgi uydurma.
Parantez, sahne açıklaması, kamera açıklaması veya efekt yazma.
"Merhaba arkadaşlar", "Biliyor muydunuz ki" gibi girişler kullanma.

BAŞLIK:
Güçlü bir merak açığı (curiosity gap) yaratan, tıklatmaya
zorlayan ama yanıltıcı olmayan Türkçe başlık yaz.
Şu tarz kalıplardan ilham al (birebir kopyalama):
"Bilim Dünyasının Sakladığı Gerçek", "Kimsenin Bilmediği
Hikaye", "Onu Çıldırtan Keşif" gibi.
Kısa, çarpıcı, tek satır.

AÇIKLAMA:
1-2 kısa Türkçe cümle.

ETİKETLER:
8-12 adet Türkçe etiket, virgülle ayrılmış.
# kullanma.

ÇIKTIYI TAM OLARAK ŞU FORMATTA VER:

KONU:
...

BAŞLIK:
...

METİN:
...

AÇIKLAMA:
...

ETİKETLER:
...
"""

    return call_gemini_with_retry(prompt)

def parse(text):

    text = clean_text(text)

    def extract(field, next_field):
        pattern = rf"{field}\s*:\s*(.*?)(?=\s*{next_field}\s*:|$)"
        m = re.search(pattern, text, re.I | re.S)
        return m.group(1).strip() if m else ""

    topic = extract("KONU", "BAŞLIK")
    title = extract("BAŞLIK", "METİN")
    script = extract("METİN", "AÇIKLAMA")
    description = extract("AÇIKLAMA", "ETİKETLER")

    m = re.search(r"ETİKETLER\s*:\s*(.*)", text, re.I | re.S)
    tags = m.group(1).strip() if m else ""

    return {
        "topic": topic,
        "title": title,
        "script": script,
        "description": description,
        "tags": tags,
        "word_count": len(script.split())
    }

def main():

    print("=" * 60)
    print("      SHORTS KONU + İÇERİK MOTORU (TEK İSTEK)")
    print("=" * 60)

    history = load_history()

    avoid_list_text = (
        "\n".join(f"- {t}" for t in history)
        if history
        else "(henüz yok)"
    )

    parsed = None

    for attempt in range(3):

        try:
            raw = generate(avoid_list_text)
            candidate = parse(raw)

            topic = candidate["topic"].strip()
            script = candidate["script"].strip()

            history_lower = [
                x.strip().lower()
                for x in history
            ]

            if (
                is_valid_topic(topic)
                and script
                and len(script.split()) >= 25
                and topic.lower() not in history_lower
            ):
                parsed = candidate
                break

            print(
                f"   ⚠️ Geçersiz/tekrar konu veya boş metin geldi "
                f"({topic!r}), yeniden deneniyor..."
            )

        except Exception as e:
            print("   ⚠️ Üretim hatası:", e)

            if attempt < 2:
                time.sleep(5)

    if not parsed:
        raise SystemExit(
            "❌ Yapay zeka geçerli bir konu+içerik üretemedi."
        )

    print()
    print("🎯 Konu:", parsed["topic"])
    print("🎬 Başlık:", parsed["title"])
    print("✅ Hazır |", parsed["word_count"], "kelime")

    history.append(parsed["topic"])
    save_history(history)

    os.makedirs(OUT, exist_ok=True)

    with open(TOPIC_FILE, "w", encoding="utf-8") as f:
        f.write(parsed["topic"])

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "count": 1,
        "contents": [parsed]
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 60)
    print("SHORTS İÇERİĞİ TAMAMLANDI (1 istek)")
    print("=" * 60)
    print("Dosya:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
