# install dependencies from requirements.txt
import subprocess
import logging
from datetime import datetime

subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True)

from flask import Flask, render_template, jsonify, send_from_directory, Response
from requests.auth import HTTPDigestAuth
from camera import Camera
import requests
import xml.etree.ElementTree as ElementTree
from config import config, get_server_ip, get_context


debug = False  # True
logging.basicConfig(level=logging.DEBUG if debug else logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

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

def fetch_and_save_assets_data(url, filename):
    try:
        response = requests.get(url)
        response.raise_for_status()
        assets_root = ElementTree.fromstring(response.content)
        bookings = assets_root.findall('booking')
        bookings = [booking for booking in bookings if booking.attrib['end'].split('T')[0] == datetime.today().strftime("%Y-%m-%d")
                    and booking.attrib['room'].startswith('F3')]
        assets_root.clear()
        for booking in bookings:
            assets_root.append(booking)
        ElementTree.ElementTree(assets_root).write(filename, encoding='utf-8', xml_declaration=True)
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f'Request to {url} failed:', e)
        return False

def parse_bookings_from_xml(filename):
    try:
        tree = ElementTree.parse(filename)
        root = tree.getroot()
        bookings = []
        for child in root:
            if child.tag == "booking":
                end_date = child.attrib['end'].split('T')[0]
                current_date = datetime.today().strftime("%Y-%m-%d")
                if not end_date == current_date:
                    bookings.append({'title': 'No bookings today', 'room_id': child.attrib['room_id']})
                else:
                    bookings.append(child.attrib)
        return bookings
    except Exception as ex:
        logger.error(ex)
        return [{'error': 'no bookings available'}]

@app.route('/api/arbs')
def get_bookings():
    arbs_url = config.arbs_url
    assets_url = config.assets_url
    filename = 'arbs.xml'

    if not fetch_and_save_arbs_data(arbs_url, filename):
        if not fetch_and_save_assets_data(assets_url, filename):
            logger.error('Failed to fetch data from both ARBS and assets URLs, falling back to cached data.')

    return jsonify(parse_bookings_from_xml(filename))


@app.route('/video_feed')
def video_feed():
    # return video feed
    return Response(camera.generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')



if __name__ == "__main__":
    logger.info(f'Servers public IP4: {get_server_ip()}:{config.server_port}')
    port = 5500 if debug else config.server_port
    app.run(host="0.0.0.0", port=port, debug=False)
