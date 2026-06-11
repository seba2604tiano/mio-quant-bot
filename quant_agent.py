import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import requests
from datetime import datetime, timedelta

# ==============================================================================
# 🚢 CONFIGURAZIONE PLANCIA STREAMLIT (v55.0 - Global Cross-Asset Edition)
# ==============================================================================
st.set_page_config(
    page_title="🚢 Transatlantico v55.0 - Plancia Quant", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inizializzazione della memoria della nave (Session State)
if 'pnl_realizzato' not in st.session_state:
    st.session_state.pnl_realizzato = 1485.50  
if 'posizioni_attive' not in st.session_state:
    st.session_state.posizioni_attive = {
        "BTC-USD": {"prezzo_ingresso": 96200.0, "stop_loss": 95800.0, "max_prezzo": 96500.0, "quantita": 0.05, "trailing_attivo": True, "orario_ingresso": datetime.now()},
        "NVDA": {"prezzo_ingresso": 135.20, "stop_loss": 134.50, "max_prezzo": 136.10, "quantita": 10, "trailing_attivo": False, "orario_ingresso": datetime.now()}
    }
if 'storico_trade' not in st.session_state:
    st.session_state.storico_trade = [
        {"data": "2026-06-08", "ticker": "TSLA", "tipo": "LONG", "profitto": 120.00, "esito": "✅ WIN"},
        {"data": "2026-06-08", "ticker": "SOL-USD", "tipo": "LONG", "profitto": 45.50, "esito": "✅ WIN"},
        {"data": "2026-06-09", "ticker": "AAPL", "tipo": "LONG", "profitto": -30.00, "esito": "❌ LOSS"},
    ]
if 'log_sistema' not in st.session_state:
    st.session_state.log_sistema = ["Sistemi avviati. Radar Global Cross-Asset (45 Bersagli) online."]

def aggiungi_log(messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_sistema.insert(0, f"[{orario}] {messaggio}")
    if len(st.session_state.log_sistema) > 30:
        st.session_state.log_sistema.pop()

def fmt_p(val):
    """Helper di bordo per formattare i prezzi senza perdere i pip del Forex o delle micro-crypto"""
    return f"${val:.4f}" if val < 5 else f"${val:.2f}"

# ==============================================================================
# 🌌 MOTORI: GENERAZIONE UNIVERSO GLOBAL CROSS-ASSET (45 TARGET)
# ==============================================================================
@st.cache_data(ttl=1800)
def genera_universo_volumetrico():
    """Restituisce il paniere diversificato di 45 asset per la VPS di MVPS"""
    crypto = [
        "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "SHIB-USD",
        "XRP-USD", "AVAX-USD", "ADA-USD", "LINK-USD", "DOT-USD",
        "LTC-USD", "UNI-USD", "NEAR-USD", "APT-USD", "SUI-USD",
        "FET-USD", "ICP-USD", "ATOM-USD", "ALGO-USD", "FIL-USD"
    ]
    
    nasdaq = [
        "NVDA", "TSLA", "AAPL", "AMD", "MSFT", 
        "PLTR", "AMZN", "META", "GOOGL", "NFLX", 
        "COIN", "MARA", "SMCI", "HOOD", "QCOM"
    ]
    
    commodities = [
        "GC=F", "SI=F", "CL=F", "GLD", "SLV"
    ]
    
    forex = [
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"
    ]
    
    return crypto + nasdaq + commodities + forex

# ==============================================================================
# 🛡️ CONTROMISURE ECM: DOWNLOAD CON USER-AGENT ED EVASIONE RATE LIMIT
# ==============================================================================
@st.cache_data(ttl=60)  
def scarica_dati_radar(universo_tickers):
    """Scarica i dati aggirando i blocchi IP di Yahoo Finance usando un browser fittizio e tentativi multipli"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    session = requests.Session()
    session.headers.update(headers)
    
    # Algoritmo di retry: se fallisce, aspetta e riprova fino a 3 volte
    for tentativo in range(3):
        try:
            df = yf.download(universo_tickers, period="5d", interval="15m", progress=False, group_by='ticker', session=session)
            if not df.empty:
                return df
        except Exception:
            time.sleep(1.5) # Pausa tattica prima di riprovare
            continue
            
    return pd.DataFrame()

def calcola_rsi(serie_prezzi, periodi=14):
    delta = serie_prezzi.diff()
    guadagno = (delta.where(delta > 0, 0)).rolling(window=periodi).mean()
    perdita = (-delta.where(delta < 0, 0)).rolling(window=periodi).mean()
    rs = guadagno / (perdita + 1e-9)
    return 100 - (100 / (1 + rs))

# ==============================================================================
# 🎯 PLANCIA SUPERIORE: SEZIONE METRICHE
# ==============================================================================
st.title("🚢 Transatlantico Volumetrico v55.0")
st.subheader("Plancia di Comando Quantitativa H24 — Scalping Lampo & Time-Stop Global")

totale_trades = len(st.session_state.storico_trade)
win_trades = sum(1 for t in st.session_state.storico_trade if "WIN" in t["esito"] or "LAMPO" in t["esito"])
win_rate = (win_trades / totale_trades * 100) if totale_trades > 0 else 0.0

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #10b981;'>", unsafe_allow_html=True)
    st.metric(label="💰 PROFITTO NETTO REALIZZATO", value=f"${st.session_state.pnl_realizzato:,.2f}", delta="Messo in Cassaforte")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #3b82f6;'>", unsafe_allow_html=True)
    attive = len(st.session_state.posizioni_attive)
    st.metric(label="🎯 SILURI IN MARE (POSIZIONI)", value=f"{attive} / {st.session_state.get('max_pos_sidebar', 5)} Target", delta=f"{st.session_state.get('max_pos_sidebar', 5) - attive} Slot Liberi", delta_color="inverse")
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #f59e0b;'>", unsafe_allow_html=True)
    st.metric(label="📈 PRECISIONE STRATEGIA", value=f"{win_rate:.1f}%", delta=f"Su {totale_trades} Operazioni Chiuse")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
# 🎛️ SIDEBAR PARAMETRI E TRITTICO TRAILING A VISTA
# ==============================================================================
st.sidebar.header("⚓ Parametri Ingressi")
soglia_rsi_fondo = st.sidebar.slider("Grilletto RSI (Ipervenduto)", 10, 40, 25)
max_posizioni = st.sidebar.number_input("Limite Massimo Posizioni", 1, 10, 5)
st.session_state.max_pos_sidebar = max_posizioni 

st.sidebar.markdown("---")
st.sidebar.header("🎯 Il Trio Trailing (Scalping)")
trail_attivazione = st.sidebar.slider("1. Soglia Attivazione (%)", 0.05, 1.0, 0.20, step=0.05)
trail_distanza = st.sidebar.slider("2. Distanza Stop (%)", 0.1, 2.0, 0.30, step=0.05)
trail_passo = st.sidebar.slider("3. Passo Aggiornamento (%)", 0.01, 0.5, 0.05, step=0.01)

st.sidebar.markdown("---")
st.sidebar.header("⚡ Difese Temporali")
tp_lampo_pct = st.sidebar.slider("4. Take-Profit Lampo (%)", 0.1, 2.0, 0.40, step=0.05)
time_stop_minuti = st.sidebar.slider("5. Time-Stop Uscita (Minuti)", 5, 120, 15, step=1)

if st.sidebar.button("🔄 Forza Scansione Universo"):
    st.cache_data.clear()
    aggiungi_log("Universo Cross-Asset e Radar ricalcolati da zero.")

# ==============================================================================
# 🛰️ RADAR & LOGICA DI TRADING (TRIO TRAILING + TIME-DECAY)
# ==============================================================================
st.header("🔍 Monitoraggio Mercato in Tempo Reale")

with st.spinner("Scansione radar attiva con protezione ECM..."):
    universo = genera_universo_volumetrico()
    storico_universo = scarica_dati_radar(universo)

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
                
                # --- CORE LOGIC: GESTIONE POSIZIONI ATTIVE + TIME-DECAY ---
                if ticker in st.session_state.posizioni_attive:
                    pos = st.session_state.posizioni_attive[ticker]
                    rendimento_attuale_pct = ((prezzo_attuale - pos["prezzo_ingresso"]) / pos["prezzo_ingresso"]) * 100
                    
                    if "trailing_attivo" not in pos:
                        pos["trailing_attivo"] = False
                    if "orario_ingresso" not in pos:
                        pos["orario_ingresso"] = datetime.now()

                    minuti_trascorsi = (datetime.now() - pos["orario_ingresso"]).total_seconds() / 60.0

                    # -------------------------------------------------------------
                    # 🚀 VARIANTE A: L'ARTIGLIO (Take-Profit Lampo)
                    # -------------------------------------------------------------
                    if rendimento_attuale_pct >= tp_lampo_pct:
                        profitto_ottenuto = (prezzo_attuale - pos["prezzo_ingresso"]) * pos["quantita"]
                        st.session_state.pnl_realizzato += profitto_ottenuto
                        st.session_state.storico_trade.append({
                            "data": datetime.now().strftime("%Y-%m-%d"),
                            "ticker": ticker, "tipo": "LONG", "profitto": profitto_ottenuto,
                            "esito": "⚡ WIN LAMPO"
                        })
                        del st.session_state.posizioni_attive[ticker]
                        aggiungi_log(f"⚡ TP LAMPO: Target colpito su {ticker}! Profitto: +${profitto_ottenuto:.2f}")
                        continue 

                    # -------------------------------------------------------------
                    # ⏱️ VARIANTE B: IL CRONOMETRO (Time-Stop d'emergenza)
                    # -------------------------------------------------------------
                    elif minuti_trascorsi >= time_stop_minuti:
                        profitto_ottenuto = (prezzo_attuale - pos["prezzo_ingresso"]) * pos["quantita"]
                        st.session_state.pnl_realizzato += profitto_ottenuto
                        st.session_state.storico_trade.append({
                            "data": datetime.now().strftime("%Y-%m-%d"),
                            "ticker": ticker, "tipo": "LONG", "profitto": profitto_ottenuto,
                            "esito": "⏳ TIME-OUT WIN" if profitto_ottenuto > 0 else "⏳ TIME-OUT LOSS"
                        })
                        del st.session_state.posizioni_attive[ticker]
                        aggiungi_log(f"⏱️ TIME-STOP: {ticker} in stallo da {int(minuti_trascorsi)} min. Posizione liquidata. Esito: ${profitto_ottenuto:.2f}")
                        continue 

                    # -------------------------------------------------------------
                    # Componente 1: Attivazione del Trailing
                    if not pos["trailing_attivo"] and rendimento_attuale_pct >= trail_attivazione:
                        st.session_state.posizioni_attive[ticker]["trailing_attivo"] = True
                        st.session_state.posizioni_attive[ticker]["max_prezzo"] = prezzo_attuale
                        st.session_state.posizioni_attive[ticker]["stop_loss"] = prezzo_attuale * (1 - (trail_distanza / 100))
                        aggiungi_log(f"⚡ TRAILING ATTIVATO per {ticker}: Raggiunta soglia +{rendimento_attuale_pct:.2f}%")
                    
                    # Componente 2 & 3: Inseguimento con Distanza e Passo (Step)
                    elif pos["trailing_attivo"] and prezzo_attuale > pos["max_prezzo"]:
                        scostamento_passo_pct = ((prezzo_attuale - pos["max_prezzo"]) / pos["max_prezzo"]) * 100
                        
                        if scostamento_passo_pct >= trail_passo:
                            st.session_state.posizioni_attive[ticker]["max_prezzo"] = prezzo_attuale
                            nuovo_stop = prezzo_attuale * (1 - (trail_distanza / 100))
                            if nuovo_stop > pos["stop_loss"]:
                                st.session_state.posizioni_attive[ticker]["stop_loss"] = nuovo_stop
                                aggiungi_log(f"🛡️ TRITTICO: Stop alzato su {ticker} a {fmt_p(nuovo_stop)} (Passo +{scostamento_passo_pct:.3f}% superato)")

                    # Controllo ed esecuzione Stop Loss
                    if prezzo_attuale <= pos["stop_loss"]:
                        profitto_ottenuto = (pos["stop_loss"] - pos["prezzo_ingresso"]) * pos["quantita"]
                        st.session_state.pnl_realizzato += profitto_ottenuto
                        st.session_state.storico_trade.append({
                            "data": datetime.now().strftime("%Y-%m-%d"),
                            "ticker": ticker,
                            "tipo": "LONG",
                            "profitto": profitto_ottenuto,
                            "esito": "✅ WIN (Trail)" if profitto_ottenuto > 0 else "❌ LOSS (Stop)"
                        })
                        del st.session_state.posizioni_attive[ticker]
                        aggiungi_log(f"💥 SCALPING EXIT: Stop colpito su {ticker}. Esito: ${profitto_ottenuto:.2f}")
                
                # --- INGRESSI CACCIA SUL FONDO ---
                else:
                    if rsi_attuale <= soglia_rsi_fondo and var_percentuale < 0:
                        opportunita_rilevate.append({
                            "Ticker": ticker, "Prezzo": fmt_p(prezzo_attuale),
                            "Variazione GG": f"{var_percentuale:.2f}%", "RSI attuale": f"{rsi_attuale:.1f}"
                        })
                        if len(st.session_state.posizioni_attive) < max_posizioni:
                            stop_iniziale = prezzo_attuale * (1 - (trail_distanza / 100))
                            st.session_state.posizioni_attive[ticker] = {
                                "prezzo_ingresso": prezzo_attuale, "stop_loss": stop_iniziale,
                                "max_prezzo": prezzo_attuale, "quantita": round(2000 / prezzo_attuale, 4),
                                "trailing_attivo": False,
                                "orario_ingresso": datetime.now()  
                            }
                            aggiungi_log(f"🚀 ENTRATA AUTOMATICA: {ticker} a {fmt_p(prezzo_attuale)} (RSI: {rsi_attuale:.1f})")
        except Exception:
            continue
else:
    st.warning("⚠️ Radar disturbato da Yahoo Finance. Allineamento contromisure ECM in corso, i dati verranno recuperati automaticamente al prossimo ciclo...")

# ==============================================================================
# 📟 VISUALIZZAZIONE INTERFACCIA
# ==============================================================================
col_sx, col_dx = st.columns([2, 1])

with col_sx:
    st.subheader("🎯 Posizioni Attualmente in Mare")
    if st.session_state.posizioni_attive:
        tabella_pos = []
        for tk, dati in st.session_state.posizioni_attive.items():
            t_status = "ATTIVO ⚡" if dati.get("trailing_attivo", False) else "In attesa di soglia ⏳"
            minuti_passati = int((datetime.now() - dati.get("orario_ingresso", datetime.now())).total_seconds() / 60)
            
            tabella_pos.append({
                "Asset": tk, 
                "Ingresso": fmt_p(dati['prezzo_ingresso']),
                "Stop Loss": fmt_p(dati['stop_loss']), 
                "Max Visto": fmt_p(dati['max_prezzo']),
                "Stato Trailing": t_status,
                "Tempo in Mare": f"{minuti_passati} min"
            })
        st.dataframe(pd.DataFrame(tabella_pos), width='stretch', hide_index=True)
    else:
        st.info("Nessun siluro in mare.")

    st.subheader("🔥 Radar Occasioni Rilevate (RSI sul Fondo)")
    if opportunita_rilevate:
        st.dataframe(pd.DataFrame(opportunita_rilevate), width='stretch', hide_index=True)
    else:
        st.success("Nessun asset sottoesteso trovato al momento.")

with col_dx:
    st.subheader("📜 Log Scatola Nera (Live)")
    testo_log = "\n".join(st.session_state.log_sistema)
    st.text_area("Eventi del Motore", value=testo_log, height=180, label_visibility="collapsed")
    
    st.subheader("📋 Storico Ultimi Rilasci")
    df_storico = pd.DataFrame(st.session_state.storico_trade)
    if not df_storico.empty:
        st.dataframe(df_storico.tail(5), width='stretch', hide_index=True)

time.sleep(0.5)
