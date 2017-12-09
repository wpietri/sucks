import hashlib
import logging
import time
from base64 import b64decode, b64encode
from collections import OrderedDict
from threading import Event

import click
import requests
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


class VacBot(ClientXMPP):
    def __init__(self, user, domain, resource, secret, vacuum, continent):
        ClientXMPP.__init__(self, user + '@' + domain, '0/' + resource + '/' + secret)

        self.user = user
        self.domain = domain
        self.resource = resource
        self.vacuum = vacuum
        self.continent = continent
        self.credentials['authzid'] = user
        self.add_event_handler("session_start", self.session_start)

        self.ready_flag = Event()
        self.clean_status = None
        self.charge_status = None
        self.battery_status = None

    def wait_until_ready(self):
        self.ready_flag.wait()

    def session_start(self, event):
        logging.debug("----------------- starting session ----------------")
        logging.debug("event = {}".format(event))
        self.ready_flag.set()

        self.__register_callback("CleanReport", self.handle_clean_report)
        self.__register_callback("ChargeState", self.handle_charge_report)
        self.__register_callback("BatteryInfo", self.handle_battery_report)
        self.__register_callback("error", self.handle_error)

        self.schedule('Ping', 30, self.send_ping, repeat=True)


    def __register_callback(self, kind, function):
        self.register_handler(Callback(kind,
                                       MatchXPath('{jabber:client}iq/{com:ctl}query/{com:ctl}ctl[@td="' + kind + '"]'),
                                       function))


    def handle_clean_report(self, iq):
        self.clean_status = iq.find('{com:ctl}query/{com:ctl}ctl/{com:ctl}clean').get('type')
        logging.debug("*** clean_status = " + self.clean_status)

    def handle_battery_report(self, iq):
        try:
            self.battery_status = float(iq.find('{com:ctl}query/{com:ctl}ctl/{com:ctl}battery').get('power')) / 100
            logging.debug("*** battery_status = {:.0%}".format(self.battery_status))
        except ValueError:
            logging.warning("couldn't parse battery status " + ET.tostring(iq))

    def handle_charge_report(self, iq):
        report = iq.find('{com:ctl}query/{com:ctl}ctl/{com:ctl}charge').get('type')
        if report.lower() == 'going':
            self.charge_status = 'returning'
        elif report.lower() == 'slotcharging':
            self.charge_status = 'charging'
        elif report.lower() == 'idle':
            self.charge_status = 'idle'
        else:
            logging.warning("Unknown charging status '" + report + "'")
        logging.debug("*** charge_status = " + self.charge_status)

    def handle_error(self, iq):
        error = iq.find('{com:ctl}query/{com:ctl}ctl').get('error')
        error_no = iq.find('{com:ctl}query/{com:ctl}ctl').get('errno')
        logging.debug("*** error = " + error_no + " " + error)

    def send_command(self, xml):
        c = self.wrap_command(xml)
        logging.debug('Sending command {0}'.format(c))
        c.send()

    def wrap_command(self, ctl):
        q = self.make_iq_query(xmlns=u'com:ctl', ito=self.__vacuum_adress(), ifrom=self.__my_address())
        q['type'] = 'set'
        for child in q.xml:
            if child.tag.endswith('query'):
                child.append(ctl)
                return q

    def send_ping(self):
        q = self.make_iq_get(ito=self.__vacuum_adress(), ifrom=self.__my_address())
        q.xml.append(ET.Element('ping', {'xmlns': 'urn:xmpp:ping'}))
        logging.debug("*** sending ping ***")
        q.send()

    def __my_address(self):
        return self.user + '@' + self.domain + '/' + self.resource

    def __vacuum_adress(self):
        return self.vacuum['did'] + '@' + self.vacuum['class'] + '.ecorobot.net/atom'

    def connect_and_wait_until_ready(self):
        self.connect(('msg-{}.ecouser.net'.format(self.continent), '5223'))
        self.process()
        self.wait_until_ready()

    def run(self, action):
        self.send_command(action.to_xml())
        action.wait_for_completion(self)


class VacBotCommand:
    def __init__(self, name, args=None, wait=None, terminal=False):
        self.name = name
        self.args = args
        self.wait = wait
        self.terminal = terminal

    def wait_for_completion(self, bot):
        if self.wait:
            click.echo("waiting in " + self.command_name() + " for " + str(self.wait) + "s")
            time.sleep(self.wait)

    def to_xml(self):
        ctl = ET.Element('ctl', {'td': self.name})
        if self.args:
            inner = ET.Element(self.name.lower(), self.args)
            ctl.append(inner)
        return ctl

    def __str__(self, *args, **kwargs):
        return self.command_name() + " command"

    def command_name(self):
        return self.__class__.__name__.lower()


class Clean(VacBotCommand):
    def __init__(self, wait):
        super().__init__('Clean', {'type': 'auto', 'speed': 'standard'}, wait)


class Edge(VacBotCommand):
    def __init__(self, wait):
        super().__init__('Clean', {'type': 'border', 'speed': 'strong'}, wait)


class Charge(VacBotCommand):
    def __init__(self):
        super().__init__('Charge', {'type': 'go'}, terminal=True)

    def wait_for_completion(self, bot):
        logging.debug("waiting in " + self.name)
        while bot.charge_status not in ['charging']:
            time.sleep(0.5)
        logging.debug("done waiting in " + self.name)
        click.echo("docked")


class Stop(VacBotCommand):
    def __init__(self):
        super().__init__('Clean', {'type': 'stop', 'speed': 'standard'}, terminal=True)

    def wait_for_completion(self, bot):
        logging.debug("waiting in " + self.name)
        while bot.clean_status not in ['stop']:
            time.sleep(0.5)
        logging.debug("done waiting in " + self.name)
