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