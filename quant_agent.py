import streamlit as st
import pandas as pd
import requests
import time
import json
import os
import yfinance as yf
from datetime import datetime, timedelta, timezone

# Configurazione iniziale della pagina
st.set_page_config(page_title="Quant Agent Global v45.0", layout="wide")

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

# --- CONFIGURAZIONE SATELLITE TELEGRAM ---
st.sidebar.markdown("---")
st.sidebar.subheader("📱 Radar Notifiche Telegram")
tg_token = st.sidebar.text_input("Telegram Bot Token", value="", type="password")
tg_chat_id = st.sidebar.text_input("Telegram Chat ID", value="")

def invia_notifica_telegram(messaggio):
    if tg_token and tg_chat_id:
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": tg_chat_id, "text": messaging}, timeout=3)
        except:
            pass

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Gestione Munizioni Base")
size_dollari = st.sidebar.slider("Capitale Base per Trade ($)", min_value=5, max_value=500, value=50, step=5)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Parametri Triple Shield (v45.0)")
moltiplicatore_vol = st.sidebar.slider("Filtro Volumi (Soglia x Media)", min_value=1.1, max_value=2.5, value=1.5, step=0.1)
moltiplicatore_atr_stop = st.sidebar.slider("Moltiplicatore ATR Stop Loss", min_value=1.5, max_value=4.0, value=2.5, step=0.1)
trailing_distance = st.sidebar.slider("Distanza Fallback Trailing (% dal max)", min_value=0.5, max_value=5.0, value=1.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("🏹 Strategia d'Ingresso")
tipo_strategia = st.sidebar.selectbox("Condizione d'Acquisto", ["Ipervenduto Classico (RSI < 35)", "Inseguimento FOMO (RSI > 65)"])

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Pannello Armamenti")
attiva_capitale = st.sidebar.toggle("🚀 ATTIVA TRADING AUTOMATICO", value=stato_precedente)
salva_config_stato(attiva_capitale)

# --- STRUTTURA MULTI-ASSET GLOBAL v45.0 ---
EQUIPAGGIO = {
    "👑 Crypto Blue-Chips Ufficiali (24/7)": ["BTC/USD", "ETH/USD", "SOL/USD"],
    "🇺🇸 I Giganti di Wall Street (Azioni USA)": [
        "AAPL", "TSLA", "NVDA", "AMZN", "MSFT", "GOOGL", "META", "NFLX", "AMD", "PLTR",
        "SMCI", "MU", "AVGO", "COIN", "LLY", "JPM", "XOM", "COST", "DIS", "NKE"
    ],
    "📊 ETF Indici e Settori Chiave USA": ["SPY", "QQQ", "SOXX", "XLF"],
    "📀 Metalli Preziosi (ETF Safe Haven)": ["GLD", "SLV"]
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

def calcola_ema200(prezzi):
    if len(prezzi) < 200: return None
    return round(pd.Series(prezzi).ewm(span=200, adjust=False).mean().iloc[-1], 4)

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

def scarica_dati_globali_batch():
    mappa_prezzi = {}
    ticker_mapping = {}
    
    for s in tutti_i_soldati:
        yf_ticker = s.replace("/", "-") if "/USD" in s else s
        ticker_mapping[yf_ticker] = s
        
    tickers_list = list(ticker_mapping.keys())
    
    try:
        df_global_5m = yf.download(" ".join(tickers_list), period="5d", interval="5m", progress=False)
        df_global_1h = yf.download(" ".join(tickers_list), period="60d", interval="1h", progress=False)
        
        for yf_tick, orig_tick in ticker_mapping.items():
            try:
                if len(tickers_list) == 1:
                    df_tick = df_global_5m.dropna()
                    df_tick_1h = df_global_1h.dropna()
                else:
                    df_tick = pd.DataFrame({
                        "Close": df_global_5m["Close"][yf_tick], "High": df_global_5m["High"][yf_tick],
                        "Low": df_global_5m["Low"][yf_tick], "Volume": df_global_5m["Volume"][yf_tick]
                    }).dropna()
                    df_tick_1h = pd.DataFrame({"Close": df_global_1h["Close"][yf_tick]}).dropna()
                
                if not df_tick.empty and "Close" in df_tick:
                    chiusure = df_tick["Close"].tolist()
                    volumi = df_tick["Volume"].tolist()
                    high = df_tick["High"]
                    low = df_tick["Low"]
                    close_prev = df_tick["Close"].shift(1)
                    
                    tr = pd.concat([high - low, (high - close_prev).abs(), (low - close_prev).abs()], axis=1).max(axis=1)
                    atr_val = tr.rolling(14).mean().iloc[-1] if len(tr) >= 14 else 0
                    
                    ema200_1h = None
                    if not df_tick_1h.empty and len(df_tick_1h) >= 200:
                        ema200_1h = calcola_ema200(df_tick_1h["Close"].tolist())
                        
                    vol_attuale = volumi[-1] if len(volumi) > 0 else 0
                    media_vol_20 = pd.Series(volumi).rolling(20).mean().iloc[-1] if len(volumi) >= 20 else 1
                    volume_valido = vol_attuale >= (media_vol_20 * moltiplicatore_vol)
                    
                    mappa_prezzi[orig_tick] = {
                        "prezzo": round(chiusure[-1], 4) if chiusure[-1] < 1 else round(chiusure[-1], 2),
                        "rsi": calcola_rsi(chiusure),
                        "ema200_1h": ema200_1h,
                        "vol_attuale": vol_attuale,
                        "media_vol_20": round(media_vol_20, 2),
                        "volume_valido": volume_valido,
                        "atr": atr_val
                    }
                else:
                    mappa_prezzi[orig_tick] = {"prezzo": "Senza Feed", "rsi": "--", "ema200_1h": None, "volume_valido": False, "atr": 0, "vol_attuale": 0, "media_vol_20": 1}
            except:
                mappa_prezzi[orig_tick] = {"prezzo": "Errore Elab.", "rsi": "--", "ema200_1h": None, "volume_valido": False, "atr": 0, "vol_attuale": 0, "media_vol_20": 1}
    except:
        for s in tutti_i_soldati:
            mappa_prezzi[s] = {"prezzo": "Offline Radar", "rsi": "--", "ema200_1h": None, "volume_valido": False, "atr": 0, "vol_attuale": 0, "media_vol_20": 1}
            
    return mappa_prezzi

# --- INTERFACCIA UTENTE ---
st.markdown("## 🛰️ Quant Agent Global Terminal v45.0 • Triple Shield Architecture")

if attiva_capitale:
    st.error("🚨 **SISTEMA TRADING ARMATO E ATTIVO**: Scansione volumetrica 3-Tier e Stop Loss Adattivo in esecuzione.")
else:
    st.info("🛡️ **MODALITÀ VEDETTA IN SICUREZZA**: I tre filtri stanno analizzando il mercato in tempo reale senza inviare ordini.")

# Pulsanti di sicurezza sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🚨 Protocollo Difesa")
if st.sidebar.button("💥 PANIC BUTTON MANUALE"):
    posizioni_attuali = ottieni_posizioni_reali(alpaca_key, alpaca_secret)
    for simbolo_clean, dati in posizioni_attuali.items():
        invia_ordine_market(simbolo_clean, "sell", dati["qty"], True, alpaca_key, alpaca_secret)
    st.session_state.scatola_nera = {}
    invia_notifica_telegram("⚠️ PROTOCOLLO LIQUIDAZIONE TOTALE ATTIVATO MANUALE!")
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

# Metriche principali di conto
info_conto = ottieni_bilancio_conto(alpaca_key, alpaca_secret)
pos_reali = ottieni_posizioni_reali(alpaca_key, alpaca_secret)
totale_guadagnato = sum([t["Gain ($)"] for t in st.session_state.storico_profitti])

c1, c2, c3 = st.columns(3)
with c1: st.metric("💰 Cash Disponibile", f"$ {info_conto['cash']}")
with c2: st.metric("🛡️ Capitale Corazzata", f"$ {info_conto['portfolio_value']}")
with c3: st.metric("💵 CASSA PROFITTI GLOBAL", f"$ {round(totale_guadagnato, 2)}", delta="Filtri Volumetrici Attivi")

# --- BACHECA STATISTICHE ---
st.markdown("---")
vincenti = sum(1 for t in st.session_state.storico_profitti if float(t.get("Gain ($)", 0.0)) > 0)
pareggi = sum(1 for t in st.session_state.storico_profitti if "[BREAK-EVEN]" in str(t.get("Perf %", "")))
stop_loss = sum(1 for t in st.session_state.storico_profitti if "[ATR STOP]" in str(t.get("Perf %", "")) or "[HARD STOP]" in str(t.get("Perf %", "")))

bg_c1, bg_c2 = st.columns([1, 2])
with bg_c1:
    st.markdown(f"#### 📊 Contatore dei Vittorie\n🔥 **{vincenti}** Vincenti  |  🤝 **{pareggi}** Pareggi (BE)  |  🚨 **{stop_loss}** Stop Loss")

with bg_c2:
    trade_vincenti_lista = [t for t in st.session_state.storico_profitti if float(t.get("Gain ($)", 0.0)) > 0]
    if trade_vincenti_lista:
        miglior_colpo = max(trade_vincenti_lista, key=lambda x: float(x.get("Gain ($)", 0.0)))
        st.markdown(f"#### 🥇 Top Gun della Sessione\n🚀 Miglior Colpo: **{miglior_colpo['Asset']}** | Bottino: **+${miglior_colpo['Gain ($)']}**")
    else:
        st.markdown("#### 🥇 Top Gun della Sessione\n🛰️ In attesa del primo bersaglio conforme ai 3 Schermi Difensivi.")

if trade_vincenti_lista:
    with st.expander("🏆 HALL OF FAME DEI PROFITTI", expanded=True):
        st.dataframe(pd.DataFrame(trade_vincenti_lista), use_container_width=True, hide_index=True)
st.markdown("---")

dati_mercato_freschi = scarica_dati_globali_batch()

tabella_finale_mappa = {}
for coin in tutti_i_soldati:
    coin_clean = coin.replace("/", "")
    dati_c = dati_mercato_freschi.get(coin, {"prezzo": "Errore", "rsi": "--", "ema200_1h": None, "volume_valido": False, "atr": 0, "vol_attuale": 0, "media_vol_20": 1})
    
    ultimo_prezzo = dati_c["prezzo"]
    rsi_attuale = dati_c["rsi"]
    ema200_1h_attuale = dati_c["ema200_1h"]
    volume_valido_attuale = dati_c["volume_valido"]
    atr_attuale = dati_c["atr"]
    stato = "🛰️ In Caccia"
    trend_macro_rialzista = False
    
    if isinstance(ultimo_prezzo, (int, float)):
        ha_posizione_reale = coin_clean in pos_reali or coin in pos_reali
        blocco_acquisto = ha_posizione_reale or (coin in st.session_state.scatola_nera)
        
        trend_macro_rialzista = True if (ema200_1h_attuale is None or ultimo_prezzo > ema200_1h_attuale) else False
        
        if atr_attuale > 0:
            atr_pct = (atr_attuale / ultimo_prezzo) * 100
            moltiplicatore_volatilità = 0.35 / max(atr_pct, 0.02)
            moltiplicatore_volatilità = max(0.4, min(moltiplicatore_volatilità, 1.8))
            size_ottimizzata = round(size_dollari * moltiplicatore_volatilità, 2)
        else:
            size_ottimizzata = size_dollari
            
        if attiva_capitale:
            if "Ipervenduto" in tipo_strategia:
                condizione_rsi = (rsi_attuale < 35)
            else:
                condizione_rsi = (rsi_attuale > 65)
                
            if condizione_rsi and trend_macro_rialzista and volume_valido_attuale and not blocco_acquisto:
                if invia_ordine_market(coin, "buy", size_ottimizzata, False, alpaca_key, alpaca_secret):
                    stop_loss_iniziale_atr = ultimo_prezzo - (moltiplicatore_atr_stop * atr_attuale) if atr_attuale > 0 else ultimo_prezzo * 0.97
                    
                    st.session_state.scatola_nera[coin] = {
                        "prezzo_acquisto": ultimo_prezzo, 
                        "prezzo_massimo": ultimo_prezzo, 
                        "stop_loss_atr": round(stop_loss_iniziale_atr, 4),
                        "size_effettiva": size_ottimizzata,
                        "venduto_parziale": False,
                        "break_even_attivo": False
                    }
                    invia_notifica_telegram(f"🛒 TRIPLE SHIELD BUY!\nAsset: {coin}\nPrezzo: ${ultimo_prezzo}\nVolumi: {dati_c['vol_attuale']} (Media: {dati_c['media_vol_20']})\nStop Loss ATR: ${round(stop_loss_iniziale_atr, 2)}")
                    st.toast(f"🛒 Acquistato {coin} dopo validazione filtri!", icon="🟢")
            
            if ha_posizione_reale:
                if coin not in st.session_state.scatola_nera:
                    stop_loss_iniziale_atr = ultimo_prezzo - (moltiplicatore_atr_stop * atr_attuale) if atr_attuale > 0 else ultimo_prezzo * 0.97
                    st.session_state.scatola_nera[coin] = {
                        "prezzo_acquisto": ultimo_prezzo, 
                        "prezzo_massimo": ultimo_prezzo, 
                        "stop_loss_atr": round(stop_loss_iniziale_atr, 4),
                        "size_effettiva": size_dollari,
                        "venduto_parziale": False,
                        "break_even_attivo": False
                    }
                
                dati_pos = st.session_state.scatola_nera[coin]
                
                if ultimo_prezzo > dati_pos.get("prezzo_massimo", ultimo_prezzo):
                    st.session_state.scatola_nera[coin]["prezzo_massimo"] = ultimo_prezzo
                    dati_pos["prezzo_massimo"] = ultimo_prezzo
                
                guadagno_pct = ((ultimo_prezzo - dati_pos["prezzo_acquisto"]) / dati_pos["prezzo_acquisto"]) * 100
                stato = f"📦 {round(guadagno_pct, 2)}%"
                
                # 1. SCUDO ATR STOP LOSS
                if ultimo_prezzo <= dati_pos.get("stop_loss_atr", 0):
                    qty_rimanente = pos_reali.get(coin_clean, pos_reali.get(coin, {})).get("qty", 0)
                    if qty_rimanente > 0:
                        if invia_ordine_market(coin, "sell", qty_rimanente, True, alpaca_key, alpaca_secret):
                            cap_imp = dati_pos.get("size_effettiva", size_dollari)
                            bot_dol = round((cap_imp * (guadagno_pct / 100)), 2)
                            d_sl = {"Ora": datetime.now().strftime('%H:%M:%S'), "Asset": coin, "Perf %": f"{round(guadagno_pct, 2)}% [ATR STOP]", "Gain ($)": bot_dol}
                            st.session_state.storico_profitti.append(d_sl)
                            salva_storico_persistente(st.session_state.storico_profitti)
                            invia_notifica_telegram(f"🚨 SCUDO ATR ATTIVATO: Chiusura stop loss su {coin}!")
                            del st.session_state.scatola_nera[coin]
                            stato = "💥 ATR Stop"
                            continue
                
                # 2. TAKE PROFIT PARZIALE (50%)
                if guadagno_pct >= 1.5 and not dati_pos.get("venduto_parziale", False):
                    qty_totale = pos_reali.get(coin_clean, pos_reali.get(coin, {})).get("qty", 0)
                    if qty_totale > 0:
                        qty_da_vendere = round(qty_totale / 2, 4)
                        if invia_ordine_market(coin, "sell", qty_da_vendere, True, alpaca_key, alp
