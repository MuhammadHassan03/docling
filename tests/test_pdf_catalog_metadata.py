# SPDX-FileCopyrightText: The Docling Contributors
# SPDX-License-Identifier: MIT

"""The PDF catalog /Lang and XMP metadata reach ConversionResult, and only there."""

from pathlib import Path

import pytest

from docling.datamodel.accelerator_options import AcceleratorDevice
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from .verify_utils import CONFID_PREC, COORD_PREC, _normalize_newlines

SOURCES = Path("./tests/data/pdf/sources")
GROUNDTRUTH = Path("./tests/data/pdf/groundtruth")


def _convert(name: str) -> ConversionResult:
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    pipeline_options.accelerator_options.device = AcceleratorDevice.CPU
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    return converter.convert(SOURCES / name)


def test_pdf_language_and_xmp_land_on_conversion_result_only(tmp_path: Path):
    # right_to_left_01.pdf carries catalog /Lang (en-US) and an XMP packet.
    conv_res = _convert("right_to_left_01.pdf")

    assert conv_res.pdf_language == "en-US"
    assert conv_res.pdf_xmp_metadata is not None
    assert conv_res.pdf_xmp_metadata["Producer"] == "Microsoft® Word LTSC"

    # The document and its exports stay exactly as the groundtruth recorded them.
    doc = conv_res.document
    expected_md = _normalize_newlines(
        (GROUNDTRUTH / "right_to_left_01.md").read_text(encoding="utf-8")
    )
    assert _normalize_newlines(doc.export_to_markdown(compact_tables=True)) == (
        expected_md
    )
    # Same call the groundtruth was generated with (verify_utils.check_conversion_result_v2).
    json_path = tmp_path / "right_to_left_01.json"
    doc.save_as_json(
        json_path, indent=2, coord_precision=COORD_PREC, confid_precision=CONFID_PREC
    )
    assert _normalize_newlines(json_path.read_text(encoding="utf-8")) == (
        _normalize_newlines(
            (GROUNDTRUTH / "right_to_left_01.json").read_text(encoding="utf-8")
        )
    )


def test_pdf_without_language_and_xmp_leaves_both_fields_none():
    conv_res = _convert("table_mislabeled_as_picture.pdf")

    assert conv_res.pdf_language is None
    assert conv_res.pdf_xmp_metadata is None


def test_parser_failure_reading_annotations_does_not_fail_the_conversion(
    monkeypatch: pytest.MonkeyPatch,
):
    def raise_runtime_error(self, doc_key):
        raise RuntimeError("annotations unreadable")

    monkeypatch.setattr(
        "docling.backend.docling_parse_backend.DoclingThreadedPdfParser.get_annotations",
        raise_runtime_error,
    )

    # right_to_left_01.pdf has /Lang and XMP, so both would be set without the failure.
    conv_res = _convert("right_to_left_01.pdf")

    assert conv_res.status == ConversionStatus.SUCCESS
    assert conv_res.document.texts
    assert conv_res.pdf_language is None
    assert conv_res.pdf_xmp_metadata is None
