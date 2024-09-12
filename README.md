# WSBD Prob Piping Check

This repository contains code for the probabilistic piping check for waterboard WSBD

## Status

These scripts are work in progress and not production ready yet!

## Setup

* Create a virtual environment using ```python -m venv .venv```
* Install the requirements using ```python -m pip install -r requirements.txt```
* Setup the data in the data directory
* Run the piping_prob.py script to start the process

## Input data

The required input data is in the form of Excel sheets using the WSBD template for piping parameters. The sheets should be put in the data directory preceding the dijktrajectnaam like;

/data/{DIKE_TRAJECT_NAAM}/{PARAMATER_FILE}.xlsx

The PARAMATER_FILE should be named {DIKE_TRAJECT_NAAM}_LBO-1.xlsx for the piping parameters or {DIKE_TRAJECT_NAAM}_Hydra.xlsx for the waterlevels and probability parameters.

* example of a valid parameter file; /data/34-1/34-1_LBO-1.xlsx
* example of a valid hydra file; /data/34-1/34-1_Hydra.xlsx

## Code

TODO 

```
Bedankt voor je e-mail. Er is inderdaad een handleiding beschikbaar. Deze kan je vinden door in de Probabilistic Toolkit op “help” te klikken en je kan het ook vinden in de map C:\Program Files (x86)\Deltares\Probabilistic Toolkit\bin. Je kan externe modellen runnen door de console van dit model aan te sluiten als Executable (hst 5.2.1.1 van de manual). Je kan ook een python functie met Sellmeijer aansluiten (hst 5.2.1.4).

De python functies om de Toolkit aan te sturen kan je vinden in de map C:\Program Files (x86)\Deltares\Probabilistic Toolkit\bin\Python. Hieronder een kort voobeeld van hoe je een bestaand Toolkit-bestand opent, runt en het resultaat leest. Als je toolkit_model.py opent zie je alle functies die je kan gebruiken.

import sys
from pathlib import Path
pt_python_dir = Path(r'C:\Program Files (x86)\Deltares\Probabilistic Toolkit\bin\Python')
if not str(pt_python_dir) in sys.path:
    sys.path.append(str(pt_python_dir))
import toolkit_model as pt
toolkit = pt.ToolKit()
project = toolkit.load(Path.cwd().joinpath('project.tkx'))
# Make changes to the Toolkit file (for example connect a different dike section or scenario, change the variables)
project.run()
result = project.design_point.reliability_index
print(result)
toolkit.save('test.ptk')

Als je verschillende ondergrond scenario’s wilt berekenen kan je het best verschillende Toolkit files maken. Eerst een template maken met de user interface en daarna met Python steeds de ondergrond aanpassen. Als je een bepaalde parameter wilt variëren kan je ook Table kiezen bij Analysis (Figure 6.1 en hst 8.2.2 van de manual).

Hopelijk kan je Hiermee verder. Ik hoor het graag als je nog meer vragen hebt.
```