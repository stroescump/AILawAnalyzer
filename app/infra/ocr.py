from dataclasses import dataclass
from pathlib import Path

import pytesseract
from PIL import Image


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float | None


def ocr_image(path: Path, lang: str = "ron") -> OcrResult:
    img = Image.open(path)
    try:
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractError:
        # Pareto: fall back to English if Romanian traineddata isn't installed locally.
        data = pytesseract.image_to_data(img, lang="eng", output_type=pytesseract.Output.DICT)
    texts: list[str] = []
    confs: list[float] = []

    for t, c in zip(data.get("text", []), data.get("conf", [])):
        if not t or not str(t).strip():
            continue
        texts.append(str(t))
        try:
            cf = float(c)
            if cf >= 0:
                confs.append(cf)
        except Exception:
            continue

    avg = (sum(confs) / len(confs)) if confs else None
    return OcrResult(text=" ".join(texts).strip(), confidence=avg)
