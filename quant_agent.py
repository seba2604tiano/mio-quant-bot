import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# Configurazione iniziale della pagina
st.set_page_config(page_title="Mio Quant Bot", layout="wide")

st.title("🤖 Il Mio Quant Bot - Dashboard Operativa")

# --- RECUPERO CHIAVI FISSE DAI SECRETS ---
chiave_fissa_id = st.secrets.get("ALPACA_API_KEY_ID", "")
chiave_fissa_secret = st.secrets.get("ALPACA_API_SECRET_KEY", "")

# Barra laterale per le configurazioni e le chiavi
st.sidebar.header("🔑 Configurazione API Alpaca")
alpaca_key = st.sidebar.text_input("Alpaca API Key ID", value=chiave_fissa_id, type="password")
alpaca_secret = st.sidebar.text_input("Alpaca API Secret Key", value=chiave_fissa_secret, type="password")
trading_mode = st.sidebar.radio("Modalità Trading", ["Paper (Simulazione)", "Live (Reale)"])

# Impostazione degli endpoint corretti in base alla modalità scelta
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

# Lista crypto
crypto_maior = ["BTC/USD", "ETH/USD", "SOL/USD"]
universo_hunter = ["DOGE/USD", "SHIB/USD", "PEPE/USD", "WIF/USD", "BONK/USD"]

# Inizializzazione della memoria del Trailing Stop nella sessione del bot
if "portfolio_trailing" not in st.session_state:
    st.session_state.portfolio_trailing = {}  # Struttura: { SIMBOLO: {"prezzo_acquisto": X, "prezzo_massimo": Y} }

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

# Funzione per inviare ordini di Compra/Vendi ad Alpaca
def invia_ordine_alpaca(simbolo, lato, qty_dollari, key, secret):
    url_ordine = f"{BASE_URL}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
        "Content-Type": "application/json"
    }
    # Formato pulito senza barra per l'esecuzione degli ordini
    simbolo_ordine = simbolo.replace("/", "")
    
    payload = {
        "symbol": simbolo_ordine,
        "notional": str(qty_dollari), # Specifica quanti dollari investire (es. 10 dollari)
        "side": lato,
        "type": "market",
        "time_in_force": "gtc"
    }
    try:
        res = requests.post(url_ordine, json=payload, headers=headers)
        return res.status_code == 200 or res.status_code == 201
    except:
        return False

# Funzione per scaricare i dati reali e gestire la logica operativa
def ottieni_e_trada_crypto(simbolo, key, secret):
    if not key or not secret:
        return {"Prezzo ($)": "Mancano chiavi", "RSI (2m)": "--", "Stato": "Attesa"}
    
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    params = {"symbols": simbolo, "timeframe": "2Min", "limit": 30}
    
    try:
        risposta = requests.get(DATA_URL, headers=headers, params=params)
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
                
                stato = "🔄 In Monitoraggio"
                
                # --- LOGICA DI TRADING AUTOMATICO (SE ATTIVATO) ---
                if attiva_capitale:
                    # CASO 1: ACQUISTO (Se l'RSI è in ipervenduto e non possediamo già il token)
                    if rsi_attuale < 30 and simbolo not in st.session_state.portfolio_trailing:
                        esito = invia_ordine_alpaca(simbolo, "buy", 10, key, secret) # Compra 10$
                        if esito:
                            st.session_state.portfolio_trailing[simbolo] = {
                                "prezzo_acquisto": ultimo_prezzo,
                                "prezzo_massimo": ultimo_prezzo
                            }
                            st.toast(f"🛒 Acquistato {simbolo} a ${ultimo_prezzo}!", icon="🟢")

                    # CASO 2: GESTIONE TRAILING STOP (Se abbiamo la moneta in portafoglio)
                    if simbolo in st.session_state.portfolio_trailing:
                        dati_pos = st.session_state.portfolio_trailing[simbolo]
                        
                        # Aggiorna il prezzo massimo se il mercato sale
                        if ultimo_prezzo > dati_pos["prezzo_massimo"]:
                            st.session_state.portfolio_trailing[simbolo]["prezzo_massimo"] = ultimo_prezzo
                            dati_pos["prezzo_massimo"] = ultimo_prezzo
                        
                        # Calcola il guadagno attuale rispetto all'acquisto
                        guadagno_pct = ((ultimo_prezzo - dati_pos["prezzo_acquisto"]) / dati_pos["prezzo_acquisto"]) * 100
                        
                        # Calcola la discesa dal punto più alto registrato
                        discesa_dal_massimo = ((dati_pos["prezzo_massimo"] - ultimo_prezzo) / dati_pos["prezzo_massimo"]) * 100
                        
                        stato = f"📦 In Posizione ({round(guadagno_pct, 2)}%)"
                        
                        # Condizione di scatto del Trailing: attivato sopra il X% e sceso del Y% dal picco
                        if guadagno_pct >= trailing_activation and discesa_dal_massimo >= trailing_distance:
                            esito_vendita = invia_ordine_alpaca(simbolo, "sell", 10, key, secret)
                            if esito_vendita:
                                del st.session_state.portfolio_trailing[simbolo]
                                stato = "🔴 Trailing Stop Scattato! Venduto."
                                st.toast(f"💰 Trailing Stop Scattato su {simbolo}! Profitto incassato.", icon="🔥")
                
                return {"Prezzo ($)": ultimo_prezzo, "RSI (2m)": rsi_attuale, "Stato": stato}
            return {"Prezzo ($)": "No Data", "RSI (2m)": "--", "Stato": "Nessuna barra"}
        return {"Prezzo ($)": "Errore", "RSI (2m)": "--", "Stato": f"Errore {risposta.status_code}"}
    except:
        return {"Prezzo ($)": "Errore", "RSI (2m)": "--", "Stato": "Connessione KO"}

# --- INTERFACCIA GRAFICA ---
st.subheader("📈 Mercato Principale")
col1, col2, col3 = st.columns(3)
colonne = [col1, col2, col3]

for i, token in enumerate(crypto_maior):
    dati_token = ottieni_e_trada_crypto(token, alpaca_key, alpaca_secret)
    with colonne[i]:
        st.metric(label=token, value=f"$ {dati_token['Prezzo ($)']}", delta=f"RSI: {dati_token['RSI (2m)']}")

st.markdown("---")
st.subheader("🎯 Scanner Hunter & Gestione Ordini / Trailing")

risultati_meme = []
for token in universo_hunter:
    dati_token = ottieni_e_trada_crypto(token, alpaca_key, alpaca_secret)
    risultati_meme.append({
        "Crypto": token,
        "Prezzo Attuale": dati_token["Prezzo ($)"],
        "RSI (2 min)": dati_token["RSI (2m)"],
        "Stato Operativo / Posizione": dati_token["Stato"]
    })

df_meme = pd.DataFrame(risultati_meme)
st.dataframe(df_meme, use_container_width=True)

# Riepilogo grafico del Trailing Stop interno se ci sono posizioni attive
if st.session_state.portfolio_trailing:
    st.markdown("---")
    st.subheader("📊 Monitoraggio Interno Trailing Stop")
    st.write(st.session_state.portfolio_trailing)

# Aggiornamento automatico ogni 10 secondi
st.caption(f"Ultimo aggiornamento della dashboard: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(10)
st.rerun()
