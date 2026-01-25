import subprocess, random, os, json

if os.path.exists("entries.json"):
    with open("entries.json") as file:
        entries = json.load(file)

random.shuffle(entries)
for entry in entries:
    city, country = entry[1], entry[2]

    print(f"{city}, {country}: ", end="")
    process = subprocess.Popen(
        ["ping", "-c4", "-w1", "-i0.2", entry[0]],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )

    responses = 0
    for line in process.stdout:
        if "rtt" in line: summary = line
        if "icmp" in line:
            print(".", end="", flush=True)
            responses += 1
    if responses == 0: summary = None

    rtt = round(float(summary.split('/')[4])) if summary else None

    thresholds = [(30, "\033[92m"), (80, "\033[32m"), (160, "\033[93m"), (200, "\033[33m"), (260, "\033[91m")]
    if rtt is None: color = "\033[90m"
    else: color = next((c for t, c in thresholds if rtt < t), "\033[31m")

    print(f"\033[{responses}D{color}{rtt if rtt else ' ---'}\033[0m{'ms' if rtt else ''}  ")