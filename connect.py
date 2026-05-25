import requests
import os
from dotenv import load_dotenv
import datetime

load_dotenv()
URL_HASSIO = os.getenv("URL_HASSIO")
ENTITY_ID = os.getenv("ENTITY_ID")
TOKEN = os.getenv("TOKEN")
GIORNI = os.getenv("GIORNI")

is_offline_str = str(os.getenv("IS_OFFLINE", "False")).strip().lower()
IS_OFFLINE = is_offline_str in ['true', '1', 't', 'yes']

DATA_INIZIO = os.getenv("DATA_INIZIO")
DATA_FINE = os.getenv("DATA_FINE")

def connessione_hassio():
    """
    connessione ad hassio tramite token, recupero il sensor.pinza_amperometrica_consumo_istantaneo
    """
    adesso_locale = datetime.datetime.now().astimezone()

    #seleziona tra modalità specifica Offline o modalità Giorni
    if IS_OFFLINE and DATA_INIZIO:
        print(f"MODALITA OFFLINE: scarico i dati dal ({DATA_INIZIO} a {DATA_FINE})")
        
        #usa la data di inizio del .env
        timestamp_inizio = DATA_INIZIO
        
        #se c'è una data di fine usa quella, altrimenti usa "adesso"
        if DATA_FINE:
            timestamp_fine = DATA_FINE
        else:
            timestamp_fine = adesso_locale.astimezone(datetime.timezone.utc).isoformat()
            
    else:
        print(f"MODALITA GIORNI: scarico gli ultimi ({GIORNI}) giorni.")
        
        mezzanotte_locale = adesso_locale.replace(hour=0, minute=0, second=0, microsecond=0)
        
        try:
            giorni_fix = int(GIORNI) - 1
        except (ValueError, TypeError):
            giorni_fix = 0
            
        data_inizio_locale = mezzanotte_locale - datetime.timedelta(days=giorni_fix)
        
        timestamp_inizio = data_inizio_locale.astimezone(datetime.timezone.utc).isoformat()
        timestamp_fine = adesso_locale.astimezone(datetime.timezone.utc).isoformat()

    #creazione url e parametri
    url = f"{URL_HASSIO}/api/history/period/{timestamp_inizio}"

    parametri = {
        "filter_entity_id": ENTITY_ID,
        "end_time": timestamp_fine
    }

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, params=parametri)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError:
        print("impossibile connettersi ad hassio. controlla l'url.")
    except requests.exceptions.HTTPError as errore:
        print(f"errore http: {errore}.")
    except Exception as errore:
        print(errore)

if __name__ == "__main__":
    connessione_hassio()