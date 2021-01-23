import json
import logging
import requests
import aiohttp
import socket
import time

from palazzetti_sdk_asset_parser import AssetParser as psap
from .exceptions import *

_LOGGER = logging.getLogger(__name__)

UDP_PORT = 54549
DISCOVERY_TIMEOUT = 5
DISCOVERY_MESSAGE = b"plzbridge?"
BUFFER_SIZE = 2048
HTTP_TIMEOUT = 15

# to be completed!!
class PalComm(object):
    async def async_callUDP(self, host, message):
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # Enable broadcasting mode
        # server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

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
            # maybe connection error between ConnBox and Stove
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
            _LOGGER.error("Timeout reach for request : " + queryStr)
            return False
        except requests.exceptions.ConnectTimeout:
            # equivalent of ping
            _LOGGER.error("Please check parm ip : " + self.ip)
            return False

        if response == False:
            return False

        _response_json = json.loads(response.text)

        # If no response return
        if _response_json["SUCCESS"] != True:
            # maybe connection error between ConnBox and Stove
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

        api_discovery = PalComm()
        use_ip = testIP

        _response = await api_discovery.async_callUDP(use_ip, DISCOVERY_MESSAGE)

        if not _response:
            return False

        return True

    async def checkIP_HTTP(self, testIP):
        """verify the IP is a Connection Box using HTTP call with command GET LABL"""
        api_discovery = PalComm()
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


# this class represent the product, to get all the needed informations
# to handle it data_config_json is the minimum required also
# response_json is needed for more detailed info
class Palazzetti(object):
    """Palazzetti HTTP class"""

    response_json_alls = None
    response_json_stdt = None

    response_json = None

    data = None
    data_config_json = None
    data_config_object = None

    def __init__(self, host, product_id="uniqueID"):
        _LOGGER.debug("Init of class palazzetti")

        self.ip = host
        self.palsocket = PalComm()
        self.state = "online"
        self.unique_id = product_id
        self.data = {}
        self.data["title"] = self.unique_id

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

    # TODO: Rename to get_static_data
    async def async_get_stdt(self):
        """Get counters"""
        await self.__async_get_request("GET STDT")

    # TODO: Rename to get_alls
    async def async_get_alls(self):
        """Get All data or almost ;)"""
        await self.__async_get_request("GET ALLS")

    async def async_UDP_get_alls(self):
        """Get All data or almost ;)"""
        await self.__async_UDP_get_request(b"plzbridge?GET ALLS")

    # TODO: Remove async_ from name
    async def async_get_label(self):
        """Get All data or almost ;)"""
        await self.__async_get_request("GET LABL")

    # TODO: Remove async_ from name
    async def async_get_status(self):
        """Get All data or almost ;)"""
        await self.__async_get_request("GET STAT")

    # TODO: Remove async_ from name
    async def async_get_fan_data(self):
        """Get All data or almost ;)"""
        await self.__async_get_request("GET FAND")

    async def async_get_power(self):
        """Get All data or almost ;)"""
        await self.__async_get_request("GET POWR")

    # TODO: Remove async_ from name
    async def async_get_temperatures(self):
        """Get All data or almost ;)"""
        await self.__async_get_request("GET TMPS")

    # TODO: Rename to get_counters
    async def async_get_cntr(self):
        """Get counters"""
        await self.__async_get_request("GET CNTR")

    async def __async_get_request(self, message):
        """ request the stove """
        _response_json = None

        # check if op is defined or stop here
        if message is None:
            return False

        _LOGGER.debug("Executing command: {message}")
        # response = False

        # api_discovery=PalComm()
        # _response = await api_discovery.async_getHTTP(self.ip, message)
        _response = await self.palsocket.async_getHTTP(self.ip, message)

        if not _response:
            self.state = "offline"
            self.data["state"] = self.state
            if self.response_json != None:
                self.response_json.update({"icon": "mdi:link-off"})
            else:
                self.response_json = json.loads('{"icon": "mdi:link-off"}')
            return False

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

        if message == "GET ALLS":
            self.data["status"] = self.code_status.get(
                self.response_json["STATUS"], self.response_json["STATUS"]
            )
            self.response_json_alls = _response
        elif message == "GET STDT":
            self.response_json_stdt = _response

    # only works with GET ALLS
    async def __async_UDP_get_request(self, message):
        """ request the stove """
        _response_json = None

        # check if op is defined or stop here
        if message is None:
            return False

        # _LOGGER.debug("Executing command: {message}")
        _response = await self.palsocket.async_callUDP(self.ip, message)
        # print(_response)
        # one single retry
        if _response is None:
            # print("retry")
            _response = await self.palsocket.async_callUDP(self.ip, message)

        if not _response:
            # print("enter here")
            self.state = "offline"
            self.data["state"] = self.state
            if self.response_json != None:
                self.response_json.update({"icon": "mdi:link-off"})
            else:
                self.response_json = json.loads('{"icon": "mdi:link-off"}')
            return False

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

        if message == b"plzbridge?GET ALLS":
            # print("Passa di qua: UDP GET_ALLS")
            self.data["status"] = self.code_status.get(
                self.response_json["STATUS"], self.response_json["STATUS"]
            )
            self.response_json_alls = _response

    # send request to stove for set commands
    # why not async?
    def __request_send(self, message):
        """ request the stove """
        _response_json = None

        # check if op is defined or stop here
        if message is None:
            return False

        _LOGGER.debug("request stove " + message)
        # response = False

        retry = 0
        success = False

        _response = False
        _response_json = None
        # error returned by Cbox
        while not success:
            # let's go baby
            # api_discovery=PalComm()
            # _response = await api_discovery.async_getHTTP(self.ip, message)
            _response = self.palsocket.getHTTP(self.ip, message)

            # cbox return error
            if not _response:
                # print("palazzetti.stove - com error")
                self.state = "com error"
                self.data["state"] = self.state

                if self.response_json != None:
                    self.response_json.update({"icon": "mdi:link-off"})
                else:
                    self.response_json = json.loads('{"icon": "mdi:link-off"}')

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

    def __validate_power(self, value):
        _power = None

        try:
            _power = int(f"{value}", 10)
        except:
            _power = None

        if _power == None:
            raise InvalidPowerError

        if self.data_config_object.flag_has_power == False:
            raise NotAvailablePowerError

        if _power < 1 or _power > 5:
            raise InvalidPowerMinMaxError

        return True

    def __validate_fan(self, fan, value):
        _fan = None

        try:
            _fan = int(f"{value}", 10)
        except:
            _fan = None

        if _fan == None:
            raise InvalidFanError

        # self.async_get_alls()

        _fan_limits = {}

        try:
            _fan_limits["min"] = self.data_config_object.value_fan_limits[
                ((fan - 1) * 2)
            ]
            _fan_limits["max"] = self.data_config_object.value_fan_limits[
                (((fan - 1) * 2) + 1)
            ]
        except IndexError as error:
            raise InvalidFanOutOfRange
        except Exception as error:
            _fan_limits["min"] = None
            _fan_limits["max"] = None

        if (_fan_limits.get("min", None) == None) or (
            _fan_limits.get("max", None) == None
        ):
            raise InvalidFanLimitsError

        if _fan < _fan_limits.get("min") or _fan > _fan_limits.get("max"):
            raise InvalidFanMinMaxError

        return True

    def __validate_setpoint(self, value):
        _setpoint = None

        try:
            _setpoint = int(f"{value}", 10)
        except:
            _setpoint = None

        if _setpoint == None:
            raise InvalidSetpointError

        if self.data_config_object.flag_has_setpoint == False:
            raise NotAvailableSetpointError

        if (
            _setpoint < self.data_config_object.value_setpoint_min
            or _setpoint > self.data_config_object.value_setpoint_max
        ):
            raise InvalidSetpointMinMaxError

        return True

    def __build_fan_command(self, fan, value):

        _command = {"FAN_1": "SET RFAN", "FAN_2": "SET FN3L", "FAN_3": "SET FN4L"}

        command = f'{_command.get("FAN_" + "" + str(fan), None)} {value}'

        if command is None:
            raise InvalidFanOutOfRange

        return command

    def __config_parse(self):
        asset_parser = psap(get_alls=self.response_json, get_stdt=self.response_json)
        asset_capabilities = asset_parser.parsed_data
        self.data_config_object = asset_capabilities

    # TODO: Is it possible to remove this function?
    # BYNOW it has been limited to setpoint only
    async def set_parameters(self, datas):
        """set parameters following service call"""
        await self.async_set_setpoint(datas.get("SETP", None))  # temperature
        # self.set_powr(datas.get("PWR", None))  # fire power
        # self.set_rfan(datas.get("RFAN", None))  # Fan
        # self.set_status(datas.get("STATUS", None))  # status

    async def async_set_label(self, value):
        """Set target temperature"""
        if value == None or value == "":
            raise InvalidLabelValueError

        command = f"SET LABL {str(value)}"

        if await self.__async_get_request(command) == False:
            raise SendCommandError

        # change state
        self.data["label"] = value
        self.response_json.update({"LABEL": value})

    async def async_set_power(self, value):

        self.__validate_power(value)

        command = f"SET POWR {str(value)}"

        if await self.__async_get_request(command) == False:
            raise SendCommandError

        # change state
        self.data["powr"] = value
        self.response_json.update({"POWR": value})

    async def async_set_fan_silent_mode(self):

        command = self.__build_fan_command(1, 0)

        if self.data_config_object.flag_has_fan_zero_speed_fan == True:
            command = "SET SLNT 1"

        if await self.__async_get_request(command) == False:
            raise SendCommandError

    async def async_set_fan_auto_mode(self, fan=1):

        value = "7"  # Auto Mode
        command = self.__build_fan_command(fan, value)

        if await self.__async_get_request(command) == False:
            raise SendCommandError

    async def async_set_fan_high_mode(self, fan=1):

        value = "6"  # High Mode
        command = self.__build_fan_command(fan, value)

        if await self.__async_get_request(command) == False:
            raise SendCommandError

    async def async_set_fan(self, fan, value):

        self.__validate_fan(fan, value)

        command = self.__build_fan_command(fan, value)

        if await self.__async_get_request(command) == False:
            raise SendCommandError

    async def async_set_light(self, value):
        if (value == None) or (type(value) is not bool):
            raise InvalidLightError

        command = f"SET LGHT {str(1 if value == True else 0)}"

        if await self.__async_get_request(command) == False:
            raise SendCommandError

    async def async_set_door(self, value):
        if (value == None) or (type(value) is not bool):
            raise InvalidDoorError

        if await self.__async_get_request("GET STAT") == False:
            raise SendCommandError

        if self.data_config_object.flag_error_status == True:
            raise InvalidStateError

        command = f"SET DOOR {str(1 if value == True else 2)}"

        if await self.__async_get_request(command) == False:
            raise SendCommandError

    async def async_set_setpoint(self, value):
        """Set target temperature"""

        self.__validate_setpoint(value)

        command = f"SET SETP {str(value)}"

        # if value == self.response_json["SETP"]:
        #     return

        if await self.__async_get_request(command) == False:
            raise SendCommandError

        # change state
        self.data["setp"] = value
        self.response_json.update({"SETP": value})

    def power_on(self):

        if self.__request_send("GET STAT") == False:
            raise SendCommandError

        if self.data_config_object.flag_error_status == True:
            raise InvalidStateError

        if self.data_config_object.flag_has_switch_on_off != True:
            raise InvalidStateTransitionError

        if self.data_config_object.value_product_is_on == False:
            raise InvalidStateTransitionError

        command = "CMD ON"

        if self.__request_send(command) == False:
            raise SendCommandError

    def power_off(self):

        if self.__request_send("GET STAT") == False:
            raise SendCommandError

        if self.data_config_object.flag_error_status == True:
            raise InvalidStateError

        if self.data_config_object.flag_has_switch_on_off != True:
            raise InvalidStateTransitionError

        if self.data_config_object.value_product_is_on == False:
            raise InvalidStateTransitionError

        command = "CMD OFF"

        if self.__request_send(command) == False:
            raise SendCommandError

    # retuens list of states: title, state, ip
    def get_data_states(self) -> list:
        return self.data

    # retuens JSON with all keys of GET ALLS, GET STDT and GET CNTR
    def get_data_json(self) -> json:
        return self.response_json

    # returns JSON with configuration keys
    def get_data_config_json(self) -> json:
        return vars(self.data_config_object)

    # returns OBJECT with configuration keys
    def get_data_config_object(self):
        return self.data_config_object

    # returns JSON with the DATA key content of the last GET ALLS
    def get_data_alls_json(self) -> json:
        return self.response_json_alls

    # returns JSON with the DATA key content of the last GET STDT
    def get_data_stdt_json(self) -> json:
        return self.response_json_stdt

    # returns int with setpoint
    def get_setpoint(self) -> int:
        """Get target temperature for climate"""
        if self.response_json == None or self.response_json["SETP"] == None:
            return

        return int(self.response_json["SETP"])

    # get generic KEY in the datas
    # if key doesn't exist returns None
    # TODO: Is it possible to remove this function?
    # BYNOW does not generate risks
    def get_key(self, mykey="STATUS"):
        """Get target temperature for climate"""
        if (
            self.response_json == None
            or (mykey in self.response_json) == False
            or self.response_json[mykey] == None
        ):
            return

        return self.response_json[mykey]

    @property
    def product_id(self) -> str:
        """Return unique ID of product"""
        return self.unique_id

    @property
    def online(self) -> bool:
        """Return True if product is online"""
        return self.state == "online"