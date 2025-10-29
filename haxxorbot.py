import re, os, discord, asyncio, aiohttp, time, json, sys

bot_token_file = "~/bot_tokens/tilleyhelper.token"
channel_id = 1432235050476503154
boring_list = ["US", "RO", "RU"]
mundane_list = ["NL", "IN", "SG", "ID"]

token = open(os.path.expanduser(bot_token_file)).read().strip()
client = discord.Client(intents=discord.Intents.default())

user_patterns = [
    re.compile(r"Accepted publickey for (\S+) from"),
    re.compile(r"Invalid user (\S+) from"),
    re.compile(r"rhost=\d{1,3}(?:\.\d{1,3}){3}\s+user=(\S+)")
]

async def get_json(url):
    headers = {'User-Agent': 'curl/7.68.0'}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            return await resp.json()

async def process_line(line, channel):
    if not any(k in line for k in ("Accepted publickey", "Invalid user", "authentication failure")): return
    user = next((p.search(line).group(1) for p in user_patterns if p.search(line)), None)
    ip = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b").search(line).group(1)
    if not (ip and user): return

    info = None
    if not os.path.exists("cache.txt"): open("cache.txt", "w").close()
    is_new_haxxor = False
    with open("cache.txt") as cache:
        lines = cache.readlines()
        for i in range(len(lines)):
            if ip in lines[i]:
                info = json.loads(lines[i].strip())
                break

    if not info:
        info = await get_json(f"https://ipinfo.io/{ip}")
        with open("cache.txt", "a") as cache:
            cache.write(f"{json.dumps(info)}\n")
        is_new_haxxor = True
    country_name = await get_json(f"https://restcountries.com/v3.1/alpha/{info['country']}")
    country_name = country_name[0]["name"]["common"]

    location=f"[{re.sub(r'\b(\w+(?: \w+)*)(?:, \1\b)+',r'\1',f'{info['city']}, {info['region']}, {country_name}')}]"
    map_link = location + f"(https://www.openstreetmap.org/#map=12/{info['loc'].replace(',', '/')})"
    org_link = f"[{' '.join(info['org'].split()[1:])}](https://ipinfo.io/{info['org'].split()[0]})"

    if "Accepted" in line:
        title, color = "Tilley detected", 0xd447e8
    elif is_new_haxxor:
        title, color = "New haxxor detected", 0x3483eb
    elif info['country'] in boring_list:
        title, color = "Boring haxxor detected", 0xed1e1e
    elif info['country'] in mundane_list:
        title, color = "Mundane haxxor detected", 0xffb800
    else:
        title, color = "Interesting haxxor detected", 0x1ed123

    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="User", value=user, inline=False)
    embed.add_field(name="IP", value=ip, inline=False)
    embed.add_field(name="Location", value=map_link, inline=False)
    embed.add_field(name="Host", value=org_link, inline=False)

    thumbnail = f"https://flagsapi.com/{info['country']}/flat/64.png"
    embed.set_thumbnail(url=thumbnail)

    await channel.send(embed=embed)

    with open("haxxorlog.csv", "a") as file:
        file.write(f"{ip},{user},{info['country']},{info['org'].replace(",", "")},{int(time.time())}\n")

@client.event
async def on_ready():
    channel = await client.fetch_channel(channel_id)
    with open("/var/log/auth.log") as log_file:
        log_file.seek(0, 2)
        while True:
            line = log_file.readline()
            if line: await process_line(line, channel)
            else: await asyncio.sleep(0.1)

if not os.path.exists("/var/log/auth.log"):
    print("please install rsyslog")
    sys.exit(1)

client.run(token)
