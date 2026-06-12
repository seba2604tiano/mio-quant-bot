import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import json
import os
import requests
from datetime import datetime

# ==============================================================================
# 🚢 CONFIGURAZIONE PLANCIA STREAMLIT (v64.0 - CASH 500$ + BLITZ MODE)
# ==============================================================================
st.set_page_config(
    page_title="🚢 Transatlantico v64.0 - Blitz Mode", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Parametri di gestione capitale reale
BUDGET_TOTALE = 500.0

# ==============================================================================
# 💾 PERSISTENZA DATI SU FILE (Salvataggio permanente tra sessioni)
# ==============================================================================
SAVE_FILE = "transatlantico_stato.json"

def salva_stato():
    """Salva PnL e storico trade su file JSON per persistenza permanente."""
    try:
        stato = {
            "pnl_realizzato": st.session_state.pnl_realizzato,
            "storico_trade": st.session_state.storico_trade,
        }
        with open(SAVE_FILE, "w") as f:
            json.dump(stato, f, indent=2)
    except Exception as e:
        aggiungi_log(f"⚠️ Errore salvataggio stato: {e}")

def carica_stato():
    """Carica PnL e storico trade da file se presente sullo scafo."""
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

# Inizializzazione della memoria della nave (Session State)
stato_caricato = carica_stato()

if 'pnl_realizzato' not in st.session_state:
    st.session_state.pnl_realizzato = stato_caricato["pnl_realizzato"] if stato_caricato else 1485.50

if 'posizioni_attive' not in st.session_state:
    st.session_state.posizioni_attive = {}

if 'storico_trade' not in st.session_state:
    st.session_state.storico_trade = stato_caricato["storico_trade"] if stato_caricato else []

if 'log_sistema' not in st.session_state:
    st.session_state.log_sistema = ["[BOOT] Sistemi online. v64.0 - Modulo Scalping Blitz configurato su budget 500$."]

def aggiungi_log(messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_sistema.insert(0, f"[{orario}] {messaggio}")
    if len(st.session_state.log_sistema) > 30:
        st.session_state.log_sistema.pop()

def fmt_p(val):
    """Formattazione dei decimali protetta per il Forex."""
    return f"${val:.4f}" if val < 5 else f"${val:.2f}"

def get_orario_ingresso(pos):
    """Converte in modo sicuro la stringa ISO dell'orario in datetime."""
    oi = pos.get("orario_ingresso", datetime.now().isoformat())
    if isinstance(oi, datetime):
        return oi
    try:
        return datetime.fromisoformat(oi)
    except Exception:
        return datetime.now()

# ==============================================================================
# 🌌 MOTORI: GENERAZIONE UNIVERSO GLOBAL CROSS-ASSET (45 TARGET)
# ==============================================================================
@st.cache_data(ttl=1800)
def genera_universo_volumetrico():
    crypto = [
        "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "XRP-USD", 
        "AVAX-USD", "ADA-USD", "LINK-USD", "DOT-USD", "LTC-USD", 
        "NEAR-USD", "FET-USD", "ICP-USD", "ATOM-USD", "ALGO-USD", "FIL-USD"
    ]
    nasdaq = [
        "NVDA", "TSLA", "AAPL", "AMD", "MSFT", "PLTR", "AMZN", 
        "META", "GOOGL", "NFLX", "COIN", "MARA", "SMCI", "HOOD", "QCOM"
    ]
    commodities = [
        "GC=F", "SI=F", "CL=F", "GLD", "SLV"
    ]
    forex = [
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"
    ]
    return crypto + nasdaq + commodities + forex

# ==============================================================================
# 🛡️ RADAR TEMPORALE: DOWNLOAD E CALCOLO STRATEGIA QUANTITATIVA
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
            df = yf.download(
                universo_tickers, period="1mo", interval="15m",
                progress=False, group_by='ticker', session=session
            )
            if not df.empty:
                return df
        except Exception:
            time.sleep(1.5)
    return pd.DataFrame()

def calcola_rsi(serie_prezzi, periodi=14):
    delta = serie_prezzi.diff()
    guadagno = delta.where(delta > 0, 0).rolling(window=periodi).mean()
    perdita = (-delta.where(delta < 0, 0)).rolling(window=periodi).mean()
    rs = guadagno / (perdita + 1e-9)
    return 100 - (100 / (1 + rs))

def calcola_ema(serie_prezzi, periodi=50):
    return serie_prezzi.ewm(span=periodi, adjust=False).mean()

def classifica_asset(ticker):
    if ticker.endswith("-USD"):
        return "Crypto"
    elif ticker.endswith("=X"):
        return "Forex"
    elif ticker in ["GC=F", "SI=F", "CL=F", "GLD", "SLV"]:
        return "Metalli"
    else:
        return "Nasdaq"

def calcola_dimensione_posizione(prezzo_attuale, classe_asset, is_blitz=False):
    """Allocazione basata su 500$ reali. Ridotta del 50% in modalità Blitz."""
    budget_target = {
        "Crypto": 60.0,
        "Nasdaq": 75.0,
        "Metalli": 70.0,
        "Forex": 100.0
    }
    
    quota_base = budget_target.get(classe_asset, 50.0)
    if is_blitz:
        quota_base = quota_base * 0.5  # Dimezza l'esposizione per i micro-colpi in salita
        
    if classe_asset == "Forex":
        return 1000.0  # 1 Micro-lotto standard fisso
    else:
        return round(quota_base / prezzo_attuale, 6)

# ==============================================================================
# 🎛️ SIDEBAR PARAMETRI DI CONTROLLO INTERFACCIA DI BORDO
# ==============================================================================
st.sidebar.header("⚓ Configurazione Limiti")
max_posizioni = st.sidebar.number_input("Limite Massimo Posizioni", 1, 15, 10)
st.session_state.max_pos_sidebar = max_posizioni

st.sidebar.markdown("---")
st.sidebar.header("⚡ Configurazione Impulso Blitz")
soglia_blitz_vel = st.sidebar.slider("Grilletto Accelerazione Blitz (%)", 0.05, 1.0, 0.20, step=0.05,
                                    help="Scatto percentuale minimo registrato sull'ultima candela a 15m per comprare in salita.")

st.sidebar.markdown("---")
st.sidebar.header("📉 Grilletti RSI Caccia sul Fondo")
rsi_crypto    = st.sidebar.slider("Crypto RSI Trigger",   10, 40, 22, step=1)
rsi_nasdaq    = st.sidebar.slider("Nasdaq RSI Trigger",   10, 40, 26, step=1)
rsi_commodity = st.sidebar.slider("Metalli RSI Trigger",  10, 40, 28, step=1)
rsi_forex     = st.sidebar.slider("Forex RSI Trigger",    10, 40, 32, step=1)

st.sidebar.markdown("---")
st.sidebar.header("🛡️ Gestione Inseguimento & Difese")
trail_attivazione = st.sidebar.slider("Soglia Attivazione Trailing (%)", 0.05, 1.0,  0.20, step=0.05)
trail_distanza    = st.sidebar.slider("Distanza Stop Trailing (%)",       0.1,  2.0,  0.30, step=0.05)
trail_passo       = st.sidebar.slider("Passo Aggiornamento Trailing (%)", 0.01, 0.5,  0.05, step=0.01)

st.sidebar.markdown("---")
st.sidebar.header("🔋 Moduli d'Uscita Rapida")
tp_lampo_pct    = st.sidebar.slider("Take-Profit Lampo (%)",    0.1, 2.0,  0.40, step=0.05)
time_stop_minuti = st.sidebar.slider("Time-Stop Uscita (Minuti)", 5, 120, 15,   step=1)

st.sidebar.markdown("---")
st.sidebar.header("📡 Scudo EMA")
ema_periodi = st.sidebar.slider("Periodi EMA (Scudo Trend)", 20, 200, 50, step=5)

if st.sidebar.button("🔄 Forza Scansione Universo"):
    st.cache_data.clear()
    aggiungi_log("Universo e Radar ricalcolati da zero.")

# ==============================================================================
# 🛰️ REATTORE NATIVO: PROPULSIONE AUTO-REFRESH 60 SECONDI
# ==============================================================================
st.title("🚢 Transatlantico Volumetrico v64.0 (Blitz Mode)")
st.subheader("Centrale Quantistica Multimercato — Doppia Logica Contrarian & Momentum H24")
st.sidebar.success("🔁 Auto-refresh Nativo: Attivo (60s)")

@st.fragment(run_every=60)
def esegui_plancia_live():
    # Ricalcolo metriche interne alla plancia frammentata
    totale_trades = len(st.session_state.storico_trade)
    win_trades = sum(1 for t in st.session_state.storico_trade if "WIN" in t["esito"] or "LAMPO" in t["esito"])
    win_rate = (win_trades / totale_trades * 100) if totale_trades > 0 else 0.0
    pnl_floating = 0.0

    universo = genera_universo_volumetrico()
    storico_universo = scarica_dati_radar(tuple(universo))

    opportunita_rilevate = []
    posizioni_da_chiudere = []  

    if not storico_universo.empty:
        for ticker in universo:
            try:
                col_levels = storico_universo.columns.get_level_values(0)
                if ticker not in col_levels:
                    continue

                df_ticker = storico_universo[ticker].dropna().copy()
                if len(df_ticker) < (ema_periodi + 5):
                    continue

                prezzo_attuale = float(df_ticker['Close'].iloc[-1])
                df_ticker['RSI'] = calcola_rsi(df_ticker['Close'])
                rsi_attuale = float(df_ticker['RSI'].iloc[-1])

                df_ticker['EMA'] = calcola_ema(df_ticker['Close'], ema_periodi)
                ema_attuale = float(df_ticker['EMA'].iloc[-1])
                macro_trend_rialzista = prezzo_attuale > ema_attuale

                # 📊 CALCOLO VELOCITÀ BLITZ (Rapporto tra l'ultima candela chiusa e l'attuale)
                prezzo_precedente = float(df_ticker['Close'].iloc[-2])
                var_velocita = ((prezzo_attuale - prezzo_precedente) / prezzo_precedente) * 100

                # Variazione intraday standard
                oggi = datetime.now().date()
                df_oggi = df_ticker[df_ticker.index.date == oggi] if hasattr(df_ticker.index, 'date') else df_ticker
                if len(df_oggi) >= 2:
                    apertura_gg = float(df_oggi['Open'].iloc[0])
                else:
                    apertura_gg = float(df_ticker['Open'].iloc[-10])  
                var_percentuale = ((prezzo_attuale - apertura_gg) / apertura_gg) * 100

                classe_asset = classifica_asset(ticker)
                soglia_rsi = {
                    "Crypto": rsi_crypto, "Forex": rsi_forex, "Metalli": rsi_commodity, "Nasdaq": rsi_nasdaq
                }.get(classe_asset, rsi_nasdaq)

                # --- 1. GESTIONE DELLE POSIZIONI ATTIVE IN MARE ---
                if ticker in st.session_state.posizioni_attive:
                    pos = st.session_state.posizioni_attive[ticker]
                    orario_ingresso = get_orario_ingresso(pos)
                    minuti_trascorsi = (datetime.now() - orario_ingresso).total_seconds() / 60.0
                    rendimento_attuale_pct = ((prezzo_attuale - pos["prezzo_ingresso"]) / pos["prezzo_ingresso"]) * 100

                    if "trailing_attivo"   not in pos: pos["trailing_attivo"]  = False
                    if "break_even_attivo" not in pos: pos["break_even_attivo"] = False

                    pnl_floating += (prezzo_attuale - pos["prezzo_ingresso"]) * pos["quantita"]

                    # 🛡️ PROTEZIONE AUTO BREAK-EVEN (Scatta a metà strada dal target lampo)
                    if not pos["break_even_attivo"] and rendimento_attuale_pct >= (tp_lampo_pct / 2):
                        st.session_state.posizioni_attive[ticker]["stop_loss"] = pos["prezzo_ingresso"]
                        st.session_state.posizioni_attive[ticker]["break_even_attivo"] = True
                        aggiungi_log(f"🛡️ BREAK-EVEN: Blindato profitto su {ticker} @ {fmt_p(pos['prezzo_ingresso'])}")

                    posizione_chiusa = False

                    # Uscita A: TAKE-PROFIT LAMPO
                    if rendimento_attuale_pct >= tp_lampo_pct:
                        profitto = (prezzo_attuale - pos["prezzo_ingresso"]) * pos["quantita"]
                        st.session_state.pnl_realizzato += profitto
                        st.session_state.storico_trade.append({
                            "data": datetime.now().strftime("%Y-%m-%d"), "ticker": ticker,
                            "tipo": "LONG", "profitto": round(profitto, 2), "esito": "⚡ WIN LAMPO"
                        })
                        posizioni_da_chiudere.append(ticker)
                        aggiungi_log(f"⚡ TP LAMPO COLPITO: {ticker}! +${profitto:.2f}")
                        salva_stato()
                        posizione_chiusa = True

                    # Uscita B: CRONOMETRO TIME-STOP
                    elif minuti_trascorsi >= time_stop_minuti:
                        profitto = (prezzo_attuale - pos["prezzo_ingresso"]) * pos["quantita"]
                        st.session_state.pnl_realizzato += profitto
                        st.session_state.storico_trade.append({
                            "data": datetime.now().strftime("%Y-%m-%d"), "ticker": ticker,
                            "tipo": "LONG", "profitto": round(profitto, 2), "esito": "⏳ TIME-OUT"
                        })
                        posizioni_da_chiudere.append(ticker)
                        aggiungi_log(f"⏱️ TIME-STOP: {ticker} liquidato dopo {int(minuti_trascorsi)} min. Esito: ${profitto:.2f}")
                        salva_stato()
                        posizione_chiusa = True

                    # Uscita C: VIOLAZIONE STOP LOSS SUL PREZZO
                    elif prezzo_attuale <= pos["stop_loss"]:
                        profitto = (pos["stop_loss"] - pos["prezzo_ingresso"]) * pos["quantita"]
                        st.session_state.pnl_realizzato += profitto
                        esito = "✅ WIN (Trail)" if profitto > 0 else "❌ LOSS (Stop)"
                        st.session_state.storico_trade.append({
                            "data": datetime.now().strftime("%Y-%m-%d"), "ticker": ticker,
                            "tipo": "LONG", "profitto": round(profitto, 2), "esito": esito
                        })
                        posizioni_da_chiudere.append(ticker)
                        aggiungi_log(f"💥 STOP COLPITO: {ticker}. Chiuso a {fmt_p(prezzo_attuale)}. PnL: ${profitto:.2f}")
                        salva_stato()
                        posizione_chiusa = True

                    # AGGIORNAMENTO DINAMICO DEL TRAILING STOP INSEGUIMENTO
                    if not delete_flag and not posizione_chiusa:
                        if not pos["trailing_attivo"] and rendimento_attuale_pct >= trail_attivazione:
                            st.session_state.posizioni_attive[ticker]["trailing_attivo"] = True
                            st.session_state.posizioni_attive[ticker]["max_prezzo"] = prezzo_attuale
                            st.session_state.posizioni_attive[ticker]["stop_loss"] = prezzo_attuale * (1 - trail_distanza / 100)
                            aggiungi_log(f"⚡ TRAILING ATTIVATO: Inseguimento iniziato per {ticker} a +{rendimento_attuale_pct:.2f}%")

                        elif pos["trailing_attivo"] and prezzo_attuale > pos["max_prezzo"]:
                            scostamento_pct = ((prezzo_attuale - pos["max_prezzo"]) / pos["max_prezzo"]) * 100
                            if scostamento_pct >= trail_passo:
                                nuovo_stop = prezzo_attuale * (1 - trail_distanza / 100)
                                if nuovo_stop > pos["stop_loss"]:
                                    st.session_state.posizioni_attive[ticker]["max_prezzo"] = prezzo_attuale
                                    st.session_state.posizioni_attive[ticker]["stop_loss"] = nuovo_stop
                                    aggiungi_log(f"🛡️ TRAILING UP: Alzata barriera per {ticker} a {fmt_p(nuovo_stop)}")

                # --- 2. MOTORE DI SCANSIONE NUOVI INGRESSI (DOPPIA ARMA) ---
                else:
                    # Condizione A: Caccia sul fondo contrarian classico
                    is_ingresso_rsi = (rsi_attuale <= soglia_rsi and var_percentuale < 0 and macro_trend_rialzista)
                    
                    # Condizione B: Scalping Blitz direzionale in salita
                    is_ingresso_blitz = (var_velocita >= soglia_blitz_vel and macro_trend_rialzista and var_percentuale > -1.0)

                    if (is_ingresso_rsi or is_ingresso_blitz) and len(st.session_state.posizioni_attive) < max_posizioni:
                        tipo_strategia = "⚡ BLITZ MOVEMENT" if is_ingresso_blitz else "📉 RSI FONDO"
                        blitz_flag = True if is_ingresso_blitz else False
                        
                        stop_iniziale = prezzo_attuale * (1 - trail_distanza / 100)
                        quantita = calcola_dimensione_posizione(prezzo_attuale, classe_asset, is_blitz=blitz_flag)
                        
                        st.session_state.posizioni_attive[ticker] = {
                            "prezzo_ingresso": prezzo_attuale,
                            "stop_loss": stop_iniziale,
                            "max_prezzo": prezzo_attuale,
                            "quantita": quantita,
                            "trailing_attivo": False,
                            "break_even_attivo": False,
                            "orario_ingresso": datetime.now().isoformat(),
                            "tipo_operazione": tipo_strategia
                        }
                        
                        opportunita_rilevate.append({
                            "Ticker": ticker, "Classe": classe_asset, "Prezzo": fmt_p(prezzo_attuale),
                            "RSI": f"{rsi_attuale:.1f}", "Var Velocità": f"+{var_velocita:.2f}%", "Strategia": tipo_strategia
                        })
                        
                        aggiungi_log(f"🚀 INGRESSO ({tipo_strategia}): Acquistato {ticker} ({classe_asset}) @ {fmt_p(prezzo_attuale)} | Q: {quantita}")
                        salva_stato()

            except Exception:
                continue

    # Pulizia e rimozione posizioni archiviate al di fuori del loop di iterazione dict
    for ticker in posizioni_da_chiudere:
        if ticker in st.session_state.posizioni_attive:
            del st.session_state.posizioni_attive[ticker]

    # ==============================================================================
    # 📟 VISUALIZZAZIONE INTERFACCIA METRICHE SUPERIORI
    # ==============================================================================
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #10b981;'>", unsafe_allow_html=True)
        st.metric(label="💰 PROFITTO NETTO REALIZZATO", value=f"${st.session_state.pnl_realizzato:,.2f}", delta="In Cassaforte JSON")
        st.markdown("</div>", unsafe_allow_html=True)
    with m_col2:
        st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #3b82f6;'>", unsafe_allow_html=True)
        st.metric(label="🎯 SILURI IN MARE (POSIZIONI)", value=f"{len(st.session_state.posizioni_attive)} / {max_posizioni}", delta=f"{max_posizioni - len(st.session_state.posizioni_attive)} Slot")
        st.markdown("</div>", unsafe_allow_html=True)
    with m_col3:
        st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #f59e0b;'>", unsafe_allow_html=True)
        st.metric(label="📈 PRECISIONE STRATEGIA", value=f"{win_rate:.1f}%", delta=f"Su {totale_trades} trade")
        st.markdown("</div>", unsafe_allow_html=True)
    with m_col4:
        st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #a855f7;'>", unsafe_allow_html=True)
        st.metric(label="📊 P&L FLOATING (aperto)", value=f"${pnl_floating:,.2f}", delta="Contenimento Fluttuazione")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ==============================================================================
    # 📟 LAYOUT PLANCIA DI COMANDO AD ALTA DENSITÀ D'INFORMAZIONE
    # ==============================================================================
    col_sx, col_dx = st.columns([2, 1])
    
    with col_sx:
        st.subheader("🎯 Posizioni Attualmente in Mare")
        if st.session_state.posizioni_attive:
            tabella_pos = []
            for tk, dati in st.session_state.posizioni_attive.items():
                orario_ingresso = get_orario_ingresso(dati)
                minuti_passati = int((datetime.now() - orario_ingresso).total_seconds() / 60)
                t_status = "TRAILING ⚡" if dati.get("trailing_attivo", False) else ("BREAK-EVEN 🛡️" if dati.get("break_even_attivo", False) else "Iniziale ⏳")
                tabella_pos.append({
                    "Asset": tk, "Classe": classifica_asset(tk), "Modalità": dati.get("tipo_operazione", "📉 RSI FONDO"),
                    "Ingresso": fmt_p(dati["prezzo_ingresso"]), "Stop Loss": fmt_p(dati["stop_loss"]), 
                    "Max Visto": fmt_p(dati["max_prezzo"]), "Stato Difese": t_status, "Tempo": f"{minuti_passati} min"
                })
            st.dataframe(pd.DataFrame(tabella_pos), width='stretch', hide_index=True)
        else:
            st.info("Nessun siluro in mare. Il radar sta scansionando i flussi volumetrici cross-asset.")

        st.subheader("🔥 Monitor Occasioni Intercettate dal Radar")
        if opportunita_rilevate:
            st.dataframe(pd.DataFrame(opportunita_rilevate), width='stretch', hide_index=True)
        else:
            st.success("Tutti gli asset monitorati viaggiano stabili dentro i canali di volatilità ordinaria.")

    with col_dx:
        st.subheader("📜 Log Scatola Nera (Live)")
        testo_log = "\n".join(st.session_state.log_sistema)
        st.text_area("Eventi del Motore", value=testo_log, height=200, label_visibility="collapsed")

        st.subheader("📋 Storico Ultimi Rilasci (In Salva Stato)")
        df_storico = pd.DataFrame(st.session_state.storico_trade)
        if not df_storico.empty:
            st.dataframe(df_storico.tail(8), width='stretch', hide_index=True)

    # Area Curve di Crescita
    if len(st.session_state.storico_trade) > 1:
        with st.expander("📈 Equity Curve — Profitto Cumulativo Storico", expanded=False):
            df_eq = pd.DataFrame(st.session_state.storico_trade)
            if 'profitto' in df_eq.columns:
                df_eq["profitto_cumulativo"] = df_eq["profitto"].cumsum() + 1485.50
                st.line_chart(df_eq[["profitto_cumulativo"]], width='stretch')

# Esecuzione e propulsione dell'interfaccia
esegui_plancia_live()
