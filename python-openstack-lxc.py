from flask import Flask, request, Response
app = Flask(__name__)

try:
    from simplejson import json
except:
    import json

import psutil

import shlex, subprocess, re # calls to lxc-*

import threading

global base_url
base_url = 'http://localhost:5000/v2'

@app.route('/v2.0/tokens', methods = [ 'POST' ])
def auth():
    auth_dict = get_auth()
    json_raw = json.dumps(auth_dict)
    return Response(json_raw, status=200, mimetype='application/json')

def is_auth_ok(request_obj):
    headers = request_obj.headers
    if 'X-Auth-Token' in headers:
        if headers['X-Auth-Token'] == 'only_this_id':
            return True
    return False

def get_auth():
    d = {}
    d['access'] = {}
    d['access']['token'] = { 'id': 'only_this_id'}
    d['access']['serviceCatalog'] = get_serviceCatalog()
    d['access']['user'] = d['access']['token'] # for ruby fog?
    return d

def get_serviceCatalog():
    url = base_url + '/compute'
    d = [{
            "endpoints": [
                {
#                    "adminURL": url, 
                    "internalURL": url,
                    "publicURL": url,
                    "region": "RegionOne"
                }
            ],
            "name": "nova",
            "type": "compute"
        }]    
    return d

# --- This ensures authorization and json representation
def gen_response(dict_data):
    ok_str = 'AUTH_OK' if is_auth_ok(request) else 'BAD_AUTH'
    print('{0}'.format(ok_str))
    threads = [t.name for t in threading.enumerate()]
    print('threads: {0}'.format(threads))
    json_raw = json.dumps(dict_data)
    return Response(json_raw, status=200, mimetype='application/json')

# --- This deserializes a json request
def unmarshal(request_obj):
    # TODO: ensure json, support xml
    json_raw = json.loads(request_obj.data)
    return json_raw

#--- Compute - Create
def run(cmd):
    try:
        print "EXEC: {0}".format(cmd)
        out = subprocess.check_output(shlex.split(cmd))
        print out
    except subprocess.CalledProcessError as e:
        print 'WOW "{0}" SAYS "{1}"'.format(cmd, e.output)

def lxc_create(name, template_id):
#    cmd = 'lxc-create -n {0} -t {1} -- -r precise'.format(name, template_id)
    cmd = 'lxc-create -n {0} -t {1} -- -u /vagrant/userdata.cloud-init -r precise -S /home/vagrant/.ssh/id_rsa.pub'.format(name, template_id)
    run(cmd)

def lxc_start(name):
    cmd = 'lxc-start -n {0} -d -o /tmp/lxc.log'.format(name)
    run(cmd)

def lxc_wait(name, state):
    cmd = 'lxc-wait -n {0} -s {1}'.format(name, state)
    run(cmd)

def lxc_destroy(name):
    cmd = 'lxc-destroy -n {0}'.format(name)
    run(cmd)

def lxc_stop(name):
    cmd = 'lxc-stop -n {0}'.format(name)
    run(cmd)

def start_lxc_compute(compute_request):
    """thread: lxc-create, lxc-start, get_ip"""
    import time
    time.sleep(2)
    info = compute_request['server']
    name = info['name']
    lxc_create(name, 'ubuntu-cloud')
    #lxc_create(name, 'ubuntu')
    lxc_wait(name, 'STOPPED')
    lxc_start(name)
    print "done w/ {0}".format(name)

def start_lxc_thread(compute_request):
    existing_nodes = [ n for node_per_state in lxc_list() for n in node_per_state ]
    n = compute_request["server"]["name"]
    if n in existing_nodes:
        print 'AAAAAAAAAAAAAAAHHHHHH {0} exists.'.format(n)
    else:
        t = threading.Thread(target=start_lxc_compute, name="starting:{0}".format(n), args=(compute_request, ))
        t.daemon = True
        t.start()

def get_server(name):
    new_compute = unmarshal(request)
    print(new_compute)
    start_lxc_thread(new_compute)
    #d = { 'servers': [] }
    compute_id = name #"5bbcc3c4-1da2-4437-a48a-66f15b1b13f9"
    url = base_url + '/compute/servers/' + compute_id
    # self was with version, bookmark w/o version
    d = {
        "server": {
            "adminPass": "ubuntu",
            "id": compute_id,
            "links": [
                {
                    "href": url,
                    "rel": "self"
                },
                {
                    "href": url,
                    "rel": "bookmark"
                }
            ]
        }
    }
        
    return d

@app.route('/v2/compute/servers', methods = [ 'POST' ] )
def compute_servers():
    compute_request = unmarshal(request)
    if "server" in compute_request and "name" in compute_request["server"]:
        name = compute_request["server"]["name"]
        resp = get_server(name)
    else:
        resp = {}
    return gen_response(resp)

def delete_compute_server(compute_id):
    lxc_stop(compute_id)
    lxc_wait(compute_id, 'STOPPED')
    lxc_destroy(compute_id)

#--- Compute - Single compute info
@app.route('/v2/compute/servers/<string:compute_id>', methods = [ 'GET', 'DELETE' ])
def get_compute_servers(compute_id):
    if request.method == 'DELETE':
        print('asking to delete {0}'.format(compute_id))
        delete_compute_server(compute_id)
        return gen_response({})
    else:
        print('{0} compute_id'.format(compute_id))
        return gen_response(create_compute_server(compute_id))

def get_id_and_links(datadict):
    return dict([ (k, datadict[k]) for k in ('id', 'links') if k in datadict ])

def name_to_compute_id(cid):
    return cid

def get_ip_from_lease_file(compute_id):
    name = name_to_compute_id(compute_id)
    filename = "/var/lib/lxc/{0}/rootfs/var/lib/dhcp/dhclient.eth0.leases".format(name)
    lease_contents = []
    ip = None
    try:
        with open(filename) as f:
            lease_contents = f.readlines()
    except IOError as e:
        pass

    for lease in lease_contents:
        match = re.search(r'fixed-address ([^;]+);', lease)
        if match:
            ip = match.groups()[0]
    return ip

def get_compute_addresses(compute_id):
    ip = get_ip_from_lease_file(compute_id)
    d = { "private": [], "public": [] }
    if ip:
        d["private"].append({ "addr": ip, "version": 4 })
        d["public"].append({ "addr": ip, "version": 4 })
    return d

def create_compute_server(compute_id):
    flavor = get_id_and_links(get_flavor())
    image = get_id_and_links(get_images()['images'][0])
    #compute_id = "893c7791-f1df-4c3d-8383-3caae9656c62"
    url = base_url + '/compute/servers/' + compute_id
    d = {
        "server": {
            "accessIPv4": "",
            "accessIPv6": "",
            "addresses": get_compute_addresses(compute_id),
            "created": "2012-08-20T21:11:09Z",
            "flavor": flavor,
            "hostId": compute_id, #"65201c14a29663e06d0748e561207d998b343e1d164bfa0aafa9c45d",
            "id": compute_id,
            "image": image,
            "links": [
                {
                    "href": url,
                    "rel": "self"
                },
                {
                    "href": url,
                    "rel": "bookmark"
                }
            ],
            "metadata": {},
            "name": compute_id,
            "progress": 0,
            "status": "UNKNOWN",
            "tenant_id": "openstack",
            "updated": "2012-08-20T21:11:09Z",
            "user_id": "fake"
        }
    }
    return d

#--- Compute - Detail
@app.route('/v2/compute/servers/detail')
def compute_servers_detail():
    return gen_response(get_servers_detail())

# all in thread list should be pending
# then lxc_list runing should be running
# unless they don't have an ip, then they are also pending
def get_pending_from_threads():
    threads = [t.name for t in threading.enumerate()]
    return [ t.split(':')[1] for t in threads if "starting:" in t]

def get_servers_detail():
    pending_nodes = get_pending_from_threads()
    running_lxc_nodes = lxc_list()[0]
    running_with_ip = [ n for n in running_lxc_nodes if get_ip_from_lease_file(n) ]
    # pending nodes are from threads and running w/o ip
    print 'running w/o ip: {0}'.format(set(running_lxc_nodes).difference(running_with_ip))
    pending_nodes = set(pending_nodes).union(set(running_lxc_nodes).difference(running_with_ip))
    print "pending: {0}".format(pending_nodes)
    print "running: {0}".format(running_with_ip) 
    print "all: {0}".format(set(running_with_ip).union(pending_nodes)) 
    servers = []
    for n in pending_nodes:
        cn = create_compute_server(n)['server']
        cn["status"] = "BUILD"
        servers.append(cn)
    if len(pending_nodes) > 0:
        import time
        time.sleep(10)
    for n in running_with_ip:
        cn = create_compute_server(n)['server']
        cn["status"] = "ACTIVE"
        servers.append(cn)
    d = { 'servers': servers }
    return d

def lxc_list():
    """ returns tuple of started, running node list"""
    out = subprocess.check_output('lxc-list')
    node_info = re.split(r'(?:RUNNING|FROZEN|STOPPED)\n', out)
    types = \
        [ n.strip().split('\n') if len(n.strip()) else [] for n in node_info ]
    _, r, f, s = \
        [ [ n.strip() for n in t ] for t in types ]
    return (r, s)

#--- Compute - Flavors
def get_images():
    d = {
    "images": [
        {
            "created": "2011-01-01T01:02:03Z",
            "id": "70a599e0-31e7-49b7-b260-868f441e862b",
            "links": [
                {
                    "href": "http://openstack.example.com/v2/openstack/images/70a599e0-31e7-49b7-b260-868f441e862b",
                    "rel": "self"
                },
                {
                    "href": "http://openstack.example.com/openstack/images/70a599e0-31e7-49b7-b260-868f441e862b",
                    "rel": "bookmark"
                },
                {
                    "href": "http://glance.openstack.example.com/openstack/images/70a599e0-31e7-49b7-b260-868f441e862b",
                    "rel": "alternate",
                    "type": "application/vnd.openstack.image"
                }
            ],
            "metadata": {
                "architecture": "x86_64",
                "auto_disk_config": "True",
                "kernel_id": "nokernel",
                "ramdisk_id": "nokernel"
            },
            "minDisk": 0,
            "minRam": 0,
            "name": "fakeimage7",
            "progress": 100,
            "status": "ACTIVE",
            "updated": "2011-01-01T01:02:03Z"
        }]}
    return d

@app.route('/v2/compute/images/detail')
def images():
    return gen_response(get_images())

#--- Compute - Flavors
@app.route('/v2/compute/flavors/detail')
def flavors():
    return gen_response(get_flavors())

def get_flavors():
    d = { 'flavors' : [ get_flavor() ]  }
    return d

def get_ram():
    return psutil.virtual_memory().available / (1024**2)

def get_vcpus():
    return psutil.NUM_CPUS

def get_disk():
    return psutil.disk_usage('/').free / (1024**3)

def get_flavor():
    flavor_id = 1
    url = base_url + '/compute/flavors/' + str(flavor_id)
    # bookmark link does not have version in it..
    d = {
        "disk": get_disk(),
        "id": str(flavor_id),
        "links": [
            {
                "href": url,
                "rel": "self"
            },
            {
                "href": url,
                "rel": "bookmark"
            }
        ],
        "name": "default.lxc",
        "ram": get_ram(),
        "vcpus": get_vcpus()
    }
    return d

if __name__ == '__main__':
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000 )
