import requests, os, asyncio
from dotenv import load_dotenv
from logfollower import get_visitor_info

async def process_line(line):
    if "Accepted publickey" in line:
        ip = line.split(" ")[8]
        title, color = "Tilley connected", 0x3ef06e
    elif "Disconnected from" in line:
        ip = line.split(" ")[7]
        title, color = "Tilley disconnected", 0xf0374a
    else: return
    user = line.split(" ")[6]

    if not (ip and user): return

    visitor_info, _ = get_visitor_info(ip)

    country = visitor_info["location"]["country"]["name"]
    country_code = visitor_info["location"]["country"]["code"].lower()
    region = visitor_info["location"]["region"]["name"]
    region_code = visitor_info["location"]["region"]["code"].lower()
    city = visitor_info["location"]["city"]

    icon_code = country_code if country_code in ["GB", "US"] else region_code

    location_text = ", ".join(filter(None, [
        city, region if country_code in ["DE", "US", "GB", "CA"] and region != "" else None, country
    ]))

    embed = {
        "title": title,
        "color": color,
        "fields": [
            {"name": "IP", "value": ip, "inline": False},
            {"name": "User", "value": user, "inline": False},
            {"name": "Location", "value": location_text, "inline": False},
        ],
        "thumbnail": {
            "url": f"https://flagcdn.com/160x120/{icon_code}.png"
        }
    }

    requests.post(os.getenv("SSHD_WEBHOOK"), json={"embeds": [embed]}, timeout=5)

async def main():
    with open("/var/log/auth.log") as log_file:
        log_file.seek(0, 2)
        while True:
            line = log_file.readline()
            if line: await process_line(line)
            else: await asyncio.sleep(0.1)

load_dotenv("/root/secrets/env")
asyncio.run(main())
