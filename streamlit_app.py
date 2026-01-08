import streamlit as st
import requests

BACKEND_URL = "https://olist-backend-420147884504.asia-southeast1.run.app"

st.set_page_config(
    page_title="Olist Capstone",
    layout="centered"
)

st.title("📦 Olist Capstone Project")
st.caption("Streamlit frontend • Google Cloud Run backend")

query = st.text_area(
    "Enter your question",
    placeholder="Apa kategori yang tersedia di dataset?"
)

if st.button("Submit"):
    if not query.strip():
        st.warning("Please enter a query")
    else:
        with st.spinner("Processing..."):
            try:
                res = requests.post(
                    f"{BACKEND_URL}/chat",
                    json={"query": query},
                    timeout=30
                )

                if res.status_code == 200:
                    data = res.json()
                    st.success("Response")
                    st.write(data["answer"])
                else:
                    st.error(f"Backend error ({res.status_code})")
                    st.text(res.text)

            except requests.exceptions.RequestException as e:
                st.error("Cannot connect to backend")
                st.text(e)
