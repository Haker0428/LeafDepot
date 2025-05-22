import zxing
import cv2
import numpy as np

def preprocess_barcode_image(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)  # Convert to grayscale
    img = cv2.GaussianBlur(img, (3, 3), 0)  # Reduce noise
    _, img = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)  # Binarize
    return img

img = preprocess_barcode_image("BarCodeDemo_04.png")
cv2.imwrite("processed_barcode.jpg", img)  # Save for debugging

# Now try decoding
reader = zxing.BarCodeReader()

barcode = reader.decode("processed_barcode.jpg")

# barcode = reader.decode("BarCodeDemo_06.jpg")  # Use decode() instead of read()
if barcode:
    print("Barcode Type:", barcode.format)
    print("Barcode Data:", barcode.raw)
else:
    print("No barcode found or could not decode.")