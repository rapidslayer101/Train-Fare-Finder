from requests import get
from math import floor
from os import path


if not path.exists("station_codes.txt"):
    with open("station_codes.txt", "w") as f:
        f.write("")

if not path.exists("travel_fares.txt"):
    with open("travel_fares.txt", "w") as f:
        f.write("")

with open("apikey.txt", "r") as f:
    apikey = f.read()


def resolve_name_to_code(st_from):
    with open("station_codes.txt", "r") as f:
        for line in f.readlines():
            if line.split("=")[1].strip() == st_from:
                return line.split("=")[0].strip()
    try:
        st_code = get(f"https://{apikey}@gw.brfares.com/"
                      f"legacy_ac_loc?term={st_from}").json()[0]["code"]
        with open("station_codes.txt", "a+") as f:
            f.write(f"{st_code}={st_from}\n")
        return st_code
    except IndexError:
        print(f"Station, {st_from}, not found")
        return False


def price_calc(original_price, saver_16_17=0, saver_16_25=1, adults=1):
    saver_16_17_s = saver_16_17
    saver_16_25_s = saver_16_25
    _price = 0
    for i in range(adults):
        if saver_16_17_s:
            saver_16_17_s -= 1
            _price += original_price*0.5
        elif saver_16_25:
            saver_16_25_s -= 1
            _price += floor((original_price*0.66)*20)/20
        else:
            _price += original_price
    return _price


def get_fares(st_from, st_to):
    # todo redo pull from travel_fares.txt
    with open("travel_fares.txt", "r", encoding="utf-8") as f:
        for line in f.readlines():
            if line.split("=")[0] == f"{st_from}" and line.split("=")[1] == f"{st_to}":
                p_bands = eval(line.split("=")[2])
                t_price_list = eval(line.split("=")[3])
                return p_bands, t_price_list

    p_url = (f"https://{apikey}@gw.brfares.com/"
             f"legacy_querysimple?orig={st_from}&dest={st_to}&rlc=")
    prices_ = get(p_url).json()['fares']
    t_price_list = []
    p_bands = []
    for price_ in prices_:
        try:
            r_price_ = round(price_calc(float(price_['adult']['fare'])/100), 2)
            if r_price_ > 1:
                p_bands.append(r_price_)
        except KeyError:
            pass
        if price_['ticket']['longname'] not in ["ADVANCE", "ADVANCE 1ST"]:
            try:
                t_price = round(price_calc(int(price_['adult']['fare'])/100), 2)
                t_price_list.append(f"{price_['ticket']['longname']} - £{t_price}")
            except KeyError:
                pass
        #if t_price_out['ticket']['longname'] in ["SUPER OFFPEAK R", "OFF-PEAK R", "OFF-PEAK DAY R",
        #                                         "SUP OFFPK DAY R"]:
        #    if price < off_r[0]:
        #        print(off_r)
        #        off_r = [round(price, 2), return_types[t_price_out['ticket']['longname']]]

    p_bands = list(set([p for p in p_bands]))
    p_bands.sort()
    with open("travel_fares.txt", "a+", encoding="utf-8") as f:
        f.write(f"{st_from}={st_to}={p_bands}={t_price_list}\n")
    return p_bands, t_price_list

