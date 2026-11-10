import time

import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="Maç Analiz", page_icon="⚽")
st.title("⚽ Maç Analiz")

# --- Basit şifre koruması (linki bulan başkaları kullanmasın diye) ---
sifre = st.text_input("Şifre", type="password")
if sifre != st.secrets["APP_PASSWORD"]:
    st.stop()

PROMPT = """Sana bir bahis sitesinden (Nesine) maç ekran görüntüsü/görüntüleri veriyorum.

Görüntüdeki TÜM pazarlara bak: Maç Sonucu, Çifte Şans, Handikaplı Maç Sonucu, Alt/Üst (1.5, 2.5, 3.5, 4.5), Karşılıklı Gol, Yarı Sonucu, Yarı Alt/Üst,
Takım Alt/Üst, Toplam Gol Aralığı, Tek/Çift, Maç Sonucu + Alt/Üst birleşikleri vb. Sadece MS, KG ve 2.5 ile sınırlı kalma.
Takım formu, puan durumu, geçmiş maç bilgisi görüntüde varsa kullan; yoksa sadece oranlardan çıkarım yaptığını belirt.

CEVABI KISA VER, hesaplama gösterme, uzun açıklama yazma. Tam olarak şu formatta yaz:

**Maç:** takım adları

**En çok gelmesi muhtemel 4-5 seçenek** (oranı düşük de olsa fark etmez, gerçekleşme ihtimali en yüksek olanlar):
- Pazar — oran — tahmini %olasılık — tek kısa cümle neden

**Yüksek oranlı, gelme ihtimali makul 2-3 seçenek** (değerli olabilecekler):
- Pazar — oran — tahmini %olasılık — tek kısa cümle neden

**Uzak dur:** 1-2 pazar ve tek cümle neden

**Genel yorum:** en fazla 2 cümle.

Kurallar: Oranları görüntüden aynen oku, okuyamadığını veya görmediğin veriyi uydurma. Türkçe yaz.
Son satıra tek cümleyle bunun kesin değil, tahmin olduğunu yaz."""

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# Uzun "düşünme" süresini kapatır, cevap çok daha hızlı gelir
HIZLI = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0),
    max_output_tokens=1200,
)


@st.cache_data(ttl=3600)
def model_bul(_client):
    """Google'ın o an sunduğu uygun bir Flash modelini otomatik bulur."""
    adaylar = []
    for m in _client.models.list():
        ad = m.name.replace("models/", "")
        eylemler = getattr(m, "supported_actions", None) or []
        if "generateContent" not in eylemler:
            continue
        if "flash" not in ad:
            continue
        if any(x in ad for x in ["image", "tts", "live", "audio", "lite", "thinking", "robotics", "computer"]):
            continue
        adaylar.append(ad)
    # Önce "preview/exp" olmayanlar, sonra en yeni sürüm adı
    adaylar.sort(key=lambda a: (not any(x in a for x in ["preview", "exp"]), a), reverse=True)
    return adaylar


dosyalar = st.file_uploader(
    "Maç ekran görüntüsü (birden fazla yükleyebilirsin)",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=True,
)
not_ = st.text_input("Eklemek istediğin not (isteğe bağlı)", placeholder="Örn: X oyuncusu sakat")

if st.button("Analiz et", disabled=not dosyalar):
    parcalar = [
        types.Part.from_bytes(data=d.getvalue(), mime_type=d.type) for d in dosyalar
    ]
    metin = PROMPT + (f"\n\nEk not: {not_}" if not_ else "")
    parcalar.append(metin)

    with st.spinner("Analiz ediliyor..."):
        try:
            modeller = model_bul(client)
            if not modeller:
                st.error("Uygun model bulunamadı. API anahtarını kontrol et.")
                st.stop()
            son_hata = None
            basarili = False
            gecici = ["404", "NOT_FOUND", "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "500", "INTERNAL"]
            for model in modeller[:5]:
                for deneme in range(3):
                    try:
                        try:
                            cevap = client.models.generate_content(
                                model=model, contents=parcalar, config=HIZLI
                            )
                        except Exception as e0:
                            # Model bu hızlı ayarı desteklemiyorsa ayarsız dene
                            if "INVALID_ARGUMENT" in str(e0) or "thinking" in str(e0).lower():
                                cevap = client.models.generate_content(
                                    model=model, contents=parcalar
                                )
                            else:
                                raise
                        st.markdown(cevap.text)
                        st.caption(f"Kullanılan model: {model}")
                        basarili = True
                        break
                    except Exception as e:
                        son_hata = e
                        hata = str(e)
                        if not any(k in hata for k in gecici):
                            break  # geçici olmayan hata, denemeyi bırak
                        if "404" in hata or "NOT_FOUND" in hata:
                            break  # bu model yok, sıradakine geç
                        time.sleep(2)  # yoğunluk: biraz bekle, tekrar dene
                if basarili:
                    break
                if son_hata is not None and not any(k in str(son_hata) for k in gecici):
                    break
            if not basarili:
                st.error(
                    "Google şu an yoğun veya limit doldu. Birkaç dakika bekleyip tekrar dene. "
                    f"(Ayrıntı: {son_hata})"
                )
        except Exception as e:
            st.error(f"Hata oluştu: {e}")

st.caption("Tahminler eğlence ve analiz amaçlıdır, kesin sonuç değildir.")
