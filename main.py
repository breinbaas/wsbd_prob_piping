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
import scipy.stats as stats
from matplotlib.ticker import StrMethodFormatter

from prob_functions import prob_analysis


NUM_SIMULATIONS = int(1e4)

# define which dijktraject to analyse
DIJKTRAJECT = "34a-1"
GEACCEPTEERDE_FAALKANS = 1 / 5000
SLOOT_OPZET_STAPGROOTTE = 0.2

BERMLENGTE_START = 0
BERMLENGTE_EIND = 20
BERMLENGTE_STAP = 2

# path to input data
GEGEVENS_XLSX = rf"./invoergegevens/{DIJKTRAJECT}/{DIJKTRAJECT}_LBO-1_met_check.xlsx"
HYDRA_XLSX = rf"./invoergegevens/{DIJKTRAJECT}/{DIJKTRAJECT}_Hydra.xlsx"

# path to output data
OUTPUT_PATH = rf"./output"


class InputData:
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
        self.voorland_stijghoogte = parameters["voorland stijghoogte"]
        self.voorland_lengte = parameters["voorland kwelweglengte"]
        self.opmerkingen = parameters["opmerkingen"]
        self.sloot_diepte = parameters["sloot_diepte"]
        self.hoogte_maaiveld = parameters["hoogte_maaiveld"]
        self.intredepunt_dempen = parameters["intredepunt_dempen"]
        self.uittredepunt_dempen = parameters["uittredepunt_dempen"]
        self.kwelweglengte_dempen = parameters["kwelweglengte_dempen"]
        self.deklaagdikte_dempen = parameters["deklaagdikte_dempen"]


class Scenario(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    kans: float
    parameters: InputData

    def log(self, scenario_number) -> None:
        logging.info(f"SCENARIO {scenario_number}, kans {self.kans}")
        logging.info("---------------------------------------------")
        logging.info(f"effectieve deklaagdikte     : {self.parameters.d_exit_eff_m}")
        logging.info(f"s_effectieve deklaagdikte   : {self.parameters.d_exit_eff_s}")
        logging.info(f"totale deklaagdikte         : {self.parameters.d_exit_tot_m}")
        logging.info(f"s_totale deklaagdikte       : {self.parameters.d_exit_tot_s}")
        logging.info(f"kwelweglengte               : {self.parameters.L_u_m}")
        logging.info(f"cov_kwelweglengte           : {self.parameters.L_u_cov}")
        logging.info(f"dikte watervoerend pakket   : {self.parameters.D_m}")
        logging.info(f"s_dikte watervoerendpakket  : {self.parameters.D_s}")
        logging.info(f"doorlatendheid aquifer      : {self.parameters.k_z_m}")
        logging.info(f"cov_doorlatendheid          : {self.parameters.k_z_cov}")
        logging.info(f"d70 bovenste laag           : {self.parameters.d_70_m}")
        logging.info(f"cov_d70 bovenste laag       : {self.parameters.d_70_cov}")
        logging.info(f"polderpeil                  : {self.parameters.h_exit_m}")
        logging.info(f"s_polderpeil                : {self.parameters.h_exit_s}")
        logging.info(f"verzadigd gewicht deklaag   : {self.parameters.vol_m}")
        logging.info(f"s_verzadigd gewicht deklaag : {self.parameters.vol_s}")
        logging.info(f"dempingsfactor              : {self.parameters.demping_m}")
        logging.info(f"s_dempingsfactor            : {self.parameters.demping_s}")
        logging.info(f"kritiek heave gradient      : {self.parameters.krit_heave_gr}")
        logging.info(
            f"overleefde_waterstand       : {self.parameters.overleefde_waterstand}"
        )
        logging.info(
            f"voorland maaiveld           : {self.parameters.voorland_maaiveld}"
        )
        logging.info(
            f"voorland stijghoogte        : {self.parameters.voorland_stijghoogte}"
        )
        logging.info(f"voorland lengte             : {self.parameters.voorland_lengte}")
        logging.info(f"opmerkingen                 : {self.parameters.opmerkingen}")
        logging.info(f"sloot diepte                : {self.parameters.sloot_diepte}")
        logging.info(f"hoogte maaiveld             : {self.parameters.hoogte_maaiveld}")
        logging.info(
            f"intredepunt dempen          : {self.parameters.intredepunt_dempen}"
        )
        logging.info(
            f"uittredepunt dempen         : {self.parameters.uittredepunt_dempen}"
        )
        logging.info(
            f"kwelweglengte dempen        : {self.parameters.kwelweglengte_dempen}"
        )
        logging.info(
            f"deklaagdikte dempen         : {self.parameters.deklaagdikte_dempen}"
        )


class Waterstanden(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    hoogtes: np.ndarray
    kansen: np.ndarray


class DijkvakResultaat(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    waterstanden: np.ndarray = None
    probabilities: List[Union[float, np.ndarray]] = (
        []
    )  # e[0] = eventuele info over bv waterstand of bermlengte

    @property
    def has_results(self) -> bool:
        return len(self.probabilities) > 0


class Dijkvak(BaseModel):
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
        logging.info(f"DIJKVAK: {self.name}")
        self.log_waterstanden()
        self.log_scenarios()

    def log_waterstanden(self):
        logging.info("-------------------------")
        logging.info("| waterstand |   kans   |")
        logging.info("-------------------------")
        for i in range(self.waterstanden.hoogtes.shape[0]):
            logging.info(
                f"|{self.waterstanden.hoogtes[i]:11.2f} |{self.waterstanden.kansen[i]:9.5f} |"
            )
        logging.info("-------------------------")

    def log_scenarios(self) -> None:
        for i, scenario in enumerate(self.scenarios):
            logging.info("")
            scenario.log(i + 1)

    def generate_fc(self):
        faalkans_per_scenario = []

        for scenario in self.scenarios:  # Calculate failure probability per scenario
            # Monte Carlo
            r_waterstanden, p, _, _, _ = prob_analysis(
                self.waterstanden, scenario.parameters, NUM_SIMULATIONS
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
        # We gaan er vanuit dat de h_exit_m en hoogte_maaiveld niet per scenario kunnen verschillen
        # TODO, als je h_exit_m vast instelt met op te zetten peil wat te doen met h_exit_s = 0?
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
            for (
                scenario
            ) in self.scenarios:  # Calculate failure probability per scenario
                # Monte Carlo
                r_waterstanden, p, _, _, _ = prob_analysis(
                    self.waterstanden,
                    scenario.parameters,
                    NUM_SIMULATIONS,
                    h_exit_m=slootpeil,  # forceer h_exit_m op slootpeil ipv de standaard parameter waarde
                )
                faalkans_per_scenario.append((np.array(p) * scenario.kans))

            p_totaal = np.sum(faalkans_per_scenario, axis=0)
            faalkans_per_slootpeil.append((slootpeil - h_min, p_totaal))

            # bewaar de resultaten
            self.fc_slootopzetten.waterstanden = r_waterstanden
            self.fc_slootopzetten.probabilities.append((slootpeil - h_min, p_totaal))

    def generate_fc_sloot_dempen(
        self, kwelweglengte: float, deklaagdikte: float, filename: str
    ) -> None:
        faalkans_per_scenario = []

        for scenario in self.scenarios:  # Calculate failure probability per scenario
            # Monte Carlo
            r_waterstanden, p, _, _, _ = prob_analysis(
                self.waterstanden,
                scenario.parameters,
                NUM_SIMULATIONS,
                kwelweglengte=kwelweglengte,
                deklaagdikte=self.deklaagdikte_dempen,
            )
            faalkans_per_scenario.append((np.array(p) * scenario.kans))

        p_totaal = np.sum(faalkans_per_scenario, axis=0)

        # bewaar de resultaten
        self.fc_slootdemping.waterstanden = r_waterstanden
        self.fc_slootdemping.probabilities.append((0.0, p_totaal))

        # TODO plotje maken (normaal en gedempt)

    def generate_fc_bermen(
        self, bermlengte_start: float, bermlengte_eind: float, stapgrootte: float
    ) -> None:
        faalkans_per_berm = []

        for bermbreedte in np.arange(
            bermlengte_start, bermlengte_eind + stapgrootte / 2.0, stapgrootte
        ):
            faalkans_per_scenario = []
            for (
                scenario
            ) in self.scenarios:  # Calculate failure probability per scenario
                # Monte Carlo
                r_waterstanden, p, _, _, _ = prob_analysis(
                    self.waterstanden,
                    scenario.parameters,
                    NUM_SIMULATIONS,
                    kwelweglengte_offset=bermbreedte,  # forceer h_exit_m op slootpeil ipv de standaard parameter waarde
                )
                faalkans_per_scenario.append((np.array(p) * scenario.kans))

            p_totaal = np.sum(faalkans_per_scenario, axis=0)
            faalkans_per_berm.append((bermbreedte, p_totaal))

            # bewaar de resultaten
            self.fc_bermen.waterstanden = r_waterstanden
            self.fc_bermen.probabilities.append((bermbreedte, p_totaal))

    def generate_result_plots(self, output_path: str) -> None:
        # FC obv waterstanden en geen maatregelen
        if self.fc.has_results:
            fig, ax = plt.subplots(figsize=(10, 8))

            if not np.isnan(self.hoogte_voorland):
                ax.plot([self.hoogte_voorland, self.hoogte_voorland], [0, 1], "k--")
                ax.text(self.hoogte_voorland, 0, "voorland hoogte", rotation=90)

            if not np.isnan(self.overleefde_waterstand):
                ax.plot(
                    [self.overleefde_waterstand, self.overleefde_waterstand],
                    [0, 1],
                    "k--",
                )
                ax.text(
                    self.overleefde_waterstand, 0, "overleefde waterstand", rotation=90
                )

            r_waterstanden = self.fc.waterstanden
            _, p_totaal = self.fc.probabilities[0]

            if not np.isnan(self.hoogte_voorland):
                p_totaal_voorland = p_totaal.copy()
                p_totaal_voorland[r_waterstanden <= self.hoogte_voorland] = 0
                ax.plot(r_waterstanden, p_totaal_voorland, "go-", label="Voorland")

            if not np.isnan(self.hoogte_voorland):
                p_totaal_overleefd = p_totaal.copy()
                p_totaal_overleefd[r_waterstanden <= self.overleefde_waterstand] = 0
                ax.plot(
                    r_waterstanden,
                    p_totaal_overleefd,
                    "ro-",
                    label="Overleefde waterstand",
                )

            ax.plot(r_waterstanden, p_totaal, "bo-", label="Sellmeijer")
            ax.set_title(
                f"Probabilistisch piping analyse - {DIJKTRAJECT} dijkvak {str(dijkvak.name).upper()}"
            )
            ax.grid()
            plt.xlabel("Watertstand [m tov NAP]")
            plt.ylabel("Kans op falen [0-1]")
            # ax.set_yscale('log')

            fig.savefig(Path(OUTPUT_PATH) / f"{DIJKTRAJECT}_{self.name}.fc.png")
            plt.close()

        # FC bij maatregel slootpeil opzetten

    def plot_bermen(self, ax) -> None:
        if self.fc_bermen.has_results:
            ax.set_title(f"Berm aanleggen")
            ax.grid()
            ax.set_xlabel("Waterstand [m tov NAP]")
            r_waterstanden = self.fc_bermen.waterstanden
            for bermbreedte, p_totaal in self.fc_bermen.probabilities:
                ax.plot(
                    r_waterstanden,
                    p_totaal,
                    "o-",
                    label=f"bermbreedte = {bermbreedte:.2f}",
                )

            ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.2f}"))
            ax.set_ylabel("Kans op falen [0-1]")
            self.plot_overleefd_en_of_voorland(ax)
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
        if not np.isnan(self.hoogte_voorland):
            ymax = ax.get_ylim()[1]
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
        ax.set_ylabel("Terugkeertijd [jaar]")
        ax.legend()

    def plot_slootpeil_opzetten(self, ax) -> None:
        if self.fc_slootopzetten.has_results:
            ax.set_title(f"Slootpeil opzetten")
            ax.grid()
            ax.set_xlabel("Watertstand [m tov NAP]")

            r_waterstanden = self.fc_slootopzetten.waterstanden
            for offset, p_totaal in self.fc_slootopzetten.probabilities:
                ax.plot(
                    r_waterstanden,
                    p_totaal,
                    "o-",
                    label=f"slootpeil + {offset:.2f} ({self.polderpeil + offset:.2f} tov NAP)",
                )

            self.plot_overleefd_en_of_voorland(ax)
            ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.2f}"))
            ax.set_ylabel("Kans op falen [0-1]")
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

    def plot_normal_fc(self, ax) -> None:
        if self.fc.has_results:
            self.plot_overleefd_en_of_voorland(ax)

            r_waterstanden = self.fc.waterstanden
            _, p_totaal = self.fc.probabilities[0]

            if not np.isnan(self.hoogte_voorland):
                p_totaal_voorland = p_totaal.copy()
                p_totaal_voorland[r_waterstanden <= self.hoogte_voorland] = 0
                ax.plot(r_waterstanden, p_totaal_voorland, "go-", label="Voorland")

            if not np.isnan(self.hoogte_voorland):
                p_totaal_overleefd = p_totaal.copy()
                p_totaal_overleefd[r_waterstanden <= self.overleefde_waterstand] = 0
                ax.plot(
                    r_waterstanden,
                    p_totaal_overleefd,
                    "ro-",
                    label="Overleefde waterstand",
                )

            ax.plot(r_waterstanden, p_totaal, "bo-", label="Sellmeijer")
            ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.2f}"))
            ax.set_title(f"Met en zonder slootdemping")
            ax.grid()
            ax.set_xlabel("Watertstand [m tov NAP]")
            ax.set_ylabel("Kans op falen [0-1]")

        # met slootpeil opzetten
        if self.fc_slootdemping.has_results:
            r_waterstanden = self.fc_slootdemping.waterstanden
            ax.plot(
                r_waterstanden,
                self.fc_slootdemping.probabilities[0][1],
                "o-",
                label=f"sloot gedempt",
            )
        ax.legend()

    def generate_total_plot(self) -> None:
        fig, axs = plt.subplots(
            ncols=2, nrows=2, figsize=(16, 12), layout="constrained"
        )

        self.plot_waterstanden(axs[0, 0])
        self.plot_normal_fc(axs[0, 1])
        self.plot_bermen(axs[1, 0])
        self.plot_slootpeil_opzetten(axs[1, 1])

        fig.suptitle(
            f"Probabilistisch piping analyse - {DIJKTRAJECT} dijkvak {str(dijkvak.name).upper()}"
        )

        fig.savefig(Path(OUTPUT_PATH) / f"{DIJKTRAJECT}_{dijkvak.name}.fc.totaal.png")
        plt.close()

    def calculate_countermeasures(self, waterstanden: List[float]) -> None:
        logging.info("Maatregelen bepalen...")
        req_prob = GEACCEPTEERDE_FAALKANS

        df = pd.DataFrame({"waterstanden": waterstanden})

        # slootpeil opzetten
        if self.fc_slootopzetten.has_results:
            for offset, probs in self.fc_slootopzetten.probabilities:
                x = self.fc_slootopzetten.waterstanden
                y = probs
                p_failure = np.interp(waterstanden, x, y)
                df[f"op_{offset:.1f}m"] = p_failure
        else:
            logging.warning(
                "Bij dit dijkvak is het niet mogelijk om een slootpeil op te zetten."
            )

        # sloot dempen
        if self.fc_slootdemping.has_results:
            x = self.fc_slootdemping.waterstanden
            y = self.fc_slootdemping.probabilities[0][1]
            p_failure = np.interp(waterstanden, x, y)
            df["dempen"] = p_failure
        else:
            logging.warning(
                "Bij dit dijkvak is het niet mogelijk om een sloot te dempen."
            )

        # bermen
        if self.fc_bermen.has_results:
            for breedte, probs in self.fc_bermen.probabilities:
                x = self.fc_bermen.waterstanden
                y = probs
                p_failure = np.interp(waterstanden, x, y)
                df[f"b_{breedte:.1f}m"] = p_failure
        else:
            logging.warning(
                "Bij dit dijkvak is het niet gelukt om bermen te berekenen."
            )

        df.set_index("waterstanden", inplace=True)
        df.to_excel(Path(f"{OUTPUT_PATH}") / f"{DIJKTRAJECT}_resultaat.xlsx")
        df.to_csv(Path(f"{OUTPUT_PATH}") / f"{DIJKTRAJECT}_resultaat.csv")


class Dijktraject(BaseModel):
    dijkvakken: List[Dijkvak] = []

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

        # dijkvakken kunnen meerdere scenario's hebben
        # bepaal alle kolom namen
        col_dict = {kol.split(".")[0]: 0 for kol in df_gegevens.columns}

        for col in df_gegevens.columns:
            naam_dijkvak = col.split(".")[0]

            if not result.has_dijkvak_name(naam_dijkvak):  # create dijkvak
                waterstanden = Waterstanden(
                    hoogtes=df_hydra[naam_dijkvak].to_numpy()[1:].astype(float),
                    kansen=df_hydra.iloc[:, 0].to_numpy()[1:].astype(float),
                )
                result.dijkvakken.append(
                    Dijkvak(
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

for dijkvak in tqdm(dijktraject.dijkvakken[:1]):
    dijkvak.log()

    # standaard FC
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
            dijkvak.generate_fc_sloot_dempen(
                kwelweglengte=dijkvak.kwelweglengte_dempen,
                deklaagdikte=dijkvak.deklaagdikte_dempen,
                filename=Path(OUTPUT_PATH)
                / f"{DIJKTRAJECT}_{dijkvak.name}.fc.sloot_dempen.png",
            )
        except Exception as e:
            logging.error(
                f"Fout bij het bepalen van de FC bij het dempen van de sloot, '{e}'"
            )

    # FC bij maatregel berm aanbrengen
    try:
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
    dijkvak.generate_total_plot()
    dijkvak.calculate_countermeasures([2.5, 2.8, 3.0, 3.3])
