import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# Configurazione iniziale della pagina
st.set_page_config(page_title="Quant Agent Corazzata v38.5", layout="wide")

# --- RECUPERO CHIAVI FISSE DAI SECRETS ---
chiave_fissa_id = st.secrets.get("ALPACA_API_KEY_ID", "")
chiave_fissa_secret = st.secrets.get("ALPACA_API_SECRET_KEY", "")

# Barra laterale per le configurazioni e le chiavi
st.sidebar.header("🔑 Configurazione API Alpaca")
alpaca_key = st.sidebar.text_input("Alpaca API Key ID", value=chiave_fissa_id, type="password")
alpaca_secret = st.sidebar.text_input("Alpaca API Secret Key", value=chiave_fissa_secret, type="password")
trading_mode = st.sidebar.radio("Modalità Trading", ["Paper (Simulazione)", "Live (Reale)"])

if trading_mode == "Live (Reale)":
    BASE_URL = "https://api.alpaca.markets"
else:
    BASE_URL = "https://paper-api.alpaca.markets"

DATA_URL = "https://data.alpaca.markets/v1beta3/crypto/us/bars"

# Barra laterale per le munizioni e parametri trailing
st.sidebar.markdown("---")
st.sidebar.subheader("💰 Gestione Munizioni")
size_dollari = st.sidebar.slider("Capitale per Singolo Trade ($)", min_value=5, max_value=500, value=50, step=5)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parametri Trailing Stop")
trailing_activation = st.sidebar.slider("Attivazione Trailing Stop (%)", min_value=1.0, max_value=20.0, value=4.0, step=0.5)
trailing_distance = st.sidebar.slider("Distanza dallo Stop (% dal massimo)", min_value=0.5, max_value=5.0, value=1.5, step=0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("🏹 Strategia d'Ingresso")
tipo_strategia = st.sidebar.selectbox("Condizione d'Acquisto", ["Ipervenduto Classico (RSI < 35)", "Inseguimento FOMO (RSI > 65)"])

st.sidebar.markdown("---")
attiva_capitale = st.sidebar.checkbox("🚀 Attiva Trading Automatico", value=False)

if attiva_capitale:
    st.sidebar.warning("⚠️ CORAZZATA ARMATA: Il bot sparerà ordini in automatico!")

# --- IL NUOVO EQUIPAGGIO DI SELEZIONE (25 MONETE ATTIVE SU ALPACA) ---
EQUIPAGGIO = {
    "👑 I Re del Mercato": ["BTC/USD", "ETH/USD", "SOL/USD"],
    "⚡ Layer 1 & Altcoin Calde": ["AVAX/USD", "LINK/USD", "DOT/USD", "MATIC/USD", "ADA/USD", "LTC/USD", "XRP/USD", "BCH/USD", "NEAR/USD", "ATOM/USD"],
    "🌶️ Battaglione Meme & Speculazione": ["DOGE/USD", "SHIB/USD", "PEPE/USD", "WIF/USD", "BONK/USD"],
    "🔮 DeFi & Web3": ["UNI/USD", "AAVE/USD", "MKR/USD", "GRT/USD", "STX/USD", "IMX/USD", "LDO/USD"]
}

# Appiattiamo la lista per i cicli di scansione interni
tutti_i_soldati = [coin for cat in EQUIPAGGIO.values() for coin in cat]

# Inizializzazione sessioni
if "scatola_nera" not in st.session_state: st.session_state.scatola_nera = {}
if "storico_profitti" not in st.session_state: st.session_state.storico_profitti = []
if "errori_consecutivi" not in st.session_state: st.session_state.errori_consecutivi = 0

def calcola_rsi(prezzi, periodi=14):
    if len(prezzi) < periodi + 1: return 50.0
    variazioni = pd.Series(prezzi).diff()
    guadagni = variazioni.clip(lower=0)
    perdite = -variazioni.clip(upper=0)
    media_guadagni = guadagni.ewm(span=periodi, adjust=False).mean()
    media_perdite = perdite.ewm(span=periodi, adjust=False).mean()
    rs = media_guadagni / media_perdite.replace(0, 0.00001)
    return round((100 - (100 / (1 + rs))).iloc[-1], 2)

def ottieni_posizioni_reali(key, secret):
    url = f"{BASE_URL}/v2/positions"
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            st.session_state.errori_consecutivi = 0
            return {p["symbol"]: float(p["qty"]) for p in res.json()}
    except: st.session_state.errori_consecutivi += 1
    return {}

def ottieni_bilancio_conto(key, secret):
    url = f"{BASE_URL}/v2/account"
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            dati = res.json()
            return {"cash": round(float(dati["cash"]), 2), "portfolio_value": round(float(dati["portfolio_value"]), 2)}
    except: pass
    return {"cash": "0.0", "portfolio_value": "0.0"}

def invia_ordine_alpaca(simbolo, lato, qty_dollari, key, secret):
    url_ordine = f"{BASE_URL}/v2/orders"
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret, "Content-Type": "application/json"}
    payload = {"symbol": simbolo.replace("/", ""), "notional": str(qty_dollari), "side": lato, "type": "market", "time_in_force": "gtc"}
    try:
        res = requests.post(url_ordine, json=payload, headers=headers)
        return res.status_code == 200 or res.status_code == 201
    except: return False

def ottieni_e_trada_crypto(simbolo, posizioni_reali, key, secret):
    if not key or not secret: return {"Prezzo ($)": "Mancano chiavi", "RSI": "--", "Stato": "Attesa"}
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    params = {"symbols": simbolo, "timeframe": "2Min", "limit": 30}
    simbolo_clean = simbolo.replace("/", "")
    try:
        risposta = requests.get(DATA_URL, headers=headers, params=params)
        if risposta.status_code == 400 and "/" in simbolo:
            params["symbols"] = simbolo_clean
            risposta = requests.get(DATA_URL, headers=headers, params=params)
        if risposta.status_code == 200:
            dati = risposta.json()
            barre = dati.get("bars", {}).get(simbolo, dati.get("bars", {}).get(simbolo_clean, []))
            if barre:
                prezzi_chiusura = [b["c"] for b in barre]
                ultimo_prezzo = prezzi_chiusura[-1]
                rsi_attuale = calcola_rsi(prezzi_chiusura)
                ha_posizione_reale = simbolo_clean in posizioni_reali or simbolo in posizioni_reali
                stato = "🛰️ Radar"
                
                if not ha_posizione_reale and simbolo in st.session_state.scatola_nera:
                    del st.session_state.scatola_nera[simbolo]

                if attiva_capitale:
                    condizione = (rsi_attuale < 35) if "Ipervenduto" in tipo_strategia else (rsi_attuale > 65)
                    if condizione and not ha_posizione_reale:
                        if invia_ordine_alpaca(simbolo, "buy", size_dollari, key, secret):
                            st.session_state.scatola_nera[simbolo] = {"prezzo_acquisto": ultimo_prezzo, "prezzo_massimo": ultimo_prezzo}
                            st.toast(f"🛒 Inserito Soldato: {simbolo}", icon="🟢")
                    if ha_posizione_reale:
                        if simbolo not in st.session_state.scatola_nera:
                            st.session_state.scatola_nera[simbolo] = {"prezzo_acquisto": ultimo_prezzo, "prezzo_massimo": ultimo_prezzo}
                        dati_pos = st.session_state.scatola_nera[simbolo]
                        if ultimo_prezzo > dati_pos["prezzo_massimo"]:
                            st.session_state.scatola_nera[simbolo]["prezzo_massimo"] = ultimo_prezzo
                            dati_pos["prezzo_massimo"] = ultimo_prezzo
                        guadagno_pct = ((ultimo_prezzo - dati_pos["prezzo_acquisto"]) / dati_pos["prezzo_acquisto"]) * 100
                        discesa_dal_massimo = ((dati_pos["prezzo_massimo"] - ultimo_prezzo) / dati_pos["prezzo_massimo"]) * 100
                        stato = f"📦 {round(guadagno_pct, 2)}%"
                        
                        if guadagno_pct >= trailing_activation and discesa_dal_massimo >= trailing_distance:
                            if invia_ordine_alpaca(simbolo, "sell", size_dollari, key, secret):
                                st.session_state.storico_profitti.append({
                                    "Ora": datetime.now().strftime('%H:%M:%S'), "Asset": simbolo,
                                    "Perf %": f"+{round(guadagno_pct, 2)}%", "Gain ($)": round((size_dollari * (guadagno_pct / 100)), 2)
                                })
                                del st.session_state.scatola_nera[simbolo]
                                stato = "💥 Trailing!"
                                st.toast(f"💰 Cassa incassata su {simbolo}!", icon="🔥")
                elif ha_posizione_reale: stato = "📦 In Hold"
                return {"Prezzo ($)": ultimo_prezzo, "RSI": rsi_attuale, "Stato": stato}
        return {"Prezzo ($)": "No Feed", "RSI": "--", "Stato": "Ricerca"}
    except: return {"Prezzo ($)": "Errore", "RSI": "--", "Stato": "Rete"}

# --- GRAFICA TERMINALE ---
st.markdown("## 🛰️ Quant Agent Corazzata Terminal v38.5")

if st.session_state.errori_consecutivi >= 3:
    st.session_state.errori_consecutivi = 0
    st.rerun()

info_conto = ottieni_bilancio_conto(alpaca_key, alpaca_secret)
pos_reali = ottieni_posizioni_reali(alpaca_key, alpaca_secret)
totale_guadagnato = sum([t["Gain ($)"] for t in st.session_state.storico_profitti])

c1, c2, c3 = st.columns(3)
with c1: st.metric("💰 Cash Disponibile", f"$ {info_conto['cash']}")
with c2: st.metric("🛡️ Capitale Corazzata", f"$ {info_conto['portfolio_value']}")
with c3: st.metric("💵 CASSA PROFITTI SESSIONE", f"$ {round(totale_guadagnato, 2)}", delta="Stato Battaglia")

# --- SCANSIONE GLOBALE DI TUTTI I SOLDATI ---
@st.cache_data(ttl=8)
def scansiona_tutto(pos_chiavi_str, key, secret):
    mappa = {}
    for s in tutti_i_soldati:
        mappa[s] = ottieni_e_trada_crypto(s, pos_reali, key, secret)
    return mappa

dati_globali = scansiona_tutto(str(pos_reali), alpaca_key, alpaca_secret)

# --- CREAZIONE GRIGLIE DIVISE PER CATEGORIA ---
for categoria, monete in EQUIPAGGIO.items():
    st.markdown(f"### {categoria}")
    righe_cat = []
    for coin in monete:
        dati_c = dati_globali.get(coin, {"Prezzo ($)": "--", "RSI": "--", "Stato": "--"})
        righe_cat.append({
            "Asset": coin,
            "Prezzo Attuale": dati_c["Prezzo ($)"],
            "RSI (2 Min)": dati_c["RSI"],
            "Stato Operativo / Profitto": dati_c["Stato"]
        })
    st.dataframe(pd.DataFrame(righe_cat), use_container_width=True, hide_index=True)

# STORICO PROFITTI E TRACKING PICCHI
if st.session_state.storico_profitti:
    st.markdown("---")
    st.subheader("💰 Registro dei Bottini di Guerra (Trade Chiusi)")
    st.dataframe(pd.DataFrame(st.session_state.storico_profitti), use_container_width=True)

if st.session_state.scatola_nera:
    st.markdown("---")
    st.subheader("📊 Inseguimento Scatola Nera Attiva")
    st.dataframe(pd.DataFrame(st.session_state.scatola_nera).T, use_container_width=True)

st.caption(f"Radar Corazzata sincronizzato alle ore: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(10)
st.rerun()
