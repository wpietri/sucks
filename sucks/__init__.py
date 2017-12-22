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


class EcoVacsAPI:
    CLIENT_KEY = "eJUWrzRv34qFSaYk"
    SECRET = "Cyu5jcR4zyK6QEPn1hdIGXB5QIDAQABMA0GC"
    PUBLIC_KEY = 'MIIB/TCCAWYCCQDJ7TMYJFzqYDANBgkqhkiG9w0BAQUFADBCMQswCQYDVQQGEwJjbjEVMBMGA1UEBwwMRGVmYXVsdCBDaXR5MRwwGgYDVQQKDBNEZWZhdWx0IENvbXBhbnkgTHRkMCAXDTE3MDUwOTA1MTkxMFoYDzIxMTcwNDE1MDUxOTEwWjBCMQswCQYDVQQGEwJjbjEVMBMGA1UEBwwMRGVmYXVsdCBDaXR5MRwwGgYDVQQKDBNEZWZhdWx0IENvbXBhbnkgTHRkMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDb8V0OYUGP3Fs63E1gJzJh+7iqeymjFUKJUqSD60nhWReZ+Fg3tZvKKqgNcgl7EGXp1yNifJKUNC/SedFG1IJRh5hBeDMGq0m0RQYDpf9l0umqYURpJ5fmfvH/gjfHe3Eg/NTLm7QEa0a0Il2t3Cyu5jcR4zyK6QEPn1hdIGXB5QIDAQABMA0GCSqGSIb3DQEBBQUAA4GBANhIMT0+IyJa9SU8AEyaWZZmT2KEYrjakuadOvlkn3vFdhpvNpnnXiL+cyWy2oU1Q9MAdCTiOPfXmAQt8zIvP2JC8j6yRTcxJCvBwORDyv/uBtXFxBPEC6MDfzU2gKAaHeeJUWrzRv34qFSaYkYta8canK+PSInylQTjJK9VqmjQ'
    MAIN_URL_FORMAT = 'https://eco-{country}-api.ecovacs.com/v1/private/{country}/{lang}/{deviceId}/{appCode}/{appVersion}/{channel}/{deviceType}'
    USER_URL_FORMAT = 'https://users-{continent}.ecouser.net:8000/user.do'
    REALM = 'ecouser.net'

    def __init__(self, device_id, account_id, password_hash, country, continent):
        self.meta = {
            'country': country,
            'lang': 'en',
            'deviceId': device_id,
            'appCode': 'i_eco_e',
            'appVersion': '1.3.5',
            'channel': 'c_googleplay',
            'deviceType': '1'
        }
        logging.debug("Setting up EcoVacsAPI")
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
        self.user_access_token = self.__call_login_by_it_token()['token']
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
        logging.debug("calling main api {} with {}".format(function, args))
        params = OrderedDict(args)
        params['requestId'] = self.md5(time.time())
        url = (EcoVacsAPI.MAIN_URL_FORMAT + "/" + function).format(**self.meta)
        api_response = requests.get(url, self.__sign(params))
        json = api_response.json()
        logging.debug("got {}".format(json))
        if json['code'] == '0000':
            return json['data']
        elif json['code'] == '1005':
            logging.warning("incorrect email or password")
            raise ValueError("incorrect email or password")
        else:
            logging.error("call to {} failed with {}".format(function, json))
            raise RuntimeError("failure code {} ({}) for call {} and parameters {}".format(
                json['code'], json['msg'], function, args))

    def __call_user_api(self, function, args):
        logging.debug("calling user api {} with {}".format(function, args))
        params = {'todo': function}
        params.update(args)
        response = requests.post(EcoVacsAPI.USER_URL_FORMAT.format(continent=self.continent), json=params)
        json = response.json()
        logging.debug("got {}".format(json))
        if json['result'] == 'ok':
            return json
        else:
            logging.error("call to {} failed with {}".format(function, json))
            raise RuntimeError(
                "failure {} ({}) for call {} and parameters {}".format(json['error'], json['errno'], function, params))

    def __call_login_by_it_token(self):
        return self.__call_user_api('loginByItToken',
                                    {'country': self.meta['country'].upper(),
                                     'resource': self.resource,
                                     'realm': EcoVacsAPI.REALM,
                                     'userId': self.uid,
                                     'token': self.auth_code}
                                    )

    def devices(self):
        devices = self.__call_user_api('GetDeviceList', {
            'userid': self.uid,
            'auth': {
                'with': 'users',
                'userid': self.uid,
                'realm': EcoVacsAPI.REALM,
                'token': self.user_access_token,
                'resource': self.resource
            }
        })['devices']
        return devices

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


class VacBot():
    def __init__(self, user, domain, resource, secret, vacuum, continent, server_address=None):

        self.vacuum = vacuum
        self.clean_status = None
        self.charge_status = None
        self.battery_status = None

        self.xmpp = EcoVacsXMPP(user, domain, resource, secret, continent, server_address)

        self.xmpp.subscribe_to_ctls(self._handle_ctl)

    def connect_and_wait_until_ready(self):
        self.xmpp.connect_and_wait_until_ready()

        self.xmpp.schedule('Ping', 30, lambda: self.xmpp.send_ping(self._vacuum_address()), repeat=True)

    def _handle_ctl(self, ctl):
        method = '_handle_' + ctl['event']
        if hasattr(self, method):
            getattr(self, method)(ctl)

    def _handle_clean_report(self, event):
        self.clean_status = event['type']
        logging.debug("*** clean_status = " + self.clean_status)

    def _handle_battery_info(self, iq):
        try:
            self.battery_status = float(iq['power']) / 100
            logging.debug("*** battery_status = {:.0%}".format(self.battery_status))
        except ValueError:
            logging.warning("couldn't parse battery status " + ET.tostring(iq))

    def _handle_charge_state(self, event):
        report = event['type']
        if report == 'going':
            self.charge_status = 'returning'
        elif report == 'slot_charging':
            self.charge_status = 'charging'
        elif report == 'idle':
            self.charge_status = 'idle'
        else:
            logging.warning("Unknown charging status '" + report + "'")
        logging.debug("*** charge_status = " + self.charge_status)

    def _vacuum_address(self):
        return self.vacuum['did'] + '@' + self.vacuum['class'] + '.ecorobot.net/atom'

    def send_command(self, xml):
        self.xmpp.send_command(xml, self._vacuum_address())

    def run(self, action):
        self.send_command(action.to_xml())

    def disconnect(self, wait=False):
        self.xmpp.disconnect(wait=wait)


class EcoVacsXMPP(ClientXMPP):
    def __init__(self, user, domain, resource, secret, continent, server_address=None):
        ClientXMPP.__init__(self, user + '@' + domain, '0/' + resource + '/' + secret)

        self.user = user
        self.domain = domain
        self.resource = resource
        self.continent = continent
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
        logging.debug("----------------- starting session ----------------")
        logging.debug("event = {}".format(event))
        self.register_handler(Callback("general",
                                       MatchXPath('{jabber:client}iq/{com:ctl}query/{com:ctl}'),
                                       self._handle_ctl))
        self.ready_flag.set()

    def subscribe_to_ctls(self, function):
        self.ctl_subscribers.append(function)

    def _handle_ctl(self, message):
        the_good_part = message.get_payload()[0][0]
        as_dict = self._ctl_to_dict(the_good_part)
        for s in self.ctl_subscribers:
            s(as_dict)

    def _ctl_to_dict(self, xml):
        result = xml.attrib.copy()
        result['event'] = result.pop('td')
        if xml:
            result.update(xml[0].attrib)

        for key in result:
            result[key] = stringcase.snakecase(result[key])
        return result

    def register_callback(self, kind, function):
        self.register_handler(Callback(kind,
                                       MatchXPath('{jabber:client}iq/{com:ctl}query/{com:ctl}ctl[@td="' + kind + '"]'),
                                       function))

    def send_command(self, xml, recipient):
        c = self._wrap_command(xml, recipient)
        logging.debug('Sending command {0}'.format(c))
        c.send()

    def _wrap_command(self, ctl, recipient):
        q = self.make_iq_query(xmlns=u'com:ctl', ito=recipient, ifrom=self._my_address())
        q['type'] = 'set'
        for child in q.xml:
            if child.tag.endswith('query'):
                child.append(ctl)
                return q

    def _my_address(self):
        return self.user + '@' + self.domain + '/' + self.resource

    def send_ping(self, to):
        q = self.make_iq_get(ito=to, ifrom=self._my_address())
        q.xml.append(ET.Element('ping', {'xmlns': 'urn:xmpp:ping'}))
        logging.debug("*** sending ping ***")
        q.send()

    def connect_and_wait_until_ready(self):
        self.connect(self.server_address)
        self.process()
        self.wait_until_ready()


class VacBotCommand:
    CLEAN_MODE = {
        'auto': 'auto',
        'edge': 'border',
        'spot': 'spot',
        'single_room': 'singleroom',
        'stop': 'stop'
    }
    FAN_SPEED = {
        'normal': 'standard',
        'high': 'strong'
    }
    CHARGE_MODE = {
        'return': 'go',
        'returning': 'Going',
        'charging': 'SlotCharging',
        'idle': 'Idle'
    }
    COMPONENT = {
        'main_brush': 'Brush',
        'side_brush': 'SideBrush',
        'filter': 'DustCaseHeap'
    }
    ACTION = {
        'forward': 'forward',
        'left': 'SpinLeft',
        'right': 'SpinRight',
        'turn_around': 'TurnAround',
        'stop': 'stop'
    }

    def __init__(self, name, args=None):
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

    def __str__(self, *args, **kwargs):
        return self.command_name() + " command"

    def command_name(self):
        return self.__class__.__name__.lower()


class Clean(VacBotCommand):
    def __init__(self, mode='auto', speed='normal', terminal=False):
        super().__init__('Clean', {'clean': {'type': self.CLEAN_MODE[mode], 'speed': self.FAN_SPEED[speed]}})


class Edge(Clean):
    def __init__(self):
        super().__init__('edge', 'high')


class Spot(Clean):
    def __init__(self):
        super().__init__('spot', 'high')


class Stop(Clean):
    def __init__(self):
        super().__init__('stop', 'normal')


class Charge(VacBotCommand):
    def __init__(self):
        super().__init__('Charge', {'charge': {'type': self.CHARGE_MODE['return']}})


class Move(VacBotCommand):
    def __init__(self, action):
        super().__init__('Move', {'move': {'action': self.ACTION[action]}})


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
        super().__init__('GetLifeSpan', {'type': self.COMPONENT[component]})


class SetTime(VacBotCommand):
    def __init__(self, timestamp, timezone):
        super().__init__('SetTime', {'time': {'t': timestamp, 'tz': timezone}})
