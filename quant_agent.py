import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime

# Configurazione iniziale della pagina
st.set_page_config(page_title="Quant Agent Ultimate v38.7", layout="wide")

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
trailing_activation = st.sidebar.slider("Attivazione Trailing Stop (%)", min_value=1.0, max_value=20.0, value=4.0, step=0.5)
trailing_distance = st.sidebar.slider("Distanza dallo Stop (% dal massimo)", min_value=0.5, max_value=5.0, value=1.5, step=0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("🏹 Strategia d'Ingresso")
tipo_strategia = st.sidebar.selectbox("Condizione d'Acquisto", ["Ipervenduto Classico (RSI < 35)", "Inseguimento FOMO (RSI > 65)"])

st.sidebar.markdown("---")
attiva_capitale = st.sidebar.checkbox("🚀 Attiva Trading Automatico", value=False)

if attiva_capitale:
    st.sidebar.warning("⚠️ RETE COINVOLTA: Algoritmo di scansione in funzione.")

# Asset certificati Alpaca
EQUIPAGGIO = {
    "👑 I Re del Mercato": ["BTC/USD", "ETH/USD", "SOL/USD"],
    "⚡ I Pilastri Altcoin": ["AVAX/USD", "LINK/USD", "DOT/USD", "LTC/USD", "XRP/USD", "BCH/USD"],
    "🌶️ Battaglione Meme (Botti Notturni)": ["DOGE/USD", "SHIB/USD", "PEPE/USD", "WIF/USD", "BONK/USD"],
    "🔮 DeFi & Web3 Leader": ["UNI/USD", "AAVE/USD", "GRT/USD", "LDO/USD"]
}

tutti_i_soldati = [coin for cat in EQUIPAGGIO.values() for coin in cat]

# Inizializzazione sessioni persistenti
if "scatola_nera" not in st.session_state: st.session_state.scatola_nera = {}
if "storico_profitti" not in st.session_state: st.session_state.storico_profitti = []
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
            # Salva quantità esatta e quantità liquida per evitare frazioni bloccate
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
    payload = {
        "symbol": simbolo.replace("/", ""),
        "side": lato,
        "type": "market",
        "time_in_force": "gtc"
    }
    if is_qty:
        payload["qty"] = str(quantita_o_dollari)  # Per vendite millesimali chirurgiche
    else:
        payload["notional"] = str(quantita_o_dollari) # Per acquisti in dollari
        
    try:
        res = requests.post(url_ordine, json=payload, headers=headers)
        return res.status_code == 200 or res.status_code == 201
    except: return False

def panic_button_vendi_tutto(posizioni_reali, key, secret):
    st.toast("🚨 PANIC BUTTON ATTIVATO! Evacuazione totale...", icon="⚠️")
    for simbolo_clean, dati in posizioni_reali.items():
        invia_ordine_market(simbolo_clean, "sell", dati["qty"], True, key, secret)
    st.session_state.scatola_nera = {}
    st.toast("🔥 Portafoglio completamente azzerato e convertito in Cash!", icon="💰")
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
                    if condizione and not ha_posizione_reale:
                        if invia_ordine_market(simbolo, "buy", size_dollari, False, key, secret):
                            st.session_state.scatola_nera[simbolo] = {"prezzo_acquisto": ultimo_prezzo, "prezzo_massimo": ultimo_prezzo}
                            st.toast(f"🛒 Entrato su {simbolo}", icon="🟢")
                    
                    if ha_posizione_reale:
                        if simbolo not in st.session_state.scatola_nera:
                            st.session_state.scatola_nera[simbolo] = {"prezzo_acquisto": ultimo_prezzo, "prezzo_massimo": ultimo_prezzo}
                        dati_pos = st.session_state.scatola_nera[simbolo]
                        if ultimo_prezzo > dati_pos["prezzo_massimo"]:
                            st.session_state.scatola_nera[simbolo]["prezzo_massimo"] = ultimo_prezzo
                            dati_pos["prezzo_massimo"] = ultimo_prezzo
                        
                        guadagno_pct = ((ultimo_prezzo - dati_pos["prezzo_acquisto"]) / dati_pos["prezzo_acquisto"]) * 100
                        discesa_dal_massimo = ((dati_pos["prezzo_massimo"] - ultimo_prezzo) / dati_pos["prezzo_massimo"]) * 100
                        stato = f"📦 {round(guadagno_pct, 2)}%"
                        
                        # SCATTO CHIRURGICO: Vendiamo la quantità precisa presente nel portafoglio Alpaca
                        if guadagno_pct >= trailing_activation and discesa_dal_massimo >= trailing_distance:
                            qty_esatta = posizioni_reali.get(simbolo_clean, posizioni_reali.get(simbolo))["qty"]
                            if invia_ordine_market(simbolo, "sell", qty_esatta, True, key, secret):
                                st.session_state.storico_profitti.append({
                                    "Ora": datetime.now().strftime('%H:%M:%S'), "Asset": simbolo,
                                    "Perf %": f"+{round(guadagno_pct, 2)}%", "Gain ($)": round((size_dollari * (guadagno_pct / 100)), 2)
                                })
                                del st.session_state.scatola_nera[simbolo]
                                stato = "💥 Chiuso!"
                                st.toast(f"💰 Preso profitto su {simbolo}!", icon="🔥")
                elif ha_posizione_reale: stato = "📦 In Posizione"
                return {"Prezzo ($)": ultimo_prezzo, "RSI": rsi_attuale, "Stato": stato}
        return {"Prezzo ($)": "Errore", "RSI": "--", "Stato": "Ricerca"}
    except: return {"Prezzo ($)": "Errore", "RSI": "--", "Stato": "Rete"}

# --- GRAFICA TERMINALE OPERATIVO ---
st.markdown("## 🛰️ Quant Agent Ultimate Terminal v38.7 — SANDBOX TEST")

# Sidebar Protocolli
st.sidebar.markdown("---")
st.sidebar.subheader("🚨 Protocollo Difesa")
if st.sidebar.button("💥 PANIC BUTTON: VENDI TUTTO"):
    pos_attuali_pulsante = ottieni_posizioni_reali(alpaca_key, alpaca_secret)
    panic_button_vendi_tutto(pos_attuali_pulsante, alpaca_key, alpaca_secret)

# MANOVRALITÀ DI RESET RAPIDO SENZA FARE IL BOOT
if st.sidebar.button("🔄 Reset Dati Sessione"):
    st.session_state.scatola_nera = {}
    st.session_state.storico_profitti = []
    st.toast("Tabula Rasa effettuata con successo!", icon="🧼")
    time.sleep(0.5)
    st.rerun()

if st.session_state.errori_consecutivi >= 3:
    st.session_state.errori_consecutivi = 0
    st.rerun()

info_conto = ottieni_bilancio_conto(alpaca_key, alpaca_secret)
pos_reali = ottieni_posizioni_reali(alpaca_key, alpaca_secret)
totale_guadagnato = sum([t["Gain ($)"] for t in st.session_state.storico_profitti])

c1, c2, c3 = st.columns(3)
with c1: st.metric("💰 Cash Disponibile", f"$ {info_conto['cash']}")
with c2: st.metric("🛡️ Capitale Corazzata", f"$ {info_conto['portfolio_value']}")
with c3: st.metric("💵 CASSA PROFITTI SESSIONE", f"$ {round(totale_guadagnato, 2)}", delta="Simulatore Sandbox")

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

# --- PANEL DI STRESS-TEST MANUALE INTERATTIVO ---
st.markdown("---")
st.subheader("🛠️ Console di Controllo Manuale (Stress-Test Sandbox)")
col_test1, col_test2 = st.columns(2)

with col_test1:
    token_scelto = st.selectbox("Seleziona Asset da Forzare", tutti_i_soldati)
    if st.button("🛒 FORZA ACQUISTO MANUALE (Test)"):
        if invia_ordine_market(token_scelto, "buy", size_dollari, False, alpaca_key, alpaca_secret):
            st.success(f"Comando eseguito! Inviato ordine d'acquisto per {token_scelto}.")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Errore nell'invio del comando ad Alpaca. Controlla le chiavi.")

with col_test2:
    st.info("💡 **Come testare il Trailing Stop stasera:**\n\n1. Seleziona una moneta (es. SOL/USD) e clicca sul pulsante di acquisto forzato.\n2. La vedrai apparire istantaneamente nel portafoglio di Alpaca e nella tabella d'Inseguimento qui sotto.\n3. Guarda come la Scatola Nera memorizza il prezzo d'ingresso e comincia a rincorrere i picchi!")

if st.session_state.storico_profitti:
    st.markdown("---")
    st.subheader("💰 Registro dei Bottini di Guerra (Trade Chiusi)")
    st.dataframe(pd.DataFrame(st.session_state.storico_profitti), use_container_width=True)

if st.session_state.scatola_nera:
    st.markdown("---")
    st.subheader("📊 Inseguimento Scatola Nera Attiva")
    st.dataframe(pd.DataFrame(st.session_state.scatola_nera).T, use_container_width=True)

st.caption(f"Terminale operativo pronto. Orario di bordo: {datetime.now().strftime('%H:%M:%S')}")
time.sleep(10)
st.rerun()
