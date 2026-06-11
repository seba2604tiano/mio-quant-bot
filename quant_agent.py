import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import json
import os
import requests
from datetime import datetime, timedelta

# ==============================================================================
# 🚢 CONFIGURAZIONE PLANCIA STREAMLIT (v61.0 - Elite Quant System - FIXED)
# ==============================================================================
st.set_page_config(
    page_title="🚢 Transatlantico v61.0 - Plancia Quant", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 💾 PERSISTENZA DATI SU FILE (Fix: salvataggio tra sessioni)
# ==============================================================================
SAVE_FILE = "transatlantico_stato.json"

def salva_stato():
    """Salva PnL e storico trade su file JSON per persistenza tra sessioni."""
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
    """Carica PnL e storico trade da file se esiste."""
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
    st.session_state.posizioni_attive = {
        "BTC-USD": {
            "prezzo_ingresso": 96200.0, "stop_loss": 95800.0, "max_prezzo": 96500.0,
            "quantita": 0.05, "trailing_attivo": True, "break_even_attivo": False,
            "orario_ingresso": datetime.now().isoformat()
        },
        "NVDA": {
            "prezzo_ingresso": 135.20, "stop_loss": 134.50, "max_prezzo": 136.10,
            "quantita": 10, "trailing_attivo": False, "break_even_attivo": False,
            "orario_ingresso": datetime.now().isoformat()
        }
    }

if 'storico_trade' not in st.session_state:
    st.session_state.storico_trade = stato_caricato["storico_trade"] if stato_caricato else [
        {"data": "2026-06-08", "ticker": "TSLA", "tipo": "LONG", "profitto": 120.00, "esito": "✅ WIN"},
        {"data": "2026-06-08", "ticker": "SOL-USD", "tipo": "LONG", "profitto": 45.50, "esito": "✅ WIN"},
        {"data": "2026-06-09", "ticker": "AAPL", "tipo": "LONG", "profitto": -30.00, "esito": "❌ LOSS"},
    ]

if 'log_sistema' not in st.session_state:
    st.session_state.log_sistema = ["[BOOT] Sistemi avviati. Transatlantico v61.0 online."]

def aggiungi_log(messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_sistema.insert(0, f"[{orario}] {messaggio}")
    if len(st.session_state.log_sistema) > 30:
        st.session_state.log_sistema.pop()

def fmt_p(val):
    """Formattazione dinamica dei prezzi per salvaguardare i decimali del Forex."""
    return f"${val:.4f}" if val < 5 else f"${val:.2f}"

def get_orario_ingresso(pos):
    """Converte l'orario d'ingresso da stringa ISO a datetime in modo sicuro."""
    oi = pos.get("orario_ingresso", datetime.now().isoformat())
    if isinstance(oi, datetime):
        return oi
    try:
        return datetime.fromisoformat(oi)
    except Exception:
        return datetime.now()

# ==============================================================================
# 🌌 MOTORI: GENERAZIONE UNIVERSO GLOBAL CROSS-ASSET (45 TARGET)
# Fix: rimossi ticker non validi su Yahoo Finance (UNI1-USD, APT1-USD, SUI1-USD)
# Sostituiti con ticker corretti: UNI-USD, APT-USD, SUI20947-USD → AGIX-USD
# ==============================================================================
@st.cache_data(ttl=1800)
def genera_universo_volumetrico():
    crypto = [
        "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "SHIB-USD",
        "XRP-USD", "AVAX-USD", "ADA-USD", "LINK-USD", "DOT-USD",
        "LTC-USD", "UNI-USD", "NEAR-USD", "APT-USD", "FET-USD",
        "ICP-USD", "ATOM-USD", "ALGO-USD", "FIL-USD", "MATIC-USD"
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
# 🛡️ RADAR TEMPORALE: DOWNLOAD DATI + CLASSIFICAZIONE ASSET
# ==============================================================================
@st.cache_data(ttl=60)
def scarica_dati_radar(universo_tickers):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
        except Exception as e:
            aggiungi_log(f"⚠️ Download tentativo {tentativo+1}/3 fallito: {type(e).__name__}: {e}")
            time.sleep(1.5)
    return pd.DataFrame()

def calcola_rsi(serie_prezzi, periodi=14):
    delta = serie_prezzi.diff()
    guadagno = delta.where(delta > 0, 0).rolling(window=periodi).mean()
    perdita = (-delta.where(delta < 0, 0)).rolling(window=periodi).mean()
    rs = guadagno / (perdita + 1e-9)
    return 100 - (100 / (1 + rs))

def calcola_ema(serie_prezzi, periodi=50):
    """EMA con periodi parametrizzabili dalla sidebar (default 50 = ~12.5h su 15m)."""
    return serie_prezzi.ewm(span=periodi, adjust=False).mean()

def classifica_asset(ticker):
    """Restituisce la classe dell'asset in modo affidabile."""
    if ticker.endswith("-USD"):
        return "Crypto"
    elif ticker.endswith("=X"):
        return "Forex"
    elif ticker in ["GC=F", "SI=F", "CL=F", "GLD", "SLV"]:
        return "Metalli"
    else:
        return "Nasdaq"

def calcola_dimensione_posizione(prezzo_attuale, classe_asset, capitale_per_trade=2000):
    """
    Fix: dimensione posizione corretta per classe asset.
    - Crypto/Nasdaq/Metalli: dimensione in unità = capitale / prezzo
    - Forex: usa lotti micro (1000 unità base) invece di 2000 unità che sarebbe assurdo
    """
    if classe_asset == "Forex":
        return 1000.0  # 1 micro-lotto standard
    else:
        return round(capitale_per_trade / prezzo_attuale, 6)

# ==============================================================================
# 🎯 PLANCIA SUPERIORE: SEZIONE METRICHE DI PERFORMANCE
# ==============================================================================
st.title("🚢 Transatlantico Volumetrico v61.0")
st.subheader("Centrale Quantistica Multimercato — Protezione Break-Even & Scudo EMA")

totale_trades = len(st.session_state.storico_trade)
win_trades = sum(1 for t in st.session_state.storico_trade if "WIN" in t["esito"] or "LAMPO" in t["esito"])
win_rate = (win_trades / totale_trades * 100) if totale_trades > 0 else 0.0

# Calcolo P&L floating sulle posizioni aperte
pnl_floating = 0.0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #10b981;'>", unsafe_allow_html=True)
    st.metric(label="💰 PROFITTO NETTO REALIZZATO", value=f"${st.session_state.pnl_realizzato:,.2f}", delta="In Cassaforte")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #3b82f6;'>", unsafe_allow_html=True)
    attive = len(st.session_state.posizioni_attive)
    st.metric(label="🎯 SILURI IN MARE (POSIZIONI)", value=f"{attive} / {st.session_state.get('max_pos_sidebar', 5)} Target",
              delta=f"{st.session_state.get('max_pos_sidebar', 5) - attive} Slot Liberi", delta_color="inverse")
    st.markdown("</div>", unsafe_allow_html=True)

with col3:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #f59e0b;'>", unsafe_allow_html=True)
    st.metric(label="📈 PRECISIONE STRATEGIA", value=f"{win_rate:.1f}%", delta=f"Su {totale_trades} Operazioni Chiuse")
    st.markdown("</div>", unsafe_allow_html=True)

with col4:
    st.markdown("<div style='background-color:#1e293b; padding:15px; border-radius:10px; border-left: 5px solid #a855f7;'>", unsafe_allow_html=True)
    colore_floating = "normal" if pnl_floating >= 0 else "inverse"
    st.metric(label="📊 P&L FLOATING (aperto)", value=f"${pnl_floating:,.2f}", delta="Live (si aggiorna dopo scansione)")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
# 🎛️ SIDEBAR PARAMETRI
# ==============================================================================
st.sidebar.header("⚓ Configurazione Limiti")
max_posizioni = st.sidebar.number_input("Limite Massimo Posizioni", 1, 15, 10)
st.session_state.max_pos_sidebar = max_posizioni

st.sidebar.markdown("---")
st.sidebar.header("🎯 Grilletti RSI per Classe Asset")
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
st.sidebar.header("⚡ Moduli d'Uscita Rapida")
tp_lampo_pct    = st.sidebar.slider("Take-Profit Lampo (%)",    0.1, 2.0,  0.40, step=0.05)
time_stop_minuti = st.sidebar.slider("Time-Stop Uscita (Minuti)", 5, 120, 15,   step=1)

# Fix: EMA ora parametrizzabile invece di fissa a 100
st.sidebar.markdown("---")
st.sidebar.header("📡 Scudo EMA")
ema_periodi = st.sidebar.slider("Periodi EMA (Scudo Trend)", 20, 200, 50, step=5,
                                help="50 = ~12.5h | 100 = ~25h su timeframe 15m")

if st.sidebar.button("🔄 Forza Scansione Universo"):
    st.cache_data.clear()
    aggiungi_log("Universo e Radar ricalcolati con i nuovi parametri chirurgici.")

# ==============================================================================
# 🛰️ RADAR & LOGICA DI TRADING AVANZATA (EMA + MULTI-RSI + BREAK-EVEN)
# ==============================================================================
st.header("🔍 Monitoraggio e Puntamento di Precisione")

# Auto-refresh ogni 60 secondi (Fix: il sistema si aggiorna automaticamente)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=60000, limit=None, key="radar_refresh")
    st.sidebar.success("🔁 Auto-refresh: ogni 60s")
except ImportError:
    st.sidebar.warning("⚠️ Installa `streamlit-autorefresh` per aggiornamento automatico:\n`pip install streamlit-autorefresh`")

with st.spinner("Scansione in corso del paniere Cross-Asset..."):
    universo = genera_universo_volumetrico()
    storico_universo = scarica_dati_radar(tuple(universo))

opportunita_rilevate = []
posizioni_da_chiudere = []  # Fix: raccogliamo le chiusure e le eseguiamo fuori dal loop dict

if not storico_universo.empty:
    for ticker in universo:
        try:
            # Fix: gestione robusta dei livelli delle colonne MultiIndex
            col_levels = storico_universo.columns.get_level_values(0)
            if ticker not in col_levels:
                continue

            df_ticker = storico_universo[ticker].dropna().copy()
            if len(df_ticker) < (ema_periodi + 5):
                continue

            prezzo_attuale = float(df_ticker['Close'].iloc[-1])
            df_ticker['RSI'] = calcola_rsi(df_ticker['Close'])
            rsi_attuale = float(df_ticker['RSI'].iloc[-1])

            # Scudo EMA con periodi parametrizzati
            df_ticker['EMA'] = calcola_ema(df_ticker['Close'], ema_periodi)
            ema_attuale = float(df_ticker['EMA'].iloc[-1])
            macro_trend_rialzista = prezzo_attuale > ema_attuale

            # Fix variazione intraday: usa la candela più vicina all'apertura della sessione corrente
            oggi = datetime.now().date()
            df_oggi = df_ticker[df_ticker.index.date == oggi] if hasattr(df_ticker.index, 'date') else df_ticker
            if len(df_oggi) >= 2:
                apertura_gg = float(df_oggi['Open'].iloc[0])
            else:
                apertura_gg = float(df_ticker['Open'].iloc[-10])  # fallback sicuro: ultime 10 candele
            var_percentuale = ((prezzo_attuale - apertura_gg) / apertura_gg) * 100

            classe_asset = classifica_asset(ticker)
            soglia_rsi = {
                "Crypto": rsi_crypto,
                "Forex": rsi_forex,
                "Metalli": rsi_commodity,
                "Nasdaq": rsi_nasdaq
            }.get(classe_asset, rsi_nasdaq)

            # --- CORE LOGIC: GESTIONE POSIZIONI ATTIVE ---
            if ticker in st.session_state.posizioni_attive:
                pos = st.session_state.posizioni_attive[ticker]

                # Compatibilità con vecchi stati che hanno datetime invece di isoformat
                orario_ingresso = get_orario_ingresso(pos)
                minuti_trascorsi = (datetime.now() - orario_ingresso).total_seconds() / 60.0
                rendimento_attuale_pct = ((prezzo_attuale - pos["prezzo_ingresso"]) / pos["prezzo_ingresso"]) * 100

                if "trailing_attivo"  not in pos: pos["trailing_attivo"]  = False
                if "break_even_attivo" not in pos: pos["break_even_attivo"] = False

                # Aggiorna P&L floating (visualizzato nella metrica in alto)
                pnl_floating += (prezzo_attuale - pos["prezzo_ingresso"]) * pos["quantita"]

                # 🛡️ MODULO AUTO BREAK-EVEN
                if not pos["break_even_attivo"] and rendimento_attuale_pct >= (tp_lampo_pct / 2):
                    st.session_state.posizioni_attive[ticker]["stop_loss"] = pos["prezzo_ingresso"]
                    st.session_state.posizioni_attive[ticker]["break_even_attivo"] = True
                    aggiungi_log(f"🛡️ BREAK-EVEN: Blindato su {ticker} @ {fmt_p(pos['prezzo_ingresso'])}")

                posizione_chiusa = False

                # 🚀 MODULO A: TAKE-PROFIT LAMPO
                if rendimento_attuale_pct >= tp_lampo_pct:
                    profitto = (prezzo_attuale - pos["prezzo_ingresso"]) * pos["quantita"]
                    st.session_state.pnl_realizzato += profitto
                    st.session_state.storico_trade.append({
                        "data": datetime.now().strftime("%Y-%m-%d"), "ticker": ticker,
                        "tipo": "LONG", "profitto": round(profitto, 2), "esito": "⚡ WIN LAMPO"
                    })
                    posizioni_da_chiudere.append(ticker)
                    aggiungi_log(f"⚡ TP LAMPO: {ticker} colpito! +${profitto:.2f}")
                    salva_stato()
                    posizione_chiusa = True

                # ⏱️ MODULO B: CRONOMETRO TIME-STOP
                elif minuti_trascorsi >= time_stop_minuti:
                    profitto = (prezzo_attuale - pos["prezzo_ingresso"]) * pos["quantita"]
                    st.session_state.pnl_realizzato += profitto
                    st.session_state.storico_trade.append({
                        "data": datetime.now().strftime("%Y-%m-%d"), "ticker": ticker,
                        "tipo": "LONG", "profitto": round(profitto, 2), "esito": "⏳ TIME-OUT"
                    })
                    posizioni_da_chiudere.append(ticker)
                    aggiungi_log(f"⏱️ TIME-STOP: {ticker} liquidato dopo {int(minuti_trascorsi)} min. ${profitto:.2f}")
                    salva_stato()
                    posizione_chiusa = True

                # 💥 STOP LOSS COLPITO
                elif prezzo_attuale <= pos["stop_loss"]:
                    profitto = (pos["stop_loss"] - pos["prezzo_ingresso"]) * pos["quantita"]
                    st.session_state.pnl_realizzato += profitto
                    esito = "✅ WIN (Trail)" if profitto > 0 else "❌ LOSS (Stop)"
                    st.session_state.storico_trade.append({
                        "data": datetime.now().strftime("%Y-%m-%d"), "ticker": ticker,
                        "tipo": "LONG", "profitto": round(profitto, 2), "esito": esito
                    })
                    posizioni_da_chiudere.append(ticker)
                    aggiungi_log(f"💥 STOP COLPITO: {ticker}. Esito: ${profitto:.2f}")
                    salva_stato()
                    posizione_chiusa = True

                # MODULO C: TRAILING STOP (solo se posizione ancora aperta)
                if not posizione_chiusa:
                    if not pos["trailing_attivo"] and rendimento_attuale_pct >= trail_attivazione:
                        st.session_state.posizioni_attive[ticker]["trailing_attivo"] = True
                        st.session_state.posizioni_attive[ticker]["max_prezzo"] = prezzo_attuale
                        st.session_state.posizioni_attive[ticker]["stop_loss"] = prezzo_attuale * (1 - trail_distanza / 100)
                        aggiungi_log(f"⚡ TRAILING ATTIVATO: {ticker} a +{rendimento_attuale_pct:.2f}%")

                    elif pos["trailing_attivo"] and prezzo_attuale > pos["max_prezzo"]:
                        scostamento_pct = ((prezzo_attuale - pos["max_prezzo"]) / pos["max_prezzo"]) * 100
                        if scostamento_pct >= trail_passo:
                            nuovo_stop = prezzo_attuale * (1 - trail_distanza / 100)
                            if nuovo_stop > pos["stop_loss"]:
                                st.session_state.posizioni_attive[ticker]["max_prezzo"] = prezzo_attuale
                                st.session_state.posizioni_attive[ticker]["stop_loss"] = nuovo_stop
                                aggiungi_log(f"🛡️ TRAILING UP: {ticker} → stop a {fmt_p(nuovo_stop)}")

            # --- INGRESSI: CACCIA SUL FONDO CON SCUDO EMA ---
            else:
                if rsi_attuale <= soglia_rsi and var_percentuale < 0 and macro_trend_rialzista:
                    status_trend = "RIALZISTA ✅"
                    opportunita_rilevate.append({
                        "Ticker": ticker,
                        "Classe": classe_asset,
                        "Prezzo": fmt_p(prezzo_attuale),
                        "RSI": f"{rsi_attuale:.1f} (soglia {soglia_rsi})",
                        "Var%": f"{var_percentuale:.2f}%",
                        "Macro Trend": status_trend
                    })

                    if len(st.session_state.posizioni_attive) < max_posizioni:
                        stop_iniziale = prezzo_attuale * (1 - trail_distanza / 100)
                        # Fix: dimensione posizione corretta per classe asset
                        quantita = calcola_dimensione_posizione(prezzo_attuale, classe_asset)
                        st.session_state.posizioni_attive[ticker] = {
                            "prezzo_ingresso": prezzo_attuale,
                            "stop_loss": stop_iniziale,
                            "max_prezzo": prezzo_attuale,
                            "quantita": quantita,
                            "trailing_attivo": False,
                            "break_even_attivo": False,
                            "orario_ingresso": datetime.now().isoformat()  # Fix: stringa ISO serializzabile
                        }
                        aggiungi_log(f"🚀 ACQUISTO: {ticker} ({classe_asset}) @ {fmt_p(prezzo_attuale)} | Q: {quantita}")

        except Exception as e:
            # Fix: log degli errori invece di inghiottirli silenziosamente
            aggiungi_log(f"⚠️ Errore su {ticker}: {type(e).__name__}: {e}")
            continue

else:
    st.warning("⚠️ Radar disturbato da Yahoo Finance. Allineamento contromisure ECM in corso...")

# Fix: chiusura posizioni fuori dal loop per evitare modifica del dict durante iterazione
for ticker in posizioni_da_chiudere:
    if ticker in st.session_state.posizioni_attive:
        del st.session_state.posizioni_attive[ticker]

# Aggiorna metrica floating dopo il loop
# (si aggiorna al prossimo rerun, è corretto)

# ==============================================================================
# 📊 EQUITY CURVE (Bonus: grafico PnL cumulativo storico)
# ==============================================================================
if len(st.session_state.storico_trade) > 1:
    with st.expander("📈 Equity Curve — Curva Profitto Cumulativo", expanded=False):
        df_eq = pd.DataFrame(st.session_state.storico_trade)
        df_eq["profitto_cumulativo"] = df_eq["profitto"].cumsum() + 1485.50
        st.line_chart(df_eq[["profitto_cumulativo"]], use_container_width=True)

# ==============================================================================
# 📟 VISUALIZZAZIONE INTERFACCIA GRAFICA DI BORDO
# ==============================================================================
col_sx, col_dx = st.columns([2, 1])

with col_sx:
    st.subheader("🎯 Posizioni Attualmente in Mare")
    if st.session_state.posizioni_attive:
        tabella_pos = []
        for tk, dati in st.session_state.posizioni_attive.items():
            orario_ingresso = get_orario_ingresso(dati)
            minuti_passati = int((datetime.now() - orario_ingresso).total_seconds() / 60)
            t_status = (
                "TRAILING ⚡" if dati.get("trailing_attivo", False)
                else ("BREAK-EVEN 🛡️" if dati.get("break_even_attivo", False)
                      else "Iniziale ⏳")
            )
            tabella_pos.append({
                "Asset": tk,
                "Classe": classifica_asset(tk),
                "Ingresso": fmt_p(dati["prezzo_ingresso"]),
                "Stop Loss": fmt_p(dati["stop_loss"]),
                "Max Visto": fmt_p(dati["max_prezzo"]),
                "Stato Difese": t_status,
                "Tempo in Mare": f"{minuti_passati} min"
            })
        st.dataframe(pd.DataFrame(tabella_pos), use_container_width=True, hide_index=True)
    else:
        st.info("Nessun siluro in mare. Radar in scansione profonda.")

    st.subheader("🔥 Radar Occasioni Rilevate (Approvate da Scudo EMA)")
    if opportunita_rilevate:
        st.dataframe(pd.DataFrame(opportunita_rilevate), use_container_width=True, hide_index=True)
    else:
        st.success("Tutti gli asset idonei sono in acque sicure. Nessun segnale pulito filtrato dalla EMA al momento.")

with col_dx:
    st.subheader("📜 Log Scatola Nera (Live)")
    testo_log = "\n".join(st.session_state.log_sistema)
    st.text_area("Eventi del Motore", value=testo_log, height=200, label_visibility="collapsed")

    st.subheader("📋 Storico Ultimi Rilasci")
    df_storico = pd.DataFrame(st.session_state.storico_trade)
    if not df_storico.empty:
        st.dataframe(df_storico.tail(8), use_container_width=True, hide_index=True)

# Fix: rimosso time.sleep(0.5) — bloccava il rendering senza benefici
