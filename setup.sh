apt-get update
apt-get install -y lxc vim python-pip git python-novaclient tmux curl

### code errors with module has no attribute virtual_memory
### apt-get install -y python-psutil
# SO
apt-get install -y python-dev
pip install -r /vagrant/requirements.txt

## for ruby's fog:
#apt-get install -y libxslt-dev libxml-dev build-essential
#gem install fog
