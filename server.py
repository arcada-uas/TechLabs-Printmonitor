# install dependencies from requirements.txt
import subprocess
from datetime import datetime

subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True)

import json
import socket
import netifaces as ni
from flask import Flask, render_template, jsonify, send_from_directory
from requests.auth import HTTPDigestAuth
from camera import Camera
import requests
import xml.etree.ElementTree as ElementTree

debug = False  # True
camera = Camera()

app = Flask(__name__)

# Load the credentials from the .env file
class ConfigLoader:
    def __init__(self, config_file):
        self.config_file = config_file
        self.credentials = {}

    def load_credentials(self):
        print('Loading credentials')
        with open(self.config_file, 'r') as file:
            for line in file:
                key, value = line.strip().split('=')
                self.credentials[key.strip()] = value.strip()

    def get(self, key):
        return self.credentials.get(key)


# Render the index.html template with the context
class TemplateRenderer:
    def __init__(self, context):
        print('Context:', context)
        self.context = context

    def render_index(self):
        if debug:
            print('Rendering index with context:', self.context)
        return render_template("index.html", **self.context)


def get_featured_content():
    with open('templates/featuredContent.html', 'r') as file:
        return file.read()


# Get the IP address of the server
def get_server_ip():
    # print(f'Servers local IP: {socket.gethostbyname(socket.gethostname())}')
    # Get all interfaces
    for interface in ni.interfaces():
        # Get addresses for each interface
        addresses = ni.ifaddresses(interface)
        # Check for IPv4 addresses
        if ni.AF_INET in addresses:
            ipv4_info = addresses[ni.AF_INET][0]
            ip_address = ipv4_info['addr']
            if ip_address != "127.0.0.1":
                return ip_address
    return "127.0.0.1"


# Get the context for the index.html template
def get_context(_debug=False):
    server_ip = get_server_ip()
    server_port = config_loader.get('SERVER_PORT')
    if _debug:
        server_port = 5500
    image_api = '/images/last'
    data_api = '/api/data'
    arbs_api = '/api/arbs'
    server = f'http://{server_ip}:{server_port}'

    context = {
        'server': server,
        'rooms': json.dumps(["F363", "F364", "F365", "F367", "F368", "F370"]),
        'featuredContent': get_featured_content(),
        'image_url': f"{server}{image_api}",
        'printer_status_url': f"{server}{data_api}",
        'arbs_url': f"{server}{arbs_api}",
        'background_image': f'{server}/images/FallbackPortrait1.png',
    }
    if _debug:
        print('context printer url ', context['printer_status_url'])
    return context


@app.after_request
def add_header(r):
    """ Disable caching of image, allow CORS for infoscreen """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Expires"] = "0"
    r.headers["Access-Control-Allow-Origin"] = "*"
    return r


@app.route("/")
def entrypoint():
    return renderer.render_index()


@app.route("/images/last")
def last_image():
    if debug:
        return send_from_directory("images", "arcada-logo.png")
    else:
        camera.capture_and_save()
        return send_from_directory("images", "last.png")


@app.route('/api/data')
def get_data():
    # Define the authentication credentials
    username = config_loader.get('USERNAME')
    password = config_loader.get('PASSWORD')
    printer_ip = config_loader.get('PRINTER_IP')

    api_url = 'http://' + printer_ip + '/api/v1/status'  # Printer IP
    # Talk to api to get printer status
    try:
        response = requests.get(api_url, auth=HTTPDigestAuth(username, password), timeout=10)
        resJSON = response.json()

        if debug:
            print(api_url)
            print(resJSON)

        if resJSON['printer']['state'] == 'PRINTING':
            # Second api to get filename of current job
            api_url = 'http://' + printer_ip + '/api/v1/job'  # Printer IP
            response = requests.get(api_url, auth=HTTPDigestAuth(username, password), timeout=10)
            res2Json = response.json()
            # Store display_name of job in response from first API
            resJSON['display_name'] = res2Json['file']['display_name']
        return jsonify(resJSON)
    # If printer is not reachable
    except requests.exceptions.RequestException as e:
        print('Error:', e)
        return jsonify({'error': 'Could not connect to printer',
                        'printer': {'state': 'IDLE', 'display_name': 'Could not connect to printer'}})


@app.route('/api/arbs')
def get_bookings():
    arbs_url = 'https://famnen.arcada.fi/arbs/infotv/block_bookings.php?wing=F&floor=3'
    try:
        response = requests.get(arbs_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        if len(response.content) > 10:
            with open('arbs.xml', 'wb') as _f:
                _f.write(response.content)
    except requests.exceptions.RequestException as e:
        print('Request to famnen.arcada.fi failed, trying assets.arcada.fi:', e)
        try:
            response = requests.get('https://assets.arcada.fi/infowall/data/bookings.xml')
            response.raise_for_status()
            assets_root = ElementTree.fromstring(response.content)
            bookings = assets_root.findall('booking')
            # remove all bookings that are not for today and where the room_id does not start with F3
            bookings = [booking for booking in bookings if booking.attrib['end'].split('T')[0] == datetime.today().strftime("%Y-%m-%d")
                        and booking.attrib['room'].startswith('F3')]
            assets_root.clear()
            for booking in bookings:
                assets_root.append(booking)
            ElementTree.ElementTree(assets_root).write('arbs.xml', encoding='utf-8', xml_declaration=True)
        except requests.exceptions.RequestException as e1:
            print('Request to assets.arcada.fi failed, falling back to cached arbs.xml:', e1)

    try:
        tree = ElementTree.parse('arbs.xml')  # create element tree object
        root = tree.getroot()
        bookings = []
        for child in root:
            if child.tag == "booking":
                print(child.attrib)
                # get the end date of the booking which is in format end="2024-08-29T12:00:00+03:00"
                end_date = child.attrib['end'].split('T')[0]
                current_date = datetime.today().strftime("%Y-%m-%d")
                if not end_date == current_date:
                    bookings.append({'title': 'No bookings today', 'room_id': child.attrib['room_id']})
                else:
                    bookings.append(child.attrib)  # list of dicts is suitable json
            else:
                continue
        return jsonify(bookings)
    except Exception as ex:
        print(ex)
        return jsonify({'error': 'no bookings available'})


def gen(_camera):
    # Starting stream
    while True:
        frame = _camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/png\r\n\r\n' + frame + b'\r\n')


if __name__ == "__main__":
    print('main')
    # Load the credentials from the .env file
    config_loader = ConfigLoader('.env')
    config_loader.load_credentials()
    # Initialize the TemplateRenderer with the context
    renderer = TemplateRenderer(get_context(_debug=debug))
    print(f'Servers public IP4: {get_server_ip()}:{config_loader.get("SERVER_PORT")}')
    port = 5500 if debug else config_loader.get('SERVER_PORT')
    # Redirect stdout and stderr to log file
    # if not debug:
    #     with open(config_loader.get('LOG_FILE'), 'a') as f:
    #         sys.stdout = f
    #         sys.stderr = f

    app.run(host="0.0.0.0", port=port, debug=False)
