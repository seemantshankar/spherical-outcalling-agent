# pyre-ignore-all-errors
import logging
import pandas as pd
import json
import cv2
import numpy as np
import fitz
from PIL import Image
from openai import OpenAI
import os
import base64
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class TableAdapter:
    def __init__(self, df, page):
        self.df = df
        self.page = page

def parse_tables_from_pdf(filepath: str, pages: str = "all"):
    """
    Extracts tables using Camelot, utilizing local layout parsing without LLMs.
    Focuses parsing specifically to the pages indicated to contain tables.
    """
    try:
        import camelot
        tables = camelot.read_pdf(filepath, pages=pages, flavor='lattice') # type: ignore
        
        valid_lattice = False
        if tables.n > 0:
            for t in tables:
                if not t.df.empty and len(t.df.columns) > 1:
                    # Check if data columns (index > 0) have any content
                    data_cols = t.df.iloc[:, 1:]
                    data_non_empty = data_cols.astype(str).replace([r'^\s*$', r'(?i)^nan$', r'(?i)^none$'], '', regex=True).apply(lambda x: x.str.strip() != '').sum().sum()
                    if data_non_empty > 15:
                        valid_lattice = True
                        break

        if valid_lattice:
            logger.info(f"Camelot extracted {tables.n} tables using lattice from {filepath} on pages {pages}")
            return tables
            
        logger.info(f"Lattice flavor found 0 tables, falling back to 'stream' on pages {pages}")
        stream_tables = camelot.read_pdf(filepath, pages=pages, flavor='stream') # type: ignore
        
        # Check if stream tables are junk (mostly empty strings)
        valid_stream = False
        if stream_tables.n > 0:
            for t in stream_tables:
                if not t.df.empty and len(t.df.columns) > 1:
                    data_cols = t.df.iloc[:, 1:]
                    data_non_empty = data_cols.astype(str).replace([r'^\s*$', r'(?i)^nan$', r'(?i)^none$'], '', regex=True).apply(lambda x: x.str.strip() != '').sum().sum()
                    if data_non_empty > 15:
                        valid_stream = True
                        break
                    
        if valid_stream:
            logger.info(f"Camelot extracted {stream_tables.n} tables using stream")
            return stream_tables
            
        logger.warning("Camelot stream extracted junk/empty tables, executing Vision LLM fallback")
        vision_tables = parse_tables_with_vision(filepath, pages)
        if vision_tables:
            return vision_tables
            
        logger.warning("Vision LLM extraction failed or returned 0 tables, falling back to pdfplumber")
        
        import pdfplumber
        plumber_tables = []
        page_nums = [int(p) for p in pages.split(',')] if pages != "all" else None
        
        with pdfplumber.open(filepath) as pdf:
            pdf_pages = [pdf.pages[i-1] for i in page_nums] if page_nums else pdf.pages
            for page in pdf_pages:
                extracted = page.extract_tables()
                for t in extracted:
                    df = pd.DataFrame(t)
                    df = df.fillna('')
                    if not df.empty and len(df.columns) > 1:
                         plumber_tables.append(TableAdapter(df, page.page_number))
                         
        logger.info(f"pdfplumber extracted {len(plumber_tables)} tables")
        return plumber_tables
        
    except ImportError as e:
        logger.error(f"Dependencies (camelot, cv2, etc.) not installed properly: {e}")
        return []
    except Exception as e:
        logger.error(f"Camelot parsing failed for {filepath}: {e}", exc_info=True)
        return []


def parse_tables_with_vision(filepath: str, pages: str):
    """
    Uses PyMuPDF to render the page, OpenCV to find table strict bounding boxes, 
    and Gemini 1.5 Pro to extract structured JSON data.
    """
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    except Exception as e:
        logger.error(f"Could not initialize OpenRouter client. Ensure OPENROUTER_API_KEY is set: {e}")
        return []

    result_tables = []
    page_nums = [int(p) for p in pages.split(',')] if pages != "all" else [1]
    
    doc = fitz.open(filepath)
    for p_num in page_nums:
        try:
            page = doc.load_page(p_num - 1)
            # High-res rendering to ensure checkmarks are visible
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh, img_bin = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            img_bin = 255 - img_bin

            kernel_length = np.array(img).shape[1] // 80
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
            (thresh, img_final_bin) = cv2.threshold(img_final_bin, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

            contours, _ = cv2.findContours(img_final_bin, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            table_bboxes = []
            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                # Filter out extreme noise and the entire page boundary
                if (w > 500 and h > 200) and (w < img.shape[1]*0.95 or h < img.shape[0]*0.95):
                    table_bboxes.append((x, y, w, h))

            # Sort bounding boxes top to bottom
            table_bboxes = sorted(table_bboxes, key=lambda b: b[1])
            
            # De-duplicate bounding boxes that perfectly overlap
            filtered_bboxes = []
            for b in table_bboxes:
                is_dup = False
                for fb in filtered_bboxes:
                    if abs(b[0] - fb[0]) < 10 and abs(b[1] - fb[1]) < 10:
                        is_dup = True
                        break
                if not is_dup:
                    filtered_bboxes.append(b)

            logger.info(f"Vision LLM found {len(filtered_bboxes)} table bboxes on page {p_num}")

            for idx, b in enumerate(filtered_bboxes):
                x, y, w, h = b
                table_roi = img[y:y+h, x:x+w]
                
                # Convert cv2 image back to PIL, then base64 for OpenAI Vision API
                _, buffer = cv2.imencode('.png', table_roi)
                base64_image = base64.b64encode(buffer).decode('utf-8')
                
                prompt = (
                    "Extract the data from this image of a table. "
                    "Return a JSON array of arrays, representing the table. "
                    "CRITICAL INSTRUCTIONS FOR NORMALIZE RESTRUCTURING: "
                    "1. If multiple vehicle trims are grouped in a single column header (e.g. 'Trim A, Trim B, Trim C'), you MUST split them into completely separate, individual columns (e.g. 'Trim A', 'Trim B', 'Trim C'). "
                    "2. The FIRST array in your response MUST be a header row starting exactly with ['Feature', 'Best Effort Category', <EACH INDIVIDUAL TRIM as its own separate column>]. "
                    "3. For the 'Best Effort Category' column, deduce a 1-2 word semantic category for each feature (e.g. 'Safety', 'Efficiency', 'Exterior', 'Infotainment'). You must infer this based on the feature name. "
                    "4. For the data rows, distribute the cell values into the correct newly separated trim columns. If a value applied to a grouped column, duplicate it for all the individual trims in that group. "
                    "5. TRIM-SPECIFIC FEATURES: If a feature explicitly mentions a trim (e.g. 'Kerb Weight Trim A' or 'Trim B AGS'), place its value ONLY in the corresponding trim column(s) and use '-' for the other unrelated trims. Then simplify the feature name by removing the trim (e.g. 'Kerb Weight'). "
                    "6. MULTI-VALUE PRESERVATION: If a single cell contains multiple values for different configurations (e.g. '32 (Petrol) / 60 (Water equivalent)', '1,000 / 1,200'), YOU MUST return the full string exactly as shown. Do NOT pick just one. If there is a slash or newline, keep the separation. Include all units and parenthetical notes (e.g. '(Petrol)', '(CNG)', '(Water equivalent)').\n"
                    "7. Replace checkmarks ('✓') with 'Standard' and crosses ('x') or hyphens ('-') with '-'. "
                    "Do NOT include markdown formatting or backticks around the json, just return the raw JSON array."
                )

                try:
                    vision_model = os.environ.get("VISION_LLM_MODEL", "google/gemini-1.5-pro")
                    response = client.chat.completions.create(
                        model=vision_model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ]
                    )
                    
                    raw_text = response.choices[0].message.content.strip()
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:-3]
                    elif raw_text.startswith("```"):
                        raw_text = raw_text[3:-3]
                        
                    data = json.loads(raw_text)
                    if data and len(data) > 1:
                        df = pd.DataFrame(data[1:], columns=data[0])
                        result_tables.append(TableAdapter(df, p_num))
                        logger.info(f"Successfully extracted Vision table with {len(df)} rows.")
                except Exception as eval_e:
                    logger.error(f"Gemini evaluation failed for crop {idx}: {eval_e}")

        except Exception as page_e:
            logger.error(f"Vision Pipeline failed on page {p_num}: {page_e}")
            
    return result_tables

