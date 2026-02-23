# pyre-ignore-all-errors
import streamlit as st
import requests
import json

st.set_page_config(page_title="RAG Data Platform", layout="wide")

st.title("🚗 OEM RAG Campaign Manager Platform")
st.markdown("This interface visualizes the **Phase 1: Ingestion & Extraction Core** allowing operators to upload PDFs and verify real-time Voice-Agent data retrievals.", unsafe_allow_html=True)

# URL of FastAPI backend
import os
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/retrieval")

tab1, tab2 = st.tabs(["Ingestion (Upload Brochure)", "Voice Retrieval (Query Data)"])

with tab1:
    st.header("Upload New Campaign PDF")
    
    col1, col2 = st.columns(2)
    with col1:
        oem_id = st.text_input("OEM ID", value="maruti_suzuki")
        campaign_id = st.text_input("Campaign ID", value="wagonr_2024_launch")
        model_code = st.text_input("Model Code", value="wagonr")
        model_year = st.number_input("Model Year", value=2024, min_value=2000, max_value=2030)
        
    with col2:
        region = st.text_input("Region", value="IN")
        engine_code = st.text_input("Engine Configuration (Base)", value="K12N")
        transmission = st.text_input("Transmission (Base)", value="AMT")
        fuel_type = st.text_input("Fuel Type", value="petrol")

    uploaded_file = st.file_uploader("Upload Automobile Brochure (PDF)", type=["pdf"])

    if st.button("Extract and Ingest Data to RAG Engine"):
        if uploaded_file is not None:
            with st.spinner("Classifying Pages and Extracting Layout matrices..."):
                payload = {
                    "oem_id": oem_id,
                    "campaign_id": campaign_id,
                    "model_code": model_code,
                    "model_year": str(model_year),
                    "region": region,
                    "engine_code": engine_code,
                    "transmission": transmission,
                    "fuel_type": fuel_type
                }
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                
                try:
                    res = requests.post(f"{BACKEND_URL}/upload", data=payload, files=files)
                    if res.status_code == 200:
                        data = res.json()
                        st.success(data.get("message"))
                    else:
                        st.error(f"Error {res.status_code}: {res.text}")
                except Exception as e:
                    st.error(f"Backend Connection Error: {e}")
        else:
            st.warning("Please upload a PDF file first.")

with tab2:
    st.header("Voice Agent Sandbox Query")
    st.write("Simulate a query hitting the cache resolver using entity states.")
    
    col3, col4 = st.columns(2)
    with col3:
        q_oem = st.text_input("Query OEM", value="maruti_suzuki")
        q_campaign = st.text_input("Query Campaign", value="wagonr_2024_launch")
        q_model = st.text_input("Query Model", value="wagonr")
        q_year = st.number_input("Query Year", value=2024)
        
    with col4:
        q_region = st.text_input("Query Region", value="IN")
        q_trim = st.text_input("Inferred Trim (E.g. VXi, ZXi)", value="VXi")
        q_engine = st.text_input("Inferred Engine", value="K12N")
        q_trans = st.text_input("Inferred Transmission", value="AMT")
        q_fuel = st.text_input("Inferred Fuel", value="petrol")

    st.markdown("---")
    
    # Dynamic text input to test Ontology resolution
    target_feature = st.text_input(
        "Voice Request Feature Intent (e.g., 'Smartplay Studio', 'River Crossing')", 
        value="Smartplay Studio"
    )

    if st.button("Execute Vector/Hash Cache Search"):
        with st.spinner("Routing Query Through Spec Resolver..."):
            query_payload = {
                "oem_id": q_oem,
                "campaign_id": q_campaign,
                "model_code": q_model,
                "model_year": q_year,
                "region": q_region,
                "trim": q_trim,
                "engine_code": q_engine,
                "transmission": q_trans,
                "fuel_type": q_fuel,
                "feature_id": target_feature
            }
            try:
                res = requests.post(f"{BACKEND_URL}/query", json=query_payload)
                if res.status_code == 200:
                    result = res.json()
                    st.success(f"**🗣️ Agent Speech:** {result['answer']}")
                    
                    st.markdown("### Metadata Breakdown")
                    st.json(result)
                else:
                    st.error(f"Lookup Failed (Code {res.status_code}): {res.text}")
            except Exception as e:
                 st.error(f"Backend Connection Error: {e}")
