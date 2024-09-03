# Flask-opencv webcam and print-data infoscreen #
This software is intended to be run on any machine on the same LAN as a PrusaLink enabled printer.
The use case is a simple data consolidator for an infoscreen for a 3D printer.
The infoscreen (front-end) displays a webcam feed and some data on the current print job.

## Components ##
It contains a flask webserver, an opencv webcam frame capturer, 
a prusalink data fetcher and a front-end for displaying the data from the different sources.
On top of the camera implementation, the server script also grabs data 
from a prusa mk4 printer on the same local network to display the current status 
of the printer as well as some additional information about the print job.

## Requirements ##
You need flask for the server to work
You need opencv2 for the camera to work
`pip install flask opencv-python`

> [!NOTE]
> You need to provide environment for `server.py` in a file `.env`:
> ```
> USERNAME=maker
> PASSWORD=YOUR_PRINTER_PASSWORD
> PRINTER_IP=YOUR_PRINTER_IP 
> SERVER_PORT=5000
> PRINTER_STATUS_ENDPOINT=/api/v1/status
> PRINTER_JOB_ENDPOINT=/api/v1/job
> PRINTER_NAME=prusamk4.example.net
> LOG_FILE=logs/server.log
> ROOMS=["F363", "F364", "F365", "F367", "F368", "F370"]
> ARBS_URL="https://..."
> ASSETS_URL="https://.../bookings.xml"
>```
> Also note that the IP of the server computer (where you run this script) is intended to be detected 
> and injected automatically into the front-end.


## Running ##
The service only runs on python3
`nohup python3 server.py &`
and you'll find the output in `nohup.out`

After starting the server you can access the front end on:
http://YOUR_SERVER_IP:5000

## Structure ##
The latest image is saved in `/images/last.png`
The template file for the front-end is inside `templates/index.html`

## Endpoints ##
The flask server hosts the following enpoints:
- `/` - The root endpoint hosts the front-end for the print monitor
- `/api/data`- Captures data from the prusalink (the printer)
- `/images/last` - Captures an image and stores it on disk
- `/api/arbs` - Fetches the latest bookings from `https://famnen.arcada.fi/arbs/infotv/block_bookings.php?wing=F&floor=3`

## The front-end ##
The front end shows the latest image from the webcam, and the following info on the print:
```
Status: Printing/Finished
Job: Name of job
Progress: % of print
Remaining: minutes remaining
Nozzle temp: in C
Bed temp: in C
Z-height: in mm
```
The front-end refreshes every 20 seconds, fetching both a new image and info about the job.

Featured content (the information displayed when the printer is idle) is fetched once when the server starts. 
If you want to display dynamic content, you need to rewrite the server code.
