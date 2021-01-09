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

    def getHTTP(self, host, message):
        queryStr = "http://" + host + "/cgi-bin/sendmsg.lua"
        # params for GET
        params = (("cmd", message),)
        _response_json = None

        # check if op is defined or stop here
        if message is None:
            return False
        # print(message)

        _LOGGER.debug("Executing command: {message}")

        try:
            response = requests.get(queryStr, params=params, timeout=30)
        except requests.exceptions.ReadTimeout:
            # timeout ( can happend when wifi is used )
            _LOGGER.error('Timeout reach for request : ' + queryStr)
            return False
        except requests.exceptions.ConnectTimeout:
            # equivalent of ping
            _LOGGER.error('Please check parm ip : ' + self.ip)
            return False
        
        if response == False:
            return False
        
        _response_json = json.loads(response.text)
        
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
        self.palsocket=PalComm()
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

        #api_discovery=PalComm()
        #_response = await api_discovery.async_getHTTP(self.ip, message)
        _response = await self.palsocket.async_getHTTP(self.ip, message)

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

    # send request to stove for set commands
    # why not async?
    def request_stove(self, message):
        """ request the stove """
        _response_json = None

        # check if op is defined or stop here
        if message is None:
            return False

        # print(self.op)
        _LOGGER.debug("request stove " + message)
        # response = False

        # save
        self.last_op = message

        retry = 0
        success = False

        _response = False
        _response_json = None
        # error returned by Cbox
        while not success:
            # let's go baby
            #api_discovery=PalComm()
            #_response = await api_discovery.async_getHTTP(self.ip, message)
            _response = self.palsocket.getHTTP(self.ip, message)

            # cbox return error
            if not _response:
                # print("palazzetti.stove - com error")
                self.state = "com error"
                self.data["state"] = self.state
                self.response_json.update({"icon": "mdi:link-off"})
                _LOGGER.error(
                    "Error returned by CBox - retry in 2 seconds (" + message + ")"
                )
                time.sleep(2)
                retry = retry + 1

                if retry == 3:
                    _LOGGER.error(
                        "Error returned by CBox - stop retry after 3 attempt ("
                        + message
                        + ")"
                    )
                    break
            
            success = True

        # merge the result with the exixting responnse_json
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
        self.__config_parse()

        return _response

    # update configuration: call json parse function
    # async def async_config_parse(self):
    #     asset_parser = psap(
    #         get_alls=self.response_json_alls, get_stdt=self.response_json_stdt
    #     )
    #     asset_capabilities = asset_parser.parsed_data
    #     self.data_config_object = asset_capabilities

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
        self.set_setp(datas.get("SETP", None))  # temperature
        #self.set_powr(datas.get("PWR", None))  # fire power
        #self.set_rfan(datas.get("RFAN", None))  # Fan
        #self.set_status(datas.get("STATUS", None))  # status

    def set_setp(self, value):
        """Set target temperature"""
        if value == None or type(value) != int:
            return
            
        if value < self.data_config_object.value_setpoint_min or value > self.data_config_object.value_setpoint_max:
            return

        if value == self.response_json["SETP"]
            return
        
        op = "SET SETP"

        # params for GET

        command = op + " " + str(value)
        
        # avoid multiple request
        if command == self.last_op:
            _LOGGER.debug("retry for op :" + op + " avoided")
            return

        # request the stove
        if self.request_stove(command) == False:
            return

        # change state
        self.data["setp"] = value
        self.response_json.update({"SETP": value})

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

    # retuens list of states: title, state, ip
    def get_data_states(self):
        return self.data
    
    # retuens JSON with all keys of GET ALLS, GET STDT and GET CNTR
    def get_data_json(self):
        return self.response_json
    
    # returns JSON with configuration keys
    def get_data_config_json(self):
        return vars(self.data_config_object)

    # returns JSON with the DATA key content of the last GET ALLS
    def get_data_alls_json(self):
        return self.response_json_alls

    # returns JSON with the DATA key content of the last GET STDT
    def get_data_stdt_json(self):
        return self.response_json_stdt