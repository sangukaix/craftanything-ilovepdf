import base64
import io
import json
import re
import unittest
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pymupdf
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from pdf_extra import ROOT, ExtraInputError
from pdf_advanced import pdfa_convert, validate_pdfa_path, text_lines, replace_text, sign_pdf, verify_signatures


def sample():
    doc=pymupdf.open();page=doc.new_page(width=595,height=842)
    page.draw_rect(pymupdf.Rect(35,40,270,110),color=(0,0,1),fill=(.9,.95,1))
    page.insert_text((50,80),"ORIGINAL TEXT",fontsize=14,color=(.7,0,0))
    page.insert_text((50,140),"PUBLIC preserved",fontsize=14)
    data=doc.tobytes();doc.close();return data


def test_certificate():
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"LOCAL TEST ONLY")])
    now=datetime.now(timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5))
          .not_valid_after(now+timedelta(days=1)).add_extension(x509.BasicConstraints(ca=False,path_length=None),True)
          .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=True,key_encipherment=False,
            data_encipherment=False,key_agreement=False,key_cert_sign=False,crl_sign=False,
            encipher_only=None,decipher_only=None),True).sign(key,hashes.SHA256()))
    return pkcs12.serialize_key_and_certificates(b"LOCAL TEST ONLY",key,cert,None,
        serialization.BestAvailableEncryption(b"local-test-only"))


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p12=test_certificate()

    def test_pdfa_validated_and_content_preserved(self):
        output,report=pdfa_convert(sample())
        self.assertTrue(report["compliant"]);self.assertEqual(report["failedRules"],0)
        with pymupdf.open(stream=output,filetype="pdf") as doc:
            self.assertEqual(len(doc),1);self.assertIn("ORIGINAL TEXT",doc[0].get_text())
            self.assertIn("PUBLIC preserved",doc[0].get_text())

    def test_plain_pdf_fails_pdfa_validation(self):
        work=ROOT/"work";work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pdfa-test-",dir=work) as temp:
            path=Path(temp)/"plain.pdf";path.write_bytes(sample())
            self.assertFalse(validate_pdfa_path(path)["compliant"])

    def test_korean_pdfa(self):
        from pdf_extra import render_plain_pdf
        output,report=pdfa_convert(render_plain_pdf("한국어 보관 문서 12345"))
        self.assertTrue(report["compliant"])
        with pymupdf.open(stream=output,filetype="pdf") as doc:
            self.assertIn("한국어",doc[0].get_text());self.assertIn("12345",doc[0].get_text())

    def test_original_is_removed_and_korean_replaced(self):
        original=sample();lines=text_lines(original,1)["lines"]
        line=next(line for line in lines if line["text"]=="ORIGINAL TEXT")
        output=replace_text(original,{"operations":[{"page":1,"id":line["id"],"original":line["text"],"text":"수정한 문장"}]})
        with pymupdf.open(stream=output,filetype="pdf") as doc:
            text=re.sub(r"\s+"," ",doc[0].get_text())
            self.assertNotIn("ORIGINAL TEXT",text);self.assertIn("수정한 문장",text);self.assertIn("PUBLIC preserved",text)
            # Background vector rectangle survives text-only replacement.
            self.assertTrue(doc[0].get_drawings())

    def test_stale_original_and_oversize_replacement_rejected(self):
        line=text_lines(sample(),1)["lines"][0]
        for old,new in [("wrong","new"),(line["text"],"X"*1000)]:
            with self.assertRaises(ExtraInputError):
                replace_text(sample(),{"operations":[{"page":1,"id":line["id"],"original":old,"text":new}]})

    def test_tight_leading_preserves_neighbouring_line(self):
        for spacing in (14,16,18):
            with self.subTest(spacing=spacing):
                doc=pymupdf.open();page=doc.new_page();page.insert_text((50,80),"First line",fontsize=14)
                page.insert_text((50,80+spacing),"Second line",fontsize=14);source=doc.tobytes();doc.close()
                line=text_lines(source,1)["lines"][0]
                output=replace_text(source,{"operations":[{"page":1,"id":line["id"],"original":line["text"],"text":"New text"}]})
                with pymupdf.open(stream=output,filetype="pdf") as result:
                    self.assertIn("Second line",result[0].get_text());self.assertNotIn("First line",result[0].get_text())

    def sign(self,source):
        return sign_pdf(source,{"certificate":base64.b64encode(self.p12).decode(),"certificatePassword":"local-test-only",
            "page":1,"x":50,"y":300,"width":250,"height":90,"reason":"Synthetic integration test"})

    def test_pades_signature_and_tampering(self):
        output=self.sign(sample());signatures=verify_signatures(output)["signatures"]
        self.assertEqual(len(signatures),1);self.assertTrue(signatures[0]["intact"])
        self.assertTrue(signatures[0]["valid"]);self.assertTrue(signatures[0]["unchanged"])
        self.assertFalse(signatures[0]["trustChecked"])
        self.assertIn(b"/ETSI.CAdES.detached",output)
        original_hex=b"PUBLIC preserved".hex().encode();modified_hex=b"PUBLIC tampered!".hex().encode()
        self.assertTrue(original_hex in output)
        altered=output.replace(original_hex,modified_hex,1)
        self.assertFalse(verify_signatures(altered)["signatures"][0]["intact"])

    def test_wrong_certificate_password_rejected(self):
        with self.assertRaises(ExtraInputError):
            sign_pdf(sample(),{"certificate":base64.b64encode(self.p12).decode(),"certificatePassword":"wrong"})


if __name__=="__main__":unittest.main()
