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

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY bulunamadı.")

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
- Giordano Bruno'nun fikirleri yüzünden diri diri yakılması
- Évariste Galois'nın 20 yaşında düelloda ölmesi
- Vera Rubin'in karanlık madde keşfinin yıllarca göz ardı edilmesi
- Jocelyn Bell Burnell'in pulsar keşfinde göz ardı edilmesi
- Emmy Noether'in kadın olduğu için üniversitede maaş alamaması
- Ada Lovelace'in ilk programcı olarak tanınmadan ölmesi
- Katherine Johnson'un ırkçılığa rağmen NASA'da yükselmesi
- Srinivasa Ramanujan'ın İngiltere'de yalnızlıktan hastalanması
- Kurt Gödel'in paranoyadan açlıktan ölmesi
- John Nash'in şizofreniyle mücadelesi
- Antoine Lavoisier'in kimyayı bilim yapıp sonra idam edilmesi
"""


def clean_text(text):
    text = re.sub(r"\[[^\]]*\]", "", text or "")
    text = re.sub(r"\([^)]*\)", "", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_history():
    if os.path.exists(TOPIC_HISTORY_FILE):
        try:
            with open(TOPIC_HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
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
    if len(topic) < 8 or len(topic) > 200:
        return False
    if not re.search(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]{3,}", topic):
        return False
    if len(topic.split()) < 2:
        return False
    return True


def call_gemini_with_retry(prompt, max_retries=5):
    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-3.6-flash:generateContent"
    )

    delay = 5

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                url,
                params={"key": API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=120
            )

            if response.status_code in (429, 503):
                print(f"   ⏳ Gemini meşgul (HTTP {response.status_code}), "
                      f"{delay} sn bekleyip tekrar denenecek "
                      f"({attempt}/{max_retries})...")
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue

            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

        except requests.exceptions.RequestException as e:
            print(f"   ⚠️ Gemini isteği hatası: {e}, "
                  f"{delay} sn bekleyip tekrar denenecek "
                  f"({attempt}/{max_retries})...")
            time.sleep(delay)
            delay = min(delay * 2, 60)

    raise RuntimeError("Gemini API'ye ulaşılamadı (tüm denemeler başarısız).")


def generate(avoid_list_text):

    prompt = f"""
Sen "DAHİLER VE KEŞİFLER" adlı Türkçe bilgi YouTube kanalının
Shorts konu bulan VE içerik yazan editörüsün. Bu tek istekte
HEM konuyu seçeceksin HEM de o konu için Shorts metnini
yazacaksın.

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

1. ADIM - KONU SEÇ:
İzleyicinin "vay be, bunu bilmiyordum" diyeceği, çarpıcı,
meraklandırıcı, GERÇEK ve DOĞRULANABİLİR TEK BİR bilim
insanı/mucit/kaşif hikayesi seç. Konu MUTLAKA yukarıdaki
nişe (dramatik bilim insanı hikayesi) uymalı. Genel tarih,
uzay, hayvanlar, günlük eşyalar gibi başka konu türlerine
kayma.

KESİNLİKLE ŞU DAHA ÖNCE KULLANILAN KONULARI TEKRAR SEÇME
(bunlara çok benzer/aynı konuları da seçme):
{avoid_list_text}

2. ADIM - METNİ YAZ:
Seçtiğin konu hakkında 15-30 saniyede seslendirilebilecek,
kısa ve son derece çarpıcı bir YouTube Shorts anlatım metni
oluştur.

AMAÇ:
İzleyicinin daha ilk cümlede durup videoyu izlemeye devam
etmesini sağlamak. İzleyici hiçbir anda sıkılıp kaydırmamalı.
Metin boyunca kişinin insani tarafını (korku, umut, acı,
haksızlık, zafer) hissettir.

ÇOK ÖNEMLİ:
- Bilgi uydurma, tarihi ve bilimsel gerçeklere sadık kal.
- Doğrulanamayan bilgiyi kesin gerçek gibi sunma.
- Gazete/haber dili kullanma, sıcak bir anlatıcı gibi konuş.
- Gereksiz detaya girme, sadece en çarpıcı 1-2 bilgiye odaklan.
- Konuyla alakasız hiçbir şey ekleme.
- Siyasi propaganda, savaş suçluları, diktatörler, hakaret veya
  kışkırtıcı dil/içerik kullanma.

KANAL TARZI:
- Türkçe.
- Doğal, akıcı, sıcak anlatıcı sesi.
- Kısa ve vurucu cümleler.
- İLK CÜMLE bir soru, şaşırtıcı bir gerçek veya çarpıcı bir
  iddia ile başlamalı ve izleyiciyi anında yakalamalı.
- KESİNLİKLE ŞU AÇILIŞLARI KULLANMA: "Biliyor muydunuz ki", "Az
  bilinen bir gerçek", "Şunu biliyor musun", "İşte size ...
  hakkında X şey", "Bugün size ... anlatacağım", "Hazır
  mısınız", herhangi bir selamlama veya kanal/konu tanıtımıyla
  başlamak.
- Bunun yerine şu açılış tarzlarından birini kullan (her
  seferinde farklısını dene):
  1) Doğrudan şok edici bir iddiayla aç.
  2) Beklenmedik bir soruyla aç, "biliyor musunuz" kalıbını
     kullanmadan.
  3) Ortadan başlayan bir sahneyle aç.
- Açılış cümlesi en fazla 8-10 kelime olsun, tek nefeste
  söylenebilmeli.
- "Merhaba arkadaşlar" gibi giriş yapma.
- Video ortasında hiç durgunluk olmasın.
- SON CÜMLE izleyicide "bir daha izlemek" hissi uyandırmalı,
  mümkünse ("loop-friendly") bir çarpıcı kapanışla bitsin.
- Kamera/sahne açıklaması, müzik/efekt, parantez içi açıklama
  yazma.

BAŞLIK:
- Özgün, merak uyandıran, ama yanıltıcı clickbait olmayan.
- Videoda anlatılmayan şeyi vaat etmemeli.

METİN:
Yaklaşık 40-75 kelime (15-30 saniyelik seslendirmeye uygun).
Sadece anlatıcının okuyacağı cümlelerden oluşsun.

AÇIKLAMA:
Videonun ne anlattığını 1-2 kısa cümleyle açıkla.

ETİKETLER:
8-12 adet alakalı Türkçe etiket, virgülle ayrılmış, hashtag (#)
kullanma.

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
        pattern = rf"{field}:\s*(.*?)(?=\s*{next_field}:|$)"
        m = re.search(pattern, text, re.I | re.S)
        return m.group(1).strip() if m else ""

    topic = extract("KONU", "BAŞLIK")
    title = extract("BAŞLIK", "METİN")
    script = extract("METİN", "AÇIKLAMA")
    description = extract("AÇIKLAMA", "ETİKETLER")

    m = re.search(r"ETİKETLER:\s*(.*)", text, re.I | re.S)
    tags = m.group(1).strip() if m else ""

    if not script:
        script = text

    words = len(script.split())

    if words < 30:
        print("[UYARI] Metin çok kısa:", words, "kelime")
    if words > 100:
        print("[UYARI] Metin çok uzun:", words, "kelime")

    return {
        "topic": topic,
        "title": title,
        "script": script,
        "description": description,
        "tags": tags,
        "word_count": words
    }


def main():

    print("=" * 60)
    print("      SHORTS KONU + İÇERİK MOTORU (TEK İSTEK)")
    print("=" * 60)

    history = load_history()
    avoid_list_text = "\n".join(f"- {t}" for t in history) if history else "(henüz yok)"

    parsed = None

    for attempt in range(3):
        try:
            raw = generate(avoid_list_text)
            candidate = parse(raw)

            if (
                candidate["topic"]
                and is_valid_topic(candidate["topic"])
                and candidate["topic"] not in history
                and candidate["script"]
            ):
                parsed = candidate
                break

            print(f"   ⚠️ Geçersiz/tekrar konu veya boş metin geldi "
                  f"({candidate.get('topic')!r}), yeniden deneniyor...")

        except Exception as e:
            print("   ⚠️ Üretim hatası:", e)
            time.sleep(5)

    if not parsed:
        raise SystemExit("❌ Yapay zeka geçerli bir konu+içerik üretemedi.")

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
        json.dump(result, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print("SHORTS İÇERİĞİ TAMAMLANDI (1 Gemini isteğiyle)")
    print("=" * 60)
    print("Dosya:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
