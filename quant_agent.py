import streamlit as st
import pandas as pd
import json
import os
import requests  # 🛰️ Necessaria per il collegamento alla cassaforte cloud
from datetime import datetime

# ==========================================
# 1. IMPOSTAZIONI PAGINA & STILE TERMINALE
# ==========================================
st.set_page_config(layout="wide", page_title="Quant Agent Elite Terminal v38.1", page_icon="📈")

# Forziamo un look pulito e compatto stile plancia di comando
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .metric-box { padding: 10px; background: white; border-radius: 5px; box-shadow: 0px 1px 3px rgba(0,0,0,0.1); }
    </style>
""", unsafe_allow_html=True) # 🟢 Parametro corretto al singolare

MEMORY_FILE = "quant_bot_memory_v38.json"

# ==========================================
# 2. GESTIONE SCATOLA NERA IBRIDA (LOCALE + CASSAFORTE CLOUD)
# ==========================================
def carica_scatola_nera():
    default_data = {"registro": [], "cassa_incassata": 0.0}
    
    # 🛡️ PASSO A: Se mancano le chiavi cloud (come sul PC locale), lavora sul disco fisso
    if "GITHUB_TOKEN" not in st.secrets or "GIST_ID" not in st.secrets:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r") as f:
                    dati = json.load(f)
                    if isinstance(dati, dict):
                        dati.setdefault("registro", [])
                        dati.setdefault("cassa_incassata", 0.0)
                        return dati
                return default_data
            except: 
                return default_data
        return default_data
        
    # 🛰️ PASSO B: Se rileva le chiavi nel cloud, si connette alla cassaforte remota blindata
    try:
        token = st.secrets["GITHUB_TOKEN"]
        gist_id = st.secrets["GIST_ID"]
        url = f"https://api.github.com/gists/{gist_id}"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            gist_data = res.json()
            content = gist_data['files']['quant_bot_memory_v38.json']['content']
            return json.loads(content)
    except:
        return default_data
    return default_data

def salva_in_scatola_nera(asset, profitto, nota):
    dati = carica_scatola_nera()
    nuovo_trade = {
        "Orario": datetime.now().strftime("%H:%M:%S"),
        "Asset": asset,
        "Profitto [$]": round(profitto, 2),
        "Note": nota
    }
    dati["registro"].append(nuovo_trade)
    dati["cassa_incassata"] = round(dati["cassa_incassata"] + profitto, 2)
    
    # 1. Salva sempre una copia locale di backup (funziona sia su PC che su Cloud temporaneamente)
    with open(MEMORY_FILE, "w") as f:
        json.dump(dati, f, indent=4)
        
    # 2. Se siamo sul Cloud, spara l'aggiornamento istantaneo alla cassaforte remota GitHub Gist
    if "GITHUB_TOKEN" in st.secrets and "GIST_ID" in st.secrets:
        try:
            token = st.secrets["GITHUB_TOKEN"]
            gist_id = st.secrets["GIST_ID"]
            url = f"https://api.github.com/gists/{gist_id}"
            headers = {"Authorization": f"token {token}"}
            payload = {
                "files": {
                    "quant_bot_memory_v38.json": {
                        "content": json.dumps(dati, indent=4)
                    }
                }
            }
            requests.patch(url, headers=headers, json=payload)
        except:
            pass
            
    return dati

# Inizializzazione Session State Protetta 🟢
if "scatola_nera" not in st.session_state:
    st.session_state.scatola_nera = carica_scatola_nera()

# ==========================================
# 3. SIDEBAR - PANNELLO DEI CURSORI TATTICI
# ==========================================
st.sidebar.markdown("### 🔌 API Alpaca")
attiva_reale = st.sidebar.checkbox("🔴 ATTIVA CAPITALE REALE (DAL VIVO)", value=True)
st.sidebar.text_input("Chiave API Alpaca", type="password", value="STUB_KEY_ALREADY_SET")
st.sidebar.text_input("Chiave Segreta Alpaca", type="password", value="STUB_SECRET_ALREADY_SET")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Target & Protezioni Fast 2M")
soglia_trailing = st.sidebar.slider("Soglia Attivazione Trailing (%)", 0.10, 3.00, 0.60, step=0.10)
distanza_trailing = st.sidebar.slider("Distanza Inseguimento Trailing (%)", 0.05, 1.50, 0.30, step=0.05)
stop_loss_fisso = st.sidebar.slider("Stop loss Iniziale Fisso (%)", -5.00, -0.50, -1.00, step=0.10)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Configurazione Sgancio")
st.sidebar.number_input("Cap Massimo Posizioni Contemporanee", value=65)
st.sidebar.checkbox("⚡ Filtro Velocità di Caduta", value=True)
st.sidebar.slider("Caduta Minima RSI", 10, 90, 50)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔵 Nucleo Flotta (Maggiore 2M)")
rsi_core = st.sidebar.slider("RSI Ingresso Core (2m)", 10, 90, 75)
st.sidebar.number_input("Dimensione Trade Core ($)", value=100)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🦅 Cacciatore Speculativo (CHAOS 2M)")
attiva_hunter = st.sidebar.checkbox("🔥 Attiva Cacciatore Speculativo", value=True)
rsi_hunter = st.sidebar.slider("RSI Ingresso Hunter (2m)", 10, 90, 75)
st.sidebar.number_input("Dimensione Trade Hunter ($)", value=100)

# Bottone Svuota Registro con pulizia sincronizzata (Locale + Cloud)
if st.sidebar.button("🗑️ Svuota Registro Scatola Nera"):
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
    st.session_state.scatola_nera = {"registro": [], "cassa_incassata": 0.0}
    if "GITHUB_TOKEN" in st.secrets and "GIST_ID" in st.secrets:
        try:
            token = st.secrets["GITHUB_TOKEN"]
            gist_id = st.secrets["GIST_ID"]
            url = f"https://api.github.com/gists/{gist_id}"
            headers = {"Authorization": f"token {token}"}
            payload = {"files": {"quant_bot_memory_v38.json": {"content": json.dumps(st.session_state.scatola_nera, indent=4)}}}
            requests.patch(url, headers=headers, json=payload)
        except:
            pass
    st.rerun()

# ==========================================
# 4. CONFIGURAZIONE UNIVERSI ASSET REVISIONATI
# ==========================================
universo_core = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD"]
universo_hunter = [
    "DOGE-USD", "SHIB-USD", "PEPE-USD", "WIF-USD", "BONK-USD", 
    "FLOKI-USD", "POPCAT-USD", "BOME-USD", "TURBO-USD", "AVAX-USD",
    # "LINK-USD", "NEAR-USD", "FET-USD", "SUI-USD", "APT-USD", "RENDER-USD",
    # "GALA-USD", "FTM-USD", "Jasmy-USD", "ICP-USD", "LUNC-USD", "TAO-USD", "RUNE-USD", 
    # "GRT-USD", "FIL-USD", "OM-USD", "W-USD", "CHZ-USD", "1INCH-USD", "STX-USD", "ATOM-USD",
    # "HOME-USD", "WLD-USD", "ARRR-USD", "STG-USD", "HYPE-USD", "BIO-USD", "XLM-USD", 
    # "FARTCOIN-USD", "BCH-USD", "ZIG-USD", "DEXE-USD", "BRETT-USD", "PYTH-USD", "PENDLE-USD", 
    # "MON-USD", "ORDI-USD", "ARB-USD", "INJ-USD", "ZK-USD", "HNT-USD", "ACH-USD", 
    # "STRK-USD", "SPX-USD", "ENA-USD"
]



# ==========================================
# 5. CORPO PRINCIPALE - INTERFACCIA PLANCIA
# ==========================================
st.markdown("## 📊 Quant Agent Elite Terminal v38.1 — SCATOLA CORAZZATA")
st.success("💾 **SCATOLA NERA ATTIVA:** storico profitti e tracciamento picchi salvati istantaneamente sia sul disco che sulla rete cloud.")

# --- BILANCIO CONTO REALE ---
st.markdown("### 💰 Bilancio del Conto Real-Time")
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Liquidità Cash Disponibile", "$88.449,68")
with c2:
    st.metric("Valore Asset Correnti", "7.756,51 $")
with c3:
    st.metric("PATRIMONIO NETTO COMPLESSIVO", "$96.203,88")

st.markdown("---")

# --- REGISTRO PROFITTI (SCATOLA NERA VISIVA CON LETTURA PROTETTA) ---
st.markdown("### 📦 Registro Profitti Unificato (Cassa Protetta su Disco)")
col_cassa, col_tabella = st.columns([1, 4])

with col_cassa:
    cassa_val = st.session_state.scatola_nera.get("cassa_incassata", 0.0)
    colore_cassa = "🟩" if cassa_val >= 0 else "🟥"
    st.metric("CASSA INCASSATA", f"{colore_cassa} ${cassa_val}")

with col_tabella:
    if st.session_state.scatola_nera.get("registro"):
        df_registro = pd.DataFrame(st.session_state.scatola_nera["registro"])
        st.dataframe(df_registro.iloc[::-1], use_container_width=True)
    else:
        st.info("Nessuna operazione registrata nel ciclo attuale.")

st.markdown("---")

# --- POSIZIONI ATTIVE & INSEGUIMENTO DINAMICO ---
st.markdown("### 🗃️ Posizioni Attive & Inseguimento Dinamico (2M)")

posizioni_mock = [
    {"Asset": "AAPL", "P&L (%)": -0.85, "Picco Max (%)": -0.85, "Valore Mercato": "$0.98", "RSI 2m": 37.8, "ALM SCORE": "40/100", "Modalità Stop": "🛡️ Protezione Lineare"},
    {"Asset": "AMZN", "P&L (%)": -0.02, "Picco Max (%)": -0.02, "Valore Mercato": "$0.58", "RSI 2m": 41.7, "ALM SCORE": "43/100", "Modalità Stop": "🛡️ Protezione Lineare"},
    {"Asset": "COIN", "P&L (%)": 0.55, "Picco Max (%)": 0.55, "Valore Mercato": "$1.02", "RSI 2m": 71.2, "ALM SCORE": "50/100", "Modalità Stop": "🛡️ Protezione Lineare"},
    {"Asset": "DOGE-USD", "P&L (%)": 1.34, "Picco Max (%)": 1.54, "Valore Mercato": "$200.55", "RSI 2m": 53.1, "ALM SCORE": "55/100", "Modalità Stop": "🚀 TRAILING ATTIVO (Freno 1.24%)"},
    {"Asset": "MARA", "P&L (%)": -2.07, "Picco Max (%)": -2.07, "Valore Mercato": "$1.05", "RSI 2m": 64.3, "ALM SCORE": "31/100", "Modalità Stop": "🛡️ Protezione Lineare"},
    {"Asset": "NVDA", "P&L (%)": -0.47, "Picco Max (%)": -0.47, "Valore Mercato": "$0.00", "RSI 2m": 40.1, "ALM SCORE": "50/100", "Modalità Stop": "🛡️ Protezione Lineare"},
]
df_posizioni = pd.DataFrame(posizioni_mock)
st.dataframe(df_posizioni, use_container_width=True)
st.caption(f"Stiva Attuale: {len(df_posizioni)} asset attivi / Limite Max: 65.")

st.markdown("---")

# --- SCANNER REAL-TIME FLOTTE ---
st.markdown("### 🔹 Scanner Real-Time Scalping: Flotta Crypto Major (Candele 2m)")
crypto_major_mock = [
    {"Asset": "BTC-USD", "Prezzo": "$67.453,20", "RSI 2m": 57.1, "ALM SCORE": "💙 82/100", "Fiche Sganciata": "$100.00", "Stato": "💻 APERTO"},
    {"Asset": "ETH-USD", "Prezzo": "$3.521,40", "RSI 2m": 52.0, "ALM SCORE": "💙 68/100", "Fiche Sganciata": "$100.00", "Stato": "💻 APERTO"},
    {"Asset": "SOL-USD", "Prezzo": "$154.55", "RSI 2m": 54.0, "ALM SCORE": "💙 65/100", "Fiche Sganciata": "$100.00", "Stato": "💻 APERTO"},
]
st.dataframe(pd.DataFrame(crypto_major_mock), use_container_width=True)

st.markdown("### 🔸 Scanner Real-Time Scalping: Flotta Meme, AI & Altcoin Estesa (Frequenza 2m)")
hunter_mock = [
    {"Asset": token, "Prezzo": "In Scansione...", "RSI 2m": "Calcolo...", "ALM SCORE": "Analisi...", "Fiche Sganciata": f"${rsi_hunter}", "Stato": "📡 IN STIVA"}
    for token in universo_hunter[:5]
]
st.dataframe(pd.DataFrame(hunter_mock), use_container_width=True)

# Bottone di test simulato per la chiusura dei trade
if st.checkbox("Simula Chiusura Trade Real-Time (Test Meccanica)"):
    if st.button("Sgancia Profitto ADA-USD +$10.06"):
        st.session_state.scatola_nera = salva_in_scatola_nera("ADA-USD", 10.06, "Trailing (1.20%)")
        st.rerun()
