import logging, asyncio, json, requests, aiohttp

from palazzetti_sdk_local_api import Palazzetti, PalDiscovery, PalComm
# Run python3 setup.py build_py before execute
from build.lib.palazzetti_sdk_local_api_sync import SyncPalazzetti, SyncPalDiscovery, SyncPalComm

_LOGGER = logging.getLogger(__name__)

TEST_IP = "192.168.18.21"

def main_findip():
    api_discovery=PalDiscovery()
    loop = asyncio.get_event_loop()

    print("Chiamata diretta:")
    found_ips=loop.run_until_complete(api_discovery.discovery_UDP())
    print(found_ips)

    if not found_ips:
        print("No ConnBox found")
        return
    
    print(found_ips)

    """use_ip=found_ips[0]
    #use_ip="192.168.1.133"
    print(f"Using IP: {use_ip}")
    api=Palazzetti(use_ip)
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
    print(f"{api.get_datas()}")"""

def main2():
    api_discovery=PalDiscovery()
    loop = asyncio.get_event_loop()

    print("Chiamata diretta:")
    use_ip=TEST_IP
    is_IP_OK=loop.run_until_complete(api_discovery.checkIP_HTTP(use_ip))
    print(f"From checkIP_HTTP: {is_IP_OK}")

    if not is_IP_OK:
        print("No ConnBox found")
        return

    #use_ip="192.168.1.133"
    print(f"Using IP: {use_ip}")
    api=Palazzetti(use_ip)

    loop.run_until_complete(api.async_get_alls())
    #loop.close()
    print(f"{api.get_datas()}")
    #key volutamente errata
    print(api.get_key('MACive'))
    #diverse forme di print
    print(api.get_key('MAC'))
    print(f"{api.get_key('STATUS')} {api.get_key('MAC')}")
    loop.run_until_complete(api.async_get_stdt())
    loop.close()
    print(f"{api.get_datas()}")

def main3():
    api_discovery=PalDiscovery()
    loop = asyncio.get_event_loop()

    print("Chiamata diretta:")
    use_ip = TEST_IP
    is_IP_OK=loop.run_until_complete(api_discovery.checkIP_UDP(use_ip))
    print(f"From checkIP_UDP {is_IP_OK}")

    if not is_IP_OK:
        print("No ConnBox found via UDP, checking via HTTP...")
        is_IP_OK=loop.run_until_complete(api_discovery.checkIP_HTTP(use_ip))
        print(f"From checkIP_HTTP {is_IP_OK}")
        if not is_IP_OK:
            print("No ConnBox found")
            return
    
    #use_ip="192.168.1.133"
    print(f"Using IP: {use_ip}")
    api=Palazzetti(use_ip)
    
    loop.run_until_complete(api.async_get_alls())
    #loop.close()
    print(f"{api.get_datas()}")
    #key volutamente errata
    print(api.get_key('MACive'))
    #diverse forme di print
    print(api.get_key('MAC'))
    print(f"{api.get_key('STATUS')} {api.get_key('MAC')}")
    loop.run_until_complete(api.async_get_stdt())
    loop.close()
    print(f"{api.get_datas()}")

def main4():
    api_discovery=PalDiscovery()
    loop = asyncio.get_event_loop()

    print("Chiamata diretta:")
    use_ip = TEST_IP
    is_IP_OK=loop.run_until_complete(api_discovery.checkIP(use_ip))
    print(f"From checkIP: {is_IP_OK}")

    if not is_IP_OK:
        print("No ConnBox found")
        return

    #use_ip="192.168.1.133"
    print(f"Using IP: {use_ip}")
    api=SyncPalazzetti(use_ip)
    
    print("Recupera TUTTO")
    #loop.run_until_complete(api.async_get_alls())
    #loop.close()

    print(api.get_alls())
    api.get_stdt()

    print(f"{api.get_data_json()}")
    #key volutamente errata
    print(api.get_key('MACive'))
    #diverse forme di print
    print(api.get_key('MAC'))
    print(f"{api.get_key('STATUS')} {api.get_key('MAC')}")
    #loop.run_until_complete(api.async_get_gen('GET STDT'))
    #loop.run_until_complete(api.async_config_parse())
    loop.close()
    print("Recupera GET STDT")
    print(f"{api.get_data_stdt_json()}")
    print("Recupera CONFIG")
    print(f"{api.get_data_config_json()}")

def main5():
    loop = asyncio.get_event_loop()

    use_ip="192.168.20.45"
    print(f"Using IP: {use_ip}")
    api=Palazzetti(use_ip)

    loop.run_until_complete(api.async_get_alls())
    print(f"{api.get_data_json()}")
    #key volutamente errata
    print(api.get_key('MACive'))
    #diverse forme di print
    print(api.get_key('MAC'))
    print(f"{api.get_key('STATUS')} {api.get_key('MAC')}")
    loop.close()
    print(f"interrogazione config: {api.get_data_config()['flag_tipologia_aria']}")
    if api.get_data_config()['flag_tipologia_aria']:
        print("Aria")
    else:
        print("Acqua")

def main6():
    #api_discovery=PalComm()
    api_discovery=PalDiscovery()
    loop = asyncio.get_event_loop()

    print("Chiamata diretta:")
    use_ip = "192.168.1.130"
    #is_IP_OK=loop.run_until_complete(api_discovery.async_callHTTP(use_ip, b"plzbridge?"))
    is_IP_OK=loop.run_until_complete(api_discovery.checkIP_UDP(use_ip))
    print(f"From checkIP_UDP {is_IP_OK}")

def main7():
    api_discovery=PalComm()
    #api_discovery=PalDiscovery()
    loop = asyncio.get_event_loop()

    print("Chiamata diretta:")
    use_ip = "192.168.1.121"
    is_IP_OK=loop.run_until_complete(api_discovery.async_getHTTP(use_ip, "GET STDT"))
    #is_IP_OK=loop.run_until_complete(api_discovery.checkIP_UDP(use_ip))
    print(f"From checkIP_HTTP {is_IP_OK}")

if __name__ == "__main__":
    main4()