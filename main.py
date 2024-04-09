import requests
import json
import argparse
import os
from datetime import datetime, timedelta, date
    
def config_list(args):
    if not os.path.isfile("domains.json"):
        print("No configuration file present")
        return
    else:
        with open("domains.json", "r") as f:
            try:
                config = json.load(f)
            except json.decoder.JSONDecodeError:
                print("Configuration file is malformed")
                return
        
        problems = []
        if ("API" not in config):
            problems.append("API key not present")
        if ("domains" not in config):
            problems.append("Domain list not present")
        elif (len(config["domains"]) == 0):
            problems.append("Domain list not populated")
            
        if (problems):
            print("Configuration invalid: ")
            for i in problems:
                print("\t" + i)
            return
            
        print(f"API Key present: ...{config['API'][-6:]}\n")
        for i in config["domains"]:
            print("Domain Name: " + i)
            print("Domain Zone ID: " + config["domains"][i]["ID"])
            for j in config["domains"][i]["names"]:
                print(f"\t{j}\t(ID: {config['domains'][i]['names'][j]})")
            print()
        if ("ip" in config):
            print("Cached IP address: " + config["ip"].get("ip"))
            print("Cache time: " + config["ip"].get("last_set"))
        
def config_create(args):
    if (os.path.isfile("domains.json")):
        if (args.yes):
            accept = input(f"Existing domains.json file! Do you wish to overwrite it and continue? A backup {'will NOT' if args.no_backup else 'will'} be made. (Y/N) ").upper()
            if (accept in ["Y", "YES"]):
                pass
            else:
                return
        
        if (not args.no_backup):
            backup_date = datetime.today().isoformat()
            with open("domains.json", "r") as prev, open(f"domains_{backup_date}.json.bak", "w") as new:
                new.writelines(prev.readlines())
            print("Backed up existing configuration file to 'domains_{backup_date}.json.bak'")
            
    while True:
        API = input("API key? ")
         
        req = session.get("https://api.cloudflare.com/client/v4/user/tokens/verify", headers={"Authorization": "Bearer " + API})
        if (req.status_code != 200):
            print(f"Error from Cloudflare. Status code {req.status_code}")
            continue
        else:
            break
            
    session.headers = {
        "Content-Type": "application/json",
        "X-Auth-Email": API,
        "Authorization": f"Bearer {API}"
    }
    req = session.get("https://api.cloudflare.com/client/v4/zones")
    zones = [(i["name"], i["id"]) for i in json.loads(req.text)["result"]]
    
    while True:
        print("Zones found:")
        for i in range(len(zones)):
            print(f"\t{i+1}: {zones[i]}")
        select = input("Zones? (numbers separated by commas) ").strip().split(",")
        try:
            select = [int(i) for i in select]
        except ValueError:
            print("Selection must be a number")
            continue
            
        if (not all([i >= 1 and i <= len(zones) for i in select])):
            print(f"Inputs must be between 1 and {len(zones)}\n")
            continue
        else:
            selected_zones = [[zones[i-1][0], zones[i-1][1], []] for i in select]
            break
            
    for i in range(len(selected_zones)):
        req = session.get(f"https://api.cloudflare.com/client/v4/zones/{selected_zones[i][1]}/dns_records", params={"type": "A"})
        domains = [(j["name"], j["id"]) for j in json.loads(req.text)["result"]]
        while True:
            print(f"A records for {selected_zones[i][0]}:")
            for j in range(len(domains)):
                print(f"\t{j+1}: {domains[j]}")
            select = input("Domains? (numbers separated by commas) ").strip().split(",")
            try:
                select = [int(i) for i in select]
            except ValueError:
                print("Selection must be a number")
                continue
                
            if (not all([i >= 1 and i <= len(domains) for i in select])):
                print(f"Inputs must be between 1 and {len(domains)}\n")
                continue
            else:
                selected_zones[i][2] = [(domains[j-1][0], domains[j-1][1]) for j in select]
                break
                
    config = {"API": API, "domains": {i[0]: {"ID": i[1], "names": {j[0]: j[1] for j in i[2]}} for i in selected_zones}}
    with open("domains.json", "w") as f:
        json.dump(config, f)
    print("\nConfiguration saved as 'domains.json'")
    
def config_edit(args):
    print("This isn't implemented yet! Use 'config create' to make it from scratch")
    
def config_backup(args):
    print("This isn't implemented yet! Manually copy the 'domains.json' file to back it up")
    
def config_restore(args):
    print("This isn't implemented yet! Manually overwrite the 'domains.json' file with a backup to restore it")
    
def run_main(args):
    if not os.path.isfile("domains.json"):
        print("No configuration file present")
        return
    else:
        with open("domains.json", "r") as f:
            config = json.load(f)
        
    if (args.update_ip):
        fetch_ip = True
    elif ("ip" in config): #Only check it hourly!
        if (datetime.fromisoformat(config["ip"].get("last_set")) + timedelta(hours=1) < datetime.today()):
            fetch_ip = True
        else:
            fetch_ip = False
    else:
        fetch_ip = True
            
    if (args.set_ip):
        ip = args.set_ip
        print("IP manually set to: " + ip)
    else:
        if (fetch_ip):
            response = requests.get("http://ipecho.net/plain")
            response.raise_for_status()
            ip = response.text
            config["ip"] = {"ip": ip, "last_set": datetime.today().isoformat()}
            with open("domains.json", "w") as f: #This is the only part of the config we edit, so just drop it here
                json.dump(config, f)
            print("IP updated to: " + ip)
        else:
            ip = config["ip"]["ip"]
            print("Cached IP of: " + ip)
            
    session.headers = {
        "Content-Type": "application/json",
        "X-Auth-Email": config["API"],
        "Authorization": f"Bearer {config['API']}"
    }
    
    print()
    if (args.dry_run):
        print("DRY RUN: NO CHANGES MADE")
    for i in config["domains"]:
        if (args.zone and i not in args.zone):
            continue
        
        zone = config["domains"][i]["ID"]
        print("Updating subdomains on " + i)
        for j in config["domains"][i]["names"]:
            if (args.domain and j not in args.domain):
                continue
            if (not args.dry_run):
                response = session.patch(f"https://api.cloudflare.com/client/v4/zones/{zone}/dns_records/{config['domains'][i]['names'][j]}", json={
                    "content": ip,
                    "name": j,
                    "type": "A",
                    "ttl": 60
                })
            print("\tUpdated subdomain: " + j)
        print()
    
function_map = {
    "config": {
        "list": config_list,
        "create": config_create,
        "edit": config_edit,
        "backup": config_backup,
        "restore": config_restore
    },
    "run": run_main
}
    
parser = argparse.ArgumentParser(
    prog="cloudflareDNS", 
    description='''Dynamic Cloudflare DNS configuration, for multiple zones.''', 
    epilog="Connor Heindel (connor@heindel.us)",
    add_help=True,
    formatter_class=argparse.RawDescriptionHelpFormatter
)

subparsers = parser.add_subparsers(required=True, dest="parser_command")

parser_config = subparsers.add_parser("config", help="work with the domains.json configuration file")
parser_config_sub = parser_config.add_subparsers(dest="configuration_command", required=True)

parser_config.add_argument("-b", "--no-backup", help="skip saving a configuration backup", action="store_true")
parser_config.add_argument("-y", "--yes", help="accept any overrides", action="store_false")

parser_config_list = parser_config_sub.add_parser("list", help="list configuration")
parser_config_create = parser_config_sub.add_parser("create", help="create new configuration")
parser_config_edit = parser_config_sub.add_parser("edit", help="edit current configuration")
parser_config_backup = parser_config_sub.add_parser("backup", help="backup current configuration")
parser_config_restore = parser_config_sub.add_parser("restore", help="restore configuration backup")

parser_run = subparsers.add_parser("run", help="push DNS changes to Cloudflare", )
parser_run.add_argument("--dry-run", help="go through the process without making any changes", action="store_true")
parser_run.add_argument("-z", "--zone", help="update only the specified zones", action="append")
parser_run.add_argument("-d", "--domain", help="update only the specified subdomains (requires --zone)", action="append")
parser_run.add_argument("-i", "--set-ip", help="override the IP address to a specified address")
parser_run.add_argument("-u", "--update-ip", help="update the IP address no matter the cache date", action="store_true")

args = parser.parse_args()

session = requests.Session()
session.headers = {
    "Content-Type": "application/json"
}

if (args.parser_command == "config"):
    func = function_map["config"][args.configuration_command]
else:
    func = function_map["run"]
    
func(args)