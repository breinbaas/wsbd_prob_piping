import numpy as np
from scipy.stats import lognorm, gumbel_r, linregress, norm
from scipy import integrate

from objects import InputData
from plotter import plot_gumbel_fit, plot_fc


def prob_analysis(data: InputData):
    mu, beta = gumbel_fit(data.hydra_data_f, data.hydra_data_hf)
    plot_gumbel_fit(
        data.hydra_data_f,
        data.hydra_data_hf,
        mu,
        beta,
        f"output/{data.dijkvak}.gumbel_fit.png",
    )

    # Maak FC curve en bepaal totale faalkans
    # Range waterstanden
    h_start = np.min(data.hydra_data_hf) - 1
    h_einde = np.max(data.hydra_data_hf)
    stap = 0.1
    waterstanden = np.arange(h_start, h_einde + stap, stap)
    num = int(1e6)  # Monte Carlo berekeningen per waterstand
    # P(F|H) -> FC
    p = []
    p_te = []
    p_op = []
    p_he = []
    for h in waterstanden:
        f_h = h_variabel(data, h, num)
        p.append(f_h[0])
        p_te.append(f_h[1])
        p_op.append(f_h[2])
        p_he.append(f_h[3])

    gumbel = gumbel_pdf(waterstanden, mu, beta)
    faalkans = [a * b for a, b in zip(gumbel, p)]
    f_piping = integrate.simpson(faalkans, x=waterstanden)
    betab = -norm.ppf(f_piping)

    # Bepaal kans zonder FC curve.
    # Bepaal faalkans en betrouwbaarheidsindex met h_gumbel
    f_piping_gumbel = h_gumbel(data, num, mu, beta)
    betab_gumbel = -norm.ppf(f_piping_gumbel)

    plot_fc(
        waterstanden,
        p,
        p_te,
        p_op,
        p_he,
        gumbel,
        faalkans,
        f_piping,
        betab,
        f"output/{data.dijkvak}.fc.png",
    )

    print(f"Faalkans = {f_piping_gumbel:.2e}")
    print(f"Betrouwbaarheidsindex = {betab_gumbel:.2f}")


# %% Random trekking uit verdeling
# random trekking van normaal verdeling
def r_norm(mu, sigma, num):
    return norm.rvs(loc=mu, scale=sigma, size=num)


# random trekking van lognormaal verdeling
def r_ln_s(mu, sigma, num):
    mu_ln = np.log(mu / np.sqrt(1 + (sigma / mu) ** 2))
    sigma_ln = np.sqrt(np.log(1 + (sigma / mu) ** 2))

    return lognorm.rvs(scale=np.exp(mu_ln), s=sigma_ln, size=num)


# %% Prob met waterstand variabel
def h_variabel(data: InputData, h: float, num: int):
    d_exit_s = data.d_exit_m * 0.3
    L_u_s = data.L_u_m * 0.1
    D_s = data.D_m * 0.5
    k_z_s = data.k_z_m * 0.5
    d_70_s = data.d_70_m * 0.12
    h_exit_s = 0.1
    vol_s = (data.vol_m - 10) * 0.05

    d_exit = r_ln_s(data.d_exit_m, d_exit_s, num)
    L_u = r_ln_s(data.L_u_m, L_u_s, num)
    D = r_ln_s(data.D_m, D_s, num)
    k_z = r_ln_s(data.k_z_m, k_z_s, num)
    d_70 = r_ln_s(data.d_70_m, d_70_s, num)
    h_exit = r_norm(data.h_exit_m, h_exit_s, num)
    h = h
    vol = r_ln_s(data.vol_m - 10, vol_s, num) + 10
    r_d = 1

    # Model factoren
    m_p = np.ones(num)  # r_ln_s(1.0, 0.12, num)
    m_u = np.ones(num)  # r_ln_s(1.0, 0.10, num)

    # Deterministen
    eta = 0.25
    gamma_subparticles = 16.5
    gamma_water = 9.81
    r_c = 0.3
    theta = 37
    d70m = 2.08e-4
    g = 9.81
    visc = 1.33e-6

    ### Terugschrijdende Erosie
    # Belasting
    S_te = h - h_exit - r_c * d_exit

    # Weerstand
    kappa = visc / g * k_z
    F_resistance = eta * gamma_subparticles / gamma_water * np.tan(theta * np.pi / 180)
    F_scale = (d70m / (kappa * L_u) ** (1 / 3)) * (d_70 / d70m) ** 0.4
    F_geometry = 0.91 * (D / L_u) ** (0.28 / ((D / L_u) ** 2.8 - 1) + 0.04)
    DeltaH_c = F_resistance * F_scale * F_geometry * L_u
    R_te = DeltaH_c * m_p

    ### Opbarsten
    # Belasting
    phi_exit = h_exit + r_d * (h - h_exit)
    d_phi = phi_exit - h_exit
    S_op = d_phi

    # Weerstand
    stijghoogte_k = d_exit * (vol - gamma_water) / gamma_water
    R_op = stijghoogte_k * m_u

    ### Heave
    # Belasting
    i = (phi_exit - h_exit) / d_exit
    S_he = i

    # Weerstand
    i_ch = r_ln_s(0.5, 0.1, num)
    R_he = i_ch

    # Faalt als Zte, Zhe en Zop < 0
    result = np.where((R_te < S_te) & (R_op < S_op) & (R_he < S_he), 1, 0)

    result_te = np.where(R_te < S_te, 1, 0)
    result_op = np.where(R_op < S_op, 1, 0)
    result_he = np.where(R_he < S_he, 1, 0)

    return np.mean(result), np.mean(result_te), np.mean(result_op), np.mean(result_he)


# %% Prob met waterstand gumbelverdeling -> sneller maar geen fragility curve
def h_gumbel(data, num, mu, beta):
    d_exit_s = data.d_exit_m * 0.3
    L_u_s = data.L_u_m * 0.1
    D_s = data.D_m * 0.5
    k_z_s = data.k_z_m * 0.5
    d_70_s = data.d_70_m * 0.12
    h_exit_s = 0.1
    vol_s = (data.vol_m - 10) * 0.05

    d_exit = r_ln_s(data.d_exit_m, d_exit_s, num)
    L_u = r_ln_s(data.L_u_m, L_u_s, num)
    D = r_ln_s(data.D_m, D_s, num)
    k_z = r_ln_s(data.k_z_m, k_z_s, num)
    d_70 = r_ln_s(data.d_70_m, d_70_s, num)
    h_exit = r_norm(data.h_exit_m, h_exit_s, num)
    h = gumbel_r.rvs(loc=mu, scale=beta, size=num)
    vol = r_ln_s(data.vol_m - 10, vol_s, num) + 10
    r_d = 1

    # Model factor
    m_p = np.ones(num)  # r_ln_s(1.0, 0.12, num)
    m_u = np.ones(num)  # r_ln_s(1.0, 0.10, num)

    # Deterministen
    eta = 0.25
    gamma_subparticles = 16.5
    gamma_water = 9.81
    r_c = 0.3
    theta = 37
    d70m = 2.08e-4
    g = 9.81
    visc = 1.33e-6

    ### Terugschrijdende Erosie
    # Belasting
    S_te = h - h_exit - r_c * d_exit

    # Weerstand
    kappa = visc / g * k_z
    F_resistance = eta * gamma_subparticles / gamma_water * np.tan(theta * np.pi / 180)
    F_scale = (d70m / (kappa * L_u) ** (1 / 3)) * (d_70 / d70m) ** 0.4
    F_geometry = 0.91 * (D / L_u) ** (0.28 / ((D / L_u) ** 2.8 - 1) + 0.04)
    DeltaH_c = F_resistance * F_scale * F_geometry * L_u
    R_te = DeltaH_c * m_p

    ### Opbarsten
    # Belasting
    phi_exit = h_exit + r_d * (h - h_exit)
    d_phi = phi_exit - h_exit
    S_op = d_phi

    # Weerstand
    stijghoogte_k = d_exit * (vol - gamma_water) / gamma_water
    R_op = stijghoogte_k * m_u

    ### Heave
    # Belasting
    i = (phi_exit - h_exit) / d_exit
    S_he = i

    # Weerstand
    i_ch = r_ln_s(0.5, 0.1, num)
    R_he = i_ch

    # Faalt als Zte, Zhe en Zop < 0
    result = np.where((R_te < S_te) & (R_op < S_op) & (R_he < S_he), 1, 0)  #

    return np.mean(result)


# bepaal mu en beta voor gumbel parameters:
def gumbel_fit(F: np.array, h_F: np.array):
    F_log = -np.log(-np.log(1 - F))
    a, b, _, _, _ = linregress(F_log, h_F)
    return b, a


def gumbel_pdf(x, mu, beta):
    return (1 / beta) * np.exp(-(x - mu) / beta - np.exp(-(x - mu) / beta))
