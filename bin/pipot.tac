from twisted.application import service, internet
from twisted.internet import ssl

import config_parser
import serverCollector
import database

# Create application
application = service.Application("pipotd")
# Load settings file
config = config_parser.parse_config('config')
# Init DB
db = database.create_session(config['DATABASE_URI'])
# General collector
collector_inst = serverCollector.ServerCollector(db)

# Create service that'll hold all services
multi_service = service.MultiService()
# SSL listener for incoming collector messages
ssl_service = internet.SSLServer(
    config.get('COLLECTOR_SSL_PORT', 12345),
    serverCollector.SSLFactory(collector_inst),
    ssl.DefaultOpenSSLContextFactory(
        config.get('SSL_KEY', 'cert/pipot.key'),
        config.get('SSL_CERT', 'cert/pipot.crt')
    ),
    interface=config.get('SERVER_IP', '0.0.0.0')
)
# UDP listener for incoming collector messages
udp_service = internet.UDPServer(
    config.get('COLLECTOR_UDP_PORT', 12346),
    serverCollector.UDPCollector(collector_inst),
    interface=config.get('SERVER_IP', '0.0.0.0')
)

# Assign service parents
ssl_service.setServiceParent(multi_service)
udp_service.setServiceParent(multi_service)
multi_service.setServiceParent(application)
