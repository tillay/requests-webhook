## requests webhook

a python script i made to log requests to my webserver for debugging purposes

this has only been tested on caddy

to use:
1. clone the repo and such
2. add an env and change the line `load_dotenv("/root/secrets/env")` in the script to have the path to your env
3. make a [webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) and an [ipregistry](https://ipregistry.co/) token
4. make sure your env has the following lines for the secrets
```
FELLAS_WEBHOOK=https://discord.com/api/webhooks/....
IPREGISTRY_TOKEN=ira_....
```
5. make sure your caddy config has logging enabled like so (if you change the path you have to change it in the code too)
```
log {
    output file /var/log/caddy/caddy.log
    format json
}
```
6. run `python3 logfollower.py` in the same directory as the script to start it
