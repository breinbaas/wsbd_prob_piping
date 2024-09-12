import matplotlib.pyplot as plt
import numpy as np


def plot_gumbel_fit(F, h_F, mu, beta, filename):
    F_log = -np.log(-np.log(1 - F))
    x = F_log
    y = x * beta + mu
    plt.plot(h_F, F_log, "ok", label="Hydra-NL")
    plt.plot(y, x, label="Lineaire regressie")
    plt.grid()
    plt.xlabel("Waterstand h [m + NAP]")
    plt.ylabel("-ln(-ln(1-F)X>x)))")
    plt.title("Gumbel verdeling")
    plt.legend()
    plt.savefig(filename)


def plot_fc(
    waterstanden, p, p_te, p_op, p_he, gumbel, faalkans, f_piping, betab, filename
):
    fig, ax = plt.subplots(3, 1, figsize=(12, 12))

    ax[0].plot(waterstanden, p)

    # Zet aan voor individuele mechanismes.

    # ax[0].plot(waterstanden, p_te)
    # ax[0].plot(waterstanden, p_op)
    # ax[0].plot(waterstanden, p_he)

    ax[1].plot(waterstanden, gumbel)
    ax[2].plot(waterstanden, faalkans)

    ax[0].set_title("Fragility Curve", fontsize=16)
    ax[0].set_xlabel("Waterstand [m + NAP]")
    ax[0].set_ylabel("P(F|H)")
    ax[0].grid(True)

    ax[1].set_title("Waterstand Gumbel verdeling", fontsize=16)
    ax[1].set_ylabel("P(H)")
    ax[1].set_xlabel("Waterstand [m + NAP]")
    ax[1].grid(True)

    ax[2].set_title("Faalkans (P) per waterstand", fontsize=16)
    ax[2].set_ylabel("P(F|H) $\cdot$ P(H)")
    ax[2].set_xlabel("Waterstand [m + NAP]")
    ax[2].grid(True)

    text1 = f"P = {f_piping:.2e}"
    text2 = r"$\beta$ = {}".format(round(betab, 3))
    ax[2].text(
        0.955,
        0.985,
        text2,
        ha="right",
        va="top",
        transform=ax[2].transAxes,
        fontsize=12,
    )
    ax[2].text(
        0.98, 0.91, text1, ha="right", va="top", transform=ax[2].transAxes, fontsize=12
    )

    plt.tight_layout()
    plt.savefig(filename)
