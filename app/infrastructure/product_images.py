from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from anyio import to_thread
from fastapi import HTTPException, status
from starlette.datastructures import UploadFile

MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@dataclass(frozen=True, slots=True)
class StoredProductImages:
    urls: list[str]
    cover_url: str


async def store_product_images(
    images: list[UploadFile],
    *,
    cover_index: int,
    upload_dir: Path,
) -> StoredProductImages:
    if not images:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No images sent",
        )
    if cover_index < 0 or cover_index >= len(images):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="cover_index is outside the uploaded images",
        )

    product_dir = upload_dir / "products"
    await to_thread.run_sync(product_dir.mkdir, 0o755, True, True)
    stored_paths: list[Path] = []
    try:
        for image in images:
            extension = IMAGE_EXTENSIONS.get(image.content_type or "")
            if extension is None:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Product images must be JPEG, PNG, or WebP",
                )
            content = await image.read(MAX_IMAGE_BYTES + 1)
            if len(content) > MAX_IMAGE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="Each product image must be at most 10 MB",
                )
            path = product_dir / f"{uuid4().hex}{extension}"
            await to_thread.run_sync(path.write_bytes, content)
            stored_paths.append(path)
    except Exception:
        for path in stored_paths:
            await to_thread.run_sync(path.unlink, True)
        raise

    urls = [f"/uploads/products/{path.name}" for path in stored_paths]
    return StoredProductImages(urls=urls, cover_url=urls[cover_index])


async def delete_product_images(urls: list[str], *, upload_dir: Path) -> None:
    prefix = "/uploads/products/"
    for url in urls:
        if url.startswith(prefix):
            path = upload_dir / "products" / Path(url).name
            await to_thread.run_sync(path.unlink, True)
