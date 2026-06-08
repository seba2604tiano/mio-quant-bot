import streamlit as st
import pandas as pd
import requests
import time
import json
import os
from datetime import datetime, timedelta, timezone

# Configurazione iniziale della pagina
st.set_page_config(page_title="Quant Agent Global v40.0", layout="wide")

CACHE_FILE = "storico_profitti_cache.json"
CONFIG_FILE = "config_fortezza.json"

# --- RECUPERO CHIAVI FISSE DAI SECRETS ---
chiave_fissa_id = st.secrets.get("ALPACA_API_KEY_ID", "")
chiave_fissa_secret = st.secrets.get("ALPACA_API_SECRET_KEY", "")

# --- GESTIONE MEMORIA STATO INTERRUTTORE ---
def carica_config_stato():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: 
                return json.load(f).get("auto_trading", False)
        except: 
            return False
    return False

def salva_config_stato(stato):
    try:
        with open(CONFIG_FILE, "w") as f: 
            json.dump({"auto_trading": stato}, f)
    except: 
        pass

stato_precedente = carica_config_stato()

# Barra laterale per le configurazioni e le chiavi
st.sidebar.header("🔑 Configurazione API Alpaca")
alpaca_key = st.sidebar.text_input("Alpaca API Key ID", value=chiave_fissa_id, type="password")
alpaca_secret = st.sidebar.text_input("Alpaca API Secret Key", value=chiave_fissa_secret, type="password")
trading_mode = st.sidebar.radio("Modalità Trading", ["Paper (Simulazione)", "Live (Reale)"])

if trading_mode == "Live (Reale)": 
    BASE_URL = "https://api.alpaca.markets"
else: 
    BASE_URL = "https://paper-api.alpaca.markets"

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Gestione Munizioni")
size_dollari = st.sidebar.slider("Capitale per Singolo Trade ($)", min_value=5, max_value=500, value=50, step=5)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parametri Trailing Stop")
trailing_activation = st.sidebar.slider("Attivazione Trailing Stop (%)", min_value=1.0, max_value=20.0, value=1.5, step=0.1)
trailing_distance = st.sidebar.slider("Distanza dallo Stop (% dal massimo)", min_value=0.5, max_value=5.0, value=0.5, step=0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("🏹 Strategia d'Ingresso")
tipo_strategia = st.sidebar.selectbox("Condizione d'Acquisto", ["Ipervenduto Classico (RSI < 35)", "Inseguimento FOMO (RSI > 65)"])

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Pannello Armamenti")
attiva_capitale = st.sidebar.toggle("🚀 ATTIVA TRADING AUTOMATICO", value=stato_precedente)
salva_config_stato(attiva_capitale)

# --- NUOVA STRUTTURA MULTI-ASSET GLOBAL IMPERIUM ---
EQUIPAGGIO = {
    "👑 I Re del Mercato (Crypto 24/7)": ["BTC/USD", "ETH/USD", "SOL/USD"],
    "🇺🇸 I Giganti di Wall Street (Azioni)": ["AAPL", "TSLA", "NVDA", "AMZN", "MSFT"],
    "📀 Metalli Preziosi (ETF Oro & Argento)": ["GLD", "SLV"],
    "🌶️ Battaglione Meme (Crypto Botti)": ["DOGE/USD", "SHIB/USD", "PEPE/USD", "BONK/USD"]
}

tutti_i_soldati = [coin for cat in EQUIPAGGIO.values() for coin in cat]

def carica_storico_persistente():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f: return json.load(f)
        except: return []
    return []

def salva_storico_persistente(storico):
    try:
        with open(CACHE_FILE, "w") as f: json.dump(storico, f)
    except: pass

if "scatola_nera" not in st.session_state: st.session_state.scatola_nera = {}
if "storico_profitti" not in st.session_state: st.session_state.storico_profitti = carica_storico_persistente()

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
            return {p["symbol"]: {"qty": float(p["qty"]), "asset_id": p["asset_id"]} for p in res.json()}
    except: pass
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

def invia_ordine_market(simbolo, lato, quantita_o_dollari, is_qty, key, secret):
    url_ordine = f"{BASE_URL}/v2/orders"
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret, "Content-Type": "application/json"}
    payload = {"symbol": simbolo.replace("/", ""), "side": lato, "type": "market", "time_in_force": "gtc"}
    if is_qty: 
        payload["qty"] = str(quantita_o_dollari)
    else: 
        payload["notional"] = str(quantita_o_dollari)
    try:
        res = requests.post(url_ordine, json=payload, headers=headers)
        return res.status_code == 200 or res.status_code == 201
    except: return False

# --- ARCHITETTURA DI SCANSIONE DUALE MULTI-ASSET BATCH ---
def scarica_dati_globali_batch(key, secret):
    if not key or not secret: return {}
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    mappa_prezzi = {}
    
    # Divisione asset per canali differenti
    crypto_assets = [s for s in tutti_i_soldati if "/USD" in s]
    stock_assets = [s for s in tutti_i_soldati if "/USD" not in s]
    
    # Finestra temporale di 5 giorni per superare i weekend di Wall Street
    ora_inizio = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # 1. CANALE DATA CRYPTO
    if crypto_assets:
        try:
            url_crypto = "https://data.alpaca.markets/v1beta3/crypto/us/bars"
            res = requests.get(url_crypto, headers=headers, params={"symbols": ",".join(crypto_assets), "timeframe": "5Min", "limit": 2000, "start": ora_inizio})
            if res.status_code == 200:
                dati_c = res.json().get("bars", {})
                for s in crypto_assets:
                    barre = dati_c.get(s, dati_c.get(s.replace("/", ""), []))
                    if barre:
                        chiusure = [b["c"] for b in barre]
                        mappa_prezzi[s] = {"prezzo": chiusure[-1], "rsi": calcola_rsi(chiusure)}
                    else: mappa_prezzi[s] = {"prezzo": "No Feed", "rsi": "--"}
            else:
                for s in crypto_assets: mappa_prezzi[s] = {"prezzo": f"Err {res.status_code}", "rsi": "--"}
        except:
            for s in crypto_assets: mappa_prezzi[s] = {"prezzo": "Errore Rete", "rsi": "--"}

    # 2. CANALE DATA WALL STREET & METALLI (STOCKS)
    if stock_assets:
        try:
            url_stocks = "https://data.alpaca.markets/v2/stocks/bars"
            res = requests.get(url_stocks, headers=headers, params={"symbols": ",".join(stock_assets), "timeframe": "5Min", "limit": 2000, "start": ora_inizio})
            if res.status_code == 200:
                dati_s = res.json().get("bars", {})
                for s in stock_assets:
                    barre = dati_s.get(s, [])
                    if barre:
                        chiusure = [b["c"] for b in barre]
                        mappa_prezzi[s] = {"prezzo": chiusure[-1], "rsi": calcola_rsi(chiusure)}
                    else: mappa_prezzi[s] = {"prezzo": "Chiuso/NoFeed", "rsi": "--"}
            else:
                for s in stock_assets: mappa_prezzi[s] = {"prezzo": f"Err {res.status_code}", "rsi": "--"}
        except:
            for s in stock_assets: mappa_prezzi[s] = {"prezzo": "Errore Rete", "rsi": "--"}
            
    return mappa_prezzi

# --- INTERFACCIA TERMINALE v40.0 ---
st.markdown("## 🛰️ Quant Agent Global Terminal v40.0")

if attiva_capitale:
    st.error("🚨 **IMPERIO ARMATO ATTIVO**: Il bot sta cacciando su Criptovalute, Wall Street ed ETF Metalli in contemporanea.")
else:
    st.info("🛡️ **MODALITÀ VEDETTA IN SICUREZZA**: Schermate di analisi attive. Nessun ordine verrà inviato a mercato.")

# Pulsanti di sicurezza laterali
st.sidebar.markdown("---")
st.sidebar.subheader("🚨 Protocollo Difesa")
if st.sidebar.button("💥 PANIC BUTTON MANUALE"):
    posizioni_attuali = ottieni_posizioni_reali(alpaca_key, alpaca_secret)
    for simbolo_clean, dati in posizioni_attuali.items():
        invia_ordine_market(simbolo_clean, "sell", dati["qty"], True, alpaca_key, alpaca_secret)
    st.session_state.scatola_nera = {}
    st.toast("Impero interamente liquidato!", icon="🔥")
    time.sleep(0.5)
    st.rerun()

if st.sidebar.button("🔄 Reset Dati Sessione"):
    st.session_state.scatola_nera = {}
    st.session_state.storico_profitti = []
    if os.path.exists(CACHE_FILE): os.remove(CACHE_FILE)
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.toast("Tabula Rasa Effettuata!", icon="🧼")
    time.sleep(0.5)
    st.rerun()

# Raccolta Metriche
info_conto = ottieni_bilancio_conto(alpaca_key, alpaca_secret)
pos_reali = ottieni_posizioni_reali(alpaca_key, alpaca_secret)
totale_guadagnato = sum([t["Gain ($)"] for t in st.session_state.storico_profitti])

c1, c2, c3 = st.columns(3)
with c1: st.metric("💰 Cash Disponibile", f"$ {info_conto['cash']}")
with c2: st.metric("🛡️ Capitale Corazzata", f"$ {info_conto['portfolio_value']}")
with c3: st.metric("💵 CASSA PROFITTI GLOBAL", f"$ {round(totale_guadagnato, 2)}", delta="Multi-Asset Unificato")

# Download Dati Dual-Core
dati_mercato_freschi = scarica_dati_globali_batch(alpaca_key, alpaca_secret)

tabella_finale_mappa = {}
for coin in tutti_i_soldati:
    coin_clean = coin.replace("/", "")
    dati_c = dati_mercato_freschi.get(coin, {"prezzo": "Errore", "rsi": "--"})
    
    ultimo_prezzo = dati_c["prezzo"]
    rsi_attuale = dati_c["rsi"]
    stato = "🛰️ In Caccia"
    
    if isinstance(ultimo_prezzo, (int, float)):
        ha_posizione = coin_clean in pos_reali or coin in pos_reali
        
        if not ha_posizione and coin in st.session_state.scatola_nera:
            del st.session_state.scatola_nera[coin]
            
        if attiva_capitale:
            condizione = (rsi_attuale < 35) if "Ipervenduto" in tipo_strategia else (rsi_attuale > 65)
            if condizione and not ha_posizione:
                if invia_ordine_market(coin, "buy", size_dollari, False, alpaca_key, alpaca_secret):
                    st.session_state.scatola_nera[coin] = {"prezzo_acquisto": ultimo_prezzo, "prezzo_massimo": ultimo_prezzo, "piramidato": False}
                    st.toast(f"🛒 Acquistato {coin}", icon="🟢")
            
            if ha_posizione:
                if coin not in st.session_state.scatola_nera:
                    st.session_state.scatola_nera[coin] = {"prezzo_acquisto": ultimo_prezzo, "prezzo_massimo": ultimo_prezzo, "piramidato": False}
                
                dati_pos = st.session_state.scatola_nera[coin]
                if ultimo_prezzo > dati_pos["prezzo_massimo"]:
                    st.session_state.scatola_nera[coin]["prezzo_massimo"] = ultimo_prezzo
                    dati_pos["prezzo_massimo"] = ultimo_prezzo
                
                guadagno_pct = ((ultimo_prezzo - dati_pos["prezzo_acquisto"]) / dati_pos["prezzo_acquisto"]) * 100
                discesa_dal_massimo = ((dati_pos["prezzo_massimo"] - ultimo_prezzo) / dati_pos["prezzo_massimo"]) * 100
                stato = f"📦 {round(guadagno_pct, 2)}%"
                
                if "FOMO" in tipo_strategia and rsi_attuale > 78 and not dati_pos.get("piramidato", False):
                    if invia_ordine_market(coin, "buy", size_dollari, False, alpaca_key, alpaca_secret):
                        st.session_state.scatola_nera[coin]["prezzo_acquisto"] = (dati_pos["prezzo_acquisto"] + ultimo_prezzo) / 2
                        st.session_state.scatola_nera[coin]["piramidato"] = True
                
                if guadagno_pct >= trailing_activation and discesa_dal_massimo >= trailing_distance:
                    qty_esatta = pos_reali.get(coin_clean, pos_reali.get(coin))["qty"]
                    if invia_ordine_market(coin, "sell", qty_esatta, True, alpaca_key, alpaca_secret):
                        factor = 2 if dati_pos.get("piramidato", False) else 1
                        st.session_state.storico_profitti.append({
                            "Ora": datetime.now().strftime('%H:%M:%S'), "Asset": coin,
                            "Perf %": f"+{round(guadagno_pct, 2)}%", "Gain ($)": round(((size_dollari * factor) * (guadagno_pct / 100)), 2)
                        })
                        salva_storico_persistente(st.session_state.storico_profitti)
                        del st.session_state.scatola_nera[coin]
                        stato = "💥 Chiuso!"
        elif ha_posizione: 
            stato = "📦 In Posizione"

    tabella_finale_mappa[coin] = {"Prezzo": ultimo_prezzo, "RSI": rsi_attuale, "Stato": stato}

# --- RENDERING DEI BLOCCHI EDITATI ---
for categoria, monete in EQUIPAGGIO.items():
    st.markdown(f"### {categoria}")
    righe_cat = []
    for coin in monete:
        d = tabella_finale_mappa.get(coin, {"Prezzo": "--", "RSI": "--", "Stato": "--"})
        p_val = d["Prezzo"]
        if isinstance(p_val, (int, float)):
            p_str = f"$ {p_val:,.4f}" if p_val < 1 else f"$ {p_val:,.2f}"
        else:
            p_str = str(p_val)
            
        rsi_val = d["RSI"]
        rsi_str = f"{rsi_val:.2f}" if isinstance(rsi_val, (int, float)) else str(rsi_val)
        
        righe_cat.append({
            "Asset": coin, "Prezzo Attuale": p_str, "RSI (5 Min)": rsi_str, "Stato Operativo": str(d["Stato"])
        })
    st.dataframe(pd.DataFrame(righe_cat), use_container_width=True, hide_index=True)

# Console Test manuale
st.markdown("---")
st.subheader("🛠️ Console di Controllo Manuale Global")
token_scelto = st.selectbox("Seleziona Asset da Forzare", tutti_i_soldati)
if st.button("🛒 FORZA ACQUISTO MANUALE (Test)"):
    if invia_ordine_market(token_scelto, "buy", size_dollari, False, alpaca_key, alpaca_secret):
        prezzo_m = tabella_finale_mappa.get(token_scelto, {"Prezzo": 1})["Prezzo"]
        st.session_state.scatola_nera[token_scelto] = {"prezzo_acquisto": prezzo_m if isinstance(prezzo_m, (int, float)) else 1, "prezzo_massimo": prezzo_m if isinstance(prezzo_m, (int, float)) else 1, "piramidato": False}
        st.success(f"Inviato ordine globale per {token_scelto}.")
        time.sleep(0.5)
        st.rerun()

if st.session_state.storico_profitti:
    st.markdown("---")
    st.subheader("💰 Registro dei Bottini di Guerra Persistente")
    st.dataframe(pd.DataFrame(st.session_state.storico_profitti), use_container_width=True)

st.caption(f"Fortezza Unificata v40.0 attiva. Log Orario: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(10)
st.rerun()
