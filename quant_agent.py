import streamlit as st
import pandas as pd
import requests
import time
import json
import os
from datetime import datetime, timedelta, timezone

# Configurazione iniziale della pagina
st.set_page_config(page_title="Quant Agent Global v41.6", layout="wide")

CACHE_FILE = "storico_profitti_cache.json"
CONFIG_FILE = "config_fortezza.json"

# --- RECUPERO CHIAVI FISSE DAI SECRETS ---
chiave_fissa_id = st.secrets.get("ALPACA_API_KEY_ID", "")
chiave_fissa_secret = st.secrets.get("ALPACA_API_SECRET_KEY", "")

# --- GESTIONE MEMORIA STATO INTERRUTTORE ---
def carica_config_stato():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f).get("auto_trading", False)
        except: return False
    return False

def salva_config_stato(stato):
    try:
        with open(CONFIG_FILE, "w") as f: json.dump({"auto_trading": stato}, f)
    except: pass

stato_precedente = carica_config_stato()

# Barra laterale per le configurazioni e le chiavi
st.sidebar.header("🔑 Configurazione API Alpaca")
alpaca_key = st.sidebar.text_input("Alpaca API Key ID", value=chiave_fissa_id, type="password")
alpaca_secret = st.sidebar.text_input("Alpaca API Secret Key", value=chiave_fissa_secret, type="password")
trading_mode = st.sidebar.radio("Modalità Trading", ["Paper (Simulazione)", "Live (Reale)"])
BASE_URL = "https://api.alpaca.markets" if trading_mode == "Live (Reale)" else "https://paper-api.alpaca.markets"

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Gestione Munizioni Base")
size_dollari = st.sidebar.slider("Capitale Base per Trade ($)", min_value=5, max_value=500, value=50, step=5)
attiva_capitale = st.sidebar.toggle("🚀 ATTIVA TRADING AUTOMATICO", value=stato_precedente)
salva_config_stato(attiva_capitale)

# --- STRUTTURA MULTI-ASSET ---
EQUIPAGGIO = {
    "👑 Crypto Blue-Chips": ["BTC/USD", "ETH/USD", "SOL/USD"],
    "⚡ Crypto Liquidità": ["LTC/USD", "BCH/USD", "LINK/USD", "UNI/USD"],
    "🇺🇸 Azioni USA": ["AAPL", "TSLA", "NVDA", "AMZN", "MSFT"],
    "📀 Metalli": ["GLD", "SLV"]
}
tutti_i_soldati = [coin for cat in EQUIPAGGIO.values() for coin in cat]

if "scatola_nera" not in st.session_state: st.session_state.scatola_nera = {}
if "storico_profitti" not in st.session_state: st.session_state.storico_profitti = []

# --- FUNZIONI DI SUPPORTO (Intatte) ---
def calcola_rsi(prezzi):
    if len(prezzi) < 15: return 50.0
    delta = pd.Series(prezzi).diff()
    gain = delta.clip(lower=0).ewm(span=14).mean()
    loss = -delta.clip(upper=0).ewm(span=14).mean()
    rs = gain / loss.replace(0, 0.001)
    return round(100 - (100 / (1 + rs.iloc[-1])), 2)

def ottieni_posizioni_reali():
    url = f"{BASE_URL}/v2/positions"
    headers = {"APCA-API-KEY-ID": alpaca_key, "APCA-API-SECRET-KEY": alpaca_secret}
    try:
        res = requests.get(url, headers=headers)
        return {p["symbol"]: {"qty": float(p["qty"])} for p in res.json()} if res.status_code == 200 else {}
    except: return {}

def invia_ordine(simbolo, lato, val, is_qty):
    url = f"{BASE_URL}/v2/orders"
    headers = {"APCA-API-KEY-ID": alpaca_key, "APCA-API-SECRET-KEY": alpaca_secret, "Content-Type": "application/json"}
    payload = {"symbol": simbolo.replace("/", ""), "side": lato, "type": "market", "time_in_force": "gtc"}
    if is_qty: payload["qty"] = str(val)
    else: payload["notional"] = str(val)
    return requests.post(url, json=payload, headers=headers).status_code in [200, 201]

# --- SCANNER (Motore v41.2 intatto) ---
def scarica_dati_globali_batch():
    headers = {"APCA-API-KEY-ID": alpaca_key, "APCA-API-SECRET-KEY": alpaca_secret}
    mappa = {}
    for coin in tutti_i_soldati:
        try:
            url = f"https://data.alpaca.markets/v1beta3/crypto/us/bars" if "/USD" in coin else "https://data.alpaca.markets/v2/stocks/bars"
            res = requests.get(url, headers=headers, params={"symbols": coin.replace("/", ""), "timeframe": "5Min", "limit": 20})
            if res.status_code == 200:
                barre = res.json().get("bars", {}).get(coin.replace("/", ""), [])
                if barre:
                    close = barre[-1]["c"]
                    # ATR semplificato per demo
                    atr = (barre[-1]["h"] - barre[-1]["l"]) 
                    mappa[coin] = {"prezzo": close, "rsi": 50, "atr": atr}
        except: mappa[coin] = {"prezzo": "Errore", "rsi": 50, "atr": 0}
    return mappa

# --- ESECUZIONE E LOGICA EXIT (Implementazione Integrata) ---
st.markdown("## 🛰️ Quant Agent Global v41.6")
pos_reali = ottieni_posizioni_reali()
dati_mercato = scarica_dati_globali_batch()

for coin in tutti_i_soldati:
    if coin in st.session_state.scatola_nera:
        dati_pos = st.session_state.scatola_nera[coin]
        dati_m = dati_mercato.get(coin, {"prezzo": 0, "atr": 0})
        prezzo_curr = float(dati_m["prezzo"]) if isinstance(dati_m["prezzo"], (int, float)) else 0
        
        if prezzo_curr > 0:
            guadagno_pct = ((prezzo_curr - dati_pos["prezzo_acquisto"]) / dati_pos["prezzo_acquisto"]) * 100
            
            # 1. SCALING OUT (+1.5%)
            if guadagno_pct >= 1.5 and not dati_pos.get("venduto_parziale", False):
                qty_tot = pos_reali.get(coin.replace("/", ""), {}).get("qty", 0)
                if qty_tot > 0 and invia_ordine(coin, "sell", qty_tot/2, True):
                    st.session_state.scatola_nera[coin]["venduto_parziale"] = True
                    st.toast(f"✅ TP Parziale su {coin}")
            
            # 2. TRAILING STOP (ATR)
            stop_dinamico = prezzo_curr - (2 * dati_m["atr"])
            if prezzo_curr <= stop_dinamico and guadagno_pct > -5:
                qty_tot = pos_reali.get(coin.replace("/", ""), {}).get("qty", 0)
                if qty_tot > 0 and invia_ordine(coin, "sell", qty_tot, True):
                    st.session_state.storico_profitti.append(f"Chiuso {coin} a {prezzo_curr}")
                    del st.session_state.scatola_nera[coin]
                    st.toast(f"💥 Uscita ATR su {coin}")

# Rendering Tabella
st.dataframe(pd.DataFrame([{"Asset": c, "Prezzo": str(dati_mercato.get(c, {}).get("prezzo", "N/D"))} for c in tutti_i_soldati]))

if st.button("🔄 Riavvia"): st.rerun()
time.sleep(10)
st.rerun()
