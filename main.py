from pathlib import Path
import sys, os
import pandas as pd
import logging
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Union
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import glob
from matplotlib.ticker import StrMethodFormatter, ScalarFormatter, FuncFormatter
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.drawing.image import Image
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import PatternFill

from prob_functions import prob_analysis

# aantal simulaties, advies 1e4 voor debugging / testing en 1e7 voor uitvoering
NUM_SIMULATIONS = int(1e4)

# naam dijktraject
DIJKTRAJECT = "34a-1"

# geaccepteerde faalkans
GEACCEPTEERDE_FAALKANS = 1 / 5000

# stapgrootte voor het opzetten van het slootpeil
# hoe kleiner de stappen hoe meer berekeningen en dit kan
# de plot onleesbaar maken
SLOOT_OPZET_STAPGROOTTE = 0.2

# welke waterstand gebruiken we om de maatregelen te bepalen
WATERSTANDEN_VOOR_MAATREGELEN = [2.5, 2.8, 3.0, 3.3]

# hoe laten we de bermbreedte verlopen (van, tot, stapgrootte)
BERMLENGTE_START = 0
BERMLENGTE_EIND = 20
BERMLENGTE_STAP = 4

# pad naar input data
# PAD EN EXCEL BESTANDEN MOETEN BESTAAN
GEGEVENS_XLSX = rf"./invoergegevens/{DIJKTRAJECT}/{DIJKTRAJECT}_LBO-1_met_check.xlsx"
HYDRA_XLSX = rf"./invoergegevens/{DIJKTRAJECT}/{DIJKTRAJECT}_Hydra.xlsx"

# pad naar uitvoer data, PAD MOET BESTAAN
OUTPUT_PATH = rf"./output"

# as limiet voor de conditionele faalkans in de plots
Y_P_MIN = 1
Y_P_MAX = 1e5

SHOW_MAATREGELEN_WATERSTANDEN = False  # toont blauwe verticale lijnen bij de gehanteerde waterstanden (voor debugging)

# Optie om een minimale kans vast te stellen
# Als dit is ingesteld worden kansen die kleiner zijn dan de opgegeven waarde op deze waarde gezet
# Let op dat dit rare grafieken kan geven, om dat te voorkomen kan MIN_PROBABILITY = 0 gebruikt worden
# In dat geval zijn de grafieken mooier maar kun je (ongevaarlijke) division by zero meldingen krijgen
MIN_PROBABILITY = 0


def custom_log_formatter(x) -> str:
    """format de y as als 1 10 100 1.000 10.000 etc

    Args:
        x (int): kolom index


    Returns:
        str: getal met duizende scheiding
    """
    if x == 0:
        return "0"
    return f"{x:,.0f}".replace(",", ".")


def column_index_to_excel_column(index) -> str:
    """Converts a column index (1-based) to its Excel-style letter representation.

    Args:
        index: The column index to convert.

    Returns:
        The Excel-style column letter representation.
    """

    if index <= 0:
        raise ValueError("Index must be positive")

    result = ""
    while index > 0:
        remainder = (index - 1) % 26
        result = chr(ord("A") + remainder) + result
        index = (index - 1) // 26

    return result


class InputData:
    """een class om de invoerdata op te slaan"""

    def __init__(
        self,
        parameters,
    ) -> None:
        self.d_exit_eff_m = parameters["effectieve deklaagdikte"]
        self.d_exit_eff_s = parameters["s_effectieve deklaagdikte"]
        self.d_exit_tot_m = parameters["totale deklaagdikte"]
        self.d_exit_tot_s = parameters["s_totale deklaagdikte"]
        self.L_u_m = parameters["kwelweglengte"]
        self.L_u_cov = parameters["cov_kwelweglengte"]
        self.D_m = parameters["dikte watervoerend pakket"]
        self.D_s = parameters["s_dikte watervoerendpakket"]
        self.k_z_m = parameters["doorlatendheid aquifer"]
        self.k_z_cov = parameters["cov_doorlatendheid"]
        self.d_70_m = parameters["d70 bovenste laag"]
        self.d_70_cov = parameters["cov_d70 bovenste laag"]
        self.h_exit_m = parameters["polderpeil"]
        self.h_exit_s = parameters["s_polderpeil"]
        self.vol_m = parameters["verzadigd gewicht deklaag"]
        self.vol_s = parameters["s_verzadigd gewicht deklaag"]
        self.demping_m = parameters["dempingsfactor"]
        self.demping_s = parameters["s_dempingsfactor"]
        self.krit_heave_gr = parameters["kritiek heave gradient"]
        self.scenario_kans = (
            parameters["scenario_kans"]
            if not np.isnan(parameters["scenario_kans"])
            else 1
        )
        self.overleefde_waterstand = parameters["overleefde_waterstand"]
        self.voorland_maaiveld = parameters["voorland maaiveld"]
        # self.voorland_stijghoogte = parameters["voorland stijghoogte"]
        self.voorland_lengte = parameters["voorland lengte"]
        self.opmerkingen = parameters["opmerkingen"]
        self.sloot_diepte = parameters["sloot_diepte"]
        self.hoogte_maaiveld = parameters["hoogte_maaiveld"]
        self.intredepunt_dempen = parameters["intredepunt_dempen"]
        self.uittredepunt_dempen = parameters["uittredepunt_dempen"]
        self.kwelweglengte_dempen = parameters["kwelweglengte_dempen"]
        self.deklaagdikte_dempen = parameters["deklaagdikte_dempen"]


class Scenario(BaseModel):
    """Een scenario bevat de informatie voor een scenario binnen een dijkvak"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kans: float
    parameters: InputData

    def log(self, scenario_number, sheet) -> None:
        """Log de invoer data in de Excel sheet

        Args:
            scenario_number (int): Nummer voor het scenario
            sheet (Excel Sheet): De excelsheet om naar te schrijven
        """
        sheet.append(["SCENARIO", scenario_number])
        sheet.append(["kans", self.kans])
        sheet.append(["effectieve deklaagdikte", self.parameters.d_exit_eff_m])
        sheet.append(["s_effectieve deklaagdikte", self.parameters.d_exit_eff_s])
        sheet.append(["totale deklaagdikte", self.parameters.d_exit_tot_m])
        sheet.append(["s_totale deklaagdikte", self.parameters.d_exit_tot_s])
        sheet.append(["kwelweglengte", self.parameters.L_u_m])
        sheet.append(["cov_kwelweglengte", self.parameters.L_u_cov])
        sheet.append(["dikte watervoerend pakket", self.parameters.D_m])
        sheet.append(["s_dikte watervoerendpakket", self.parameters.D_s])
        sheet.append(["doorlatendheid aquifer", self.parameters.k_z_m])
        sheet.append(["cov_doorlatendheid", self.parameters.k_z_cov])
        sheet.append(["d70 bovenste laag", self.parameters.d_70_m])
        sheet.append(["cov_d70 bovenste laag", self.parameters.d_70_cov])
        sheet.append(["polderpeil", self.parameters.h_exit_m])
        sheet.append(["s_polderpeil", self.parameters.h_exit_s])
        sheet.append(["verzadigd gewicht deklaag", self.parameters.vol_m])
        sheet.append(["s_verzadigd gewicht deklaag", self.parameters.vol_s])
        sheet.append(["dempingsfactor", self.parameters.demping_m])
        sheet.append(["s_dempingsfactor", self.parameters.demping_s])
        sheet.append(["kritiek heave gradient", self.parameters.krit_heave_gr])
        sheet.append(["overleefde_waterstand", self.parameters.overleefde_waterstand])
        sheet.append(["voorland maaiveld", self.parameters.voorland_maaiveld])
        sheet.append(["voorland lengte", self.parameters.voorland_lengte])
        sheet.append(["sloot diepte", self.parameters.sloot_diepte])
        sheet.append(["hoogte maaiveld", self.parameters.hoogte_maaiveld])
        sheet.append(["intredepunt dempen", self.parameters.intredepunt_dempen])
        sheet.append(["uittredepunt dempen", self.parameters.uittredepunt_dempen])
        sheet.append(["kwelweglengte dempen", self.parameters.kwelweglengte_dempen])
        sheet.append(["deklaagdikte dempen", self.parameters.deklaagdikte_dempen])
        sheet.append(["aantal simulaties", NUM_SIMULATIONS])
        sheet.append(
            ["geaccepteerde faalkans", f"1:{round(1/GEACCEPTEERDE_FAALKANS)} jaar"]
        )

        sheet.append([""])
        sheet.append(["OPMERKINGEN", self.parameters.opmerkingen])


class Waterstanden(BaseModel):
    """Informatie over de waterstanden, hoogtes en kansen"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    hoogtes: np.ndarray
    kansen: np.ndarray


class DijkvakResultaat(BaseModel):
    """Opslagplek voor de resultaten van een dijkvak bestaande uit de waterstanden en de berekende kansen"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    waterstanden: np.ndarray = None
    probabilities: List[Union[float, np.ndarray]] = (
        []
    )  # e[0] = eventuele info over bv waterstand of bermlengte

    @property
    def has_results(self) -> bool:
        return len(self.probabilities) > 0


class Dijkvak(BaseModel):
    """Een dijkvak bevat alle informatie om de maatregelen voor dit vak te berekenen en te bepalen"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    scenarios: List[Scenario] = []
    waterstanden: Waterstanden
    overleefde_waterstand: float = np.nan
    hoogte_voorland: float = np.nan

    # Resultaten
    fc: DijkvakResultaat = DijkvakResultaat()
    fc_slootdemping: DijkvakResultaat = DijkvakResultaat()
    fc_slootopzetten: DijkvakResultaat = DijkvakResultaat()
    fc_bermen: DijkvakResultaat = DijkvakResultaat()

    # Excel sheet voor uitvoer (komt van Dijktraject eigenschap)
    workbook: Workbook
    sheet: Worksheet

    @property
    def polderpeil(self) -> Optional[float]:
        # We gaan er vanuit dat over de scenarios in een dijkvak het polderpeil gelijk is!
        return self.scenarios[0].parameters.h_exit_m

    @property
    def hoogte_maaiveld_polder(self) -> Optional[float]:
        # We gaan er vanuit dat over de scenarios in een dijkvak de hoogte van het polder maaiveld gelijk is!
        return self.scenarios[0].parameters.hoogte_maaiveld

    @property
    def deklaagdikte_dempen(self) -> Optional[float]:
        # We gaan er vanuit dat over de scenarios in een dijkvak de deklaagdikte dempen gelijk is!
        return self.scenarios[0].parameters.deklaagdikte_dempen

    @property
    def kwelweglengte_dempen(self) -> Optional[float]:
        # We gaan er vanuit dat over de scenarios in een dijkvak de kwelweglengte dempen gelijk is!
        return self.scenarios[0].parameters.kwelweglengte_dempen

    def log(self) -> None:
        self.log_waterstanden()
        self.sheet.append([""])
        self.log_scenarios(self.sheet)
        self.sheet.append([""])

    def log_waterstanden(self):
        self.sheet.append(["waterstand", "kans"])
        for i in range(self.waterstanden.hoogtes.shape[0]):
            self.sheet.append(
                [self.waterstanden.hoogtes[i], self.waterstanden.kansen[i]]
            )

    def log_scenarios(self, sheet: Worksheet) -> None:
        for i, scenario in enumerate(self.scenarios):
            logging.info("")
            scenario.log(i + 1, sheet)

    def generate_fc(self):
        """Genereer de faalkans voor de situatie zonder maatregelen"""
        faalkans_per_scenario = []

        for i, scenario in enumerate(
            self.scenarios
        ):  # Calculate failure probability per scenario
            logging.info(
                f"Berekening instellingen voor de faalkans zonder maatregelen voor scenario {i+1}"
            )

            # Monte Carlo
            r_waterstanden, p, _, _, _ = prob_analysis(
                waterstanden=self.waterstanden,
                num_simulations=NUM_SIMULATIONS,
                d_exit_eff_m=scenario.parameters.d_exit_eff_m,
                d_exit_eff_s=scenario.parameters.d_exit_eff_s,
                d_exit_tot_m=scenario.parameters.d_exit_tot_m,
                d_exit_tot_s=scenario.parameters.d_exit_tot_s,
                L_u_m=scenario.parameters.L_u_m,
                L_u_cov=scenario.parameters.L_u_cov,
                D_m=scenario.parameters.D_m,
                D_s=scenario.parameters.D_s,
                k_z_m=scenario.parameters.k_z_m,
                k_z_cov=scenario.parameters.k_z_cov,
                d_70_m=scenario.parameters.d_70_m,
                d_70_cov=scenario.parameters.d_70_cov,
                h_exit_m=scenario.parameters.h_exit_m,
                h_exit_s=scenario.parameters.h_exit_s,
                vol_m=scenario.parameters.vol_m,
                vol_s=scenario.parameters.vol_s,
                demping_m=scenario.parameters.demping_m,
                demping_s=scenario.parameters.demping_s,
                krit_heave_gr=scenario.parameters.krit_heave_gr,
                voorland_maaiveld=scenario.parameters.voorland_maaiveld,
                voorland_lengte=scenario.parameters.voorland_lengte,
            )
            faalkans_per_scenario.append((np.array(p) * scenario.kans))

        p_totaal = np.sum(faalkans_per_scenario, axis=0)

        # Sorteer alles
        sorted_indices = np.argsort(r_waterstanden)
        r_waterstanden = r_waterstanden[sorted_indices]
        p_totaal = p_totaal[sorted_indices]

        # bewaar de resultaten
        self.fc.waterstanden = r_waterstanden
        self.fc.probabilities.append((np.nan, p_totaal))

    def generate_fc_slootpeil(self):
        """Genereer de faalkans voor de situatie waarbij we het slootpeil opzetten"""
        # We gaan er vanuit dat de h_exit_m en hoogte_maaiveld niet per scenario kunnen verschillen
        faalkans_per_slootpeil = []

        h_min = self.polderpeil
        h_max = self.hoogte_maaiveld_polder

        if np.isnan(h_max):
            logging.warning(
                "Kan het slootpeil voor dit scenario niet opzetten omdat de hoogte van het maaiveld niet gedefinieerd is"
            )
            return

        for slootpeil in np.arange(
            h_min, h_max + SLOOT_OPZET_STAPGROOTTE / 2.0, SLOOT_OPZET_STAPGROOTTE
        ):
            faalkans_per_scenario = []
            for i, scenario in enumerate(
                self.scenarios
            ):  # Calculate failure probability per scenario
                # Monte Carlo
                logging.info(
                    f"Berekening instellingen voor de faalkans met slootpeil {slootpeil} voor scenario {i+1}"
                )
                r_waterstanden, p, _, _, _ = prob_analysis(
                    waterstanden=self.waterstanden,
                    num_simulations=NUM_SIMULATIONS,
                    d_exit_eff_m=scenario.parameters.d_exit_eff_m,
                    d_exit_eff_s=scenario.parameters.d_exit_eff_s,
                    d_exit_tot_m=scenario.parameters.d_exit_tot_m,
                    d_exit_tot_s=scenario.parameters.d_exit_tot_s,
                    L_u_m=scenario.parameters.L_u_m,
                    L_u_cov=scenario.parameters.L_u_cov,
                    D_m=scenario.parameters.D_m,
                    D_s=scenario.parameters.D_s,
                    k_z_m=scenario.parameters.k_z_m,
                    k_z_cov=scenario.parameters.k_z_cov,
                    d_70_m=scenario.parameters.d_70_m,
                    d_70_cov=scenario.parameters.d_70_cov,
                    h_exit_m=slootpeil,  # gebruik het slootpeil
                    h_exit_s=1.0,  # de kans is 100%
                    vol_m=scenario.parameters.vol_m,
                    vol_s=scenario.parameters.vol_s,
                    demping_m=scenario.parameters.demping_m,
                    demping_s=scenario.parameters.demping_s,
                    krit_heave_gr=scenario.parameters.krit_heave_gr,
                    voorland_maaiveld=scenario.parameters.voorland_maaiveld,
                    voorland_lengte=scenario.parameters.voorland_lengte,
                )
                faalkans_per_scenario.append((np.array(p) * scenario.kans))

            p_totaal = np.sum(faalkans_per_scenario, axis=0)
            faalkans_per_slootpeil.append((slootpeil - h_min, p_totaal))

            # bewaar de resultaten
            self.fc_slootopzetten.waterstanden = r_waterstanden
            self.fc_slootopzetten.probabilities.append((slootpeil - h_min, p_totaal))

    def generate_fc_sloot_dempen(self) -> None:
        """Genereer de faalkans voor de situatie waarbij de sloot gedempt wordt"""
        faalkans_per_scenario = []

        for i, scenario in enumerate(
            self.scenarios
        ):  # Calculate failure probability per scenario
            # Monte Carlo
            logging.info(
                f"Berekening instellingen voor de faalkans met gedempte sloot voor scenario {i+1}"
            )
            r_waterstanden, p, _, _, _ = prob_analysis(
                waterstanden=self.waterstanden,
                num_simulations=NUM_SIMULATIONS,
                d_exit_eff_m=scenario.parameters.deklaagdikte_dempen,  # gebruik de aangepaste deklaagdikte
                d_exit_eff_s=scenario.parameters.d_exit_eff_s,
                d_exit_tot_m=scenario.parameters.deklaagdikte_dempen,  # gebruik de aangepaste deklaagdikte
                d_exit_tot_s=scenario.parameters.d_exit_tot_s,
                L_u_m=scenario.parameters.kwelweglengte_dempen,  # gebruikt de kwelweglengte bij dempen
                L_u_cov=scenario.parameters.L_u_cov,  # cov blijft hetzelfde
                D_m=scenario.parameters.D_m,
                D_s=scenario.parameters.D_s,
                k_z_m=scenario.parameters.k_z_m,
                k_z_cov=scenario.parameters.k_z_cov,
                d_70_m=scenario.parameters.d_70_m,
                d_70_cov=scenario.parameters.d_70_cov,
                h_exit_m=scenario.parameters.h_exit_m,  # ondanks dempen sloot houden we het polderpeil aan
                h_exit_s=scenario.parameters.h_exit_s,
                vol_m=scenario.parameters.vol_m,
                vol_s=scenario.parameters.vol_s,
                demping_m=scenario.parameters.demping_m,
                demping_s=scenario.parameters.demping_s,
                krit_heave_gr=scenario.parameters.krit_heave_gr,
                voorland_maaiveld=scenario.parameters.voorland_maaiveld,
                voorland_lengte=scenario.parameters.voorland_lengte,
            )
            faalkans_per_scenario.append((np.array(p) * scenario.kans))

        p_totaal = np.sum(faalkans_per_scenario, axis=0)

        # bewaar de resultaten
        self.fc_slootdemping.waterstanden = r_waterstanden
        self.fc_slootdemping.probabilities.append((0.0, p_totaal))

    def generate_fc_bermen(
        self, bermlengte_start: float, bermlengte_eind: float, stapgrootte: float
    ) -> None:
        """Genereer de faalkans voor de situatie waarbij we bermen aanleggen"""
        faalkans_per_berm = []

        for bermbreedte in np.arange(
            bermlengte_start, bermlengte_eind + stapgrootte / 2.0, stapgrootte
        ):
            faalkans_per_scenario = []
            for i, scenario in enumerate(
                self.scenarios
            ):  # Calculate failure probability per scenario
                # Monte Carlo
                logging.info(
                    f"Berekening instellingen voor de faalkans met bermbreedte {bermbreedte} voor scenario {i+1}"
                )
                r_waterstanden, p, _, _, _ = prob_analysis(
                    waterstanden=self.waterstanden,
                    num_simulations=NUM_SIMULATIONS,
                    d_exit_eff_m=scenario.parameters.d_exit_eff_m,
                    d_exit_eff_s=scenario.parameters.d_exit_eff_s,
                    d_exit_tot_m=scenario.parameters.d_exit_tot_m,
                    d_exit_tot_s=scenario.parameters.d_exit_tot_s,
                    L_u_m=scenario.parameters.L_u_m
                    + bermbreedte,  # voeg bermbreedte toe aan kwelweg lengte
                    L_u_cov=scenario.parameters.L_u_cov,  # cov houden we gelijk
                    D_m=scenario.parameters.D_m,
                    D_s=scenario.parameters.D_s,
                    k_z_m=scenario.parameters.k_z_m,
                    k_z_cov=scenario.parameters.k_z_cov,
                    d_70_m=scenario.parameters.d_70_m,
                    d_70_cov=scenario.parameters.d_70_cov,
                    h_exit_m=scenario.parameters.h_exit_m,
                    h_exit_s=scenario.parameters.h_exit_s,
                    vol_m=scenario.parameters.vol_m,
                    vol_s=scenario.parameters.vol_s,
                    demping_m=scenario.parameters.demping_m,
                    demping_s=scenario.parameters.demping_s,
                    krit_heave_gr=scenario.parameters.krit_heave_gr,
                    voorland_maaiveld=scenario.parameters.voorland_maaiveld,
                    voorland_lengte=scenario.parameters.voorland_lengte,
                )
                faalkans_per_scenario.append((np.array(p) * scenario.kans))

            p_totaal = np.sum(faalkans_per_scenario, axis=0)
            faalkans_per_berm.append((bermbreedte, p_totaal))

            # bewaar de resultaten
            self.fc_bermen.waterstanden = r_waterstanden
            self.fc_bermen.probabilities.append((bermbreedte, p_totaal))

    def plot_bermen(self, ax, used_waterlevels) -> None:
        if self.fc_bermen.has_results:
            ax.set_title(f"Berm aanleggen")
            ax.grid()
            ax.set_xlabel("Waterstand [m tov NAP]")
            r_waterstanden = self.fc_bermen.waterstanden
            ax.plot(
                [np.min(r_waterstanden), np.max(r_waterstanden)],
                [1 / GEACCEPTEERDE_FAALKANS, 1 / GEACCEPTEERDE_FAALKANS],
                "k--",
                label="minimaal geaccepteerde faalkans",
            )
            if SHOW_MAATREGELEN_WATERSTANDEN:
                for ws in used_waterlevels:
                    ax.plot([ws, ws], [Y_P_MIN, Y_P_MAX], "b--")
            for bermbreedte, p_totaal in self.fc_bermen.probabilities:
                if MIN_PROBABILITY != 0.0:
                    p_totaal[p_totaal <= MIN_PROBABILITY] = MIN_PROBABILITY
                ax.plot(
                    r_waterstanden,
                    1 / p_totaal,
                    "o-",
                    label=f"bermbreedte = {bermbreedte:.2f}",
                )

            ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.2f}"))
            ax.set_ylabel("Kans op falen [0-1]")
            ax.set_ylabel("Conditionele faalkans [jaar]")
            ax.set_yscale("log")
            ax.set_ylim(Y_P_MIN, Y_P_MAX)
            ax.yaxis.set_major_formatter(FuncFormatter(custom_log_formatter))
            ax.legend()
        else:
            ax.annotate(
                f"geen bermen berekend",
                (0.5, 0.5),
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=18,
                color="darkgrey",
            )

    def plot_overleefd_en_of_voorland(self, ax):
        ymax = ax.get_ylim()[1]
        if not np.isnan(self.hoogte_voorland):
            ax.plot(
                [self.hoogte_voorland, self.hoogte_voorland],
                [0, ymax],
                "k--",
            )
            ax.text(
                self.hoogte_voorland, ymax, "voorland hoogte", rotation=90, va="top"
            )

        if not np.isnan(self.overleefde_waterstand):
            ax.plot(
                [self.overleefde_waterstand, self.overleefde_waterstand],
                [0, ymax],
                "k--",
            )
            ax.text(
                self.overleefde_waterstand,
                ymax,
                "overleefde waterstand",
                rotation=90,
                va="top",
            )

    def plot_waterstanden(self, ax) -> None:
        ax.set_title(f"Waterstanden en kansen")
        ax.grid()
        ax.plot(
            self.waterstanden.hoogtes,
            1 / self.waterstanden.kansen,
            linewidth=3,
            label="HydraNL",
        )
        ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.2f}"))
        ax.set_yscale("log")
        # ax.plot(x, pdf, "k--", label="Gumbel")
        self.plot_overleefd_en_of_voorland(ax)
        ax.set_xlabel("Watertstand [m tov NAP]")
        ax.set_ylabel("Conditionele faalkans [jaar]")
        ax.set_ylim(Y_P_MIN, Y_P_MAX)
        ax.yaxis.set_major_formatter(FuncFormatter(custom_log_formatter))
        ax.legend()

    def plot_slootpeil_opzetten(self, ax, used_waterlevels) -> None:
        if self.fc_slootopzetten.has_results:
            ax.set_title(f"Slootpeil opzetten")
            ax.grid()
            ax.set_xlabel("Watertstand [m tov NAP]")
            r_waterstanden = self.fc_slootopzetten.waterstanden
            ax.plot(
                [np.min(r_waterstanden), np.max(r_waterstanden)],
                [1 / GEACCEPTEERDE_FAALKANS, 1 / GEACCEPTEERDE_FAALKANS],
                "k--",
                label="minimaal geaccepteerde faalkans",
            )
            if SHOW_MAATREGELEN_WATERSTANDEN:
                for ws in used_waterlevels:
                    ax.plot([ws, ws], [Y_P_MIN, Y_P_MAX], "b--")

            for offset, p_totaal in self.fc_slootopzetten.probabilities:
                # 1/p kan 1/0 betekenen, dit is lelijk maar geeft toch goede plotjes omdat de nans niet worden geplot
                if MIN_PROBABILITY != 0.0:
                    p_totaal[p_totaal <= MIN_PROBABILITY] = MIN_PROBABILITY
                ax.plot(
                    r_waterstanden,
                    1 / p_totaal,
                    "o-",
                    label=f"slootpeil + {offset:.2f} ({self.polderpeil + offset:.2f} tov NAP)",
                )

            # self.plot_overleefd_en_of_voorland(ax)
            ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.2f}"))
            # ax.set_ylabel("Kans op falen [0-1]")
            ax.set_ylabel("Conditionele faalkans [jaar]")
            ax.set_ylim(Y_P_MIN, Y_P_MAX)
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(FuncFormatter(custom_log_formatter))
            ax.legend()
        else:
            ax.annotate(
                f"geen slootpeilen berekend",
                (0.5, 0.5),
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=18,
                color="darkgrey",
            )

    def plot_normal_fc(self, ax, used_waterlevels) -> None:
        if self.fc.has_results:
            r_waterstanden = self.fc.waterstanden
            ax.plot(
                [np.min(r_waterstanden), np.max(r_waterstanden)],
                [1 / GEACCEPTEERDE_FAALKANS, 1 / GEACCEPTEERDE_FAALKANS],
                "k--",
                label="minimaal geaccepteerde faalkans",
            )
            if SHOW_MAATREGELEN_WATERSTANDEN:
                for ws in used_waterlevels:
                    ax.plot([ws, ws], [Y_P_MIN, Y_P_MAX], "b--")
            _, p_totaal = self.fc.probabilities[0]
            if MIN_PROBABILITY != 0.0:
                p_totaal[p_totaal <= MIN_PROBABILITY] = MIN_PROBABILITY

            ax.plot(r_waterstanden, 1 / p_totaal, "o-", label="Niet gedempt")
            ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.2f}"))
            ax.set_title(f"Met en zonder slootdemping")
            ax.grid()
            ax.set_xlabel("Watertstand [m tov NAP]")
            ax.set_ylabel("Conditionele faalkans [jaar]")
            ax.set_ylim(Y_P_MIN, Y_P_MAX)
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(FuncFormatter(custom_log_formatter))

        # met slootpeil opzetten
        if self.fc_slootdemping.has_results:
            r_waterstanden = self.fc_slootdemping.waterstanden
            p_totaal = self.fc_slootdemping.probabilities[0][1]
            if MIN_PROBABILITY != 0.0:
                p_totaal[p_totaal <= MIN_PROBABILITY] = MIN_PROBABILITY
            ax.plot(
                r_waterstanden,
                1 / p_totaal,
                "o-",
                label=f"sloot gedempt",
            )

        ax.legend()

    def generate_total_plot(self, used_waterlevels) -> None:
        fig, axs = plt.subplots(ncols=2, nrows=2, figsize=(12, 8), layout="constrained")

        self.plot_waterstanden(axs[0, 0])
        self.plot_slootpeil_opzetten(axs[0, 1], used_waterlevels)
        self.plot_normal_fc(axs[1, 0], used_waterlevels)
        self.plot_bermen(axs[1, 1], used_waterlevels)

        fig.suptitle(
            f"Probabilistisch piping analyse - {DIJKTRAJECT} dijkvak {str(self.name).upper()}"
        )

        fig_path = Path(OUTPUT_PATH) / f"{DIJKTRAJECT}_{self.name}.fc.totaal.png"
        fig.savefig(fig_path)

        img = Image(fig_path)
        img.anchor = "D2"
        self.sheet.add_image(img)

        plt.close()

    def check_excel_row(self, row, waterstanden):
        """Verwacht een excel rij met omschrijving, kans bij waterstand 1, kans bij waterstand 2, .., kans bij waterstand n
        en wijzigt de uitvoer in het geval dat de waterstand lager is dan de overleefde waterstand of het voorland.

        Args:
            row (_type_): omschrijving, p1, p2, ..., p;n
            waterstanden (_type_): ws1, ws2, ..., ws;n
        """
        for i in range(1, len(waterstanden)):
            if waterstanden[i] <= self.overleefde_waterstand:
                row[i] = "overleefd"
            if waterstanden[i] <= self.hoogte_voorland:
                row[i] = "voorland"
        return row

    def calculate_countermeasures(self, waterstanden: List[float]) -> None:
        logging.info("Maatregelen bepalen...")
        req_prob = GEACCEPTEERDE_FAALKANS

        self.sheet.append([f"MAATREGELEN"])
        self.sheet.append(["Slootpeil opzetten (kans uitgedrukt als terugkeertijd)"])

        conclusies_slootpeil_opzetten = {ws: "geen" for ws in waterstanden}
        conclusies_sloot_dempen = {ws: "geen" for ws in waterstanden}
        conclusies_bermen = {ws: "geen" for ws in waterstanden}

        excel_waterstanden_row = [f"+{ws:.2f}" for ws in waterstanden]
        excel_waterstanden_row.insert(0, "")
        # slootpeil opzetten
        if self.fc_slootopzetten.has_results:
            self.sheet.append(excel_waterstanden_row)
            for offset, probs in self.fc_slootopzetten.probabilities:
                x = self.fc_slootopzetten.waterstanden
                y = probs
                p_failure = np.interp(waterstanden, x, y)
                b_failure = p_failure < GEACCEPTEERDE_FAALKANS
                for ws, b in zip(waterstanden, b_failure):
                    if b:
                        if conclusies_slootpeil_opzetten[ws] == "geen":
                            conclusies_slootpeil_opzetten[ws] = offset

                p_failure = 1 / p_failure
                excel_row = np.round(p_failure).tolist()
                excel_row.insert(0, f"+{offset:.2f}m")
                self.sheet.append(self.check_excel_row(excel_row, waterstanden))
        else:
            self.sheet.append(
                ["Bij dit dijkvak is het niet mogelijk om een slootpeil op te zetten."]
            )

        # sloot dempen
        self.sheet.append([""])
        self.sheet.append(["Sloot dempen (kans uitgedrukt als terugkeertijd)"])
        if self.fc_slootdemping.has_results:
            self.sheet.append(excel_waterstanden_row)
            x = self.fc_slootdemping.waterstanden
            y = self.fc_slootdemping.probabilities[0][1]
            p_failure = np.interp(waterstanden, x, y)
            b_failure = p_failure < GEACCEPTEERDE_FAALKANS
            for ws, b in zip(waterstanden, b_failure):
                if b:
                    if conclusies_sloot_dempen[ws] == "geen":
                        conclusies_sloot_dempen[ws] = "dempen"

            p_failure = 1 / p_failure
            excel_row = np.round(p_failure).tolist()
            excel_row.insert(0, "gedempt")
            self.sheet.append(self.check_excel_row(excel_row, waterstanden))
        else:
            self.sheet.append(
                ["Bij dit dijkvak is het niet mogelijk om een sloot te dempen."]
            )

        # bermen
        self.sheet.append([""])
        self.sheet.append(["Bermen aanbrengen (kans uitgedrukt als terugkeertijd)"])
        if self.fc_bermen.has_results:
            self.sheet.append(excel_waterstanden_row)
            for breedte, probs in self.fc_bermen.probabilities:
                x = self.fc_bermen.waterstanden
                y = probs
                p_failure = np.interp(waterstanden, x, y)
                b_failure = p_failure < GEACCEPTEERDE_FAALKANS
                for ws, b in zip(waterstanden, b_failure):
                    if b:
                        if conclusies_bermen[ws] == "geen":
                            conclusies_bermen[ws] = breedte
                p_failure = 1 / p_failure
                excel_row = np.round(p_failure).tolist()
                excel_row.insert(0, f"{breedte:.2f}m")
                self.sheet.append(self.check_excel_row(excel_row, waterstanden))
        else:
            self.sheet.append(
                ["Bij dit dijkvak is het niet gelukt om bermen te berekenen."]
            )

        self.sheet.append([""])
        self.sheet.append(["CONCLUSIE"])
        for ws in waterstanden:
            if ws < self.overleefde_waterstand:
                self.sheet.append(
                    [
                        f"Maatregel bij waterstand NAP+{ws:.2f}: Dit traject heeft een waterstand van NAP+{self.overleefde_waterstand}m overleefd, geen maatregel nodig"
                    ]
                )
            elif conclusies_slootpeil_opzetten[ws] == 0.0:
                self.sheet.append(
                    [f"Maatregel bij waterstand NAP+{ws:.2f}: Geen maatregel nodig"]
                )
            elif conclusies_slootpeil_opzetten[ws] != "geen":
                self.sheet.append(
                    [
                        f"Maatregel bij waterstand NAP+{ws:.2f}: Slootpeil opzetten met {conclusies_slootpeil_opzetten[ws]:.1f}m"
                    ]
                )
            elif conclusies_sloot_dempen[ws] == "dempen":
                self.sheet.append(
                    [f"Maatregel bij waterstand NAP+{ws:.2f}: Sloot dempen"]
                )
            elif conclusies_bermen[ws] == 0.0:
                self.sheet.append(
                    [
                        f"Maatregel bij waterstand NAP+{ws:.2f}: Herziening nodig, slootpeil opzetten of dempen helpt niet maar een berm van 0m voldoet wel, dit is een uitzondering die verder bekeken moet worden"
                    ]
                )
            elif conclusies_bermen[ws] != "geen":
                self.sheet.append(
                    [
                        f"Maatregel bij waterstand NAP+{ws:.2f}: Berm aanbrengen van {round(conclusies_bermen[ws])} meter"
                    ]
                )
            else:
                self.sheet.append(
                    [
                        f"Maatregel bij waterstand NAP+{ws:.2f}: Geen enkele maatregel voldoet"
                    ]
                )


class Dijktraject(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    dijkvakken: List[Dijkvak] = []
    workbook: Workbook = Workbook()

    @classmethod
    def from_excel(
        cls, excel_gegevens: str, excel_hydra: str
    ) -> Optional["Dijktraject"]:
        result = Dijktraject()

        # Piping gegevens inladen
        df_gegevens = pd.read_excel(GEGEVENS_XLSX)
        df_gegevens.columns = df_gegevens.columns.str.strip().str.lower()
        df_gegevens = df_gegevens.assign(
            dijkvak=df_gegevens["dijkvak"].str.strip().str.lower()
        ).set_index("dijkvak")

        # Hydraulische belasting inladen
        df_hydra = pd.read_excel(HYDRA_XLSX)
        df_hydra.columns = df_hydra.columns.str.strip().str.lower()

        for col in df_gegevens.columns:
            naam_dijkvak = col.split(".")[0]

            if not result.has_dijkvak_name(naam_dijkvak):  # create dijkvak
                waterstanden = Waterstanden(
                    hoogtes=df_hydra[naam_dijkvak].to_numpy()[1:].astype(float),
                    kansen=df_hydra.iloc[:, 0].to_numpy()[1:].astype(float),
                )
                result.workbook.create_sheet(title=naam_dijkvak, index=None)
                result.dijkvakken.append(
                    Dijkvak(
                        workbook=result.workbook,
                        sheet=result.workbook[naam_dijkvak],
                        name=naam_dijkvak,
                        waterstanden=waterstanden,
                        hoogte_voorland=df_gegevens[col]["voorland maaiveld"],
                        overleefde_waterstand=df_gegevens[col]["overleefde_waterstand"],
                    )
                )

            dv = result.get_dijkvak_by_name(naam_dijkvak)
            kans = (
                df_gegevens[col]["scenario_kans"]
                if not np.isnan(df_gegevens[col]["scenario_kans"])
                else 1
            )
            parameters = InputData(df_gegevens[col])
            dv.scenarios.append(Scenario(kans=kans, parameters=parameters))

        return result

    def get_dijkvak_by_name(self, name: str) -> Optional[Dijkvak]:
        for dv in self.dijkvakken:
            if dv.name == name:
                return dv

        return None

    def has_dijkvak_name(self, name: str) -> bool:
        return name in [dv.name for dv in self.dijkvakken]

    def generate_maatregelen(self):
        for dijkvak in tqdm(dijktraject.dijkvakken):
            dijkvak.log()

            # standaard FC
            logging.info("-" * 80)
            logging.info("FC zonder maatregelen")
            logging.info("-" * 80)
            try:
                dijkvak.generate_fc()
            except Exception as e:
                logging.error(f"Fout bij het bepalen van de FC, '{e}'")

            # FC bij maatregel slootpeil opzetten
            if np.isnan(dijkvak.hoogte_maaiveld_polder):
                logging.warning(
                    "Kan het slootpeil voor dit scenario niet opzetten omdat de hoogte van het maaiveld niet gedefinieerd is"
                )
            else:
                try:
                    logging.info("-" * 80)
                    logging.info("FC met slootpeilen")
                    logging.info("-" * 80)
                    dijkvak.generate_fc_slootpeil()
                except Exception as e:
                    logging.error(
                        f"Fout bij het bepalen van de FC bij het opzetten van de slootpeilen, '{e}'"
                    )

            # FC bij maatregel sloot dempen
            if np.isnan(dijkvak.kwelweglengte_dempen):
                logging.warning(
                    "Voor dit dijkvak is er geen mogelijkheid om de sloot te dempen."
                )
            else:
                try:
                    logging.info("-" * 80)
                    logging.info("FC met sloot dempen")
                    logging.info("-" * 80)
                    dijkvak.generate_fc_sloot_dempen()
                except Exception as e:
                    logging.error(
                        f"Fout bij het bepalen van de FC bij het dempen van de sloot, '{e}'"
                    )

            # FC bij maatregel berm aanbrengen
            try:
                logging.info("-" * 80)
                logging.info("FC met bermen")
                logging.info("-" * 80)
                dijkvak.generate_fc_bermen(
                    bermlengte_start=BERMLENGTE_START,
                    bermlengte_eind=BERMLENGTE_EIND,
                    stapgrootte=BERMLENGTE_STAP,
                )
            except Exception as e:
                logging.error(
                    f"Fout bij het bepalen van de FC bij het aanleggen van bermen, '{e}'"
                )

            # dijkvak.generate_result_plots(OUTPUT_PATH)
            dijkvak.generate_total_plot(WATERSTANDEN_VOOR_MAATREGELEN)
            dijkvak.calculate_countermeasures(WATERSTANDEN_VOOR_MAATREGELEN)

            self.workbook.save(Path(f"{OUTPUT_PATH}") / f"{DIJKTRAJECT}_resultaat.xlsx")


# clear the output path
files = glob.glob(f"{OUTPUT_PATH}/*")
for f in files:
    os.remove(f)

# create a logging file
logging.basicConfig(
    filename=str(Path(OUTPUT_PATH) / f"{DIJKTRAJECT}.log"),
    filemode="w",
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,  # INFO in production
)


if not Path(GEGEVENS_XLSX).exists():
    print(f"Geen gegevens bestand ('{GEGEVENS_XLSX}') gevonden.")
    sys.exit(1)

if not Path(HYDRA_XLSX).exists():
    print("Geen hydra bestand ('{GEGEVENS_XLSX}') gevonden.")
    sys.exit(1)

dijktraject = Dijktraject.from_excel(GEGEVENS_XLSX, HYDRA_XLSX)
dijktraject.generate_maatregelen()
