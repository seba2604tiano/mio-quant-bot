import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# =====================================================================
# 1. CONFIGURAZIONE CONFIG E STILE DELLA PLATFORM
# =====================================================================
st.set_page_config(page_title="CORAZZATA QUANT v46.0", layout="wide", initial_sidebar_state="expanded")

# Inizializzazione degli Stati di Memoria Globali (Streamlit Session State)
if "SYSTEM_STATE" not in st.session_state:
    st.session_state.SYSTEM_STATE = "NORMAL"  # NORMAL, STORM_LOCK, SCOUT_MODE
if "STORM_TRIGGER_TICKER" not in st.session_state:
    st.session_state.STORM_TRIGGER_TICKER = None
if "LOG_TRADES" not in st.session_state:
    st.session_state.LOG_TRADES = []
if "TOTAL_PROFIT_USD" not in st.session_state:
    st.session_state.TOTAL_PROFIT_USD = 0.0
if "BOT_RUNNING" not in st.session_state:
    st.session_state.BOT_RUNNING = False
if "TRACKED_POSITIONS" not in st.session_state:
    st.session_state.TRACKED_POSITIONS = {} # Struttura per gestire i Trailing Stop Algoritmici

# Costanti di Sistema Rigide (Addio Slider, Parametri Dinamici)
MAX_SLOTS = 5
RISK_PER_TRADE_USD = 10.0
LOOKBACK_DAYS = 14
ATR_MULTIPLIER = 1.5

# Lista Asset Unificata (Crypto, Azioni, ETF)
ASSET_UNIVERSE = [
    # 🌟 CRIPTOVALUTE (Attive 24/7)
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "LINK-USD", "AVAX-USD", "DOGE-USD",
    
    # 🏎️ TECNOLOGIA & MOMENTUM (Wall Street)
    "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "NFLX", "AMD", "INTC", "QCOM",
    
    # 🔋 TITOLI COMPORTAMENTALI, FINTECH & EV
    "PLTR", "COIN", "MARA", "SMCI", "BABA", "SQ", "HOOD", "NIO",
    
    # 🛡️ ETF & MATERIE PRIME (Coperture macro)
    "SPY", "QQQ", "IWM", "DIA", "GLD", "SLV", "USO", "SMH", "ARKK", "XLE", "XBI", "TLT"
]
# Mapping per Alpaca (Rimuove il trattino per le crypto in esecuzione reale)
def clean_ticker_for_alpaca(ticker):
    return ticker.replace("-", "")

# =====================================================================
# 2. CONNESSIONE PROTETTA ALPACA
# =====================================================================
# Cerca le chiavi nei Secrets di Streamlit per evitare inserimenti manuali errati
try:
    ALPACA_API_KEY = st.secrets["ALPACA_API_KEY"]
    ALPACA_SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
    ALPACA_PAPER = st.secrets.get("ALPACA_PAPER", True)
    trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=ALPACA_PAPER)
    api_connected = True
except Exception as e:
    api_connected = False

# =====================================================================
# 3. MOTORE MATEMATICO: ANALISI ADATTIVA 14 GIORNI (DAILY)
# =====================================================================
def analyze_market_dynamics(ticker):
    """
    Scarica lo storico daily a 14 periodi e calcola la struttura matematica:
    ATR percentuale, Volume Medio, Volume Ratio e la EMA 9 di controllo.
    """
    try:
        # Scarica 40 giorni per essere sicuro di calcolare correttamente le medie a 14 periodi
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=40)
        df = yf.download(ticker, start=start_date, end=end_date, interval="1d", progress=False)
        
        if df.empty or len(df) < LOOKBACK_DAYS:
            return None
            
        # Calcolo True Range (TR) e Average True Range (ATR)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(window=LOOKBACK_DAYS).mean()
        
        # Struttura Dinamica %
        df['atr_pct'] = (df['atr'] / df['Close']) * 100
        df['vol_medio_14d'] = df['Volume'].rolling(window=LOOKBACK_DAYS).mean()
        df['volume_ratio'] = df['Volume'] / df['vol_medio_14d']
        df['ema_fast'] = df['Close'].ewm(span=9, adjust=False).mean()
        
        last_row = df.iloc[-1]
        return {
            "close": float(last_row['Close']),
            "atr_pct": float(last_row['atr_pct']),
            "volume_ratio": float(last_row['volume_ratio']),
            "ema_fast": float(last_row['ema_fast'])
        }
    except Exception:
        return None

# =====================================================================
# 4. LOGICA DEL COCKPIT: SELEZIONE MERITOCRATICA E SIZE ENGINERING
# =====================================================================
def scan_and_rank_signals():
    """
    Scansiona l'universo degli asset, estrae quelli con volumi insoliti
    e crea la classifica meritocratica per gli slot disponibili.
    """
    signals = []
    for asset in ASSET_UNIVERSE:
        data = analyze_market_dynamics(asset)
        if data is None:
            continue
            
        # Segnale Tecnico Base: Se l'asset ha un Volume Ratio > 1.0 (Volume sopra la media dei 14gg)
        # ed è in una fase di prezzo favorevole (es. sopra o vicino al supporto, qui simulato con Volume Ratio di spinta)
        if data['volume_ratio'] > 1.0:
            signals.append({
                "ticker": asset,
                "close": data['close'],
                "atr_pct": data['atr_pct'],
                "volume_ratio": data['volume_ratio'],
                "ema_fast": data['ema_fast']
            })
            
    # Classifica Meritocratica: Ordina per Volume Ratio Decrescente (Le mani forti più pesanti prima)
    ranked_signals = sorted(signals, key=lambda x: x['volume_ratio'], reverse=True)
    return ranked_signals

def execute_buy_order(asset_data, open_slots):
    """
    Calcola la size dinamica in base all'ATR ed esegue l'acquisto su Alpaca.
    Applica il protocollo Sonda se il sistema è in SCOUT_MODE.
    """
    ticker = asset_data['ticker']
    prezzo_attuale = asset_data['close']
    atr_pct = asset_data['atr_pct']
    
    # Calcolo Stop Loss Dinamico (Più l'asset oscilla, più si allarga il paracadute)
    stop_loss_dist_pct = atr_pct * ATR_MULTIPLIER
    
    # Calcolo della Taglia (Size Engineering) per mantenere il rischio fisso a $10
    size_in_quote = RISK_PER_TRADE_USD / (prezzo_attuale * (stop_loss_dist_pct / 100))
    budget_usd = size_in_quote * prezzo_attuale
    
    # Applicazione Cautelare del Protocollo Sonda
    current_mode = st.session_state.SYSTEM_STATE
    if current_mode == "SCOUT_MODE":
        size_in_quote = size_in_quote * 0.5
        budget_usd = budget_usd * 0.5
        
    alpaca_ticker = clean_ticker_for_alpaca(ticker)
    
    # Esecuzione Ordine Reale su Alpaca Client
    if api_connected:
        try:
            req = MarketOrderRequest(
                symbol=alpaca_ticker,
                qty=round(size_in_quote, 4) if "USD" in ticker else int(size_in_quote) if size_in_quote > 1 else 1,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC
            )
            trading_client.submit_order(order_data=req)
            
            # Registrazione nel tracciamento locale del Trailing Stop
            st.session_state.TRACKED_POSITIONS[ticker] = {
                "entry_price": prezzo_attuale,
                "highest_price": prezzo_attuale,
                "stop_price": prezzo_attuale * (1 - (stop_loss_dist_pct / 100)),
                "size": size_in_quote,
                "mode": current_mode,
                "time": datetime.datetime.now().strftime("%H:%M:%S")
            }
            return True
        except Exception as e:
            st.error(f"Errore nell'invio ordine per {ticker}: {str(e)}")
            return False
    return False

# =====================================================================
# 5. PROTEZIONE TEMPESTA & TRAILING STOP ATTIVO
# =====================================================================
def monitor_active_positions():
    """
    Monitora secondo per secondo le posizioni aperte.
    Aggiorna i Trailing Stop e se rileva un cross di stop-loss attiva il Fusibile della Tempesta.
    """
    tickers_to_remove = []
    
    for ticker, pos in list(st.session_state.TRACKED_POSITIONS.items()):
        # Prende l'ultimo prezzo aggiornato
        market_data = analyze_market_dynamics(ticker)
        if market_data is None:
            continue
            
        current_price = market_data['close']
        
        # Aggiornamento della vetta (Trailing Stop)
        if current_price > pos['highest_price']:
            st.session_state.TRACKED_POSITIONS[ticker]['highest_price'] = current_price
            # Trascina lo stop loss verso l'alto mantenendo la distanza calcolata all'inizio
            dist_pct = ((pos['entry_price'] - pos['stop_price']) / pos['entry_price'])
            st.session_state.TRACKED_POSITIONS[ticker]['stop_price'] = current_price * (1 - dist_pct)
            
        # Controllo della violazione dello Stop Loss (Preso in Caduta)
        if current_price <= pos['stop_price']:
            # Esecuzione Ordine di Vendita su Alpaca
            alpaca_ticker = clean_ticker_for_alpaca(ticker)
            if api_connected:
                try:
                    req = MarketOrderRequest(
                        symbol=alpaca_ticker,
                        qty=pos['size'],
                        side=OrderSide.SELL,
                        time_in_force=TimeInForce.GTC
                    )
                    trading_client.submit_order(order_data=req)
                except Exception:
                    pass
            
            # Calcolo profitto/perdita dell'operazione chiusa
            pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
            pnl_usd = (current_price - pos['entry_price']) * pos['size']
            
            st.session_state.TOTAL_PROFIT_USD += pnl_usd
            st.session_state.LOG_TRADES.append({
                "Orario": datetime.datetime.now().strftime("%H:%M:%S"),
                "Asset": ticker,
                "Profitto %": f"{pnl_pct:+.2f}%",
                "Profitto USD": f"${pnl_usd:+.2f}",
                "Tipo Chiusura": "TRAILING STOP" if pnl_pct > 0 else "STOP LOSS LOSS"
            })
            
            # SE LO STOP HA GENERATO UNA PERDITA -> ATTIVA IL FUSIBILE DELLA TEMPESTA
            if pnl_pct < 0:
                st.session_state.SYSTEM_STATE = "STORM_LOCK"
                st.session_state.STORM_TRIGGER_TICKER = ticker
                
            # Se il trade sonda ha avuto successo (chiuso in profitto), disattiva lo stato sonda
            if pos['mode'] == "SCOUT_MODE" and pnl_pct > 0:
                st.session_state.SYSTEM_STATE = "NORMAL"
                st.session_state.STORM_TRIGGER_TICKER = None
                
            tickers_to_remove.append(ticker)
            
    for t in tickers_to_remove:
        if t in st.session_state.TRACKED_POSITIONS:
            del st.session_state.TRACKED_POSITIONS[t]

def check_storm_clearance():
    """
    Rilevatore Intelligente di Cielo Sereno.
    Se l'asset che ha innescato il crash chiude sopra la sua EMA 9 Daily, la tempesta è finita.
    """
    if st.session_state.SYSTEM_STATE == "STORM_LOCK" and st.session_state.STORM_TRIGGER_TICKER:
        ticker = st.session_state.STORM_TRIGGER_TICKER
        data = analyze_market_dynamics(ticker)
        if data:
            if data['close'] > data['ema_fast']:
                st.session_state.SYSTEM_STATE = "SCOUT_MODE" # Passa al modulo di test leggero

# =====================================================================
# 6. INTERFACCIA UTENTE E DASHBOARD
# =====================================================================
# Header Principale
st.title("🛡️ CORAZZATA AUTONOMA ADATTIVA v46.0")
st.subheader("Architettura Quantistica di Protezione e Scalping Volumetrico")
st.markdown("---")

# Sezione Stato Connessione API
if not api_connected:
    st.error("⚠️ Chiavi Alpaca API mancanti o errate nel file secrets.toml. Il bot girerà in modalità Simulazione Totale.")
else:
    st.success("⚡ Connessione ad Alpaca Trading API stabilita con Successo. Sistemi di fuoco Armati.")

# Layout a Colonne per i Dati di Sintesi della Cassa
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("CASSA PROFITTI GLOBAL", f"${st.session_state.TOTAL_PROFIT_USD:+.2f}")
with col2:
    stato_attuale = st.session_state.SYSTEM_STATE
    if stato_attuale == "NORMAL":
        st.metric("STATO DEL SISTEMA", "🌤️ NORMALE / CACCIA")
    elif stato_attuale == "STORM_LOCK":
        st.metric("STATO DEL SISTEMA", f"🌪️ TEMPESTA ({st.session_state.STORM_TRIGGER_TICKER})", delta="BLOCCO ACQUISTI", delta_color="inverse")
    elif stato_attuale == "SCOUT_MODE":
        st.metric("STATO DEL SISTEMA", "🏹 MODULO SONDA", delta="SIZE DIMEZZATA")
with col3:
    occupati = len(st.session_state.TRACKED_POSITIONS)
    st.metric("SLOT OCCUPATI HANGAR", f"{occupati} / {MAX_SLOTS}")
with col4:
    win_trades = [t for t in st.session_state.LOG_TRADES if "-" not in t['Profitto %']]
    total_trades = len(st.session_state.LOG_TRADES)
    wr = (len(win_trades) / total_trades * 100) if total_trades > 0 else 0.0
    st.metric("WIN RATE SESSIONE", f"{wr:.1f}%", f"{total_trades} Operazioni Totali")

st.markdown("---")

# PANNELLO DI CONTROLLO MACRO
st.sidebar.title("🎛️ Pannello di Controllo")
btn_start = st.sidebar.button("🚀 ATTIVA ALGORITMO ADATTIVO", use_container_width=True)
btn_stop = st.sidebar.button("🛑 SPEGNI MOTORI", use_container_width=True)

if btn_start:
    st.session_state.BOT_RUNNING = True
if btn_stop:
    st.session_state.BOT_RUNNING = False

# LOOP DI ESECUZIONE CONTINUA INTERNA
if st.session_state.BOT_RUNNING:
    st.sidebar.info("🤖 L'automa è attivo e sta scansionando i 14 giorni storici...")
    
    # 1. Monitoraggio posizioni aperte e aggiornamento dei Trailing stop
    monitor_active_positions()
    
    # 2. Controllo sblocco della tempesta
    if st.session_state.SYSTEM_STATE == "STORM_LOCK":
        check_storm_clearance()
        
    # 3. Controllo degli acquisti se ci sono slot liberi e non siamo in blocco totale
    slots_occupati = len(st.session_state.TRACKED_POSITIONS)
    slots_liberi = MAX_SLOTS - slots_occupati
    
    if slots_liberi > 0 and st.session_state.SYSTEM_STATE != "STORM_LOCK":
        # Scansione e ordinamento meritocratico sui volumi
        segnali_rilevati = scan_and_rank_signals()
        # Filtra e seleziona i migliori in base agli slot liberi disponibili
        asset_da_comprare = segnali_rilevati[:slots_liberi]
        
        for asset in asset_da_comprare:
            # Controlla che l'asset non sia già in portafoglio
            if asset['ticker'] not in st.session_state.TRACKED_POSITIONS:
                execute_buy_order(asset, slots_liberi)
                
    # Piccola pausa tecnica per non sovraccaricare le chiamate API
    time.sleep(1)
    st.rerun()
else:
    st.sidebar.warning("💤 Sistemi spenti. Il Bot è in modalità vedetta passiva.")

# =====================================================================
# 7. VISUALIZZAZIONE TABELLONE DI BORDO (STILE v45.0 ENHANCED)
# =====================================================================
st.subheader("⚔️ L'Hangar delle Posizioni Attive (Massimo 5 Slot)")
if len(st.session_state.TRACKED_POSITIONS) > 0:
    pos_data = []
    for k, v in st.session_state.TRACKED_POSITIONS.items():
        pos_data.append({
            "Asset": k,
            "Prezzo Ingresso": f"${v['entry_price']:.2f}",
            "Picco Massimo Registrato": f"${v['highest_price']:.2f}",
            "Stop Loss Dinamico (Prezzo)": f"${v['stop_price']:.2f}",
            "Taglia Allocata": f"{v['size']:.5f}",
            "Modalità Ingresso": v['mode'],
            "Orario Apertura": v['time']
        })
    st.table(pd.DataFrame(pos_data))
else:
    st.info("Nessun caccia nell'hangar. Il bot sta scansionando i volumi per trovare ingressi istituzionali istituzionali.")

# DIARIO DI BORDO DI FINE GIORNATA (Richiesto: Report Pulito e Strutturato)
st.markdown("---")
with st.expander("📋 DIARIO DI BORDO GENERALE & REPORT DI FINE GIORNATA", expanded=True):
    if len(st.session_state.LOG_TRADES) > 0:
        st.dataframe(pd.DataFrame(st.session_state.LOG_TRADES), use_container_width=True)
    else:
        st.text("Nessun report compilato per oggi. Il bot invierà il bilancio totale alla chiusura delle sessioni.")
