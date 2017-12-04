import configparser
import hashlib
import itertools
import logging
import os
import random
import re
import time
from base64 import b64decode, b64encode
from collections import OrderedDict
from threading import Event

import click
import requests
from pycountry_convert import country_alpha2_to_continent_code
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
        self.ready_flag.set()

        self.register_handler(Callback('clean report',
                                       MatchXPath('{jabber:client}iq/{com:ctl}query/{com:ctl}ctl[@td="CleanReport"]'),
                                       self.handle_clean_report))
        self.register_handler(Callback('clean report',
                                       MatchXPath('{jabber:client}iq/{com:ctl}query/{com:ctl}ctl[@td="ChargeState"]'),
                                       self.handle_charge_report))
        self.register_handler(Callback('clean report',
                                       MatchXPath('{jabber:client}iq/{com:ctl}query/{com:ctl}ctl[@td="BatteryInfo"]'),
                                       self.handle_battery_report))

    def handle_clean_report(self, iq):
        self.clean_status = iq.find('{com:ctl}query/{com:ctl}ctl/{com:ctl}clean').get('type')
        logging.debug("*** clean_status =" + self.clean_status)

    def handle_battery_report(self, iq):
        try:
            self.battery_status = float(iq.find('{com:ctl}query/{com:ctl}ctl/{com:ctl}battery').get('power')) / 100
        except ValueError:
            logging.warning("couldn't parse battery status " + ET.tostring(iq))
        logging.debug("*** battery_status = {:.0%}".format(self.battery_status))

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
        logging.debug("*** charge_status =" + self.charge_status)

    def send_command(self, xml):
        c = self.wrap_command(xml)
        c.send()

    def wrap_command(self, ctl):
        q = self.make_iq_query(xmlns=u'com:ctl',
                               ito=self.vacuum['did'] + '@' + self.vacuum['class'] + '.ecorobot.net/atom',
                               ifrom=self.user + '@' + self.domain + '/' + self.resource)
        q['type'] = 'set'
        for child in q.xml:
            if child.tag.endswith('query'):
                child.append(ctl)
                return q

    def connect_and_wait_until_ready(self):
        self.connect(('msg-{}.ecouser.net'.format(self.continent), '5223'))
        self.process()
        self.wait_until_ready()

    def run(self, action):
        self.send_command(action.to_xml())
        action.wait_for_completion(self)


class VacBotCommand():
    def __init__(self, name, args, wait=None, terminal=False):
        self.name = name
        self.args = args
        self.wait = wait
        self.terminal = terminal

    def wait_for_completion(self, bot):
        if self.wait:
            click.echo("waiting in " + self.command_name() + " for " + str(self.wait) + "s")
            time.sleep(self.wait)

    def to_xml(self):
        ctl = ET.Element('ctl', {'td': self.name.capitalize()})
        inner = ET.Element(self.name, self.args)
        ctl.append(inner)
        return ctl

    def __str__(self, *args, **kwargs):
        return self.command_name() + " command"

    def command_name(self):
        return self.__class__.__name__.lower()


class Clean(VacBotCommand):
    def __init__(self, wait):
        super().__init__('clean', {'type': 'auto', 'speed': 'standard'}, wait)


class Edge(VacBotCommand):
    def __init__(self, wait):
        super().__init__('clean', {'type': 'border', 'speed': 'strong'}, wait)


class Charge(VacBotCommand):
    def __init__(self):
        super().__init__('charge', {'type': 'go'}, terminal=True)

    def wait_for_completion(self, bot):
        logging.debug("waiting in " + self.name)
        while bot.charge_status not in ['charging']:
            time.sleep(0.5)
        logging.debug("done waiting in " + self.name)
        click.echo("docked")


class Stop(VacBotCommand):
    def __init__(self):
        super().__init__('clean', {'type': 'stop', 'speed': 'standard'}, terminal=True)

    def wait_for_completion(self, bot):
        logging.debug("waiting in " + self.name)
        while bot.clean_status not in ['stop']:
            time.sleep(0.5)
        logging.debug("done waiting in " + self.name)


class FrequencyParamType(click.ParamType):
    name = 'frequency'
    RATIONAL_PATTERN = re.compile(r'([.0-9]+)/([.0-9]+)')

    def convert(self, value, param, ctx):
        result = None
        try:
            search = self.RATIONAL_PATTERN.search(value)
            if search:
                result = float(search.group(1)) / float(search.group(2))
            else:
                try:
                    result = float(value)
                except ValueError:
                    pass
        except (ValueError, ArithmeticError):
            pass

        if result is None:
            self.fail('%s is not a valid frequency' % value, param, ctx)
        if 0 <= result <= 1:
            return result

        self.fail('%s is not between 0 and 1' % value, param, ctx)


FREQUENCY = FrequencyParamType()


def config_file():
    return os.path.expanduser('~/.config/sucks.conf')


def config_file_exists():
    return os.path.isfile(config_file())


def read_config():
    parser = configparser.ConfigParser()
    with open(config_file()) as fp:
        parser.read_file(itertools.chain(['[global]'], fp), source=config_file())
    return parser['global']


def write_config(config):
    parser = configparser.ConfigParser()
    with open(config_file(), 'w') as fp:
        for key in config:
            fp.write(key + '=' + config[key] + "\n")


def current_country():
    try:
        return requests.get('http://ipinfo.io/json').json()['country'].lower()
    except:
        return 'us'


def continent_for_country(country_code):
    return country_alpha2_to_continent_code(country_code.upper()).lower()


def should_run(frequency):
    if frequency is None:
        return True
    n = random.random()
    result = n <= frequency
    logging.debug("tossing coin: {:0.3f} <= {:0.3f}: {}".format(n, frequency, result))
    return result


@click.group(chain=True)
@click.option('--charge/--no-charge', default=True, help='Return to charge after running. Defaults to yes.')
@click.option('--debug/--no-debug', default=False)
def cli(charge, debug):
    level = logging.DEBUG if debug else logging.ERROR
    logging.basicConfig(level=level, format='%(levelname)-8s %(message)s')


@cli.command(help='logs in with specified email; run this first')
@click.option('--email', prompt='Ecovacs app email')
@click.option('--password', prompt='Ecovacs app password', hide_input=True)
@click.option('--country-code', prompt='your two-letter country code', default=lambda: current_country())
@click.option('--continent-code', prompt='your two-letter continent code',
              default=lambda: continent_for_country(click.get_current_context().params['country_code']))
def login(email, password, country_code, continent_code):
    if config_file_exists() and not click.confirm('overwrite existing config?'):
        click.echo("Skipping login.")
        exit(0)
    config = OrderedDict()
    password_hash = EcoVacsAPI.md5(password)
    device_id = EcoVacsAPI.md5(str(time.time()))
    try:
        EcoVacsAPI(device_id, email, password_hash, country_code, continent_code)
    except ValueError as e:
        click.echo(e.args[0])
        exit(1)
    config['email'] = email
    config['password_hash'] = password_hash
    config['device_id'] = device_id
    config['country'] = country_code.lower()
    config['continent'] = continent_code.lower()
    write_config(config)
    click.echo("Config saved.")
    exit(0)


@cli.command(help='auto-cleans for the specified number of minutes')
@click.option('--frequency', '-f', type=FREQUENCY, help='frequency with which to run; e.g. 0.5 or 3/7')
@click.argument('minutes', type=click.FLOAT)
def clean(frequency, minutes):
    if should_run(frequency):
        return Clean(minutes * 60)


@cli.command(help='cleans room edges for the specified number of minutes')
@click.option('--frequency', '-f', type=FREQUENCY, help='frequency with which to run; e.g. 0.5 or 3/7')
@click.argument('minutes', type=click.FLOAT)
def edge(frequency, minutes):
    if should_run(frequency):
        return Edge(minutes * 60)


@cli.command(help='returns to charger')
def charge():
    return Charge()


@cli.command(help='stops the robot in its current position')
def stop():
    return Stop()


@cli.resultcallback()
def run(actions, charge, debug):
    actions = list(filter(None.__ne__, actions))
    if actions and charge and not actions[-1].terminal:
        actions.append(Charge())

    if not config_file_exists():
        click.echo("Not logged in. Do 'click login' first.")
        exit(1)

    if actions:
        config = read_config()
        api = EcoVacsAPI(config['device_id'], config['email'], config['password_hash'],
                         config['country'], config['continent'])
        vacuum = api.devices()[0]
        vacbot = VacBot(api.uid, api.REALM, api.resource, api.user_access_token, vacuum, config['continent'])
        vacbot.connect_and_wait_until_ready()

        for action in actions:
            click.echo("performing " + str(action))
            vacbot.run(action)

        vacbot.disconnect(wait=True)

    click.echo("done")


if __name__ == '__main__':
    cli()
