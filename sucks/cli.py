import configparser
import itertools
import os
import random
import re

from pycountry_convert import country_alpha2_to_continent_code

from sucks import *


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
    with open(config_file(), 'w') as fp:
        for key in config:
            fp.write(key + '=' + config[key] + "\n")


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
    logging.debug("tossing coin: {:0.3f} <= {:0.3f}: {}".format(n, frequency, result))
    return result


@click.group(chain=True)
@click.option('--debug/--no-debug', default=False)
def cli(debug):
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
def run(actions, debug):
    actions = list(filter(None.__ne__, actions))
    if actions and charge and not actions[-1].terminal:
        actions.append(Charge())

    if not config_file_exists():
        click.echo("Not logged in. Do 'click login' first.")
        exit(1)

    if debug:
        logging.debug("will run {}".format(actions))

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
