"""
main.py - FastAPI backend for a2d-pdf
Accepts a scanned PDF, sends to Gemini, returns pixel-perfect HTML replica
"""

import json
import time
import os
import tempfile
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types

app = FastAPI(title="a2d-pdf API", version="1.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://a2dpdf.web.app", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL   = "gemini-2.5-flash"

DIGITIZE_PROMPT = """You are an expert document digitization specialist.
You are given a scanned PDF document.

Your task is to produce a PIXEL-PERFECT digital HTML replica of this document.

Rules:
1. Read every single word, number, date, code, checkbox, stamp, signature line exactly as it appears
2. Identify the document structure:
   - HEADINGS: bold/large text -> use <h1>, <h2>, <h3> with matching font size and weight
   - PARAGRAPHS: body text -> use <p>
   - TABLES: any grid/tabular data -> use proper <table><thead><tbody><tr><td> with borders
   - FORMS: labeled fields like "Name: ___" -> use styled form layout with label + value
   - LISTS: bullet points or numbered items -> use <ul>/<ol><li>
   - CHECKBOXES: checked or unchecked -> use ☑ or ☐ unicode characters
   - LOGOS/HEADERS: company names at top -> style as document header
   - FOOTERS: page numbers, disclaimers at bottom -> style as footer
   - DIVIDERS: horizontal lines -> use <hr>
   - TWO-COLUMN LAYOUTS: side by side content -> use HTML tables for layout
3. Apply styles that match the original document appearance:
   - Font sizes proportional to original
   - Bold where original is bold
   - Spacing and margins that match the layout
   - Table borders matching original
4. Each page should be in its own <div class="page"> with a page-break-after style
5. Preserve ALL content - do not skip, summarize or redact anything
6. Use ONLY inline styles - no external CSS, no external images, no external URLs
7. Use only standard HTML elements compatible with print

Return a JSON object with exactly these fields:
{
  "title": "document title or type",
  "document_type": "e.g. Medical Record, Invoice, Contract",
  "pages": [
    {
      "page_number": 1,
      "html_content": "<complete HTML for this page with inline styles>",
      "raw_text": "plain text of this page"
    }
  ],
  "summary": {
    "total_pages": 0,
    "key_info": {}
  }
}

Return ONLY valid JSON. No markdown fences. No explanation."""


def build_html(data: dict) -> str:
    pages = data.get("pages", [])
    pages_html = ""
    for p in pages:
        num     = p.get("page_number", "?")
        content = p.get("html_content", p.get("raw_text", ""))
        pages_html += f'<div class="page" id="page-{num}">\n{content}\n</div>\n'

    title    = data.get("title", "Document")
    doc_type = data.get("document_type", "Document")
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: Arial, sans-serif;
    font-size: 12pt;
    color: #000;
    background: #e8e8e8;
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
    page-break-after: always;
  }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  table th, table td {{ border: 1px solid #000; padding: 6px 8px; font-size: 10pt; text-align: left; }}
  table th {{ background: #f0f0f0; font-weight: bold; }}
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
  }}
</style>
</head>
<body>
<div class="document-wrapper">
  <div class="meta-bar">
    <span><strong>{title}</strong> &nbsp;|&nbsp; {doc_type}</span>
    <span>Pages: {len(pages)} &nbsp;|&nbsp; Generated: {generated}</span>
  </div>
  {pages_html}
</div>
</body>
</html>"""


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

    if not API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    # Save uploaded file to temp
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        client = genai.Client(api_key=API_KEY)

        # Upload PDF to Gemini File API
        uploaded = client.files.upload(
            file=tmp_path,
            config=types.UploadFileConfig(mime_type="application/pdf")
        )

        # Wait for file to be ready
        for _ in range(10):
            file_info = client.files.get(name=uploaded.name)
            if file_info.state.name == "ACTIVE":
                break
            time.sleep(1)
        else:
            raise HTTPException(status_code=500, detail="File processing timeout")

        # Send to Gemini
        chat = client.chats.create(model=MODEL)
        response = chat.send_message(
            [uploaded, DIGITIZE_PROMPT],
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=65536,
            )
        )

        # Cleanup uploaded file
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw.rsplit("```", 1)[0].strip()

        data = json.loads(raw)
        html = build_html(data)

        return JSONResponse({
            "success": True,
            "title": data.get("title", "Document"),
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
