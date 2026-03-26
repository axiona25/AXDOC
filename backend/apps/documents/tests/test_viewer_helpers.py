"""Test funzioni pure viewer.py (FASE 33B)."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from apps.documents.viewer import (
    convert_image_to_web,
    convert_office_to_pdf,
    convert_video_to_mp4,
    detect_mime_type,
    get_viewer_type,
    parse_eml,
)


def test_detect_mime_extra_map():
    assert detect_mime_type("x.heic") == "image/heic"
    assert detect_mime_type("doc.p7m") == "application/pkcs7-mime"


def test_detect_mime_respects_non_octet_fallback():
    assert detect_mime_type("x.bin", fallback="application/pdf") == "application/pdf"


def test_get_viewer_categories():
    assert get_viewer_type("application/pdf") == "pdf"
    assert get_viewer_type("image/png") == "image"
    assert get_viewer_type("video/mp4") == "video"
    assert get_viewer_type("") == "generic"
    assert get_viewer_type("application/unknown") == "generic"


def test_parse_eml_plain(tmp_path):
    eml = tmp_path / "m.eml"
    eml.write_text(
        "From: a@b.c\nTo: d@e.f\nSubject: Subj\n"
        "MIME-Version: 1.0\nContent-Type: text/plain; charset=utf-8\n\nCiao mondo\n",
        encoding="utf-8",
    )
    r = parse_eml(str(eml))
    assert "Ciao mondo" in (r.get("body_text") or "")


def test_convert_image_bmp_to_jpeg(tmp_path):
    bmp = tmp_path / "x.bmp"
    Image.new("RGB", (8, 8), color="blue").save(bmp, format="BMP")
    out_path, mime = convert_image_to_web(str(bmp))
    assert mime == "image/jpeg"
    assert os.path.isfile(out_path)


@patch("apps.documents.viewer.subprocess.run")
def test_convert_office_to_pdf_mock(mock_run, tmp_path):
    def side_effect(cmd, **kwargs):
        out_dir = cmd[cmd.index("--outdir") + 1]
        src = cmd[-1]
        base = os.path.splitext(os.path.basename(src))[0]
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / f"{base}.pdf").write_bytes(b"%PDF-1.4")
        return MagicMock(returncode=0, stderr=b"")

    mock_run.side_effect = side_effect
    doc = tmp_path / "w.doc"
    doc.write_bytes(b"fake doc")
    pdf_path = convert_office_to_pdf(str(doc))
    assert pdf_path.endswith(".pdf")
    assert os.path.isfile(pdf_path)


@patch("apps.documents.viewer.subprocess.run")
def test_convert_video_to_mp4_mock(mock_run, tmp_path):
    def side_effect(cmd, **kwargs):
        out_path = cmd[-1]
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(b"fake mp4")
        return MagicMock(returncode=0, stderr=b"")

    mock_run.side_effect = side_effect
    mov = tmp_path / "c.mov"
    mov.write_bytes(b"fake mov")
    out = convert_video_to_mp4(str(mov))
    assert out.endswith(".mp4")
