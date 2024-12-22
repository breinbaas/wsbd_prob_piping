import numpy as np
from scipy.stats import lognorm, norm, linregress, gumbel_r
import math
import logging

# Deterministen
ETA = 0.25
GAMMA_SUB = 16.5
GAMMA_WATER = 10
R_C = 0.3
THETA = 37
D70M = 2.08e-4
GRAVITY = 9.81
VISC = 1.33e-6


def prob_analysis(
    waterstanden,
    num_simulations: int,  # aantal simulaties voor MC
    d_exit_eff_m: float,  # effectieve deklaagdikte
    d_exit_eff_s: float,  # s_effectieve deklaagdikte
    d_exit_tot_m: float,  # totale deklaagdikte
    d_exit_tot_s: float,  # s_totale deklaagdikte
    L_u_m: float,  # kwelweglengte
    L_u_cov: float,  # cov_kwelweglengte
    D_m: float,  # dikte watervoerend pakket
    D_s: float,  # s_dikte watervoerendpakket
    k_z_m: float,  # doorlatendheid aquifer
    k_z_cov: float,  # cov_doorlatendheid
    d_70_m: float,  # d70 bovenste laag
    d_70_cov: float,  # s d70 bovenste laag
    h_exit_m: float,  # polderpeil
    h_exit_s: float,  # s polderpeil
    vol_m: float,  # verzadigd gewicht deklaag
    vol_s: float,  # s verzadigd gewicht deklaag
    demping_m: float,  # dempingsfactor
    demping_s: float,  # s dempingsfactor
    krit_heave_gr: float,  # kritiek heave gradient
    voorland_maaiveld: float = np.nan,  # maaiveldhoogte van een voorland of np.nan als die er niet is
    voorland_lengte: float = np.nan,  # voorland lengte dat bij de kwelweglengte opgeteld moet worden
):
    h_start = 1.5
    h_einde = round(waterstanden.hoogtes[-1], 2) + 1
    stap = 0.1

    r_waterstanden = np.arange(h_start, h_einde + stap, stap)

    p = []  # Totale faalkans
    p_te = []  # Faalkans terugschrijdende erosie
    p_op = []  # Faalkans opbarsten
    p_he = []  # Faalkans heave

    if not np.isnan(voorland_maaiveld) and not np.isnan(voorland_lengte):
        L_u_m += voorland_lengte

    for h in r_waterstanden:
        logging.info("-" * 80)
        logging.info(f"Waterlevel: {h}")
        logging.info("-" * 80)

        f_h = piping_sellmeijer(
            river_level=round(h, 1),
            num_simulations=num_simulations,
            d_exit_eff_m=d_exit_eff_m,
            d_exit_eff_s=d_exit_eff_s,
            d_exit_tot_m=d_exit_tot_m,
            d_exit_tot_s=d_exit_tot_s,
            L_u_m=L_u_m,
            L_u_cov=L_u_cov,
            D_m=D_m,
            D_s=D_s,
            k_z_m=k_z_m,
            k_z_cov=k_z_cov,
            d_70_m=d_70_m,
            d_70_cov=d_70_cov,
            h_exit_m=h_exit_m,
            h_exit_s=h_exit_s,
            vol_m=vol_m,
            vol_s=vol_s,
            demping_m=demping_m,
            demping_s=demping_s,
            krit_heave_gr=krit_heave_gr,
        )  # Monte Carlo

        p.append(f_h[0])
        p_te.append(f_h[1])
        p_op.append(f_h[2])
        p_he.append(f_h[3])

    return r_waterstanden, p, p_te, p_op, p_he


# Random trekking van normaal verdeling
def r_norm(mu, sigma, num):
    if sigma == 0:
        return np.ones(num) * mu
    return norm.rvs(loc=mu, scale=sigma, size=num)


# Random trekking van lognormaal verdeling
def r_ln_s(mu, sigma, num):
    if sigma == 0:
        return np.ones(num) * mu

    mu_ln = np.log(mu / np.sqrt(1 + (sigma / mu) ** 2))
    sigma_ln = np.sqrt(np.log(1 + (sigma / mu) ** 2))

    return lognorm.rvs(scale=np.exp(mu_ln), s=sigma_ln, size=num)


def r_gumbel(mu, sigma, num):

    beta = sigma * np.sqrt(6) / np.pi
    loc = mu - beta * np.euler_gamma

    return gumbel_r.rvs(loc=loc, scale=beta, size=num)


# Probabilistische analyse Sellmeijer met variabele waterstand
def piping_sellmeijer(
    river_level: float,  # rivier waterstand
    num_simulations: int,  # aantal simulaties voor MC
    d_exit_eff_m: float,  # effectieve deklaagdikte
    d_exit_eff_s: float,  # s_effectieve deklaagdikte
    d_exit_tot_m: float,  # totale deklaagdikte
    d_exit_tot_s: float,  # s_totale deklaagdikte
    L_u_m: float,  # kwelweglengte
    L_u_cov: float,  # cov_kwelweglengte
    D_m: float,  # dikte watervoerend pakket
    D_s: float,  # s_dikte watervoerendpakket
    k_z_m: float,  # doorlatendheid aquifer
    k_z_cov: float,  # cov_doorlatendheid
    d_70_m: float,  # d70 bovenste laag
    d_70_cov: float,  # s d70 bovenste laag
    h_exit_m: float,  # polderpeil
    h_exit_s: float,  # s polderpeil
    vol_m: float,  # verzadigd gewicht deklaag
    vol_s: float,  # s verzadigd gewicht deklaag
    demping_m: float,  # dempingsfactor
    demping_s: float,  # s dempingsfactor
    krit_heave_gr: float,  # kritiek heave gradient
):
    logging.info(f"river_level                  : {river_level}")
    logging.info(f"aantal simulaties            : {num_simulations}")
    logging.info(f"effectieve laagdikte         : {d_exit_eff_m}")
    logging.info(f"s effectieve deklaagdikte    : {d_exit_eff_s}")
    logging.info(f"totale deklaagdikte          : {d_exit_tot_m}")
    logging.info(f"s totale deklaagdikte        : {d_exit_tot_s}")
    logging.info(f"kwelweglengte                : {L_u_m}")
    logging.info(f"cov kwelweglengte            : {L_u_cov}")
    logging.info(f"dikte watervoerend pakket    : {D_m}")
    logging.info(f"s dikte watervoerend pakket  : {D_s}")
    logging.info(f"polderpeil                   : {k_z_m}")
    logging.info(f"s polderpeil                 : {k_z_cov}")
    logging.info(f"d70 bovenste laag            : {d_70_m}")
    logging.info(f"s d70 bovenste laag          : {d_70_cov}")
    logging.info(f"polderpeil                   : {h_exit_m}")
    logging.info(f"s polderpeil                 : {h_exit_s}")
    logging.info(f"verzadigd gewicht deklaag    : {vol_m}")
    logging.info(f"s verzadigd gewicht deklaag  : {vol_s}")
    logging.info(f"dempingsfactor               : {demping_m}")
    logging.info(f"s dempingsfactor             : {demping_s}")
    logging.info(f"kritiek heave gradient       : {krit_heave_gr}")

    L_u_s = L_u_m * L_u_cov
    k_z_s = k_z_m * k_z_cov
    d_70_s = d_70_m * d_70_cov
    r_s = demping_s

    # Random trekkingen stochasten
    d_exit_eff = r_ln_s(d_exit_eff_m, d_exit_eff_s, num_simulations)
    d_exit_tot = r_ln_s(d_exit_tot_m, d_exit_tot_s, num_simulations)
    L_u = r_ln_s(L_u_m, L_u_s, num_simulations)
    D = r_ln_s(D_m, D_s, num_simulations)
    k_z = r_ln_s(k_z_m, k_z_s, num_simulations)
    d_70 = r_ln_s(d_70_m, d_70_s, num_simulations)
    h_exit = r_norm(h_exit_m, h_exit_s, num_simulations)
    vol = r_ln_s(vol_m - 10, vol_s, num_simulations) + 10
    r_d = r_ln_s(demping_m, r_s, num_simulations)
    i_ch = np.ones(num_simulations) * krit_heave_gr

    # Model factoren
    m_p = np.ones(num_simulations)  # r_ln_s(1.0, 0.12, num)
    m_u = np.ones(num_simulations)  # r_ln_s(1.0, 0.10, num)

    ### Terugschrijdende Erosie (Sellmeijer)
    # Belasting
    S_te = river_level - h_exit - R_C * d_exit_tot

    # Weerstand
    kappa = VISC / GRAVITY * k_z
    F_res = ETA * GAMMA_SUB / 10 * np.tan(THETA * np.pi / 180)
    F_scale = (D70M / (kappa * L_u) ** (1 / 3)) * (d_70 / D70M) ** 0.4
    F_geometry = 0.91 * (D / L_u) ** (0.28 / ((D / L_u) ** 2.8 - 1) + 0.04)
    DeltaH_c = F_res * F_scale * F_geometry * L_u
    R_te = DeltaH_c * m_p

    ### Opbarsten
    # Belasting
    phi_exit = h_exit + r_d * (river_level - h_exit)
    d_phi = phi_exit - h_exit
    S_op = d_phi

    # Weerstand
    stijghoog_k = d_exit_eff * (vol - GAMMA_WATER) / GAMMA_WATER
    R_op = stijghoog_k * m_u

    ### Heave
    # Belasting
    S_he = (phi_exit - h_exit) / d_exit_tot

    # Weerstand
    R_he = i_ch

    # Faalt als Zte, Zhe en Zop < 0
    result = np.where((R_te < S_te) & (R_op < S_op) & (R_he < S_he), 1, 0)

    # Individuele faalkansen
    res_te = np.where(R_te < S_te, 1, 0)
    res_op = np.where(R_op < S_op, 1, 0)
    res_he = np.where(R_he < S_he, 1, 0)

    return np.mean(result), np.mean(res_te), np.mean(res_op), np.mean(res_he)


def gumbel_fit(F: np.array, h_F: np.array):
    F_log = -np.log(-np.log(1 - F))
    a, b, _, _, _ = linregress(F_log, h_F)
    return b, a


def prob_sellmeijer_met_gumbel(parameters, num: int):
    mu, sigma = gumbel_fit(parameters.hydra_data_f, parameters.hydra_data_hf)
    h = r_gumbel(mu, sigma, num)

    # Faalkans onder overleefde op 0
    h[h < parameters.overleefde_waterstand] = -100

    return piping_sellmeijer(parameters, h, num)


def gumbel_pdf(parameters):
    mu, beta = gumbel_fit(parameters.hydra_data_f, parameters.hydra_data_hf)

    h_start = 1.5
    h_einde = round(parameters.hydra_data_hf[-1], 2) + 1
    stap = 0.1

    x = np.arange(h_start, h_einde + stap, stap)

    return x, (1 / beta) * np.exp(-(x - mu) / beta - np.exp(-(x - mu) / beta))
