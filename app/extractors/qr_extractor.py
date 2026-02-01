from qreader import QReader
import requests
import cv2
import numpy as np
import requests
qr = cv2.cvtColor(cv2.imread(filename="qr.jpg"),cv2.COLOR_BGR2RGB)
qreader = QReader()
detected_text = qreader.detect_and_decode(image=qr)
print(detected_text)