import logging, asyncio, json, requests, aiohttp

_LOGGER = logging.getLogger(__name__)

# class based on NINA 6kw
# contact me if you have a other model of stove
class Palazzetti(object):

    pinged = False
    op = None
    response_json = None

    last_op = None
    last_params = None

    """docstring for Palazzetti"""
    def __init__(self, config):
    #def __init__(self, hass, config):

        #self.hass       = hass
        self.ip         = config
        #self.ipname     = config.replace(".","")
        self.queryStr   = 'http://'+self.ip+'/cgi-bin/sendmsg.lua'

        _LOGGER.debug('Init of class palazzetti')

        self.code_status = {
            0 : "OFF",
            1 : "OFF TIMER",
            2 : "TESTFIRE",
            3 : "HEATUP",
            4 : "FUELIGN",
            5 : "IGNTEST",
            6 : "BURNING",
            9 : "COOLFLUID",
            10 : "FIRESTOP",
            11 : "CLEANFIRE",
            12 : "COOL",
            241 : "CHIMNEY ALARM",
            243 : "GRATE ERROR",
            244 : "NTC2 ALARM",
            245 : "NTC3 ALARM",
            247 : "DOOR ALARM",
            248 : "PRESS ALARM",
            249 : "NTC1 ALARM",
            250 : "TC1 ALARM",
            252 : "GAS ALARM",
            253 : "NOPELLET ALARM"
        }

        self.code_fan_nina = {
            0 : "off",
            6 : "high",
            7 : "auto"
        }
        self.code_fan_nina_reversed = {
            "off" : 0,
            "high" : 6,
            "auto" : 7
        }


        # States are in the format DOMAIN.OBJECT_ID.
        #hass.states.async_set('palazzetti.ip', self.ip)
    
    # make request generic
    async def async_get_gen(self,myrequest='GET LABL'):
        """Get counters"""
        self.op = myrequest
        await self.async_get_request()


    # make request GET STDT
    async def async_get_stdt(self):
        """Get counters"""
        self.op = 'GET STDT'
        await self.async_get_request()
    
    # make request GET ALLS
    async def async_get_alls(self):
        """Get All data or almost ;)"""
        self.op = 'GET ALLS'
        await self.async_get_request()

    # make request GET CNTR
    async def async_get_cntr(self):
        """Get counters"""
        self.op = 'GET CNTR'
        await self.async_get_request()

    # send a get request for get datas
    async def async_get_request(self):
        """ request the stove """
        # params for GET
        params = (
            ('cmd', self.op),
        )

        # check if op is defined or stop here
        if self.op is None:
            return False

        # let's go baby
        print(self.op)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.queryStr, params=params) as response:                    
                    if response.status != 200 : 
                        _LOGGER.error("Error during api request : http status returned is {}".format(response.status))
                        print('palazzetti.stove - offline')
                        #self.hass.states.async_set('palazzetti.stove', 'offline')
                        response = False
                    else:
                        # save response in json object
                        response_json = json.loads(await response.text())

        except aiohttp.ClientError as client_error:
            _LOGGER.error("Error during api request: {emsg}".format(emsg=client_error))
            print('palazzetti.stove - offline')
            #self.hass.states.async_set('palazzetti.stove', 'offline')
            response = False
        except json.decoder.JSONDecodeError as err:
            _LOGGER.error("Error during json parsing: response unexpected from Cbox")
            print('palazzetti.stove - offline')
            #self.hass.states.async_set('palazzetti.stove', 'offline')
            response = False
        
        if response == False:
            _LOGGER.debug('get_request() response false for op ' + self.op)
            return False

        

        #If no response return
        if response_json['SUCCESS'] != True :
            print('palazzetti.stove - com error')
            #self.hass.states.async_set('palazzetti.stove', 'com error', self.response_json)
            _LOGGER.error('Error returned by CBox')
            return False

        # merge response with existing dict
        if self.response_json != None :
            response_merged = self.response_json.copy()
            response_merged.update(response_json['DATA'])
            self.response_json = response_merged
        else:
            self.response_json = response_json['DATA']

        print('palazzetti.stove - online')
        #self.hass.states.async_set('palazzetti.stove', 'online', self.response_json)
        self.change_states()

    # send request to stove
    def request_stove(self, op, params):
        _LOGGER.debug('request stove ' + op)

        if op is None:
            return False       

        # save
        self.last_op = op
        self.last_params = str(params)

        retry = 0
        success = False
        # error returned by Cbox
        while not success :
            # let's go baby
            try:
                response = requests.get(self.queryStr, params=params, timeout=30)
            except requests.exceptions.ReadTimeout:
                # timeout ( can happend when wifi is used )
                _LOGGER.error('Timeout reach for request : ' + self.queryStr)
                _LOGGER.info('Please check if you can ping : ' + self.ip)
                print('palazzetti.stove - offline')
                #self.hass.states.set('palazzetti.stove', 'offline')
                return False
            except requests.exceptions.ConnectTimeout:
                # equivalent of ping
                _LOGGER.error('Please check parm ip : ' + self.ip)
                print('palazzetti.stove - offline')
                #self.hass.states.set('palazzetti.stove', 'offline')
                return False

            if response == False:
                return False

            # save response in json object
            response_json = json.loads(response.text)
            success = response_json['SUCCESS']

            # cbox return error
            if not success:
                print('palazzetti.stove - com error')
                #self.hass.states.async_set('palazzetti.stove', 'com error', self.response_json)
                _LOGGER.error('Error returned by CBox - retry in 2 seconds (' +op+')')
                time.sleep(2)
                retry = retry + 1

                if retry == 3 :
                     _LOGGER.error('Error returned by CBox - stop retry after 3 attempt (' +op+')')
                     break
            
            

        # merge response with existing dict
        if self.response_json != None :
            response_merged = self.response_json.copy()
            response_merged.update(response_json['DATA'])
            self.response_json = response_merged
        else:
            self.response_json = response_json['DATA']

        print('palazzetti.stove - online')
        #self.hass.states.async_set('palazzetti.stove', 'online', self.response_json)

        return response

    def change_states(self):
        #to be further developed according to GET STDT data

        """Change states following result of request"""
        if self.op == 'GET ALLS':
            #self.hass.states.async_set('palazzetti.STATUS', self.code_status.get(self.response_json['STATUS'], self.response_json['STATUS']))
            #self.hass.states.async_set('palazzetti.F2L', int(self.response_json['F2L']))
            #self.hass.states.async_set('palazzetti.PWR', self.response_json['PWR'])
            #self.hass.states.async_set('palazzetti.SETP', self.response_json['SETP'])
            
            # update for sensor platform 
            # should force sensor platform update somehow but don't know how
            #self.hass.data[DOMAIN] = {
            #  't1': self.response_json['T1'],
            #  't2': self.response_json['T2'],
            #  't5': self.response_json['T5'],
            #  'setp': self.response_json['SETP'],
            #  'plevel': self.response_json['PLEVEL'],
            #  'pellet': self.response_json['PQT']
            #}
            print(f'assign GET ALLS - ' + self.code_status.get(self.response_json['STATUS'], self.response_json['STATUS']))

    def get_sept(self):
        """Get target temperature for climate"""
        if self.response_json == None or self.response_json['SETP'] == None:
            return 0

        return self.response_json['SETP']
    
    def get_key(self,mykey='STATUS'):
        """Get target temperature for climate"""
        if self.response_json == None or (mykey in self.response_json) == False or self.response_json[mykey] == None:
            return

        return self.response_json[mykey]

    def set_parameters(self, datas):
        """set parameters following service call"""
        self.set_sept(datas.get('SETP', None))       # temperature
        self.set_powr(datas.get('PWR', None))        # fire power
        self.set_rfan(datas.get('RFAN', None))       # Fan
        self.set_status(datas.get('STATUS', None))   # status

    def set_sept(self, value):
        """Set target temperature"""

        if value == None or type(value) != int:
            return

        op = 'SET SETP'

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
        print('set palazzetti.SETP to: ' + self.response_json['SETP'])
        #self.hass.states.set('palazzetti.SETP', self.response_json['SETP'])

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

    def get_datas(self):
        return self.response_json

if __name__ == "__main__":
    api = Palazzetti("192.168.1.133")
    loop = asyncio.get_event_loop()
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
