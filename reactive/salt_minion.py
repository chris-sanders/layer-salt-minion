from charms.reactive import when, when_all, when_not, set_state, remove_state
from charmhelpers.core.hookenv import status_set
from charmhelpers.core.services.base import service_restart
from charmhelpers.fetch import apt_install

@when_not('salt-minion.installed')
@when('salt-common.installed')
def install_layer_salt_minion_subordinate():
    status_set('maintenance','installing salt-minion')
    apt_install('salt-minion')
    set_state('salt-minion.installed')
    status_set('active','')

@when('salt-minion.installed')
@when('saltmaster.changed')
def configure_master(saltmaster):
    with open('/etc/salt/minion.d/master.conf','w') as conf:
        conf.write("master: {}".format(saltmaster.address))
    service_restart('salt-minion')
    saltmaster.minion_ready()
    remove_state('saltmaster.changed')
    
