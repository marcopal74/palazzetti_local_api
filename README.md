# Palazzetti SDK - Local HUB

## Library to interact with Palazzetti product via LOCAL HTTP HUB

Requires Python 3.6 and uses palazzetti-sdk-asset-parser to detect product capabilities.

```python
import asyncio

from palazzetti_sdk_local_api import Hub

def main():
    loop = asyncio.get_event_loop()
    use_ip = "192.168.20.94"
    hub = Hub(use_ip)

    print("----- BEFORE UPDATE -----")
    print(f"ID Hub: {hub.hub_id}")
    print(f"Online: {hub.hub_online}")
    print(f"BioCC: {hub.hub_isbiocc}")
    print(f"Product Online: {hub.product_online}")
    print("Attributes:")
    print(hub.get_attributes())

    # now update the hub without discovery only via UDP (deep=False)
    print (f"Please wait, checking Hub at {use_ip}...")
    loop.run_until_complete(hub.async_update(discovery=False, deep=False))

    print("----- POST UPDATE -----")
    if hub.hub_online:
        print(f"Online: {hub.hub_online}")
        print(f"Label: {hub.label}")
        print(f"ID Hub: {hub.hub_id}")
        print(f"BioCC: {hub.hub_isbiocc}")
        print("Attributes:")
        print(hub.get_attributes())
        if hub.product_online:
            print(f"Product Online: {hub.product_online}")

            # now update the hub with discovery and HTTP failover if UDP fails (deep=True)
            print (f"Please wait, discovering product details for Hub {hub.hub_id}...")
            loop.run_until_complete(hub.async_update(discovery=True, deep=True))

            if hub.product and hub.product.online:
                print(f"ID Product: {hub.product.product_id}")
                print("Product Capabilities:")
                print(hub.product.get_data_config_json())
                print("Product Attributes:")
                print(hub.product.get_prod_data_json())
                return

            # this should neve happen...
            print ("Product should be online but has not been initiated")
            return

        print ("Hub is online but no Product found")
        return

    print ("Hub offline")
```