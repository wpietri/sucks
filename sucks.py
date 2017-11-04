import configparser
import itertools
import logging
import os
import random
import re
import time
from threading import Event

import click
from sleekxmpp import ClientXMPP, Callback, MatchXPath
from sleekxmpp.xmlstream import ET


class VacBot(ClientXMPP):
    def __init__(self, user, domain, resource, secret, vacuum):
        ClientXMPP.__init__(self, user + '@' + domain, '0/' + resource + '/' + secret)

        self.user = user
        self.domain = domain
        self.resource = resource
        self.vacuum = vacuum
        self.credentials['authzid'] = user
        self.add_event_handler("session_start", self.session_start)

        self.ready_flag = Event()
        self.clean_status = None
        self.charge_status = None

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

    def handle_clean_report(self, iq):
        self.clean_status = iq.find('{com:ctl}query/{com:ctl}ctl/{com:ctl}clean').get('type')
        logging.debug("*** clean_status =" + self.clean_status)

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
        q = self.make_iq_query(xmlns=u'com:ctl', ito=self.vacuum + '/atom',
                               ifrom=self.user + '@' + self.domain + '/' + self.resource)
        q['type'] = 'set'
        for child in q.xml:
            if child.tag.endswith('query'):
                child.append(ctl)
                return q

    def connect_and_wait_until_ready(self):
        self.connect(('47.88.66.164', '5223'))  # TODO: change to domain name
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
        clean = ET.Element(self.name, self.args)
        ctl = ET.Element('ctl', {'td': self.name.capitalize()})
        ctl.append(clean)
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
    RATIONAL_PATTERN = re.compile(r'([.0-9])/([.0-9])')

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
        except ValueError:
            pass

        if result is None:
            self.fail('%s is not a valid frequency' % value, param, ctx)
        if 0 <= result <= 1:
            return result

        self.fail('%s is not between 0 and 1' % value, param, ctx)


FREQUENCY = FrequencyParamType()


def read_config(filename):
    parser = configparser.ConfigParser()
    with open(filename) as fp:
        parser.read_file(itertools.chain(['[global]'], fp), source=filename)
    return parser['global']


def should_run(frequency):
    if frequency is None:
        return
    n = random.random()
    result = n <= frequency
    logging.debug("tossing coin: {:0.3f} <= {:0.3f}: {}".format( n, frequency, result))
    return result


@click.group(chain=True)
@click.option('--charge/--no-charge', default=True, help='Return to charge after running. Defaults to yes.')
@click.option('--debug/--no-debug', default=False)
def cli(charge, debug):
    level = logging.DEBUG if debug else logging.ERROR
    logging.basicConfig(level=level, format='%(levelname)-8s %(message)s')


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

    if actions:
        config = read_config(os.path.expanduser('~/.config/sucks.conf'))
        vacbot = VacBot(config['user'], config['domain'], config['resource'], config['secret'],
                        config['vacuum'])
        vacbot.connect_and_wait_until_ready()

        for action in actions:
            click.echo("performing " + str(action))
            vacbot.run(action)

        vacbot.disconnect(wait=True)

    click.echo("done")


if __name__ == '__main__':
    cli()
