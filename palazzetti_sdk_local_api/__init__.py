import json
import logging
import requests
import aiohttp
import asyncio
import socket
import time

from palazzetti_sdk_asset_parser import AssetParser as psap

_LOGGER = logging.getLogger(__name__)

UDP_PORT = 54549
DISCOVERY_TIMEOUT = 5
DISCOVERY_MESSAGE = b"plzbridge?"
BUFFER_SIZE = 2048
HTTP_TIMEOUT = 15

#to be completed!!
class PalComm(object):
    async def async_callUDP(self, host, message):
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # Enable broadcasting mode
        server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        server.settimeout(DISCOVERY_TIMEOUT)
        server.sendto(message, (host, UDP_PORT))

        while True:
            # Receive the client packet along with the address it is coming from
            try:
                data, addr = server.recvfrom(BUFFER_SIZE)
                # print(data.decode('utf-8'))
                if data != "":
                    mydata = data.decode("utf-8")
                    mydata_json = json.loads(mydata)
                    if mydata_json["SUCCESS"] == True:
                        return mydata_json["DATA"]

            except socket.timeout:
                return

    async def async_getHTTP(self, host, message):
        queryStr = "http://" + host + "/cgi-bin/sendmsg.lua"
        # params for GET
        params = (("cmd", message),)
        _response_json = None

        # check if op is defined or stop here
        if message is None:
            return False
        # print(message)

        _LOGGER.debug("Executing command: {message}")

        mytimeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)

        try:
            async with aiohttp.ClientSession(timeout=mytimeout) as session:
                async with session.get(queryStr, params=params) as response:
                    if response.status != 200:
                        _LOGGER.error(
                            "Error during api request : http status returned is {}".format(
                                response.status
                            )
                        )
                        response = False
                    else:
                        # save response in json object
                        _response_json = json.loads(await response.text())

        except aiohttp.ClientError as client_error:
            _LOGGER.error("Error during api request: {emsg}".format(emsg=client_error))
            response = False
        except json.decoder.JSONDecodeError as err:
            _LOGGER.error("Error during json parsing: response unexpected from Cbox")
            self.state = "offline"
            response = False
        except:
            response = False

        if response == False:
            return False

        # If no response return
        if _response_json["SUCCESS"] != True:
            #maybe connection error between ConnBox and Stove
            return False

        return _response_json["DATA"]

class PalDiscovery(object):
    async def discovery_UDP(self):
        """discovers all ConnBoxes responding to broadcast"""

        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # Enable broadcasting mode
        server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        server.settimeout(DISCOVERY_TIMEOUT)
        myips = []
        server.sendto(DISCOVERY_MESSAGE, ("<broadcast>", UDP_PORT))
        while True:
            # Receive the client packet along with the address it is coming from
            try:
                data, addr = server.recvfrom(BUFFER_SIZE)
                # print(data)
                if data != "":
                    mydata = data.decode("utf-8")
                    mydata_json = json.loads(mydata)
                    if mydata_json["SUCCESS"] == True:
                        myips.append(addr[0])
                        # print(addr[0])

            except socket.timeout:
                # print("retry")
                myips = list(dict.fromkeys(myips))
                return myips

    async def checkIP_UDP(self, testIP):
        """verify the IP is a Connection Box using UDP"""

        api_discovery=PalComm()    
        use_ip = testIP
        
        _response = await api_discovery.async_callUDP(use_ip, DISCOVERY_MESSAGE)
        
        if not _response:
            return False
        
        return True

    async def checkIP_HTTP(self, testIP):
        """verify the IP is a Connection Box using HTTP call with command GET LABL"""
        api_discovery=PalComm()    
        use_ip = testIP
        
        _response = await api_discovery.async_getHTTP(use_ip, "GET STDT")
        
        if not _response:
            return False
        
        return True

    async def checkIP(self, testIP):
        is_IP_OK = await self.checkIP_UDP(testIP)
        # print(f"From checkIP_UDP {is_IP_OK}")

        if not is_IP_OK:
            # print("No ConnBox found via UDP, checking via HTTP...")
            is_IP_OK = await self.checkIP_HTTP(testIP)
            # print(f"From checkIP_HTTP {is_IP_OK}")
            if not is_IP_OK:
                # print("No ConnBox found")
                return False

        return True

class Palazzetti(object):
    """Palazzetti HTTP class"""

    op = None

    response_json_alls = None
    response_json_stdt = None

    response_json = None

    data = None
    data_config_json = None
    data_config_object = None

    last_op = None
    last_params = None

    def __init__(self, host, title="uniqueID"):
        self.ip = host
        self.state = "online"
        self.unique_id = title
        self.data = {}
        self.data["title"] = self.unique_id

        _LOGGER.debug("Init of class palazzetti")

        self.code_status = {
            0: "OFF",
            1: "OFF TIMER",
            2: "TESTFIRE",
            3: "HEATUP",
            4: "FUELIGN",
            5: "IGNTEST",
            6: "BURNING",
            9: "COOLFLUID",
            10: "FIRESTOP",
            11: "CLEANFIRE",
            12: "COOL",
            241: "CHIMNEY ALARM",
            243: "GRATE ERROR",
            244: "NTC2 ALARM",
            245: "NTC3 ALARM",
            247: "DOOR ALARM",
            248: "PRESS ALARM",
            249: "NTC1 ALARM",
            250: "TC1 ALARM",
            252: "GAS ALARM",
            253: "NOPELLET ALARM",
        }

        #carica tutti i dati possibili
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.async_get_stdt())
        loop.run_until_complete(self.async_get_alls())
        loop.run_until_complete(self.async_get_cntr())
        loop.close()

    # generic command
    #da togliere magari...
    async def async_get_gen(self, myrequest="GET LABL"):
        """Get generic request"""
        self.op = myrequest
        await self.async_get_request()

    # make request GET STDT
    async def async_get_stdt(self):
        """Get counters"""
        self.op = "GET STDT"
        await self.async_get_request()

    # make request GET ALLS
    async def async_get_alls(self):
        """Get All data or almost ;)"""
        self.op = "GET ALLS"
        await self.async_get_request()

    # make request GET CNTR
    async def async_get_cntr(self):
        """Get counters"""
        self.op = "GET CNTR"
        await self.async_get_request()

    async def async_get_request(self):
        """ request the stove """
        message=self.op
        _response_json = None

        # check if op is defined or stop here
        if message is None:
            return False

        # print(self.op)
        _LOGGER.debug("Executing command: {message}")
        # response = False

        api_discovery=PalComm()
        _response = await api_discovery.async_getHTTP(self.ip, message)

        if not _response:
            self.state = "offline"
            self.data["state"] = self.state
            self.response_json.update({"icon": "mdi:link-off"})
            return False
        
        #merge the result with the exixting responnse_json
        if self.response_json != None:
            response_merged = self.response_json.copy()
            response_merged.update(_response)
            self.response_json = response_merged
        else:
            self.response_json = _response
        
        self.state = "online"
        self.data["state"] = self.state
        self.response_json.update({"icon": "mdi:link"})
        self.data["ip"] = self.ip

        if self.op == "GET ALLS":
            self.data["status"] = self.code_status.get(
                self.response_json["STATUS"], self.response_json["STATUS"]
            )
            self.response_json_alls = _response
            self.__config_parse()
        elif self.op == "GET STDT":
            self.response_json_stdt = _response
            self.__config_parse()

    # send request to stove
    def request_stove(self, op, params):
        _LOGGER.debug("request stove " + op)

        if op is None:
            return False

        # save
        self.last_op = op
        self.last_params = str(params)

        retry = 0
        success = False

        response = False
        _response_json = None
        # error returned by Cbox
        while not success:
            # let's go baby
            try:
                response = requests.get(self.queryStr, params=params, timeout=30)
            except requests.exceptions.ReadTimeout:
                # timeout ( can happend when wifi is used )
                _LOGGER.error("Timeout reach for request : " + self.queryStr)
                _LOGGER.info("Please check if you can ping : " + self.ip)
                # print("palazzetti.stove - offline")
                self.state = "offline"
                self.data["state"] = self.state
                return False
            except requests.exceptions.ConnectTimeout:
                # equivalent of ping
                _LOGGER.error("Please check parm ip : " + self.ip)
                # print("palazzetti.stove - offline")
                self.state = "offline"
                self.data["state"] = self.state
                self.response_json.update({"icon": "mdi:link-off"})
                return False

            if response == False:
                self.state = "offline"
                self.data["state"] = self.state
                self.response_json.update({"icon": "mdi:link-off"})
                raise Exception("Sorry timeout")

            # save response in json object
            _response_json = json.loads(response.text)
            success = _response_json["SUCCESS"]

            # cbox return error
            if not success:
                # print("palazzetti.stove - com error")
                self.state = "com error"
                self.data["state"] = self.state
                self.response_json.update({"icon": "mdi:link-off"})
                _LOGGER.error(
                    "Error returned by CBox - retry in 2 seconds (" + op + ")"
                )
                time.sleep(2)
                retry = retry + 1

                if retry == 3:
                    _LOGGER.error(
                        "Error returned by CBox - stop retry after 3 attempt ("
                        + op
                        + ")"
                    )
                    break

        # merge response with existing dict
        if self.response_json != None:
            response_merged = self.response_json.copy()
            response_merged.update(_response_json["DATA"])
            self.response_json = response_merged
        else:
            self.response_json = _response_json["DATA"]

        self.response_json.update({"icon": "mdi:link"})
        self.response_json.update({"unique_id": self.unique_id})
        self.state = "online"
        self.data["state"] = self.state
        self.data["ip"] = self.ip

        return response

    # update configuration: call json parse function
    async def async_config_parse(self):
        asset_parser = psap(
            get_alls=self.response_json_alls, get_stdt=self.response_json_stdt
        )
        asset_capabilities = asset_parser.parsed_data
        self.data_config_object = asset_capabilities

    def __config_parse(self):
        asset_parser = psap(
            get_alls=self.response_json_alls, get_stdt=self.response_json_stdt
        )
        asset_capabilities = asset_parser.parsed_data
        self.data_config_object = asset_capabilities

    def get_sept(self):
        """Get target temperature for climate"""
        if self.response_json == None or self.response_json["SETP"] == None:
            return 

        return self.response_json["SETP"]

    # get generic KEY in the datas
    # if key doesn't exist returns None
    def get_key(self, mykey="STATUS"):
        """Get target temperature for climate"""
        if (
            self.response_json == None
            or (mykey in self.response_json) == False
            or self.response_json[mykey] == None
        ):
            return

        return self.response_json[mykey]

    def set_parameters(self, datas):
        """set parameters following service call"""
        self.set_sept(datas.get("SETP", None))  # temperature
        self.set_powr(datas.get("PWR", None))  # fire power
        self.set_rfan(datas.get("RFAN", None))  # Fan
        self.set_status(datas.get("STATUS", None))  # status

    def set_sept(self, value):
        """Set target temperature"""

        if value == None or type(value) != int:
            return

        op = "SET SETP"

        # params for GET
        params = (("cmd", op + " " + str(value)),)

        # avoid multiple request
        if op == self.last_op and str(params) == self.last_params:
            _LOGGER.debug("retry for op :" + op + " avoided")
            return

        # request the stove
        if self.request_stove(op, params) == False:
            return

        # change state
        print("set palazzetti.SETP to: " + self.response_json["SETP"])
        self.data["setp"] = self.response_json["SETP"]
        # self.hass.states.set('palazzetti.SETP', self.response_json['SETP'])

    def set_powr(self, value):
        """Set power of fire
        if value is None :
            return

        op = 'SET POWR'

        # params for GET
        params = (
            ('cmd', op + ' ' + str(value)),
        )

        # avoid multiple request
        if op == self.last_op and str(params) == self.last_params :
            _LOGGER.debug('retry for op :' +op+' avoided')
            return

        # request the stove
        if self.request_stove(op, params) == False:
            return

        # change state
        self.hass.states.set('palazzetti.PWR', self.response_json['PWR'])"""

    def set_rfan(self, value):
        """Set fan level

        if value == None:
            return

        # must be str or int
        if type(value) != str and type(value) != int:
            return

        op = 'SET RFAN'

        # params for GET
        params = (
            ('cmd', op + ' ' + str(value)),
        )

        # avoid multiple request
        if op == self.last_op and str(params) == self.last_params :
            _LOGGER.debug('retry for op :' +op+' avoided')
            return

        # request the stove
        if self.request_stove(op, params) == False:
            return

        # change state
        self.hass.states.async_set('palazzetti.F2L', self.response_json['F2L'])"""

    def set_status(self, value):
        """start or stop stove
        if value == None or type(value) != str :
            return

        # only ON of OFF value allowed
        if value != 'on' and value != 'off':
            return

        op = 'CMD'

        # params for GET
        params = (
            ('cmd', op + ' ' + str(value)),
        )

        # request the stove
        if self.request_stove(op, params) == False:
            return

        # change state
        self.hass.states.async_set('palazzetti.STATUS', self.code_status.get(self.response_json['STATUS'], self.response_json['STATUS']))"""

    def get_data_states(self):
        return self.data

    def get_data_json(self):
        return self.response_json

    def get_data_config_json(self):
        self.__config_parse()
        return vars(self.data_config_object)

    def get_data_alls_json(self):
        return self.response_json_alls

    def get_data_stdt_json(self):
        return self.response_json_stdt
