cache=0
filename=/vagrant/apt-cache
if [ -s $filename ]; then
    cacheraddress=$(cat $filename)
    ping -c1 $cacheraddress
    if [ $? -eq 0 ]; then
        echo using apt-cacher box $cacheraddress
        echo 'Acquire::http::Proxy "http://'$cacheraddress':3142";' > /etc/apt/apt.conf.d/01proxy
        cache=1
    fi
fi
if [ $cache -eq 0 ]; then echo "not using cache"; fi
