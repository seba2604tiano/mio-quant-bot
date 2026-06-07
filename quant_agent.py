import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# Configurazione iniziale della pagina
st.set_page_config(page_title="Quant Agent Elite v38.3", layout="wide")

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
size_dollari = st.sidebar.slider("Capitale per Singolo Trade ($)", min_value=5, max_value=250, value=20, step=5)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parametri Trailing Stop")
trailing_activation = st.sidebar.slider("Attivazione Trailing Stop (%)", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
trailing_distance = st.sidebar.slider("Distanza dallo Stop (% dal massimo)", min_value=0.5, max_value=5.0, value=2.0, step=0.1)

st.sidebar.markdown("---")
attiva_capitale = st.sidebar.checkbox("🚀 Attiva Trading Automatico", value=False)

if attiva_capitale:
    st.sidebar.warning("⚠️ BOT ATTIVO: Operazioni automatiche abilitate.")

# Universi di Asset
crypto_maior = ["BTC/USD", "ETH/USD", "SOL/USD"]
universo_hunter = [
    "DOGE/USD", "SHIB/USD", "PEPE/USD", "WIF/USD", "BONK/USD", 
    "FLOKI/USD", "MEME/USD", "BOME/USD", "POPCAT/USD", "BRETT/USD"
]

# --- INIZIALIZZAZIONE CASSA DI MEMORIA E CONTROLLI ANTI-BLOCCO ---
if "scatola_nera" not in st.session_state:
    st.session_state.scatola_nera = {}
if "storico_profitti" not in st.session_state:
    st.session_state.storico_profitti = []  # Cassa di memoria dei trade chiusi
if "errori_consecutivi" not in st.session_state:
    st.session_state.errori_consecutivi = 0

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

# Funzioni di comunicazione Alpaca
def ottieni_posizioni_reali(key, secret):
    url = f"{BASE_URL}/v2/positions"
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            st.session_state.errori_consecutivi = 0  # Reset contatore errori se risponde
            return {p["symbol"]: float(p["qty"]) for p in res.json()}
    except:
        st.session_state.errori_consecutivi += 1
    return {}

def ottieni_bilancio_conto(key, secret):
    url = f"{BASE_URL}/v2/account"
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            dati = res.json()
            return {"cash": round(float(dati["cash"]), 2), "portfolio_value": round(float(dati["portfolio_value"]), 2)}
    except:
        pass
    return {"cash": "0.0", "portfolio_value": "0.0"}

def invia_ordine_alpaca(simbolo, lato, qty_dollari, key, secret):
    url_ordine = f"{BASE_URL}/v2/orders"
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret, "Content-Type": "application/json"}
    payload = {"symbol": simbolo.replace("/", ""), "notional": str(qty_dollari), "side": lato, "type": "market", "time_in_force": "gtc"}
    try:
        res = requests.post(url_ordine, json=payload, headers=headers)
        return res.status_code == 200 or res.status_code == 201
    except:
        return False

# Motore di scansione e trading
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
                
                ha_posizione_reale = simbolo_clean in posizioni_reali or simbolo in posizioni_reali
                stato = "🔄 In Monitoraggio"
                
                if not ha_posizione_reale and simbolo in st.session_state.scatola_nera:
                    del st.session_state.scatola_nera[simbolo]

                # --- LOGICA CORE ---
                if attiva_capitale:
                    # ACQUISTO
                    if rsi_attuale < 30 and not ha_posizione_reale:
                        if invia_ordine_alpaca(simbolo, "buy", size_dollari, key, secret):
                            st.session_state.scatola_nera[simbolo] = {"prezzo_acquisto": ultimo_prezzo, "prezzo_massimo": ultimo_prezzo, "ora_acquisto": datetime.now().strftime('%H:%M:%S')}
                            st.toast(f"🟢 Preso {simbolo} (${size_dollari})", icon="🛒")
                    
                    # INSEGUIMENTO E TRAILING STOP
                    if ha_posizione_reale:
                        if simbolo not in st.session_state.scatola_nera:
                            st.session_state.scatola_nera[simbolo] = {"prezzo_acquisto": ultimo_prezzo, "prezzo_massimo": ultimo_prezzo, "ora_acquisto": datetime.now().strftime('%H:%M:%S')}
                        
                        dati_pos = st.session_state.scatola_nera[simbolo]
                        if ultimo_prezzo > dati_pos["prezzo_massimo"]:
                            st.session_state.scatola_nera[simbolo]["prezzo_massimo"] = ultimo_prezzo
                            dati_pos["prezzo_massimo"] = ultimo_prezzo
                        
                        guadagno_pct = ((ultimo_prezzo - dati_pos["prezzo_acquisto"]) / dati_pos["prezzo_acquisto"]) * 100
                        discesa_dal_massimo = ((dati_pos["prezzo_massimo"] - ultimo_prezzo) / dati_pos["prezzo_massimo"]) * 100
                        stato = f"📦 In Posizione ({round(guadagno_pct, 2)}%)"
                        
                        # SCATTO TRAILING: REGISTRAZIONE NELLA CASSA PROFITTI
                        if guadagno_pct >= trailing_activation and discesa_dal_massimo >= trailing_distance:
                            if invia_ordine_alpaca(simbolo, "sell", size_dollari, key, secret):
                                profitto_esatto_dollari = round((size_dollari * (guadagno_pct / 100)), 2)
                                
                                # Salvataggio storico permanente nella cassa di memoria
                                st.session_state.storico_profitti.append({
                                    "Orario Chiusura": datetime.now().strftime('%H:%M:%S'),
                                    "Crypto": simbolo,
                                    "Prezzo Ingresso": dati_pos["prezzo_acquisto"],
                                    "Prezzo Uscita": ultimo_prezzo,
                                    "Performance %": f"+{round(guadagno_pct, 2)}%",
                                    "Profitto Netto ($)": profitto_esatto_dollari
                                })
                                
                                if simbolo in st.session_state.scatola_nera:
                                    del st.session_state.scatola_nera[simbolo]
                                stato = "🔴 Trailing Scattato!"
                                st.toast(f"🔥 Venduto {simbolo}! Portato a casa il profitto.", icon="💰")
                
                elif ha_posizione_reale:
                    stato = "📦 In Portafoglio (Auto-Trade Off)"

                return {"Prezzo ($)": ultimo_prezzo, "RSI (2m)": rsi_attuale, "Stato": stato}
        return {"Prezzo ($)": "No Data", "RSI (2m)": "--", "Stato": "Ricerca..."}
    except:
        return {"Prezzo ($)": "Errore", "RSI (2m)": "--", "Stato": "Connessione ricalibrata"}

# --- SCHERMATA PRINCIPALE TERMINALE ---
st.markdown("## 🛰️ Quant Agent Elite Terminal v38.3")

# MECCANISMO AUTO-REBOOT INTEGRATO (Se ci sono più di 3 errori di rete consecutivi, pulisce e riavvia)
if st.session_state.errori_consecutivi >= 3:
    st.session_state.errori_consecutivi = 0
    st.toast("🔄 Rilevato blocco di rete. Esecuzione Auto-Reboot protettivo...", icon="⚡")
    time.sleep(2)
    st.rerun()

info_conto = ottieni_bilancio_conto(alpaca_key, alpaca_secret)
pos_reali = ottieni_posizioni_reali(alpaca_key, alpaca_secret)

# Calcolo totale della Cassa Profitti
totale_guadagnato = sum([trade["Profitto Netto ($)"] for trade in st.session_state.storico_profitti])

# Widget Finanziari
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Liquidità Cash Disponibile", f"$ {info_conto['cash']}")
with c2:
    st.metric("Valore Totale Portafoglio", f"$ {info_conto['portfolio_value']}")
with c3:
    # Questa è la tua nuova cassa profitti visiva
    st.metric("💵 CASSA PROFITTI SESSIONE", f"$ {round(totale_guadagnato, 2)}", delta="Performance Bot")

# --- TABELLA DELLE MEME ---
st.markdown("---")
st.subheader("🎯 Scanner Hunter & Inseguimento Trailing Stop")

risultati_meme = []
for token in universo_hunter:
    dati_token = ottieni_e_trada_crypto(token, pos_reali, alpaca_key, alpaca_secret)
    risultati_meme.append({"Crypto": token, "Prezzo Attuale": dati_token["Prezzo ($)"], "RSI (2 min)": dati_token["RSI (2m)"], "Stato Operativo": dati_token["Stato"]})

df_meme = pd.DataFrame(risultati_meme)
st.dataframe(df_meme, use_container_width=True)

# --- VISUALIZZAZIONE CASSA STORICA PROFITTI ---
if st.session_state.storico_profitti:
    st.markdown("---")
    st.subheader("💰 Cassa Storica dei Trade Vincenti (Sessione Notturna)")
    st.dataframe(pd.DataFrame(st.session_state.storico_profitti), use_container_width=True)

# Memoria della Scatola Nera attiva
if st.session_state.scatola_nera:
    st.markdown("---")
    st.subheader("📊 Scatola Nera: Monitoraggio Picchi Attivi")
    st.dataframe(pd.DataFrame(st.session_state.scatola_nera).T, use_container_width=True)

# Auto-aggiornamento
st.caption(f"Ultimo aggiornamento della dashboard: {datetime.now().strftime('%H:%M:%S')} | Errori consecutivi: {st.session_state.errori_consecutivi}/3")
time.sleep(10)
st.rerun()
