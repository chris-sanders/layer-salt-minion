from charms.reactive import when, when_not, set_state
from charmhelpers.core.hookenv import status_set
from charmhelpers.fetch import apt_install

@when_not('salt-minion.installed')
@when('salt-common.installed')
def install_layer_salt_minion_subordinate():
    status_set('maintenance','installing salt-minion')
    apt_install('salt-minion')
    set_state('salt-minion.installed')
    status_set('active','')
