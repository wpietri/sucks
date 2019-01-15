import hashlib
import logging
import time
from base64 import b64decode, b64encode
from collections import OrderedDict
from threading import Event

import requests
import stringcase
from sleekxmpp import ClientXMPP, Callback, MatchXPath
from sleekxmpp.xmlstream import ET
from sleekxmpp.exceptions import XMPPError

_LOGGER = logging.getLogger(__name__)

# These consts define all of the vocabulary used by this library when presenting various states and components.
# Applications implementing this library should import these rather than hard-code the strings, for future-proofing.

CLEAN_MODE_AUTO = 'auto'
CLEAN_MODE_EDGE = 'edge'
CLEAN_MODE_SPOT = 'spot'
CLEAN_MODE_SPOT_AREA = 'spotarea'
CLEAN_MODE_SINGLE_ROOM = 'single_room'
CLEAN_MODE_STOP = 'stop'

CLEAN_ACTION_START = 'start'
CLEAN_ACTION_PAUSE = 'pause'
CLEAN_ACTION_RESUME = 'resume'

FAN_SPEED_NORMAL = 'normal'
FAN_SPEED_HIGH = 'high'

CHARGE_MODE_RETURN = 'return'
CHARGE_MODE_RETURNING = 'returning'
CHARGE_MODE_CHARGING = 'charging'
CHARGE_MODE_IDLE = 'idle'

COMPONENT_SIDE_BRUSH = 'side_brush'
COMPONENT_MAIN_BRUSH = 'main_brush'
COMPONENT_FILTER = 'filter'

VACUUM_STATUS_OFFLINE = 'offline'

CLEANING_STATES = {CLEAN_MODE_AUTO, CLEAN_MODE_EDGE, CLEAN_MODE_SPOT, CLEAN_MODE_SPOT_AREA, CLEAN_MODE_SINGLE_ROOM}
CHARGING_STATES = {CHARGE_MODE_CHARGING}

# These dictionaries convert to and from Sucks's consts (which closely match what the UI and manuals use)
# to and from what the Ecovacs API uses (which are sometimes very oddly named and have random capitalization.)
CLEAN_MODE_TO_ECOVACS = {
    CLEAN_MODE_AUTO: 'auto',
    CLEAN_MODE_EDGE: 'border',
    CLEAN_MODE_SPOT: 'spot',
    CLEAN_MODE_SPOT_AREA: 'SpotArea',
    CLEAN_MODE_SINGLE_ROOM: 'singleroom',
    CLEAN_MODE_STOP: 'stop'
}

CLEAN_ACTION_TO_ECOVACS = {
    CLEAN_ACTION_START: 's',
    CLEAN_ACTION_PAUSE: 'p',
    CLEAN_ACTION_RESUME: 'r',
}

CLEAN_MODE_FROM_ECOVACS = {
    'auto': CLEAN_MODE_AUTO,
    'border': CLEAN_MODE_EDGE,
    'spot': CLEAN_MODE_SPOT,
    'SpotArea': CLEAN_MODE_SPOT_AREA,
    'singleroom': CLEAN_MODE_SINGLE_ROOM,
    'stop': CLEAN_MODE_STOP,
    'going': CHARGE_MODE_RETURNING
}

FAN_SPEED_TO_ECOVACS = {
    FAN_SPEED_NORMAL: 'standard',
    FAN_SPEED_HIGH: 'strong'
}

FAN_SPEED_FROM_ECOVACS = {
    'standard': FAN_SPEED_NORMAL,
    'strong': FAN_SPEED_HIGH
}

CHARGE_MODE_TO_ECOVACS = {
    CHARGE_MODE_RETURN: 'go',
    CHARGE_MODE_RETURNING: 'Going',
    CHARGE_MODE_CHARGING: 'SlotCharging',
    CHARGE_MODE_IDLE: 'Idle'
}

CHARGE_MODE_FROM_ECOVACS = {
    'going': CHARGE_MODE_RETURNING,
    'slot_charging': CHARGE_MODE_CHARGING,
    'idle': CHARGE_MODE_IDLE
}

COMPONENT_TO_ECOVACS = {
    COMPONENT_MAIN_BRUSH: 'Brush',
    COMPONENT_SIDE_BRUSH: 'SideBrush',
    COMPONENT_FILTER: 'DustCaseHeap'
}

COMPONENT_FROM_ECOVACS = {
    'brush': COMPONENT_MAIN_BRUSH,
    'side_brush': COMPONENT_SIDE_BRUSH,
    'dust_case_heap': COMPONENT_FILTER
}

class EcoVacsAPI:
    CLIENT_KEY = "eJUWrzRv34qFSaYk"
    SECRET = "Cyu5jcR4zyK6QEPn1hdIGXB5QIDAQABMA0GC"
    PUBLIC_KEY = 'MIIB/TCCAWYCCQDJ7TMYJFzqYDANBgkqhkiG9w0BAQUFADBCMQswCQYDVQQGEwJjbjEVMBMGA1UEBwwMRGVmYXVsdCBDaXR5MRwwGgYDVQQKDBNEZWZhdWx0IENvbXBhbnkgTHRkMCAXDTE3MDUwOTA1MTkxMFoYDzIxMTcwNDE1MDUxOTEwWjBCMQswCQYDVQQGEwJjbjEVMBMGA1UEBwwMRGVmYXVsdCBDaXR5MRwwGgYDVQQKDBNEZWZhdWx0IENvbXBhbnkgTHRkMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDb8V0OYUGP3Fs63E1gJzJh+7iqeymjFUKJUqSD60nhWReZ+Fg3tZvKKqgNcgl7EGXp1yNifJKUNC/SedFG1IJRh5hBeDMGq0m0RQYDpf9l0umqYURpJ5fmfvH/gjfHe3Eg/NTLm7QEa0a0Il2t3Cyu5jcR4zyK6QEPn1hdIGXB5QIDAQABMA0GCSqGSIb3DQEBBQUAA4GBANhIMT0+IyJa9SU8AEyaWZZmT2KEYrjakuadOvlkn3vFdhpvNpnnXiL+cyWy2oU1Q9MAdCTiOPfXmAQt8zIvP2JC8j6yRTcxJCvBwORDyv/uBtXFxBPEC6MDfzU2gKAaHeeJUWrzRv34qFSaYkYta8canK+PSInylQTjJK9VqmjQ'
    MAIN_URL_FORMAT = 'https://eco-{country}-api.ecovacs.com/v1/private/{country}/{lang}/{deviceId}/{appCode}/{appVersion}/{channel}/{deviceType}'
    USER_URL_FORMAT = 'https://users-{continent}.ecouser.net:8000/user.do'
    PORTAL_URL_FORMAT = 'https://portal-{continent}.ecouser.net/api'

    USERSAPI = 'users/user.do'
    IOTDEVMANAGERAPI = 'iot/devmanager.do' # IOT Device Manager - This provides control of "IOT" products via API, no longer XMPP
    PRODUCTAPI = 'pim/product' # Leaving this open, the only endpoint known currently is "Product IOT Map" -  pim/product/getProductIotMap - This provides a list of "IOT" products, which is assumed should use IOT API instead of XMPP
        
      
    REALM = 'ecouser.net'

    def __init__(self, device_id, account_id, password_hash, country, continent):
        self.meta = {
            'country': country,
            'lang': 'en',
            'deviceId': device_id,
            'appCode': 'i_eco_e',
            #'appCode': 'i_eco_a' - iphone
            'appVersion': '1.3.5',
            #'appVersion': '1.4.6' - iphone
            'channel': 'c_googleplay',
            #'channel': 'c_iphone', - iphone
            'deviceType': '1'
            #'deviceType': '2' - iphone
        }
        _LOGGER.debug("Setting up EcoVacsAPI")
        self.resource = device_id[0:8]
        self.country = country
        self.continent = continent
        login_info = self.__call_main_api('user/login',
                                          ('account', self.encrypt(account_id)),
                                          ('password', self.encrypt(password_hash)))
        self.uid = login_info['uid']
        self.login_access_token = login_info['accessToken']
        self.auth_code = self.__call_main_api('user/getAuthCode',
                                              ('uid', self.uid),
                                              ('accessToken', self.login_access_token))['authCode']
        login_response = self.__call_login_by_it_token()
        self.user_access_token = login_response['token']
        if login_response['userId'] != self.uid:
            logging.debug("Switching to shorter UID " + login_response['userId'])
            self.uid = login_response['userId']
        logging.debug("EcoVacsAPI connection complete")

    def __sign(self, params):
        result = params.copy()
        result['authTimespan'] = int(time.time() * 1000)
        result['authTimeZone'] = 'GMT-8'

        sign_on = self.meta.copy()
        sign_on.update(result)
        sign_on_text = EcoVacsAPI.CLIENT_KEY + ''.join(
            [k + '=' + str(sign_on[k]) for k in sorted(sign_on.keys())]) + EcoVacsAPI.SECRET

        result['authAppkey'] = EcoVacsAPI.CLIENT_KEY
        result['authSign'] = self.md5(sign_on_text)
        return result

    def __call_main_api(self, function, *args):
        _LOGGER.debug("calling main api {} with {}".format(function, args))
        params = OrderedDict(args)
        params['requestId'] = self.md5(time.time())
        url = (EcoVacsAPI.MAIN_URL_FORMAT + "/" + function).format(**self.meta)
        api_response = requests.get(url, self.__sign(params))
        json = api_response.json()
        _LOGGER.debug("got {}".format(json))
        if json['code'] == '0000':
            return json['data']
        elif json['code'] == '1005':
            _LOGGER.warning("incorrect email or password")
            raise ValueError("incorrect email or password")
        else:
            _LOGGER.error("call to {} failed with {}".format(function, json))
            raise RuntimeError("failure code {} ({}) for call {} and parameters {}".format(
                json['code'], json['msg'], function, args))

    def __call_user_api(self, function, args):
        _LOGGER.debug("calling user api {} with {}".format(function, args))
        params = {'todo': function}
        params.update(args)
        response = requests.post(EcoVacsAPI.USER_URL_FORMAT.format(continent=self.continent), json=params)
        json = response.json()
        _LOGGER.debug("got {}".format(json))
        if json['result'] == 'ok':
            return json
        else:
            _LOGGER.error("call to {} failed with {}".format(function, json))
            raise RuntimeError(
                "failure {} ({}) for call {} and parameters {}".format(json['error'], json['errno'], function, params))

    def __call_portal_api(self, api, function, args):
        _LOGGER.debug("calling portal api {} function {} with {}".format(api, function, args))
        if api == self.USERSAPI:
            params = {'todo': function}
            params.update(args)
        else:
            params = {}
            params.update(args)


        url = (EcoVacsAPI.PORTAL_URL_FORMAT + "/" + api).format(continent=self.continent, **self.meta)
        response = None
        if not api == self.IOTDEVMANAGERAPI:
            response = requests.post(url, json=params)
        else:
            try: #IOT Device sometimes doesnt provide a response depending on command, reduce timeout to 1.25 to accomodate and make requests faster
                response = requests.post(url, json=params, timeout=1.25) #May think about having timeout as an arg that could be provided in the future
            except requests.exceptions.ReadTimeout:
                _LOGGER.debug("call to {} failed with ReadTimeout".format(function))
                return {}                

        json = response.json()
        _LOGGER.debug("got {}".format(json))
        if api == self.USERSAPI:    
            if json['result'] == 'ok':
                return json
        
        if api == self.IOTDEVMANAGERAPI:    
            if json['ret'] == 'ok':
                return json
            elif json['ret'] == 'fail':
                if 'debug' in json:
                    if json['debug'] == 'wait for response timed out': 
                        #TODO - Maybe handle timeout for IOT better in the future
                        _LOGGER.error("call to {} failed with {}".format(function, json))
                        return {}
                else:
                    #TODO - Not sure if we want to raise an error yet, just return empty for now
                    _LOGGER.error("call to {} failed with {}".format(function, json))
                    return {}
                    #raise RuntimeError(
                    #"failure {} ({}) for call {} and parameters {}".format(json['error'], json['errno'], function, params))

        if api.startswith(self.PRODUCTAPI):
            if json['code'] == 0:
                return json      

        else:
            _LOGGER.error("call to {} failed with {}".format(function, json))
            raise RuntimeError(
                "failure {} ({}) for call {} and parameters {}".format(json['error'], json['errno'], function, params))

    def __call_login_by_it_token(self):
        return self.__call_portal_api(self.USERSAPI,'loginByItToken',
                                    {'country': self.meta['country'].upper(),
                                     'resource': self.resource,
                                     'realm': EcoVacsAPI.REALM,
                                     'userId': self.uid,
                                     'token': self.auth_code}
                                    )

  

    def getdevices(self):
        return  self.__call_portal_api(self.USERSAPI,'GetDeviceList', {
            'userid': self.uid,
            'auth': {
                'with': 'users',
                'userid': self.uid,
                'realm': EcoVacsAPI.REALM,
                'token': self.user_access_token,
                'resource': self.resource
            }
        })['devices']

    def getiotProducts(self):
        return self.__call_portal_api(self.PRODUCTAPI + '/getProductIotMap','', {
            'channel': '',
            'auth': {
                'with': 'users',
                'userid': self.uid,
                'realm': EcoVacsAPI.REALM,
                'token': self.user_access_token,
                'resource': self.resource
            }
        })['data']

    def SetIOTDevices(self, devices, iotproducts):
        for device in devices: #Check if the device is part of iotProducts
            for iotProduct in iotproducts:
                if not device['class'] == iotProduct['classid']:
                    device['iot'] = False
                else:
                    device['iot'] = True #If it is add an iot flag. 
                    
        return devices
       
    def devices(self):
        return self.SetIOTDevices(self.getdevices(), self.getiotProducts())

    @staticmethod
    def md5(text):
        return hashlib.md5(bytes(str(text), 'utf8')).hexdigest()

    @staticmethod
    def encrypt(text):
        from Crypto.PublicKey import RSA
        from Crypto.Cipher import PKCS1_v1_5
        key = RSA.import_key(b64decode(EcoVacsAPI.PUBLIC_KEY))
        cipher = PKCS1_v1_5.new(key)
        result = cipher.encrypt(bytes(text, 'utf8'))
        return str(b64encode(result), 'utf8')


class EventEmitter(object):
    """A very simple event emitting system."""
    def __init__(self):
        self._subscribers = []

    def subscribe(self, callback):
        listener = EventListener(self, callback)
        self._subscribers.append(listener)
        return listener

    def unsubscribe(self, listener):
        self._subscribers.remove(listener)

    def notify(self, event):
        for subscriber in self._subscribers:
            subscriber.callback(event)


class EventListener(object):
    """Object that allows event consumers to easily unsubscribe from events."""
    def __init__(self, emitter, callback):
        self._emitter = emitter
        self.callback = callback

    def unsubscribe(self):
        self._emitter.unsubscribe(self)


class VacBot():
    def __init__(self, user, domain, resource, secret, vacuum, continent, server_address=None, monitor=False):

        self.vacuum = vacuum

        # If True, the VacBot object will handle keeping track of all statuses,
        # including the initial request for statuses, and new requests after the
        # VacBot returns from being offline. It will also cause it to regularly
        # request component lifespans
        self._monitor = monitor

        self._failed_pings = 0

        # These three are representations of the vacuum state as reported by the API
        self.clean_status = None
        self.charge_status = None
        self.battery_status = None

        # This is an aggregate state managed by the sucks library, combining the clean and charge events to a single state
        self.vacuum_status = None
        self.fan_speed = None

        # Populated by component Lifespan reports
        self.components = {}

        self.statusEvents = EventEmitter()
        self.batteryEvents = EventEmitter()
        self.lifespanEvents = EventEmitter()
        self.errorEvents = EventEmitter()

        if vacuum['iot']:
            self.iot = EcoVacsIOT(user, domain, resource, secret, continent, vacuum)            
            self.iot.subscribe_to_ctls(self._handle_ctl)
        
        self.xmpp = EcoVacsXMPP(user, domain, resource, secret, continent, vacuum, server_address )
        self.xmpp.subscribe_to_ctls(self._handle_ctl)


    def connect_and_wait_until_ready(self):
        self.xmpp.connect_and_wait_until_ready()
        self.xmpp.schedule('Ping', 30, lambda: self.send_ping(), repeat=True)
        
        #ToDo identify the best way to handle similar for IOT devices
            #self.iot.connect_and_wait_until_ready()
            #self.iot.schedule('Ping', 30, lambda: self.send_ping(), repeat=True)

        if self._monitor:
            # Do a first ping, which will also fetch initial statuses if the ping succeeds
            self.send_ping()
            self.xmpp.schedule('Components', 3600, lambda: self.refresh_components(), repeat=True)

    def _handle_ctl(self, ctl):
        method = '_handle_' + ctl['event']
        if hasattr(self, method):
            getattr(self, method)(ctl)

    def _handle_error(self, event):
        error = event['error']
        self.errorEvents.notify(error)
        _LOGGER.debug("*** error = " + error)

    def _handle_life_span(self, event):
        type = event['type']
        try:
            type = COMPONENT_FROM_ECOVACS[type]
        except KeyError:
            _LOGGER.warning("Unknown component type: '" + type + "'")

        if 'val' in event:
            lifespan = int(event['val']) / 100
        else:
            lifespan = int(event['left']) / 60  #This works for a D901
        self.components[type] = lifespan
        
        lifespan_event = {'type': type, 'lifespan': lifespan}
        self.lifespanEvents.notify(lifespan_event)
        _LOGGER.debug("*** life_span " + type + " = " + str(lifespan))

    def _handle_clean_report(self, event):
        type = event['type']
        try:
            type = CLEAN_MODE_FROM_ECOVACS[type]
        except KeyError:
            _LOGGER.warning("Unknown cleaning status '" + type + "'")
        self.clean_status = type
        self.vacuum_status = type

        if self.vacuum['iot']: #Was able to parse additional status from the IOT, may apply to XMPP too
            cleaning = event.get('st', None)
            if cleaning == 'p':
                self.clean_status = 'paused'
            elif cleaning == 'h':
                self.clean_status = 'standby'
            else:
                self.clean_status = 'cleaning'
        
        fan = event.get('speed', None)
        if fan is not None:
            try:
                fan = FAN_SPEED_FROM_ECOVACS[fan]
            except KeyError:
                _LOGGER.warning("Unknown fan speed: '" + fan + "'")
        self.fan_speed = fan
        self.statusEvents.notify(self.vacuum_status)
        if self.fan_speed:
            _LOGGER.debug("*** clean_status = " + self.clean_status + " fan_speed = " + self.fan_speed)
        else:
            _LOGGER.debug("*** clean_status = " + self.clean_status + " fan_speed = None")

    def _handle_battery_info(self, iq):
        try:
            self.battery_status = float(iq['power']) / 100
        except ValueError:
            _LOGGER.warning("couldn't parse battery status " + ET.tostring(iq))
        else:
            self.batteryEvents.notify(self.battery_status)
            _LOGGER.debug("*** battery_status = {:.0%}".format(self.battery_status))

    def _handle_charge_state(self, event):
        if 'type' in event:
            status = event['type']
        elif 'errno' in event: #Handle error
            if event['ret'] == 'fail' and event['errno'] == '8': #Already charging
                status = 'slot_charging'
            else: 
                _LOGGER.error("Unknown charging status '" + event['errno'] + "'") #Log this so we can identify more errors    
        
        try:
            status = CHARGE_MODE_FROM_ECOVACS[status]
        except KeyError:
            _LOGGER.warning("Unknown charging status '" + status + "'")

        self.charge_status = status
        if status != 'idle' or self.vacuum_status == 'charging':
            # We have to ignore the idle messages, because all it means is that it's not
            # currently charging, in which case the clean_status is a better indicator
            # of what the vacuum is currently up to.
            self.vacuum_status = status
            self.statusEvents.notify(self.vacuum_status)
        _LOGGER.debug("*** charge_status = " + self.charge_status)

    def _vacuum_address(self):
        if self.vacuum['iot']:
            return self.vacuum['did']
        else:
            return self.vacuum['did'] + '@' + self.vacuum['class'] + '.ecorobot.net/atom'

    @property
    def is_charging(self) -> bool:
        return self.vacuum_status in CHARGING_STATES

    @property
    def is_cleaning(self) -> bool:
        return self.vacuum_status in CLEANING_STATES

    def send_ping(self):
        try:
            if not self.vacuum['iot']:
                self.xmpp.send_ping(self._vacuum_address())
            else:
                self.xmpp.send_ping(EcoVacsAPI.REALM) #IOT vacuums are using the realm instead
        except XMPPError as err:
            _LOGGER.warning("Ping did not reach VacBot. Will retry.")
            _LOGGER.debug("*** Error type: " + err.etype)
            _LOGGER.debug("*** Error condition: " + err.condition)
            self._failed_pings += 1
            if self._failed_pings >= 4:
                self.vacuum_status = 'offline'
                self.statusEvents.notify(self.vacuum_status)
        else:
            self._failed_pings = 0
            if self._monitor:
                # If we don't yet have a vacuum status, request initial statuses again now that the ping succeeded
                if self.vacuum_status == 'offline' or self.vacuum_status is None:
                    self.request_all_statuses()
            else:
                # If we're not auto-monitoring the status, then just reset the status to None, which indicates unknown
                if self.vacuum_status == 'offline':
                    self.vacuum_status = None
                    self.statusEvents.notify(self.vacuum_status)

            if self.vacuum['iot']: #If an IOT device request statuses, to update events
                self.refresh_statuses()

    def refresh_components(self):
        try:
            self.run(GetLifeSpan('main_brush'))
            self.run(GetLifeSpan('side_brush'))
            self.run(GetLifeSpan('filter'))
        except XMPPError as err:
            _LOGGER.warning("Component refresh requests failed to reach VacBot. Will try again later.")
            _LOGGER.debug("*** Error type: " + err.etype)
            _LOGGER.debug("*** Error condition: " + err.condition)

    def refresh_statuses(self):
        try:
            self.run(GetCleanState())
            self.run(GetChargeState())
            self.run(GetBatteryState())
        except XMPPError as err:
            _LOGGER.warning("Initial status requests failed to reach VacBot. Will try again on next ping.")
            _LOGGER.debug("*** Error type: " + err.etype)
            _LOGGER.debug("*** Error condition: " + err.condition)

    def request_all_statuses(self):
        self.refresh_statuses()
        self.refresh_components()

    def send_command(self, action):
        if not self.vacuum['iot']:
            self.xmpp.send_command(action.to_xml(), self._vacuum_address()) 
        else:
            self.iot.send_command(action, self._vacuum_address())  #IOT devices need the full action for additional parsing
            
    def run(self, action):
        self.send_command(action) 

    def disconnect(self, wait=False):
        self.xmpp.disconnect(wait=wait)

#This is used by EcoVacsIOT and EcoVacsXMPP for _ctl_to_dict
def RepresentsInt(stringvar):
    try: 
        int(stringvar)
        return True
    except ValueError:
        return False

class EcoVacsIOT():
    def __init__(self, user, domain, resource, secret, continent, vacuum):
        self.uid = user
        self.domain = domain
        self.resource = resource
        self.secret = secret
        self.continent = continent
        self.vacuum = vacuum
        self.api = EcoVacsAPI
        self.api.continent = continent
        self.api.meta = {}
        #self.add_event_handler("session_start", self.session_start)
        self.ctl_subscribers = []
        self.ready_flag = Event()
                   
    #TODO: Determine what to do with IOT connect and wait, or scrap
    # def connect_and_wait_until_ready(self):
    #     self.connect(EcoVacsAPI._EcoVacsAPI__call_portal_api())
    #     self.process()
    #     self.wait_until_ready()

    def send_command(self, action, recipient):
        c = self._wrap_command(action, recipient)
        _LOGGER.debug('Sending command {0}'.format(c))
        self._handle_ctl(action, self.api._EcoVacsAPI__call_portal_api(self.api, self.api.IOTDEVMANAGERAPI,'',c  ))
        

    def _wrap_command(self, cmd, recipient):
        return {
            'auth': {
                'realm': EcoVacsAPI.REALM,
                'resource': self.resource,
                'token': self.secret,
                'userid': self.uid,
                'with': 'users',
            },
            "cmdName": cmd.name,
            "payload": cmd.args_to_xml(),            
            "payloadType": "x",
            "td": "q",
            "toId": recipient,
            "toRes": self.vacuum['resource'],
            "toType": self.vacuum['class']
        }     


    def subscribe_to_ctls(self, function):
        self.ctl_subscribers.append(function)

   
    def _handle_ctl(self, action, message):
        if not message == {}:
            resp = self._ctl_to_dict(action, message['resp'])
            if resp is not None:
                for s in self.ctl_subscribers:
                    s(resp)
                

    def _ctl_to_dict(self, action, xmlstring):
        xml = ET.fromstring(xmlstring)
    
        xmlchild = xml.getchildren()
        if len(xmlchild) > 0:
            result = xmlchild[0].attrib.copy()
            #Fix for difference in XMPP vs IOT response
            #Depending on the report will use the tag and add "report" to fit the mold of sucks library
            if xmlchild[0].tag == "clean":
                result['event'] = "CleanReport"
            elif xmlchild[0].tag == "charge":
                result['event'] = "ChargeState"
            elif xmlchild[0].tag == "battery":
                result['event'] = "BatteryInfo"
            else: #Default back to replacing Get from the api cmdName
                result['event'] = action.name.replace("Get","",1) 
    
        else:
            result = xml.attrib.copy()
            result['event'] = action.name.replace("Get","",1)
            if 'ret' in result: #Handle errors as needed
                if result['ret'] == 'fail':
                    if action.name == "Charge": #So far only seen this with Charge, when already docked
                        result['event'] = "ChargeState"
   
        for key in result:
            if not RepresentsInt(result[key]): #Fix to handle negative int values
                result[key] = stringcase.snakecase(result[key])

        return result


class EcoVacsXMPP(ClientXMPP):
    def __init__(self, user, domain, resource, secret, continent, vacuum, server_address=None ):
        ClientXMPP.__init__(self, user + '@' + domain, '0/' + resource + '/' + secret)

        self.user = user
        self.domain = domain
        self.resource = resource
        self.continent = continent
        self.vacuum = vacuum
        self.credentials['authzid'] = user
        if server_address is None:
            self.server_address = ('msg-{}.ecouser.net'.format(self.continent), '5223')
        else:
            self.server_address = server_address
        self.add_event_handler("session_start", self.session_start)
        self.ctl_subscribers = []
        self.ready_flag = Event()

    def wait_until_ready(self):
        self.ready_flag.wait()

    def session_start(self, event):
        _LOGGER.debug("----------------- starting session ----------------")
        _LOGGER.debug("event = {}".format(event))
        self.register_handler(Callback("general",
                                       MatchXPath('{jabber:client}iq/{com:ctl}query/{com:ctl}'),
                                       self._handle_ctl))
        self.ready_flag.set()

    def subscribe_to_ctls(self, function):
        self.ctl_subscribers.append(function)

    def _handle_ctl(self, message):
        the_good_part = message.get_payload()[0][0]
        as_dict = self._ctl_to_dict(the_good_part)
        if as_dict is not None:
            for s in self.ctl_subscribers:
                s(as_dict)

    def _ctl_to_dict(self, xml):
        result = xml.attrib.copy()
        if 'td' not in result:
            # This happens for commands with no response data, such as PlaySound
            return

        result['event'] = result.pop('td')
        if xml:
            result.update(xml[0].attrib)

        for key in result:
            if not RepresentsInt(result[key]): #Fix to handle negative int values
                result[key] = stringcase.snakecase(result[key])
            
        return result

    def register_callback(self, kind, function):
        self.register_handler(Callback(kind,
                                       MatchXPath('{jabber:client}iq/{com:ctl}query/{com:ctl}ctl[@td="' + kind + '"]'),
                                       function))

    def send_command(self, xml, recipient):
        c = self._wrap_command(xml, recipient)
        _LOGGER.debug('Sending command {0}'.format(c))
        c.send()

    def _wrap_command(self, ctl, recipient):
        q = self.make_iq_query(xmlns=u'com:ctl', ito=recipient, ifrom=self._my_address())
        q['type'] = 'set'
        for child in q.xml:
            if child.tag.endswith('query'):
                child.append(ctl)
                return q

    def _my_address(self):
        if not self.vacuum['iot']:
            return self.user + '@' + self.domain + '/' + self.boundjid.resource
        else:
            return self.user + '@' + self.domain + '/' + self.resource


    def send_ping(self, to):
        q = self.make_iq_get(ito=to, ifrom=self._my_address())
        q.xml.append(ET.Element('ping', {'xmlns': 'urn:xmpp:ping'}))
        _LOGGER.debug("*** sending ping ***")
        q.send()

    def connect_and_wait_until_ready(self):
        self.connect(self.server_address)
        self.process()
        self.wait_until_ready()

class VacBotCommand:
    ACTION = {
        'forward': 'forward',
        'backward': 'backward',
        'left': 'SpinLeft',
        'right': 'SpinRight',
        'turn_around': 'TurnAround',
        'stop': 'stop'
    }

    def __init__(self, name, args=None, **kwargs):
        if args is None:
            args = {}
        self.name = name
        self.args = args

    def to_xml(self):
        ctl = ET.Element('ctl', {'td': self.name})
        for key, value in self.args.items():
            if type(value) is dict:
                inner = ET.Element(key, value)
                ctl.append(inner)
            else:
                ctl.set(key, value)
        return ctl

    def args_to_xml(self):
        ctl = ET.Element('ctl',{})
        for key, value in self.args.items():
            if type(value) is dict:
                inner = ET.Element(key, value)
                ctl.append(inner)
            else:
               ctl.set(key, value)
        return ET.tostring(ctl).decode()


    def __str__(self, *args, **kwargs):
        return self.command_name() + " command"

    def command_name(self):
        return self.__class__.__name__.lower()


class Clean(VacBotCommand):
    def __init__(self, mode='auto', speed='normal', terminal=False, **kwargs):
        if kwargs is None:
            super().__init__('Clean', {'clean': {'type': CLEAN_MODE_TO_ECOVACS[mode], 'speed': FAN_SPEED_TO_ECOVACS[speed]}})
        else:
            initcmd = {'type': CLEAN_MODE_TO_ECOVACS[mode], 'speed': FAN_SPEED_TO_ECOVACS[speed]}
            for kkey, kvalue in kwargs.items():
                initcmd[kkey] = kvalue
            super().__init__('Clean', {'clean': initcmd})

class Edge(Clean):
    def __init__(self):
        super().__init__('edge', 'high')


class Spot(Clean):
    def __init__(self):
        super().__init__('spot', 'high')


class Stop(Clean):
    def __init__(self):
        super().__init__('stop', 'normal')

class SpotArea(Clean):
    def __init__(self, action='start', namedarea='', customarea='', cleanings='1'):
        if namedarea != '': #For cleaning specified map area
            super().__init__('spotarea', 'normal', act=CLEAN_ACTION_TO_ECOVACS[action], mid=namedarea)
        elif customarea != '': #For cleaning custom map area, and specify deep amount 1x/2x
            super().__init__('spotarea' ,'normal',act=CLEAN_ACTION_TO_ECOVACS[action], p=customarea, deep=cleanings)
        else:
            #no valid entries
            raise ValueError("must provide namedarea or customarea for spotarea clean")

class Charge(VacBotCommand):
    def __init__(self):
        super().__init__('Charge', {'charge': {'type': CHARGE_MODE_TO_ECOVACS['return']}})


class Move(VacBotCommand):
    def __init__(self, action):
        super().__init__('Move', {'move': {'action': self.ACTION[action]}})


class PlaySound(VacBotCommand):
    def __init__(self, sid="0"):
        super().__init__('PlaySound', {'sid': sid})


class GetCleanState(VacBotCommand):
    def __init__(self):
        super().__init__('GetCleanState')


class GetChargeState(VacBotCommand):
    def __init__(self):
        super().__init__('GetChargeState')


class GetBatteryState(VacBotCommand):
    def __init__(self):
        super().__init__('GetBatteryInfo')


class GetLifeSpan(VacBotCommand):
    def __init__(self, component):
        super().__init__('GetLifeSpan', {'type': COMPONENT_TO_ECOVACS[component]})


class SetTime(VacBotCommand):
    def __init__(self, timestamp, timezone):
        super().__init__('SetTime', {'time': {'t': timestamp, 'tz': timezone}})
