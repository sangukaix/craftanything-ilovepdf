import io
import re
import unittest
import os
import zipfile
import pymupdf
from pypdf import PdfReader
from pdf_extra import office_pdf, edit_or_redact, translate_pdf, ExtraInputError

def sample_pdf():
    doc=pymupdf.open();page=doc.new_page()
    page.insert_text((50,80),"SECRET123",fontsize=14)
    page.insert_text((50,140),"PUBLIC content",fontsize=14)
    page.add_text_annot((60,70),"SECRET comment")
    page.insert_link({"kind":pymupdf.LINK_URI,"from":pymupdf.Rect(50,60,200,90),"uri":"https://example.com/secret"})
    widget=pymupdf.Widget();widget.field_name="Student";widget.field_type=pymupdf.PDF_WIDGET_TYPE_TEXT;widget.rect=pymupdf.Rect(50,180,250,210);page.add_widget(widget)
    widget=pymupdf.Widget();widget.field_name="Agree";widget.field_type=pymupdf.PDF_WIDGET_TYPE_CHECKBOX;widget.rect=pymupdf.Rect(50,230,70,250);page.add_widget(widget)
    output=doc.tobytes();doc.close();return output

def office_samples():
    from docx import Document
    from pptx import Presentation
    from pptx.util import Inches
    import xlsxwriter
    d=Document();d.add_paragraph("Office Word 0010");d.add_paragraph("한글 문서 변환 시험");b=io.BytesIO();d.save(b)
    word=b.getvalue();b=io.BytesIO()
    w=xlsxwriter.Workbook(b,{"in_memory":True});s=w.add_worksheet();s.set_column(0,0,26);s.set_column(1,1,12);s.write_row(0,0,["Office Excel","Count"]);s.write_row(1,0,["Test item",42]);w.close();excel=b.getvalue()
    p=Presentation();slide=p.slides.add_slide(p.slide_layouts[6]);slide.shapes.add_textbox(Inches(1),Inches(1),Inches(7),Inches(1)).text="Office PowerPoint 123";b=io.BytesIO();p.save(b)
    return {"docx":word,"xlsx":excel,"pptx":b.getvalue()}

class Tests(unittest.TestCase):
    def test_office_three_formats(self):
        for ext,source in office_samples().items():
            with self.subTest(extension=ext):
                output=office_pdf(source,ext);reader=PdfReader(io.BytesIO(output));text="\n".join(p.extract_text() for p in reader.pages)
                self.assertIn({"docx":"Office Word","xlsx":"Office Excel","pptx":"Office PowerPoint"}[ext],text)

    def test_edit_korean(self):
        output=edit_or_redact(sample_pdf(),{"operations":[{"page":1,"x":50,"y":300,"width":300,"height":70,"text":"추가한 한국어 문장","size":16}]})
        text=PdfReader(io.BytesIO(output)).pages[0].extract_text();self.assertIn("추가한 한국어 문장",re.sub(r"\s+"," ",text));self.assertIn("PUBLIC",text)

    def test_permanent_redaction(self):
        output=edit_or_redact(sample_pdf(),{"operations":[{"page":1,"x":45,"y":55,"width":180,"height":45}]},True)
        with pymupdf.open(stream=output,filetype="pdf") as doc:
            self.assertNotIn("SECRET123",doc[0].get_text());self.assertIn("PUBLIC",doc[0].get_text());self.assertFalse(list(doc[0].annots() or []));self.assertFalse(doc[0].get_links());self.assertEqual(len(list(doc[0].widgets() or [])),2)
            pix=doc[0].get_pixmap();self.assertEqual(pix.pixel(80,75),(0,0,0))

    def test_bounds_and_office_type(self):
        with self.assertRaises(ExtraInputError):edit_or_redact(sample_pdf(),{"operations":[{"page":1,"x":-5,"y":0,"width":10,"height":10,"text":"x"}]})
        with self.assertRaises(ExtraInputError):office_pdf(b"not an office file","xlsx")

    def test_external_office_relationship(self):
        source=io.BytesIO()
        with zipfile.ZipFile(source,"w") as archive:
            archive.writestr("word/document.xml","<document/>")
            archive.writestr("word/_rels/document.xml.rels","<Relationships><Relationship TargetMode = 'External' Target='https://example.com'/></Relationships>")
        with self.assertRaisesRegex(ExtraInputError,"외부"):
            office_pdf(source.getvalue(),"docx")

    def test_redaction_removes_image_pixels_and_field(self):
        from PIL import Image
        image=io.BytesIO();Image.new("RGB",(100,100),(255,0,0)).save(image,format="PNG")
        doc=pymupdf.open();page=doc.new_page(width=300,height=300)
        page.insert_image(pymupdf.Rect(50,50,150,150),stream=image.getvalue())
        widget=pymupdf.Widget();widget.field_name="Secret field";widget.field_value="secret value";widget.field_type=pymupdf.PDF_WIDGET_TYPE_TEXT;widget.rect=pymupdf.Rect(75,75,125,100);page.add_widget(widget)
        output=edit_or_redact(doc.tobytes(),{"operations":[{"page":1,"x":70,"y":70,"width":60,"height":60}]},True);doc.close()
        with pymupdf.open(stream=output,filetype="pdf") as result:
            self.assertFalse(list(result[0].widgets() or []))
            # Check the embedded image itself, not just the black overlay.
            images=result[0].get_images(full=True);self.assertTrue(images)
            pixels=pymupdf.Pixmap(result,images[0][0])
            self.assertEqual(pixels.pixel(5,5),(255,0,0))
            self.assertNotEqual(pixels.pixel(50,50),(255,0,0))

    @unittest.skipIf(os.environ.get('PDF_SKIP_AI_TESTS')=='1','Local AI explicitly disabled for this run')
    def test_local_translation(self):
        doc=pymupdf.open();doc.new_page().insert_text((50,80),"Hello. This is a local translation test.");data=doc.tobytes();doc.close()
        output=translate_pdf(data,"ko");text=PdfReader(io.BytesIO(output)).pages[0].extract_text();self.assertRegex(text,r"[가-힣]");self.assertNotIn("This is a local translation test",text)

if __name__=="__main__":unittest.main()
