import streamlit as st
import pandas as pd
import requests
import time
import json
from datetime import datetime

# Configurazione iniziale della pagina
st.set_page_config(page_title="Quant Agent Elite v38.1", layout="wide")

# --- RECUPERO CHIAVI FISSE DAI SECRETS ---
chiave_fissa_id = st.secrets.get("ALPACA_API_KEY_ID", "")
chiave_fissa_secret = st.secrets.get("ALPACA_API_SECRET_KEY", "")

# Barra laterale per le configurazioni e le chiavi
st.sidebar.header("🔑 Configurazione API Alpaca")
alpaca_key = st.sidebar.text_input("Alpaca API Key ID", value=chiave_fissa_id, type="password")
alpaca_secret = st.sidebar.text_input("Alpaca API Secret Key", value=chiave_fissa_secret, type="password")
trading_mode = st.sidebar.radio("Modalità Trading", ["Paper (Simulazione)", "Live (Reale)"])

# Impostazione degli endpoint in base alla modalità scelta
if trading_mode == "Live (Reale)":
    BASE_URL = "https://api.alpaca.markets"
else:
    BASE_URL = "https://paper-api.alpaca.markets"

DATA_URL = "https://data.alpaca.markets/v1beta3/crypto/us/bars"

# Parametri del Trailing Stop configurabili direttamente dalla barra laterale
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parametri Trailing Stop")
trailing_activation = st.sidebar.slider("Attivazione Trailing Stop (%)", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
trailing_distance = st.sidebar.slider("Distanza dallo Stop (% dal massimo)", min_value=0.5, max_value=5.0, value=2.0, step=0.1)

# Pulsante critico per attivazione speculazione reale
st.sidebar.markdown("---")
attiva_capitale = st.sidebar.checkbox("🚀 Attiva Trading Automatico", value=False)

if attiva_capitale:
    st.sidebar.warning("⚠️ BOT ATTIVO: Il sistema eseguirà ordini in base ai segnali!")

# Universi di Asset
crypto_maior = ["BTC/USD", "ETH/USD", "SOL/USD"]
universo_hunter = ["DOGE/USD", "SHIB/USD", "PEPE/USD", "WIF/USD", "BONK/USD"]

# Inizializzazione della Scatola Nera per tracciare i picchi dei prezzi
if "scatola_nera" not in st.session_state:
    st.session_state.scatola_nera = {} # Struttura: { SIMBOLO: {"prezzo_acquisto": X, "prezzo_massimo": Y} }

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

# Funzione per interrogare il portafoglio REALE su Alpaca
def ottieni_posizioni_reali(key, secret):
    url = f"{BASE_URL}/v2/positions"
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            posizioni = res.json()
            # Mappa i simboli reali (es. BTCUSD) per riconoscerli nel bot
            return {p["symbol"]: float(p["qty"]) for p in posizioni}
    except:
        pass
    return {}

# Funzione per recuperare il bilancio totale del conto
def ottieni_bilancio_conto(key, secret):
    url = f"{BASE_URL}/v2/account"
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            dati = res.json()
            return {
                "cash": round(float(dati["cash"]), 2),
                "portfolio_value": round(float(dati["portfolio_value"]), 2)
            }
    except:
        pass
    return {"cash": "0.0", "portfolio_value": "0.0"}

# Funzione per inviare ordini di Compra/Vendi ad Alpaca
def invia_ordine_alpaca(simbolo, lato, qty_dollari, key, secret):
    url_ordine = f"{BASE_URL}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
        "Content-Type": "application/json"
    }
    simbolo_ordine = simbolo.replace("/", "")
    payload = {
        "symbol": simbolo_ordine,
        "notional": str(qty_dollari),
        "side": lato,
        "type": "market",
        "time_in_force": "gtc"
    }
    try:
        res = requests.post(url_ordine, json=payload, headers=headers)
        return res.status_code == 200 or res.status_code == 201
    except:
        return False

# Funzione per scaricare i dati reali e gestire il Trailing Stop
def ottieni_e_trada_crypto(simbolo, posizioni_reali, key, secret):
    if not key or not secret:
        return {"Prezzo ($)": "Mancano chiavi", "RSI (2m)": "--", "Stato": "Attesa"}
    
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
                
                # Verifica se possediamo l'asset sul conto Alpaca vero
                ha_posizione_reale = simbolo_clean in posizioni_reali or simbolo in posizioni_reali
                stato = "🔄 In Monitoraggio"
                
                # Se Alpaca dice che non abbiamo più la posizione, la cancelliamo dalla scatola nera del trailing
                if not ha_posizione_reale and simbolo in st.session_state.scatola_nera:
                    del st.session_state.scatola_nera[simbolo]

                # --- LOGICA OPERATIVA ---
                if attiva_capitale:
                    # 1. COMPRA se l'RSI va sotto 30 e non abbiamo posizioni aperte
                    if rsi_attuale < 30 and not ha_posizione_reale:
                        if invia_ordine_alpaca(simbolo, "buy", 10, key, secret):
                            st.session_state.scatola_nera[simbolo] = {
                                "prezzo_acquisto": ultimo_prezzo,
                                "prezzo_massimo": ultimo_prezzo
                            }
                            st.toast(f"🟢 Acquistato {simbolo} a ${ultimo_prezzo}!", icon="🛒")
                    
                    # 2. INSEGUIMENTO TRAILING se abbiamo la moneta in portafoglio
                    if ha_posizione_reale:
                        # Se il bot riparte e trova una posizione reale ma non ha lo storico del massimo, lo reinizializza
                        if simbolo not in st.session_state.scatola_nera:
                            st.session_state.scatola_nera[simbolo] = {
                                "prezzo_acquisto": ultimo_prezzo,
                                "prezzo_massimo": ultimo_prezzo
                            }
                        
                        dati_pos = st.session_state.scatola_nera[simbolo]
                        
                        # Aggiorna il picco massimo se il prezzo sale
                        if ultimo_prezzo > dati_pos["prezzo_massimo"]:
                            st.session_state.scatola_nera[simbolo]["prezzo_massimo"] = ultimo_prezzo
                            dati_pos["prezzo_massimo"] = ultimo_prezzo
                        
                        guadagno_pct = ((ultimo_prezzo - dati_pos["prezzo_acquisto"]) / dati_pos["prezzo_acquisto"]) * 100
                        discesa_dal_massimo = ((dati_pos["prezzo_massimo"] - ultimo_prezzo) / dati_pos["prezzo_massimo"]) * 100
                        
                        stato = f"📦 In Posizione ({round(guadagno_pct, 2)}%)"
                        
                        # Condizione di scatto: profitto minimo raggiunto e ritracciamento rilevato dal picco massimo
                        if guadagno_pct >= trailing_activation and discesa_dal_massimo >= trailing_distance:
                            if invia_ordine_alpaca(simbolo, "sell", 10, key, secret):
                                if simbolo in st.session_state.scatola_nera:
                                    del st.session_state.scatola_nera[simbolo]
                                stato = "🔴 Trailing Scattato! Venduto."
                                st.toast(f"🔥 Venduto {simbolo}! Profitto messo in cassaforte.", icon="💰")
                
                elif ha_posizione_reale:
                    stato = "📦 Asset in Portafoglio (Trading automatico spento)"

                return {"Prezzo ($)": ultimo_prezzo, "RSI (2m)": rsi_attuale, "Stato": stato}
            return {"Prezzo ($)": "No Data", "RSI (2m)": "--", "Stato": "Nessuna barra"}
        return {"Prezzo ($)": "Errore", "RSI (2m)": "--", "Stato": f"Errore {risposta.status_code}"}
    except:
        return {"Prezzo ($)": "Errore", "RSI (2m)": "--", "Stato": "Connessione KO"}

# --- SCHERMATA PRINCIPALE TERMINALE ---
st.markdown("## 🛰️ Quant Agent Elite Terminal v38.1 — SCATOLA CORRAZZATA")
st.success("🔒 **SCATOLA NERA ATTIVA:** Sincronizzazione in tempo reale con il portafoglio ufficiale Alpaca.")

# Recupero dati conto correnti
info_conto = ottieni_bilancio_conto(alpaca_key, alpaca_secret)
pos_reali = ottieni_posizioni_reali(alpaca_key, alpaca_secret)

# Widget di riepilogo finanziario
c1, c2 = st.columns(2)
with c1:
    st.metric("Liquidità Cash Disponibile", f"$ {info_conto['cash']}")
with c2:
    st.metric("Valore Totale Portafoglio (Asset + Cash)", f"$ {info_conto['portfolio_value']}")

# --- SEZIONE 1: CRYPTO PRINCIPALI ---
st.markdown("---")
st.subheader("📈 Crypto Principali (Real-time)")
col1, col2, col3 = st.columns(3)
colonne = [col1, col2, col3]

for i, token in enumerate(crypto_maior):
    dati_token = ottieni_e_trada_crypto(token, pos_reali, alpaca_key, alpaca_secret)
    with colonne[i]:
        st.metric(label=token, value=f"$ {dati_token['Prezzo ($)']}", delta=f"RSI: {dati_token['RSI (2m)']}")

# --- SEZIONE 2: MEME & HUNTER ---
st.markdown("---")
st.subheader("🎯 Scanner Hunter & Inseguimento Trailing Stop")

risultati_meme = []
for token in universo_hunter:
    dati_token = ottieni_e_trada_crypto(token, pos_reali, alpaca_key, alpaca_secret)
    risultati_meme.append({
        "Crypto": token,
        "Prezzo Attuale": dati_token["Prezzo ($)"],
        "RSI (2 min)": dati_token["RSI (2m)"],
        "Stato Operativo / Posizione": dati_token["Stato"]
    })

df_meme = pd.DataFrame(risultati_meme)
st.dataframe(df_meme, use_container_width=True)

# Visualizzazione della memoria interna del Trailing Stop
if st.session_state.scatola_nera:
    st.markdown("---")
    st.subheader("📊 Scatola Nera: Monitoraggio Picchi e Prezzi di Carico")
    df_scatola = pd.DataFrame(st.session_state.scatola_nera).T
    st.dataframe(df_scatola, use_container_width=True)

# Aggiornamento automatico ogni 10 secondi
st.caption(f"Ultimo aggiornamento della dashboard: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(10)
st.rerun()
