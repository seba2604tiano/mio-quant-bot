import streamlit as st
import pandas as pd
import requests
import time
import json
import os
from datetime import datetime

# Configurazione iniziale della pagina
st.set_page_config(page_title="Quant Agent Fast v38.9", layout="wide")

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

if trading_mode == "Live (Reale)": BASE_URL = "https://api.alpaca.markets"
else: BASE_URL = "https://paper-api.alpaca.markets"

DATA_URL = "https://data.alpaca.markets/v1beta3/crypto/us/bars"

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
# Il flag ora ricorda lo stato anche se spegni il PC o fai il refresh
attiva_capitale = st.sidebar.checkbox("🚀 Attiva Trading Automatico", value=stato_precedente)
salva_config_stato(attiva_capitale)

if attiva_capitale:
    st.sidebar.warning("⚠️ AUTOMAZIONE ATTIVA: La fortezza è in caccia continua.")

# Asset stabili certificati Alpaca
EQUIPAGGIO = {
    "👑 I Re del Mercato": ["BTC/USD", "ETH/USD", "SOL/USD"],
    "⚡ I Pilastri Altcoin": ["AVAX/USD", "LINK/USD", "DOT/USD", "LTC/USD", "XRP/USD", "BCH/USD"],
    "🌶️ Battaglione Meme (Botti Notturni)": ["DOGE/USD", "SHIB/USD", "PEPE/USD", "WIF/USD", "BONK/USD"],
    "🔮 DeFi & Web3 Leader": ["UNI/USD", "AAVE/USD", "GRT/USD", "LDO/USD"]
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
    if is_qty: payload["qty"] = str(quantita_o_dollari)
    else: payload["notional"] = str(quantita_o_dollari)
    try:
        res = requests.post(url_ordine, json=payload, headers=headers)
        return res.status_code == 200 or res.status_code == 201
    except: return False

# --- NUOVA FUNZIONE: SCANSIONE SUPER-FAST BATCH (1 SOLA CHIAMATA API) ---
def scarica_dati_globali_batch(key, secret):
    if not key or not secret: return {}
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    # Uniamo tutti i simboli in un'unica stringa per la chiamata cumulativa
    simboli_cumulati = ",".join(tutti_i_soldati)
    params = {"symbols": simboli_cumulati, "timeframe": "2Min", "limit": 30}
    
    mappa_prezzi = {}
    try:
        risposta = requests.get(DATA_URL, headers=headers, params=params)
        if risposta.status_code == 200:
            dati_totali = risposta.json().get("bars", {})
            for s in tutti_i_soldati:
                s_clean = s.replace("/", "")
                # Cerca i dati sia con lo slash che senza
                barre = dati_totali.get(s, dati_totali.get(s_clean, []))
                if barre:
                    prezzi_chiusura = [b["c"] for b in barre]
                    mappa_prezzi[s] = {"prezzo": prezzi_chiusura[-1], "rsi": calcola_rsi(prezzi_chiusura)}
                else:
                    mappa_prezzi[s] = {"prezzo": "No Feed", "rsi": "--"}
        else:
            for s in tutti_i_soldati: mappa_prezzi[s] = {"prezzo": "Rate Limit", "rsi": "--"}
    except:
        for s in tutti_i_soldati: mappa_prezzi[s] = {"prezzo": "Errore Rete", "rsi": "--"}
    return mappa_prezzi

# --- GRAFICA TERMINALE OPERATIVO ---
st.markdown("## 🛰️ Quant Agent High-Speed Terminal v38.9 — MEGA-BATCH DATA FEED")

# Controlli Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("🚨 Protocollo Difesa")
if st.sidebar.button("💥 PANIC BUTTON MANUALE"):
    posizioni_attuali = ottieni_posizioni_reali(alpaca_key, alpaca_secret)
    for simbolo_clean, dati in posizioni_attuali.items():
        invia_ordine_market(simbolo_clean, "sell", dati["qty"], True, alpaca_key, alpaca_secret)
    st.session_state.scatola_nera = {}
    st.toast("Portafoglio interamente liquidato!", icon="🔥")
    time.sleep(0.5)
    st.rerun()

if st.sidebar.button("🔄 Reset Dati Sessione"):
    st.session_state.scatola_nera = {}
    st.session_state.storico_profitti = []
    if os.path.exists(CACHE_FILE): os.remove(CACHE_FILE)
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    st.toast("Tabula Rasa effettuata!", icon="🧼")
    time.sleep(0.5)
    st.rerun()

info_conto = ottieni_bilancio_conto(alpaca_key, alpaca_secret)
pos_reali = ottieni_posizioni_reali(alpaca_key, alpaca_secret)
totale_guadagnato = sum([t["Gain ($)"] for t in st.session_state.storico_profitti])

c1, c2, c3 = st.columns(3)
with c1: st.metric("💰 Cash Disponibile", f"$ {info_conto['cash']}")
with c2: st.metric("🛡️ Capitale Corazzata", f"$ {info_conto['portfolio_value']}")
with c3: st.metric("💵 CASSA PROFITTI SESSIONE", f"$ {round(totale_guadagnato, 2)}", delta="Ottimizzazione Batch Attiva")

# Esegui l'unica chiamata internet per tutti i prezzi
dati_mercato_freschi = scarica_dati_globali_batch(alpaca_key, alpaca_secret)

# Elaborazione trading ed esposizione tabelle
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
        elif ha_posizione: stato = "📦 In Posizione"

    tabella_finale_mappa[coin] = {"Prezzo": ultimo_prezzo, "RSI": rsi_attuale, "Stato": stato}

# Rendering delle griglie visive velocizzate
for categoria, monete in EQUIPAGGIO.items():
    st.markdown(f"### {categoria}")
    righe_cat = []
    for coin in monete:
        d = tabella_finale_mappa.get(coin, {"Prezzo": "--", "RSI": "--", "Stato": "--"})
        righe_cat.append({"Asset": coin, "Prezzo Attuale": d["Prezzo"], "RSI (2 Min)": d["RSI"], "Stato Operativo / Profitto": d["Stato"]})
    st.dataframe(pd.DataFrame(righe_cat), use_container_width=True, hide_index=True)

# Console di stress-test manuale aggiornata
st.markdown("---")
st.subheader("🛠️ Console di Controllo Manuale (Stress-Test Sandbox)")
token_scelto = st.selectbox("Seleziona Asset da Forzare", tutti_i_soldati)
if st.button("🛒 FORZA ACQUISTO MANUALE (Test)"):
    if invia_ordine_market(token_scelto, "buy", size_dollari, False, alpaca_key, alpaca_secret):
        prezzo_m = tabella_finale_mappa.get(token_scelto, {"Prezzo": 1})["Prezzo"]
        st.session_state.scatola_nera[token_scelto] = {"prezzo_acquisto": prezzo_m if isinstance(prezzo_m, (int, float)) else 1, "prezzo_massimo": prezzo_m if isinstance(prezzo_m, (int, float)) else 1, "piramidato": False}
        st.success(f"Inviato ordine d'acquisto forzato per {token_scelto}.")
        time.sleep(0.5)
        st.rerun()

if st.session_state.storico_profitti:
    st.markdown("---")
    st.subheader("💰 Registro dei Bottini di Guerra Persistente")
    st.dataframe(pd.DataFrame(st.session_state.storico_profitti), use_container_width=True)

if st.session_state.scatola_nera:
    st.markdown("---")
    st.subheader("📊 Inseguimento Scatola Nera Attiva")
    st.dataframe(pd.DataFrame(st.session_state.scatola_nera).T, use_container_width=True)

st.caption(f"Fortezza v38.9 sbloccata. Orario: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(10)
st.rerun()
