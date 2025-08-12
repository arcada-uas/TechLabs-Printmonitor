import subprocess
import logging
from datetime import datetime
import sys
from pathlib import Path
import time
import atexit
import json
import asyncio

# install dependencies from requirements.txt
try:
    subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True)
except:
    print("Installation of requirements failed. You may need to install them manuially.")

from flask import Flask, render_template, jsonify, send_from_directory, Response
from requests.auth import HTTPDigestAuth
from camera import Camera
import requests
import xml.etree.ElementTree as ElementTree

from config import config, get_server_ip, get_context

content_manager = subprocess.Popen(["python3", "content_manager.py"])

debug = True # False

class CustomFormatter(logging.Formatter):
    # Define color codes
    BLUE = "\033[94m"
    RED = "\033[91m"
    RESET = "\033[0m"

    def format(self, record):
        log_fmt = self._style._fmt
        if record.levelno == logging.INFO:
            log_fmt = self.BLUE + self._style._fmt + self.RESET
        elif record.levelno == logging.ERROR:
            log_fmt = self.RED + self._style._fmt + self.RESET
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

logging.basicConfig(level=logging.DEBUG if debug else logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

# Apply custom formatter
for handler in logging.getLogger().handlers:
    handler.setFormatter(CustomFormatter(handler.formatter._style._fmt))


logger = logging.getLogger(__name__)

camera = Camera()

app = Flask(__name__)


@app.after_request
def add_header(r):
    """ Disable caching of image, allow CORS for infoscreen """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Expires"] = "0"
    r.headers["Access-Control-Allow-Origin"] = "*"
    return r


@app.route("/")
def entrypoint():
    context = get_context(_debug=debug)
    logger.debug('Rendering index with context:', context)
    return render_template("index.html", **context)


@app.route("/images/last")
def last_image():
    if debug:
        return send_from_directory("images", "arcada-logo.png")
    else:
        camera.capture_and_save()
        return send_from_directory("images", "last.png")


@app.route('/api/data')
def get_data():
    printer_url = 'http://' + config.printer_ip
    api_url_status = printer_url + config.printer_status
    api_url_job = printer_url + config.printer_job
    auth = HTTPDigestAuth(config.username, config.password)
    # Talk to api to get printer status
    try:
        resJSON = requests.get(api_url_status, auth=auth, timeout=10).json()

        logger.debug(api_url_status)
        logger.debug(resJSON)

        if resJSON['printer']['state'] == 'PRINTING':
            # Second api to get filename of current job
            res2Json = requests.get(api_url_job, auth=auth, timeout=10).json()
            # Store display_name of job in response from first API
            resJSON['display_name'] = res2Json['file']['display_name']

        return jsonify(resJSON)
    # printer is not reachable
    except requests.exceptions.RequestException as e:
        logger.error('Could not connect to printer:', e)
        return jsonify({'error': 'Could not connect to printer',
                        'printer': {'state': 'IDLE', 'display_name': 'Could not connect to printer'}})

def fetch_and_save_arbs_data(url, filename):
    try:
        response = requests.get(url)
        response.raise_for_status()
        if len(response.content) > 10:
            with open(filename, 'wb') as _f:
                _f.write(response.content)
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f'Request to {url} failed:', e)
        return False

# function that checks if booking is today
def is_booking_for_today(booking):
    end_date = booking.attrib['end'].split('T')[0]
    current_date = datetime.today().strftime("%Y-%m-%d")
    return end_date == current_date

def fetch_and_save_assets_data(url, filename):
    try:
        response = requests.get(url)
        logger.debug(f'Fetching data from {url}')
        logger.debug(f'Response: {response.content}')

        response.raise_for_status()
        assets_root = ElementTree.fromstring(response.content)
        bookings = assets_root.findall('booking')
        logger.debug(f'Found {len(bookings)} bookings')
        def filter_rooms(rooms_str):
            # <booking id="2705388" title="Vårdandets grunder" room="E383, F365, B323" start="2024-09-04T12:30:00+03:00" ...
            # <booking id="2750788" title="Digital Commerce " room="F363, F365" start="2024-09-05T13:00:00+03:00"
            rooms = rooms_str.split(',')
            filtered_rooms = [room.strip() for room in rooms if room.strip().startswith('F3')]
            return (filtered_rooms[0] if len(filtered_rooms)>0 else None)

        for booking in bookings:
            # filter out bookings that are not today
            if not is_booking_for_today(booking):
                assets_root.remove(booking)
                continue

            filtered_rooms = filter_rooms(booking.attrib['room'])
            if filtered_rooms:
                booking.attrib['room'] = filtered_rooms
            else:
                assets_root.remove(booking)

        ElementTree.ElementTree(assets_root).write(filename, encoding='utf-8', xml_declaration=True)
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f'Request to {url} failed:', e)
        return False

def get_room_id(element, config):
    if 'room_id' in element.attrib:
        return element.attrib['room_id']
    room = element.attrib.get('room')
    if room in config.rooms:
        return str(config.rooms.index(room) + 1)
    return None

def parse_bookings_from_xml(filename):
    try:
        tree = ElementTree.parse(filename)
        root = tree.getroot()
        bookings = []
        for child in root:
            if child.tag == "booking":
                if not is_booking_for_today(child):
                    room_id = get_room_id(child, config)
                    bookings.append({'title': 'No bookings today', 'room_id': room_id})
                else:
                    bookings.append(child.attrib)
        return bookings
    except Exception as ex:
        logger.error(ex)
        return [{'error': 'no bookings available'}]

@app.route('/api/arbs')
def get_bookings():
    filename = 'arbs.xml'

    if not fetch_and_save_arbs_data(config.arbs_url, filename):
        if not fetch_and_save_assets_data(config.assets_url, filename):
            logger.error('Failed to fetch data from both ARBS and assets URLs, falling back to cached data.')

    return jsonify(parse_bookings_from_xml(filename))


@app.route('/video_feed')
def video_feed():
    # return video feed or a static image
    try:
        return Response(camera.generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        logger.error('Could not get video feed:', e)
        return send_from_directory("images", "arcada-logo.png")

# https://stackoverflow.com/questions/320232/ensuring-subprocesses-are-dead-on-exiting-python-program
def cleanup():
    timeout_sec = 5
    p_sec = 0
    for second in range(timeout_sec):
        if content_manager.poll() == None:
            time.sleep(1)
            p_sec += 1
    if p_sec >= timeout_sec:
        content_manager.kill() # supported from python 2.6
    print('cleaned up!')

if __name__ == "__main__":
    logger.info(f'Servers public IP4: {get_server_ip()}:{config.server_port}')
    port = config.server_port_debug if debug else config.server_port
    app.run(host="0.0.0.0", port=port, debug=False)
    atexit.register(cleanup)