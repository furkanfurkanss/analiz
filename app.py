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

# Model çalışmazsa burayı Google AI Studio'daki güncel bir Flash modeliyle değiştir.
MODEL = "gemini-flash-latest"

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

    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    with st.spinner("Analiz ediliyor..."):
        try:
            cevap = client.models.generate_content(model=MODEL, contents=parcalar)
            st.markdown(cevap.text)
        except Exception as e:
            st.error(f"Hata oluştu: {e}")

st.caption("Tahminler eğlence ve analiz amaçlıdır, kesin sonuç değildir.")
