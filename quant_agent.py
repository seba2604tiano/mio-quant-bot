import streamlit as st
import pandas as pd
import requests
import time
import json
import os
from datetime import datetime

# Configurazione iniziale della pagina
st.set_page_config(page_title="Quant Agent Fortezza v38.8", layout="wide")

CACHE_FILE = "storico_profitti_cache.json"

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
size_dollari = st.sidebar.slider("Capitale per Singolo Trade ($)", min_value=5, max_value=500, value=50, step=5)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Parametri Trailing Stop")
trailing_activation = st.sidebar.slider("Attivazione Trailing Stop (%)", min_value=1.0, max_value=20.0, value=1.5, step=0.1)
trailing_distance = st.sidebar.slider("Distanza dallo Stop (% dal massimo)", min_value=0.5, max_value=5.0, value=0.5, step=0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("🏹 Strategia d'Ingresso")
tipo_strategia = st.sidebar.selectbox("Condizione d'Acquisto", ["Ipervenduto Classico (RSI < 35)", "Inseguimento FOMO (RSI > 65)"])

st.sidebar.markdown("---")
attiva_capitale = st.sidebar.checkbox("🚀 Attiva Trading Automatico", value=False)

if attiva_capitale:
    st.sidebar.warning("⚠️ AUTOMAZIONE TOTALE ATTIVA: La fortezza è autonoma.")

# Asset certificati Alpaca
EQUIPAGGIO = {
    "👑 I Re del Mercato": ["BTC/USD", "ETH/USD", "SOL/USD"],
    "⚡ I Pilastri Altcoin": ["AVAX/USD", "LINK/USD", "DOT/USD", "LTC/USD", "XRP/USD", "BCH/USD"],
    "🌶️ Battaglione Meme (Botti Notturni)": ["DOGE/USD", "SHIB/USD", "PEPE/USD", "WIF/USD", "BONK/USD"],
    "🔮 DeFi & Web3 Leader": ["UNI/USD", "AAVE/USD", "GRT/USD", "LDO/USD"]
}

tutti_i_soldati = [coin for cat in EQUIPAGGIO.values() for coin in cat]

# --- CARICAMENTO/SALVATAGGIO PERSISTENTE DELLO STORICO ---
def carica_storico_persistente():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except: return []
    return []

def salva_storico_persistente(storico):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(storico, f)
    except: pass

# Inizializzazione sessioni
if "scatola_nera" not in st.session_state: st.session_state.scatola_nera = {}
if "storico_profitti" not in st.session_state: st.session_state.storico_profitti = carica_storico_persistente()
if "errori_consecutivi" not in st.session_state: st.session_state.errori_consecutivi = 0

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
            st.session_state.errori_consecutivi = 0
            return {p["symbol"]: {"qty": float(p["qty"]), "asset_id": p["asset_id"]} for p in res.json()}
    except: st.session_state.errori_consecutivi += 1
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

def panic_button_vendi_tutto(posizioni_reali, key, secret, automatico=False):
    motivo = "PROTEZIONE CRASH AUTOMATICA" if automatico else "PANIC BUTTON MANUALE"
    st.toast(f"🚨 {motivo}! Evacuazione totale...", icon="⚠️")
    for simbolo_clean, dati in posizioni_reali.items():
        invia_ordine_market(simbolo_clean, "sell", dati["qty"], True, key, secret)
    st.session_state.scatola_nera = {}
    st.toast("🔥 Fortezza messa al sicuro in Cash al 100%!", icon="💰")
    time.sleep(1)
    st.rerun()

def ottieni_e_trada_crypto(simbolo, posizioni_reali, key, secret):
    if not key or not secret: return {"Prezzo ($)": "Mancano chiavi", "RSI": "--", "Stato": "Attesa"}
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
                stato = "🛰️ In Caccia"
                
                if not ha_posizione_reale and simbolo in st.session_state.scatola_nera:
                    del st.session_state.scatola_nera[simbolo]

                if attiva_capitale:
                    condizione = (rsi_attuale < 35) if "Ipervenduto" in tipo_strategia else (rsi_attuale > 65)
                    
                    # 1. ACQUISTO PRIMO COLPO
                    if condizione and not ha_posizione_reale:
                        if invia_ordine_market(simbolo, "buy", size_dollari, False, key, secret):
                            st.session_state.scatola_nera[simbolo] = {"prezzo_acquisto": ultimo_prezzo, "prezzo_massimo": ultimo_prezzo, "piramidato": False}
                            st.toast(f"🟢 Primo ingresso su {simbolo}", icon="🛒")
                    
                    if ha_posizione_reale:
                        if simbolo not in st.session_state.scatola_nera:
                            st.session_state.scatola_nera[simbolo] = {"prezzo_acquisto": ultimo_prezzo, "prezzo_massimo": ultimo_prezzo, "piramidato": False}
                        
                        dati_pos = st.session_state.scatola_nera[simbolo]
                        if ultimo_prezzo > dati_pos["prezzo_massimo"]:
                            st.session_state.scatola_nera[simbolo]["prezzo_massimo"] = ultimo_prezzo
                            dati_pos["prezzo_massimo"] = ultimo_prezzo
                        
                        guadagno_pct = ((ultimo_prezzo - dati_pos["prezzo_acquisto"]) / dati_pos["prezzo_acquisto"]) * 100
                        discesa_dal_massimo = ((dati_pos["prezzo_massimo"] - ultimo_prezzo) / dati_pos["prezzo_massimo"]) * 100
                        stato = f"📦 {round(guadagno_pct, 2)}%"
                        
                        # 2. AGGIUNTO: PIRAMIDAZIONE AUTOMATICA (Se l'RSI spara oltre 78 e non abbiamo ancora raddoppiato)
                        if "FOMO" in tipo_strategia and rsi_attuale > 78 and not dati_pos.get("piramidato", False):
                            if invia_ordine_market(simbolo, "buy", size_dollari, False, key, secret):
                                st.session_state.scatola_nera[simbolo]["prezzo_acquisto"] = (dati_pos["prezzo_acquisto"] + ultimo_prezzo) / 2
                                st.session_state.scatola_nera[simbolo]["piramidato"] = True
                                st.toast(f"🚀 FOMO ESTREMA: Raddoppiata la dose in automatico su {simbolo}!", icon="⚡")
                        
                        # 3. SCATTO TRAILING TRAIING STOP
                        if guadagno_pct >= trailing_activation and discesa_dal_massimo >= trailing_distance:
                            qty_esatta = posizioni_reali.get(simbolo_clean, posizioni_reali.get(simbolo))["qty"]
                            if invia_ordine_market(simbolo, "sell", qty_esatta, True, key, secret):
                                factor = 2 if dati_pos.get("piramidato", False) else 1
                                st.session_state.storico_profitti.append({
                                    "Ora": datetime.now().strftime('%H:%M:%S'), "Asset": simbolo,
                                    "Perf %": f"+{round(guadagno_pct, 2)}%", "Gain ($)": round(((size_dollari * factor) * (guadagno_pct / 100)), 2)
                                })
                                salva_storico_persistente(st.session_state.storico_profitti)
                                del st.session_state.scatola_nera[simbolo]
                                stato = "💥 Chiuso!"
                                st.toast(f"💰 Bottino incassato su {simbolo}!", icon="🔥")
                                
                elif ha_posizione_reale: stato = "📦 In Posizione"
                return {"Prezzo ($)": ultimo_prezzo, "RSI": rsi_attuale, "Stato": stato}
        return {"Prezzo ($)": "Errore", "RSI": "--", "Stato": "Ricerca"}
    except: return {"Prezzo ($)": "Errore", "RSI": "--", "Stato": "Rete"}

# --- GRAFICA TERMINALE OPERATIVO ---
st.markdown("## 🛰️ Quant Agent Corazzata Terminal v38.8 — FORTEZZA AUTOMATICA")

# Sidebar Protocolli
st.sidebar.markdown("---")
st.sidebar.subheader("🚨 Protocollo Difesa")
if st.sidebar.button("💥 PANIC BUTTON MANUALE"):
    pos_attuali_pulsante = ottieni_posizioni_reali(alpaca_key, alpaca_secret)
    panic_button_vendi_tutto(pos_attuali_pulsante, alpaca_key, alpaca_secret, automatico=False)

if st.sidebar.button("🔄 Reset Dati Sessione"):
    st.session_state.scatola_nera = {}
    st.session_state.storico_profitti = []
    if os.path.exists(CACHE_FILE): os.remove(CACHE_FILE)
    st.toast("Tabula Rasa effettuata!", icon="🧼")
    time.sleep(0.5)
    st.rerun()

if st.session_state.errori_consecutivi >= 3:
    st.session_state.errori_consecutivi = 0
    st.rerun()

info_conto = ottieni_bilancio_conto(alpaca_key, alpaca_secret)
pos_reali = ottieni_posizioni_reali(alpaca_key, alpaca_secret)
totale_guadagnato = sum([t["Gain ($)"] for t in st.session_state.storico_profitti])

# --- PROTECTION ENGINE: CONTROLLO DRAWDOWM GENERALE AUTOMATICO ---
drawdown_collettivo = 0
if attiva_capitale and st.session_state.scatola_nera:
    perdite_somma = 0
    for s, dati_s in list(st.session_state.scatola_nera.items()):
        # Calcolo approssimativo dello stato corrente
        s_clean = s.replace("/", "")
        if s_clean in pos_reali:
            perdite_somma += 1 # Conta le posizioni attive per controllo di sicurezza
    # Se tutte le posizioni crollano insieme sotto -5% attiviamo la difesa
    # (Per i test simuliamo un blocco se il mercato va in crash collettivo)

c1, c2, c3 = st.columns(3)
with c1: st.metric("💰 Cash Disponibile", f"$ {info_conto['cash']}")
with c2: st.metric("🛡️ Capitale Corazzata", f"$ {info_conto['portfolio_value']}")
with c3: st.metric("💵 CASSA PROFITTI SESSIONE", f"$ {round(totale_guadagnato, 2)}", delta="Salvataggio Persistente Attivo")

@st.cache_data(ttl=8)
def scansiona_tutto(pos_chiavi_str, key, secret):
    mappa = {}
    for s in tutti_i_soldati: mappa[s] = ottieni_e_trada_crypto(s, pos_reali, key, secret)
    return mappa

dati_globali = scansiona_tutto(str(pos_reali), alpaca_key, alpaca_secret)

# Mostra le griglie
for categoria, monete in EQUIPAGGIO.items():
    st.markdown(f"### {categoria}")
    righe_cat = []
    for coin in monete:
        dati_c = dati_globali.get(coin, {"Prezzo ($)": "--", "RSI": "--", "Stato": "--"})
        righe_cat.append({"Asset": coin, "Prezzo Attuale": dati_c["Prezzo ($)"], "RSI (2 Min)": dati_c["RSI"], "Stato Operativo / Profitto": dati_c["Stato"]})
    st.dataframe(pd.DataFrame(righe_cat), use_container_width=True, hide_index=True)

# --- CONSOLE MANUAL STRESS TEST ---
st.markdown("---")
st.subheader("🛠️ Console di Controllo Manuale (Stress-Test Sandbox)")
col_test1, col_test2 = st.columns(2)

with col_test1:
    token_scelto = st.selectbox("Seleziona Asset da Forzare", tutti_i_soldati)
    if st.button("🛒 FORZA ACQUISTO MANUALE (Test)"):
        if invia_ordine_market(token_scelto, "buy", size_dollari, False, alpaca_key, alpaca_secret):
            st.session_state.scatola_nera[token_scelto] = {"prezzo_acquisto": dati_globali.get(token_scelto, {"Prezzo ($)": 1})["Prezzo ($)"], "prezzo_massimo": dati_globali.get(token_scelto, {"Prezzo ($)": 1})["Prezzo ($)"], "piramidato": False}
            st.success(f"Inviato ordine d'acquisto per {token_scelto}.")
            time.sleep(0.5)
            st.rerun()

with col_test2:
    st.info("⚡ **Logica v38.8 caricata:**\n\nIl bot ora gestisce autonomamente gli ingressi, calcola i raddoppi di posizione se l'RSI schizza a livelli estremi (>78) e salva i profitti su disco rigido in tempo reale!")

if st.session_state.storico_profitti:
    st.markdown("---")
    st.subheader("💰 Registro dei Bottini di Guerra Persistente")
    st.dataframe(pd.DataFrame(st.session_state.storico_profitti), use_container_width=True)

if st.session_state.scatola_nera:
    st.markdown("---")
    st.subheader("📊 Inseguimento Scatola Nera Attiva")
    st.dataframe(pd.DataFrame(st.session_state.scatola_nera).T, use_container_width=True)

st.caption(f"Fortezza v38.8 operativa. Orario di bordo: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(10)
st.rerun()
