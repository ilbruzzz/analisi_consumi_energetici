import os
import pandas as pd

cartella_base = os.path.dirname(os.path.abspath(__file__))

mesi_mappa = {
    '1_gennaio': '01_gennaio', '2_febbraio': '02_febbraio', '3_marzo': '03_marzo',
    '4_aprile': '04_aprile', '5_maggio': '05_maggio', '6_giugno': '06_giugno',
    '7_luglio': '07_luglio', '8_agosto': '08_agosto', '9_settembre': '09_settembre'
}

giorni_mappa = {
    'lunedi.csv': '01_lunedi.csv', 'martedi.csv': '02_martedi.csv',
    'mercoledi.csv': '03_mercoledi.csv', 'giovedi.csv': '04_giovedi.csv',
    'venerdi.csv': '05_venerdi.csv', 'sabato.csv': '06_sabato.csv',
    'domenica.csv': '07_domenica.csv'
}

for nome_dir in os.listdir(cartella_base):
    percorso_vecchio = os.path.join(cartella_base, nome_dir)
    if os.path.isdir(percorso_vecchio) and nome_dir in mesi_mappa:
        percorso_nuovo = os.path.join(cartella_base, mesi_mappa[nome_dir])
        os.rename(percorso_vecchio, percorso_nuovo)

for root, dirs, files in os.walk(cartella_base):
    for nome_file in files:
        if nome_file.endswith(".csv"):
            
            percorso_attuale = os.path.join(root, nome_file)
            nuovo_nome_file = giorni_mappa.get(nome_file, nome_file) 
            percorso_nuovo = os.path.join(root, nuovo_nome_file)
            
            if nome_file != nuovo_nome_file:
                os.rename(percorso_attuale, percorso_nuovo)
            
            try:
                df = pd.read_csv(percorso_nuovo, low_memory=False)
                
                #pulizia base e calcolo consumi
                df = df[df["timestamp"] != "timestamp"].copy()
                df["Data-Ora"] = pd.to_datetime(pd.to_numeric(df["timestamp"], errors="coerce"), unit="s")
                df = df.drop(columns=["timestamp"])
                
                for col in df.columns:
                    if col != "Data-Ora":
                        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                
                df["Consumo"] = df.drop(columns=["Data-Ora"]).sum(axis=1)
                df_clean = df[["Data-Ora", "Consumo"]].copy()
                
                df_clean.set_index("Data-Ora", inplace=True)
                
                #calcoliamo la media raggruppando per 1 minuto
                df_clean = df_clean.resample("1min").mean()
                
                #rimuoviamo eventuali righe vuote se c'erano buchi nei dati
                df_clean = df_clean.dropna(subset=["Consumo"])
                
                #facciamo tornare "Data-Ora" come colonna normale
                df_clean = df_clean.reset_index()
                
                #formattazione finale (mantiene il formato GG/MM/AAAA-HH:MM:SS)
                df_clean = df_clean.sort_values("Data-Ora")
                df_clean["Data-Ora"] = df_clean["Data-Ora"].dt.strftime("%d/%m/%Y-%H:%M:%S")
                
                #sovrascrittura del file
                df_clean.to_csv(percorso_nuovo, index=False)
                
            except Exception as erorre:
                print(f"errore nel processare {percorso_nuovo}: {erorre}")

print("\nOK")