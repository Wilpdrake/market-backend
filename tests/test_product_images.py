from io import BytesIO

from starlette.datastructures import Headers, UploadFile

from app.infrastructure.product_images import store_product_images


def image(filename: str, content: bytes) -> UploadFile:
    return UploadFile(
        BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": "image/jpeg"}),
    )


async def test_store_product_images_preserves_all_files_and_selects_cover(tmp_path) -> None:
    uploads = [image("front.jpg", b"front"), image("back.jpg", b"back")]

    stored = await store_product_images(uploads, cover_index=1, upload_dir=tmp_path)

    assert len(stored.urls) == 2
    assert stored.cover_url == stored.urls[1]
    assert [(tmp_path / url.removeprefix("/uploads/")).read_bytes() for url in stored.urls] == [
        b"front",
        b"back",
    ]
