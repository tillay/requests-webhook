import requests, subprocess, json, time, os

num = 100
with open("codes.json") as f:
    country_dict = json.load(f)

def get_location_list(ip):
    try: ipinfo = requests.get(f"https://ipinfo.io/{ip}/json").json()
    except requests.exceptions.RequestException: exit("Unable to use ipinfo.io for lookups!")
    except KeyError: exit("Ipinfo out of requests!")

    country_code = ipinfo.get('country')
    country = country_dict.get(country_code.lower())
    region, city = ipinfo.get('region'), ipinfo.get('city')
    if country_code in ["US"]: city += f", {region}"
    return [ip, city, country]

def handle_search(search):
    if search.count(".") == 3:
        infos = [get_location_list(search)]
        chosen_index = 1
    else:
        url = f"https://atlas.ripe.net/api/v2/anchors/?format=json&page_size={num}&"

        if len(search) == 2: url += f"country={search.upper()}"
        else: url += f"search={search}"

        anchors = requests.get(url).json().get("results", [])
        if not anchors:
            print(f"no anchors found for search {search}")
            return

        infos = []
        try:
            for anchor in anchors:
                ip = anchor.get("ip_v4")
                code = anchor.get("hostname")[:6]
                if not any(entry and entry[0] == ip for entry in infos):
                    try:
                        start_time = time.monotonic()
                        subprocess.check_output(["ping", "-c", "1", "-W", "1", ip])
                        latency = f"{round((time.monotonic() - start_time) * 1000)}ms"
                        info = get_location_list(ip)
                        infos.append(info)
                        print(f"{len(infos)}. {code}: {ip} - {info[1]}, {info[2]} ({latency})")

                    except subprocess.CalledProcessError: pass
        except KeyboardInterrupt: pass

        if len(anchors) == num: print(f"more anchors not shown")
        if not infos:
            print(f"no responses from {search} ips")
            return

        chosen_index = input("choose ip num to add: ")

    entries = []
    if os.path.exists("entries.json"):
        with open("entries.json") as file:
            entries = json.load(file)
    entries.append(infos[int(chosen_index) - 1])
    with open("entries.json", "w") as file:
        json.dump(entries, file)

handle_search(input("search location or enter ip: "))