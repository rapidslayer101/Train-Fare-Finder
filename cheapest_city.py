from trainlib import resolve_name_to_code, get_fares

while True:
    station_from = input("Enter start station: ")
    station_to = input("Enter destination: ")

    try:
        from_code = resolve_name_to_code(station_from)
        to_code = resolve_name_to_code(station_to)
        p_bands_out, t_price_out = get_fares(station_from, station_to)
        print(f"Fares from {station_from} to {station_to} start at £{p_bands_out[0]}"
              f" -> £{p_bands_out[1]} -> £{p_bands_out[2]} -> £{p_bands_out[3]}- > £{p_bands_out[4]} "
              f"----- Return from £{p_bands_out[0]*2}")
    except IndexError:
        print("Invalid Station Name")