import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

st.set_page_config(page_title="My Investment Hub AI", layout="wide", initial_sidebar_state="expanded")

st.title("🚀 My Investment Hub AI")
st.sidebar.header("Navigazione")
pagina = st.sidebar.radio("Seleziona uno strumento:", ["Analisi Titolo", "Il Ring (Confronto Titoli)", "Il Mio Portafoglio", "Calcolatore PAC", "Radar Crescita", "Cruscotto Macroeconomico", "Market News & AI Sentiment"])

# --- MOTORE DI FORMATTAZIONE NUMERI (STANDARD ITALIANO) ---
def formatta_numeri(val):
    try:
        if pd.isna(val):
            return ""
        val_float = float(val)
        if abs(val_float) >= 1000:
            return f"{val_float:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"{val_float:.4f}".replace(".", ",")
    except:
        return val

def fmt_2_decimali(x):
    try:
        return f"{float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return x

# --- IL MOTORE DEL CACHING ---
@st.cache_resource
def carica_ia():
    return SentimentIntensityAnalyzer()
analizzatore_ia = carica_ia()

@st.cache_data(ttl=3600)
def scarica_storico_prezzi(ticker):
    return yf.Ticker(ticker).history(period="2y")

@st.cache_data(ttl=3600)
def scarica_dati_bilancio(ticker):
    azienda = yf.Ticker(ticker)
    return azienda.info, azienda.financials.dropna(how='all'), azienda.balance_sheet.dropna(how='all')

# --- PAGINA 1: ANALISI TITOLO ---
if pagina == "Analisi Titolo":
    st.subheader("📊 Analisi Singola Azienda")
    ticker = st.text_input("Inserisci il codice dell'azienda (es. LDO.MI, RACE.MI, AAPL):", "AAPL")
    
    if ticker:
        ticker = ticker.upper().strip()
        with st.spinner("Estrazione dati ottimizzata in corso..."):
            info, financials, balance_sheet = scarica_dati_bilancio(ticker)
            storico = scarica_storico_prezzi(ticker)
            
        st.header(f"{info.get('longName', ticker)}")
        
        col1, col2, col3 = st.columns(3)
        prezzo_val = info.get('currentPrice', 0)
        col1.metric("Prezzo Attuale", f"{fmt_2_decimali(prezzo_val)} {info.get('currency', 'EUR')}")
        
        pe_val = info.get('trailingPE', 'N/D')
        col2.metric("P/E Ratio", fmt_2_decimali(pe_val) if pe_val != 'N/D' else 'N/D')
        
        roe = info.get('returnOnEquity', 0)
        col3.metric("ROE (%)", f"{(roe * 100):.2f}%".replace(".", ",") if roe else "N/D")
        
        st.divider()
        
        st.subheader("📈 Analisi Tecnica: Prezzo e Medie Mobili")
        col_sma1, col_sma2 = st.columns(2)
        with col_sma1: mostra_sma50 = st.checkbox("🟡 Mostra Media Mobile 50 giorni")
        with col_sma2: mostra_sma200 = st.checkbox("🟣 Mostra Media Mobile 200 giorni")

        if not storico.empty:
            storico['SMA_50'] = storico['Close'].rolling(window=50).mean()
            storico['SMA_200'] = storico['Close'].rolling(window=200).mean()
            fig_prezzo = go.Figure(data=[go.Candlestick(x=storico.index, open=storico['Open'], high=storico['High'], low=storico['Low'], close=storico['Close'], name='Prezzo', increasing_line_color='#2ecc71', decreasing_line_color='#e74c3c')])
            
            if mostra_sma50: fig_prezzo.add_trace(go.Scatter(x=storico.index, y=storico['SMA_50'], mode='lines', name='SMA 50', line=dict(color='#f1c40f', width=2)))
            if mostra_sma200: fig_prezzo.add_trace(go.Scatter(x=storico.index, y=storico['SMA_200'], mode='lines', name='SMA 200', line=dict(color='#9b59b6', width=2)))

            fig_prezzo.update_layout(xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), height=500, template="plotly_dark")
            st.plotly_chart(fig_prezzo, use_container_width=True)
        
        st.divider()

        st.subheader("⚖️ Salute Finanziaria Rapida")
        c_bar, c_pie = st.columns(2)
        with c_bar:
            st.write("**Fatturato vs Utile Netto**")
            try:
                df_fin = financials.T[['Total Revenue', 'Net Income']].dropna()
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(x=df_fin.index.year, y=df_fin['Total Revenue'], name='Fatturato', marker_color='#3498db'))
                fig_bar.add_trace(go.Bar(x=df_fin.index.year, y=df_fin['Net Income'], name='Utile Netto', marker_color='#2ecc71'))
                fig_bar.update_layout(barmode='group', template='plotly_dark', margin=dict(l=0, r=0, t=30, b=0), height=300)
                st.plotly_chart(fig_bar, use_container_width=True)
            except: st.info("Grafico di bilancio non disponibile.")

        with c_pie:
            st.write("**Rischio Aziendale (Debito vs Patrimonio)**")
            
            debito = info.get('totalDebt', 0)
            patrimonio = info.get('totalStockholderEquity', 0)
            
            try:
                if (patrimonio == 0 or pd.isna(patrimonio)) and not balance_sheet.empty:
                    for voce in ['Stockholders Equity', 'Common Stock Equity', 'Total Equity Gross Minority Interest']:
                        if voce in balance_sheet.index:
                            patrimonio = balance_sheet.loc[voce].iloc[0]
                            break
                            
                if (debito == 0 or pd.isna(debito)) and not balance_sheet.empty:
                    if 'Total Debt' in balance_sheet.index:
                        debito = balance_sheet.loc['Total Debt'].iloc[0]
            except:
                pass
                
            debito = 0 if pd.isna(debito) else debito
            patrimonio = 0 if pd.isna(patrimonio) else patrimonio

            if debito > 0 or patrimonio > 0:
                fig_pie = go.Figure(data=[go.Pie(labels=['Debito', 'Patrimonio Netto'], values=[debito, patrimonio], hole=.5, marker_colors=['#e74c3c', '#2ecc71'])])
                fig_pie.update_layout(template='plotly_dark', margin=dict(l=0, r=0, t=30, b=0), height=300)
                st.plotly_chart(fig_pie, use_container_width=True)
            else: 
                st.info("Dati sui debiti o patrimonio non disponibili al momento.")

        st.divider()
        st.subheader("📚 Analisi di Bilancio Avanzata")
        
        # --- IL MEGA DIZIONARIO ITALIANO ---
        dizionario_oic = {
            # --- CONTO ECONOMICO ---
            "Total Revenue": "A) VALORE DELLA PRODUZIONE (Ricavi Totali)",
            "Operating Revenue": "   Ricavi delle Vendite e Prestazioni",
            "Cost Of Revenue": "B) COSTI DELLA PRODUZIONE (Materie e Servizi)",
            "Gross Profit": "📊 MARGINE LORDO INDUSTRIALE",
            "Operating Expense": "   Spese di Struttura e Amministrative",
            "Selling General And Administration": "   Spese Generali, Amministrative e di Vendita",
            "Research And Development": "   Ricerca e Sviluppo",
            "Operating Income": "🔴 RISULTATO OPERATIVO (EBIT)",
            "Net Non Operating Interest Income Expense": "C) PROVENTI E ONERI FINANZIARI NETTI",
            "Interest Expense": "   Oneri Finanziari (Interessi Passivi)",
            "Interest Expense Non Operating": "   Interessi Passivi Extra-Operativi",
            "Interest Income": "   Proventi Finanziari (Interessi Attivi)",
            "Interest Income Non Operating": "   Interessi Attivi Extra-Operativi",
            "Net Interest Income": "   Margine di Interesse Netto",
            "Other Income Expense": "   Altri Proventi e Oneri",
            "Pretax Income": "📈 RISULTATO ANTE IMPOSTE (EBT)",
            "Tax Provision": "20) Imposte sul Reddito d'Esercizio",
            "Net Income": "🏆 21) UTILE (PERDITA) DELL'ESERCIZIO",
            "Net Income Continuous Operations": "   Utile da Attività in Continuità",
            "Net Income From Continuing And Discontinued Operation": "   Utile da Tutte le Operazioni",
            "Net Income Common Stockholders": "   Utile Netto per gli Azionisti Ordinari",
            "Diluted NI Available to Com Stockholders": "   Utile Netto Disponibile (Diluito)",
            "Total Unusual Items": "   Totale Voci Straordinarie",
            "Total Unusual Items Excluding Taxes": "   Voci Straordinarie (Senza Imposte)",
            "Tax Effect Of Unusual Items": "   Effetto Fiscale sulle Voci Straordinarie",
            "Tax Rate For Calcs": "   Aliquota Fiscale Applicata",
            "Normalized EBITDA": "   EBITDA Normalizzato",
            "EBITDA": "   EBITDA (Margine Operativo Lordo)",
            "EBIT": "   EBIT (Risultato Operativo)",
            "Reconciled Depreciation": "   Ammortamenti e Svalutazioni Riconciliati",
            "Reconciled Cost Of Revenue": "   Costo del Venduto Riconciliato",
            "Basic EPS": "   Utile per Azione (EPS) Base",
            "Diluted EPS": "   Utile per Azione (EPS) Diluito",
            "Basic Average Shares": "   Numero Medio di Azioni (Base)",
            "Diluted Average Shares": "   Numero Medio di Azioni (Diluite)",
            "Total Expenses": "   Costi Totali",
            "Total Operating Income As Reported": "   Risultato Operativo Dichiarato",

            # --- STATO PATRIMONIALE ---
            "Total Assets": "👑 TOTALE ATTIVO PATRIMONIALE",
            "Total Non Current Assets": "B) IMMOBILIZZAZIONI TOTALI (Attivo Fisso)",
            "Net PPE": "   Immobilizzazioni Materiali (Impianti/Macchinari)",
            "Gross PPE": "   Immobilizzazioni Materiali Lorde",
            "Accumulated Depreciation": "   Fondo Ammortamento",
            "Leases": "   Contratti di Leasing",
            "Machinery Furniture Equipment": "   Macchinari, Arredi ed Attrezzature",
            "Buildings And Improvements": "   Fabbricati e Migliorie",
            "Land And Improvements": "   Terreni e Migliorie",
            "Properties": "   Proprietà Immobiliari",
            "Goodwill": "   Immobilizzazioni Immateriali (Avviamento)",
            "Other Intangible Assets": "   Altre Attività Immateriali",
            "Goodwill And Other Intangible Assets": "   Avviamento e Altri Intangibili",
            "Available For Sale Securities": "   Titoli Disponibili per la Vendita",
            "Investmentin Financial Assets": "   Investimenti in Attività Finanziarie",
            "Investments And Advances": "   Investimenti e Anticipi",
            "Other Investments": "   Altri Investimenti",
            "Other Non Current Assets": "   Altre Attività a Lungo Termine",
            
            "Current Assets": "C) ATTIVO CIRCOLANTE TOTALE",
            "Cash And Cash Equivalents": "   Disponibilità Liquide (Cassa e Banche)",
            "Cash Equivalents": "   Equivalenti di Cassa",
            "Cash Financial": "   Cassa e Strumenti Finanziari",
            "Other Short Term Investments": "   Altri Investimenti a Breve Termine",
            "Inventory": "   Rimanenze (Magazzino)",
            "Receivables": "   Crediti Commerciali ed Altri Crediti",
            "Accounts Receivable": "   Crediti verso Clienti",
            "Other Receivables": "   Altri Crediti Correnti",
            "Other Current Assets": "   Altre Attività Correnti",
            
            "Total Equity Gross Minority Interest": "TOTALE FONTI (Patrimonio Netto e Minoranze)",
            "Stockholders Equity": "A) PATRIMONIO NETTO TOTALE",
            "Retained Earnings": "   Riserve e Utili Portati a Nuovo",
            "Capital Stock": "   Capitale Azionario",
            "Common Stock": "   Azioni Ordinarie",
            "Common Stock Equity": "   Capitale Sociale Azioni Ordinarie",
            "Accumulated Other Comprehensive Income": "   Altre Componenti di Conto Economico Complessivo",
            
            "Total Liabilities Net Minority Interest": "TOTALE PASSIVITÀ (Debiti Totali)",
            "Total Non Current Liabilities Net Minority Interest": "D) Debiti a Medio/Lungo Termine Totali",
            "Long Term Debt": "   Debiti Finanziari Oltre i 12 Mesi",
            "Long Term Debt And Capital Lease Obligation": "   Debiti e Leasing a Lungo Termine",
            "Non Current Deferred Taxes Liabilities": "   Passività Fiscali Differite (Lungo Termine)",
            "Other Non Current Liabilities": "   Altre Passività a Lungo Termine",
            
            "Current Liabilities": "E) Debiti a Breve Termine Totali",
            "Accounts Payable": "   Debiti verso Fornitori (Entro i 12 Mesi)",
            "Payables": "   Debiti Commerciali",
            "Payables And Accrued Expenses": "   Debiti e Ratei Passivi",
            "Current Accrued Expenses": "   Ratei Passivi Correnti",
            "Current Debt": "   Debito a Breve Termine",
            "Current Debt And Capital Lease Obligation": "   Debiti e Leasing a Breve Termine",
            "Current Deferred Liabilities": "   Passività Differite Correnti",
            "Current Deferred Revenue": "   Ricavi Differiti Correnti",
            "Pensionand Other Post Retirement Benefit Plans Current": "   Fondi Pensione Correnti",
            "Other Current Liabilities": "   Altre Passività a Breve Termine",
            
            "Treasury Shares Number": "   Numero Azioni Proprie",
            "Ordinary Shares Number": "   Numero Azioni Ordinarie",
            "Share Issued": "   Azioni Emesse",
            "Total Debt": "   Debito Totale Generale",
            "Net Debt": "   Indebitamento Finanziario Netto",
            "Tangible Book Value": "   Valore Contabile Tangibile",
            "Net Tangible Assets": "   Attivo Tangibile Netto",
            "Working Capital": "   Capitale Circolante Netto",
            "Invested Capital": "   Capitale Investito",
            "Capital Lease Obligations": "   Obbligazioni per Leasing Finanziari",
            "Total Capitalization": "   Capitalizzazione Totale"
        }
        
        ordine_ce = [
            "Total Revenue", "Operating Revenue", "Cost Of Revenue", "Gross Profit", 
            "Operating Expense", "Operating Income", "Net Non Operating Interest Income Expense", 
            "Interest Expense", "Interest Income", "Pretax Income", "Tax Provision", 
            "Net Income", "Diluted NI Available to Com Stockholders"
        ]
        
        ordine_sp = [
            "Total Assets", "Total Non Current Assets", "Net PPE", "Goodwill", 
            "Current Assets", "Cash And Cash Equivalents", "Inventory", "Receivables", 
            "Total Equity Gross Minority Interest", "Stockholders Equity", "Retained Earnings", 
            "Total Liabilities Net Minority Interest", "Total Non Current Liabilities Net Minority Interest", 
            "Long Term Debt", "Current Liabilities", "Accounts Payable"
        ]
        
        # --- TRADUTTORE AUTOMATICO DI EMERGENZA ---
        def traduttore_dinamico(testo):
            sostituzioni = {
                "Total": "Totale", "Other": "Altre", "Current": "Correnti", "Non Current": "Non Correnti",
                "Assets": "Attività", "Liabilities": "Passività", "Net": "Netto", "Debt": "Debito",
                "Revenue": "Ricavi", "Expense": "Spese", "Income": "Reddito", "And": "e", "Of": "di",
                "Taxes": "Imposte", "Tax": "Imposta", "Deferred": "Differite", "Operating": "Operativo",
                "Financial": "Finanziari", "Cash": "Cassa", "Receivables": "Crediti", "Payables": "Debiti",
                "Equity": "Patrimonio", "Stock": "Azioni", "Shares": "Azioni", "Average": "Media", "Value": "Valore"
            }
            nuovo_testo = str(testo)
            for eng, ita in sostituzioni.items():
                nuovo_testo = nuovo_testo.replace(eng, ita)
            return f"   {nuovo_testo} *"

        def applica_ordine_e_traduzione_oic(df, ordine_ideale):
            # 1. Dividiamo le voci principali (da mettere in cima) e quelle secondarie
            presenti = [r for r in ordine_ideale if r in df.index]
            rimanenti = [r for r in df.index if r not in ordine_ideale]
            df_ordinato = df.loc[presenti + rimanenti]
            
            # 2. Creiamo una mappa dinamica per TUTTE le righe del file
            mappa_finale = {}
            for riga in df_ordinato.index:
                if riga in dizionario_oic:
                    mappa_finale[riga] = dizionario_oic[riga]
                else:
                    mappa_finale[riga] = traduttore_dinamico(riga)
                    
            return df_ordinato.rename(index=mappa_finale)

        tab_ce, tab_sp = st.tabs(["Conto Economico", "Stato Patrimoniale"])
        with tab_ce:
            try: 
                ce_italiano = applica_ordine_e_traduzione_oic(financials, ordine_ce)
                st.dataframe(ce_italiano.style.format(formatta_numeri), use_container_width=True)
            except: st.warning("Conto Economico non reperibile.")
        with tab_sp:
            try:
                if 'Current Assets' in balance_sheet.index and 'Current Liabilities' in balance_sheet.index:
                    attivi, passivita = balance_sheet.loc['Current Assets'].iloc[0], balance_sheet.loc['Current Liabilities'].iloc[0]
                    if passivita > 0: 
                        ratio_formattato = f"{(attivi / passivita):.2f}".replace(".", ",")
                        st.info(f"💡 **Indice di Liquidità (Current Ratio): {ratio_formattato}**")
                
                sp_italiano = applica_ordine_e_traduzione_oic(balance_sheet, ordine_sp)
                st.dataframe(sp_italiano.style.format(formatta_numeri), use_container_width=True)
            except: st.warning("Stato Patrimoniale non reperibile.")

        # --- SEZIONE: LA MACCHINA DEI DIVIDENDI ---
        st.divider()
        st.subheader("💸 Storico Dividendi e Rendimento")
        
        with st.spinner("Estrazione storico dividendi in corso..."):
            try:
                azienda = yf.Ticker(ticker)
                dividendi = azienda.dividends
                
                if not dividendi.empty:
                    try:
                        div_annuali = dividendi.resample('YE').sum()
                    except:
                        div_annuali = dividendi.resample('Y').sum()
                        
                    div_annuali.index = div_annuali.index.year
                    
                    storia_recente = azienda.history(period="1d")
                    prezzo_att = storia_recente['Close'].iloc[-1] if not storia_recente.empty else 0
                    
                    ultimo_div = div_annuali.iloc[-1]
                    div_yield = (ultimo_div / prezzo_att * 100) if prezzo_att > 0 else 0
                    
                    col_d1, col_d2 = st.columns([1, 3])
                    
                    with col_d1:
                        st.metric("Ultimo Dividendo Annuale", fmt_2_decimali(ultimo_div))
                        st.metric("Dividend Yield (Stimato)", f"{div_yield:.2f}%".replace(".", ","))
                        st.info("Un Dividend Yield alto indica un buon ritorno sul capitale, ma va confrontato con la sostenibilità dell'azienda.")
                        
                    with col_d2:
                        fig_div = go.Figure(data=[go.Bar(x=div_annuali.index, y=div_annuali.values, marker_color='#f1c40f')])
                        fig_div.update_layout(title="Dividendi Totali Pagati per Anno", template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0), height=300)
                        st.plotly_chart(fig_div, use_container_width=True)
                else:
                    st.info("Questa azienda non distribuisce dividendi (oppure i dati non sono al momento disponibili).")
            except Exception as e:
                st.error(f"Errore tecnico individuato: {e}")

# --- PAGINA NUOVA: IL RING (CONFRONTO TITOLI) ---
elif pagina == "Il Ring (Confronto Titoli)":
    st.header("🥊 Il Ring: Confronto Titoli")
    st.write("Confronta due o più aziende normalizzando il prezzo (Base 100). Scopri chi ha performato meglio a parità di capitale investito iniziale.")

    col_t1, col_t2, col_periodo = st.columns(3)
    with col_t1: ticker1 = st.text_input("Sfidante 1 (es. RACE.MI, TSLA):", "TSLA").upper()
    with col_t2: ticker2 = st.text_input("Sfidante 2 (es. STLA.MI, F):", "F").upper()
    with col_periodo: periodo = st.selectbox("Orizzonte temporale:", ["1y", "2y", "5y", "max"], index=1)

    if st.button("Avvia Sfida"):
        with st.spinner("Preparazione del Ring in corso..."):
            try:
                dati1 = yf.Ticker(ticker1).history(period=periodo)
                dati2 = yf.Ticker(ticker2).history(period=periodo)

                if not dati1.empty and not dati2.empty:
                    dati1['Norm'] = (dati1['Close'] / dati1['Close'].iloc[0]) * 100
                    dati2['Norm'] = (dati2['Close'] / dati2['Close'].iloc[0]) * 100

                    fig_ring = go.Figure()
                    fig_ring.add_trace(go.Scatter(x=dati1.index, y=dati1['Norm'], mode='lines', name=ticker1, line=dict(color='#3498db', width=2.5)))
                    fig_ring.add_trace(go.Scatter(x=dati2.index, y=dati2['Norm'], mode='lines', name=ticker2, line=dict(color='#e74c3c', width=2.5)))

                    fig_ring.update_layout(title=f"Testa a Testa: {ticker1} vs {ticker2} ({periodo})", template="plotly_dark", yaxis_title="Valore (Partenza a 100)", margin=dict(l=0, r=0, t=40, b=0), height=450)
                    st.plotly_chart(fig_ring, use_container_width=True)

                    perf1 = ((dati1['Close'].iloc[-1] - dati1['Close'].iloc[0]) / dati1['Close'].iloc[0]) * 100
                    perf2 = ((dati2['Close'].iloc[-1] - dati2['Close'].iloc[0]) / dati2['Close'].iloc[0]) * 100

                    vincitore = ticker1 if perf1 > perf2 else ticker2
                    st.success(f"🏆 Il vincitore del periodo è **{vincitore}**!")

                    c1, c2 = st.columns(2)
                    c1.metric(f"Performance Storica {ticker1}", f"{perf1:.2f}%".replace(".", ","))
                    c2.metric(f"Performance Storica {ticker2}", f"{perf2:.2f}%".replace(".", ","))
                else:
                    st.error("Dati non trovati. Controlla che i Ticker siano corretti (aggiungi .MI per le italiane).")
            except Exception as e:
                st.error("Si è verificato un errore di connessione con i mercati.")

# --- PAGINA 2: IL MIO PORTAFOGLIO ---
elif pagina == "Il Mio Portafoglio":
    st.header("💼 Il Mio Portafoglio Tracker")
    if 'titoli_salvati' not in st.session_state:
        st.session_state['titoli_salvati'] = pd.DataFrame(columns=["Ticker", "Quantità", "Prezzo_di_Carico"])

    with st.expander("➕ Aggiungi un nuovo Asset al Portafoglio", expanded=True):
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1: nuovo_ticker = st.text_input("Ticker (es. AAPL, VWCE.DE, BTC-USD)")
        with col2: nuova_quantita = st.number_input("Quantità", min_value=0.01, value=1.00, step=0.1)
        with col3: nuovo_prezzo = st.number_input("Prezzo Acquisto", min_value=0.01, value=100.0, step=10.0)
        with col4:
            st.write(""); st.write("")
            if st.button("Salva nel Portafoglio"):
                if nuovo_ticker:
                    nuova_riga = pd.DataFrame({"Ticker": [nuovo_ticker.upper()], "Quantità": [nuova_quantita], "Prezzo_di_Carico": [nuovo_prezzo]})
                    st.session_state['titoli_salvati'] = pd.concat([st.session_state['titoli_salvati'], nuova_riga], ignore_index=True)
                    st.rerun() 

    if not st.session_state['titoli_salvati'].empty:
        df_grezzo = st.session_state['titoli_salvati'].copy()
        df_grezzo['Capitale_Speso'] = df_grezzo['Quantità'] * df_grezzo['Prezzo_di_Carico']
        
        df_portafoglio = df_grezzo.groupby('Ticker').agg(
            Quantità=('Quantità', 'sum'),
            Capitale_Investito=('Capitale_Speso', 'sum')
        ).reset_index()
        
        df_portafoglio['Prezzo_di_Carico'] = df_portafoglio['Capitale_Investito'] / df_portafoglio['Quantità']
        
        prezzi_attuali = []
        with st.spinner("Aggiornamento prezzi ultra-rapido..."):
            for ticker in df_portafoglio['Ticker']:
                try:
                    storia_prezzi = scarica_storico_prezzi(ticker)
                    if not storia_prezzi.empty: prezzi_attuali.append(storia_prezzi['Close'].iloc[-1])
                    else: prezzi_attuali.append(0)
                except: prezzi_attuali.append(0) 
        
        df_portafoglio['Prezzo_Attuale'] = prezzi_attuali
        df_portafoglio['Valore_Attuale'] = df_portafoglio['Quantità'] * df_portafoglio['Prezzo_Attuale']
        df_portafoglio['Profitti/Perdite'] = df_portafoglio['Valore_Attuale'] - df_portafoglio['Capitale_Investito']
        df_portafoglio['Rendimento (%)'] = df_portafoglio.apply(lambda row: (row['Profitti/Perdite'] / row['Capitale_Investito'] * 100) if row['Capitale_Investito'] > 0 else 0, axis=1)

        totale_investito = df_portafoglio['Capitale_Investito'].sum()
        totale_attuale = df_portafoglio['Valore_Attuale'].sum()
        profitto_totale = df_portafoglio['Profitti/Perdite'].sum()
        rendimento_totale_perc = (profitto_totale / totale_investito) * 100 if totale_investito > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Totale Investito", f"{fmt_2_decimali(totale_investito)} €")
        c2.metric("📈 Valore Attuale", f"{fmt_2_decimali(totale_attuale)} €", f"{fmt_2_decimali(profitto_totale)} € ({rendimento_totale_perc:.2f}%)".replace(".", ","))
        c3.metric("🛒 Asset Diversi in Portafoglio", len(df_portafoglio))

        df_vis = df_portafoglio[['Ticker', 'Quantità', 'Prezzo_di_Carico', 'Prezzo_Attuale', 'Capitale_Investito', 'Valore_Attuale', 'Profitti/Perdite', 'Rendimento (%)']]

        st.dataframe(df_vis.style.format({
            "Quantità": lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "Prezzo_di_Carico": lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "Prezzo_Attuale": lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "Capitale_Investito": lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "Valore_Attuale": lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "Profitti/Perdite": lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "Rendimento (%)": lambda x: f"{x:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
        }), use_container_width=True)

        if totale_attuale > 0:
            fig_diversificazione = go.Figure(data=[go.Pie(labels=df_vis['Ticker'], values=df_vis['Valore_Attuale'], hole=.4)])
            fig_diversificazione.update_layout(template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0), height=350)
            st.plotly_chart(fig_diversificazione, use_container_width=True)

        if st.button("🗑️ Svuota Portafoglio"):
            st.session_state['titoli_salvati'] = pd.DataFrame(columns=["Ticker", "Quantità", "Prezzo_di_Carico"])
            st.rerun()

# --- PAGINA 3: CALCOLATORE PAC ---
elif pagina == "Calcolatore PAC":
    st.header("🧮 Simulatore Piano di Accumulo (PAC)")
    col1, col2 = st.columns(2)
    with col1: deposito_mensile = st.number_input("Versamento mensile (€)", value=100, step=10)
    with col1: anni = st.slider("Durata investimento (Anni)", 1, 40, 20)
    with col2: rendimento_annuo = st.slider("Rendimento annuo stimato (%)", 1.0, 15.0, 7.0)
        
    mesi = anni * 12
    tasso_mensile = (1 + rendimento_annuo/100)**(1/12) - 1
    montante_finale = deposito_mensile * ((1 + tasso_mensile)**mesi - 1) / tasso_mensile
    capitale_versato = deposito_mensile * mesi
    tasse_da_pagare = (montante_finale - capitale_versato) * 0.26
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Capitale Versato", f"{capitale_versato:,}".replace(",", ".") + " €")
    c2.metric("Tasse stimate (26%)", f"{fmt_2_decimali(tasse_da_pagare)} €")
    c3.metric("Netto Finale", f"{fmt_2_decimali(montante_finale - tasse_da_pagare)} €")

# --- PAGINA 4: RADAR CRESCITA ---
elif pagina == "Radar Crescita":
    st.header("🚀 Radar Crescita")
    col1, col2 = st.columns(2)
    with col1: roe_minimo = st.slider("ROE Minimo (%)", 0, 30, 15)
    with col2: pe_massimo = st.slider("P/E Massimo", 10, 50, 25)
        
    aziende_test = ["LDO.MI", "RACE.MI", "AAPL", "NVDA", "MSFT", "TSLA"]
    tabella_dati = []
    
    with st.spinner("Analisi in corso..."):
        for t in aziende_test:
            az = yf.Ticker(t)
            inf = az.info
            r = inf.get('returnOnEquity', 0)
            r_percent = (r * 100) if r else 0
            pe = inf.get('trailingPE', 999) 
            if r_percent >= roe_minimo and pe <= pe_massimo:
                prezzo_val = inf.get('currentPrice', 0)
                prezzo_fmt = f"{fmt_2_decimali(prezzo_val)} {inf.get('currency', 'EUR')}"
                pe_fmt = fmt_2_decimali(pe) if pe != 999 else "N/D"
                roe_fmt = f"{r_percent:.2f}%".replace(".", ",")
                
                tabella_dati.append({
                    "Ticker": t, 
                    "Azienda": inf.get('longName', t), 
                    "Prezzo": prezzo_fmt, 
                    "P/E": pe_fmt, 
                    "ROE (%)": roe_fmt
                })
                
    if tabella_dati: 
        df_visualizzazione = pd.DataFrame(tabella_dati)
        st.dataframe(df_visualizzazione, use_container_width=True)
        csv = df_visualizzazione.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Scarica in formato Excel (CSV)", data=csv, file_name='radar_crescita_aziende.csv', mime='text/csv')
    else: 
        st.warning("Nessuna azienda soddisfa i filtri.")

# --- PAGINA 5: CRUSCOTTO MACROECONOMICO ---
elif pagina == "Cruscotto Macroeconomico":
    st.header("🌍 Cruscotto Macroeconomico")
    st.write("Monitora i polsi dell'economia globale in tempo reale. I dati mostrano la chiusura attuale e la variazione percentuale rispetto al giorno precedente.")

    macro_tickers = {
        "S&P 500 (Azionario)": "^GSPC",
        "Oro (Beni Rifugio)": "GC=F",
        "Petrolio WTI (Energia)": "CL=F",
        "Cambio EUR/USD": "EURUSD=X",
        "T-Bond 10Y (Tassi)": "^TNX"
    }

    with st.spinner("Lettura dei dati globali in corso..."):
        cols = st.columns(len(macro_tickers))
        
        for i, (nome, ticker) in enumerate(macro_tickers.items()):
            try:
                dati = yf.Ticker(ticker).history(period="5d")
                if not dati.empty and len(dati) >= 2:
                    chiusura_oggi = dati['Close'].iloc[-1]
                    chiusura_ieri = dati['Close'].iloc[-2]
                    delta_perc = ((chiusura_oggi - chiusura_ieri) / chiusura_ieri) * 100
                    
                    valore_formattato = f"{fmt_2_decimali(chiusura_oggi)}%" if ticker == "^TNX" else fmt_2_decimali(chiusura_oggi)
                    delta_formattato = f"{delta_perc:.2f}%".replace(".", ",")
                    
                    cols[i].metric(nome.split(" (")[0], valore_formattato, delta_formattato)
                else:
                    cols[i].metric(nome.split(" (")[0], "N/D")
            except:
                cols[i].metric(nome.split(" (")[0], "Errore")

    st.divider()
    
    st.subheader("📈 Analisi del Trend (Ultimo Anno)")
    selettore_trend = st.selectbox("Seleziona l'indicatore per vederne l'andamento storico:", list(macro_tickers.keys()))

    if selettore_trend:
        ticker_scelto = macro_tickers[selettore_trend]
        with st.spinner("Generazione grafico..."):
            storico_macro = yf.Ticker(ticker_scelto).history(period="1y")
            
            if not storico_macro.empty:
                colore_linea = '#2ecc71' if storico_macro['Close'].iloc[-1] >= storico_macro['Close'].iloc[0] else '#e74c3c'
                
                fig_macro = go.Figure(data=[go.Scatter(x=storico_macro.index, y=storico_macro['Close'], mode='lines', fill='tozeroy', line=dict(color=colore_linea, width=2))])
                fig_macro.update_layout(title=f"Andamento {selettore_trend} (1 Anno)", template="plotly_dark", margin=dict(l=0, r=0, t=40, b=0), height=400)
                st.plotly_chart(fig_macro, use_container_width=True)
            else:
                st.warning("Dati storici non disponibili al momento.")

# --- PAGINA 6: MARKET NEWS & AI SENTIMENT ---
elif pagina == "Market News & AI Sentiment":
    st.header("🧠 Analisi Sentiment delle News con IA")
    ticker_news = st.text_input("Cerca le notizie per l'azienda (es. TSLA, AAPL):", "TSLA")
    
    if ticker_news:
        with st.spinner("L'IA sta leggendo le notizie..."):
            notizie = yf.Ticker(ticker_news).news
            if notizie:
                for notizia in notizie[:6]: 
                    if 'content' in notizia:
                        titolo, editore, link = notizia['content'].get('title', 'Titolo N/D'), notizia['content'].get('provider', {}).get('displayName', 'Fonte N/D'), notizia['content'].get('canonicalUrl', {}).get('url', '#')
                    else:
                        titolo, editore, link = notizia.get('title', 'Titolo N/D'), notizia.get('publisher', 'Fonte N/D'), notizia.get('link', '#')
                    
                    punteggio_ia = analizzatore_ia.polarity_scores(titolo)['compound']
                    if punteggio_ia > 0.05: etichetta_sentiment = "🟢 **POSITIVO**"
                    elif punteggio_ia < -0.05: etichetta_sentiment = "🔴 **NEGATIVO**"
                    else: etichetta_sentiment = "⚪ **NEUTRALE**"
                    
                    with st.container():
                        st.markdown(f"#### [{titolo}]({link})")
                        st.write(f"**Giudizio IA:** {etichetta_sentiment} | 🗞️ Fonte: {editore}")
                        st.divider()
            else:
                st.warning("Nessuna notizia trovato.")