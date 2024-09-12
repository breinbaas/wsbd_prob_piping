from pydantic import BaseModel, ConfigDict
import numpy as np


class InputData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    dijkvak: str  # naam dijkvak
    d_exit_m: float  # Effectieve deklaagdikte
    L_u_m: float  # Kwelweglengte
    D_m: float  # Dikte watervoerend pakket
    k_z_m: float  # Doorlatendheid aquifer
    d_70_m: float  # d70 bovenste laag
    h_exit_m: float  # Polderpeil
    vol_m: float  # Verzadigd gewicht deklaag
    hydra_data_hf: np.array  # waterstanden
    hydra_data_f: np.array  # kansen
