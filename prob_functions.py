import numpy as np
from scipy.stats import lognorm, norm, linregress, gumbel_r
import math


def prob_analysis(
    waterstanden,
    parameters,
    sim,
    h_exit_m=np.nan,
    kwelweglengte: float = np.nan,
    kwelweglengte_offset: float = 0.0,
    deklaagdikte: float = np.nan,
):
    h_start = 1.5
    h_einde = round(waterstanden.hoogtes[-1], 2) + 1
    stap = 0.1

    r_waterstanden = np.arange(h_start, h_einde + stap, stap)

    p = []  # Totale faalkans
    p_te = []  # Faalkans terugschrijdende erosie
    p_op = []  # Faalkans opbarsten
    p_he = []  # Faalkans heave

    for h in r_waterstanden:

        # if h < h voorland, l = l + l voorland else nothing
        f_h = piping_sellmeijer(
            parameters, round(h, 1), sim, h_exit_m, kwelweglengte, kwelweglengte_offset
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
    parameters,
    h,
    num: int,
    h_exit_m=np.nan,
    kwelweglengte: float = np.nan,  # mogelijkheid om de waarde uit de parameters te overschrijven voor bv demping of berm
    kwelweglengte_offset: float = 0.0,
    deklaagdikte: float = np.nan,  # mogelijkheid om de waarde uit parameters voor de deklaagdikte te overschrijven
    apply_voorland: bool = False,
):
    # Standaardafwijkingen stochasten
    d_exit_eff_s = parameters.d_exit_eff_s
    d_exit_tot_s = parameters.d_exit_tot_s
    L_u_s = parameters.L_u_m * parameters.L_u_cov
    D_s = parameters.D_s
    k_z_s = parameters.k_z_m * parameters.k_z_cov
    d_70_s = parameters.d_70_m * parameters.d_70_cov
    h_exit_s = parameters.h_exit_s
    vol_s = parameters.vol_s
    r_s = parameters.demping_s

    # check of de deklaagdikte overschreven is
    if np.isnan(deklaagdikte):
        deklaagdikte = parameters.d_exit_eff_m
        # TODO -> waarschuwing dat dit ook de totale deklaagdikte aanpast (in functie omschrijving)
        totale_deklaagdikte = parameters.d_exit_tot_m
    else:
        totale_deklaagdikte = deklaagdikte

    # Random trekkingen stochasten
    d_exit_eff = r_ln_s(deklaagdikte, d_exit_eff_s, num)
    d_exit_tot = r_ln_s(totale_deklaagdikte, d_exit_tot_s, num)

    # als de kwelweglengte niet overschreven is gebruiken
    # we de standaard kwelweglengte
    if np.isnan(kwelweglengte):
        kwelweglengte = parameters.L_u_m

    # voeg een eventuele offset toe (bv door een berm)
    kwelweglengte += kwelweglengte_offset

    if apply_voorland and (
        not math.isnan(parameters.voorland_maaiveld)
        and h <= parameters.voorland_maaiveld
    ):  # als de waterhoogte lager is dan de voor landhoogte
        # voeg de voorlandlengte aan de kwelweglengte toe
        L_u = r_ln_s(kwelweglengte + kwelweglengte, L_u_s, num)
    else:
        L_u = r_ln_s(kwelweglengte, L_u_s, num)

    D = r_ln_s(parameters.D_m, D_s, num)
    k_z = r_ln_s(parameters.k_z_m, k_z_s, num)
    d_70 = r_ln_s(parameters.d_70_m, d_70_s, num)

    if not np.isnan(h_exit_m):  # override h_exit_m with given value
        h_exit = r_norm(h_exit_m, h_exit_s, num)
    else:
        h_exit = r_norm(parameters.h_exit_m, h_exit_s, num)

    vol = r_ln_s(parameters.vol_m - 10, vol_s, num) + 10
    r_d = r_ln_s(parameters.demping_m, r_s, num)
    i_ch = np.ones(num) * parameters.krit_heave_gr

    # Model factoren
    m_p = np.ones(num)  # r_ln_s(1.0, 0.12, num)
    m_u = np.ones(num)  # r_ln_s(1.0, 0.10, num)

    # Deterministen
    eta = 0.25
    gamma_sub = 16.5
    gamma_water = 10
    r_c = 0.3
    theta = 37
    d70m = 2.08e-4
    g = 9.81
    visc = 1.33e-6

    ### Terugschrijdende Erosie (Sellmeijer)
    # Belasting
    S_te = h - h_exit - r_c * d_exit_tot

    # Weerstand
    kappa = visc / g * k_z
    F_res = eta * gamma_sub / 10 * np.tan(theta * np.pi / 180)
    F_scale = (d70m / (kappa * L_u) ** (1 / 3)) * (d_70 / d70m) ** 0.4
    F_geometry = 0.91 * (D / L_u) ** (0.28 / ((D / L_u) ** 2.8 - 1) + 0.04)
    DeltaH_c = F_res * F_scale * F_geometry * L_u
    R_te = DeltaH_c * m_p

    ### Opbarsten
    # Belasting
    phi_exit = h_exit + r_d * (h - h_exit)
    d_phi = phi_exit - h_exit
    S_op = d_phi

    # Weerstand
    stijghoog_k = d_exit_eff * (vol - gamma_water) / gamma_water
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
