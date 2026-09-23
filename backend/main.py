"""
main.py - FastAPI backend for a2d-pdf
Converts PDF pages to images using pymupdf, sends to Gemini, returns pixel-perfect HTML
Same approach as process.py which produces superb results.
"""

import json
import os
import tempfile
import time
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
import fitz

app = FastAPI(title="a2d-pdf API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://a2dpdf.web.app", "http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL = "gemini-3.6-flash"

EXTRACT_PROMPT = """You are an expert document digitization specialist.
You are given scanned page images of a document.

Your task is to produce a PIXEL-PERFECT digital HTML replica of this document.

Rules:
1. Read every single word, number, date, code, checkbox, stamp, signature line exactly as it appears
2. Identify the document structure:
   - HEADINGS: bold/large text -> use <h1>, <h2>, <h3> with matching font size and weight
   - PARAGRAPHS: body text -> use <p>
   - TABLES: any grid/tabular data -> use proper <table><thead><tbody><tr><td> with borders
   - FORMS: labeled fields like "Name: ___" -> use styled form layout with label + value
   - LISTS: bullet points or numbered items -> use <ul>/<ol><li>
   - CHECKBOXES: ☐ or □ -> use ☑ or ☐ unicode characters
   - LOGOS/HEADERS: company names at top -> style as document header
   - FOOTERS: page numbers, disclaimers at bottom -> style as footer
   - DIVIDERS: horizontal lines -> use <hr>
   - TWO-COLUMN LAYOUTS: side by side content -> use HTML table for layout
3. Apply styles that match the original document appearance:
   - Font sizes proportional to original
   - Bold where original is bold
   - Spacing and margins that match the layout
   - Table borders matching original
4. DO NOT use position:absolute or position:fixed
5. Use normal document flow - block elements stacked top to bottom
6. Preserve ALL content - do not skip, summarize or redact anything

Return a JSON object with exactly these fields:
{
  "title": "document title or type",
  "document_type": "e.g. Medical Record, Invoice, Contract",
  "pages": [
    {
      "page_number": 1,
      "html_content": "<complete HTML for this page with inline styles>"
    }
  ],
  "summary": {
    "total_pages": 0,
    "key_info": {}
  }
}

Return ONLY valid JSON. No markdown fences. No explanation."""


HTML_WRAPPER = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: Arial, sans-serif;
    font-size: 12pt;
    color: #000;
    background: #e0e0e0;
    padding: 20px;
  }}
  .document-wrapper {{ max-width: 870px; margin: 0 auto; }}
  .meta-bar {{
    background: #1a3a5c;
    color: #fff;
    padding: 10px 20px;
    margin-bottom: 20px;
    font-size: 10pt;
    display: flex;
    justify-content: space-between;
  }}
  .page {{
    background: #fff;
    padding: 60px 70px;
    margin-bottom: 30px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    min-height: 1100px;
    position: relative;
  }}
  .page-break-label {{
    text-align: center;
    color: #888;
    font-size: 10pt;
    margin: 10px 0;
    letter-spacing: 1px;
  }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  table th, table td {{ border: 1px solid #000; padding: 6px 8px; text-align: left; font-size: 10pt; }}
  table th {{ background: #f0f0f0; font-weight: bold; }}
  .field-row {{ display: flex; gap: 4px; margin: 3px 0; font-size: 11pt; }}
  .field-label {{ font-weight: bold; min-width: 140px; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 10px 0; }}
  .section-box {{ border: 1px solid #000; padding: 10px; margin: 8px 0; }}
  h1 {{ font-size: 16pt; margin: 10px 0; }}
  h2 {{ font-size: 14pt; margin: 8px 0; }}
  h3 {{ font-size: 12pt; margin: 6px 0; }}
  p  {{ margin: 6px 0; line-height: 1.5; }}
  ul, ol {{ margin: 6px 0 6px 20px; }}
  li {{ margin: 3px 0; line-height: 1.4; }}
  hr {{ border: none; border-top: 1px solid #000; margin: 10px 0; }}
  @media print {{
    body {{ background: #fff; padding: 0; }}
    .meta-bar {{ display: none; }}
    .page {{
      box-shadow: none;
      margin: 0;
      padding: 40px 50px;
      min-height: auto;
      page-break-after: always;
    }}
    .page-break-label {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="document-wrapper">
  <div class="meta-bar">
    <span><strong>{title}</strong> &nbsp;|&nbsp; {doc_type}</span>
    <span>Pages: {page_count} &nbsp;|&nbsp; Generated: {generated}</span>
  </div>
  {pages_html}
</div>
</body>
</html>"""


def pdf_to_images(pdf_path: str) -> list:
    """Convert each PDF page to PNG bytes using pymupdf."""
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def build_html(data: dict, filename: str) -> str:
    pages = data.get("pages", [])
    pages_html = ""
    for p in pages:
        num     = p.get("page_number", "?")
        content = p.get("html_content", "")
        pages_html += f'<div class="page" id="page-{num}">\n{content}\n</div>\n'
        pages_html += f'<div class="page-break-label">— Page {num} of {len(pages)} —</div>\n'

    return HTML_WRAPPER.format(
        title      = data.get("title", filename),
        doc_type   = data.get("document_type", "Document"),
        page_count = len(pages),
        generated  = datetime.now().strftime("%Y-%m-%d %H:%M"),
        pages_html = pages_html
    )


@app.get("/")
def root():
    return {"status": "ok", "service": "a2d-pdf API"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/digitalize")
async def digitalize(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # Convert PDF pages to images
        images = pdf_to_images(tmp_path)

        # Build parts: all page images + prompt
        parts = []
        for img_bytes in images:
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
        parts.append(EXTRACT_PROMPT)

        # Send to Gemini with retry on 503
        client = genai.Client(api_key=API_KEY)
        response = None
        for attempt in range(3):
            try:
                chat = client.chats.create(model=MODEL)
                response = chat.send_message(
                    parts,
                    config=types.GenerateContentConfig(
                        temperature=0,
                        max_output_tokens=65536,
                    )
                )
                break
            except Exception as e:
                if attempt < 2 and "503" in str(e):
                    time.sleep(5)
                    continue
                raise

        raw = response.text.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0].strip()

        data = json.loads(raw)
        filename = Path(file.filename).stem
        html = build_html(data, filename)

        return JSONResponse({
            "success": True,
            "title": data.get("title", filename),
            "document_type": data.get("document_type", "Document"),
            "total_pages": len(data.get("pages", [])),
            "html": html,
            "summary": data.get("summary", {})
        })

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse Gemini response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
