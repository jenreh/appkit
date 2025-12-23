"""API endpoints for serving generated images."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from appkit_imagecreator.backend.repository import GeneratedImageRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/{image_id}")
async def get_image(image_id: int) -> Response:
    """Serve a generated image by ID.

    Args:
        image_id: The database ID of the image to retrieve.

    Returns:
        The image binary data with appropriate content type.

    Raises:
        HTTPException: If the image is not found.
    """
    result = await GeneratedImageRepository.get_image_data(image_id)

    if result is None:
        logger.warning("Image not found: %d", image_id)
        raise HTTPException(status_code=404, detail="Image not found")

    image_data, content_type = result

    return Response(
        content=image_data,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=31536000",  # Cache for 1 year
            "Content-Disposition": f'inline; filename="image_{image_id}.png"',
        },
    )
