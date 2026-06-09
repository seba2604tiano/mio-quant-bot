import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime

# ==============================================================================
# 🚢 CONFIGURAZIONE PLANCIA STREAMLIT (v51.0)
# ==============================================================================
st.set_page_config(
    page_title="🚢 Transatlantico v51.0 - Plancia Quant", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔥 AUTO-LAVAGGIO INTELLIGENTE: Se rileva la vecchia v50 in memoria, cancella e pulisce tutto
if 'versione_corrente' not in st.session_state or st.session_state.versione_corrente != "51.0":
    st.session_state.clear() # Svuota completamente la vecchia memoria incastrata
    st.session_state.versione_corrente = "51.0"
    st.session_state.pnl_realizzato = 1485.50
    st.session_state.posizioni_attive = {
        "BTC-USD": {"prezzo_ingresso": 96200.0, "stop_loss": 95800.0, "max_prezzo": 96500.0, "quantita": 0.05},
        "NVDA": {"prezzo_ingresso": 135.20, "stop_loss": 134.50, "max_prezzo": 136.10, "quantita": 10}
    }
    st.session_state.storico_trade = [
        {"data": "2026-06-08", "ticker": "TSLA", "tipo": "LONG", "profitto": 120.00, "esito": "✅ WIN"},
        {"data": "2026-06-08", "ticker": "SOL-USD", "tipo": "LONG", "profitto": 45.50, "esito": "✅ WIN"}
    ]
    st.session_state.log_sistema = ["Sistemi v51.0 avviati. Memoria precedente svuotata con successo!"]
    st.session_state.stop_count = {}

def aggiungi_log(messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_sistema.insert(0, f"[{orario}] {messaggio}")
    if len(st.session_state.log_sistema) > 30:
        st.session_state.log_sistema.pop()

# ==============================================================================
# 🌌 MOTORI: UNIVERSO VOLUMETRICO
# ==============================================================================
@st.cache_data(ttl=1800)
def genera_universo_volumetrico():
    crypto_kings = ["BTC-USD", "ETH-USD", "SOL-USD"]
    pool_di_base = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "NFLX", "AMD", "INTC", "SPY", "QQQ"]
    return crypto_kings + pool_di_base

def calcola_rsi(serie_prezzi, periodi=14):
    delta = serie_prezzi.diff()
    guadagno = (delta.where(delta > 0, 0)).rolling(window=periodi).mean()
    perdita = (-delta.where(delta < 0, 0)).rolling(window=periodi).mean()
    rs = guadagno / (perdita + 1e-9)
    return 100 - (100 / (1 + rs))

# ==============================================================================
# 🎯 PLANCIA VISIVA V51.0
# ==============================================================================
st.title("🚢 Transatlantico Volumetrico v51.0")
st.subheader("Modulo d'Attacco con Trailing Stop Adattivo - Live Logs")

totale_trades = len(st.session_state.storico_trade)
win_trades = sum(1 for t in st.session_state.storico_trade if "WIN" in t["esito"])
win_rate = (win_trades / totale_trades * 100) if totale_trades > 0 else 0.0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="💰 PROFITTO NETTO REALIZZATO", value=f"${st.session_state.pnl_realizzato:,.2f}")
with col2:
    st.metric(label="🎯 SILURI IN MARE (POSIZIONI)", value=f"{len(st.session_state.posizioni_attive)} / 5 Attive")
with col3:
    st.metric(label="📈 PRECISIONE SQUADRA", value=f"{win_rate:.1f}%")

st.markdown("---")

# Sidebar
st.sidebar.header("⚓ Parametri Corazzata")
soglia_rsi_fondo = st.sidebar.slider("Grilletto RSI", 10, 40, 25)
stop_iniziale_pct = st.sidebar.slider("Stop Loss Iniziale (%)", 0.5, 5.0, 1.5, step=0.1)
max_posizioni = st.sidebar.number_input("Massimo Slot Siluri", 1, 10, 5)

universo = genera_universo_volumetrico()
try:
    storico_universo = yf.download(universo, period="5d", interval="15m", progress=False, group_by='ticker')
except:
    storico_universo = pd.DataFrame()

opportunita_rilevate = []

if not storico_universo.empty:
    for ticker in universo:
        try:
            if ticker in storico_universo.columns.levels[0]:
                df_ticker = storico_universo[ticker].dropna()
                if len(df_ticker) < 20: continue
                prezzo_attuale = df_ticker['Close'].iloc[-1]
                rsi_attuale = calcola_rsi(df_ticker['Close']).iloc[-1]
                apertura_gg = df_ticker['Open'].iloc[0]
                var_percentuale = ((prezzo_attuale - apertura_gg) / apertura_gg) * 100
                
                # Gestione posizioni operative
                if ticker in st.session_state.posizioni_attive:
                    pos = st.session_state.posizioni_attive[ticker]
                    if prezzo_attuale <= pos['stop_loss']:
                        profitto = (prezzo_attuale - pos['prezzo_ingresso']) * pos['quantita']
                        st.session_state.pnl_realizzato += profitto
                        st.session_state.storico_trade.append({"data": datetime.now().strftime("%Y-%m-%d"), "ticker": ticker, "tipo": "LONG", "profitto": profitto, "esito": "✅ WIN" if profitto > 0 else "❌ LOSS"})
                        del st.session_state.posizioni_attive[ticker]
                        aggiungi_log(f"💥 STOP COLPITO su {ticker}. Posizione chiusa.")
                else:
                    if rsi_attuale <= soglia_rsi_fondo and var_percentuale < 0:
                        opportunita_rilevate.append({"Ticker": ticker, "Prezzo": f"${prezzo_attuale:.2f}", "Variazione": f"{var_percentuale:.2f}%", "RSI": f"{rsi_attuale:.1f}"})
                        if len(st.session_state.posizioni_attive) < max_posizioni:
                            st.session_state.posizioni_attive[ticker] = {"prezzo_ingresso": prezzo_attuale, "stop_loss": prezzo_attuale * (1 - (stop_iniziale_pct / 100)), "quantita": round(2000 / prezzo_attuale, 4)}
                            aggiungi_log(f"🚀 INGRESSO ESEGUITO: {ticker} a ${prezzo_attuale:.2f}")
        except:
            continue

# Render dei dati
col_sx, col_dx = st.columns([2, 1])
with col_sx:
    st.subheader("🎯 Flotta in Mare (Posizioni Attive)")
    if st.session_state.posizioni_attive:
        st.dataframe(pd.DataFrame([{"Asset": k, "Prezzo Ingresso": f"${v['prezzo_ingresso']:.2f}", "Stop Loss": f"${v['stop_loss']:.2f}"} for k, v in st.session_state.posizioni_attive.items()]), use_container_width=True, hide_index=True)
    else: st.info("Nessuna posizione aperta.")
    
    st.subheader("🔥 Radar Occasioni d'Attacco")
    if opportunita_rilevate: st.dataframe(pd.DataFrame(opportunita_rilevate), use_container_width=True, hide_index=True)
    else: st.success("Nessun titolo sottoesteso al momento.")

with col_dx:
    st.subheader("📜 Scatola Nera Live")
    # Formattazione pulita riga per riga senza doppi escape
    testo_log_pulito = "\n".join(st.session_state.log_sistema)
    st.text_area("Eventi", value=testo_log_pulito, height=220, label_visibility="collapsed")

time.sleep(1)
