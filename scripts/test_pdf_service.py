import base64
import io
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
from pdf_service import Handler, process_pdf, convert_to_word, convert_to_powerpoint, repair_pdf

def fixture():
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=500)
    content = DecodedStreamObject()
    content.set_data(b"q\nQ\n" * 10000)
    page[NameObject("/Contents")] = writer._add_object(content)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()

class Tests(unittest.TestCase):
    def test_repair_invalid_cross_reference(self):
        import pymupdf
        doc = pymupdf.open()
        doc.new_page().insert_text((50, 80), "Repair test content")
        data = doc.tobytes()
        damaged = data[:data.rfind(b"startxref")] + b"startxref\n0\n%%EOF\n"
        result = PdfReader(io.BytesIO(repair_pdf(damaged)))
        self.assertIn("Repair test content", result.pages[0].extract_text())
        with self.assertRaises(ValueError):
            repair_pdf(b"%PDF-not-a-real-document")
        doc.close()

    def test_word_and_ocr_text_fallback(self):
        import pymupdf
        from docx import Document
        for invisible in (False, True):
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((50, 80), "Word conversion 0010", render_mode=3 if invisible else 0)
            data = convert_to_word(doc.tobytes())
            converted = Document(io.BytesIO(data))
            text = "".join(p.text for p in converted.paragraphs)
            self.assertIn("Word conversion 0010", text)
            if invisible:
                self.assertEqual(converted.core_properties.comments, "text-only-ocr-fallback")
            doc.close()

    def test_powerpoint_page_images(self):
        import pymupdf
        from pptx import Presentation
        doc = pymupdf.open()
        doc.new_page(width=400, height=600).insert_text((50, 80), "First page")
        doc.new_page(width=600, height=400).insert_text((50, 80), "Second page")
        result = Presentation(io.BytesIO(convert_to_powerpoint(doc.tobytes())))
        self.assertEqual(len(result.slides), 2)
        for index, slide in enumerate(result.slides):
            self.assertEqual(len(slide.shapes), 1)
            expected = doc[index].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False).tobytes("png")
            self.assertEqual(slide.shapes[0].image.blob, expected)
        doc.close()

    def test_protect_unlock(self):
        source = fixture()
        encrypted = process_pdf("protect", source, "test-only-123")
        reader = PdfReader(io.BytesIO(encrypted))
        self.assertTrue(reader.is_encrypted)
        self.assertEqual(reader.trailer["/Encrypt"]["/R"], 6)
        with self.assertRaises(ValueError):
            process_pdf("unlock", encrypted, "wrong")
        unlocked = process_pdf("unlock", encrypted, "test-only-123")
        reader = PdfReader(io.BytesIO(unlocked))
        self.assertFalse(reader.is_encrypted)
        self.assertEqual(len(reader.pages), 1)
        self.assertEqual(reader.pages[0].get_contents().get_data(), PdfReader(io.BytesIO(source)).pages[0].get_contents().get_data())

    def test_lossless_compression(self):
        source = fixture()
        result = process_pdf("compress", source)
        self.assertLess(len(result), len(source))
        self.assertEqual(PdfReader(io.BytesIO(result)).pages[0].get_contents().get_data(), PdfReader(io.BytesIO(source)).pages[0].get_contents().get_data())
        self.assertLessEqual(len(process_pdf("compress", result)), len(result))

    def test_http_and_origin(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/pdf/protect"
            body = json.dumps({"pdf": base64.b64encode(fixture()).decode(), "password": "test-only-123"}).encode()
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "Origin": "http://127.0.0.1:8766"})
            with urllib.request.urlopen(req) as response:
                self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://127.0.0.1:8766")
                self.assertTrue(PdfReader(io.BytesIO(response.read())).is_encrypted)
            req.add_header("Origin", "https://untrusted.example")
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(req)
            self.assertEqual(error.exception.code, 403)
            error.exception.close()
        finally:
            server.shutdown()
            server.server_close()

if __name__ == "__main__":
    unittest.main()
