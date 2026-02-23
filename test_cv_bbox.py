import cv2
import numpy as np
import fitz  # PyMuPDF

pdf_path = "/Users/seemantshankar/Downloads/WagonR-Brochure.pdf"
page_num = 5

doc = fitz.open(pdf_path)
page = doc.load_page(page_num - 1)
# Render page to an image
pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 2x zoom for better resolution
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)

if pix.n == 4: # RGBA
    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
elif pix.n == 3: # RGB
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

thresh, img_bin = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
img_bin = 255 - img_bin 

kernel_length = np.array(img).shape[1]//80
 
verticle_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_length))
hori_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_length, 1))
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

img_temp1 = cv2.erode(img_bin, verticle_kernel, iterations=3)
verticle_lines_img = cv2.dilate(img_temp1, verticle_kernel, iterations=3)

img_temp2 = cv2.erode(img_bin, hori_kernel, iterations=3)
horizontal_lines_img = cv2.dilate(img_temp2, hori_kernel, iterations=3)

alpha = 0.5
beta = 1.0 - alpha
img_final_bin = cv2.addWeighted(verticle_lines_img, alpha, horizontal_lines_img, beta, 0.0)
img_final_bin = cv2.erode(~img_final_bin, kernel, iterations=2)
(thresh, img_final_bin) = cv2.threshold(img_final_bin, 128,255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

contours, hierarchy = cv2.findContours(img_final_bin, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

print(f"Found {len(contours)} contours")

table_bboxes = []
for c in contours:
    x, y, w, h = cv2.boundingRect(c)
    if (w > 500 and h > 200) and (w < img.shape[1]*0.95 or h < img.shape[0]*0.95):
        table_bboxes.append((x, y, w, h))

print(f"Found {len(table_bboxes)} potential table bounding boxes:")
for i, b in enumerate(table_bboxes):
    x, y, w, h = b
    print(f"Table {i}: (x={x}, y={y}, w={w}, h={h})")
    # Crop the image using the bounding box
    table_roi = img[y:y+h, x:x+w]
    cv2.imwrite(f"table_{i}.png", table_roi)
    print(f"Saved table_{i}.png")
