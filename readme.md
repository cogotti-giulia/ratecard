
# Fornitori Colt e Twt (sometimes called Unidata)

Vedi documento su http://docs.voiptelitalia.it/s/b97de51e-ab9f-4e0c-86da-b7f3ca993e34 per avere una panoramica generale.

1. Crea un database mysql e assicurati di sistemare la configurazione nel file `utils/database/db_config.py`.
2. Lancia lo script python desiderato

## Script per inizializzazione listini

1. Crea un database mysql e assicurati di sistemare la configurazione nel file `utils/database/db_config.py`.
2. Lancia lo script con
   ```bash
   python init.py 
     -o "CH" "IT" 
     -s "twt" "colt" 
     --ratecard-twt-fn "docs/twt/Rates_VOIPTEL INTERNATIONAL SA (SWD Voip)_SWITCHED GOLD - DIRETTO_20220527_125057.csv" 
     --surcharge-twt-fn "docs/twt/OBR_TWT_20230804.xlsx" 
     --ratecard-colt-fn "docs/colt/CH_VoIPTel_Inter_2025.07.29.csv" 
     --surcharge-origin-colt-fn "docs/colt/Colt-Voice-Origin-Surcharges-v.87.0.xlsx" 
     --surcharge-asr-colt-fn "docs/colt/Origination-Charges-ASR-January-2026.xlsx"
   ```

| PARAMETRI                       | HELP                                                                                                                                                                                                | VALORI                                                                                           | OBBLIGATORIO                                      |
|---------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|---------------------------------------------------|
| `-o` `--surcharge-origin`       | Codice del paese d’origine per il quale applicare il surcharge one del surcharge.                                                                                                                   | lista di str. **Una o più** tra le scelte in COUNTRY_CODE_NAME_MAP nel file `utils/constants.py` | **✅** |
| `-s` `--suppliers`              | Lista di fornitori (**≥2**). Le operazioni di merge e peso rotta vengono applicate a tutte le coppie ordinate.                                                                                      | lista di str. **Due o più** tra le chiavi di RATECARD_CONFIG nel file `utils/config.py`          | **✅** |
| `--ratecard-twt-fn`             | Nome del file csv del listino di **TWT**                                                                                                                                                            | str                                                                                              | **✅** **(solo se specificato TWT nei supplier)**  |
| `--ratecard-colt-fn`            | Nome del file csv del listino di **COLT**                                                                                                                                                           | str                                                                                              | **✅** **(solo se specificato COLT nei supplier)** |
| `--surcharge-twt-fn`            | Nome del file xlxs di sovrapprezzo di **TWT**                                                                                                                                                       | str                                                                                              | **✅** **(solo se specificato TWT nei supplier)**  |
| `--surcharge-origin-colt-fn`    | Nome del primo file xlxs di sovrapprezzo di **COLT**. Quello che specifica il gruppo di regole di surcharge da applicare a partire da origine e destinazione. Da combinare poi con il secondo file. | str                                                                                              | **✅** **(solo se specificato COLT nei supplier)** |
| `--surcharge-asr-colt-fn`       | Nome del secondo file xlxs di sovrapprezzo di **COLT**. Quello che, dato codice destinazione e gruppo di surcharge, fornisce il *prezzo* da applicare alla rotta.                                   | str                                                                                              | **✅** **(solo se specificato COLT nei supplier)** |
| `--verbose` NOT YET IMPLEMENTED | Stampa esageratamente tante righe di log.                                                                                                                                                           | bool                                                                                             | **❌**                                             |
| `--dry-run` NOT YET IMPLEMENTED | Esegue una simulazione senza scrivere alcun dato nel DB.                                                                                                                                            | bool                                                                                             | **❌**                                             |


## Script per selezionare dati dai listini finali
1. Assicurarsi di aver prima eseguito l'inizializzazione dei listini
2. Lancia lo script desiderato (tra quelli presenti nella cartella `tools/`) come modulo, quindi utilizzando l'opzione **-m**
   ```bash
    python -m tools.export_satellite_ratecard 
      --origin-country-code "IT" 
      --suppliers "twt" "colt" 
    ```
   
