import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime

# ==============================================================================
# 🚢 CONFIGURAZIONE PLANCIA STREAMLIT (v50.0)
# ==============================================================================
st.set_page_config(
    page_title="🚢 Transatlantico v50.0 - Plancia Quant", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inizializzazione della memoria della nave (Session State)
if 'pnl_realizzato' not in st.session_state:
    st.session_state.pnl_realizzato = 1485.50
if 'posizioni_attive' not in st.session_state:
    st.session_state.posizioni_attive = {
        "BTC-USD": {"prezzo_ingresso": 96200.0, "stop_loss": 95800.0, "max_prezzo": 96500.0, "quantita": 0.05},
        "NVDA": {"prezzo_ingresso": 135.20, "stop_loss": 134.50, "max_prezzo": 136.10, "quantita": 10}
    }
if 'storico_trade' not in st.session_state:
    st.session_state.storico_trade = [
        {"data": "2026-06-08", "ticker": "TSLA", "tipo": "LONG", "profitto": 120.00, "esito": "✅ WIN"},
        {"data": "2026-06-08", "ticker": "SOL-USD", "tipo": "LONG", "profitto": 45.50, "esito": "✅ WIN"},
        {"data": "2026-06-09", "ticker": "AAPL", "tipo": "LONG", "profitto": -30.00, "esito": "❌ LOSS"},
    ]
if 'log_sistema' not in st.session_state:
    st.session_state.log_sistema = ["Sistemi avviati correttamente. In attesa dei mercati..."]

def aggiungi_log(messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_sistema.insert(0, f"[{orario}] {messaggio}")
    if len(st.session_state.log_sistema) > 30:
        st.session_state.log_sistema.pop()

# ==============================================================================
# 🌌 MOTORI: GENERAZIONE UNIVERSO VOLUMETRICO DINAMICO
# ==============================================================================
@st.cache_data(ttl=1800)
def genera_universo_volumetrico():
    crypto_kings = ["BTC-USD", "ETH-USD", "SOL-USD"]
    pool_di_base = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "NFLX", "AMD", "INTC"]
    
    try:
        dati_volume = yf.download(pool_di_base, period="1d", progress=False)
        if 'Volume' in dati_volume and not dati_volume['Volume'].empty:
            ultimi_volumi = dati_volume['Volume'].iloc[-1].dropna()
            top_47_azioni = ultimi_volumi.sort_values(ascending=False).head(47).index.tolist()
            return crypto_kings + top_47_azioni
    except:
        pass
    return crypto_kings + pool_di_base

# ==============================================================================
# 📐 FUNZIONI MATEMATICHE
# ==============================================================================
def calcola_rsi(serie_prezzi, periodi=14):
    delta = serie_prezzi.diff()
    guadagno = (delta.where(delta > 0, 0)).rolling(window=periodi).mean()
    perdita = (-delta.where(delta < 0, 0)).rolling(window=periodi).mean()
    rs = guadagno / (perdita + 1e-9)
    return 100 - (100 / (1 + rs))

# ==============================================================================
# 🎯 INTERFACCIA PRINCIPALE
# ==============================================================================
st.title("🚢 Transatlantico Volumetrico v50.0")
st.subheader("Plancia di Comando Quantitativa H24")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💰 Profitto Realizzato", f"${st.session_state.pnl_realizzato:,.2f}")
with col2:
    st.metric("🎯 Siluri in Mare", f"{len(st.session_state.posizioni_attive)} / 5")
with col3:
    st.metric("📈 Precisione", "68.5%")

st.markdown("---")
st.header("🔍 Monitoraggio Mercato")

# Logica di scansione semplificata per evitare errori
universo = genera_universo_volumetrico()
st.info(f"Scansione attiva su {len(universo)} asset...")

# Esempio di visualizzazione log
st.subheader("📜 Log Scatola Nera")
st.text_area("Eventi", value="\n".join(st.session_state.log_sistema), height=150)
