import configparser
import itertools
import os
import platform
import random
import re

import click
from pycountry_convert import country_alpha2_to_continent_code

from sucks import *

_LOGGER = logging.getLogger(__name__)


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


class BotWait():
    pass

    def wait(self, bot):
        raise NotImplementedError()


class TimeWait(BotWait):
    def __init__(self, seconds):
        super().__init__()
        self.seconds = seconds

    def wait(self, bot):
        click.echo("waiting for " + str(self.seconds) + "s")
        time.sleep(self.seconds)


class StatusWait(BotWait):
    def __init__(self, wait_on, wait_for):
        super().__init__()
        self.wait_on = wait_on
        self.wait_for = wait_for

    def wait(self, bot):
        if not hasattr(bot, self.wait_on):
            raise ValueError("object " + bot + " does not have method " + self.wait_on)
        _LOGGER.debug("waiting on " + self.wait_on + " for value " + self.wait_for)

        while getattr(bot, self.wait_on) != self.wait_for:
            time.sleep(0.5)
        _LOGGER.debug("wait complete; " + self.wait_on + " is now " + self.wait_for)


class CliAction:
    def __init__(self, vac_command, terminal=False, wait=None):
        self.vac_command = vac_command
        self.terminal = terminal
        self.wait = wait


def config_file():
    if platform.system() == 'Windows':
        return os.path.join(os.getenv('APPDATA'), 'sucks.conf')
    else:
        return os.path.expanduser('~/.config/sucks.conf')


def config_file_exists():
    return os.path.isfile(config_file())


def read_config():
    parser = configparser.ConfigParser()
    with open(config_file()) as fp:
        parser.read_file(itertools.chain(['[global]'], fp), source=config_file())
    return parser['global']


def write_config(config):
    os.makedirs(os.path.dirname(config_file()), exist_ok=True)
    with open(config_file(), 'w') as fp:
        for key in config:
            fp.write(key + '=' + str(config[key]) + "\n")


def current_country():
    # noinspection PyBroadException
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
    _LOGGER.debug("tossing coin: {:0.3f} <= {:0.3f}: {}".format(n, frequency, result))
    return result


@click.group(chain=True)
@click.option('--debug/--no-debug', default=False)
def cli(debug):
    logging.basicConfig(format='%(name)-10s %(levelname)-8s %(message)s')
    _LOGGER.parent.setLevel(logging.DEBUG if debug else logging.ERROR)


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
        return CliAction(Clean(), wait=TimeWait(minutes * 60))


@cli.command(help='cleans room edges for the specified number of minutes')
@click.option('--frequency', '-f', type=FREQUENCY, help='frequency with which to run; e.g. 0.5 or 3/7')
@click.argument('minutes', type=click.FLOAT)
def edge(frequency, minutes):
    if should_run(frequency):
        return CliAction(Edge(), wait=TimeWait(minutes * 60))


@cli.command(help='returns to charger')
def charge():
    return charge_action()


def charge_action():
    return CliAction(Charge(), terminal=True, wait=StatusWait('charge_status', 'charging'))


@cli.command(help='stops the robot in its current position')
def stop():
    return CliAction(Stop(), terminal=True, wait=StatusWait('clean_status', 'stop'))


@cli.resultcallback()
def run(actions, debug):
    actions = list(filter(None.__ne__, actions))
    if actions and charge and not actions[-1].terminal:
        actions.append(charge_action())

    if not config_file_exists():
        click.echo("Not logged in. Do 'click login' first.")
        exit(1)

    if debug:
        _LOGGER.debug("will run {}".format(actions))

    if actions:
        config = read_config()
        api = EcoVacsAPI(config['device_id'], config['email'], config['password_hash'],
                         config['country'], config['continent'])
        vacuum = api.devices()[0]
        vacbot = VacBot(api.uid, api.REALM, api.resource, api.user_access_token, vacuum, config['continent'])
        vacbot.connect_and_wait_until_ready()

        for action in actions:
            click.echo("performing " + str(action.vac_command))
            vacbot.run(action.vac_command)
            action.wait.wait(vacbot)

        vacbot.disconnect(wait=True)

    click.echo("done")


if __name__ == '__main__':
    cli()
