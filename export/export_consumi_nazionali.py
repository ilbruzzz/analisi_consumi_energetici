import pandas as pd
import requests
import os
import datetime
from dotenv import load_dotenv

def scarica_mix_energetico():
    """
    Scarica il mix energetico nazionale gestendo correttamente i fusi orari
    tra Italia e i server europei.
    """
    load_dotenv()
    
    FILE_PULITO = os.getenv("FILE_PULITO")
    MIX_ENERGICO = os.getenv("EXPORT_MIX_ENERGETICO_NAZIONALE")
    
    if not FILE_PULITO or not MIX_ENERGICO:
        print("ERRORE: Variabili 'FILE_PULITO' o 'EXPORT_MIX_ENERGETICO_NAZIONALE' mancanti nel .env")
        return False

    #il file di hassio pulito si trova qui, e salveremo il mix qui per i grafici
    CARTELLA_DATA = os.path.join("manipolazione_dati", "data")
    
    percorso_consumi = os.path.join(CARTELLA_DATA, FILE_PULITO)
    
    if not os.path.exists(percorso_consumi):
        print(f"ERRORE: File consumi utente non trovato in -> {percorso_consumi}")
        print("Esegui prima lo script di pulizia dati!")
        return False

    df_consumi = pd.read_csv(percorso_consumi)
    df_consumi['Data-Ora'] = pd.to_datetime(df_consumi['Data-Ora'], format='%d/%m/%Y-%H:%M:%S')
    
    start = df_consumi['Data-Ora'].min()
    end = df_consumi['Data-Ora'].max()

    #trasformiamo l'orario in orario italiano e poi in UTC per l'API
    start_utc = start.tz_localize('Europe/Rome').tz_convert('UTC')
    end_utc = end.tz_localize('Europe/Rome').tz_convert('UTC')

    url_api = "https://api.energy-charts.info/public_power"
    parametri_richiesta = {
        "country": "it", 
        "start": start_utc.strftime('%Y-%m-%dT%H:%MZ'), 
        "end": end_utc.strftime('%Y-%m-%dT%H:%MZ')
    }

    print(f"Download mix energetico dal ({start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')})")
    try:
        risposta = requests.get(url_api, params=parametri_richiesta, timeout=30)
        risposta.raise_for_status()
        dati_json = risposta.json()
        
        timestamps_convertiti = [datetime.datetime.fromtimestamp(t) for t in dati_json['unix_seconds']]
        df_mix_nazionale = pd.DataFrame({'datetime': timestamps_convertiti})
        
        for fonte_produzione in dati_json['production_types']:
            df_mix_nazionale[fonte_produzione['name']] = fonte_produzione['data']
        
        os.makedirs(CARTELLA_DATA, exist_ok=True)
        percorso_salvataggio = os.path.join(CARTELLA_DATA, MIX_ENERGICO)
        df_mix_nazionale.to_csv(percorso_salvataggio, index=False)
        
        return True
        
    except Exception as errore:
        print(errore)
        return False

if __name__ == "__main__":
    scarica_mix_energetico()