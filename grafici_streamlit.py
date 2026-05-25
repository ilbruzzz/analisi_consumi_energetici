import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
import os
import holidays
from dotenv import load_dotenv

# CONFIGURAZIONE INIZIALE STREAMLIT E TEMA
st.set_page_config(layout="wide", page_title="Analisi Consumi")

tema_selezionato = st.sidebar.radio("Tema Grafici (adattamento testi)", ["Scuro (Dark Mode)", "Chiaro (Light Mode)"])

#impostazione dei colori per i grafici in base al tema scelto
if tema_selezionato == "Scuro (Dark Mode)":
    colore_testo = "#E0E0E0"
    colore_griglia = "#333333"
else:
    colore_testo = "#1A1A1A"
    colore_griglia = "#E2E8F0"

sns.set_theme(style="whitegrid", rc={
    "axes.spines.right": False,
    "axes.spines.top": False,
    "figure.facecolor": "none",
    "axes.facecolor": "none",
    "text.color": colore_testo,
    "axes.labelcolor": colore_testo,
    "xtick.color": colore_testo,
    "ytick.color": colore_testo,
    "grid.color": colore_griglia
})
plt.rcParams['font.family'] = 'sans-serif'

# GESTIONE VARIABILI D'AMBIENTE (COSTI E FILE)
# carice confihiamo le configurazioni salvate nel file .env
load_dotenv() 

# fallback su default se non presenti
FILE_PULITO = os.getenv("FILE_PULITO")
FILE_GREEND_NORMALIZZATO = os.getenv("FILE_GREEND_NORMALIZZATO", "dataset_GREEND_normalizzato.csv")
MIX_ENERGICO = os.getenv("EXPORT_MIX_ENERGETICO_NAZIONALE")

# calcolo dei costi dell'energia
COSTO_FISSO_ENV = os.getenv("COSTO_FISSO", "0")
COSTO_FISSO = float(COSTO_FISSO_ENV) if COSTO_FISSO_ENV.strip() else 0.0
COSTO_KWH = float(os.getenv("COSTO", "0.204730")) # Costo base al kWh preso da bolletta personale

if COSTO_FISSO == 0:
    costoReale = COSTO_KWH
else:
    convertiCostoFisso = COSTO_FISSO / 1000
    costoReale = COSTO_KWH + convertiCostoFisso

# costi specifici per le fasce orarie italiane (F1, F2, F3). Se non esistono nel .env, usano il costo base.
_f1_env = os.getenv("F1")
COSTO_F1 = float(_f1_env) if _f1_env and _f1_env.strip() else costoReale

_f2_env = os.getenv("F2")
COSTO_F2 = float(_f2_env) if _f2_env and _f2_env.strip() else costoReale

_f3_env = os.getenv("F3")
COSTO_F3 = float(_f3_env) if _f3_env and _f3_env.strip() else costoReale

CARTELLA_DATA = "manipolazione_dati/data" # Cartella dove risiedono i CSV

# DIZIONARI DI TRADUZIONE E COLORI
# mappa per tradurre i nomi inglesi delle fonti del mix energetico in italiano
TRADUZIONI_FONTI = {
    'Hydro Run-of-River': 'Idroelettrico ad acqua fluente',
    'Biomass': 'Biomassa',
    'Fossil hard coal': 'Carbone fossile',
    'Fossil oil': 'Petrolio',
    'Fossil coal-derived gas': 'Gas derivato da carbone',
    'Fossil gas': 'Gas naturale',
    'Geothermal': 'Geotermico',
    'Hydro water reservoir': 'Idroelettrico a bacino',
    'Hydro pumped storage': 'Idroelettrico di pompaggio',
    'Waste': 'Rifiuti',
    'Wind offshore': 'Eolico offshore',
    'Wind onshore': 'Eolico onshore',
    'Solar': 'Solare',
    'Cross border electricity trading': 'Import',
    'Others': 'Altro'
}

# associa a ogni fonte energetica un colore specifico per mantenere coerenza visiva nei grafici
COLORI_DICT = {
    'Solare': '#FFC857',                 
    'Gas naturale': '#E9724C',           
    'Import': '#C5283D',                 
    'Rifiuti': '#623B59',                
    'Eolico onshore': '#219EBC',         
    'Eolico offshore': '#126782',        
    'Idroelettrico ad acqua fluente': '#00A8E8', 
    'Idroelettrico a bacino': '#0077B6', 
    'Idroelettrico di pompaggio': '#03045E', 
    'Biomassa': '#4CAF50',               
    'Geotermico': '#E26D5C',             
    'Carbone fossile': '#495057',        
    'Petrolio': '#795548',               
    'Gas derivato da carbone': '#95A5A6',
    'Altro': '#B0BEC5'                   
}
 
def get_colore_fonte(nome_fonte):
    return COLORI_DICT.get(nome_fonte, '#9E9E9E')

# CARICAMENTO E PREPARAZIONE DATI
# st.cache_data memorizza i risultati in cache per evitare di ricaricare/ricalcolare tutto ad ogni ricarica della pagina
@st.cache_data
def prepara_dati():
    percorso_consumi = os.path.join(CARTELLA_DATA, FILE_PULITO) if FILE_PULITO else None
    percorso_mix = os.path.join(CARTELLA_DATA, MIX_ENERGICO) if MIX_ENERGICO else None
    percorso_greend = os.path.join(CARTELLA_DATA, FILE_GREEND_NORMALIZZATO)
    
    if not percorso_consumi or not os.path.exists(percorso_consumi) or not percorso_mix or not os.path.exists(percorso_mix):
        st.error(f"Errore: File dati primari (utente o mix) non trovati in {CARTELLA_DATA}")
        st.stop() # Ferma l'esecuzione di Streamlit se mancano i file

    df_utente = pd.read_csv(percorso_consumi)
    # converte la colonna stringa in un oggetto datetime di pandas per faciltarne la manipolazione
    df_utente['Data-Ora'] = pd.to_datetime(df_utente['Data-Ora'], format='%d/%m/%Y-%H:%M:%S')
    
    # raggruppa (resample) i dati utente su base oraria calcolando la media dei consumi
    df_orario_utente = df_utente.set_index('Data-Ora').resample('1h')['Consumo'].mean().reset_index()
    # converte i Watt medi orari in kilowattora (kWh) totali per l'ora corrispondente
    df_orario_utente['kwh_totali'] = df_orario_utente['Consumo'].fillna(0) / 1000.0

    # ELABORAZIONE DATI GREEND (dataset di riferimento per machine learning/comparazioni)
    df_greend = None
    if os.path.exists(percorso_greend):
        df_greend = pd.read_csv(percorso_greend)
        
        if 'Consumo' in df_greend.columns:
            df_greend['Consumo'] = pd.to_numeric(df_greend['Consumo'], errors='coerce')
        if 'Consumo Normalizzato' in df_greend.columns:
            df_greend['Consumo Normalizzato'] = pd.to_numeric(df_greend['Consumo Normalizzato'], errors='coerce')
        if 'Data-Ora' in df_greend.columns:
            df_greend['Data-Ora'] = pd.to_datetime(df_greend['Data-Ora'], format='mixed', dayfirst=True, errors='coerce')

    # ELABORAZIONE DATI MIX ENERGETICO (da dove proviene la corrente)
    df_mix = pd.read_csv(percorso_mix)
    df_mix['datetime'] = pd.to_datetime(df_mix['datetime'])
    df_mix.columns = [c.strip() for c in df_mix.columns]
    # applichiamo il dizionario per avere i nomi delle fonti in italiano
    df_mix.rename(columns=TRADUZIONI_FONTI, inplace=True)

    # identifica quali fonti previste sono effettivamente presenti nel dataset
    categorie_valide = list(TRADUZIONI_FONTI.values())
    fonti_presenti = [c for c in categorie_valide if c in df_mix.columns]
    # calcoliamo il totale prodotto per ogni ora sommando tutte le fonti
    df_mix['produzione_totale'] = df_mix[fonti_presenti].sum(axis=1).replace(0, 1)

    # calcoliamo le percentuali (pct) di ogni singola fonte rispetto alla produzione totale
    for cat in fonti_presenti:
        df_mix[f'pct_{cat}'] = df_mix[cat] / df_mix['produzione_totale']

    # MERGE TRA DATI UTENTE E MIX ENERGETICO
    df_unito = pd.merge_asof(
        df_orario_utente.sort_values('Data-Ora'), 
        df_mix.sort_values('datetime'), 
        left_on='Data-Ora', right_on='datetime', direction='backward'
    )

    # moltiplica i kWh consumati dall'utente per la percentuale del mix energetico di quell'ora,
    # per stimare l'energia "fisica" (in kWh) derivante da ogni specifica fonte.
    for cat in fonti_presenti:
        df_unito[f'valore_{cat}'] = df_unito['kwh_totali'] * df_unito[f'pct_{cat}']
    
    return df_unito, df_utente, df_greend, fonti_presenti

# funzione per assegnare dinamicamente le fasce di costo F1, F2, F3 di ARERA
def assegna_fasce_orarie(df_in):
    df = df_in.copy()
    df['Data'] = df['Data-Ora'].dt.date # estrae la sola data senza orario
    
    # identificazione dei giorni festivi italiani utilizzando la libreria holidays
    try:
        anni = df['Data-Ora'].dt.year.unique().tolist()
        festivita_it = holidays.IT(years=anni)
    except ImportError:
        festivita_it = [] # fallback se c'è un problema con la libreria
        
    df['is_holiday'] = df['Data'].isin(festivita_it)
    df['day_of_week'] = df['Data-Ora'].dt.dayofweek # 0=Lunedì, 6=Domenica
    df['hour'] = df['Data-Ora'].dt.hour
    
    #CONDIZIONI PER LE FASCE (F3 = Festivi, Domenica, Notte; F1 = Ore di punta feriali; F2 = Intermedie e Sabato)
    cond_f3_festivi = (df['day_of_week'] == 6) | df['is_holiday'] # Domenica o giorno festivo (Natale, 1 Maggio, ecc.)
    
    cond_lun_ven = df['day_of_week'] < 5 # Dal Lunedì (0) al Venerdì (4)
    cond_f1_orario = (df['hour'] >= 8) & (df['hour'] < 19) # Orari di punta (8:00 - 18:59)
    cond_f2_orario_fer = ((df['hour'] >= 7) & (df['hour'] < 8)) | ((df['hour'] >= 19) & (df['hour'] < 23)) # Fasce cuscinetto
    
    cond_sabato = df['day_of_week'] == 5 # Sabato
    cond_f2_orario_sab = (df['hour'] >= 7) & (df['hour'] < 23) # Sabato dalle 7:00 alle 22:59
    
    # applica di default la F3 a tutti, per poi sovrascrivere F1 e F2 dove le condizioni sono rispettate
    df['Fascia'] = 'F3' 
    df.loc[cond_lun_ven & cond_f1_orario & ~cond_f3_festivi, 'Fascia'] = 'F1'
    df.loc[cond_lun_ven & cond_f2_orario_fer & ~cond_f3_festivi, 'Fascia'] = 'F2'
    df.loc[cond_sabato & cond_f2_orario_sab & ~cond_f3_festivi, 'Fascia'] = 'F2'
    
    return df

# INIZIALIZZAZIONE VARIABILI GLOBALI

# carica i dati in memoria invocando la funzione cachata
df_unito, df_utente, df_greend, fonti = prepara_dati()
giorni = sorted(df_utente['Data-Ora'].dt.date.unique())

#variabili statistiche generali per i grafici (servono per impostare scale dinamiche sensate)
media_base = df_utente['Consumo'].median()
picco_globale = df_utente['Consumo'].max()
min_globale = df_utente['Consumo'].min()
q_85 = df_utente['Consumo'].quantile(0.85)
soglia_lineare = max(200, q_85 * 1.5)

ticks_possibili = [50, 100, 200, 300, 500, 750, 1000, 1500, 2000, 3000, 5000, 7500, 10000, 15000]
ticks_dinamici = [t for t in ticks_possibili if t <= picco_globale * 1.1]

# GESTIONE MENU SIDEBAR E VISTE GRAFICHE

menu = [
    "Spesa Energetica per Fasce Orarie (F1, F2, F3)",
    "Spesa Energetica Giornaliera",
    "Confronto Hassio vs GREEND",
    "Correlazione tra Fonti Energetiche",
    "Volatilità Consumi",
    "Distribuzione Frequenze",
    "Confronto Fasce Orarie (Boxplot)",
    "Heatmap: Potenza Media",
    "Analisi Statistica Giornaliera",
    "Box-Plot: Distribuzione Giornaliera",
    "Trend Utilizzo Fonti",
    "Energia Totale Consumata per Giorno",
    "Profilo Giornaliero",
    "Dettaglio Normalizzazione GREEND"
]

# widget per selezionare il grafico desiderato
vista = st.sidebar.radio("Viste disponibili", menu)

# INIZIO DEFINIZIONE DELLE SINGOLE VISTE

if vista == "Spesa Energetica per Fasce Orarie (F1, F2, F3)":
    #crea un grafico a barre che mostra il costo totale suddiviso per le tre fasce orarie italiane
    fig, ax = plt.subplots(figsize=(16, 10))
    df_fasce = assegna_fasce_orarie(df_unito[['Data-Ora', 'kwh_totali']])
    etichette_fasce = ['F1', 'F2', 'F3']
    
    consumo_fasce = df_fasce.groupby('Fascia')['kwh_totali'].sum().reindex(etichette_fasce).fillna(0)
    
    costo_fasce = pd.Series([
        consumo_fasce['F1'] * COSTO_F1,
        consumo_fasce['F2'] * COSTO_F2,
        consumo_fasce['F3'] * COSTO_F3
    ], index=etichette_fasce)
    
    colori = ['#FFC857', '#E9724C', '#219EBC'] 
    bars = ax.bar(costo_fasce.index, costo_fasce.values, color=colori, edgecolor='white', linewidth=1.5, alpha=0.95)
    
    ax.set_title("Spesa Energetica per Fasce Orarie (F1, F2, F3)", fontweight='bold', fontsize=14, pad=20)
    ax.set_ylabel("Spesa Totale (€)", fontweight='bold', fontsize=12)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('€ %.2f'))
    ax.tick_params(axis='x', labelsize=12)
    plt.setp(ax.get_xticklabels(), fontweight='bold')
    
    costi_riferimento = [COSTO_F1, COSTO_F2, COSTO_F3]
    for i, bar in enumerate(bars):
        yval = bar.get_height()
        costo_spec = costi_riferimento[i]
        if yval > 0.01:
            testo_etichetta = f"€ {yval:.2f}\n({costo_spec:.4f} €/kWh)"
            ax.text(bar.get_x() + bar.get_width()/2, yval + (costo_fasce.max() * 0.02), testo_etichetta, 
                    ha='center', va='bottom', fontsize=11, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='none', edgecolor='gray', alpha=0.5))
    
    ax.set_ylim(top=costo_fasce.max() * 1.25 if costo_fasce.max() > 0 else 1)
    st.pyplot(fig, transparent=True)

elif vista == "Spesa Energetica Giornaliera":
    # grafico a barre che mostra quanto si è speso giorno per giorno
    fig, ax = plt.subplots(figsize=(16, 10))
    df_plot = df_unito.copy()
    df_plot['Giorno'] = df_plot['Data-Ora'].dt.strftime('%d/%m') # Estrae giorno e mese per le etichette
    
    # somma i kWh di tutto il giorno e moltiplica per il costo medio
    consumo_giornaliero = df_plot.groupby('Giorno')['kwh_totali'].sum()
    costo_giornaliero = consumo_giornaliero * costoReale
    
    bars = ax.bar(costo_giornaliero.index, costo_giornaliero.values, color='#27AE60', edgecolor='white', linewidth=1.5, alpha=0.95)
    
    ax.set_title(f"Spesa Energetica Giornaliera (Media base: {costoReale:.6f} €/kWh)", fontweight='bold', fontsize=14, pad=20)
    ax.set_ylabel("Costo (€)", fontweight='bold', fontsize=12)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('€ %.2f'))
    ax.tick_params(axis='x', rotation=45, labelsize=11)
    ax.tick_params(axis='y', labelsize=11)
    
    # aggiunge il valore in euro sopra ogni colonna
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + (costo_giornaliero.max() * 0.015), f"€ {yval:.2f}", 
                ha='center', va='bottom', fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='none', edgecolor='gray', alpha=0.5))
    
    media_costo = costo_giornaliero.mean()
    ax.axhline(media_costo, color='#E76F51', linestyle='--', linewidth=2.5, label=f"Spesa media: € {media_costo:.2f} / giorno")
    ax.legend(loc='upper right', fontsize=12, framealpha=0.5)
    ax.set_ylim(top=costo_giornaliero.max() * 1.15) 
    st.pyplot(fig, transparent=True)

elif vista == "Confronto Hassio vs GREEND":
    # dashboard che affianca i dati rilevati "in casa" contro i dataset di ricerca normalizzati
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.2])
    ax_su = fig.add_subplot(gs[0, 0])
    ax_sg = fig.add_subplot(gs[0, 1])
    ax_bar = fig.add_subplot(gs[1, :])
    plt.subplots_adjust(bottom=0.15, right=0.95, top=0.9, left=0.08, wspace=0.15, hspace=0.35)

    if df_greend is None or df_greend.empty:
        ax_su.text(0.5, 0.5, "File GREEND non disponibile", ha='center', fontsize=14)
    else:
        df_h = df_utente[['Data-Ora', 'Consumo']].dropna().copy()
        df_h['Data'] = df_h['Data-Ora'].dt.date
        giorni_hassio = sorted(df_h['Data'].unique())

        col_greend = 'Consumo Normalizzato' if 'Consumo Normalizzato' in df_greend.columns else 'Consumo'
        df_g = df_greend[['Data-Ora', col_greend]].dropna().copy()
        df_g['Data'] = df_g['Data-Ora'].dt.date
        giorni_greend = sorted(df_g['Data'].unique())

        num_giorni = min(len(giorni_hassio), len(giorni_greend))
        if num_giorni > 0:
            giorni_h_allineati = giorni_hassio[:num_giorni]
            giorni_g_allineati = giorni_greend[:num_giorni]

            # costruisce i dati per il grafico a barre sovrapposto
            dati_barre = []
            for i in range(num_giorni):
                etichetta = f"G {i+1}"
                
                # resample Hassio a 1h e conversione a kWh
                dati_h_giorno = df_h[df_h['Data'] == giorni_h_allineati[i]].set_index('Data-Ora')
                kwh_h = (dati_h_giorno['Consumo'].resample('1h').mean().fillna(0).sum()) / 1000.0
                dati_barre.append({'Giorno': etichetta, 'Energia_kWh': kwh_h, 'Sorgente': 'Hassio'})
                
                # resample Greend a 1h e conversione a kWh
                dati_g_giorno = df_g[df_g['Data'] == giorni_g_allineati[i]].set_index('Data-Ora')
                kwh_g = (dati_g_giorno[col_greend].resample('1h').mean().fillna(0).sum()) / 1000.0
                dati_barre.append({'Giorno': etichetta, 'Energia_kWh': kwh_g, 'Sorgente': 'GREEND Normalizzato'})

            df_barre = pd.DataFrame(dati_barre)

            # estrae l'ora per i lineplot della prima riga (grafici che mostrano la curva media delle 24h)
            df_h_sub = df_h[df_h['Data'].isin(giorni_h_allineati)].copy()
            df_h_sub['Ora'] = df_h_sub['Data-Ora'].dt.hour
            df_g_sub = df_g[df_g['Data'].isin(giorni_g_allineati)].copy()
            df_g_sub['Ora'] = df_g_sub['Data-Ora'].dt.hour

            # calcolo dei massimali per far combaciare e scalare correttamente gli assi Y
            max_h = max(200, df_h_sub.groupby('Ora')['Consumo'].quantile(0.95).max() * 1.20 if not df_h_sub.empty else 200)
            max_g = max(200, df_g_sub.groupby('Ora')[col_greend].quantile(0.95).max() * 1.20 if not df_g_sub.empty else 200)

            colore_hassio = '#2ECC71'
            colore_greend = '#34495E'

            # lineplot Hassio (con intervallo di confidenza errorbar)
            sns.lineplot(data=df_h_sub, x='Ora', y='Consumo', color=colore_hassio, errorbar=('pi', 90), ax=ax_su, linewidth=2.5)
            ax_su.set_title("Profilo Medio Sensore Hassio", fontweight='bold')
            ax_su.set_ylabel("Potenza Media (W)")
            ax_su.set_xlim(0, 23)
            ax_su.set_xticks(range(0, 24))
            ax_su.set_ylim(bottom=0, top=max_h)

            # lineplot Greend
            sns.lineplot(data=df_g_sub, x='Ora', y=col_greend, color=colore_greend, errorbar=('pi', 90), ax=ax_sg, linewidth=2.5)
            ax_sg.set_title("Profilo Medio Dataset GREEND Normalizzato", fontweight='bold')
            ax_sg.set_ylabel("Potenza Media (W)") 
            ax_sg.set_xlim(0, 23)
            ax_sg.set_xticks(range(0, 24))
            ax_sg.set_ylim(bottom=0, top=max_g) 

            # barplot comparativo (Hassio vs Greend per giorno)
            if not df_barre.empty:
                sns.barplot(
                    data=df_barre, x='Giorno', y='Energia_kWh', hue='Sorgente', 
                    ax=ax_bar, palette={'Hassio': colore_hassio, 'GREEND Normalizzato': colore_greend}
                )
                ax_bar.set_title("Confronto Diretto su kW Consumati", fontweight='bold')
                ax_bar.set_ylabel("Energia (kWh)")
                ax_bar.grid(axis='y', linestyle='--', alpha=0.4)
                ax_bar.set_axisbelow(True)
                
                if num_giorni > 8:
                    ax_bar.tick_params(axis='x', rotation=45)
                
                handles, labels = ax_bar.get_legend_handles_labels()
                by_label = dict(zip(labels, handles))
                ax_bar.legend(by_label.values(), by_label.keys(), title="Sorgente", frameon=True)
    st.pyplot(fig, transparent=True)

elif vista == "Correlazione tra Fonti Energetiche":
    # genera una Heatmap di correlazione per vedere quali fonti di energia crescono (o decrescono) assieme
    fig, ax = plt.subplots(figsize=(16, 10))
    plt.subplots_adjust(bottom=0.30, right=0.95, top=0.9, left=0.35)
    
    colonne_fonti = [f'valore_{f}' for f in fonti]
    df_correlazione = df_unito[colonne_fonti].copy()
    df_correlazione.columns = fonti
    df_correlazione = df_correlazione.loc[:, (df_correlazione != 0).any(axis=0)]
    
    matrice = df_correlazione.corr()
    
    maschera = np.triu(np.ones_like(matrice, dtype=bool))
    
    colori_gradiente = ['#A6611A', '#F5F5F5', '#018571']
    cmap_custom = LinearSegmentedColormap.from_list('CustomCorr', colori_gradiente)
    
    sns.heatmap(matrice, mask=maschera, annot=True, cmap=cmap_custom, fmt=".2f", ax=ax, vmin=-1, vmax=1, 
                linewidths=0.5, linecolor='gray')
    ax.set_title("Correlazione tra Fonti Energetiche nel Mix", fontweight='bold')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    
    testo_legenda = ("Lettura Matrice:\n\n+1.0 : Crescono insieme \n 0.0 : Nessuna relazione \n-1.0 : Inversamente prop.")
    fig.text(0.02, 0.5, testo_legenda, fontsize=11, va='center', bbox=dict(facecolor='none', edgecolor='gray', boxstyle='round,pad=0.8', alpha=0.5))
    st.pyplot(fig, transparent=True)

elif vista == "Volatilità Consumi":
    # grafico a barre per mostrare l'incostanza dei consumi nelle varie ore del giorno
    fig, ax = plt.subplots(figsize=(16, 10))
    df_v = df_utente.copy()
    df_v['Ora'] = df_v['Data-Ora'].dt.hour
    
    std_oraria = df_v.groupby('Ora')['Consumo'].std()
    
    ax.bar(std_oraria.index, std_oraria.values, color='#E67E22', alpha=0.9, edgecolor='white', linewidth=1)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.set_title("Volatilità Consumi (Deviazione Standard per Ora)", fontweight='bold')
    ax.set_xticks(range(0, 24))
    ax.set_ylabel("Deviazione Standard (W)")
    st.pyplot(fig, transparent=True)

elif vista == "Distribuzione Frequenze":
    # istogramma per vedere quali wattaggi ricorrono più frequentemente nel corso dei rilevamenti
    fig, ax = plt.subplots(figsize=(16, 10))
    colore_viola = '#9B5DE5'
    
    sns.histplot(df_utente['Consumo'], bins=60, kde=False, color=colore_viola, ax=ax, alpha=0.9, edgecolor='white')
    
    ax.set_yscale('log')
    ax.set_ylim(bottom=0.8)
    ax.yaxis.set_major_formatter(ticker.ScalarFormatter())
    
    ax.set_title("Distribuzione Frequenze", fontweight='bold', fontsize=14, pad=15)
    ax.set_xlabel("Potenza Rilevata (W)", fontweight='bold')
    ax.set_ylabel("Frequenza (Numero di rilevazioni)", fontweight='bold')
    
    ax.axvline(df_utente['Consumo'].mean(), color='#E76F51', linestyle='--', linewidth=2.5, label="Media Totale")
    ax.axvline(media_base, color='#27AE60', linestyle='-', linewidth=2.5, label="Mediana Base")
    
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(frameon=True, framealpha=0.5)
    st.pyplot(fig, transparent=True)

elif vista == "Confronto Fasce Orarie (Boxplot)":
    # crea una griglia di boxplot separati (uno per F1, F2, F3 e uno "Tutte le fasce")
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
    plt.subplots_adjust(bottom=0.1, right=0.95, top=0.88, left=0.08, hspace=0.3, wspace=0.15)

    df_fasce = assegna_fasce_orarie(df_utente[['Data-Ora', 'Consumo']])
    df_tutte = df_fasce.copy()
    df_tutte['Fascia'] = 'Tutte le Fasce'
    df_completo = pd.concat([df_fasce, df_tutte])
    
    etichette_fasce = ['F1', 'F2', 'F3', 'Tutte le Fasce']
    colori = ['#FFC857', '#E9724C', '#219EBC', '#623B59'] 
    
    for ax, fascia, colore in zip(axes, etichette_fasce, colori):
        dati_fascia = df_completo[df_completo['Fascia'] == fascia]
        
        sns.stripplot(data=dati_fascia, y='Consumo', color=colore, jitter=0.35, alpha=0.6, size=4, ax=ax, zorder=1)
        sns.boxplot(data=dati_fascia, y='Consumo', showfliers=False, width=0.4, ax=ax, zorder=10,
                    boxprops=dict(facecolor='none', edgecolor=colore, linewidth=2), 
                    medianprops=dict(linewidth=2.5)) 
        
        ax.axhline(media_base, color='#27AE60', linestyle='--', linewidth=1.5, alpha=0.8, zorder=0, label=f"Media Base ({media_base:.0f}W)")
        ax.set_title(fascia, fontweight='bold', pad=10, color=colore)
        
        if axes.index(ax) % 2 == 0:
            ax.set_ylabel("Potenza (W)", fontweight='bold')
        else:
            ax.set_ylabel("")
            
        ax.set_yscale('symlog', linthresh=soglia_lineare)
        ax.yaxis.set_major_formatter(ticker.ScalarFormatter())
        ax.set_yticks(ticks_dinamici)
        ax.set_ylim(bottom=min_globale - 10, top=picco_globale + (picco_globale * 0.05))
        ax.grid(axis='y', linestyle='--', alpha=0.4)
        ax.set_axisbelow(True)
        
        if axes.index(ax) == 0:
            ax.legend(loc='upper right', fontsize=9, framealpha=0.5)
        if axes.index(ax) % 2 != 0: 
            ax.tick_params(labelleft=False)
    st.pyplot(fig, transparent=True)

elif vista == "Heatmap: Potenza Media":
    # crea una "mappa di calore" per individuare facilmente pattern visivi di picchi di consumo
    # ad esempio per capire se c'è un'abitudine di alto consumo ad una specifica ora o giorno
    fig, ax = plt.subplots(figsize=(16, 10))
    df_h = df_utente.copy()
    df_h['Ora'] = df_h['Data-Ora'].dt.hour
    df_h['Data'] = df_h['Data-Ora'].dt.strftime('%d/%m')
    
    pivot = df_h.pivot_table(index='Ora', columns='Data', values='Consumo', aggfunc='mean')
    
    sns.heatmap(pivot, cmap='flare', ax=ax, linewidths=0.1)
    ax.set_title("Heatmap: Potenza Media per Ora e Giorno", fontweight='bold')
    st.pyplot(fig, transparent=True)

elif vista == "Analisi Statistica Giornaliera":
    # mette a confronto su barre affiancate le 3 metriche principali di consumo giornaliero
    fig, ax = plt.subplots(figsize=(16, 10))
    df_stats = df_utente.copy()
    df_stats['Data'] = df_stats['Data-Ora'].dt.date
    
    stats = df_stats.groupby('Data')['Consumo'].agg(['mean', 'median', 'std']).reset_index()
    
    x = np.arange(len(stats['Data'])) # Indici per l'asse x
    w = 0.25
    
    ax.bar(x - w, stats['mean'], w, label='Media', color='#27AE60', edgecolor='white', linewidth=1)
    ax.bar(x, stats['median'], w, label='Mediana', color='#5D6D7E', edgecolor='white', linewidth=1)
    ax.bar(x + w, stats['std'], w, label='Dev. Standard', color='#E67E22', edgecolor='white', linewidth=1)
    
    ax.set_xticks(x)
    ax.set_xticklabels([d.strftime('%d/%m') for d in stats['Data']], rotation=45, ha='right')
    ax.set_title("Analisi Statistica Giornaliera", fontweight='bold', fontsize=14, pad=15)
    ax.set_ylabel("Potenza (W)", fontweight='bold', fontsize=12)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.set_axisbelow(True)
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0., framealpha=0.5)
    plt.subplots_adjust(right=0.85)
    st.pyplot(fig, transparent=True)

elif vista == "Box-Plot: Distribuzione Giornaliera":
    # crea un Boxplot lungo che mostra la distribuzione dei consumi giorno per giorno
    fig, ax = plt.subplots(figsize=(16, 10))
    df_box = df_utente[['Data-Ora', 'Consumo']].copy()
    df_box['Data'] = df_box['Data-Ora'].dt.date
    gruppi = df_box.groupby('Data')
    
    dati_plot = [g['Consumo'].values for d, g in gruppi]
    etichette = [d.strftime('%d/%m') for d, g in gruppi]
    
    ax.boxplot(
        dati_plot, tick_labels=etichette, patch_artist=True, showfliers=True,
        widths=0.7, 
        boxprops=dict(facecolor='#8ECAE6', alpha=0.8, edgecolor='#219EBC', linewidth=1.5), 
        medianprops=dict(linewidth=2),
        whiskerprops=dict(linewidth=1.5),
        capprops=dict(linewidth=1.5),
        flierprops=dict(marker='o', markerfacecolor='#FB8500', markeredgecolor='none', 
                        markersize=5, alpha=0.6, markeredgewidth=0.5)
    )
    
    ax.axhline(media_base, color='#27AE60', linestyle='--', linewidth=1.5, alpha=0.8, zorder=0, label=f"Media Base ({media_base:.0f}W)")
    ax.legend(loc='upper left', fontsize=11, framealpha=0.5)
    
    ax.set_yscale('symlog', linthresh=soglia_lineare)
    ax.yaxis.set_major_formatter(ticker.ScalarFormatter())
    ax.set_yticks(ticks_dinamici)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.set_axisbelow(True) 
    ax.tick_params(axis='x', rotation=45, labelsize=11)
    ax.tick_params(axis='y', labelsize=11)
    
    idx_max = df_box['Consumo'].idxmax()
    data_picco = df_box.loc[idx_max, 'Data']
    
    testo_flag = f"Picco Massimo\n{picco_globale:.0f} W (il {data_picco.strftime('%d/%m')})"
    ax.text(0.98, 0.95, testo_flag, transform=ax.transAxes, 
            fontsize=11, fontweight='bold', color='#D62828',
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='none', edgecolor='#D62828', alpha=0.5))
    
    ax.set_title("Box-Plot: Distribuzione giornaliera consumi", fontweight='bold', fontsize=14, pad=15)
    ax.set_ylabel("Potenza (W)", fontsize=12, fontweight='bold')
    st.pyplot(fig, transparent=True)

elif vista == "Trend Utilizzo Fonti":
    # grafico a linee storiche per vedere l'andamento del mix di fonti nei giorni (es. il solare cala nei giorni di pioggia)
    fig, ax = plt.subplots(figsize=(16, 10))
    df_plot = df_unito.copy()
    df_plot['Giorno'] = df_plot['Data-Ora'].dt.strftime('%d/%m')
    
    df_raggruppato = df_plot.groupby('Giorno')[[f'valore_{f}' for f in fonti]].sum()
    df_raggruppato.columns = fonti
    
    for col in df_raggruppato.columns:
        if df_raggruppato[col].sum() > 0.1: 
            ax.plot(df_raggruppato.index, df_raggruppato[col], marker='o', label=col, color=get_colore_fonte(col), linewidth=2.5)
    
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', framealpha=0.5)
    ax.set_title("Trend di Utilizzo delle Fonti Energetiche", fontweight='bold')
    plt.subplots_adjust(right=0.85)
    st.pyplot(fig, transparent=True)

elif vista == "Energia Totale Consumata per Giorno":
    # istogramma cumulativo che mostra il volume fisico dei consumi suddiviso per colore del mix
    fig, ax = plt.subplots(figsize=(16, 10))
    df_plot = df_unito.copy()
    df_plot['Giorno'] = df_plot['Data-Ora'].dt.strftime('%d/%m')
    df_raggruppato = df_plot.groupby('Giorno')[[f'valore_{f}' for f in fonti]].sum()
    df_raggruppato.columns = fonti
    
    df_raggruppato.plot(kind='bar', stacked=True, ax=ax, 
                        color=[get_colore_fonte(f) for f in fonti], 
                        edgecolor='none', linewidth=0.5)
    
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', framealpha=0.5)
    ax.set_title("Energia Totale Consumata per Giorno (kWh)", fontweight='bold', fontsize=14, pad=20)
    ax.set_ylabel("Energia (kWh)", fontweight='bold')
    
    totali_giornalieri = df_raggruppato.sum(axis=1)
    for i, totale in enumerate(totali_giornalieri):
        ax.text(i, totale + (totale * 0.01), f"{totale:.2f} kWh", 
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.tick_params(axis='x', rotation=45)
    ax.set_ylim(top=totali_giornalieri.max() * 1.15)
    plt.subplots_adjust(right=0.85)
    st.pyplot(fig, transparent=True)

elif vista == "Profilo Giornaliero":
    # dashboard per esaminare lo scorrere di una SINGOLA GIORNATA e del suo mix
    # permette all'utente di selezionare il giorno tramite una selectbox nella sidebar
    giorno_selezionato = st.sidebar.selectbox("Seleziona Giorno", giorni)
    
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.2, 1])
    ax_orario = fig.add_subplot(gs[0, 0])
    ax_pie = fig.add_subplot(gs[1, 0])
    plt.subplots_adjust(bottom=0.10, right=0.85, top=0.95, hspace=0.4, left=0.1)

    df_giorno = df_unito[df_unito['Data-Ora'].dt.date == giorno_selezionato].copy()
    df_giorno['Ora'] = df_giorno['Data-Ora'].dt.strftime('%H:00')
    colonne = [f'valore_{f}' for f in fonti]
    
    df_plot = df_giorno.groupby('Ora')[colonne].sum()
    df_plot.columns = fonti
    df_plot = df_plot.loc[:, (df_plot != 0).any(axis=0)]
    colori = [get_colore_fonte(f) for f in df_plot.columns]
    
    df_plot.plot(kind='bar', stacked=True, color=colori, ax=ax_orario, edgecolor='none', linewidth=0.5)
    ax_orario.grid(axis='y', linestyle='--', alpha=0.4)
    ax_orario.set_title(f"Profilo Orario: {giorno_selezionato.strftime('%d/%m/%Y')}", fontweight='bold')
    ax_orario.set_ylabel("Energia (kWh)")
    ax_orario.legend(bbox_to_anchor=(1.02, 1), loc='upper left', framealpha=0.5)

    valori = df_giorno[colonne].sum()
    valori.index = [n.replace('valore_', '') for n in valori.index] # Toglie 'valore_' dalle etichette
    totale = valori.sum()
    soglia = totale * 0.02
    
    val_attivi = valori[valori > soglia].copy()
    val_piccoli = valori[valori <= soglia]
    
    if val_piccoli.sum() > 0:
        if 'Altro' in val_attivi.index: val_attivi['Altro'] += val_piccoli.sum()
        else: val_attivi['Altro'] = val_piccoli.sum()
        
    val_attivi = val_attivi[val_attivi > 0]
    colori_pie = [get_colore_fonte(n) for n in val_attivi.index]
    
    wedges, texts, autotexts = ax_pie.pie(
        val_attivi, labels=None, autopct='%1.1f%%', startangle=140,
        colors=colori_pie, pctdistance=0.75, textprops={'fontsize': 10, 'fontweight': 'bold', 'color': 'white'},
        wedgeprops={'edgecolor': 'none', 'linewidth': 2, 'antialiased': True}
    )
    
    for autotext in autotexts:
        autotext.set_bbox(dict(facecolor='black', alpha=0.3, edgecolor='none', pad=1.5, boxstyle='round,pad=0.2'))
        
    ax_pie.legend(wedges, val_attivi.index, title="Fonti Energetiche", loc="center left", bbox_to_anchor=(1, 0.5), framealpha=0.5)
    ax_pie.set_title(f"Mix energetico: {giorno_selezionato.strftime('%d/%m/%Y')} (Fonti < 2% in 'Altro')", fontweight='bold')
    st.pyplot(fig, transparent=True)

elif vista == "Dettaglio Normalizzazione GREEND":
    # grafico che mostra come il dato RAW Greend è stato trattato clippato al limite italiano del contatore a 3.3kW, normalizzato ecc.
    if df_greend is None or df_greend.empty:
        st.warning("Il file GREEND normalizzato non è disponibile.")
    else:
        df_g = df_greend.copy()
        
        df_g['Data_Giorno'] = df_g['Data-Ora'].dt.date
        giorni_greend = sorted(df_g['Data_Giorno'].dropna().unique())
        
        if not giorni_greend:
            st.warning("Nessuna data valida trovata nel file GREEND.")
        else:
            giorno_selezionato_greend = st.sidebar.selectbox("Seleziona Giorno (Dataset GREEND)", giorni_greend)
            df_giorno = df_g[df_g['Data_Giorno'] == giorno_selezionato_greend].copy()
            
            fig, ax = plt.subplots(figsize=(14, 7))
            
            if 'Consumo' in df_giorno.columns:
                ax.plot(df_giorno['Data-Ora'], df_giorno['Consumo'], 
                        label='Dato GREEND Reale (Raw)', color='#90EE90', alpha=0.4, linewidth=1)
            
            if 'Consumo_Clipped' in df_giorno.columns:
                ax.plot(df_giorno['Data-Ora'], df_giorno['Consumo_Clipped'], 
                        label='Dato Clipped (Max 3.3kW)', color='gray', alpha=0.5, linewidth=1.5)
            
            if 'Target_Portale_W' in df_giorno.columns:
                ax.plot(df_giorno['Data-Ora'], df_giorno['Target_Portale_W'], 
                        label='Media Portale dei Consumi', color='#E74C3C', linestyle='--', linewidth=2, alpha=0.8)
            
            colonna_norm = 'Consumo_Normalizzato' if 'Consumo_Normalizzato' in df_giorno.columns else ('Consumo Normalizzato' if 'Consumo Normalizzato' in df_giorno.columns else None)
            
            if colonna_norm:
                ax.plot(df_giorno['Data-Ora'], df_giorno[colonna_norm], 
                        label='Dato Normalizzato (Fuso)', color='#3498DB', linewidth=2)
            
            ax.axhline(y=3300, color='darkred', linestyle=':', label='Limite Contatore (3.3 kW)')
            
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2)) # Mette un indicatore ogni 2 ore
            ax.tick_params(axis='x', rotation=45)
            
            ax.set_title(f"Confronto Consumi: Reale vs Portale vs Normalizzato ({giorno_selezionato_greend.strftime('%d/%m/%Y')})", fontsize=14, pad=15, fontweight='bold')
            ax.set_xlabel('Orario della Giornata', fontsize=12, fontweight='bold')
            ax.set_ylabel('Potenza (Watt)', fontsize=12, fontweight='bold')
            
            ax.legend(loc='upper right', bbox_to_anchor=(1.0, 1.0), framealpha=0.5)
            
            ax.grid(True, which='major', linestyle='-', alpha=0.6)
            ax.grid(True, which='minor', linestyle=':', alpha=0.3)
            ax.minorticks_on()
            
            st.pyplot(fig, transparent=True)