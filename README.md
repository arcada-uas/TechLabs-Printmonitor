# Flask-opencv webcam and print-data infoscreen #
This software is intended to be run on any machine on the same LAN as a PrusaLink enabled printer.
The use case is a simple data consolidator for an infoscreen for a 3D printer.
The infoscreen (front-end) displays a webcam feed and some data on the current print job.

# Components #
It contains a flask webserver, an opencv webcam frame capturer, a prusalink data fetcher and a front-end for displaying the data from the different sources.
On top of the camera implementation, the server script also grabs data from a prusa mk4 printer on the same local network to display the current status of the printer as well as some additional information about the print job.

## Requirements ##
You need flask for the server to work
You need opencv2 for the camera to work
`pip install flask opencv-python`

> [!NOTE]
> In `server.py` you need to replace the password `YOURSECRETHERE` to the password generated on your printer.
> Also note that the IPs of the server computer (where you run this script) and the IP of your printer probably differs from the ones in the code here.

## Running ##
The service only runs on python3
`python3 server.py`

After starting the server you can access the front end on:
http://localhost:5000

## Structure ##
The latest image is saved in `/images/last.png`
The template file for the front-end is inside `templates/index.html`

## Endpoints ##
The flask server hosts the following enpoints:
`/` - The root endpoint hosts the front-end for the print monitor
`/api/data/`- Captures data from the prusalink (the printer)
`/images/last` - Captures an image and stores it on disk

## The front-end ##
The front end shows the latest image from the webcam, and the following info on the print
Status: Printing/Finished
Job: Name of job
Progress: % of print
Remaining: minutes remaining
Nozzle temp: in C
Bed temp: in C
Z-height: in mm

The front-end refreshes every 10 seconds, fetching both a new image and info about the job.
