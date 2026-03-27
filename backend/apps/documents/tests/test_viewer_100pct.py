"""Copertura mirata apps.documents.viewer (mock subprocess, PIL, FS)."""
import builtins
import email.message
import importlib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.nonmultipart import MIMENonMultipart
from unittest.mock import MagicMock, patch

import pytest

from apps.documents import viewer as vw


def test_detect_mime_type_branches():
    assert vw.detect_mime_type("", fallback="text/plain") == "text/plain"
    assert vw.detect_mime_type("", fallback="") == "application/octet-stream"
    assert vw.detect_mime_type("x.heic") == "image/heic"
    assert vw.detect_mime_type("unknown.zzzzz") == "application/octet-stream"
    assert vw.detect_mime_type("notes.txt").startswith("text/")


def test_get_viewer_type():
    assert vw.get_viewer_type("") == "generic"
    assert vw.get_viewer_type("application/pdf") == "pdf"
    assert vw.get_viewer_type("video/unknown") == "generic"


def test_convert_office_to_pdf_success(tmp_path):
    src = tmp_path / "doc.docx"
    src.write_text("x", encoding="utf-8")
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    def exists_side(p):
        return str(p) == str(pdf)

    with patch("apps.documents.viewer.tempfile.mkdtemp", return_value=str(tmp_path)), patch(
        "apps.documents.viewer.subprocess.run"
    ) as run, patch("apps.documents.viewer.os.path.exists", side_effect=exists_side):
        run.return_value = MagicMock(returncode=0)
        out = vw.convert_office_to_pdf(str(src))
    assert out == str(pdf)


def test_convert_office_to_pdf_libreoffice_error():
    with patch("apps.documents.viewer.tempfile.mkdtemp", return_value="/tmp/x"), patch(
        "apps.documents.viewer.subprocess.run"
    ) as run:
        run.return_value = MagicMock(returncode=1, stderr=b"fail")
        with pytest.raises(Exception, match="LibreOffice"):
            vw.convert_office_to_pdf("/in.docx")


def test_convert_office_to_pdf_missing_output():
    with patch("apps.documents.viewer.tempfile.mkdtemp", return_value="/tmp/x"), patch(
        "apps.documents.viewer.subprocess.run"
    ) as run, patch("apps.documents.viewer.os.path.exists", return_value=False):
        run.return_value = MagicMock(returncode=0)
        with pytest.raises(Exception, match="not found"):
            vw.convert_office_to_pdf("/in.docx")


def test_parse_eml_plain_html_attachment(tmp_path):
    outer = MIMEMultipart()
    outer["Subject"] = "S"
    outer["From"] = "a@a.it"
    outer["To"] = "b@b.it"
    outer["Date"] = "Mon, 1 Jan 2024 00:00:00 +0000"
    outer.attach(MIMEText("hello", "plain", "utf-8"))
    outer.attach(MIMEText("<p>hi</p>", "html", "utf-8"))
    att = MIMENonMultipart("application", "octet-stream")
    att.add_header("Content-Disposition", "attachment", filename="f.bin")
    att.set_payload(b"abc")
    outer.attach(att)
    p = tmp_path / "m.eml"
    p.write_bytes(outer.as_bytes())
    r = vw.parse_eml(str(p))
    assert r["body_text"] == "hello"
    assert "<p>" in r["body_html"]
    assert len(r["attachments"]) == 1
    assert r["attachments"][0]["filename"] == "f.bin"
    assert r["attachments"][0]["size"] == 3


def test_parse_eml_get_content_raises(tmp_path):
    outer = MIMEMultipart()
    outer["Subject"] = "S"
    outer["From"] = "x@x.it"
    outer["To"] = "y@y.it"
    outer["Date"] = "Mon, 1 Jan 2024 00:00:00 +0000"
    outer.attach(MIMEText("plain body", "plain", "utf-8"))
    outer.attach(MIMEText("<p>h</p>", "html", "utf-8"))
    p = tmp_path / "bad.eml"
    p.write_bytes(outer.as_bytes())
    real_gc = email.message.EmailMessage.get_content

    def wrapped(self, *args, **kwargs):
        ct = self.get_content_type()
        if ct == "text/plain":
            raise ValueError("decode")
        if ct == "text/html":
            raise ValueError("html")
        return real_gc(self, *args, **kwargs)

    with patch.object(email.message.EmailMessage, "get_content", wrapped):
        r = vw.parse_eml(str(p))
    assert r["body_text"] == ""
    assert r["body_html"] == ""


def test_convert_image_rgba_png(tmp_path):
    src = tmp_path / "i.tiff"
    src.write_bytes(b"fake")
    out_png = tmp_path / "i.png"
    img = MagicMock()
    img.mode = "RGBA"
    img.save = MagicMock()

    def open_side(path, mode="r"):
        return img

    with patch("apps.documents.viewer.tempfile.mkdtemp", return_value=str(tmp_path)), patch(
        "PIL.Image.open", side_effect=open_side
    ):
        path, mime = vw.convert_image_to_web(str(src))
    img.save.assert_called_once()
    assert path.endswith(".png")
    assert mime == "image/png"


def test_convert_image_rgb_jpeg(tmp_path):
    src = tmp_path / "n.jpg"
    src.write_bytes(b"fake")
    img = MagicMock()
    img.mode = "RGB"
    img.save = MagicMock()
    with patch("apps.documents.viewer.tempfile.mkdtemp", return_value=str(tmp_path)), patch(
        "PIL.Image.open", return_value=img
    ):
        path, mime = vw.convert_image_to_web(str(src))
    assert mime == "image/jpeg"
    img.save.assert_called_once()


def test_convert_image_cmyk_jpeg(tmp_path):
    src = tmp_path / "c.jpg"
    src.write_bytes(b"fake")
    img = MagicMock()
    img.mode = "CMYK"
    img.convert.return_value = img
    img.save = MagicMock()

    with patch("apps.documents.viewer.tempfile.mkdtemp", return_value=str(tmp_path)), patch(
        "PIL.Image.open", return_value=img
    ):
        path, mime = vw.convert_image_to_web(str(src))
    img.convert.assert_called_once_with("RGB")
    assert mime == "image/jpeg"


def test_convert_image_failure_rmtree(tmp_path):
    src = tmp_path / "x.bmp"
    src.write_bytes(b"fake")
    with patch("apps.documents.viewer.tempfile.mkdtemp", return_value=str(tmp_path)), patch(
        "PIL.Image.open", side_effect=OSError("bad")
    ), patch("apps.documents.viewer.shutil.rmtree") as rm:
        with pytest.raises(Exception, match="Image conversion failed"):
            vw.convert_image_to_web(str(src))
    rm.assert_called_once()


def test_convert_video_to_mp4_success(tmp_path):
    src = tmp_path / "v.mov"
    src.write_bytes(b"v")
    out_mp4 = tmp_path / "v.mp4"
    out_mp4.write_bytes(b"data")

    def exists_side(p):
        return str(p) == str(out_mp4)

    with patch("apps.documents.viewer.tempfile.mkdtemp", return_value=str(tmp_path)), patch(
        "apps.documents.viewer.subprocess.run"
    ) as run, patch("apps.documents.viewer.os.path.exists", side_effect=exists_side):
        run.return_value = MagicMock(returncode=0)
        got = vw.convert_video_to_mp4(str(src))
    assert got == str(out_mp4)


def test_convert_video_to_mp4_ffmpeg_error(tmp_path):
    src = tmp_path / "v.avi"
    src.write_bytes(b"v")
    with patch("apps.documents.viewer.tempfile.mkdtemp", return_value=str(tmp_path)), patch(
        "apps.documents.viewer.subprocess.run"
    ) as run, patch("apps.documents.viewer.shutil.rmtree") as rm:
        run.return_value = MagicMock(returncode=1, stderr=b"ffmpeg err")
        with pytest.raises(Exception, match="FFmpeg"):
            vw.convert_video_to_mp4(str(src))
    rm.assert_called_once()


def test_convert_video_to_mp4_missing_file_after_ok_return(tmp_path):
    src = tmp_path / "v.mkv"
    src.write_bytes(b"v")
    with patch("apps.documents.viewer.tempfile.mkdtemp", return_value=str(tmp_path)), patch(
        "apps.documents.viewer.subprocess.run"
    ) as run, patch("apps.documents.viewer.os.path.exists", return_value=False), patch(
        "apps.documents.viewer.shutil.rmtree"
    ) as rm:
        run.return_value = MagicMock(returncode=0)
        with pytest.raises(Exception, match="not found"):
            vw.convert_video_to_mp4(str(src))
    rm.assert_called_once()


def test_optional_pillow_heif_import_error_reload():
    import apps.documents.viewer as vmod

    sys.modules.pop("pillow_heif", None)
    real_imp = builtins.__import__

    def limited_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pillow_heif":
            raise ImportError("no heif in test")
        return real_imp(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", limited_import):
        importlib.reload(vmod)
    importlib.reload(vmod)


def test_convert_video_subprocess_raises(tmp_path):
    src = tmp_path / "v.wmv"
    src.write_bytes(b"v")
    with patch("apps.documents.viewer.tempfile.mkdtemp", return_value=str(tmp_path)), patch(
        "apps.documents.viewer.subprocess.run", side_effect=RuntimeError("timeout")
    ), patch("apps.documents.viewer.shutil.rmtree") as rm:
        with pytest.raises(RuntimeError):
            vw.convert_video_to_mp4(str(src))
    rm.assert_called_once()
