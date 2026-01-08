import streamlit as st
import requests

# ================= CONFIG =================
API_URL = "http://127.0.0.1:8000/chat"

st.set_page_config(
    page_title="Olist Analytics AI",
    page_icon="🛒",
    layout="wide"
)

# ================= HEADER =================
st.title("🛒 Olist Analytics AI")
st.caption(
    "Multi-Agent Analytics System (SQL • RAG • Seller Performance)"
)

st.divider()

# ================= SIDEBAR =================
st.sidebar.header("📌 Demo Capabilities")

st.sidebar.markdown("""
**SQL Analytics**
- Rata-rata harga per kategori  
- Daftar kategori produk  

**RAG (Review Analysis)**
- Produk / kategori dengan ulasan positif  

**Seller Performance**
- Perbandingan performa seller antar kota  
""")

st.sidebar.divider()

st.sidebar.markdown("""
**Contoh Pertanyaan**
- Ada kategori apa saja di dataset?
- Harga rata rata dari produk kategori furniture?
- Produk apa yang paling sering direview positif?
- Bandingkan performa seller di São Paulo dan Rio de Janeiro
""")

# ================= INPUT =================
st.subheader("💬 Ajukan Pertanyaan")

query = st.text_input(
    "Masukkan pertanyaan Anda:",
    placeholder="Contoh: Bandingkan performa seller di São Paulo dan Rio de Janeiro"
)

ask = st.button("🔍 Jalankan Analisis")

# ================= RESPONSE =================
if ask and query:
    with st.spinner("Memproses pertanyaan..."):
        try:
            response = requests.post(
                API_URL,
                json={"query": query},
                timeout=30
            )

            if response.status_code != 200:
                st.error(
                    f"❌ Backend error ({response.status_code})"
                )
            else:
                answer = response.json().get("answer")

                st.success("✅ Jawaban berhasil dihasilkan")
                st.markdown("### 📊 Hasil Analisis")
                st.write(answer)

        except requests.exceptions.ConnectionError:
            st.error(
                "❌ Tidak dapat terhubung ke backend FastAPI.\n\n"
                "Pastikan backend sudah dijalankan:\n"
                "`uvicorn app_updated:app`"
            )

        except Exception as e:
            st.error(f"❌ Terjadi kesalahan: {e}")

elif ask and not query:
    st.warning("⚠️ Silakan masukkan pertanyaan terlebih dahulu.")

# ================= FOOTER =================
st.divider()
st.caption(
    "Capstone Project — Generative AI & Multi-Agent System | Olist Dataset"
)
