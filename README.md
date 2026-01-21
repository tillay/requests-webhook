## requests webhook

a python script i made to log requests to my webserver for debugging purposes

this has only been tested on [caddy](https://caddyserver.com/) and probably doesn't work on other webservers

this needs a connection proxied through [cloudflare](https://cloudflare.com/) with the [visitor location info in headers](https://developers.cloudflare.com/network/ip-geolocation/) enabled

to use:
1. clone the repo and such
3. add an env and change the line `load_dotenv("/root/secrets/env")` in the script to have the path to your env
4. install dependencies (on debian `sudo apt install python3-aiofiles python3-dotenv`)
5. make a [discord webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) and get an [ipregistry](https://ipregistry.co/) token
6. make sure your env has the following lines for the secrets
```
FELLAS_WEBHOOK=https://discord.com/api/webhooks/....
IPREGISTRY_TOKEN=ira_....
```
6. make sure your caddy config has [logging enabled](https://caddyserver.com/docs/caddyfile/options#log) like so (if you change the path you have to change it in the code too)
```
log {
    output file /var/log/caddy/caddy.log
    format json
}
```
7. run `python3 logfollower.py` in the same directory as the script to start it. I recommend using [tmux](https://tmuxcheatsheet.com/).
