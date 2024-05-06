import cv2
import datetime

class Camera:
	def __init__(self,video_source=0):
		self.video_source = video_source
		self.camera = cv2.VideoCapture(self.video_source)
	
	def capture_and_save(self):
		v, frame = self.camera.read()
		font = cv2.FONT_HERSHEY_SIMPLEX; position = (10,30);	
		fontScale = 1;	fontColor = (255,255,255);	lineType = 2
		timestamp = datetime.datetime.now().isoformat().split(".")[0]
		cv2.putText(frame, timestamp, position, font, fontScale, fontColor, lineType)
		cv2.imwrite("images/last.png", frame)
		return frame
		
	def release(self):
		self.camera.release()

	