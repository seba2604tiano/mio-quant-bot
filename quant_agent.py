import streamlit as st
import pandas as pd
import requests
import time
import json
import os
from datetime import datetime, timedelta, timezone

# Configurazione iniziale della pagina
st.set_page_config(page_title="Quant Agent Global v43.0", layout="wide")

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
tg_token = st.sidebar.text_input("Telegram Bot Token", value="", type="password", help="Inserisci il token del tuo bot Telegram")
tg_chat_id = st.sidebar.text_input("Telegram Chat ID", value="", help="Inserisci il tuo ID chat di Telegram")

def invia_notifica_telegram(messaggio):
    if tg_token and tg_chat_id:
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": tg_chat_id, "text": messaggio}, timeout=3)
        except:
            pass

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Gestione Munizioni Base")
size_dollari = st.sidebar.slider("Capitale Base per Trade ($)", min_value=5, max_value=500, value=50, step=5)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parametri di Uscita e Taglio Perdite")
hard_stop_loss = st.sidebar.slider("🛡️ Livello 3: Hard Stop Loss (%)", min_value=1.0, max_value=10.0, value=3.0, step=0.5)
trailing_distance = st.sidebar.slider("Distanza Fallback (% dal massimo)", min_value=0.5, max_value=5.0, value=1.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("🏹 Strategia d'Ingresso")
tipo_strategia = st.sidebar.selectbox("Condizione d'Acquisto", ["Ipervenduto Classico + EMA200", "Inseguimento FOMO (RSI > 65)"])

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Pannello Armamenti")
attiva_capitale = st.sidebar.toggle("🚀 ATTIVA TRADING AUTOMATICO", value=stato_precedente)
salva_config_stato(attiva_capitale)

# --- STRUTTURA MULTI-ASSET GLOBAL v43.0 (FILTRATA ED ESPANSA) ---
EQUIPAGGIO = {
    "👑 Crypto Blue-Chips Ufficiali (24/7)": ["BTC/USD", "ETH/USD"],
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

def scarica_dati_globali_batch(key, secret):
    if not key or not secret: return {}
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    mappa_prezzi = {}
    
    crypto_assets = [s for s in tutti_i_soldati if "/USD" in s]
    stock_assets = [s for s in tutti_i_soldati if "/USD" not in s]
    
    ora_inizio_crypto = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ora_inizio_stocks = (datetime.now(timezone.utc) - timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    if crypto_assets:
        try:
            url_crypto = "https://data.alpaca.markets/v1beta3/crypto/us/bars"
            res = requests.get(url_crypto, headers=headers, params={"symbols": ",".join(crypto_assets), "timeframe": "5Min", "limit": 10000, "start": ora_inizio_crypto})
            if res.status_code == 200:
                dati_c = res.json().get("bars", {})
                for s in crypto_assets:
                    barre = dati_c.get(s, dati_c.get(s.replace("/", ""), []))
                    if barre:
                        df = pd.DataFrame(barre)
                        chiusure = df["c"].tolist()
                        high, low, close_prev = df["h"], df["l"], df["c"].shift(1)
                        tr = pd.concat([high - low, (high - close_prev).abs(), (low - close_prev).abs()], axis=1).max(axis=1)
                        atr_val = tr.rolling(14).mean().iloc[-1] if len(tr) >= 14 else 0
                        mappa_prezzi[s] = {"prezzo": chiusure[-1], "rsi": calcola_rsi(chiusure), "ema200": calcola_ema200(chiusure), "atr": atr_val}
                    else: mappa_prezzi[s] = {"prezzo": "No Feed", "rsi": "--", "ema200": None, "atr": 0}
            else:
                for s in crypto_assets: mappa_prezzi[s] = {"prezzo": "Rate Limit", "rsi": "--", "ema200": None, "atr": 0}
        except:
            for s in crypto_assets: mappa_prezzi[s] = {"prezzo": "Errore Rete", "rsi": "--", "ema200": None, "atr": 0}

    if stock_assets:
        try:
            url_stocks = "https://data.alpaca.markets/v2/stocks/bars"
            res = requests.get(url_stocks, headers=headers, params={"symbols": ",".join(stock_assets), "timeframe": "5Min", "limit": 10000, "start": ora_inizio_stocks})
            if res.status_code == 200:
                dati_s = res.json().get("bars", {})
                for s in stock_assets:
                    barre = dati_s.get(s, [])
                    if barre:
                        df = pd.DataFrame(barre)
                        chiusure = df["c"].tolist()
                        high, low, close_prev = df["h"], df["l"], df["c"].shift(1)
                        tr = pd.concat([high - low, (high - close_prev).abs(), (low - close_prev).abs()], axis=1).max(axis=1)
                        atr_val = tr.rolling(14).mean().iloc[-1] if len(tr) >= 14 else 0
                        mappa_prezzi[s] = {"prezzo": chiusure[-1], "rsi": calcola_rsi(chiusure), "ema200": calcola_ema200(chiusure), "atr": atr_val}
                    else: mappa_prezzi[s] = {"prezzo": "Fuori Sessione", "rsi": "--", "ema200": None, "atr": 0}
            else:
                for s in stock_assets: mappa_prezzi[s] = {"prezzo": "Attesa Open", "rsi": "--", "ema200": None, "atr": 0}
        except:
            for s in stock_assets: mappa_prezzi[s] = {"prezzo": "Errore Rete", "rsi": "--", "ema200": None, "atr": 0}
            
    return mappa_prezzi

# --- INTERFACCIA UTENTE ---
st.markdown("## 🛰️ Quant Agent Global Terminal v43.0 • Imperium Maxima")

if attiva_capitale:
    st.error("🚨 **IMPERIO ARMATO ATTIVO**: Monitoraggio feed istituzionali e protezione acquisti multilivello in esecuzione.")
else:
    st.info("🛡️ **MODALITÀ VEDETTA IN SICUREZZA**: Visualizzazione metriche attiva. Nessun ordine verrà inoltrato.")

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
with c3: st.metric("💵 CASSA PROFITTI GLOBAL", f"$ {round(totale_guadagnato, 2)}", delta="Sincronizzazione 3-Tier Attiva")

# --- 🏆 NUOVO BLOCCO: BACHECA DELLA GIOIA TATTICA ---
st.markdown("---")
vincenti = sum(1 for t in st.session_state.storico_profitti if float(t.get("Gain ($)", 0.0)) > 0)
pareggi = sum(1 for t in st.session_state.storico_profitti if "[BREAK-EVEN]" in str(t.get("Perf %", "")))
stop_loss = sum(1 for t in st.session_state.storico_profitti if "[HARD STOP]" in str(t.get("Perf %", "")))

bg_c1, bg_c2 = st.columns([1, 2])
with bg_c1:
    st.markdown(f"#### 📊 Contatore delle Vittorie\n🔥 **{vincenti}** Vincenti  |  🤝 **{pareggi}** Pareggi (BE)  |  🚨 **{stop_loss}** Stop Loss")

with bg_c2:
    trade_vincenti_lista = [t for t in st.session_state.storico_profitti if float(t.get("Gain ($)", 0.0)) > 0]
    if trade_vincenti_lista:
        miglior_colpo = max(trade_vincenti_lista, key=lambda x: float(x.get("Gain ($)", 0.0)))
        st.markdown(f"#### 🥇 Top Gun della Sessione\n🚀 Miglior Colpo: **{miglior_colpo['Asset']}** | Performance: **{miglior_colpo['Perf %']}** | Bottino: **+${miglior_colpo['Gain ($)']}**")
    else:
        st.markdown("#### 🥇 Top Gun della Sessione\n🛰️ In attesa del primo bersaglio utile. Radar in caccia.")

if trade_vincenti_lista:
    with st.expander("🏆 HALL OF FAME DEI PROFITTI (Solo Colpi in Verde)", expanded=True):
        st.dataframe(pd.DataFrame(trade_vincenti_lista), use_container_width=True, hide_index=True)
st.markdown("---")

dati_mercato_freschi = scarica_dati_globali_batch(alpaca_key, alpaca_secret)

tabella_finale_mappa = {}
for coin in tutti_i_soldati:
    coin_clean = coin.replace("/", "")
    dati_c = dati_mercato_freschi.get(coin, {"prezzo": "Errore", "rsi": "--", "ema200": None, "atr": 0})
    
    ultimo_prezzo = dati_c["prezzo"]
    rsi_attuale = dati_c["rsi"]
    ema200_attuale = dati_c["ema200"]
    atr_attuale = dati_c["atr"]
    stato = "🛰️ In Caccia"
    size_ottimizzata = size_dollari
    
    if isinstance(ultimo_prezzo, (int, float)):
        ha_posizione_reale = coin_clean in pos_reali or coin in pos_reali
        
        if not ha_posizione_reale and coin in st.session_state.scatola_nera:
            del st.session_state.scatola_nera[coin]
            
        trend_rialzista = True if (ema200_attuale is None or ultimo_prezzo > ema200_attuale) else False
        
        if atr_attuale > 0:
            atr_pct = (atr_attuale / ultimo_prezzo) * 100
            moltiplicatore_volatilità = 0.35 / max(atr_pct, 0.02)
            moltiplicatore_volatilità = max(0.4, min(moltiplicatore_volatilità, 1.8))
            size_ottimizzata = round(size_dollari * moltiplicatore_volatilità, 2)
        else:
            size_ottimizzata = size_dollari
            
        blocco_acquisto = ha_posizione_reale or (coin in st.session_state.scatola_nera)
            
        if attiva_capitale:
            if "Ipervenduto" in tipo_strategia:
                condizione_ingresso = (rsi_attuale < 35) and trend_rialzista
            else:
                condizione_ingresso = (rsi_attuale > 65)
                
            if condizione_ingresso and not blocco_acquisto:
                if invia_ordine_market(coin, "buy", size_ottimizzata, False, alpaca_key, alpaca_secret):
                    st.session_state.scatola_nera[coin] = {
                        "prezzo_acquisto": ultimo_prezzo, 
                        "prezzo_massimo": ultimo_prezzo, 
                        "piramidato": False, 
                        "size_effettiva": size_ottimizzata,
                        "venduto_parziale": False,
                        "break_even_attivo": False
                    }
                    invia_notifica_telegram(f"🛒 ACQUISTO EFFETTUATO!\nAsset: {coin}\nPrezzo: ${ultimo_prezzo}\nSize: ${size_ottimizzata}")
                    st.toast(f"🛒 Acquistato {coin} (${size_ottimizzata})", icon="🟢")
            
            if ha_posizione_reale:
                if coin not in st.session_state.scatola_nera:
                    st.session_state.scatola_nera[coin] = {
                        "prezzo_acquisto": ultimo_prezzo, 
                        "prezzo_massimo": ultimo_prezzo, 
                        "piramidato": False, 
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
                
                # Livello 3: Hard Stop Loss
                if guadagno_pct <= -hard_stop_loss:
                    qty_rimanente = pos_reali.get(coin_clean, pos_reali.get(coin, {})).get("qty", 0)
                    if qty_rimanente > 0:
                        if invia_ordine_market(coin, "sell", qty_rimanente, True, alpaca_key, alpaca_secret):
                            capitale_impiegato = dati_pos.get("size_effettiva", size_dollari)
                            bottino_dollari = round((capitale_impiegato * (guadagno_pct / 100)), 2)
                            st.session_state.storico_profitti.append({
                                "Ora": datetime.now().strftime('%H:%M:%S'), "Asset": coin,
                                "Perf %": f"{round(guadagno_pct, 2)}% [HARD STOP]", "Gain ($)": bottino_dollari
                            })
                            salva_storico_persistente(st.session_state.storico_profitti)
                            invia_notifica_telegram(f"🚨 HARD STOP LOSS SU {coin}!")
                            del st.session_state.scatola_nera[coin]
                            stato = "💥 Hard Stop"
                            continue
                
                # Livello 2: Take Profit Parziale (50%)
                if guadagno_pct >= 1.5 and not dati_pos.get("venduto_parziale", False):
                    qty_totale = pos_reali.get(coin_clean, pos_reali.get(coin, {})).get("qty", 0)
                    if qty_totale > 0:
                        qty_da_vendere = round(qty_totale / 2, 4)
                        if invia_ordine_market(coin, "sell", qty_da_vendere, True, alpaca_key, alpaca_secret):
                            st.session_state.scatola_nera[coin]["venduto_parziale"] = True
                            st.session_state.scatola_nera[coin]["break_even_attivo"] = True
                            capitale_parziale = dati_pos.get("size_effettiva", size_dollari) / 2
                            bottino_parziale = round((capitale_parziale * (guadagno_pct / 100)), 2)
                            st.session_state.storico_profitti.append({
                                "Ora": datetime.now().strftime('%H:%M:%S'), "Asset": coin,
                                "Perf %": f"+{round(guadagno_pct, 2)}% [TAKE PROFIT 50%]", "Gain ($)": bottino_parziale
                            })
                            salva_storico_persistente(st.session_state.storico_profitti)
                            invia_notifica_telegram(f"✅ TP PARZIALE (50%) su {coin}")
                            st.toast(f"Venduto 50% di {coin}. Break-Even attivo!", icon="🛡️")

                # Livello 2.5: Protezione Break-Even
                if dati_pos.get("break_even_attivo", False) and ultimo_prezzo <= dati_pos["prezzo_acquisto"]:
                    qty_rimanente = pos_reali.get(coin_clean, pos_reali.get(coin, {})).get("qty", 0)
                    if qty_rimanente > 0:
                        if invia_ordine_market(coin, "sell", qty_rimanente, True, alpaca_key, alpaca_secret):
                            st.session_state.storico_profitti.append({
                                "Ora": datetime.now().strftime('%H:%M:%S'), "Asset": coin,
                                "Perf %": "0.0% [BREAK-EVEN]", "Gain ($)": 0.0
                            })
                            salva_storico_persistente(st.session_state.storico_profitti)
                            invia_notifica_telegram(f"🛡️ PROTEZIONE BREAK-EVEN SU {coin}!")
                            del st.session_state.scatola_nera[coin]
                            stato = "🛡️ Break-Even"
                            continue

                # Trailing Stop ATR
                stop_dinamico = dati_pos["prezzo_massimo"] - (2 * atr_attuale) if atr_attuale > 0 else dati_pos["prezzo_massimo"] * (1 - (trailing_distance/100))
                
                if ultimo_prezzo <= stop_dinamico:
                    qty_rimanente = pos_reali.get(coin_clean, pos_reali.get(coin, {})).get("qty", 0)
                    if qty_rimanente > 0:
                        if invia_ordine_market(coin, "sell", qty_rimanente, True, alpaca_key, alpaca_secret):
                            capitale_impiegato = dati_pos.get("size_effettiva", size_dollari)
                            if dati_pos.get("venduto_parziale", False):
                                capitale_impiegato = capitale_impiegato / 2
                            bottino_dollari = round((capitale_impiegato * (guadagno_pct / 100)), 2)
                            st.session_state.storico_profitti.append({
                                "Ora": datetime.now().strftime('%H:%M:%S'), "Asset": coin,
                                "Perf %": f"{round(guadagno_pct, 2)}% [TRAILING]", "Gain ($)": bottino_dollari
                            })
                            salva_storico_persistente(st.session_state.storico_profitti)
                            invia_notifica_telegram(f"💥 CHIUSURA TRAILING ATR SU {coin}!")
                            del st.session_state.scatola_nera[coin]
                            stato = "💥 Chiuso ATR"
        elif ha_posizione_reale: 
            stato = "📦 In Posizione"

    trend_str = "🟢 Rialzista" if (ema200_attuale is None or ultimo_prezzo > ema200_attuale) else "🔴 Ribassista"
    tabella_finale_mappa[coin] = {"Prezzo": ultimo_prezzo, "RSI": rsi_attuale, "Trend (EMA200)": trend_str, "Size Dinamica ($)": round(size_ottimizzata, 2), "Stato": stato}

# Rendering Plance di Comando Categorie
for categoria, monete in EQUIPAGGIO.items():
    st.markdown(f"### {categoria}")
    righe_cat = []
    for coin in monete:
        d = tabella_finale_mappa.get(coin, {"Prezzo": "--", "RSI": "--", "Trend (EMA200)": "--", "Size Dinamica ($)": "--", "Stato": "--"})
        p_val = d["Prezzo"]
        
        if isinstance(p_val, (int, float)):
            if p_val < 1: p_str = f"$ {p_val:,.4f}"
            else: p_str = f"$ {p_val:,.2f}"
        else: 
            p_str = str(p_val)
            
        rsi_val = d["RSI"]
        rsi_str = f"{rsi_val:.2f}" if isinstance(rsi_val, (int, float)) else str(rsi_val)
        size_str = f"$ {d['Size Dinamica ($)']}" if isinstance(d['Size Dinamica ($)'], (int, float)) else "--"
        
        righe_cat.append({
            "Asset": str(coin), 
            "Prezzo Attuale": str(p_str), 
            "RSI (5 Min)": str(rsi_str), 
            "Trend (EMA 200)": str(d["Trend (EMA200)"]), 
            "Size Adattiva ATR": str(size_str), 
            "Stato Operativo": str(d["Stato"])
        })
    st.dataframe(pd.DataFrame(righe_cat), use_container_width=True, hide_index=True)

# Console Test manuale
st.markdown("---")
st.subheader("🛠️ Console di Controllo Manuale Global")
token_scelto = st.selectbox("Seleziona Asset da Forzare", tutti_i_soldati)
if st.button("🛒 FORZA ACQUISTO MANUALE (Test)"):
    size_t = tabella_finale_mappa.get(token_scelto, {"Size Dinamica ($)": size_dollari})["Size Dinamica ($)"]
    if invia_ordine_market(token_scelto, "buy", size_t, False, alpaca_key, alpaca_secret):
        prezzo_m = tabella_finale_mappa.get(token_scelto, {"Prezzo": 1})["Prezzo"]
        st.session_state.scatola_nera[token_scelto] = {
            "prezzo_acquisto": prezzo_m if isinstance(prezzo_m, (int, float)) else 1, 
            "prezzo_massimo": prezzo_m if isinstance(prezzo_m, (int, float)) else 1, 
            "piramidato": False, 
            "size_effettiva": size_t,
            "venduto_parziale": False,
            "break_even_attivo": False
        }
        invia_notifica_telegram(f"🚀 ORDINE MANUALE FORZATO su {token_scelto}!")
        st.success(f"Inviato ordine globale per {token_scelto}.")
        time.sleep(0.5)
        st.rerun()

if st.session_state.storico_profitti:
    st.markdown("---")
    st.subheader("📋 Registro Completo di Sessione (Storico Generale)")
    st.dataframe(pd.DataFrame(st.session_state.storico_profitti), use_container_width=True)

st.caption(f"Fortezza Hyperdrive v43.0 online. Log Orario: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(10)
st.rerun()
