from requests import get
from math import floor
from bs4 import BeautifulSoup

providers = {"London Northwestern Railway": "LNER", "Avanti West Coast": "Avanti", "South Western Railway": "SWR"}
return_types = {"SUPER OFFPEAK R": "SOPR", "OFF-PEAK R": "OPR", "OFF-PEAK DAY R": "OPDR", "SUP OFFPK DAY R": "SOPDR"}
station_from = "Rugby"   # todo multiple departure stations
station_to = "Blaenau Ffestiniog"
arr_or_dep = "dep"
dates_out = ["11-08-22", "12-08-22", "13-08-22"]
time_from_out = "04:30"
time_to_out = "15:00"
dates_ret = ["13-08-22", "14-08-22", "15-08-22"]
time_from_ret = "04:30"
time_to_ret = "16:30"
#price_tolerance = 1.75
price_tolerance = 999
adults = 2
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


def rtt_get(fr_code, t_fr, t_to, date):
    day, month, year = date.split("-")
    rtt_trains = get(f"https://www.realtimetrains.co.uk/search/detailed/gb-nr:{fr_code}/{f'20{year}-{month}-{day}'}/"
                     f"{t_fr}-{t_to}?stp=WVS&show=pax-calls&order=wtt").text.split('<a class="service " href="')[1:-1]
    print(f"https://www.realtimetrains.co.uk/search/detailed/gb-nr:{fr_code}/{f'20{year}-{month}-{day}'}/"
          f"{t_fr}-{t_to}?stp=WVS&show=pax-calls&order=wtt")
    print(f"Found {len(rtt_trains)} RTT for {date}")
    return rtt_trains


url = f"https://www.brfares.com/querysimple?orig={from_code}&dest={to_code}&rlc="
prices = get(url).json()['fares']
p_bands_out = []
train_bands_out = {}
for price in prices:
    try:
        price = round(price_calc(float(price['adult']['fare'])/100), 2)
        if price > 1:
            train_bands_out.update({price: []})
            p_bands_out.append(price)
    except KeyError:
        pass

trains = []
cheapest_price = p_bands_out[0]
highest_price = p_bands_out[-1]
p_bands_out = list(set([p for p in p_bands_out if p <= round(p_bands_out[-1]*price_tolerance, 2)]))
p_bands_out.sort()
fastest_train = 9999
print(f"There is {len(p_bands_out)} price bands, cheapest 3 are {p_bands_out[:3]}")
print(f"Starting scan between {dates_out[0]} and {dates_out[-1]} between {time_to_out} and {time_from_out}")

for date in dates_out:
    t_fr, t_to = time_from_out.replace(":", ""), time_to_out.replace(":", "")
    rtt_trains_out = rtt_get(from_code, t_fr, t_to, date)
    print(f"Scanning trains for {date}")
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
                    url = f"https://ojp.nationalrail.co.uk/service/timesandfares/" \
                          f"{from_code}/{to_code}/{date}/{train['departureTime'].replace(':', '')}/{arr_or_dep}"
                    train_bands_out[price].append([date, train, url])
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
                      f"£{price} on {train['fareProvider']} - Ticket: {url}")
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
                if int(new_tf) < int(t_fr):
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
for band in train_bands_out:
    t_bands_count += len(train_bands_out[band])
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
    cheapest_out_train = None
    for p_band in p_bands_out:
        band_num += 1
        if len(train_bands_out[p_band]) != 0:
            print(f"\nBand {band_num} - £{p_band} - {len(train_bands_out[p_band])} Trains")
            for date, train, url in train_bands_out[p_band]:
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
                    if price == cheapest_price:
                        cheapest_out_train = [date, train, url]
            else:
                print(f"Return estimated price: £{price*2}")


print(f"\n-------------------------------------\nRETURN TRAINS")
url = f"https://www.brfares.com/querysimple?orig={to_code}&dest={from_code}&rlc="
prices = get(url).json()['fares']
p_bands_ret = []
train_bands_ret = {}
for price in prices:
    try:
        price = round(price_calc(float(price['adult']['fare'])/100), 2)
        if price > 1:
            train_bands_ret.update({price: []})
            p_bands_ret.append(price)
    except KeyError:
        pass

trains = []
cheapest_price = p_bands_ret[0]
highest_price = p_bands_ret[-1]
fastest_train = 9999
p_bands_ret = list(set([p for p in p_bands_ret if p <= round(p_bands_ret[-1]*price_tolerance, 2)]))
p_bands_ret.sort()
print(f"Starting scan between {dates_ret[0]} and {dates_ret[-1]} between {time_from_ret} and {time_to_ret}")

for date in dates_ret:
    t_fr, t_to = time_from_ret.replace(":", ""), time_to_ret.replace(":", "")
    rtt_trains_in = rtt_get(to_code, t_fr, t_to, date)
    print(f"Scanning trains for {date}")
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
                    url = f"https://ojp.nationalrail.co.uk/service/timesandfares/" \
                          f"{from_code}/{to_code}/{date}/{train['departureTime'].replace(':', '')}/{arr_or_dep}"
                    train_bands_ret[price].append([date, train, url])
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
                      f"£{price} on {train['fareProvider']} - Ticket: {url}")
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
                if int(new_tf) < int(t_fr):
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
for band in train_bands_ret:
    t_bands_count += len(train_bands_ret[band])
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
    cheapest_ret_train = None
    for p_band in p_bands_ret:
        band_num += 1
        if len(train_bands_ret[p_band]) != 0:
            print(f"\nBand {band_num} - £{p_band} - {len(train_bands_ret[p_band])} Trains")
            for date, train, url in train_bands_ret[p_band]:
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
                    if price == cheapest_price:
                        cheapest_ret_train = [date, train, url]
            else:
                print(f"Return estimated price: £{price*2}")

print("\nPlease check https://www.raileasy.co.uk/ for any cheaper tickets\n")
if cheapest_out_train and cheapest_ret_train:
    combined_price = round(float(cheapest_out_train[1]['farePrice'])+float(cheapest_ret_train[1]['farePrice']), 2)
    print(f"Found cheapest combined ticket for £{combined_price}, £{round(off_r[0]-price*2, 2)} "
          f"saving (£{off_r[0]} {off_r[1]})")
    for date, train, url in [cheapest_out_train, cheapest_ret_train]:
        price = float(train['farePrice'])
        print(f"{date} - Dep {train['departureStationCRS']} {train['departureTime']} -> "
              f"Arr {train['arrivalStationCRS']} {train['arrivalTime']} "
              f"({train['durationHours']}h{train['durationMinutes']}m) {train['changes']} 🔄 "
              f"£{price} on {train['fareProvider']} - Ticket: {url}")
    print(f"Automatically Combined ticket: {cheapest_out_train[2]+cheapest_ret_train[2].split(to_code)[1]}\n")
    accept_combined = input("Accept combined ticket? (y/n): ")
else:
    accept_combined = "n"

while True:
    train_out = []
    train_ret = []
    if not accept_combined.lower() == "y":
        print("Enter 2 links to combine into a single ticket")
        ticket_out = input('Ticket 1: ')
        ticket_ret = input('Ticket 2: ')
    else:
        ticket_out = cheapest_out_train[2]
        ticket_ret = cheapest_ret_train[2]
    try:
        for p_band in p_bands_out:
            if len(train_bands_out[p_band]) != 0:
                for date, train, url in train_bands_out[p_band]:
                    if url == ticket_out:
                        train_out.append([date, train])
        for p_band in p_bands_ret:
            if len(train_bands_ret[p_band]) != 0:
                for date, train, url in train_bands_ret[p_band]:
                    if url == ticket_ret:
                        train_ret.append([date, train])
        if train_out:
            if train_ret:
                break
        else:
            if accept_combined.lower() == "y":
                input("Error linking tickets")
    except Exception:
        print("Invalid ticket link")

if not accept_combined.lower() == "y":
    print(f"Combined ticket: {ticket_out+ticket_ret.split(to_code)[1]}")

print("\nBuilding train route")
print(train_out, train_ret)

