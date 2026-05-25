import pandas as pd
import os
from dotenv import load_dotenv

def pulisci_e_aggrega_csv():
    load_dotenv()
    
    INPUT_DIR = os.path.join("manipolazione_dati", "data")
    OUTPUT_DIR = os.path.join("manipolazione_dati", "data")
    
    FILE = os.getenv("FILE")
    FILE_PULITO = os.getenv("FILE_PULITO")

    if not FILE or not FILE_PULITO:
        print("ERRORE: Variabili 'FILE' o 'FILE_PULITO' mancanti nel file .env")
        return False

    #definiamo i percorsi dei file esatti
    percorso_input = os.path.join(INPUT_DIR, FILE)
    percorso_output = os.path.join(OUTPUT_DIR, FILE_PULITO)

    if not os.path.exists(percorso_input):
        print(f"ERRORE: File grezzo non trovato ({percorso_input})")
        return False

    df = pd.read_csv(percorso_input)

    #verifichiamo che non ci siano unavable togliendo W e forzando a leggere i numeri
    df["Consumo"] = df["Consumo"].astype(str).str.replace("W", "")
    df["Consumo"] = pd.to_numeric(df["Consumo"], errors="coerce")

    #con ffill prendiamo il valore precedente e lo copiamo nelle righe NaN
    #con bfill prendiamo il valore successivo e lo copiamo nelle righe NaN 
    df["Consumo"] = df["Consumo"].ffill().bfill()

    #convertiamo la data del csv in una data interpretabile
    df['Data-Ora'] = pd.to_datetime(df['Data-Ora'], format='%d/%m/%Y-%H:%M:%S')

    #sovrascriviamo la colonna togliendo i secondi
    df['Data-Ora'] = df['Data-Ora'].dt.floor('min')

    #facciamo la media dei consumi registrati per ogni minuto
    df_pulito = df.groupby('Data-Ora')['Consumo'].mean().reset_index()    
    df_pulito["Consumo"] = df_pulito["Consumo"].round(2)
    
    #rimettiamo la data nel formato originale
    df_pulito['Data-Ora'] = df_pulito['Data-Ora'].dt.strftime('%d/%m/%Y-%H:%M:%S')

    #creiamo la cartella di output se non esiste e salviamo
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_pulito.to_csv(percorso_output, index=False)
    
    return True

if __name__ == "__main__":
    pulisci_e_aggrega_csv()