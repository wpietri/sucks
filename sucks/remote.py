import configparser
import itertools
import os
import click

from sucks import *


vacbot = None
last_error = 0
last_command = None


def config_file():
    return os.path.expanduser('~/.config/sucks.conf')


def read_config():
    parser = configparser.ConfigParser()
    with open(config_file()) as fp:
        parser.read_file(itertools.chain(['[global]'], fp), source=config_file())
    return parser['global']


def handle_error(error_no):
    global last_error

    if vacbot.charge_status == 'returning':
        resume_command = Charge()
    elif vacbot.clean_status == 'auto':
        resume_command = Clean()
    elif vacbot.clean_status == 'border':
        resume_command = Edge()
    if error_no != "100":
        click.echo('error ocurred:' + error_no)
        if time.time() - last_error > 60:
            click.echo('trying to get unstuck')
            time.sleep(2)
            vacbot.run(Move("TurnAround"))
            time.sleep(3)
            vacbot.run(resume_command)
        else:
            click.echo('error ocurred within last 60 seconds, giving up')
        last_error = time.time()


def handle_state_change():
    click.echo('Clean state: ' + str(vacbot.clean_status))
    click.echo('Charge state: ' + str(vacbot.charge_status))
    click.echo('Battery state: ' + str(vacbot.battery_status))


def run(debug=False):
    global vacbot

    level = logging.DEBUG if debug else logging.ERROR
    logging.basicConfig(level=level, format='%(levelname)-8s %(message)s')

    config = read_config()
    api = EcoVacsAPI(config['device_id'], config['email'], config['password_hash'],
                     config['country'], config['continent'])
    vacuum = api.devices()[0]
    vacbot = VacBot(api.uid, api.REALM, api.resource, api.user_access_token, vacuum, config['continent'])
    vacbot.connect_and_wait_until_ready()

    vacbot.on_error = handle_error
    vacbot.on_state_change = handle_state_change

    while True:
        value = click.prompt('Please enter an action (clean, edge, stop, charge, move)', type=str)

        if value == "clean":
            vacbot.run(Clean())

        if value == "edge":
            vacbot.run(Edge())

        if value == "stop":
            vacbot.run(Stop())

        if value == "charge":
            vacbot.run(Charge())

        if value == "move":
            direction = click.prompt('Please enter direction (forward, SpinLeft, SpinRight, stop, TurnAround)', type=str)
            vacbot.run(Move(direction))


if __name__ == '__main__':
    run(debug=False)
