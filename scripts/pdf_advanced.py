"""Validated PDF/A, selected-line replacement, and local certificate signing."""
import base64
import io
import json
import math
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
import pymupdf
from pdf_extra import ROOT, FONT, ExtraInputError, open_pdf, rect_for
from pdf_layout import FontManager


def run_local(command, timeout=150):
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        process.communicate()
        raise ExtraInputError("문서 처리 시간이 초과되었습니다. 더 작은 파일로 다시 시도하세요.")
    return process.returncode, stdout


def validate_pdfa_path(path):
    runtime = ROOT / "tools/pdfa"
    java = next((runtime / "java").rglob("java.exe"), None)
    jar = next((runtime / "verapdf/bin").glob("cli-*.jar"), None)
    if not java or not jar:
        raise ExtraInputError("로컬 PDF/A 검사기(veraPDF)가 준비되지 않았습니다.")
    code, output = run_local([str(java), "-Xmx768m", "-jar", str(jar), "--format", "json",
                              "--flavour", "2b", str(path)], 120)
    try:
        result = json.loads(output)["report"]["jobs"][0]["validationResult"][0]
        return {"compliant": result["compliant"] is True, "profile": result["profileName"],
                "passedRules": result["details"]["passedRules"],
                "failedRules": result["details"]["failedRules"],
                "failedChecks": result["details"]["failedChecks"]}
    except (KeyError, IndexError, ValueError):
        raise ExtraInputError("PDF/A 검사 결과를 읽지 못했습니다. 변환 성공으로 처리하지 않습니다.")


def pdfa_convert(data):
    with open_pdf(data) as document:
        if len(document) > 100:
            raise ExtraInputError("PDF/A 변환은 100쪽 이하 문서를 사용하세요.")
    executable = ROOT / "tools/libreoffice/runtime/program/soffice.com"
    if not executable.exists():
        raise ExtraInputError("로컬 PDF/A 변환 엔진이 준비되지 않았습니다.")
    work = ROOT / "work"; work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pdfa-", dir=work) as temp:
        directory = Path(temp).resolve()
        if not directory.is_relative_to(work.resolve()):
            raise RuntimeError("Invalid temporary directory")
        source = directory / "input.pdf"; source.write_bytes(data)
        output = directory / "out"; output.mkdir()
        profile = directory / "profile"
        options = {"SelectPdfVersion": {"type": "long", "value": "2"},
                   "ExportFormFields": {"type": "boolean", "value": "false"},
                   "ExportBookmarks": {"type": "boolean", "value": "false"}}
        code, _ = run_local([str(executable), "-env:UserInstallation=" + profile.as_uri(),
                             "--headless", "--nologo", "--norestore", "--nodefault",
                             "--nofirststartwizard", "--convert-to",
                             "pdf:draw_pdf_Export:" + json.dumps(options, separators=(",", ":")),
                             "--outdir", str(output), str(source)])
        result = output / "input.pdf"
        if code or not result.exists():
            raise ExtraInputError("PDF/A로 변환하지 못했습니다. 파일 손상 여부를 확인하세요.")
        validation = validate_pdfa_path(result)
        if not validation["compliant"]:
            raise ExtraInputError(f"PDF/A-2b 검사에서 {validation['failedRules']}개 규칙 위반이 발생했습니다. 결과를 제공하지 않습니다.")
        return result.read_bytes(), validation


def page_lines(page):
    result = []
    for block_index, block in enumerate(page.get_text("dict")["blocks"]):
        for line_index, line in enumerate(block.get("lines", [])):
            spans = line.get("spans", [])
            text = "".join(span["text"] for span in spans)
            if not text.strip() or not spans:
                continue
            supported = (not page.rotation and tuple(line.get("dir", (1, 0))) == (1, 0)
                         and len(text) <= 1000 and all(span.get("origin") for span in spans))
            result.append({"id": f"{block_index}:{line_index}", "text": text,
                           "bbox": list(line["bbox"]), "origin": list(spans[0]["origin"]),
                           "size": float(spans[0]["size"]), "color": spans[0].get("color", 0),
                           "font": spans[0]["font"],
                           "supported": supported})
    return result


def text_lines(data, page_number):
    with open_pdf(data) as document:
        number = int(page_number)
        if not 1 <= number <= len(document):
            raise ExtraInputError("페이지 번호를 확인하세요.")
        page = document[number - 1]
        return {"page": number, "pages": len(document), "width": page.rect.width,
                "height": page.rect.height, "lines": page_lines(page)}


def replace_text(data, payload):
    operations = payload.get("operations")
    if not isinstance(operations, list) or not 1 <= len(operations) <= 50:
        raise ExtraInputError("1~50개의 수정할 줄을 선택하세요.")
    with open_pdf(data) as document:
        prepared = []; seen = set(); managers = {}
        for item in operations:
            number = int(item["page"])
            if not 1 <= number <= len(document):
                raise ExtraInputError("페이지 번호를 확인하세요.")
            page = document[number - 1]
            line = next((line for line in page_lines(page) if line["id"] == item.get("id")), None)
            if not line or not line["supported"] or line["text"] != item.get("original"):
                raise ExtraInputError("원문 줄이 변경되었거나 지원하지 않는 방향입니다. 파일을 다시 선택하세요.")
            key = (number, line["id"])
            if key in seen:
                raise ExtraInputError("같은 줄을 두 번 수정할 수 없습니다. 목록에서 기존 수정을 제거하세요.")
            seen.add(key)
            replacement = item.get("text")
            if not isinstance(replacement, str) or len(replacement) > 1000 or any(ord(c) < 32 for c in replacement):
                raise ExtraInputError("한 줄의 글자를 1,000자 이내로 입력하세요. 줄바꿈은 지원하지 않습니다.")
            rect = pymupdf.Rect(line["bbox"])
            if not page.rect.contains(rect):
                raise ExtraInputError("페이지 밖에 걸친 글자는 수정할 수 없습니다.")
            if any(rect.intersects(w.rect) for w in page.widgets() or []):
                raise ExtraInputError("입력 양식과 겹친 줄입니다. PDF 양식 도구를 사용하세요.")
            # Full font-height boxes can overlap the next line even with normal
            # leading. Use a narrow strip and preflight every affected glyph;
            # reject complex layouts rather than deleting neighbouring text.
            middle = (rect.y0 + rect.y1) / 2
            erase = pymupdf.Rect(rect.x0, middle - rect.height * .1,
                                 rect.x1, middle + rect.height * .1)
            for bi, block in enumerate(page.get_text("rawdict")["blocks"]):
                for li, raw_line in enumerate(block.get("lines", [])):
                    target = f"{bi}:{li}" == line["id"]
                    for span in raw_line.get("spans", []):
                        for char in span.get("chars", []):
                            if char["c"].isspace():
                                continue
                            hit = erase.intersects(pymupdf.Rect(char["bbox"]))
                            if hit != target:
                                raise ExtraInputError("다른 글자와 겹치거나 복잡한 기준선이 있는 줄입니다. 주변 글자를 보존하기 위해 수정하지 않습니다.")
            line["erase"] = list(erase)
            if any(n == number and rect.intersects(old) for n, old, *_ in prepared):
                raise ExtraInputError("서로 겹치는 줄은 한 번에 수정할 수 없습니다.")
            size = min(96, line["size"])
            manager=managers.setdefault(number,FontManager(document,page))
            entry=manager.choose(line["font"],replacement,payload.get("fontMode","auto"))
            font=entry[0];line["chosenFont"]=entry
            width = font.text_length(replacement, fontsize=size)
            if width > rect.width:
                size *= rect.width / width
            if replacement and (not math.isfinite(size) or size < 6):
                raise ExtraInputError("새 문장이 원래 줄보다 너무 깁니다. 글자를 줄여 주세요.")
            prepared.append((number, rect, line, replacement, size))
        for number, rect, line, *_ in prepared:
            document[number - 1].add_redact_annot(pymupdf.Rect(line["erase"]), fill=False, cross_out=False)
        for number in {entry[0] for entry in prepared}:
            # Remove original glyphs, preserving background images and vector drawings.
            document[number - 1].apply_redactions(images=0, graphics=0, text=0)
        for number, rect, line, replacement, size in prepared:
            if replacement:
                color = line["color"]
                rgb = tuple(((color >> shift) & 255) / 255 for shift in (16, 8, 0))
                resource=managers[number].install(line["chosenFont"])
                document[number - 1].insert_text(line["origin"], replacement, fontsize=size,
                    fontname=resource, color=rgb, overlay=True)
        return document.tobytes(garbage=4, deflate=True)


def sign_pdf(data, payload):
    from cryptography import x509
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.pdf_utils.text import TextBoxStyle
    from pyhanko.pdf_utils.font import FontEngineFactory
    from pyhanko.pdf_utils.font.opentype import GlyphAccumulator
    from pyhanko.sign import signers, fields
    from pyhanko.stamp import TextStampStyle
    try:
        p12 = base64.b64decode(payload.get("certificate", ""), validate=True)
        password = payload.get("certificatePassword", "")
        if not 0 < len(p12) <= 2 * 1024 * 1024 or not isinstance(password, str) or len(password) > 1024:
            raise ValueError()
        signer = signers.SimpleSigner.load_pkcs12_data(p12, [], passphrase=password.encode("utf8") or None)
        certificate = x509.load_der_x509_certificate(signer.signing_cert.dump())
    except Exception:
        raise ExtraInputError("P12/PFX 인증서와 비밀번호를 확인하세요. 개인키가 포함된 인증서가 필요합니다.")
    now = datetime.now(timezone.utc)
    if not certificate.not_valid_before_utc <= now <= certificate.not_valid_after_utc:
        raise ExtraInputError("인증서의 유효기간이 시작되지 않았거나 만료되었습니다.")
    with open_pdf(data) as document:
        index = int(payload.get("page", 1)) - 1
        if not 0 <= index < len(document):
            raise ExtraInputError("페이지 번호를 확인하세요.")
        page = document[index]; rect = rect_for(page, payload)
        if rect.width < 140 or rect.height < 50:
            raise ExtraInputError("디지털 서명 영역은 너비 140pt·높이 50pt 이상으로 지정하세요.")
        box = (int(rect.x0), int(page.rect.height - rect.y1), int(rect.x1), int(page.rect.height - rect.y0))
    reason = payload.get("reason", "")
    if not isinstance(reason, str) or len(reason) > 200:
        raise ExtraInputError("서명 사유는 200자 이내로 입력하세요.")
    output = io.BytesIO()
    metadata = signers.PdfSignatureMetadata(field_name="LocalSignature_" + uuid.uuid4().hex[:12],
        md_algorithm="sha256", subfilter=fields.SigSeedSubFilter.PADES, reason=reason or None)
    class MemoryFontFactory(FontEngineFactory):
        def create_font_engine(self, writer, obj_stream=None):
            return GlyphAccumulator(writer=writer, font_handle=io.BytesIO(FONT.read_bytes()),
                                    font_size=9, obj_stream=obj_stream)
    style = TextStampStyle(stamp_text="Digitally signed\n%(signer)s\n%(ts)s",
                          text_box_style=TextBoxStyle(font=MemoryFontFactory(), font_size=9))
    try:
        signers.PdfSigner(metadata, signer, stamp_style=style,
            new_field_spec=fields.SigFieldSpec(metadata.field_name, on_page=index, box=box)).sign_pdf(
                IncrementalPdfFileWriter(io.BytesIO(data)), output=output)
    except Exception:
        raise ExtraInputError("서명하지 못했습니다. 인증서의 서명 용도와 기존 문서의 서명·수정 제한을 확인하세요.")
    return output.getvalue()


def verify_signatures(data):
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation.generic_cms import validate_sig_integrity
    with open_pdf(data):
        pass
    reader = PdfFileReader(io.BytesIO(data)); result = []
    for signature in reader.embedded_signatures:
        try:
            # Deliberately integrity-only: do not infer certificate trust from an
            # uploaded certificate, and never fetch revocation or issuer URLs.
            signature.compute_integrity_info(skip_diff=True)
            intact, valid = validate_sig_integrity(signature.signer_info, signature.signer_cert,
                expected_content_type="data", actual_digest=signature.compute_digest())
            coverage = signature.coverage.name if signature.coverage else "UNKNOWN"
            result.append({"field": signature.field_name, "signer": signature.signer_cert.subject.human_friendly,
                           "valid": bool(valid), "intact": bool(intact),
                           "coverage": coverage, "unchanged": coverage == "ENTIRE_FILE" and bool(intact and valid),
                           "trustChecked": False, "revocationChecked": False,
                           "fingerprint": signature.signer_cert.sha256.hex()})
        except Exception:
            result.append({"field": signature.field_name, "valid": False, "intact": False,
                           "unchanged": False, "trustChecked": False, "error": "서명 검증 실패"})
    return {"signatures": result, "notice": "문서 무결성만 검사합니다. 발급기관 신뢰·폐기 여부·공인 타임스탬프는 확인하지 않습니다."}
