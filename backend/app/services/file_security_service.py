from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
import zipfile

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
import pymupdf

ALLOWED_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
}


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    original_name: str
    extension: str
    media_type: str
    content: bytes


def signature_matches(extension: str, content: bytes) -> bool:
    if extension == ".pdf":
        return content.startswith(b"%PDF-")
    if extension in {".jpg", ".jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".docx":
        return content.startswith(b"PK\x03\x04")
    return b"\x00" not in content[:4096]


def safe_original_name(value: str) -> str:
    name = value.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip().strip(".")
    return name[:255]


def validate_content_structure(extension: str, content: bytes, maximum_bytes: int) -> None:
    try:
        if extension == ".pdf":
            with pymupdf.open(stream=content, filetype="pdf") as document:
                if document.page_count < 1 or document.page_count > 2000:
                    raise ValueError("PDF page count is outside the allowed range")
        elif extension == ".docx":
            with zipfile.ZipFile(BytesIO(content)) as archive:
                infos = archive.infolist()
                names = {item.filename for item in infos}
                if len(infos) > 2000 or not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                    raise ValueError("DOCX package structure is invalid")
                expanded = sum(item.file_size for item in infos)
                if expanded > 100 * 1024 * 1024 or expanded > max(len(content) * 100, 5 * 1024 * 1024):
                    raise ValueError("DOCX expanded content is too large")
        elif extension in {".jpg", ".jpeg", ".png"}:
            with Image.open(BytesIO(content)) as image:
                width, height = image.size
                if width <= 0 or height <= 0 or width * height > 40_000_000:
                    raise ValueError("Image dimensions are outside the allowed range")
                image.verify()
        elif extension in {".txt", ".md"}:
            content.decode("utf-8-sig")
    except (pymupdf.FileDataError, zipfile.BadZipFile, UnidentifiedImageError, UnicodeDecodeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="The file is corrupted or has an unsafe internal structure") from exc


async def validate_upload(upload: UploadFile, maximum_bytes: int) -> ValidatedUpload:
    original_name = safe_original_name(upload.filename or "")
    extension = Path(original_name).suffix.casefold()
    if not original_name or extension not in ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="This file type is not supported")
    media_type = (upload.content_type or "application/octet-stream").casefold()
    if media_type not in ALLOWED_TYPES[extension]:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="The file type does not match its extension")
    content = await upload.read(maximum_bytes + 1)
    await upload.close()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty files cannot be uploaded")
    if len(content) > maximum_bytes:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="The uploaded file exceeds the size limit")
    if not signature_matches(extension, content):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="The file signature is invalid or corrupted")
    validate_content_structure(extension, content, maximum_bytes)
    return ValidatedUpload(original_name=original_name, extension=extension, media_type=media_type, content=content)
