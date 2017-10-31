import configparser
import itertools
import logging
import os
import time
from threading import Event

import click
from sleekxmpp import ClientXMPP
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

    def wait_until_ready(self):
        self.ready_flag.wait()

    def session_start(self, event):
        print("----------------- starting session ----------------")
        self.ready_flag.set()

    def clean(self, speed='standard', type='auto'):
        self.make_command('clean', {'speed': speed, 'type': type}).send()

    def charge(self):
        self.make_command('charge', {'type': 'go'}).send()

    def make_command(self, name, args):
        clean = ET.Element(name, args)
        ctl = ET.Element('ctl', {'td': name.capitalize()})
        ctl.append(clean)
        command = self.wrap_command(ctl)
        return command

    def wrap_command(self, ctl):
        q = self.make_iq_query(xmlns=u'com:ctl', ito=self.vacuum + '/atom',
                               ifrom=self.user + '@' + self.domain + '/' + self.resource)
        q['type'] = 'set'
        for child in q.xml:
            if child.tag.endswith('query'):
                child.append(ctl)
                return q

    def run(self):
        self.connect(('47.88.66.164', '5223'))  # TODO: change to domain name
        click.echo("starting")
        self.process()
        click.echo("done with process")
        self.wait_until_ready()


def read_config(filename):
    parser = configparser.ConfigParser()
    with open(filename) as fp:
        parser.read_file(itertools.chain(['[global]'], fp), source=filename)
    return parser['global']


@click.group(chain=True)
@click.option('--charge/--no-charge', default=True, help='Return to charge after running. Defaults to yes.')
@click.option('--debug/--no-debug', default=False)
def cli(charge, debug):
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')


@cli.command(help='cleans for the specified number of minutes')
@click.argument('minutes', type=click.FLOAT)
def clean(minutes):
    def action(vacbot):
        click.echo('cleaning')
        vacbot.clean()
        time.sleep(minutes * 60)

    return action


@cli.command(help='returns to charger')
def charge(vacbot): # TODO convert
    click.echo('charging')
    vacbot.charge()
    time.sleep(20)


@cli.resultcallback()
def run(actions, charge, debug):
    config = read_config(os.path.expanduser('~/.config/sucks.conf'))
    vacbot = VacBot(config['user'], config['domain'], config['resource'], config['secret'],
                    config['vacuum'])
    vacbot.run()
    for action in actions:
        click.echo("running " + str(action))
        action(vacbot)
    if charge:
        vacbot.charge()
    vacbot.disconnect(wait=True)


if __name__ == '__main__':
    click.echo("starting commands")
    cli()
    click.echo("done with commands")
