"""Replace audited legacy brand artwork only in disposable MCI web exports."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import posixpath
from zipfile import ZipFile

from lxml import etree
from PIL import Image

from branding import asset_path


# Exact artwork, not filenames: signatures and inspection photos must survive.
MSL_ARTWORK = frozenset({
    "09f44191088fe81eff16b1f09dfa27cad57b38c19e1eaf306c2b248aca29640b",
    "611994a378cd7711aa3aa5d07ebfafa10bcdfcec373a00928a7fcb57a937e786",
    "57395bf5781e78441cbf74480f3da5214b7c733f06254ba9531cbffe3c540f55",
    "e8176ff11191620071d2c8397bf5ac5249c3932491b2ae91121ab5ea521a3d17",
    "787a97f3454ee6d5019b29278c7e25c7d9febba2a000f9b834aab6021c0187dc",
    "bce7b12b5510631df67ccdc8ca988547a9d7888cdd33056b2e5b4d7387c79b43",
})
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def apply_mci_web_branding(path, data):
    """Keep original templates and every non-MCI export byte-for-byte intact."""
    if str(data.get("company_code") or "").strip().upper() != "MCI-CR":
        return
    path = Path(path)
    with ZipFile(path) as source:
        entries = source.infolist()
        parts = {item.filename: source.read(item) for item in entries}
    replaced = {name for name, raw in parts.items()
                if "/media/" in name and sha256(raw).hexdigest() in MSL_ARTWORK}
    if not replaced:
        return
    logo = asset_path("mci_logo.png")
    if not logo:
        raise RuntimeError("MCI logo unavailable; refusing to export MSL branding")
    artwork = Path(logo).read_bytes()
    with Image.open(BytesIO(artwork)) as image:
        ratio = image.width / image.height
    for name in replaced:
        parts[name] = artwork
    types = etree.fromstring(parts["[Content_Types].xml"])
    for name in replaced:
        override = next((n for n in types if n.get("PartName") == "/" + name), None)
        if override is None:
            override = etree.SubElement(types, "{http://schemas.openxmlformats.org/package/2006/content-types}Override", PartName="/" + name)
        override.set("ContentType", "image/png")
    parts["[Content_Types].xml"] = etree.tostring(types, xml_declaration=True, encoding="UTF-8")
    for rel_name, raw in list(parts.items()):
        if not rel_name.endswith(".rels") or "/_rels/" not in rel_name:
            continue
        directory, filename = rel_name.rsplit("/_rels/", 1)
        owner = directory + "/" + filename[:-5]
        if owner not in parts or not owner.endswith(".xml"):
            continue
        relationships = etree.fromstring(raw)
        ids = {rel.get("Id") for rel in relationships
               if rel.get("TargetMode") != "External" and
               posixpath.normpath(posixpath.join(directory, rel.get("Target", ""))).lstrip("/") in replaced}
        if not ids:
            continue
        root = etree.fromstring(parts[owner])
        changed = False
        for blip in root.xpath(".//a:blip", namespaces=NS):
            if blip.get("{" + NS["r"] + "}embed") not in ids:
                continue
            fill = blip.getparent()
            picture = fill.getparent()
            ext = picture.find(".//a:xfrm/a:ext", NS)
            if ext is None:
                continue
            width, height = int(ext.get("cx", 0)), int(ext.get("cy", 0))
            if not width or not height:
                continue
            ext.getparent().attrib.pop("rot", None)
            # Fit inside the existing picture box without stretching the shield,
            # moving any cell/paragraph, or changing the template's print area.
            for crop in fill.findall("a:srcRect", NS):
                fill.remove(crop)
            stretch = fill.find("a:stretch", NS)
            if stretch is None:
                stretch = etree.SubElement(fill, "{" + NS["a"] + "}stretch")
            for child in list(stretch):
                stretch.remove(child)
            rect = etree.SubElement(stretch, "{" + NS["a"] + "}fillRect")
            if width / height > ratio:
                inset = round((1 - height * ratio / width) * 50000)
                rect.set("l", str(inset))
                rect.set("r", str(inset))
            else:
                inset = round((1 - width / ratio / height) * 50000)
                rect.set("t", str(inset))
                rect.set("b", str(inset))
            changed = True
        if changed:
            parts[owner] = etree.tostring(root, xml_declaration=True, encoding="UTF-8")
    for name, raw in list(parts.items()):
        if (name.startswith("xl/worksheets/") and name.endswith(".xml")) or name == "xl/sharedStrings.xml":
            root = etree.fromstring(raw)
            labels = [node for node in root.iter() if node.text == "MSL SURVEYOR SIGNATURE"]
            for node in labels:
                node.text = "MCI SURVEYOR SIGNATURE"
            if labels:
                parts[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8")
    output = BytesIO()
    with ZipFile(output, "w") as target:
        for item in entries:
            target.writestr(item, parts[item.filename])
    path.write_bytes(output.getvalue())
