from requests import get
from math import floor
from bs4 import BeautifulSoup

station_from = "Newcastle"  #Gatwick
station_to = "Dorking"  # Lincoln
arr_or_dep = "dep"
date_from = "30-07-22"
date_to = "30-07-22"
time_from = "00:01"
time_to = "23:59"
#time_tolerance = 0.5
#adults = 2  # todo logic for multiple people
saver_16_17 = False
saver_16_25 = 1

saver = None
if saver_16_17:
    saver = "TSU"
elif saver_16_25:
    saver = "YNG"
from_code = get(f"https://www.brfares.com/ac_loc?term={station_from}").json()[0]["code"]
to_code = get(f"https://www.brfares.com/ac_loc?term={station_to}").json()[0]["code"]
url = f"https://www.brfares.com/querysimple?orig={from_code}&dest={to_code}&rlc={saver}"
print(url)
prices = get(url).json()['fares']
p_bands = []
for price in prices:
    p_bands.append(int(price['adult']['fare'])/100)
print(f"There is {len(p_bands)} price bands, cheapest 3 are {p_bands[-4:-1]}")


print(f"Starting scan between {date_from} {time_from} and {date_to} {time_to}")
date_from, date_to = date_from.replace("-", ""), date_to.replace("-", "")
time_from, time_to = time_from.replace(":", ""), time_to.replace(":", "")

trains = []
cheapest_price = p_bands[0]
fastest_train = 9999
cheapest_trains = []
train_saved = None

# todo logic for multiple days
# todo logic for time tolerance
while True:
    url = f"https://ojp.nationalrail.co.uk/service/timesandfares/" \
          f"{from_code}/{to_code}/{date_from}/{time_from}/{arr_or_dep}"
    t_trains = []
    t_trains = BeautifulSoup(get(url).text, "html.parser").prettify()
    t_trains = [train.split("""}\n""")[0] for train in t_trains.split("""{"jsonJourneyBreakdown":""")[1:]]
    last_train_time = int(time_from)
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
                print("success")

            train_saved = train
            if arr_or_dep == "dep":
                if last_train_time > int(train['departureTime'].replace(":", "")):
                    break
                last_train_time = int(train['departureTime'].replace(":", ""))
                if int(time_to) < last_train_time:
                    break
            trains.append(train)
            price = float(train['fullFarePrice'])

            if saver_16_17:
                price *= 0.5
            elif saver_16_25:
                price *= 0.66
                price = floor(price*20)/20

            if price < cheapest_price:
                cheapest_price = price
                cheapest_trains = [[train, url]]
            elif price == cheapest_price:
                cheapest_trains.append([train, url])

            train_m = int(train['durationHours'])*60+int(train['durationMinutes'])
            if train_m < fastest_train:
                fastest_train = train_m
            print(f"Dep {train['departureStationName']} {train['departureTime']} -> "
                  f"Arr {train['arrivalStationName']} {train['arrivalTime']} "
                  f"({train['durationHours']}h{train['durationMinutes']}m) {train['changes']} change(s) "
                  f"£{price} on {train['fareProvider']}")
        except SyntaxError:
            pass
        except IndexError:
            print("Train does not offer Advance (Standard Class)")

    if arr_or_dep == "dep":
        if train_saved is None:
            if int(time_to) < int(time_from):
                break
        else:
            if int(time_to) > int(train_saved['departureTime'].replace(":", "")):
                new_tf = str(int(train_saved['departureTime'].replace(":", ""))+6)
                if int(new_tf) < int(time_from):  # todo remove next day trains
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
                time_from = new_tf
            else:
                break

    # todo make arr work
    #if arr_or_dep == "arr":
        #if train_saved is None:
        #    if int(time_to) < int(time_from):
        #        break
        #else:
    #    if int(time_to) < int(time_from):
    #        break
    #    if int(time_to) > int(train_saved['arrivalTime'].replace(":", "")):
    #        time_from = str(int(train_saved['arrivalTime'].replace(":", ""))+6)
    #        if len(time_from) == 3:
    #            time_from = "0"+time_from
    #    else:
    #        break
    if len(t_trains) == 0:
        print(url)
        train_saved = None
        time_from = str(int(time_from)+100)
        if len(str(time_from)) == 3:
            time_from = "0"+str(time_from)
        if int(time_to) < int(time_from):
            break

print(f"\nFound {len(trains)} trains")
if not len(trains) == 0:
    print(f"Fastest train is {fastest_train} minutes")
    #for train, url in cheapest_trains:
    #    print((int(train['durationHours'])*60+int(train['durationMinutes'])))
    try:
        print(f"Cheapest train(s) £{cheapest_price} (Price band {p_bands.index(cheapest_price)}/{len(p_bands)})")
    except ValueError:
        print(f"Cheapest train(s) £{cheapest_price}")
    # todo show trains that are very close to the cheapest price
    for train, url in cheapest_trains:
        price = float(train['fullFarePrice'])
        if saver_16_17:
            price *= 0.5
        elif saver_16_25:
            price *= 0.66
            price = floor(price * 20) / 20
        print(f"Dep {train['departureStationName']} {train['departureTime']} -> "
              f"Arr {train['arrivalStationName']} {train['arrivalTime']} "
              f"({train['durationHours']}h{train['durationMinutes']}m) {train['changes']} change(s) "
              f"£{price} on {train['fareProvider']}")
        print(f"Purchase a ticket from {url}")
    print(f"Return estimated price: £{price*2}")



