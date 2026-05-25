import pandas as pd
import numpy as np
import os
import glob
from dotenv import load_dotenv

INPUT_DIR = os.path.join("manipolazione_dati", "dataset")
OUTPUT_DIR = os.path.join("manipolazione_dati", "data")

load_dotenv()
FILE_PORTALE = os.getenv("FILE_PORTALE")
LIMITE_CONTATORE_W = float(os.getenv("CONTRATTO"))
FILE_GREEND = os.getenv("FILE_GREEND")
W_STANDBY = int(os.getenv("W_STANDBY"))


MESI_PORTALE = {
    1: 'Gen', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Mag', 6: 'Giu',
    7: 'Lug', 8: 'Ago', 9: 'Set', 10: 'Ott', 11: 'Nov', 12: 'Dic'
}

def carica_portale(file_path):
    df_portale = pd.read_csv(file_path, sep='\t', header=[0, 1], encoding='utf-16')
    df_portale.columns = [c2 if "Unnamed" in c1 else f"{c1}_{c2}" for c1, c2 in df_portale.columns]
    return df_portale

def calcola_valori_orari(df_portale, mese_str):
    """
    questa funzione legge i kWh medi di ogni ora nel file del portale
    """
    df_mese = df_portale[df_portale['Anno mese'].str.contains(mese_str, na=False)]
    
    def get_kwh_values(cols_list):
        return df_mese[cols_list].apply(lambda x: x.str.replace(',', '.').astype(float)).mean().values

    valori_orari = {
        'SAB': get_kwh_values(df_portale.columns[3:27]),
        'DOM': get_kwh_values(df_portale.columns[27:51]),
        'FER': get_kwh_values(df_portale.columns[51:75])
    }
    return valori_orari

def processa_file_greend(file_path, df_portale, output_dir, limite_contatore):
    df = pd.read_csv(file_path)
    df['Data-Ora'] = pd.to_datetime(df['Data-Ora'], format='%d/%m/%Y-%H:%M:%S')
    df.set_index('Data-Ora', inplace=True)
    
    #clipping iniziale per eliminare gli errori dei sensori
    df['Consumo_Clipped'] = df['Consumo'].clip(upper=limite_contatore)
    df['Consumo_Normalizzato'] = 0.0
    df['Target_Portale_W'] = 0.0
    
    #colonne temporanee per raggruppare i dati
    df['Date'] = df.index.date
    df['Hour'] = df.index.hour
    df['DayOfWeek'] = df.index.dayofweek
    
    #cerchiamo il numero del mese e il mese effettivo e lo passiamo per il calcolo
    mese_num = df.index[0].month
    mese_str = MESI_PORTALE[mese_num]
    valori_orari = calcola_valori_orari(df_portale, mese_str)
    
    ore_integrate = ore_reali = 0
    
    #raggruppamento ora per ora di ogni giornata (considerato anche se lavorativo, sabato e domenica)
    for (data, ora), group in df.groupby(['Date', 'Hour']):
        
        giorno_settimana = group['DayOfWeek'].iloc[0]
        if giorno_settimana == 5:
            tipo_giorno = 'SAB'
        elif giorno_settimana == 6:
            tipo_giorno = 'DOM'
        else:
            tipo_giorno = 'FER'
        
        #rappresenta quanta energia consuma mediamente una famiglia italiana in 60 min
        target_kwh_h_full = valori_orari[tipo_giorno][ora]
        
        #salviamo il target orario del Portale convertito in watt (kWh * 1000 = W)
        df.loc[group.index, 'Target_Portale_W'] = target_kwh_h_full * 1000.0
        
        minuti_presenti = len(group)
        target_kwh_h = target_kwh_h_full * (minuti_presenti / 60.0)
        
        #calcolo i consumi clippati in un ora e li trasformo da watt al min in kWh
        greend_kwh_h = group['Consumo_Clipped'].sum() / 60000.0
        
        #se il comnsumo dei sensori è minore dei dati registrati dal portale ci sono 2 possibili strade
        if greend_kwh_h < target_kwh_h:
            #1. consumo troppo basso, mancano le luci e gli standby
            
            #calcolo quindi quanto manca effettivamente
            missing_kwh = target_kwh_h - greend_kwh_h
            #converto i kWh mancanti in W da sommare ai Watt di ogni minuto
            #questo viene fatto per aggiungere gli standby non presenti
            add_w_min = (missing_kwh * 60000.0) / minuti_presenti
            
            # aggiungiamo ai consumi clippati del GREEND i valori minimi (sempre secondo i risultati statistici del portale)
            consumo_temp = group['Consumo_Clipped'] + add_w_min
            
            #applichiamo il limite massimo (il contatore stacca) e minimo (i tuoi 80W a vuoto)
            consumo_temp = np.maximum(consumo_temp, W_STANDBY) # Pavimento
            df.loc[group.index, 'Consumo_Normalizzato'] = consumo_temp.clip(upper=limite_contatore) # Soffitto
            ore_integrate += 1
            
        else:
            #2. la casa consuma di piu della media riportata nei dati del portale.
            # lo consideriamo come dato reale (es. lavatrice accesa)
            consumo_temp = np.maximum(group['Consumo_Clipped'], W_STANDBY)
            df.loc[group.index, 'Consumo_Normalizzato'] = consumo_temp.clip(upper=limite_contatore)
            ore_reali += 1

    df.drop(columns=['Date', 'Hour', 'DayOfWeek'], inplace=True)
    
    os.makedirs(output_dir, exist_ok=True)
    
    nome_originale = os.path.basename(file_path).split('.')[0]
    nome_output = os.path.join(output_dir, f"{nome_originale}_normalizzato.csv")
    
    df[['Consumo', 'Consumo_Clipped', 'Consumo_Normalizzato', 'Target_Portale_W']].reset_index().to_csv(nome_output, index=False)
    print(f"dati normalizzati salvati in {nome_output}")

def esegui_normalizzazione(input_dir=None, output_dir=None):
    if input_dir is None:
        input_dir = INPUT_DIR
    if output_dir is None:
        output_dir = OUTPUT_DIR

    if not FILE_PORTALE or not FILE_GREEND or not W_STANDBY:
        return False
        
    percorso_portale = os.path.join(input_dir, FILE_PORTALE)
    percorso_greend_pattern = os.path.join(input_dir, FILE_GREEND)
    
    if not os.path.exists(percorso_portale):
        return False
        
    df_portale = carica_portale(percorso_portale)
    file_greend_trovati = glob.glob(percorso_greend_pattern)
    
    if not file_greend_trovati:
        return False
        
    for file_path in file_greend_trovati:
        processa_file_greend(file_path, df_portale, output_dir, LIMITE_CONTATORE_W)
        
    return True

if __name__ == "__main__":
    esegui_normalizzazione()