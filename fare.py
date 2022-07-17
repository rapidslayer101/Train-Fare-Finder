from requests import get
from math import floor
from bs4 import BeautifulSoup

providers = {"London Northwestern Railway": "LNER", "Avanti West Coast": "Avanti", "South Western Railway": "SWR"}
return_types = {"SUPER OFFPEAK R": "SOPR", "OFF-PEAK R": "OPR", "OFF-PEAK DAY R": "OPDR", "SUP OFFPK DAY R": "SOPDR"}
station_from = "Holmwood"   # todo multiple departure stations
station_to = "Lincoln"
arr_or_dep = "dep"
dates_out = ["11-08-22", "12-08-22"]
time_from_out = "05:00"
time_to_out = "10:00"
dates_ret = ["13-08-22", "14-08-22"]
time_from_ret = "05:00"
time_to_ret = "10:00"
price_tolerance = 1.75
adults = 1
saver_16_17 = 1
saver_16_25 = False
max_split = 2
try:
    from_code = get(f"https://www.brfares.com/ac_loc?term={station_from}").json()[0]["code"]
except IndexError:
    print(f"Station, {station_from}, not found")
    exit()
try:
    to_code = get(f"https://www.brfares.com/ac_loc?term={station_to}").json()[0]["code"]
except IndexError:
    print(f"Station, {station_to}, not found")
    exit()


def price_calc(original_price):
    saver_16_17_s = saver_16_17
    saver_16_25_s = saver_16_25
    _price = 0
    for i in range(adults):
        if saver_16_17_s:
            saver_16_17_s -= 1
            _price += original_price*0.5
        else:
            if saver_16_25:
                saver_16_25_s -= 1
                _price += floor(original_price*0.66*20)/20
            else:
                _price += original_price
    return _price


def rtt_get(t_fr, t_to, date):
    day, month, year = date.split("-")
    rtt_trains = get(f"https://www.realtimetrains.co.uk/search/detailed/gb-nr:{from_code}/{f'20{year}-{month}-{day}'}/"
                     f"{t_fr}-{t_to}?stp=WVS&show=pax-calls&order=wtt").text.split('<a class="service " href="')[1:-1]
    print(f"https://www.realtimetrains.co.uk/search/detailed/gb-nr:{from_code}/{f'20{year}-{month}-{day}'}/"
          f"{t_fr}-{t_to}?stp=WVS&show=pax-calls&order=wtt")
    print(f"Found {len(rtt_trains)} RTT for {date}")
    return rtt_trains


url = f"https://www.brfares.com/querysimple?orig={from_code}&dest={to_code}&rlc="
prices = get(url).json()['fares']
p_bands = []
train_bands = {}
for price in prices:
    try:
        price = round(price_calc(float(price['adult']['fare'])/100), 2)
        if price > 1:
            train_bands.update({price: []})
            p_bands.append(price)
    except KeyError:
        pass

trains = []
cheapest_price = p_bands[0]
highest_price = p_bands[-1]
p_bands = list(set([p for p in p_bands if p <= round(p_bands[-1]*price_tolerance, 2)]))
p_bands.sort()
fastest_train = 9999
print(f"There is {len(p_bands)} price bands, cheapest 3 are {p_bands[:3]}")
print(f"Starting scan between {dates_out[0]} and {dates_out[-1]} between {time_to_out} and {time_from_out}")

for date in dates_out:
    t_fr, t_to = time_from_out.replace(":", ""), time_to_out.replace(":", "")
    #rtt_trains = rtt_get(from_code, t_fr, t_to, date)
    print(f"Scanning train for {date}")
    date = date.replace("-", "")
    trains_day = []
    train_saved = None
    while True:
        url = f"https://ojp.nationalrail.co.uk/service/timesandfares/" \
              f"{from_code}/{to_code}/{date}/{t_fr}/{arr_or_dep}"
        t_trains = []
        t_trains = BeautifulSoup(get(url).text, "html.parser").prettify()
        t_trains = [train.split("""}\n""")[0] for train in t_trains.split("""{"jsonJourneyBreakdown":""")[1:]]
        last_train_time = int(t_fr)
        for train in t_trains:
            try:
                dict1, dict2 = train.split('},"')
                dict1 = eval((dict1+"}").replace("null", '"null"'))
                dict2 = eval(dict2.replace('singleJsonFareBreakdowns":[', "")
                             .split('],"')[0].replace("false", '"False"').replace("null", '"null"')
                             .replace("true", '"true"'))
                try:
                    train = dict1 | dict2
                except TypeError:
                    dict2 = eval(str(dict2)[1:-1].split("Advance (Standard Class)")[1])
                    train = dict1 | dict2
                train_saved = train
                if arr_or_dep == "dep":
                    if last_train_time > int(train['departureTime'].replace(":", "")):
                        break
                    last_train_time = int(train['departureTime'].replace(":", ""))
                    if int(t_to) < last_train_time:
                        break
                trains_day.append(train)
                price_p_adult = float(train['fullFarePrice'])
                price = round(price_calc(float(train['fullFarePrice'])), 2)
                train['farePrice'] = round(price, 2)
                if price < cheapest_price:
                    cheapest_price = price
                elif price > highest_price:
                    highest_price = price
                try:
                    train_bands[price].append([date, train, url])
                except KeyError:
                    pass

                train_m = int(train['durationHours'])*60+int(train['durationMinutes'])
                if train_m < fastest_train:
                    fastest_train = train_m
                if int(train['durationMinutes']) < 10:
                    train['durationMinutes'] = "0"+str(train['durationMinutes'])
                try:
                    train['fareProvider'] = providers[train['fareProvider']]
                except KeyError:
                    pass
                print(f"Dep {train['departureStationCRS']} {train['departureTime']} -> "
                      f"Arr {train['arrivalStationCRS']} {train['arrivalTime']} "
                      f"({train['durationHours']}h{train['durationMinutes']}m) {train['changes']} 🔄 "
                      f"£{price} on {train['fareProvider']}")
                #for rtt_train in rtt_trains:
                #    if train['departureTime'].replace(":", "") in rtt_train:
                #        rtt_train = rtt_train.split('"><div class=')[0]
                #        print(f"https://www.realtimetrains.co.uk/{rtt_train}")
            except SyntaxError:
                pass
            except IndexError:
                print("Train does not offer Advance (Standard Class)")

        if train_saved is None:
            if int(t_to) < int(t_fr):
                break
        else:
            if int(t_to) > int(train_saved['departureTime'].replace(":", "")):
                new_tf = str(int(train_saved['departureTime'].replace(":", ""))+6)
                if int(new_tf) < int(t_fr):  # todo remove next day trains
                    break
                if len(new_tf) == 3:
                    new_tf = "0"+new_tf
                if int(new_tf[-2:]) >= 60:
                    new_tf1 = str(int(new_tf[:-2])+1)
                    if len(new_tf1) == 1:
                        new_tf1 = "0"+new_tf1
                    new_tf2 = str(int(new_tf[-2:])-60)
                    if len(new_tf2) == 1:
                        new_tf2 = "0"+new_tf2
                    new_tf = new_tf1+new_tf2
                t_fr = new_tf
            else:
                break
        if len(t_trains) == 0:
            print(url)
            train_saved = None
            t_fr = str(int(t_fr)+100)
            if len(str(t_fr)) == 3:
                t_fr = "0"+str(t_fr)
            if int(t_to) < int(t_fr):
                break
    print(f"\nFound {len(trains_day)} trains on {date}")
    trains.append([trains_day])

t_bands_count = 0
for band in train_bands:
    t_bands_count += len(train_bands[band])
print(f"\n-------------------------------------\nFound {t_bands_count} trains")

if not len(trains) == 0:
    if price_tolerance:
        print(f"\nTrains above £{round(cheapest_price*price_tolerance, 2)} have been excluded")
    print(f"Standard prices above £{round(highest_price*3, 2)} have been excluded")
    standard_off_r = None
    off_r = [9999, None]
    for t_price in prices:
        if t_price['ticket']['longname'] not in ["ADVANCE", "ADVANCE 1ST"]:
            try:
                price = round(price_calc(int(t_price['adult']['fare'])/100), 2)
                if highest_price*3 > price > 1.10:
                    print(f"{t_price['ticket']['longname']} - £{price}")
                    if t_price['ticket']['longname'] in ["SUPER OFFPEAK R", "OFF-PEAK R", "OFF-PEAK DAY R",
                                                         "SUP OFFPK DAY R"]:
                        if price < off_r[0]:
                            off_r = [round(price, 2), return_types[t_price['ticket']['longname']]]
            except KeyError:
                pass

    print(f"Fastest train is {fastest_train} minutes")
    print(f"Cheapest advance train(s) £{cheapest_price}")
    band_num = 0
    for p_band in p_bands:
        band_num += 1
        if len(train_bands[p_band]) != 0:
            print(f"\nBand {band_num} - £{p_band} - {len(train_bands[p_band])} Trains")
            for date, train, url in train_bands[p_band]:
                price = float(train['farePrice'])
                print(f"{date} - Dep {train['departureStationCRS']} {train['departureTime']} -> "
                      f"Arr {train['arrivalStationCRS']} {train['arrivalTime']} "
                      f"({train['durationHours']}h{train['durationMinutes']}m) {train['changes']} 🔄 "
                      f"£{price} on {train['fareProvider']} - Ticket: {url}")
            if off_r != [9999, None]:
                if price*2 > off_r[0]:
                    print(f"Return estimated price: £{price*2}, £{round(off_r[0]-price*2, 2)} "
                          f"loss (£{off_r[0]} {off_r[1]})")
                    print("[!] off-peak return is cheaper than advance single tickets")
                else:
                    print(f"Return estimated price: £{price*2}, £{round(off_r[0]-price*2, 2)} "
                          f"saving (£{off_r[0]} {off_r[1]})")
            else:
                print(f"Return estimated price: £{price*2}")


print(f"\n-------------------------------------\nRETURN TRAINS")
url = f"https://www.brfares.com/querysimple?orig={to_code}&dest={from_code}&rlc="
prices = get(url).json()['fares']
p_bands = []
train_bands = {}
for price in prices:
    try:
        price = round(price_calc(float(price['adult']['fare'])/100), 2)
        if price > 1:
            train_bands.update({price: []})
            p_bands.append(price)
    except KeyError:
        pass

trains = []
cheapest_price = p_bands[0]
highest_price = p_bands[-1]
fastest_train = 9999
p_bands = list(set([p for p in p_bands if p <= round(p_bands[-1]*price_tolerance, 2)]))
p_bands.sort()
print(f"Starting scan between {dates_ret[0]} and {dates_ret[-1]} between {time_to_ret} and {time_to_ret}")

for date in dates_ret:
    t_fr, t_to = time_from_ret.replace(":", ""), time_to_ret.replace(":", "")
    # rtt_trains = rtt_get(to_code, t_fr, t_to, date)
    print(f"Scanning train for {date}")
    date = date.replace("-", "")
    trains_day = []
    train_saved = None
    while True:
        url = f"https://ojp.nationalrail.co.uk/service/timesandfares/" \
              f"{to_code}/{from_code}/{date}/{t_fr}/{arr_or_dep}"
        t_trains = []
        t_trains = BeautifulSoup(get(url).text, "html.parser").prettify()
        t_trains = [train.split("""}\n""")[0] for train in t_trains.split("""{"jsonJourneyBreakdown":""")[1:]]
        last_train_time = int(t_fr)
        for train in t_trains:
            try:
                dict1, dict2 = train.split('},"')
                dict1 = eval((dict1+"}").replace("null", '"null"'))
                dict2 = eval(dict2.replace('singleJsonFareBreakdowns":[', "")
                             .split('],"')[0].replace("false", '"False"').replace("null", '"null"')
                             .replace("true", '"true"'))
                try:
                    train = dict1 | dict2
                except TypeError:
                    dict2 = eval(str(dict2)[1:-1].split("Advance (Standard Class)")[1])
                    train = dict1 | dict2
                train_saved = train
                if arr_or_dep == "dep":
                    if last_train_time > int(train['departureTime'].replace(":", "")):
                        break
                    last_train_time = int(train['departureTime'].replace(":", ""))
                    if int(t_to) < last_train_time:
                        break
                trains_day.append(train)
                price_p_adult = float(train['fullFarePrice'])
                price = round(price_calc(float(train['fullFarePrice'])), 2)
                train['farePrice'] = round(price, 2)
                if price < cheapest_price:
                    cheapest_price = price
                elif price > highest_price:
                    highest_price = price
                try:
                    train_bands[price].append([date, train, url])
                except KeyError:
                    pass

                train_m = int(train['durationHours'])*60+int(train['durationMinutes'])
                if train_m < fastest_train:
                    fastest_train = train_m
                if int(train['durationMinutes']) < 10:
                    train['durationMinutes'] = "0"+str(train['durationMinutes'])
                try:
                    train['fareProvider'] = providers[train['fareProvider']]
                except KeyError:
                    pass
                print(f"Dep {train['departureStationCRS']} {train['departureTime']} -> "
                      f"Arr {train['arrivalStationCRS']} {train['arrivalTime']} "
                      f"({train['durationHours']}h{train['durationMinutes']}m) {train['changes']} 🔄 "
                      f"£{price} on {train['fareProvider']}")
                #for rtt_train in rtt_trains:
                #    if train['departureTime'].replace(":", "") in rtt_train:
                #        rtt_train = rtt_train.split('"><div class=')[0]
                #        print(f"https://www.realtimetrains.co.uk/{rtt_train}")
            except SyntaxError:
                pass
            except IndexError:
                print("Train does not offer Advance (Standard Class)")

        if train_saved is None:
            if int(t_to) < int(t_fr):
                break
        else:
            if int(t_to) > int(train_saved['departureTime'].replace(":", "")):
                new_tf = str(int(train_saved['departureTime'].replace(":", ""))+6)
                if int(new_tf) < int(t_fr):  # todo remove next day trains
                    break
                if len(new_tf) == 3:
                    new_tf = "0"+new_tf
                if int(new_tf[-2:]) >= 60:
                    new_tf1 = str(int(new_tf[:-2])+1)
                    if len(new_tf1) == 1:
                        new_tf1 = "0"+new_tf1
                    new_tf2 = str(int(new_tf[-2:])-60)
                    if len(new_tf2) == 1:
                        new_tf2 = "0"+new_tf2
                    new_tf = new_tf1+new_tf2
                t_fr = new_tf
            else:
                break
        if len(t_trains) == 0:
            print(url)
            train_saved = None
            t_fr = str(int(t_fr)+100)
            if len(str(t_fr)) == 3:
                t_fr = "0"+str(t_fr)
            if int(t_to) < int(t_fr):
                break
    print(f"\nFound {len(trains_day)} trains on {date}")
    trains.append([trains_day])

t_bands_count = 0
for band in train_bands:
    t_bands_count += len(train_bands[band])
print(f"\n-------------------------------------\nFound {t_bands_count} trains")

if not len(trains) == 0:
    if price_tolerance:
        print(f"\nTrains above £{round(cheapest_price*price_tolerance, 2)} have been excluded")
    print(f"Standard prices above £{round(highest_price*3, 2)} have been excluded")
    standard_off_r = None
    off_r = [9999, None]
    for t_price in prices:
        if t_price['ticket']['longname'] not in ["ADVANCE", "ADVANCE 1ST"]:
            try:
                price = round(price_calc(int(t_price['adult']['fare'])/100), 2)
                if highest_price*3 > price > 1.10:
                    print(f"{t_price['ticket']['longname']} - £{price}")
                    if t_price['ticket']['longname'] in ["SUPER OFFPEAK R", "OFF-PEAK R", "OFF-PEAK DAY R",
                                                         "SUP OFFPK DAY R"]:
                        if price < off_r[0]:
                            off_r = [round(price, 2), return_types[t_price['ticket']['longname']]]
            except KeyError:
                pass

    print(f"Fastest train is {fastest_train} minutes")
    print(f"Cheapest advance train(s) £{cheapest_price}")
    band_num = 0
    for p_band in p_bands:
        band_num += 1
        if len(train_bands[p_band]) != 0:
            print(f"\nBand {band_num} - £{p_band} - {len(train_bands[p_band])} Trains")
            for date, train, url in train_bands[p_band]:
                price = float(train['farePrice'])
                print(f"{date} - Dep {train['departureStationCRS']} {train['departureTime']} -> "
                      f"Arr {train['arrivalStationCRS']} {train['arrivalTime']} "
                      f"({train['durationHours']}h{train['durationMinutes']}m) {train['changes']} 🔄 "
                      f"£{price} on {train['fareProvider']} - Ticket: {url}")
            if off_r != [9999, None]:
                if price*2 > off_r[0]:
                    print(f"Return estimated price: £{price*2}, £{round(off_r[0]-price*2, 2)} "
                          f"loss (£{off_r[0]} {off_r[1]})")
                    print("[!] off-peak return is cheaper than advance single tickets")
                else:
                    print(f"Return estimated price: £{price*2}, £{round(off_r[0]-price*2, 2)} "
                          f"saving (£{off_r[0]} {off_r[1]})")
            else:
                print(f"Return estimated price: £{price*2}")

# todo auto cheapest train detection if 1 each way, then combine automatically
print("\nPlease check https://www.raileasy.co.uk/ for any cheaper tickets")
print("Enter 2 links to combine into a single ticket")
print(f"Combined ticket: {input('Ticket 1: ')+input('Ticket 2: ').split(from_code)[1]}")
