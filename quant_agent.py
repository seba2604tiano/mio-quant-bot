import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime

# ==============================================================================
# 🚢 CONFIGURAZIONE PLANCIA STREAMLIT (v55.0)
# ==============================================================================
st.set_page_config(
    page_title="🚢 Transatlantico v55.0 - Quadrante Crypto", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inizializzazione della memoria di bordo (Session State)
if "pnl_realizzato" not in st.session_state:
    st.session_state.pnl_realizzato = 1485.50
if "posizioni_attive" not in st.session_state:
    st.session_state.posizioni_attive = {
        "BTC-USD": {"prezzo_ingresso": 96200.0, "stop_loss": 95800.0, "max_prezzo": 96500.0, "quantita": 0.05},
        "SOL-USD": {"prezzo_ingresso": 165.20, "stop_loss": 164.50, "max_prezzo": 166.10, "quantita": 12.0}
    }
if "storico_trade" not in st.session_state:
    st.session_state.storico_trade = [
        {"data": "2026-06-08", "ticker": "DOGE-USD", "tipo": "LONG", "profitto": 120.00, "esito": "✅ WIN"},
        {"data": "2026-06-09", "ticker": "XRP-USD", "tipo": "LONG", "profitto": -30.00, "esito": "❌ LOSS"},
    ]
if "log_sistema" not in st.session_state:
    st.session_state.log_sistema = ["Motori v55.0 avviati. Quadrante a 20 Crypto attivo H24."]

def aggiungi_log(messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_sistema.insert(0, f"[{orario}] {messaggio}")
    if len(st.session_state.log_sistema) > 30:
        st.session_state.log_sistema.pop()

# ==============================================================================
# 🌌 IL QUADRANTE DELLE 20 REGINE CRYPTO
# ==============================================================================
def genera_universo_volumetrico():
    # Selezione bilanciata delle 20 crypto più liquide e volatili supportate da yfinance
    return [
        "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "SHIB-USD",
        "XRP-USD", "AVAX-USD", "ADA-USD", "LINK-USD", "DOT-USD",
        "LTC-USD", "UNI-USD", "NEAR-USD", "APT-USD", "SUI-USD",
        "FET-USD", "ICP-USD", "ATOM-USD", "ALGO-USD", "FIL-USD"
    ]

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
# 🎯 LA CIMA DELLA PLANCIA: PERFORMANCE IN DIRETTA
# ==============================================================================
st.title("🚢 Transatlantico Volumetrico v55.0")
st.subheader("Centrale Operativa IA — 20 Asset Crypto H24 — Trailing & Scalping")

totale_trades = len(st.session_state.storico_trade)
win_trades = sum(1 for t in st.session_state.storico_trade if "WIN" in t["esito"])
win_rate = (win_trades / totale_trades * 100) if totale_trades > 0 else 0.0

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #10b981;'>", unsafe_allow_html=True)
    st.metric(label="💰 PROFITTO NETTO REALIZZATO", value=f"${st.session_state.pnl_realizzato:,.2f}", delta="In Cassaforte")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #3b82f6;'>", unsafe_allow_html=True)
    attive = len(st.session_state.posizioni_attive)
    st.metric(label="🎯 SILURI IN MARE", value=f"{attive} Posizioni", delta=f"Slot Liberi")
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #f59e0b;'>", unsafe_allow_html=True)
    st.metric(label="📈 PRECISIONE STRATEGIA", value=f"{win_rate:.1f}%", delta=f"Su {totale_trades} Chiusure")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
# 🎛️ SIDEBAR DI CONTROLLO MECCANICO
# ==============================================================================
st.sidebar.header("⚓ Parametri Meccanici v55.0")
soglia_rsi_fondo = st.sidebar.slider("Grilletto RSI (Ipervenduto)", 10, 50, 25)
trailing_stop_pct = st.sidebar.slider("Trailing Stop Ottimizzato (%)", 0.1, 2.0, 0.5, step=0.1)
max_posizioni = st.sidebar.number_input("Limite Massimo Posizioni", 1, 15, 4)

if st.sidebar.button("🔄 Forza Ricalcolo Radar"):
    st.cache_data.clear()
    aggiungi_log("Radar e cache resettati. Scansione manuale della flotta.")

# ==============================================================================
# 🛰️ SCANSIONE BULK ED ESECUZIONE DEL TRITTICO DI TRAILING
# ==============================================================================
st.header("🔍 Monitoraggio Mercato in Tempo Reale")

with st.spinner("Scansione in corso delle 20 regine crypto..."):
    universo = genera_universo_volumetrico()
    try:
        # Bulk download pulito e leggero per aggirare i rate-limit
        storico_universo = yf.download(universo, period="2d", interval="1m", progress=False, group_by='ticker')
    except Exception as e:
        st.error(f"Errore connessione radar Yahoo Finance: {e}")
        storico_universo = pd.DataFrame()

opportunita_rilevate = []

if not storico_universo.empty:
    for ticker in universo:
        try:
            if ticker in storico_universo.columns.levels[0]:
                df_ticker = storico_universo[ticker].dropna()
                if len(df_ticker) < 15:
                    continue
                
                prezzo_attuale = float(df_ticker['Close'].iloc[-1])
                df_ticker['RSI'] = calcola_rsi(df_ticker['Close'])
                rsi_attuale = float(df_ticker['RSI'].iloc[-1])
                
                apertura_gg = float(df_ticker['Open'].iloc[0])
                var_percentuale = ((prezzo_attuale - apertura_gg) / apertura_gg) * 100
                
                # --- GESTIONE TRAILING POSIZIONI APERTE ---
                if ticker in st.session_state.posizioni_attive:
                    pos = st.session_state.posizioni_attive[ticker]
                    if prezzo_attuale > pos["max_prezzo"]:
                        st.session_state.posizioni_attive[ticker]["max_prezzo"] = prezzo_attuale
                        nuovo_stop = prezzo_attuale * (1 - (trailing_stop_pct / 100))
                        if nuovo_stop > pos["stop_loss"]:
                            st.session_state.posizioni_attive[ticker]["stop_loss"] = nuovo_stop
                            aggiungi_log(f"🛡️ Trailing Stop ALZATO per {ticker} a ${nuovo_stop:.4f if prezzo_attuale < 1 else '.2f'}")
                    
                    if prezzo_attuale <= pos["stop_loss"]:
                        profitto_ottenuto = (pos["stop_loss"] - pos["prezzo_ingresso"]) * pos["quantita"]
                        st.session_state.pnl_realizzato += profitto_ottenuto
                        st.session_state.storico_trade.append({
                            "data": datetime.now().strftime("%Y-%m-%d"),
                            "ticker": ticker, "tipo": "LONG", "profitto": profitto_ottenuto,
                            "esito": "✅ WIN" if profitto_ottenuto > 0 else "❌ LOSS"
                        })
                        del st.session_state.posizioni_attive[ticker]
                        aggiungi_log(f"💥 STOP COLPITO su {ticker}. Risultato: ${profitto_ottenuto:.2f}")
                
                # --- RILEVAMENTO NUOVI INGRESSI ---
                else:
                    if rsi_attuale <= soglia_rsi_fondo and var_percentuale < 0:
                        opportunita_rilevate.append({
                            "Ticker": ticker, "Prezzo": f"${prezzo_attuale:.4f if prezzo_attuale < 1 else '.2f'}",
                            "Variazione GG": f"{var_percentuale:.2f}%", "RSI attuale": f"{rsi_attuale:.1f}"
                        })
                        
                        if len(st.session_state.posizioni_attive) < max_posizioni:
                            stop_iniziale = prezzo_attuale * (1 - (trailing_stop_pct / 100))
                            st.session_state.posizioni_attive[ticker] = {
                                "prezzo_ingresso": prezzo_attuale, "stop_loss": stop_iniziale,
                                "max_prezzo": prezzo_attuale, "quantita": round(2000 / prezzo_attuale, 4)
                            }
                            aggiungi_log(f"🚀 ORDINE ESEGUITO: Acquistato {ticker} a ${prezzo_attuale:.4f if prezzo_attuale < 1 else '.2f'} (RSI: {rsi_attuale:.1f})")
        except Exception:
            continue

# ==============================================================================
# 📟 VISUALIZZAZIONE DATI OPERATIVI
# ==============================================================================
col_sx, col_dx = st.columns([2, 1])

with col_sx:
    st.subheader("🎯 Posizioni Attualmente in Mare")
    if st.session_state.posizioni_attive:
        tabella_pos = []
        for tk, dati in st.session_state.posizioni_attive.items():
            tabella_pos.append({
                "Asset": tk,
                "Prezzo Ingresso": f"${dati['prezzo_ingresso']:.4f if dati['prezzo_ingresso'] < 1 else '.2f'}",
                "Stop Loss Attuale": f"${dati['stop_loss']:.4f if dati['stop_loss'] < 1 else '.2f'}",
                "Picco Massimo Visto": f"${dati['max_prezzo']:.4f if dati['max_prezzo'] < 1 else '.2f'}",
                "Quote a Bordo": dati['quantita']
            })
        st.dataframe(pd.DataFrame(tabella_pos), use_container_width=True, hide_index=True)
    else:
        st.info("Nessun siluro in mare. Radar attivo nei fondali Crypto.")

    st.subheader("🔥 Radar Occasioni Rilevate (RSI sul Fondo)")
    if opportunita_rilevate:
        st.dataframe(pd.DataFrame(opportunita_rilevate), use_container_width=True, hide_index=True)
    else:
        st.success("Tutti i 20 asset viaggiano in acque stabili. Nessun segnale di ipervenduto.")

with col_dx:
    st.subheader("📜 Log Scatola Nera v55.0")
    st.text_area("Eventi", value="\\n".join(st.session_state.log_sistema), height=180, label_visibility="collapsed")
    
    st.subheader("📋 Ultimi Rilasci Chiusi")
    df_storico = pd.DataFrame(st.session_state.storico_trade)
    if not df_storico.empty:
        st.dataframe(df_storico.tail(5), use_container_width=True, hide_index=True)

time.sleep(0.5)
