import os
from dotenv import load_dotenv
import json
import datetime
from pathlib import Path

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
        self.content_url = os.getenv('USER_CONTENT_URL')

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

def get_featured_content(featured_content = None): # TODO: Add features, content
    # TODO: Choose which content to display
    # TODO: Display selected content
    
    if featured_content:
        div_open ="<div class='feat-cont'> <h1>Todays meme:</h1>"
        img_src_open = "<img src='"
        img_src_close = "' style='margin-top: 20px; max-width: 600px; max-height: 350px; height: auto; width: auto;'>"
        div_close = "</div>"

        return div_open + img_src_open + featured_content + img_src_close + div_close
    else:    
        with open('templates/featuredContent.html', 'r') as file:
            return file.read()

def select_meme():
    try:
        json_data_file = open("static/content/meme_data.json", "r")
        json_data = json.load(json_data_file)
        json_data_file.close()
        featured_dict = {}
        approved_dict = {}
        for key, item in enumerate(json_data):
            if item['featured']:
                featured_dict[key] = item
            elif item['approved']:
                approved_dict[key] = item
        datestring_today = str(datetime.datetime.now()).split()[0]
        oldest_rerun = datetime.datetime.strptime(datestring_today, "%Y-%m-%d")
        oldest_rerun_index = None
        chosen_filename = None
        if len(featured_dict) > 0:
            for key, item in featured_dict.items():
                feature_date = item['featured']
                if feature_date != "pending":
                    if feature_date == datestring_today:
                        chosen_filename = item['filename']
                        print("Today's feature features on!")
                        return "static/content/images/" + chosen_filename
                    else:
                        last_featured_date = datetime.datetime.strptime(item["featured"], "%Y-%m-%d")
                        if last_featured_date < oldest_rerun:
                            oldest_rerun = last_featured_date
                            oldest_rerun_index = key
                else:
                    json_data[key]['featured'] = datestring_today
                    json_data_file = open("static/content/meme_data.json", "w")
                    json.dump(json_data, json_data_file, indent=4)
                    json_data_file.close()
                    filepath = Path("static/content/images/" + json_data[key]['filename'])
                    if filepath.exists() and not chosen_filename:
                        chosen_filename = json_data[key]['filename']
                        print("Here's a new feature!")
                        return "static/content/images/" + chosen_filename
        if len(approved_dict) > 0: # TODO: TEST!
            for key, item in approved_dict.items():
                json_data[key]['featured'] = datestring_today
                json_data_file = open("static/content/meme_data.json", "w")
                json.dump(json_data, json_data_file, indent=4)
                json_data_file.close()
                print("This one should be OK.")
                return "static/content/images/" + approved_dict[key]['filename']
        json_data[oldest_rerun_index]['featured'] = datestring_today
        print("An old favorite returns")
        return "static/content/images/" + json_data[oldest_rerun_index]['filename']
    except(FileNotFoundError):
        print("No meme data found.")
    return None

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

    featured_content = select_meme()
    # TODO: add image to featured content
    

    context = {
        'server': server,
        'rooms': config.rooms,
        'featuredContent': get_featured_content(featured_content),
        'image_url': f"{server}{image_api}",
        'printer_status_url': f"{server}{data_api}",
        'arbs_url': f"{server}{arbs_api}",
        'background_image': f'{server}/images/FallbackPortrait1.png',
    }
    if _debug:
        print('context printer url ', context['printer_status_url'])
        #print(context)
    return context
