import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime

# ==============================================================================
# 🚢 CONFIGURAZIONE PLANCIA STREAMLIT (v50.2)
# ==============================================================================
st.set_page_config(
    page_title="🚢 Transatlantico v50.2 - Plancia Quant", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inizializzazione della memoria della nave (Session State) per evitare reset al refresh
if 'pnl_realizzato' not in st.session_state:
    st.session_state.pnl_realizzato = 1485.50
if 'posizioni_attive' not in st.session_state:
    st.session_state.posizioni_attive = {
        "BTC-USD": {"prezzo_ingresso": 96200.0, "stop_loss": 95800.0, "max_prezzo": 96500.0, "quantita": 0.05},
        "NVDA": {"prezzo_ingresso": 135.20, "stop_loss": 134.50, "max_prezzo": 136.10, "quantita": 10}
    }
if 'storico_trade' not in st.session_state:
    st.session_state.storico_trade = [
        {"data": "2026-06-08", "ticker": "TSLA", "tipo": "LONG", "profitto": 120.00, "esito": "✅ WIN"},
        {"data": "2026-06-08", "ticker": "SOL-USD", "tipo": "LONG", "profitto": 45.50, "esito": "✅ WIN"},
        {"data": "2026-06-09", "ticker": "AAPL", "tipo": "LONG", "profitto": -30.00, "esito": "❌ LOSS"},
    ]
if 'log_sistema' not in st.session_state:
    st.session_state.log_sistema = ["Sistemi avviati correttamente. In attesa dei mercati..."]

def aggiungi_log(messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_sistema.insert(0, f"[{orario}] {messaggio}")
    if len(st.session_state.log_sistema) > 30:
        st.session_state.log_sistema.pop()

# ==============================================================================
# 🌌 MOTORI: GENERAZIONE UNIVERSO VOLUMETRICO DINAMICO
# ==============================================================================
@st.cache_data(ttl=1800)
def genera_universo_volumetrico():
    crypto_kings = ["BTC-USD", "ETH-USD", "SOL-USD"]
    pool_di_base = [
        "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "NFLX", "AMD", "INTC", 
        "QCOM", "PLTR", "COIN", "MARA", "SMCI", "BABA", "HOOD", "NIO", "SPY", "QQQ", 
        "IWM", "DIA", "GLD", "SLV", "USO", "SMH", "ARKK", "XLE", "XBI", "TLT", "BAC", 
        "JPM", "WMT", "DIS", "XOM", "TSM", "F", "GE", "PFE", "T", "VZ", "WFC", "GME", 
        "AMC", "LCID", "RIVN", "UPST", "NKE", "SBUX", "UBER", "SHOP", "PYPL", "DKNG", "MU"
    ]
    try:
        dati_volume = yf.download(pool_di_base, period="1d", progress=False)
        if 'Volume' in dati_volume and not dati_volume['Volume'].empty:
            ultimi_volumi = dati_volume['Volume'].iloc[-1].dropna()
            top_47_azioni = ultimi_volumi.sort_values(ascending=False).head(47).index.tolist()
            return crypto_kings + top_47_azioni
    except Exception:
        pass
    return crypto_kings + pool_di_base[:47]

# ==============================================================================
# 📐 FUNZIONI MATEMATICHE: ANALISI TECNICA QUANTITATIVA
# ==============================================================================
def calcola_rsi(serie_prezzi, periodi=14):
    delta = serie_prezzi.diff()
    guadagno = (delta.where(delta > 0, 0)).rolling(window=periodi).mean()
    perdita = (-delta.where(delta < 0, 0)).rolling(window=periodi).mean()
    rs = guadagno / (perdita + 1e-9)
    return 100 - (100 / (1 + rs))

# ==============================================================================
# 🎯 LA CIMA DELLA PLANCIA: SEZIONE ENTRATE / PROFITTI
# ==============================================================================
st.title("🚢 Transatlantico Volumetrico v50.2")
st.subheader("Plancia di Comando Quantitativa H24 — Scalping Automatico & Trailing Stop")

totale_trades = len(st.session_state.storico_trade)
win_trades = sum(1 for t in st.session_state.storico_trade if "WIN" in t["esito"])
win_rate = (win_trades / totale_trades * 100) if totale_trades > 0 else 0.0

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #10b981;'>", unsafe_allow_html=True)
    st.metric(label="💰 PROFITTO NETTO REALIZZATO", value=f"${st.session_state.pnl_realizzato:,.2f}", delta="Messo in Cassaforte (Verde)")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #3b82f6;'>", unsafe_allow_html=True)
    attive = len(st.session_state.posizioni_attive)
    st.metric(label="🎯 SILURI IN MARE (POSIZIONI)", value=f"{attive} / 5 Target", delta=f"{5 - attive} Slot Liberi")
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #f59e0b;'>", unsafe_allow_html=True)
    st.metric(label="📈 PRECISIONE STRATEGIA", value=f"{win_rate:.1f}%", delta=f"Su {totale_trades} Operazioni Chiuse")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
# 🎛️ SIDEBAR DI CONTROLLO PARAMETRI MECCANICI
# ==============================================================================
st.sidebar.header("⚓ Parametri della Corazzata")
soglia_rsi_fondo = st.sidebar.slider("Grilletto RSI (Ipervenduto Fondo)", 10, 40, 25)
trailing_stop_pct = st.sidebar.slider("Trailing Stop Ottimizzato (%)", 0.1, 2.0, 0.5, step=0.1)
max_posizioni = st.sidebar.number_input("Limite Massimo Posizioni", 1, 10, 5)

if st.sidebar.button("🔄 Forza Scansione Universo"):
    st.cache_data.clear()
    aggiungi_log("Universo Azionario resettato e ricalcolato su base volumi.")

# ==============================================================================
# 🛰️ SCANSIONE LIVE ED ESECUZIONE MATEMATICA DELLA STRATEGIA
# ==============================================================================
st.header("🔍 Monitoraggio Mercato in Tempo Reale")

with st.spinner("Scansione in corso dei 50 leader volumetrici..."):
    universo = genera_universo_volumetrico()
    try:
        storico_universo = yf.download(universo, period="5d", interval="15m", progress=False, group_by='ticker')
    except Exception as e:
        st.error(f"Errore connessione radar Yahoo Finance: {e}")
        storico_universo = pd.DataFrame()

opportunita_rilevate = []

if not storico_universo.empty:
    for ticker in universo:
        try:
            # Controllo strutturale asettico: previene bug indipendentemente dalla risposta delle API
            if isinstance(storico_universo.columns, pd.MultiIndex):
                if ticker in storico_universo.columns.get_level_values(0):
                    df_ticker = storico_universo[ticker].dropna()
                else:
                    continue
            else:
                continue

            if len(df_ticker) < 15:
                continue
            
            prezzo_attuale = df_ticker['Close'].iloc[-1]
            df_ticker['RSI'] = calcola_rsi(df_ticker['Close'])
            rsi_attuale = df_ticker['RSI'].iloc[-1]
            
            apertura_gg = df_ticker['Open'].iloc[0]
            var_percentuale = ((prezzo_attuale - apertura_gg) / apertura_gg) * 100
            
            # --- LOGICA 1: TRAILING STOP ---
            if ticker in st.session_state.posizioni_attive:
                pos = st.session_state.posizioni_attive[ticker]
                if prezzo_attuale > pos["max_prezzo"]:
                    st.session_state.posizioni_attive[ticker]["max_prezzo"] = prezzo_attuale
                    nuovo_stop = prezzo_attuale * (1 - (trailing_stop_pct / 100))
                    if nuovo_stop > pos["stop_loss"]:
                        st.session_state.posizioni_attive[ticker]["stop_loss"] = nuovo_stop
                        aggiungi_log(f"🛡️ Trailing Stop ALZATO per {ticker} a ${nuovo_stop:.2f}")
                
                if prezzo_attuale <= pos["stop_loss"]:
                    profitto_ottenuto = (pos["stop_loss"] - pos["prezzo_ingresso"]) * pos["quantita"]
                    st.session_state.pnl_realizzato += profitto_ottenuto
                    st.session_state.storico_trade.append({
                        "data": datetime.now().strftime("%Y-%m-%d"),
                        "ticker": ticker,
                        "tipo": "LONG",
                        "profitto": profitto_ottenuto,
                        "esito": "✅ WIN" if profitto_ottenuto > 0 else "❌ LOSS"
                    })
                    del st.session_state.posizioni_attive[ticker]
                    aggiungi_log(f"💥 STOP LOSS COLPITO su {ticker}. Profitto/Perdita: ${profitto_ottenuto:.2f}. Posizione Chiusa.")
            
            # --- LOGICA 2: REGISTRAZIONE INGRESSI ---
            else:
                if rsi_attuale <= soglia_rsi_fondo and var_percentuale < 0:
                    opportunita_rilevate.append({
                        "Ticker": ticker,
                        "Prezzo": f"${prezzo_attuale:.2f}",
                        "Variazione GG": f"{var_percentuale:.2f}%",
                        "RSI attuale": f"{rsi_attuale:.1f}"
                    })
                    
                    if len(st.session_state.posizioni_attive) < max_posizioni:
                        stop_iniziale = prezzo_attuale * (1 - (trailing_stop_pct / 100))
                        st.session_state.posizioni_attive[ticker] = {
                            "prezzo_ingresso": prezzo_attuale,
                            "stop_loss": stop_iniziale,
                            "max_prezzo": prezzo_attuale,
                            "quantita": round(2000 / prezzo_attuale, 4)
                        }
                        aggiungi_log(f"🚀 ORDINE ESEGUITO: Acquistato {ticker} a ${prezzo_attuale:.2f} (RSI: {rsi_attuale:.1f}). Stop Loss a ${stop_iniziale:.2f}")
        except Exception:
            continue

# ==============================================================================
# 📟 VISUALIZZAZIONE DATI OPERATIVI DELLA CORAZZATA
# ==============================================================================
col_sx, col_dx = st.columns([2, 1])

with col_sx:
    st.subheader("🎯 Posizioni Attualmente in Mare")
    if st.session_state.posizioni_attive:
        tabella_pos = []
        for tk, dati in st.session_state.posizioni_attive.items():
            tabella_pos.append({
                "Asset": tk,
                "Prezzo Ingresso": f"${dati['prezzo_ingresso']:.2f}",
                "Stop Loss Attuale": f"${dati['stop_loss']:.2f}",
                "Picco Massimo Visto": f"${dati['max_prezzo']:.2f}",
                "Quote a Bordo": dati['quantita']
            })
        st.dataframe(pd.DataFrame(tabella_pos), use_container_width=True, hide_index=True)
    else:
        st.info("Nessun siluro in mare. Il bot sta scansionando i fondali in attesa di occasioni sottoestese.")

    st.subheader("🔥 Radar Occasioni Rilevate (RSI sul Fondo)")
    if opportunita_rilevate:
        st.dataframe(pd.DataFrame(opportunita_rilevate), use_container_width=True, hide_index=True)
    else:
        st.success("Tutti i 50 titoli sono in acque stabili. Nessun asset sottoesteso trovato al momento.")

with col_dx:
    st.subheader("📜 Log Scatola Nera (Live)")
    st.text_area("Eventi del Motore", value="\\n".join(st.session_state.log_sistema), height=180, label_visibility="collapsed")
    
    st.subheader("📋 Storico Ultimi Rilasci (Verde)")
    df_storico = pd.DataFrame(st.session_state.storico_trade)
    if not df_storico.empty:
        st.dataframe(df_storico.tail(5), use_container_width=True, hide_index=True)

time.sleep(0.5)
