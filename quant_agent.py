import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# ==============================================================================
# 🚢 CONFIGURAZIONE PLANCIA STREAMLIT (v51.0)
# ==============================================================================
st.set_page_config(
    page_title="🚢 Transatlantico v51.0 - Plancia Quant", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inizializzazione della memoria della nave (Session State)
if 'pnl_realizzato' not in st.session_state:
    st.session_state.pnl_realizzato = 1485.50  # Cassa iniziale consolidata
if 'posizioni_attive' not in st.session_state:
    st.session_state.posizioni_attive = {}
if 'storico_trade' not in st.session_state:
    st.session_state.storico_trade = [
        {"data": "2026-06-08", "ticker": "TSLA", "tipo": "LONG", "profitto": 120.00, "esito": "✅ WIN"},
        {"data": "2026-06-08", "ticker": "SOL-USD", "tipo": "LONG", "profitto": 45.50, "esito": "✅ WIN"}
    ]
if 'log_sistema' not in st.session_state:
    st.session_state.log_sistema = ["Sistemi v51.0 pronti. In attesa del suono della campanella di Wall Street..."]
if 'stop_count' not in st.session_state:
    st.session_state.stop_count = {}  # Registro dei cartellini gialli/rossi per asset
if 'ultimo_reset_giorno' not in st.session_state:
    st.session_state.ultimo_reset_giorno = datetime.now().strftime("%Y-%m-%d")

# 🕛 LOGICA DI RESET A MEZZANOTTE (Tabula Rasa delle squalifiche)
oggi = datetime.now().strftime("%Y-%m-%d")
if st.session_state.ultimo_reset_giorno != oggi:
    st.session_state.stop_count = {}
    st.session_state.ultimo_reset_giorno = oggi
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_sistema.insert(0, f"[{orario}] 🕛 Reset di Mezzanotte: Tutte le squalifiche sono state azzerate. Buona giornata di campionato!")

def aggiungi_log(messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_sistema.insert(0, f"[{orario}] {messaggio}")
    if len(st.session_state.log_sistema) > 30:
        st.session_state.log_sistema.pop()

# ==============================================================================
# 🌌 MOTORI: UNIVERSO VOLUMETRICO DINAMICO (50 TOP LEADER)
# ==============================================================================
@st.cache_data(ttl=1800)
def genera_universo_volumetrico():
    crypto_kings = ["BTC-USD", "ETH-USD", "SOL-USD"]
    pool_di_base = [
        "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "NFLX", "AMD", "INTC", 
        "QCOM", "PLTR", "COIN", "MARA", "SMCI", "BABA", "HOOD", "NIO", "SPY", "QQQ", 
        "IWM", "DIA", "GLD", "SLV", "USO", "SMH", "ARKK", "XLE", "XBI", "TLT", "BAC",
        "JPM", "WMT", "DIS", "XOM", "TSM", "F", "GE", "PFE", "T", "VZ", "WFC", "GME"
    ]
    try:
        dati_volume = yf.download(pool_di_base, period="1d", progress=False)
        if 'Volume' in dati_volume and not dati_volume['Volume'].empty:
            ultimi_volumi = dati_volume['Volume'].iloc[-1].dropna()
            top_47_azioni = ultimi_volumi.sort_values(ascending=False).head(47).index.tolist()
            return crypto_kings + top_47_azioni
    except:
        pass
    return crypto_kings + pool_di_base[:47]

def calcola_rsi(serie_prezzi, periodi=14):
    delta = serie_prezzi.diff()
    guadagno = (delta.where(delta > 0, 0)).rolling(window=periodi).mean()
    perdita = (-delta.where(delta < 0, 0)).rolling(window=periodi).mean()
    rs = guadagno / (perdita + 1e-9)
    return 100 - (100 / (1 + rs))

# ==============================================================================
# 📊 METRICHE DELLA PLANCIA SUPERIORE
# ==============================================================================
st.title("🚢 Transatlantico Volumetrico v51.0")
st.subheader("Modulo d'Attacco con Trailing Stop Adattivo (Bollinger) - Timeframe 15 Minuti")

totale_trades = len(st.session_state.storico_trade)
win_trades = sum(1 for t in st.session_state.storico_trade if "WIN" in t["esito"])
win_rate = (win_trades / totale_trades * 100) if totale_trades > 0 else 0.0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="💰 PROFITTO NETTO REALIZZATO", value=f"${st.session_state.pnl_realizzato:,.2f}", delta="In Cassaforte")
with col2:
    st.metric(label="🎯 SILURI IN MARE (POSIZIONI)", value=f"{len(st.session_state.posizioni_attive)} / 5 Attive")
with col3:
    st.metric(label="📈 PRECISIONE SQUADRA", value=f"{win_rate:.1f}%", delta=f"Su {totale_trades} Match")

st.markdown("---")

# ==============================================================================
# 🎛️ SIDEBAR: MODULO TATTICO AGGIORNATO DAL MISTER
# ==============================================================================
st.sidebar.header("⚓ Configurazione Spogliatoio")
soglia_rsi_fondo = st.sidebar.slider("Grilletto RSI (Ipervenduto Fondo)", 10, 40, 25)
periodi_bollinger = st.sidebar.slider("Periodi Media Bollinger (Regista Trailing)", 10, 50, 20)
stop_iniziale_pct = st.sidebar.slider("Stop Loss Iniziale Sicurezza (%)", 0.5, 5.0, 1.5, step=0.1)
max_posizioni = st.sidebar.number_input("Massimo Slot Siluri", 1, 10, 5)

# ==============================================================================
# ⚡ RADAR SCANSIONE LIVE SUI 15 MINUTI
# ==============================================================================
universo = genera_universo_volumetrico()
try:
    # Richiesta a 15 minuti per pulire il rumore di fondo
    storico_universo = yf.download(universo, period="5d", interval="15m", progress=False, group_by='ticker')
except:
    storico_universo = pd.DataFrame()

opportunita_rilevate = []

if not storico_universo.empty:
    for ticker in universo:
        # CONTROLLO REQUISITO DISCIPLINA: Cartellino rosso (2 stop consecutivi in perdita)
        if st.session_state.stop_count.get(ticker, 0) >= 2 and ticker not in st.session_state.posizioni_attive:
            continue
            
        try:
            if ticker in storico_universo.columns.levels[0]:
                df_ticker = storico_universo[ticker].dropna()
                if len(df_ticker) < periodi_bollinger + 5:
                    continue
                
                prezzo_attuale = df_ticker['Close'].iloc[-1]
                rsi_attuale = calcola_rsi(df_ticker['Close']).iloc[-1]
                
                # Calcolo della Media Centrale delle Bande di Bollinger
                ma_centrale = df_ticker['Close'].rolling(window=periodi_bollinger).mean().iloc[-1]
                
                apertura_gg = df_ticker['Open'].iloc[0]
                var_percentuale = ((prezzo_attuale - apertura_gg) / apertura_gg) * 100
                
                # 🛡️ GESTIONE POSIZIONI ATTIVE (TRAILING ADATTIVO AL TOCCO)
                if ticker in st.session_state.posizioni_attive:
                    pos = st.session_state.posizioni_attive[ticker]
                    
                    # Logica Elastica: lo stop è quello iniziale finché il prezzo è sotto la media.
                    # Se il prezzo gioca in attacco e supera la media centrale, la media diventa il nostro Trailing Stop.
                    stop_dinamico = pos['stop_iniziale']
                    if prezzo_attuale > ma_centrale:
                        stop_dinamico = ma_centrale
                    
                    # USCITA IMMEDIATA AL MILLISECONDO (Al tocco della linea difensiva)
                    if prezzo_attuale <= stop_dinamico:
                        profitto = (prezzo_attuale - pos['prezzo_ingresso']) * pos['quantita']
                        st.session_state.pnl_realizzato += profitto
                        esito = "✅ WIN" if profitto > 0 else "❌ LOSS"
                        
                        # Se il trade è negativo, incrementiamo il contatore dei falli
                        if profitto < 0:
                            st.session_state.stop_count[ticker] = st.session_state.stop_count.get(ticker, 0) + 1
                        
                        st.session_state.storico_trade.append({
                            "data": oggi, "ticker": ticker, "tipo": "LONG", "profitto": profitto, "esito": esito
                        })
                        del st.session_state.posizioni_attive[ticker]
                        aggiungi_log(f"💥 STOP ADATTIVO COLPITO su {ticker}. Chiuso al volo a ${prezzo_attuale:.2f}. Esito: {esito} (${profitto:.2f})")
                
                # 🚀 CACCIA SUL FONDO E INGRESSO IN SQUADRA
                else:
                    if rsi_attuale <= soglia_rsi_fondo and var_percentuale < 0:
                        opportunita_rilevate.append({
                            "Ticker": ticker, "Prezzo": f"${prezzo_attuale:.2f}",
                            "Variazione GG": f"{var_percentuale:.2f}%", "RSI 15M": f"{rsi_attuale:.1f}"
                        })
                        
                        if len(st.session_state.posizioni_attive) < max_posizioni:
                            st.session_state.posizioni_attive[ticker] = {
                                "prezzo_ingresso": prezzo_attuale,
                                "stop_iniziale": prezzo_attuale * (1 - (stop_iniziale_pct / 100)),
                                "quantita": round(2000 / prezzo_attuale, 4)  # Potenza di fuoco fissa da $2000
                            }
                            aggiungi_log(f"🚀 SILURO LANCIATO: Acquistato {ticker} a ${prezzo_attuale:.2f} (RSI: {rsi_attuale:.1f}). Inizializzato Stop di sicurezza.")
        except:
            continue

# ==============================================================================
# 📟 INTERFACCIA GRAFICA DI INTERAZIONE
# ==============================================================================
col_sx, col_dx = st.columns([2, 1])

with col_sx:
    st.subheader("🎯 Flotta in Mare (Posizioni Attive)")
    if st.session_state.posizioni_attive:
        tabella_pos = []
        for tk, dati in st.session_state.posizioni_attive.items():
            tabella_pos.append({
                "Asset": tk,
                "Prezzo Ingresso": f"${dati['prezzo_ingresso']:.2f}",
                "Frizione Caricata": dati['quantita']
            })
        st.dataframe(pd.DataFrame(tabella_pos), use_container_width=True, hide_index=True)
    else:
        st.info("Nessuna posizione aperta. Il centrocampo sta filtrando i titoli.")

    st.subheader("🔥 Radar Occasioni d'Attacco (RSI <= Soglia)")
    if opportunita_rilevate:
        st.dataframe(pd.DataFrame(opportunita_rilevate), use_container_width=True, hide_index=True)
    else:
        st.success("Acque calme. Nessun leader volumetrico si trova attualmente sul fondo.")

with col_dx:
    st.subheader("📜 Scatola Nera Live")
    st.text_area("Eventi", value="\n".join(st.session_state.log_sistema), height=200, label_visibility="collapsed")
    
    st.subheader("🔴 Panchina Squalifiche (2 KO)")
    squalificati = [k for k, v in st.session_state.stop_count.items() if v >= 2]
    if squalificati:
        st.warning(f"Fuori gioco fino a Mezzanotte: {', '.join(squalificati)}")
    else:
        st.info("Nessun giocatore espulso. Rosa al completo.")

time.sleep(1)
