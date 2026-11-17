"""Loopback PDF processing. Office conversion uses a temporary job directory."""
import base64
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pypdf import PdfReader, PdfWriter
from pdf_extra import ExtraInputError, inspect_pdf, edit_or_redact, office_pdf, translate_pdf,render_plain_pdf
from pdf_advanced import pdfa_convert, text_lines, replace_text, sign_pdf, verify_signatures
from pdf_layout import get_paragraphs,reflow_paragraph
from pdf_web import html_to_pdf,summarize_pdf
from pdf_workflows import run_workflow

LIMIT = 25 * 1024 * 1024
ORIGINS = {"http://127.0.0.1:8766", "http://localhost:8766"}
SLOTS = threading.BoundedSemaphore(2)

class PdfInputError(ValueError):
    pass

def repair_pdf(data):
    if not data.startswith(b"%PDF-") or len(data) > LIMIT:
        raise PdfInputError("25MB 이하의 PDF 파일을 선택하세요.")
    import pymupdf
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise PdfInputError("이 PDF는 읽을 수 없어 복구하지 못했습니다.")
    with doc:
        if doc.is_encrypted:
            raise PdfInputError("암호화된 파일은 먼저 잠금해제하세요.")
        if not 1 <= len(doc) <= 2000:
            raise PdfInputError("1~2,000쪽의 PDF를 지원합니다.")
        return doc.tobytes(garbage=4, deflate=True)

def convert_to_powerpoint(data):
    if not data.startswith(b"%PDF-") or len(data) > LIMIT:
        raise PdfInputError("25MB 이하의 PDF 파일을 선택하세요.")
    import pymupdf
    from pptx import Presentation
    from pptx.util import Inches
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        if doc.is_encrypted:
            raise PdfInputError("암호화된 파일은 먼저 잠금해제하세요.")
        if not 1 <= len(doc) <= 100:
            raise PdfInputError("PowerPoint 변환은 1~100쪽의 PDF를 지원합니다.")
        presentation = Presentation()
        ratio = doc[0].rect.height / doc[0].rect.width
        presentation.slide_width = Inches(10)
        presentation.slide_height = Inches(min(56, max(1, 10 * ratio)))
        for page in doc:
            rect = page.rect
            scale = min(2, 2400 / max(rect.width, rect.height))
            image = io.BytesIO(page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes("png"))
            fit = min(presentation.slide_width / rect.width, presentation.slide_height / rect.height)
            width, height = int(rect.width * fit), int(rect.height * fit)
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            slide.shapes.add_picture(image, int((presentation.slide_width-width)/2), int((presentation.slide_height-height)/2), width=width, height=height)
        output = io.BytesIO()
        presentation.save(output)
        return output.getvalue()

def convert_to_word(data):
    if not data.startswith(b"%PDF-") or len(data) > LIMIT:
        raise PdfInputError("25MB 이하의 PDF 파일을 선택하세요.")
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise PdfInputError("암호화된 파일은 먼저 잠금해제하세요.")
    if len(reader.pages) > 200:
        raise PdfInputError("Word 변환은 200쪽 이하의 PDF를 지원합니다.")
    if not any((page.extract_text() or "").strip() for page in reader.pages):
        raise PdfInputError("텍스트가 없는 스캔 문서입니다. OCR PDF로 변환한 뒤 다시 시도하세요.")
    from pdf2docx import Converter
    output = io.BytesIO()
    converter = Converter(stream=data)
    try:
        converter.convert(output, multi_processing=False)
    finally:
        converter.close()
    from docx import Document
    document = Document(io.BytesIO(output.getvalue()))
    converted_text = "".join(p.text for p in document.paragraphs) + "".join(c.text for t in document.tables for row in t.rows for c in row.cells)
    if not converted_text.strip():
        # Layout converters can ignore the invisible text layer produced by OCR.
        document = Document()
        document.core_properties.comments = "text-only-ocr-fallback"
        import re
        for index, page in enumerate(reader.pages):
            if index:
                document.add_page_break()
            text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", page.extract_text() or "")
            for line in text.splitlines():
                document.add_paragraph(line)
        output = io.BytesIO()
        document.save(output)
    return output.getvalue()

def process_pdf(operation, data, password=""):
    if operation not in {"protect", "unlock", "compress"}:
        raise ValueError("지원하지 않는 PDF 작업입니다.")
    if not data.startswith(b"%PDF-") or len(data) > LIMIT:
        raise ValueError("25MB 이하의 PDF 파일을 선택하세요.")
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        if operation != "unlock":
            raise ValueError("암호화된 파일은 먼저 잠금해제하세요.")
        if not reader.decrypt(password):
            raise ValueError("PDF 암호가 올바르지 않습니다.")
    elif operation == "unlock":
        raise ValueError("이 PDF에는 열기 암호가 설정되어 있지 않습니다.")
    if len(reader.pages) > 2000:
        raise ValueError("한 번에 2,000쪽 이하의 PDF를 처리하세요.")
    writer = PdfWriter(clone_from=reader)
    if operation == "protect":
        if not password or len(password.encode("utf-8")) > 127:
            raise ValueError("암호는 UTF-8 기준 1~127바이트로 입력하세요.")
        writer.encrypt(password, algorithm="AES-256")
    if operation == "compress":
        for page in writer.pages:
            page.compress_content_streams(level=9)
        writer.compress_identical_objects()
    stream = io.BytesIO()
    writer.write(stream)
    output = stream.getvalue()
    # Already optimized documents should never become larger.
    return data if operation == "compress" and len(output) >= len(data) else output

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def allowed(self):
        return self.headers.get("Origin") in ORIGINS or not self.headers.get("Origin")

    def respond(self, status, data, content_type="application/json; charset=utf-8", extra=None):
        self.send_response(status)
        origin = self.headers.get("Origin")
        if origin in ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Expose-Headers", "X-Conversion-Mode, X-Layout-Result, X-HTML-Blocked")
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def error(self, status, message):
        self.respond(status, json.dumps({"error": message}, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        if not self.allowed():
            return self.error(403, "허용되지 않은 웹사이트입니다.")
        self.respond(204, b"", extra={"Access-Control-Allow-Methods": "POST, GET, OPTIONS", "Access-Control-Allow-Headers": "Content-Type"})

    def do_GET(self):
        if not self.allowed():
            return self.error(403, "허용되지 않은 웹사이트입니다.")
        if self.path != "/health":
            return self.error(404, "경로를 찾을 수 없습니다.")
        self.respond(200, b'{"service":"local-pdf","ready":true}')

    def do_POST(self):
        if not self.allowed():
            return self.error(403, "허용되지 않은 웹사이트입니다.")
        if self.path not in {"/api/pdf/protect", "/api/pdf/unlock", "/api/pdf/compress", "/api/pdf/word", "/api/pdf/powerpoint", "/api/pdf/repair", "/api/pdf/inspect", "/api/pdf/edit", "/api/pdf/redact", "/api/pdf/translate", "/api/pdf/office", "/api/pdf/pdfa", "/api/pdf/text-lines", "/api/pdf/replace-text", "/api/pdf/sign", "/api/pdf/verify-signatures", "/api/pdf/paragraphs", "/api/pdf/reflow", "/api/pdf/html", "/api/pdf/summarize", "/api/pdf/summary-pdf", "/api/pdf/workflow"}:
            return self.error(404, "경로를 찾을 수 없습니다.")
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.error(415, "JSON 요청이 필요합니다.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.error(400, "잘못된 요청입니다.")
        if length <= 0 or length > 36 * 1024 * 1024:
            return self.error(413, "25MB 이하의 PDF 파일을 선택하세요.")
        if not SLOTS.acquire(blocking=False):
            return self.error(429, "다른 PDF를 처리하고 있습니다. 잠시 후 다시 시도하세요.")
        try:
            payload = json.loads(self.rfile.read(length))
            password = payload.get("password", "")
            if not isinstance(password, str):
                raise ValueError("암호 형식을 확인하세요.")
            data = base64.b64decode(payload["pdf"], validate=True)
            operation = self.path.rsplit("/", 1)[1]
            if operation == "inspect":
                self.respond(200, json.dumps(inspect_pdf(data)).encode())
            elif operation == "workflow":
                self.respond(200,run_workflow(data,payload.get("steps"),process_pdf,pdfa_convert),"application/pdf")
            elif operation == "paragraphs":
                self.respond(200,json.dumps(get_paragraphs(data,payload.get("page",1)),ensure_ascii=False).encode())
            elif operation == "reflow":
                result,report=reflow_paragraph(data,payload)
                self.respond(200,result,"application/pdf",{"X-Layout-Result":json.dumps(report,ensure_ascii=True)})
            elif operation == "html":
                result,report=html_to_pdf(payload)
                self.respond(200,result,"application/pdf",{"X-HTML-Blocked":str(report["blockedRequests"])})
            elif operation == "summary-pdf":
                summary=payload.get("summary","")
                if not isinstance(summary,str) or not summary.strip() or len(summary)>30000:
                    raise ExtraInputError("요약 텍스트는 1~30,000자로 입력하세요.")
                self.respond(200,render_plain_pdf(summary),"application/pdf")
            elif operation == "summarize":
                self.respond(200,json.dumps(summarize_pdf(data,payload),ensure_ascii=False).encode())
            elif operation == "pdfa":
                result, validation = pdfa_convert(data)
                self.respond(200, result, "application/pdf", {"X-PDFA-Validated": "PDF/A-2b; veraPDF; failedRules=0"})
            elif operation == "text-lines":
                self.respond(200, json.dumps(text_lines(data, payload.get("page", 1)), ensure_ascii=False).encode())
            elif operation == "replace-text":
                self.respond(200, replace_text(data, payload), "application/pdf")
            elif operation == "sign":
                self.respond(200, sign_pdf(data, payload), "application/pdf")
            elif operation == "verify-signatures":
                self.respond(200, json.dumps(verify_signatures(data), ensure_ascii=False).encode())
            elif operation == "office":
                self.respond(200, office_pdf(data, payload.get("extension")), "application/pdf")
            elif operation == "translate":
                self.respond(200, translate_pdf(data, payload.get("target")), "application/pdf")
            elif operation in {"edit", "redact"}:
                self.respond(200, edit_or_redact(data, payload, operation == "redact"), "application/pdf")
            elif operation == "repair":
                result = repair_pdf(data)
                self.respond(200, result, "application/pdf")
            elif operation == "powerpoint":
                result = convert_to_powerpoint(data)
                self.respond(200, result, "application/vnd.openxmlformats-officedocument.presentationml.presentation")
            elif operation == "word":
                result = convert_to_word(data)
                from docx import Document
                mode = "text-only" if Document(io.BytesIO(result)).core_properties.comments == "text-only-ocr-fallback" else "layout"
                self.respond(200, result, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", {"X-Conversion-Mode": mode})
            else:
                result = process_pdf(operation, data, password)
                self.respond(200, result, "application/pdf")
        except (PdfInputError, ExtraInputError) as error:
            self.error(400, str(error))
        except (ValueError, KeyError, TypeError):
            self.error(400, "파일 형식·크기 또는 암호가 올바르지 않습니다.")
        except Exception:
            self.error(400, "PDF를 처리하지 못했습니다. 손상 여부와 암호를 확인하세요.")
        finally:
            SLOTS.release()

if __name__ == "__main__":
    print("Local PDF service: http://127.0.0.1:8767", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8767), Handler).serve_forever()
