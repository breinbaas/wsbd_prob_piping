# Import packages

import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path


from scipy.stats import norm
from scipy import integrate
from scipy.stats import lognorm
from scipy.stats import gumbel_r
from scipy.stats import linregress

from objects import InputData
from prob_functions import prob_analysis


DIJKTRAJECT = "34-1"
GEGEVENS_XLSX = f"data/{DIJKTRAJECT}/{DIJKTRAJECT}_LBO-1.xlsx"
HYDRA_XLSX = f"data/{DIJKTRAJECT}/{DIJKTRAJECT}_Hydra.xlsx"

if not Path(GEGEVENS_XLSX).exists():
    print("Geen gegevens bestand ('{GEGEVENS_XLSX}') gevonden.")

if not Path(HYDRA_XLSX).exists():
    print("Geen hydra bestand ('{GEGEVENS_XLSX}') gevonden.")

# Create output paths if not exist
Path("./output").mkdir(parents=True, exist_ok=True)

# Inlezen gegevens
df_gegevens = pd.read_excel(GEGEVENS_XLSX)
# hernoem de kolommen omdat spaties ook meetellen in de kolomnamen
df_gegevens.columns = [
    str(c) for c in df_gegevens
]  # omdat we int als str willen behandelen
df_gegevens.columns = [c.lower().strip() for c in df_gegevens.columns]
# idem voor de rijnamen
df_gegevens["dijkvak"] = df_gegevens["dijkvak"].str.strip()
df_gegevens["dijkvak"] = df_gegevens["dijkvak"].str.lower()
# index op de parameternamen
df_gegevens.set_index("dijkvak", inplace=True)

# Inlezen Hydra
df_hydra = pd.read_excel(HYDRA_XLSX)
df_hydra.columns = [str(c) for c in df_hydra]
df_hydra.columns = [c.lower().strip() for c in df_hydra.columns]


# en we zijn zo ver...
for col in df_gegevens.columns:
    parameters = df_gegevens[col]

    # get hydra data
    try:
        hydra_data_hf = df_hydra[col].to_numpy()[1:].astype(float)
        hydra_data_f = df_hydra.iloc[:, 0].to_numpy()[1:].astype(float)
    except Exception as e:
        print(f"Could not get hydra data for dijkvak '{col}', got error '{e}'")
        continue

    data = InputData(
        dijkvak=col,
        d_exit_m=parameters["effectieve deklaagdikte"],
        L_u_m=parameters["kwelweglengte"],
        D_m=parameters["dikte watervoerend pakket"],
        k_z_m=parameters["doorlatendheid aquifer"],
        d_70_m=parameters["d70 bovenste laag"],
        h_exit_m=parameters["polderpeil"],
        vol_m=parameters["verzadigd gewicht deklaag"],
        hydra_data_hf=hydra_data_hf,
        hydra_data_f=hydra_data_f,
    )
    prob_analysis(data)
    break
