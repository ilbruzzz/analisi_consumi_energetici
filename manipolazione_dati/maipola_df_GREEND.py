import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

def genera_baseline():
    """
    Genera un dataset basato sul dataset GREEND.
    Logica: 
    1. Capisce l'ultimo giorno (Riferimento).
    2. Calcola la differenza per ottenere il numero totale di giorni.
    3. Concatena ("spiaccica") i CSV corrispondenti ai giorni della settimana.
    4. Taglia all'orario esatto.
    """
    load_dotenv(override=True)
    
    INPUT_DIR = os.path.join("manipolazione_dati", "dataset")
    OUTPUT_DIR = os.path.join("manipolazione_dati", "dataset")
    
    mesi_mappa = {
        1: "01_gennaio", 2: "02_febbraio", 3: "03_marzo", 4: "04_aprile",
        5: "05_maggio", 6: "06_giugno", 7: "07_luglio", 8: "08_agosto",
        9: "09_settembre", 10: "10_ottobre", 11: "11_novembre", 12: "12_dicembre"
    }
    giorni_file = [
        "01_lunedi.csv", "02_martedi.csv", "03_mercoledi.csv", 
        "04_giovedi.csv", "05_venerdi.csv", "06_sabato.csv", "07_domenica.csv"
    ]
    
    is_offline = os.getenv("IS_OFFLINE", "False").lower() in ('true', '1', 't', 'yes')
    
    if is_offline:
        #prende le date e rimuove eventuali fusi orari per evitare errori di calcolo
        data_inizio_str = os.getenv("DATA_INIZIO")
        data_fine_str = os.getenv("DATA_FINE")
        
        inizio = pd.to_datetime(data_inizio_str).tz_localize(None)
        ultimo_giorno = pd.to_datetime(data_fine_str).tz_localize(None)
        
        #calcoliamo esattamente quanti giorni sono
        num_giorni = (ultimo_giorno.date() - inizio.date()).days + 1
        print(f"MOD_OFFLINE: scarico {num_giorni}")
        
    else:
        #modalità Live
        ultimo_giorno = datetime.now()
        try:
            num_giorni = int(os.getenv('GIORNI', 7))
        except ValueError:
            print("variabile .env (GIORNI) non valida.\ndefault (7).")
            num_giorni = 7
        print(f"MOD_LIVE: scarico {num_giorni}")

    #stabilire il giorno dall'ultimo
    mese_ultimo = ultimo_giorno.month
    giorno_settimana_ultimo = ultimo_giorno.weekday()
    
    nome_cartella_mese = mesi_mappa.get(mese_ultimo)
    percorso_cartella_mese = os.path.join(INPUT_DIR, nome_cartella_mese)
    
    if not os.path.exists(percorso_cartella_mese):
        print(f"ERRORE: mese non trovato ({percorso_cartella_mese})")
        return None

    dfs = []
    for i in range(num_giorni):
        #mantiene l'ordine cronologico
        indice_giorno = (giorno_settimana_ultimo - num_giorni + 1 + i) % 7
        nome_file = giorni_file[indice_giorno]
        percorso_file = os.path.join(percorso_cartella_mese, nome_file)
        
        if os.path.exists(percorso_file):
            try:
                df = pd.read_csv(percorso_file, low_memory=False)
                dfs.append(df)
            except Exception as errore:
                print(errore)
        else:
            print(f"{nome_file} non trovato.")

    if dfs:
        df_baseline = pd.concat(dfs, ignore_index=True)
        totale_minuti = len(df_baseline)
        
        #fissiamo la fine della giornata dell'ultimo giorno
        fine_giornata_ultimo = ultimo_giorno.replace(hour=23, minute=59, second=0, microsecond=0)
        
        #spalmiamo i minuti totali all'indietro
        nuove_date = pd.date_range(end=fine_giornata_ultimo, periods=totale_minuti, freq='min')
        df_baseline['Data-Ora_dt'] = nuove_date
        
        df_baseline = df_baseline[df_baseline['Data-Ora_dt'] <= ultimo_giorno].copy()
        
        #pulizia colonne e formattazione per il CSV
        df_baseline['Data-Ora'] = df_baseline['Data-Ora_dt'].dt.strftime('%d/%m/%Y-%H:%M:%S')
        df_baseline = df_baseline.drop(columns=['Data-Ora_dt'])
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        percorso_salvataggio = os.path.join(OUTPUT_DIR, "dataset_GREEND.csv")
        df_baseline.to_csv(percorso_salvataggio, index=False)
        
        return df_baseline
    else:
        return None

if __name__ == "__main__":
    genera_baseline()