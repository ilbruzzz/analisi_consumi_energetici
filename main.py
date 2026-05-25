from export.export import salva_export_hassio
from manipolazione_dati.pulizia_csv import pulisci_e_aggrega_csv
from export.export_consumi_nazionali import scarica_mix_energetico
from manipolazione_dati.maipola_df_GREEND import genera_baseline
from manipolazione_dati.normalizza_GREEND import esegui_normalizzazione


#estrazione dati da hassio
salva_export_hassio()

#pulizia e aggregazione csv (Genera il file pulito in manipolazione_dati/data)
pulisci_e_aggrega_csv()

#scrarica il mix energetico (Incrocia le date dal file pulito)
scarica_mix_energetico()

#genera il file GREEND_raw pulito da 
genera_baseline()

#normalizzazione GREEND_raw con portale dei consumi
esegui_normalizzazione()