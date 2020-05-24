import pandas as pd
import pickle
import time
from math import atan2, cos, pow, sin, sqrt

import const


def load_airports():
    airports = pd.read_csv(const.AIRPORTS_FILENAME)
    airports.latitude_deg = airports.latitude_deg.astype(float)
    airports.longitude_deg = airports.longitude_deg.astype(float)
    return airports

def load_jobs():
    jobs = pd.read_excel(const.JOBS_FILENAME)
    jobs.columns = ['fromIcao', 'toIcao', 'dist', 'cargo', 'quantity', 'fee', 'expires']
    # jobs.dist = jobs.dist.astype(int)
    # jobs.quantity = jobs.quantity.astype(int)
    return jobs

def load_aircraft():
    aircraft = pd.read_csv(const.AIRCRAFT_FILENAME)
    aircraft.columns = ['Location', 'MakeModel', 'CargoCapacity', 'Range']
    aircraft.CargoCapacity = aircraft.CargoCapacity.astype(int)
    aircraft.Range = aircraft.Range.astype(int)
    return aircraft


def get_earnings(row, rent_type):
    res = row['Pay']
    pt_amount = row['PtAssignment']
    if pt_amount > 6:
        res -= res * pt_amount / 100
    return round(res - row[rent_type], 2) if row[rent_type] else 0


def get_ratio(x, earnings_column):
    return round(x[earnings_column] / ((x['Distance'] + x['CraftDistance']) / x['aircraft']['CruiseSpeed']), 2)


def get_distance(lat1, lon1, lat2, lon2):
    r = 6371000
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = pow(sin(dlat / 2), 2) + cos(lat1) * cos(lat2) * pow(sin(dlon / 2), 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return round((r * c) / 1850)


def load_pickled_assignments():
    with open('assignments', 'rb') as f:
        assignments = pickle.load(f)
    assignments.Pay = assignments.Pay.astype(int)
    assignments.Amount = assignments.Amount.astype(int)
    assignments.PtAssignment = assignments.PtAssignment.map(lambda x: True if x == 'true' else False)
    assignments.UnitType = assignments.UnitType.astype(str)
    return assignments


def retry(func, *args, **kwargs):
    c = 1
    count = kwargs.pop("count", 10)
    error_type = kwargs.pop("error_type", Exception)
    interval = kwargs.pop("interval", 60)
    while True:
        try:
            return func(*args, **kwargs)
        except error_type:
            if c >= count:
                raise
            c += 1
            time.sleep(interval)


def get_total_fuel(aircraft):
    return aircraft['Ext1'] + aircraft['LTip'] + aircraft['LAux'] + aircraft['LMain'] + aircraft['Center1'] + aircraft[
        'Center2'] + aircraft['Center3'] + aircraft['RMain'] + aircraft['RAux'] + aircraft['RTip'] + aircraft['RExt2']
