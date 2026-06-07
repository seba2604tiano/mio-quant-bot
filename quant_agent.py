import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# Configurazione iniziale della pagina
st.set_page_config(page_title="Mio Quant Bot", layout="wide")

st.title("🤖 Il Mio Quant Bot - Dashboard")

# Barra laterale per le configurazioni e le chiavi
st.sidebar.header("🔑 Configurazione API Alpaca")
alpaca_key = st.sidebar.text_input("Alpaca API Key ID", type="password")
alpaca_secret = st.sidebar.text_input("Alpaca API Secret Key", type="password")
trading_mode = st.sidebar.radio("Modalità Trading", ["Paper (Simulazione)", "Live (Reale)"])

# Configurazione endpoint ufficiale Alpaca per i dati storici/real-time delle Crypto
DATA_URL = "https://data.alpaca.markets/v1beta3/crypto/us/bars"

# Pulsante per attivazione capitale
st.sidebar.markdown("---")
attiva_capitale = st.sidebar.checkbox("🚀 Attiva Capitale Reale", value=False)

if attiva_capitale:
    st.sidebar.warning("⚠️ ATTENZIONE: Il bot è pronto a operare con capitale reale!")

# --- FORMATO SIMBOLI AGGIORNATO PER ALPACA V1BETA3 ---
crypto_maior = ["BTC/USD", "ETH/USD", "SOL/USD"]
universo_hunter = ["DOGE/USD", "SHIB/USD", "PEPE/USD", "WIF/USD", "BONK/USD"]

# Funzione per calcolare l'RSI
def calcola_rsi(prezzi, periodi=14):
    if len(prezzi) < periodi + 1:
        return 50.0
    variazioni = pd.Series(prezzi).diff()
    guadagni = variazioni.clip(lower=0)
    perdite = -variazioni.clip(upper=0)
    
    media_guadagni = guadagni.ewm(span=periodi, adjust=False).mean()
    media_perdite = perdite.ewm(span=periodi, adjust=False).mean()
    
    rs = media_guadagni / media_perdite.replace(0, 0.00001)
    rsi = 100 - (100 / (1 + rs))
    return round(rsi.iloc[-1], 2)

# Funzione per scaricare i dati reali da Alpaca
def ottieni_dati_crypto(simbolo, key, secret):
    if not key or not secret:
        return {"Prezzo ($)": "Inserisci le chiavi", "RSI (2m)": "--", "Stato": "Chiavi mancanti"}
    
    headers = {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret
    }
    
    params = {
        "symbols": simbolo,
        "timeframe": "2Min",
        "limit": 30
    }
    
    try:
        risposta = requests.get(DATA_URL, headers=headers, params=params)
        
        # Se fallisce con la barra, fa un secondo tentativo automatico senza barra
        if risposta.status_code == 400 and "/" in simbolo:
            simbolo_alternativo = simbolo.replace("/", "")
            params["symbols"] = simbolo_alternativo
            risposta = requests.get(DATA_URL, headers=headers, params=params)
            simbolo = simbolo_alternativo

        if risposta.status_code == 200:
            dati = risposta.json()
            barre = dati.get("bars", {}).get(simbolo, [])
            if barre:
                prezzi_chiusura = [b["c"] for b in barre]
                ultimo_prezzo = prezzi_chiusura[-1]
                rsi_attuale = calcola_rsi(prezzi_chiusura)
                
                stato = "🔄 In Attesa"
                if rsi_attuale < 30: stato = "🟢 IPERVENDUTO"
                elif rsi_attuale > 70: stato = "🔴 IPERCOMPRATO"
                
                return {"Prezzo ($)": ultimo_prezzo, "RSI (2m)": rsi_attuale, "Stato": stato}
            else:
                return {"Prezzo ($)": "No Data", "RSI (2m)": "--", "Stato": "Nessuna barra recente"}
        elif risposta.status_code == 401:
            return {"Prezzo ($)": "Errore 401", "RSI (2m)": "--", "Stato": "Chiavi Rifiutate"}
        return {"Prezzo ($)": "Errore", "RSI (2m)": "--", "Stato": f"Codice Alpaca: {risposta.status_code}"}
    except Exception as e:
        return {"Prezzo ($)": "Errore", "RSI (2m)": "--", "Stato": "Connessione fallita"}

# --- SEZIONE 1: CRYPTO PRINCIPALI ---
st.subheader("📈 Crypto Principali (Real-time)")
col1, col2, col3 = st.columns(3)
colonne = [col1, col2, col3]

for i, token in enumerate(crypto_maior):
    dati_token = ottieni_dati_crypto(token, alpaca_key, alpaca_secret)
    with colonne[i]:
        st.metric(label=token, value=f"$ {dati_token['Prezzo ($)']}", delta=f"RSI: {dati_token['RSI (2m)']}")

# --- SEZIONE 2: MEME & HUNTER ---
st.markdown("---")
st.subheader("🎯 Scanner Meme Coins & Hunter")

risultati_meme = []
for token in universo_hunter:
    dati_token = ottieni_dati_crypto(token, alpaca_key, alpaca_secret)
    risultati_meme.append({
        "Crypto": token,
        "Prezzo Attuale": dati_token["Prezzo ($)"],
        "RSI (2 min)": dati_token["RSI (2m)"],
        "Segnale Operativo": dati_token["Stato"]
    })

df_meme = pd.DataFrame(risultati_meme)
st.dataframe(df_meme, use_container_width=True)

# Aggiornamento automatico ogni 10 secondi
st.caption(f"Ultimo aggiornamento della dashboard: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(10)
st.rerun()
