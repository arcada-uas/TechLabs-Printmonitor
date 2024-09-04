import os
from dotenv import load_dotenv
import json


class Config:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        self.debug = os.getenv('DEBUG', 'False').lower() == 'true'
        self.server_port = int(os.getenv('SERVER_PORT', 5000))
        self.server_port_debug = int(os.getenv('SERVER_PORT_DEBUG', 5300))
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD')
        self.printer_ip = os.getenv('PRINTER_IP')
        self.printer_status = os.getenv('PRINTER_STATUS_ENDPOINT', f'http://{self.printer_ip}/api/v1/status')
        self.printer_job = os.getenv('PRINTER_JOB_ENDPOINT', f'http://{self.printer_ip}/api/v1/job')
        self.log_file = os.getenv('LOG_FILE', 'app.log')

        # Load rooms from environment variable as JSON
        rooms_env = os.getenv('ROOMS', '[]')
        self.rooms = json.loads(rooms_env)

        # Strip quotes from URLs if present
        self.arbs_url = os.getenv('ARBS_URL', '').strip('"')
        self.assets_url = os.getenv('ASSETS_URL', '').strip('"')

    def get(self, key, default=None):
        return getattr(self, key, default)


config = Config()


def get_server_ip():
    import netifaces as ni
    for interface in ni.interfaces():
        addresses = ni.ifaddresses(interface)
        if ni.AF_INET in addresses:
            ipv4_info = addresses[ni.AF_INET][0]
            ip_address = ipv4_info['addr']
            if ip_address != "127.0.0.1":
                return ip_address
    return "127.0.0.1"


# Get the context for the index.html template
def get_context(_debug=False):
    server_ip = get_server_ip()
    # server_port = config_loader.get('SERVER_PORT')
    server_port = config.server_port
    if _debug:
        server_port = 5300
    image_api = '/images/last'
    data_api = '/api/data'
    arbs_api = '/api/arbs'
    server = f'http://{server_ip}:{server_port}'
    def get_featured_content():
        with open('templates/featuredContent.html', 'r') as file:
            return file.read()

    context = {
        'server': server,
        'rooms': config.rooms,
        'featuredContent': get_featured_content(),
        'image_url': f"{server}{image_api}",
        'printer_status_url': f"{server}{data_api}",
        'arbs_url': f"{server}{arbs_api}",
        'background_image': f'{server}/images/FallbackPortrait1.png',
    }
    if _debug:
        print('context printer url ', context['printer_status_url'])
        print(context)
    return context
