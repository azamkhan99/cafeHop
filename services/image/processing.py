"""
Image processing for the image service: map thumbnail generation only.
"""
from __future__ import annotations

import logging
from io import BytesIO

from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

_HEIF_REGISTERED = False
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    _HEIF_REGISTERED = True
except Exception as ex:  # ImportError, OSError if native lib missing in some images
    logger.warning("pillow_heif unavailable (%s); HEIC/HEIF may not decode", ex)

# Some browser-exported JPEGs are minimally truncated; Pillow would error on .load() otherwise.
ImageFile.LOAD_TRUNCATED_IMAGES = True


def _looks_like_xml_or_html(b: bytes) -> bool:
    t = b[:200].lstrip()
    return t.startswith(b"<") or t.startswith(b"{")


def _looks_like_heif_container(b: bytes) -> bool:
    """ISO BMFF (HEIF/HEIC/AVIF) starts with size then 'ftyp' at offset 4."""
    if len(b) < 12 or b[4:8] != b"ftyp":
        return False
    brand = b[8:12]
    return brand in (b"heic", b"heim", b"heix", b"hevc", b"hev1", b"mif1", b"msf1", b"avif")


def generate_map_thumbnail(image_bytes: bytes) -> bytes:
    """
    Produce a 150px-max-width JPEG thumbnail from raw image bytes.
    Applies EXIF orientation and normalizes to RGB.
    """
    if not image_bytes:
        raise ValueError("Empty S3 object (upload may have failed or key is wrong).")
    if _looks_like_xml_or_html(image_bytes):
        raise ValueError(
            "S3 body is not image bytes (looks like XML/JSON). Check the object key and that the PUT upload succeeded."
        )
    try:
        img = Image.open(BytesIO(image_bytes))
        img.load()
    except UnidentifiedImageError as e:
        if _looks_like_heif_container(image_bytes):
            if not _HEIF_REGISTERED:
                raise ValueError(
                    "This file looks like HEIC/HEIF but the server has no HEIF decoder. "
                    "Redeploy the image Lambda with pillow-heif, or upload JPEG/PNG."
                ) from e
            raise ValueError(
                "Could not decode HEIC/HEIF (file may be corrupt). Try exporting JPEG from Photos."
            ) from e
        raise ValueError(
            f"Unrecognized image format (JPEG, PNG, WebP, HEIC/HEIF, etc.): {e}"
        ) from e
    except (OSError, ValueError) as e:
        raise ValueError(f"Could not decode image: {e}") from e

    try:
        if getattr(img, "n_frames", 1) > 1:
            img.seek(0)
    except Exception:
        pass

    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        try:
            exif = img.getexif()
            if exif is not None and exif.get(274) == 6:
                img = img.rotate(-90, expand=True)
        except Exception:
            pass

    if img.width < 1 or img.height < 1:
        raise ValueError("Image has invalid dimensions")

    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        mask = img.split()[-1] if img.mode in ("RGBA", "LA") else None
        background.paste(img, mask=mask)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    max_width = 150
    if img.width > max_width:
        ratio = max_width / img.width
        new_h = int(img.height * ratio)
        img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)

    try:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=75, optimize=True)
        buf.seek(0)
        return buf.getvalue()
    except (OSError, ValueError) as e:
        raise ValueError(f"Could not encode thumbnail: {e}") from e
