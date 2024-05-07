from flask import Flask, render_template, jsonify, send_from_directory
from pathlib import Path
from camera import Camera
import requests
import xml.etree.ElementTree as ET 

camera = Camera()
printer_ip = 'http://192.168.1.34'

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
	return render_template("index.html")

@app.route("/images/last")
def last_image():
	camera.capture_and_save()
	return send_from_directory("images","last.png")

@app.route('/api/data')
def get_data():
    # Define the authentication credentials
    username = 'maker'
    password = 'YOURSECRETHERE'

    # Fetch printer status
    api_url = printer_ip + '/api/v1/status'  # Printer IP
    response = requests.get(api_url, auth=requests.auth.HTTPDigestAuth(username, password))
    resJSON = response.json()
	
    #print(resJSON)
    if (resJSON['printer']['state'] == 'PRINTING'):
		# Second api to get filename of current job 
        api_url = printer_ip + '/api/v1/job'  # Printer IP
        response = requests.get(api_url, auth=requests.auth.HTTPDigestAuth(username, password))
        res2Json = response.json()
        # Store display_name of job in response from first API
        resJSON['display_name'] = res2Json['file']['display_name'] 
    return jsonify(resJSON)

@app.route('/api/arbs')
def get_bookings():
  arbs_url = 'https://famnen.arcada.fi/arbs/infotv/block_bookings.php?wing=F&floor=3'
  response = requests.get(arbs_url)
  with open('arbs.xml', 'wb') as f: 
    f.write(response.content)  
  tree = ET.parse('arbs.xml') # create element tree object  
  root = tree.getroot() # get root element 
  bookings = [] 
  for child in root:
    if (child.tag == "booking"):
      # print(child.attrib)
      bookings.append(child.attrib) # list of dicts is suitable json
    elif (child.tag == "room"):
      continue
    else:
      bookings.append({'Bookings':'No bookings today'})
  return jsonify(bookings)

def gen(camera):
	# Starting stream
	while True:
		frame = camera.get_frame()
		yield (b'--frame\r\n'
			   b'Content-Type: image/png\r\n\r\n' + frame + b'\r\n')

if __name__=="__main__":
  app.run(host="0.0.0.0",debug=False)
