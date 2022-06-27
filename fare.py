from requests import get
from math import floor
from bs4 import BeautifulSoup

station_from = "Holmwood"
station_to = "Newcastle"
arr_or_dep = "dep"
date_from = "30-07-22"
date_to = "30-07-22"
time_from = "00:01"
time_to = "15:00"
saver_16_17 = True
saver_16_25 = False

saver = None
if saver_16_17:
    saver = "TSU"
elif saver_16_25:
    saver = "YNG"
from_code = get(f"https://www.brfares.com/ac_loc?term={station_from}").json()[0]["code"]
to_code = get(f"https://www.brfares.com/ac_loc?term={station_to}").json()[0]["code"]
url = f"https://www.brfares.com/querysimple?orig={from_code}&dest={station_to}&rlc={saver}"
print(url)
prices = get(url).json()['fares']
price_bands = []
for price in prices:
    price_bands.append(int(price['adult']['fare'])/100)
print(f"There is {len(price_bands)} price bands, cheapest 3 are {price_bands[-4:-1]}")


print(f"Starting scan between {date_from} {time_from} and {date_to} {time_to}")
date_from, date_to = date_from.replace("-", ""), date_to.replace("-", "")
time_from, time_to = time_from.replace(":", ""), time_to.replace(":", "")

trains = []
cheapest_price = price_bands[0]
cheapest_trains = []
while True:
    url = f"https://ojp.nationalrail.co.uk/service/timesandfares/" \
          f"{station_from}/{station_to}/{date_from}/{time_from}/{arr_or_dep}"
    print(url)
    t_trains = BeautifulSoup(get(url).text, "html.parser").prettify()
    t_trains = [train.split("""}\n""")[0] for train in t_trains.split("""{"jsonJourneyBreakdown":""")[1:]]
    for train in t_trains:
        try:
            dict1, dict2 = train.split('},"')
            dict1 = eval((dict1+"}").replace("null", '"null"'))
            dict2 = eval(dict2.replace('singleJsonFareBreakdowns":[', "").split('],"')[0].replace("false", '"False"'))
            train = dict1 | dict2

            if arr_or_dep == "dep":
                if int(time_to) < int(train['departureTime'].replace(":", "")):
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
                print(f"New cheapest train: £{cheapest_price}")
                cheapest_trains = [train]
            elif price == cheapest_price:
                cheapest_trains.append(train)
            print(f"Dep {train['departureStationName']} {train['departureTime']} -> "
                  f"Arr {train['arrivalStationName']} {train['arrivalTime']} "
                  f"({train['durationHours']}h{train['durationMinutes']}m) {train['changes']} change(s) "
                  f"£{price} on {train['fareProvider']}")
        except SyntaxError:
            print("Invalid train")

    if arr_or_dep == "dep":
        if int(time_to) > int(train['departureTime'].replace(":", "")):
            time_from = int(train['departureTime'].replace(":", ""))+6
        else:
            break

print(f"\nFound {len(trains)} trains")
print(f"Cheapest train(s) £{cheapest_price} (Price band {price_bands.index(cheapest_price)}/{len(price_bands)})")
for train in cheapest_trains:
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



