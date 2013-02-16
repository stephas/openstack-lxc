from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

from pprint import pprint as pp

OpenStack = get_driver(Provider.OPENSTACK)
driver = OpenStack('lxc', 'lxc', ex_force_auth_url = 'http://localhost:5000/', ex_force_auth_version = '2.0_password')

pp(driver.list_nodes())
pp([s.__dict__ for s in driver.list_sizes()])
pp(driver.list_images())
for n in range(0,5):
    pp(driver.create_node(name='test{0}'.format(n), size=driver.list_sizes()[0], image=driver.list_images()[0]).__dict__)

import time
not_running_count = 1
while not_running_count:
    import os
    os.system('clear')
    all_nodes = [(n.id, n.name, n.state, n.public_ips, n.private_ips, n.uuid) for n in driver.list_nodes()]
    not_running_count = len([n for n in all_nodes if n[2] <> 0 ])
    pp(all_nodes)
    print("not running: {0}".format(not_running_count))
    time.sleep(5)

print [n.destroy() for n in driver.list_nodes()]
print driver.list_nodes()
