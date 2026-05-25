import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

FILE_PULITO = os.getenv("FILE_PULITO")
FILE_GREEND = os.getenv("FILE_GREEND")
MIX_ENERGICO = os.getenv("EXPORT_MIX_ENERGETICO_NAZIONALE")
CARTELLA_DATA = os.path.join("manipolazione_dati", "data")
TRADUZIONI_FONTI = {
    "Hydro Run-of-River": "Idroelettrico ad acqua fluente",
    "Biomass": "Biomassa",
    "Fossil hard coal": "Carbone fossile",
    "Fossil oil": "Petrolio",
    "Fossil coal-derived gas": "Gas derivato da carbone",
    "Fossil gas": "Gas naturale",
    "Geothermal": "Geotermico",
    "Hydro water reservoir": "Idroelettrico a bacino",
    "Hydro pumped storage": "Idroelettrico di pompaggio",
    "Waste": "Rifiuti",
    "Wind offshore": "Eolico offshore",
    "Wind onshore": "Eolico onshore",
    "Solar": "Solare",
    "Cross border electricity trading": "Import",
    "Others": "Altro"
}

def prepara_dati():
    """
    carica i dataset dei consumi, del mix energetico e del dataset GREEND.
    Esegue il merge asincrono basato sulle date e calcola i kWh totali.
    Ritorna: df unito, df raw, df GREEND, lista fonti disponibili.
    """
    percorso_consumi = os.path.join(CARTELLA_DATA, FILE_PULITO) if CARTELLA_DATA else FILE_PULITO
    percorso_mix = os.path.join(CARTELLA_DATA, MIX_ENERGICO) if CARTELLA_DATA else MIX_ENERGICO
    percorso_greend = os.path.join(CARTELLA_DATA, FILE_GREEND) if CARTELLA_DATA else FILE_GREEND
    
    if not os.path.exists(percorso_consumi) or not os.path.exists(percorso_mix):
        print("errore: verifica i percorsi nel file .env e la cartella 'data'.")
        return None

    #caricamento e preparazione dati di consumo dell'utente
    df_consumi_hassio = pd.read_csv(percorso_consumi)
    df_consumi_hassio["Data-Ora"] = pd.to_datetime(df_consumi_hassio["Data-Ora"], format="%d/%m/%Y-%H:%M:%S")
    df_consumi_hassio["kwh_totali"] = (df_consumi_hassio["Consumo"] / 1000) / 60.0
    df_ora = df_consumi_hassio.set_index("Data-Ora").resample("1h")["kwh_totali"].sum().reset_index()

    #caricamento baseline GREEND
    df_GREEND = None
    if os.path.exists(percorso_greend):
        df_GREEND = pd.read_csv(percorso_greend)
        df_GREEND["Consumo"] = pd.to_numeric(df_GREEND["Consumo"], errors="coerce")
        if "Data-Ora" in df_GREEND.columns:
            df_GREEND["Data-Ora"] = pd.to_datetime(df_GREEND["Data-Ora"], errors="coerce")
    else:
        print("baseline_GREEND.csv non trovato")

    #caricamento e allineamento mix energetico
    df_mixEnergetico = pd.read_csv(percorso_mix)
    df_mixEnergetico["datetime"] = pd.to_datetime(df_mixEnergetico["datetime"])
    df_mixEnergetico.columns = [column.strip() for column in df_mixEnergetico.columns]
    df_mixEnergetico.rename(columns=TRADUZIONI_FONTI, inplace=True)

    categorie_indagine = list(TRADUZIONI_FONTI.values())
    fonti_disponibili = [column for column in categorie_indagine if column in df_mixEnergetico.columns]
    df_mixEnergetico["produzione_totale"] = df_mixEnergetico[fonti_disponibili].sum(axis=1).replace(0, 1)

    for cat in fonti_disponibili:
        df_mixEnergetico[f"pct_{cat}"] = df_mixEnergetico[cat] / df_mixEnergetico["produzione_totale"]

    #unione dei dati orari dell'utente con il mix energetico nazionale
    df_unito = pd.merge_asof(
        df_ora.sort_values("Data-Ora"), 
        df_mixEnergetico.sort_values("datetime"), 
        left_on="Data-Ora", right_on="datetime", direction="backward"
    )

    for cat in fonti_disponibili:
        df_unito[f"valore_{cat}"] = df_unito["kwh_totali"] * df_unito[f"pct_{cat}"]
    
    return df_unito, df_consumi_hassio, df_GREEND, fonti_disponibili

#mappatura colori esportata per l'uso nel file dei grafici
COLORI_ESTESI = [
    "#3498db", "#27ae60", "#2c3e50", "#8e44ad", "#c0392b", "#e74c3c", 
    "#e67e22", "#2980b9", "#1abc9c", "#d35400", "#9b59b6", "#34495e", 
    "#f1c40f", "#f39c12", "#7f8c8d"
]
COLORI_DICT = dict(zip(list(TRADUZIONI_FONTI.values()), COLORI_ESTESI))