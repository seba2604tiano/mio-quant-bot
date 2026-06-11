import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import requests
from datetime import datetime, timedelta

# ==============================================================================
# 🚢 CONFIGURAZIONE PLANCIA STREAMLIT (v60.0 - Elite Quant System)
# ==============================================================================
st.set_page_config(
    page_title="🚢 Transatlantico v60.0 - Plancia Quant", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inizializzazione della memoria della nave (Session State)
if 'pnl_realizzato' not in st.session_state:
    st.session_state.pnl_realizzato = 1485.50  
if 'posizioni_attive' not in st.session_state:
    st.session_state.posizioni_attive = {
        "BTC-USD": {"prezzo_ingresso": 96200.0, "stop_loss": 95800.0, "max_prezzo": 96500.0, "quantita": 0.05, "trailing_attivo": True, "break_even_attivo": False, "orario_ingresso": datetime.now()},
        "NVDA": {"prezzo_ingresso": 135.20, "stop_loss": 134.50, "max_prezzo": 136.10, "quantita": 10, "trailing_attivo": False, "break_even_attivo": False, "orario_ingresso": datetime.now()}
    }
if 'storico_trade' not in st.session_state:
    st.session_state.storico_trade = [
        {"data": "2026-06-08", "ticker": "TSLA", "tipo": "LONG", "profitto": 120.00, "esito": "✅ WIN"},
        {"data": "2026-06-08", "ticker": "SOL-USD", "tipo": "LONG", "profitto": 45.50, "esito": "✅ WIN"},
        {"data": "2026-06-09", "ticker": "AAPL", "tipo": "LONG", "profitto": -30.00, "esito": "❌ LOSS"},
    ]
if 'log_sistema' not in st.session_state:
    st.session_state.log_sistema = ["Sistemi avviati. Sistemi di puntamento v60.0 online."]

def aggiungi_log(messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_sistema.insert(0, f"[{orario}] {messaggio}")
    if len(st.session_state.log_sistema) > 30:
        st.session_state.log_sistema.pop()

def fmt_p(val):
    """Formattazione dinamica dei prezzi per salvaguardare i decimali del Forex"""
    return f"${val:.4f}" if val < 5 else f"${val:.2f}"

# ==============================================================================
# 🌌 MOTORI: GENERAZIONE UNIVERSO GLOBAL CROSS-ASSET (45 TARGET)
# ==============================================================================
@st.cache_data(ttl=1800)
def genera_universo_volumetrico():
    crypto = [
        "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "SHIB-USD",
        "XRP-USD", "AVAX-USD", "ADA-USD", "LINK-USD", "DOT-USD",
        "LTC-USD", "UNI1-USD", "NEAR-USD", "APT1-USD", "SUI1-USD",
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
# 🛡️ CONTROMISURE ECM: RADAR TEMPORALE ESTESO PER ANALISI MATRICIALE EMA
# ==============================================================================
@st.cache_data(ttl=60)  
def scarica_dati_radar(universo_tickers):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    session = requests.Session()
    session.headers.update(headers)
    
    for tentativo in range(3):
        try:
            # Esteso a '1mo' per permettere il calcolo nativo e stabile della EMA a 100 periodi
            df = yf.download(universo_tickers, period="1mo", interval="15m", progress=False, group_by='ticker', session=session)
            if not df.empty:
                return df
        except Exception:
            time.sleep(1.5)
            continue
    return pd.DataFrame()

def calcola_rsi(serie_prezzi, periodi=14):
    delta = serie_prezzi.diff()
    guadagno = (delta.where(delta > 0, 0)).rolling(window=periodi).mean()
    perdita = (-delta.where(delta < 0, 0)).rolling(window=periodi).mean()
    rs = guadagno / (perdita + 1e-9)
    return 100 - (100 / (1 + rs))

def calcola_ema(serie_prezzi, periodi=100):
    """Calcola la media mobile esponenziale per lo Scudo di Tendenza"""
    return serie_prezzi.ewm(span=periodi, adjust=False).mean()

# ==============================================================================
# 🎯 PLANCIA SUPERIORE: SEZIONE METRICHE DI PERFORMANCE
# ==============================================================================
st.title("🚢 Transatlantico Volumetrico v60.0")
st.subheader("Centrale Quantistica Multimercato — Protezione Break-Even & Scudo EMA")

totale_trades = len(st.session_state.storico_trade)
win_trades = sum(1 for t in st.session_state.storico_trade if "WIN" in t["esito"] or "LAMPO" in t["esito"])
win_rate = (win_trades / totale_trades * 100) if totale_trades > 0 else 0.0

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #10b981;'>", unsafe_allow_html=True)
    st.metric(label="💰 PROFITTO NETTO REALIZZATO", value=f"${st.session_state.pnl_realizzato:,.2f}", delta="In Cassaforte")
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
# 🎛️ SIDEBAR PARAMETRI: DIVISIONE GRILLETTI RSI CHIRURGICI
# ==============================================================================
st.sidebar.header("⚓ Configurazione Limiti")
max_posizioni = st.sidebar.number_input("Limite Massimo Posizioni", 1, 15, 10)
st.session_state.max_pos_sidebar = max_posizioni 

st.sidebar.markdown("---")
st.sidebar.header("🎯 Grilletti RSI per Classe Asset")
rsi_crypto = st.sidebar.slider("Crypto RSI Trigger", 10, 40, 22, step=1)
rsi_nasdaq = st.sidebar.slider("Nasdaq RSI Trigger", 10, 40, 26, step=1)
rsi_commodity = st.sidebar.slider("Metalli RSI Trigger", 10, 40, 28, step=1)
rsi_forex = st.sidebar.slider("Forex RSI Trigger", 10, 40, 32, step=1)

st.sidebar.markdown("---")
st.sidebar.header("🛡️ Gestione Inseguimento & Difese")
trail_attivazione = st.sidebar.slider("Soglia Attivazione Trailing (%)", 0.05, 1.0, 0.20, step=0.05)
trail_distanza = st.sidebar.slider("Distanza Stop Trailing (%)", 0.1, 2.0, 0.30, step=0.05)
trail_passo = st.sidebar.slider("Passo Aggiornamento Trailing (%)", 0.01, 0.5, 0.05, step=0.01)

st.sidebar.markdown("---")
st.sidebar.header("⚡ Moduli d'Uscita Rapida")
tp_lampo_pct = st.sidebar.slider("Take-Profit Lampo (%)", 0.1, 2.0, 0.40, step=0.05)
time_stop_minuti = st.sidebar.slider("Time-Stop Uscita (Minuti)", 5, 120, 15, step=1)

if st.sidebar.button("🔄 Forza Scansione Universo"):
    st.cache_data.clear()
    aggiungi_log("Universo e Radar ricalcolati con i nuovi parametri chirurgici.")

# ==============================================================================
# 🛰️ RADAR & LOGICA DI TRADING AVANZATA (EMA + MULTI-RSI + BREAK-EVEN)
# ==============================================================================
st.header("🔍 Monitoraggio e Puntamento di Precisione")

with st.spinner("Scansione in corso del paniere Cross-Asset..."):
    universo = genera_universo_volumetrico()
    storico_universo = scarica_dati_radar(universo)

opportunita_rilevate = []

if not storico_universo.empty:
    for ticker in universo:
        try:
            if ticker in storico_universo.columns.levels[0]:
                df_ticker = storico_universo[ticker].dropna().copy()
                if len(df_ticker) < 105: # Garantisce dati sufficienti per calcolare EMA 100
                    continue
                
                prezzo_attuale = float(df_ticker['Close'].iloc[-1])
                df_ticker['RSI'] = calcola_rsi(df_ticker['Close'])
                rsi_attuale = float(df_ticker['RSI'].iloc[-1])
                
                # Calcolo della Media Mobile Esponenziale (Scudo EMA)
                df_ticker['EMA'] = calcola_ema(df_ticker['Close'], 100)
                ema_attuale = float(df_ticker['EMA'].iloc[-1])
                macro_trend_rialzista = prezzo_attuale > ema_attuale
                
                apertura_gg = float(df_ticker['Open'].iloc[0])
                var_percentuale = ((prezzo_attuale - apertura_gg) / apertura_gg) * 100
                
                # Smistamento e classificazione dell'asset per l'assegnazione dell'RSI corretto
                if ticker.endswith("-USD") or "1-USD" in ticker:
                    classe_asset, soglia_rsi = "Crypto", rsi_crypto
                elif ticker.endswith("=X"):
                    classe_asset, soglia_rsi = "Forex", rsi_forex
                elif ticker in ["GC=F", "SI=F", "CL=F", "GLD", "SLV"]:
                    classe_asset, soglia_rsi = "Metalli", rsi_commodity
                else:
                    classe_asset, soglia_rsi = "Nasdaq", rsi_nasdaq
                
                # --- CORE LOGIC: GESTIONE POSIZIONI ATTIVE + BREAK-EVEN ---
                if ticker in st.session_state.posizioni_attive:
                    pos = st.session_state.posizioni_attive[ticker]
                    rendimento_attuale_pct = ((prezzo_attuale - pos["prezzo_ingresso"]) / pos["prezzo_ingresso"]) * 100
                    
                    if "trailing_attivo" not in pos: pos["trailing_attivo"] = False
                    if "break_even_attivo" not in pos: pos["break_even_attivo"] = False
                    if "orario_ingresso" not in pos: pos["orario_ingresso"] = datetime.now()

                    minuti_trascorsi = (datetime.now() - pos["orario_ingresso"]).total_seconds() / 60.0

                    # 🛡️ MOSSA 3: MODULO AUTO BREAK-EVEN (Protezione Capitale)
                    if not pos["break_even_attivo"] and rendimento_attuale_pct >= (tp_lampo_pct / 2):
                        st.session_state.posizioni_attive[ticker]["stop_loss"] = pos["prezzo_ingresso"]
                        st.session_state.posizioni_attive[ticker]["break_even_attivo"] = True
                        aggiungi_log(f"🛡️ BREAK-EVEN: Blindato profitto su {ticker} (Prezzo d'ingresso bloccato).")

                    # 🚀 MODULO A: TAKE-PROFIT LAMPO
                    if rendimento_attuale_pct >= tp_lampo_pct:
                        profitto_ottenuto = (prezzo_attuale - pos["prezzo_ingresso"]) * pos["quantita"]
                        st.session_state.pnl_realizzato += profitto_ottenuto
                        st.session_state.storico_trade.append({
                            "data": datetime.now().strftime("%Y-%m-%d"), "ticker": ticker, "tipo": "LONG", "profitto": profitto_ottenuto, "esito": "⚡ WIN LAMPO"
                        })
                        del st.session_state.posizioni_attive[ticker]
                        aggiungi_log(f"⚡ TP LAMPO: Target colpito su {ticker}! +${profitto_ottenuto:.2f}")
                        continue 

                    # ⏱️ MODULO B: CRONOMETRO TIME-STOP
                    elif minuti_trascorsi >= time_stop_minuti:
                        profitto_ottenuto = (prezzo_attuale - pos["prezzo_ingresso"]) * pos["quantita"]
                        st.session_state.pnl_realizzato += profitto_ottenuto
                        st.session_state.storico_trade.append({
                            "data": datetime.now().strftime("%Y-%m-%d"), "ticker": ticker, "tipo": "LONG", "profitto": profitto_ottenuto, "esito": "⏳ TIME-OUT"
                        })
                        del st.session_state.posizioni_attive[ticker]
                        aggiungi_log(f"⏱️ TIME-STOP: Liquidato {ticker} dopo {int(minuti_trascorsi)} min. Esito: ${profitto_ottenuto:.2f}")
                        continue 

                    # MODULO C: COMPONENTE TRAILING STOP (1, 2 & 3)
                    if not pos["trailing_attivo"] and rendimento_attuale_pct >= trail_attivazione:
                        st.session_state.posizioni_attive[ticker]["trailing_attivo"] = True
                        st.session_state.posizioni_attive[ticker]["max_prezzo"] = prezzo_attuale
                        st.session_state.posizioni_attive[ticker]["stop_loss"] = prezzo_attuale * (1 - (trail_distanza / 100))
                        aggiungi_log(f"⚡ TRAILING ATTIVATO per {ticker} a +{rendimento_attuale_pct:.2f}%")
                    
                    elif pos["trailing_attivo"] and prezzo_attuale > pos["max_prezzo"]:
                        scostamento_passo_pct = ((prezzo_attuale - pos["max_prezzo"]) / pos["max_prezzo"]) * 100
                        if scostamento_passo_pct >= trail_passo:
                            st.session_state.posizioni_attive[ticker]["max_prezzo"] = prezzo_attuale
                            nuovo_stop = prezzo_attuale * (1 - (trail_distanza / 100))
                            if nuovo_stop > pos["stop_loss"]:
                                st.session_state.posizioni_attive[ticker]["stop_loss"] = nuovo_stop
                                aggiungi_log(f"🛡️ TRAILING UP: Alzato stop su {ticker} a {fmt_p(nuovo_stop)}")

                    if prezzo_attuale <= pos["stop_loss"]:
                        profitto_ottenuto = (pos["stop_loss"] - pos["prezzo_ingresso"]) * pos["quantita"]
                        st.session_state.pnl_realizzato += profitto_ottenuto
                        st.session_state.storico_trade.append({
                            "data": datetime.now().strftime("%Y-%m-%d"), "ticker": ticker, "tipo": "LONG", "profitto": profitto_ottenuto, "esito": "✅ WIN (Trail)" if profitto_ottenuto > 0 else "❌ LOSS (Stop)"
                        })
                        del st.session_state.posizioni_attive[ticker]
                        aggiungi_log(f"💥 STOP COLPITO: Chiuso {ticker}. Esito: ${profitto_ottenuto:.2f}")
                
                # --- INGRESSI CACCIA SUL FONDO CON SCHERMATURA EMA E MULTI-RSI ---
                else:
                    if rsi_attuale <= soglia_rsi and var_percentuale < 0:
                        status_trend = "RIALZISTA ✅" if macro_trend_rialzista else "RIBASSISTA ❌ (Bloccato)"
                        
                        # Mostriamo sul radar visivo l'asset, ma eseguiamo l'ordine solo se passa lo Scudo EMA
                        if macro_trend_rialzista:
                            opportunita_rilevate.append({
                                "Ticker": ticker, "Classe": classe_asset, "Prezzo": fmt_p(prezzo_attuale), "RSI": f"{rsi_attuale:.1f} (Soglia {soglia_rsi})", "Macro Trend": status_trend
                            })
                            
                            if len(st.session_state.posizioni_attive) < max_posizioni:
                                stop_iniziale = prezzo_attuale * (1 - (trail_distanza / 100))
                                st.session_state.posizioni_attive[ticker] = {
                                    "prezzo_ingresso": prezzo_attuale, "stop_loss": stop_iniziale,
                                    "max_prezzo": prezzo_attuale, "quantita": round(2000 / prezzo_attuale, 4),
                                    "trailing_attivo": False, "break_even_attivo": False, "orario_ingresso": datetime.now()  
                                }
                                aggiungi_log(f"🚀 ORDINE ESEGUITO: Acquistato {ticker} ({classe_asset}) a {fmt_p(prezzo_attuale)}. Macro trend protetto.")
        except Exception:
            continue
else:
    st.warning("⚠️ Radar disturbato da Yahoo Finance. Allineamento contromisure ECM in corso...")

# ==============================================================================
# 📟 VISUALIZZAZIONE INTERFACCIA GRAFICA DI BORDO
# ==============================================================================
col_sx, col_dx = st.columns([2, 1])

with col_sx:
    st.subheader("🎯 Posizioni Attualmente in Mare")
    if st.session_state.posizioni_attive:
        tabella_pos = []
        for tk, dati in st.session_state.posizioni_attive.items():
            t_status = "TRAILING ⚡" if dati.get("trailing_attivo", False) else ("BREAK-EVEN 🛡️" if dati.get("break_even_attivo", False) else "Iniziale ⏳")
            minuti_passati = int((datetime.now() - dati.get("orario_ingresso", datetime.now())).total_seconds() / 60)
            
            tabella_pos.append({
                "Asset": tk, "Ingresso": fmt_p(dati['prezzo_ingresso']), "Stop Loss": fmt_p(dati['stop_loss']), 
                "Max Visto": fmt_p(dati['max_prezzo']), "Stato Difese": t_status, "Tempo in Mare": f"{minuti_passati} min"
            })
        st.dataframe(pd.DataFrame(tabella_pos), width='stretch', hide_index=True)
    else:
        st.info("Nessun siluro in mare. Radar in scansione profonda.")

    st.subheader("🔥 Radar Occasioni Rilevate (Approvate da Scudo EMA)")
    if opportunita_rilevate:
        st.dataframe(pd.DataFrame(opportunita_rilevate), width='stretch', hide_index=True)
    else:
        st.success("Tutti gli asset idonei sono in acque sicure. Nessun segnale pulito filtrato dalla EMA al momento.")

with col_dx:
    st.subheader("📜 Log Scatola Nera (Live)")
    testo_log = "\n".join(st.session_state.log_sistema)
    st.text_area("Eventi del Motore", value=testo_log, height=180, label_visibility="collapsed")
    
    st.subheader("📋 Storico Ultimi Rilasci")
    df_storico = pd.DataFrame(st.session_state.storico_trade)
    if not df_storico.empty:
        st.dataframe(df_storico.tail(5), width='stretch', hide_index=True)

time.sleep(0.5)
