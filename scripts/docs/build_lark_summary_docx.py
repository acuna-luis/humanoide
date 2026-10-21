#!/usr/bin/env python3
"""Generate the Spanish Lark folder guide using an isolated LibreOffice profile."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from lxml import etree


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/guides/MANUAL_RESUMEN_ARCHIVOS_LARK_CRUZR_S2_ES.html"


def format_word(document):
    """Constrain tables; separate the opening scope page and five chapters."""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    word = "{" + ns["w"] + "}"
    tree = etree.fromstring(document)

    def element(parent, name):
        current = parent.find(word + name)
        return current if current is not None else etree.SubElement(parent, word + name)

    for section in tree.findall(".//w:sectPr", ns):
        size = element(section, "pgSz")
        size.set(word + "w", "11906")
        size.set(word + "h", "16838")
        margins = element(section, "pgMar")
        for name, value in {"left": "964", "right": "964", "top": "907", "bottom": "907"}.items():
            margins.set(word + name, value)

    for paragraph in tree.findall(".//w:body/w:p", ns):
        text = "".join(paragraph.itertext())
        if text.startswith(("1. Resumen general", "2. Modelos del robot", "3. Manos, pinza", "4. Documentos", "5. Uso práctico")):
            props = element(paragraph, "pPr")
            element(props, "pageBreakBefore").set(word + "val", "1")
            element(props, "keepNext").set(word + "val", "1")

    tables = tree.findall(".//w:tbl", ns)
    fractions = (0.43, 0.40, 0.43, 0.57, 0.21)
    if len(tables) != len(fractions):
        raise ValueError("Unexpected table count in Word export")
    for table, fraction in zip(tables, fractions):
        props = element(table, "tblPr")
        for floating in props.findall(word + "tblpPr"):
            props.remove(floating)
        width = element(props, "tblW")
        width.set(word + "type", "dxa")
        width.set(word + "w", "9978")
        element(props, "tblLayout").set(word + "type", "fixed")
        indent = element(props, "tblInd")
        indent.set(word + "type", "dxa")
        indent.set(word + "w", "0")
        widths = (round(9978 * fraction), 9978 - round(9978 * fraction))
        grid = element(table, "tblGrid")
        for child in list(grid):
            grid.remove(child)
        for value in widths:
            etree.SubElement(grid, word + "gridCol").set(word + "w", str(value))
        for index, row in enumerate(table.findall("w:tr", ns)):
            row_props = element(row, "trPr")
            element(row_props, "cantSplit").set(word + "val", "1")
            if index == 0:
                element(row_props, "tblHeader").set(word + "val", "1")
            for cell, value in zip(row.findall("w:tc", ns), widths):
                cell_props = element(cell, "tcPr")
                cell_width = element(cell_props, "tcW")
                cell_width.set(word + "type", "dxa")
                cell_width.set(word + "w", str(value))
                for no_wrap in cell_props.findall(word + "noWrap"):
                    cell_props.remove(no_wrap)
    return etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New DOCX; never overwrites")
    args = parser.parse_args()
    output = args.output
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        parser.error("Use a new output file in an existing directory")
    with tempfile.TemporaryDirectory(prefix="cruzr-lark-docx-") as tmp:
        work = Path(tmp)
        source = work / "Manual_resumen_archivos_Cruzr_S2_ES.html"
        source.write_bytes(SOURCE.read_bytes())
        profile = (work / "libreoffice-profile").as_uri()
        subprocess.run([
            "libreoffice", "-env:UserInstallation=" + profile, "--headless",
            "--convert-to", "docx:Office Open XML Text", "--outdir", str(work), str(source),
        ], check=True, timeout=90, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        generated = source.with_suffix(".docx")
        with zipfile.ZipFile(generated) as bundle:
            members = [(item, bundle.read(item.filename)) for item in bundle.infolist()]
        formatted = work / "formatted.docx"
        with zipfile.ZipFile(formatted, "x", zipfile.ZIP_DEFLATED) as bundle:
            for item, data in members:
                bundle.writestr(item, format_word(data) if item.filename == "word/document.xml" else data)
        generated = formatted
        with zipfile.ZipFile(generated) as bundle:
            if bundle.testzip() is not None:
                raise ValueError("DOCX failed ZIP integrity verification")
            document = ET.fromstring(bundle.read("word/document.xml"))
            namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            # Font changes can split one Chinese filename into several runs.
            text = "".join(n.text or "" for n in document.findall(".//w:t", namespace))
            for expected in ("Resumen general", "四代手-URDF.zip", "末端 urdf", "milímetros", "disco externo"):
                if expected not in text:
                    raise ValueError("Missing expected content in DOCX: " + expected)
        with generated.open("rb") as source_file, output.open("xb") as target:
            shutil.copyfileobj(source_file, target)
    print(json.dumps({
        "output": str(output), "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "source": str(SOURCE), "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "originals_modified": False, "robot_connections": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
