import os, asyncio, json, socket, requests, aiofiles
from dotenv import load_dotenv
from datetime import datetime

load_dotenv("/root/secrets/env")
log_path = "/var/log/caddy/caddy.log"

bot_requests = ["php", "git", "env", "wp", "xml", "api", "?"]
bot_isps = ["ahrefs", "ovh", "hetzner", "techoff", "google", "microsoft", "amazon", "digitalocean"]

def post_embed(embed): requests.post(os.getenv("FELLAS_WEBHOOK"), json={"embeds": [embed]}, timeout=5)
def status_embed(title, color): post_embed({"title": title, "color": color})

# get dict for cloudflare abbreviation to country
with open("pops.json") as f:
    pop_cities = json.load(f)

# get dict for country name from code
with open("codes.json") as f:
    country_dict = json.load(f)

def format_block(display_name, domain):
    if display_name and domain:
        return f"[{display_name}](https://{domain})"
    return display_name or f"https://{domain}" or ""

def sub_search(string, array): return any(substring.lower() in string.lower() for substring in array)

def get_visitor_info(remote_ip):
    visitor_info = None
    is_new_visitor = True

    if not os.path.exists("cache.txt"):
        open("cache.txt", "w").close()
    with open("cache.txt") as cache_file:
        for cached_line in cache_file:
            line_json = json.loads(cached_line.strip())
            if line_json['ip'] == remote_ip:
                visitor_info = line_json
                is_new_visitor = False
                break

    # run this if they are new here
    if not visitor_info:
        print("detected ip is new")

        visitor_info = requests.get(
            f"https://api.ipregistry.co/{remote_ip}"
            f"?key={os.getenv("IPREGISTRY_TOKEN")}",
            timeout=4).json()

        # append line to cache file
        with open("cache.txt", "a") as cache_file:
            cache_file.write(json.dumps(visitor_info) + "\n")

        # if cache file is over 1000 lines now, remove the first line
        with open("cache.txt", "r") as cache_file: lines = cache_file.readlines()
        if len(lines) > 1000:
            with open("cache.txt", "w") as cache_file:
                cache_file.writelines(lines[1:])

    return visitor_info, is_new_visitor

prev_uri, prev_ip, prev_time = None, None, 0

async def process_line(line):
    data = json.loads(line)
    try:
        # get data from caddy log
        remote_ip = data["request"]["headers"]["Cf-Connecting-Ip"][0]
        uri = data["request"]["uri"]
        user_agent = data["request"]["headers"]["User-Agent"][0]
        cf_server = data["request"]["headers"]["Cf-Ray"][0].split("-")[1]

        country_code = data["request"]["headers"]["Cf-Ipcountry"][0]
        country = country_dict.get(country_code.lower())
        region_code = data["request"]["headers"]["Cf-Region-Code"][0]
        region = data["request"]["headers"]["Cf-Region"][0]
        city = data["request"]["headers"]["Cf-Ipcity"][0]
        lat = data["request"]["headers"]["Cf-Iplatitude"][0]
        lon = data["request"]["headers"]["Cf-Iplongitude"][0]

        status = str(data["status"])
        timestamp = float(data["ts"])

        request_path = (
            f"{'https://' if data['level'] == 'info' else ''}"
            f"{(data["request"]["host"] + '/' + uri).replace('//', '/')}"
        )
    except KeyError as k:
        print("rejected due to weird headers")
        try: offender_ip = data["request"]["headers"]["Cf-Connecting-Ip"][0]
        except KeyError: offender_ip = data['request']['remote_ip'] + "-"
        headers = []
        for header_name, header_value in data["request"]["headers"].items():
            headers.append(f"{header_name}: `{header_value[0]}`")
        post_embed({
            "title": f"Bad headers!", "color": 0xf5b342,
            "fields": [
                {"name": "IP", "value": offender_ip, "inline": True},
                {"name": "Request", "value": data["request"]["uri"], "inline": True},
                {"name": "Headers", "value": '\n'.join(headers), "inline": False},
                {"name": "Error", "value": str(k), "inline": False}
            ]})
        return

    print(
        f"{datetime.fromtimestamp(timestamp).strftime("%m/%d/%Y at %H:%M:%S")}\n\n"
        f"received request for {request_path}\n"
        f"returned code {status} (outcome: {data["level"]})\n"
        f"remote ip: {remote_ip}\n"
        f"user agent: {user_agent}\n"
    )

    global prev_uri, prev_ip, prev_time

    try: # filter out asset spam
        referrer = data["request"]["headers"]["Referer"][0]
        has_referrer = referrer.startswith("https://tilley.lol")
        print(f"referred from: {referrer}")
        if (
                has_referrer and prev_ip == remote_ip and
                timestamp - prev_time < 5 and
                ("." in uri or uri == f"{prev_uri}/" or uri == prev_uri)
        ):
            print(f"rejected due to asset request (uri: {uri})")
            return

    except KeyError: print("no referrer detected")

    # filter out bad bot spam
    if sub_search(request_path, bot_requests) or timestamp - prev_time < 0.1:
        print(f"rejected due to likely spam")
        return

    prev_uri, prev_ip, prev_time = uri, remote_ip, timestamp

    visitor_info, is_new_visitor = get_visitor_info(remote_ip)

    # build nice looking links for embed
    company_block = format_block(
        visitor_info["company"]["name"],
        visitor_info["company"]["domain"],
    )

    connection_block = format_block(
        visitor_info["connection"]["organization"],
        visitor_info["connection"]["domain"],
    )

    if connection_block == company_block: connection_block = ""

    organization_link = (
        f"{company_block} through {connection_block}"
        if company_block and connection_block
        else company_block or connection_block
    )

    location_text = ", ".join(filter(None, [
        city, region if country_code in ["DE", "US", "GB"] else None, country
    ]))

    location_link = (
        f"[{location_text}]"
        f"(https://www.openstreetmap.org/#map=12/{lat}/{lon})"
    )

    cf_link = (
        f"{country_code} -> [{cf_server} ({pop_cities.get(cf_server)})]"
        f"(https://mining.cloudflare.manfredi.io/pops/{cf_server})"
    )

    # reverse lookup to see if there are domains attached to the ip
    try: hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(remote_ip)
    except socket.herror: hostname = None

    tags = []
    security_data = visitor_info["security"]

    if country_code in ["GB", "US"]: icon_code = f"{country_code.lower()}-{region_code.lower()}"
    else: icon_code = country_code.lower()
    icon_link = f"https://flagcdn.com/160x120/{icon_code}.png"
    ip_link = f"[{remote_ip}](https://api.ipregistry.co/{remote_ip}?key=tryout)"

    # set embed color and title details
    embed_title = ""
    embed_color = 0x3a3aff
    if is_new_visitor:
        embed_title += "New "
        embed_color = 0xf783ff
    try:
        if "Discord" in user_agent and region_code == "SC":
            embed_title = "Discord Scraper"
            embed_color = 0x9b32db
        elif "Cloudflare" in organization_link:
            embed_title = "Cloudflare"
            embed_color = 0xf38020
            if "WARP" in organization_link:
                embed_title += " Warp User"
        elif security_data['is_tor']:
            embed_title += "Tor User"
            embed_color = 0x8506c9
        elif security_data['is_vpn']:
            embed_title += "VPN User"
            embed_color = 0x42f584
        elif visitor_info['carrier']['name'] is not None:
            embed_title += "Mobile User"
            embed_color = 0x0c9378
            tags.append("mobile")
        elif hostname is not None and "starlink" in hostname:
            embed_title += "Starlink User"
            embed_color = 0x888888
            tags.append("satellite")
        elif sub_search(organization_link, bot_isps) or sub_search(user_agent, ["http", "bot"]):
            embed_title += "Bot"
            embed_color = 0xf5d742
        elif security_data['is_attacker'] or security_data['is_threat']:
            embed_title = "Hostile "
            embed_color = 0xff0000
        else:
            embed_title += "Visitor"
    except Exception as e:
        print("error:", e)
        tags.append("errored")

    # levi detection - remove in prod
    if ("Amazon" in organization_link) and security_data["is_vpn"]:
        embed_title = "Levi"
        icon_link = "https://m.tilley.lol/leevi.png"

    embed = {
        "title": f"{embed_title} Detected",
        "color": embed_color,
        "fields": [
            {"name": "IP", "value": ip_link, "inline": True},
            {"name": "ISP", "value": organization_link, "inline": True},
            {"name": "\u200b", "value": "\u200b", "inline": True},
            {"name": "Cloudflare Server", "value": cf_link, "inline": True},
            {"name": "Location", "value": location_link, "inline": True},
            {"name": "\u200b", "value": "\u200b", "inline": True},
            {"name": "User Agent", "value": user_agent, "inline": False},
            {"name": "Request", "value": f"{request_path} ({status})", "inline": False},
        ],
        "thumbnail": {
            "url": icon_link
        }
    }

    for key, value in security_data.items():
        if value is True: tags.append(key.removeprefix("is_").replace('_', ' '))
    if "Cookie" in data["request"]["headers"]: tags.append("browser")

    if tags:
        embed['fields'].append({"name": "Tags", "value": ", ".join(tags), "inline": False})
        print(f"added tags: {tags}")

    if hostname is not None:
        embed["fields"].append({"name": "Detected domain", "value": hostname, "inline": False})
        print("added detected domain", hostname)

    post_embed(embed)
    print("\nwebhook sent!")
    return

async def main():
    print(f"|{'-' * 20} Started! {'-' * 20}|")
    status_embed("Started!", 0x008f1d)
    async with aiofiles.open(log_path) as log_file:
        await log_file.seek(0, 2)

        while True:
            line = await log_file.readline()
            if line:
                print(f"{'_' * 60}\n")
                try: await process_line(line)
                except Exception as line_exception:
                    post_embed({
                        "title": f"Error when parsing line", "color": 0xeb5d10,
                        "fields": [
                            {"name": "Error", "value": str(line_exception), "inline": False},
                            {"name": "Failed line", "value": line, "inline": False}
                        ]})
            else: await asyncio.sleep(0.1)

try: asyncio.run(main())
except KeyboardInterrupt: status_embed("Stopped with keyboard!", 0xff007f)
except Exception as error: status_embed(f"Entire program went up in flames: {error}", 0xfa2323)
