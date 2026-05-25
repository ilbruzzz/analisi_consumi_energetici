'''sistemato il formato in 24h da 00:00 a 23:59 per unificarlo ai dari del sensore'''
'''il fill è stato fatto per gli ultimi 10 min poichè i dati non erano presenti nell'excel'''

import os
import pandas as pd
import numpy as np

cartella_base = os.path.dirname(os.path.abspath(__file__))

for root, dirs, files in os.walk(cartella_base):
    for nome_file in files:
        if nome_file.endswith('.csv'):
            percorso_file = os.path.join(root, nome_file)
            
            try:
                #leggiamo il file già processato
                df_pulito = pd.read_csv(percorso_file, low_memory=False)
                
                if "Data-Ora" not in df_pulito.columns:
                    continue
                
                #controlliamo che i dati siano in ordine cronologico
                df_pulito["Data-Ora"] = pd.to_datetime(df_pulito["Data-Ora"], format="%d/%m/%Y-%H:%M:%S", errors="coerce")
                df_pulito = df_pulito.sort_values("Data-Ora")
                
                #assicuriamoci che la colonna "Consumo" sia considerata
                df_pulito["Consumo"] = pd.to_numeric(df_pulito["Consumo"], errors="coerce")
                
                #trasformiamo tutti gli 0 in valori nulli (NaN)
                df_pulito["Consumo"] = df_pulito["Consumo"].replace(0.0, np.nan)
                
                #usiamo ffill per riempire i buchi trascinando l'ultimo valore valido
                df_pulito["Consumo"] = df_pulito["Consumo"].ffill()
                
                #per sicurezza anche bfill, e se fallisce rimettiamo a 0
                df_pulito["Consumo"] = df_pulito["Consumo"].bfill().fillna(0)
                
                df_pulito["Data-Ora"] = df_pulito["Data-Ora"].dt.strftime("%d/%m/%Y-%H:%M:%S")
                
                df_pulito.to_csv(percorso_file, index=False)
                
            except Exception as errore:
                print(errore)

print("\nOK")