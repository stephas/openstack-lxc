openstack-lxc
=============

minimal openstack 2.0 implementation inside Vagrantfile exposing lxc containers in ubuntu 12

mini-cloud in a VM

Notes
-----

1. There are a bunch of mistakes here if you look at the code, but I got what I wanted.
2. The first lxc container will take some time to spin up, because a 230M ubuntu-12.04-server-cloudimg-amd64-root.tar.gz is downloaded

Requirements
------------

1. vagrant gem
2. virtualbox

How to
------

```
$ vagrant up
$ vagrant ssh

vagrant@precise64:~$ cd /vagrant/
vagrant@precise64:/vagrant$ sudo python python-openstack-lxc.py 
 * Running on http://0.0.0.0:5000/
 * Restarting with reloader
...

(in a second vagrant ssh session)

Python 2.7.3 (default, Aug  1 2012, 05:14:39) 
[GCC 4.6.3] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> from libcloud.compute.types import Provider
>>> from libcloud.compute.providers import get_driver
>>> from pprint import pprint as pp
>>> OpenStack = get_driver(Provider.OPENSTACK)
>>> driver = OpenStack('lxc', 'lxc', ex_force_auth_url = 'http://localhost:5000/', ex_force_auth_version = '2.0_password')
>>> pp(driver.list_nodes())
[]
...

$ vagrant destroy -f
```

Advanced provisioning speed up trick :)
----------------

* create a vagrantbox w/ ubuntu 12
* install apt-cacher-ng
* make sure that vagrantbox is reachable from the one in this repo.
* echo "ip_of_apt_cacher_ng" > apt_cache
