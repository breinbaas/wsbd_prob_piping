import numpy as np


class InputData:
    def __init__(self, dijktraject, dijkvak, d_exit_m, L_u_m,D_m,k_z_m,d_70_m,h_exit_m,vol_m,hydra_data_hf,hydra_data_f) -> None:
        self.dijktraject = dijktraject # naam / code dijktraject
        self.dijkvak = dijkvak # naam dijkvak
        self.d_exit_m = d_exit_m # Effectieve deklaagdikte
        self.L_u_m = L_u_m # Kwelweglengte
        self.D_m =D_m  # Dikte watervoerend pakket
        self.k_z_m = k_z_m # Doorlatendheid aquifer
        self.d_70_m = d_70_m # d70 bovenste laag
        self.h_exit_m =h_exit_m  # Polderpeil
        self.vol_m =vol_m  # Verzadigd gewicht deklaag
        self.hydra_data_hf =hydra_data_hf  # waterstanden
        self.hydra_data_f = hydra_data_f # kansen
