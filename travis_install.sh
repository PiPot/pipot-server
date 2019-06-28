echo "-------------------------------"
echo "|   Installing dependencies   |"
echo "-------------------------------"
echo ""
echo "* Updating package list        "
apt-get update
echo "* Installing nginx, python & pip      "

apt-get -q -y install dnsutils nginx python python-dev python-pip

if [[ "$OSTYPE" == "linux-gnu" ]]; then
    apt-get -q -y install build-essential libffi-dev libssl-dev
fi
if [ ! -f /etc/init.d/mysql* ]; then
    echo "* Installing MySQL (root password will be empty!)"
    DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server
fi
echo "* Update setuptools            "
pip install --upgrade setuptools
echo "* Installing pip dependencies"
pip install nose2 mock ipaddress enum34 cryptography idna sqlalchemy twisted pyopenssl flask-sqlalchemy flask passlib pymysql service_identity pycrypto flask-wtf netifaces gunicorn