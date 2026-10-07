import logging
import re
import pdfplumber
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def read_pdf(file_path: str):
    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    if not any("∈" in content for content in pages):
        return "".join(content + "\n" for content in pages if content)
    with pdfplumber.open(file_path) as geometry:
        if len(geometry.pages) != len(pages):
            logger.warning("PDF page count mismatch: text=%s, geometry=%s; skipping restoration",
                           len(pages), len(geometry.pages))
        else:
            for index, content in enumerate(pages):
                if "∈" in content:
                    pages[index] = restore_negated_membership(content, geometry.pages[index])
    return "".join(content + "\n" for content in pages if content)


def has_negation_slash(char, shapes):
    height = char["bottom"] - char["top"]
    margin = height * 0.1
    for shape in shapes:
        if not (shape.get("stroke") or shape.get("fill")):
            continue
        points = shape.get("pts", [])
        if not 2 <= len(points) <= 5:
            continue
        if any(part[0] not in {"m", "l", "h"} for part in shape.get("path", [])):
            continue
        if not (char["x0"] - margin <= shape["x0"] <= shape["x1"] <= char["x1"] + margin
                and char["top"] - margin <= shape["top"] <= shape["bottom"] <= char["bottom"] + margin):
            continue
        start, end = max(zip(points, points[1:]),
                         key=lambda pair: (pair[1][0] - pair[0][0]) ** 2 + (pair[1][1] - pair[0][1]) ** 2)
        dx, dy = end[0] - start[0], end[1] - start[1]
        if dx * dy >= 0 or abs(dx) < height * 0.1 or abs(dy) < height * 0.55:
            continue
        length = (dx ** 2 + dy ** 2) ** 0.5
        thickness = max(abs(dx * (y - start[1]) - dy * (x - start[0])) / length
                        for x, y in points)
        if max(thickness, shape.get("linewidth", 0)) <= max(2, height * 0.12):
            return True
    return False


def restore_negated_membership(content, page):
    flags = [has_negation_slash(char, page.lines + page.curves)
             for char in page.chars if char["text"] == "∈"]
    if not any(flags):
        return content
    if content.count("∈") != len(flags):
        logger.warning("Page %s: symbol count mismatch; skipping restoration", page.page_number)
        return content
    replacements = iter(flags)
    logger.info("Restored %s negated membership symbols on page %s", sum(flags), page.page_number)
    return re.sub("∈", lambda match: "∉" if next(replacements) else "∈", content)
