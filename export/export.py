import os
import pandas as pd
import datetime
from dotenv import load_dotenv
from connect import connessione_hassio

def dati_sensore():
    """
    estrae i dati storici dal sensore di Home Assistant e li formatta.
    """
    dati_grezzi = connessione_hassio()

    if not dati_grezzi or not dati_grezzi[0]:
        print("Errore: Nessun dato trovato dai sensori di Home Assistant.")
        return []

    storico_formattato = []
    lista_stati = dati_grezzi[0]

    for elemento in lista_stati:
        valore_grezzo = elemento.get("state")
        
        try:
            valore_numerico = float(valore_grezzo)
            valore_arrotondato = round(valore_numerico, 2)
        except (ValueError, TypeError):
            valore_arrotondato = valore_grezzo

        #estraiamo data e ora gestendo il fuso orario
        data_utc_str = elemento.get("last_updated")
        
        if data_utc_str:
            data_utc_str = data_utc_str.replace('Z', '+00:00')
            data_obj = datetime.datetime.fromisoformat(data_utc_str).astimezone()
            data_storica_testo = data_obj.strftime("%d/%m/%Y-%H:%M:%S")
        else:
            continue 

        #creiamo un dizionario per facilitare la creazione del df
        storico_formattato.append({
            "Data-Ora": data_storica_testo,
            "Consumo": valore_arrotondato
        })

    return storico_formattato

def salva_export_hassio():
    """
    funzione principale per scaricare i dati e salvarli nel dataset grezzo.
    """
    load_dotenv()
    FILE_ORIGINALE = os.getenv("FILE")
    
    #salviamo i dati grezzi nella cartella dataset per la successiva manipolazione
    OUTPUT_DIR = os.path.join("manipolazione_dati", "data")
    
    if not FILE_ORIGINALE:
        print("variabile 'FILE' non trovata nel .env")
        return False

    lista_dati = dati_sensore()

    if not lista_dati:
        return False

    #creiamo un df dai dati estratti
    df = pd.DataFrame(lista_dati)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    percorso_output = os.path.join(OUTPUT_DIR, FILE_ORIGINALE)

    df.to_csv(percorso_output, index=False)
    return True

if __name__ == "__main__":
    salva_export_hassio()