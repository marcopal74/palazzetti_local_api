import logging, asyncio, json, requests, aiohttp

from palazzetti_local_api import Palazzetti, PalDiscovery

_LOGGER = logging.getLogger(__name__)

def main():
    api_discovery=PalDiscovery()
    loop = asyncio.get_event_loop()

    print("Chiamata diretta:")
    found_ips=loop.run_until_complete(api_discovery.discovery())
    print(found_ips)

    if found_ips:
        use_ip=found_ips[0]
        #use_ip="192.168.1.133"

        print(f"Using IP: {use_ip}")
        api=Palazzetti(use_ip)
    else:
        print("No ConnBox found")
        return

    loop.run_until_complete(api.async_get_alls())
    #loop.close()
    print(f"{api.get_datas()}")
    #key volutamente errata
    print(api.get_key('MACive'))
    #diverse forme di print
    print(api.get_key('MAC'))
    print(f"{api.get_key('STATUS')} {api.get_key('MAC')}")
    loop.run_until_complete(api.async_get_gen('GET STDT'))
    loop.close()
    print(f"{api.get_datas()}")


if __name__ == "__main__":
    main()