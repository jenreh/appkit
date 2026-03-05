"""Tests for REST API routes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from server.api.models import ImageResponse
from server.api.routes import (
    _build_error_response,
    _build_success_response,
    edit_image_route,
    generate_image_route,
    get_generator,
    router,
)
from server.backend.generators import OpenAIImageGenerator
from server.backend.models import EditImageInput, GenerationInput
from server.server import GENERATOR_ID


class TestGetGeneratorDependency:
    """Test generator dependency injection."""

    @pytest.mark.asyncio
    async def test_get_generator_success(self) -> None:
        """Test successful generator retrieval from app state."""
        # Create mock generator
        mock_generator = MagicMock(spec=OpenAIImageGenerator)

        # Create FastAPI app with generator in state
        app = FastAPI()
        app.state.generators = {GENERATOR_ID: mock_generator}

        # Create mock request with app
        mock_request = MagicMock()
        mock_request.app = app

        # Get generator
        result = get_generator(mock_request)

        assert result is mock_generator

    @pytest.mark.asyncio
    async def test_get_generator_not_found(self) -> None:
        """Test generator not found in app state raises HTTPException."""
        # Create FastAPI app without generator
        app = FastAPI()
        app.state.generators = {}

        # Create mock request with app
        mock_request = MagicMock()
        mock_request.app = app

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_generator(mock_request)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "not initialized" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_generator_no_generators_attr(self) -> None:
        """Test generator not found when app.state has no generators attribute."""
        # Create FastAPI app with empty state
        app = FastAPI()

        # Create mock request with app
        mock_request = MagicMock()
        mock_request.app = app

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_generator(mock_request)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestBuildSuccessResponse:
    """Test success response building."""

    def test_build_success_response_image_format(self) -> None:
        """Test building success response with image format."""
        # Create mock response object
        mock_response = MagicMock()
        mock_response.data = "image_data_string"

        response = _build_success_response(
            response_obj=mock_response,
            response_format="image",
            prompt="test prompt",
            size="1024x1024",
            processing_time_ms=1000,
            enhanced_prompt="enhanced prompt",
        )

        assert isinstance(response, ImageResponse)
        assert response.status == "success"
        assert response.data is not None
        assert response.data.images == ["image_data_string"]
        assert response.metadata is not None
        assert response.metadata.prompt == "test prompt"
        assert response.metadata.enhanced_prompt == "enhanced prompt"
        assert response.metadata.processing_time_ms == 1000
        assert response.error is None

    def test_build_success_response_markdown_format(self) -> None:
        """Test building success response with markdown format."""
        # Create markdown response
        markdown_content = "# Image\n![img](data:image/png;base64,...)"

        response = _build_success_response(
            response_obj=markdown_content,
            response_format="markdown",
            prompt="test prompt",
            size="1024x1024",
            processing_time_ms=500,
        )

        assert response.status == "success"
        assert response.data is not None
        assert response.data.markdown == markdown_content
        assert response.data.adaptive_card is None

    def test_build_success_response_adaptive_card_format(self) -> None:
        """Test building success response with adaptive card format."""
        # Create adaptive card response
        card_json = '{"type": "AdaptiveCard", "body": []}'

        response = _build_success_response(
            response_obj=card_json,
            response_format="adaptive_card",
            prompt="test prompt",
            size="1024x1024",
            processing_time_ms=750,
        )

        assert response.status == "success"
        assert response.data is not None
        assert response.data.adaptive_card == {"type": "AdaptiveCard", "body": []}

    def test_build_success_response_without_enhanced_prompt(self) -> None:
        """Test building success response without enhanced prompt."""
        mock_response = MagicMock()
        mock_response.data = "image_data"

        response = _build_success_response(
            response_obj=mock_response,
            response_format="image",
            prompt="test prompt",
            size="512x512",
            processing_time_ms=100,
        )

        assert response.metadata is not None
        assert response.metadata.enhanced_prompt is None


class TestErrorResponse:
    """Test error response building."""

    def test_error_response_creation(self) -> None:
        """Test creating error response."""
        response = _build_error_response(
            prompt="test prompt",
            size="1024x1024",
            response_format="image",
            code="GENERATION_FAILED",
            message="Generation failed",
            details="API rate limit exceeded",
        )

        assert response.status == "error"
        assert response.data is None
        assert response.error is not None
        assert response.error.code == "GENERATION_FAILED"
        assert response.error.message == "Generation failed"
        assert response.error.details == "API rate limit exceeded"

    def test_error_response_without_details(self) -> None:
        """Test error response without additional details."""
        response = _build_error_response(
            prompt="test",
            size="1024x1024",
            response_format="image",
            code="ERROR",
            message="Something went wrong",
        )

        assert response.error is not None
        assert response.error.details == ""


class TestGenerateImageRoute:
    """Test image generation REST endpoint."""

    @pytest.mark.asyncio
    async def test_generate_image_success(self) -> None:
        """Test successful image generation via REST API."""
        # Create mock generator
        mock_generator = AsyncMock(spec=OpenAIImageGenerator)

        # Create test request
        request_data = GenerationInput(
            prompt="A red ball",
            size="1024x1024",
            response_format="image",
        )

        # Mock generate_image_impl to return image URL and enhanced prompt
        with patch(
            "server.api.routes.generate_image_impl",
            new_callable=AsyncMock,
        ) as mock_gen_impl:
            mock_gen_impl.return_value = (
                "data:image/png;base64,iVBORw0KGgo...",
                "A vibrant red ball",
            )

            # Mock generate_response to return image object
            with patch(
                "server.api.routes.generate_response",
                new_callable=AsyncMock,
            ) as mock_gen_response:
                mock_image = MagicMock()
                mock_image.data = "image_bytes"
                mock_gen_response.return_value = mock_image

                # Call route
                response = await generate_image_route(request_data, mock_generator)

        assert isinstance(response, ImageResponse)
        assert response.status == "success"
        assert response.data is not None
        assert response.metadata is not None
        assert response.metadata.enhanced_prompt == "A vibrant red ball"

    @pytest.mark.asyncio
    async def test_generate_image_with_markdown_format(self) -> None:
        """Test image generation with markdown response format."""
        mock_generator = AsyncMock(spec=OpenAIImageGenerator)

        request_data = GenerationInput(
            prompt="A blue cube",
            size="1024x1024",
            response_format="markdown",
        )

        with patch(
            "server.api.routes.generate_image_impl",
            new_callable=AsyncMock,
        ) as mock_gen_impl:
            # Return with enhanced prompt
            mock_gen_impl.return_value = ("image_url", "Enhanced prompt")

            with patch(
                "server.api.routes.generate_response",
                new_callable=AsyncMock,
            ) as mock_gen_response:
                mock_gen_response.return_value = "# Generated Image\n![img](url)"

                response = await generate_image_route(request_data, mock_generator)

        assert response.status == "success"
        assert response.data is not None
        assert response.data.markdown == "# Generated Image\n![img](url)"

    @pytest.mark.asyncio
    async def test_generate_image_with_http_exception(self) -> None:
        """Test generation route propagates HTTPException."""
        mock_generator = AsyncMock(spec=OpenAIImageGenerator)

        request_data = GenerationInput(prompt="test")

        with patch(
            "server.api.routes.generate_image_impl",
            new_callable=AsyncMock,
        ) as mock_gen_impl:
            # Raise HTTPException
            mock_gen_impl.side_effect = HTTPException(
                status_code=400, detail="Bad request"
            )

            with pytest.raises(HTTPException) as exc_info:
                await generate_image_route(request_data, mock_generator)

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_image_with_general_exception(self) -> None:
        """Test generation route catches general exceptions."""
        mock_generator = AsyncMock(spec=OpenAIImageGenerator)

        request_data = GenerationInput(prompt="test")

        with patch(
            "server.api.routes.generate_image_impl",
            new_callable=AsyncMock,
        ) as mock_gen_impl:
            # Raise generic exception
            mock_gen_impl.side_effect = RuntimeError("Unexpected error")

            response = await generate_image_route(request_data, mock_generator)

        assert response.status == "error"
        assert response.error is not None
        assert response.error.code == "INTERNAL_ERROR"
        assert "Internal server error" in response.error.message

    @pytest.mark.asyncio
    async def test_generate_image_logs_operation(self) -> None:
        """Test that generation logs the operation."""
        mock_generator = AsyncMock(spec=OpenAIImageGenerator)

        request_data = GenerationInput(
            prompt="test",
            response_format="image",
        )

        with patch(
            "server.api.routes.generate_image_impl",
            new_callable=AsyncMock,
        ) as mock_gen_impl:
            # Return valid enhanced prompt
            mock_gen_impl.return_value = ("image_url", "Enhanced prompt")

            with patch(
                "server.api.routes.generate_response",
                new_callable=AsyncMock,
            ) as mock_gen_response:
                mock_image = MagicMock()
                mock_image.data = "bytes"
                mock_gen_response.return_value = mock_image

                with patch("server.api.routes.logger") as mock_logger:
                    response = await generate_image_route(request_data, mock_generator)

                    # Verify logging calls
                    assert mock_logger.info.called
                    # Should have success response
                    assert response.status == "success"


class TestEditImageRoute:
    """Test image editing REST endpoint."""

    @pytest.mark.asyncio
    async def test_edit_image_success(self) -> None:
        """Test successful image editing via REST API."""
        mock_generator = AsyncMock(spec=OpenAIImageGenerator)

        request_data = EditImageInput(
            prompt="Add more detail",
            image_paths=["test_image.png"],
            size="1024x1024",
            response_format="image",
        )

        with patch(
            "server.api.routes.edit_image_impl",
            new_callable=AsyncMock,
        ) as mock_edit_impl:
            mock_edit_impl.return_value = "edited_image_url"

            with patch(
                "server.api.routes.generate_response",
                new_callable=AsyncMock,
            ) as mock_gen_response:
                mock_image = MagicMock()
                mock_image.data = "edited_bytes"
                mock_gen_response.return_value = mock_image

                response = await edit_image_route(request_data, mock_generator)

        assert response.status == "success"
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_edit_image_with_mask(self) -> None:
        """Test image editing with mask."""
        mock_generator = AsyncMock(spec=OpenAIImageGenerator)

        request_data = EditImageInput(
            prompt="Replace background",
            image_paths=["image.png"],
            mask_path="mask.png",
            size="1024x1024",
            response_format="markdown",
        )

        with patch(
            "server.api.routes.edit_image_impl",
            new_callable=AsyncMock,
        ) as mock_edit_impl:
            mock_edit_impl.return_value = "edited_url"

            with patch(
                "server.api.routes.generate_response",
                new_callable=AsyncMock,
            ) as mock_gen_response:
                mock_gen_response.return_value = "# Edited\n![](url)"

                response = await edit_image_route(request_data, mock_generator)

        assert response.status == "success"
        assert response.data is not None
        assert response.data.markdown == "# Edited\n![](url)"

    @pytest.mark.asyncio
    async def test_edit_image_http_exception(self) -> None:
        """Test edit route propagates HTTPException."""
        mock_generator = AsyncMock(spec=OpenAIImageGenerator)

        request_data = EditImageInput(
            prompt="test",
            image_paths=["image.png"],
        )

        with patch(
            "server.api.routes.edit_image_impl",
            new_callable=AsyncMock,
        ) as mock_edit_impl:
            mock_edit_impl.side_effect = HTTPException(
                status_code=404, detail="Image not found"
            )

            with pytest.raises(HTTPException) as exc_info:
                await edit_image_route(request_data, mock_generator)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_edit_image_general_exception(self) -> None:
        """Test edit route catches general exceptions."""
        mock_generator = AsyncMock(spec=OpenAIImageGenerator)

        request_data = EditImageInput(
            prompt="test",
            image_paths=["test.png"],
        )

        with patch(
            "server.api.routes.edit_image_impl",
            new_callable=AsyncMock,
        ) as mock_edit_impl:
            mock_edit_impl.side_effect = ValueError("Invalid image format")

            response = await edit_image_route(request_data, mock_generator)

        assert response.status == "error"
        assert response.error is not None
        assert response.error.code == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    async def test_edit_image_logs_operation(self) -> None:
        """Test that editing logs the operation."""
        mock_generator = AsyncMock(spec=OpenAIImageGenerator)

        request_data = EditImageInput(
            prompt="test",
            image_paths=["image.png"],
            response_format="image",
        )

        with patch(
            "server.api.routes.edit_image_impl",
            new_callable=AsyncMock,
        ) as mock_edit_impl:
            mock_edit_impl.return_value = "image_url"

            with patch(
                "server.api.routes.generate_response",
                new_callable=AsyncMock,
            ) as mock_gen_response:
                mock_image = MagicMock()
                mock_image.data = "bytes"
                mock_gen_response.return_value = mock_image

                with patch("server.api.routes.logger") as mock_logger:
                    await edit_image_route(request_data, mock_generator)

                    assert mock_logger.info.called


class TestAPIIntegration:
    """Integration tests for API routes with FastAPI app."""

    @pytest.fixture
    def api_app(self) -> FastAPI:
        """Create FastAPI app with mocked generator for testing."""
        app = FastAPI()
        app.include_router(router)

        # Create mock generator
        mock_generator = MagicMock(spec=OpenAIImageGenerator)

        # Store in app state
        app.state.generators = {GENERATOR_ID: mock_generator}

        return app

    @pytest.fixture
    def client(self, api_app: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(api_app)

    def test_generate_image_endpoint_exists(self, client: TestClient) -> None:
        """Test that generate_image endpoint is registered."""
        # Check that endpoint is available by looking at routes
        routes = [route.path for route in client.app.routes]
        assert "/generate_image" in routes

    def test_edit_image_endpoint_exists(self, client: TestClient) -> None:
        """Test that edit_image endpoint is registered."""
        routes = [route.path for route in client.app.routes]
        assert "/edit_image" in routes

    @pytest.mark.asyncio
    async def test_generate_image_request_validation(self) -> None:
        """Test that generation endpoint validates requests properly."""
        app = FastAPI()
        app.include_router(router)

        mock_generator = MagicMock(spec=OpenAIImageGenerator)
        app.state.generators = {GENERATOR_ID: mock_generator}

        client = TestClient(app)

        # Send request with invalid format
        response = client.post(
            "/generate_image",
            json={
                "prompt": "test",
                "size": "invalid_size",  # Invalid size
            },
        )

        # Should fail validation
        assert response.status_code in [400, 422]

    def test_response_metadata_includes_timestamp(self) -> None:
        """Test that response includes timestamp in metadata."""
        # Response metadata should include timestamp
        mock_response = _build_success_response(
            response_obj=MagicMock(data="test"),
            response_format="image",
            prompt="test",
            size="1024x1024",
            processing_time_ms=100,
        )

        assert mock_response.metadata is not None
        assert mock_response.metadata.timestamp is not None
        # Timestamp should be ISO format
        assert "T" in mock_response.metadata.timestamp

    def test_response_includes_processing_time(self) -> None:
        """Test that response includes processing time."""
        mock_response = _build_success_response(
            response_obj=MagicMock(data="test"),
            response_format="image",
            prompt="test",
            size="1024x1024",
            processing_time_ms=250,
        )

        assert mock_response.metadata is not None
        assert mock_response.metadata.processing_time_ms == 250
