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

Görüntülerdeki bilgilere (takımlar, oranlar, form, gol istatistikleri, geçmiş maçlar) dayanarak şunları yap:

1. Maçı ve görüntüde gördüğün önemli verileri kısaca özetle.
2. Oranlardan ima edilen olasılıkları hesapla (1/oran, sonra bahis payını çıkarmak için normalize et).
3. Takımların durumunu karşılaştır (form, gol atma/yeme eğilimi, varsa aralarındaki geçmiş maçlar).
4. Şu pazarlar için kendi yorumunu ve yaklaşık yüzdeni ver: Maç Sonucu (1-X-2), Karşılıklı Gol (KG Var/Yok), 2.5 Alt/Üst.
5. Kendi yorumunla oranların söylediğini karşılaştır: oran mantıklı mı, şişirilmiş mi?
6. Kısa bir sonuç yaz.

Kurallar: Sadece görüntüde gördüğün bilgilere dayan, görmediğin veriyi uydurma. Eksik veri varsa bunu belirt.
Bu bir tahmin, kesin sonuç değil; bunu en sonda tek cümleyle hatırlat. Türkçe yaz."""

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


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
                        cevap = client.models.generate_content(model=model, contents=parcalar)
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
                        time.sleep(4)  # yoğunluk: biraz bekle, tekrar dene
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
