import streamlit as st
import pandas as pd
import requests
import time
import json
import os
from datetime import datetime, timedelta, timezone

# Configurazione iniziale
st.set_page_config(page_title="Quant Agent Global v41.4", layout="wide")

CACHE_FILE = "storico_profitti_cache.json"
CONFIG_FILE = "config_fortezza.json"

# --- RECUPERO CHIAVI ---
chiave_fissa_id = st.secrets.get("ALPACA_API_KEY_ID", "")
chiave_fissa_secret = st.secrets.get("ALPACA_API_SECRET_KEY", "")

# --- GESTIONE STATO ---
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

# Barra laterale
st.sidebar.header("🔑 Configurazione API Alpaca")
alpaca_key = st.sidebar.text_input("Alpaca API Key ID", value=chiave_fissa_id, type="password")
alpaca_secret = st.sidebar.text_input("Alpaca API Secret Key", value=chiave_fissa_secret, type="password")
trading_mode = st.sidebar.radio("Modalità Trading", ["Paper (Simulazione)", "Live (Reale)"])
BASE_URL = "https://api.alpaca.markets" if trading_mode == "Live (Reale)" else "https://paper-api.alpaca.markets"

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Gestione Munizioni")
size_dollari = st.sidebar.slider("Capitale per Trade ($)", 5, 500, 50, 5)
attiva_capitale = st.sidebar.toggle("🚀 ATTIVA TRADING AUTOMATICO", value=stato_precedente)
salva_config_stato(attiva_capitale)

# --- ASSET ---
EQUIPAGGIO = {
    "👑 Crypto Blue-Chips": ["BTC/USD", "ETH/USD", "SOL/USD"],
    "⚡ Crypto Liquidità": ["LTC/USD", "BCH/USD", "LINK/USD", "UNI/USD"],
    "🇺🇸 Giganti Wall Street": ["AAPL", "TSLA", "NVDA", "AMZN", "MSFT"],
    "📀 Metalli": ["GLD", "SLV"]
}
tutti_i_soldati = [coin for cat in EQUIPAGGIO.values() for coin in cat]

if "scatola_nera" not in st.session_state: st.session_state.scatola_nera = {}
if "storico_profitti" not in st.session_state: st.session_state.storico_profitti = []

# --- FUNZIONI UTILITY ---
def calcola_rsi(prezzi, periodi=14):
    if len(prezzi) < periodi + 1: return 50.0
    variazioni = pd.Series(prezzi).diff()
    guadagni = variazioni.clip(lower=0)
    perdite = -variazioni.clip(upper=0)
    media_g = guadagni.ewm(span=periodi, adjust=False).mean()
    media_p = perdite.ewm(span=periodi, adjust=False).mean()
    rs = media_g / media_p.replace(0, 0.00001)
    return round((100 - (100 / (1 + rs))).iloc[-1], 2)

def calcola_ema200(prezzi):
    if len(prezzi) < 200: return None
    return round(pd.Series(prezzi).ewm(span=200, adjust=False).mean().iloc[-1], 4)

def ottieni_posizioni_reali():
    url = f"{BASE_URL}/v2/positions"
    headers = {"APCA-API-KEY-ID": alpaca_key, "APCA-API-SECRET-KEY": alpaca_secret}
    try:
        res = requests.get(url, headers=headers)
        return {p["symbol"]: float(p["qty"]) for p in res.json()} if res.status_code == 200 else {}
    except: return {}

def invia_ordine(simbolo, lato, val, is_qty):
    url = f"{BASE_URL}/v2/orders"
    headers = {"APCA-API-KEY-ID": alpaca_key, "APCA-API-SECRET-KEY": alpaca_secret, "Content-Type": "application/json"}
    payload = {"symbol": simbolo.replace("/", ""), "side": lato, "type": "market", "time_in_force": "gtc"}
    if is_qty: payload["qty"] = str(val)
    else: payload["notional"] = str(val)
    return requests.post(url, json=payload, headers=headers).status_code in [200, 201]

def scarica_dati_globali_batch():
    # Placeholder: la logica di recupero dati (come implementata in v41.2) rimane qui
    # Assicura di mantenere la chiamata corretta alle API di Alpaca
    return {} # Inserisci la logica batch precedente

# --- CORE ---
st.markdown("## 🛰️ Quant Agent Global v41.4")
pos_reali = ottieni_posizioni_reali()
dati_mercato = scarica_dati_globali_batch()

for coin in tutti_i_soldati:
    if coin in st.session_state.scatola_nera:
        dati_pos = st.session_state.scatola_nera[coin]
        prezzo_attuale = 100 # Esempio valore di mercato
        atr = 1.0 # Esempio valore ATR
        
        guadagno_pct = ((prezzo_attuale - dati_pos["prezzo_acquisto"]) / dati_pos["prezzo_acquisto"]) * 100
        
        # 1. SCALING OUT (Vendita Parziale)
        if guadagno_pct >= 1.5 and not dati_pos.get("venduto_parziale", False):
            qty_tot = pos_reali.get(coin.replace("/", ""), 0)
            if invia_ordine(coin, "sell", qty_tot/2, True):
                st.session_state.scatola_nera[coin]["venduto_parziale"] = True
                st.toast(f"✅ TP Parziale su {coin}")

        # 2. TRAILING STOP ATR
        stop_dinamico = prezzo_attuale - (2 * atr)
        if prezzo_attuale <= stop_dinamico:
            invia_ordine(coin, "sell", pos_reali.get(coin.replace("/", ""), 0), True)
            del st.session_state.scatola_nera[coin]
            st.toast(f"💥 Uscita Totale su {coin}")

# --- RENDER TABELLA (ROBUSTO) ---
for categoria, monete in EQUIPAGGIO.items():
    st.markdown(f"### {categoria}")
    righe = []
    for coin in monete:
        righe.append({
            "Asset": str(coin),
            "Prezzo": "N/D",
            "Stato": str(st.session_state.scatola_nera.get(coin, "🛰️ In Caccia"))
        })
    st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)

if st.button("🔄 Reset Dati"):
    st.session_state.scatola_nera = {}
    st.rerun()

time.sleep(10)
st.rerun()
