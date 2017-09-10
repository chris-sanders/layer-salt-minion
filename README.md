# Overview

This charm provides [salt-minion][salt]. To use this charm you will need to relate it with the salt-master.

# Usage

To deploy the charm

    juju deploy servicename

The intended use of this charmis to co-locate it with other services (1 per machine) so that you can configure all of the machines via salt.

## Scale out Usage

The only scale out necessary with this charm is to deploy addational units for new machines.

## Known Limitations and Issues

 * No significant limitations at this time, it's a simple charm

# Configuration

N/A

# Contact Information

## Upstream Project Name

  - https://github.com/chris-sanders/layer-salt-minion
  - https://github.com/chris-sanders/layer-salt-minion/issues 
  - email: sanders.chris@gmail.com


[salt]: https://saltstack.com/salt-open-source/
