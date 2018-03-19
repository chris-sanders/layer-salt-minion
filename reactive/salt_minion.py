from charms.reactive import when, when_not, set_state, remove_state
from charmhelpers.core import hookenv
from charmhelpers.core.hookenv import status_set
from charmhelpers.core.services.base import service_restart
from charmhelpers.fetch import apt_install
import socket


def get_minion_id():
    config = hookenv.config()
    if config['unit-as-id']:
        return hookenv.local_unit().replace('/', '-')
    else:
        return socket.getfqdn()


@when_not('salt-minion.installed')
@when('salt-common.installed')
def install_layer_salt_minion_subordinate():
    status_set('maintenance', 'installing salt-minion')
    apt_install('salt-minion')
    with open('/etc/salt/minion_id', 'w') as conf:
        conf.write("{}".format(get_minion_id()))
    set_state('salt-minion.installed')
    status_set('active', 'Minion ready')


@when('salt-minion.installed')
@when('saltmaster.changed')
def configure_master(saltmaster):
    with open('/etc/salt/minion.d/master.conf', 'w') as conf:
        conf.write("master: {}".format(saltmaster.address))
    service_restart('salt-minion')
    saltmaster.minion_ready(get_minion_id())
    remove_state('saltmaster.changed')

