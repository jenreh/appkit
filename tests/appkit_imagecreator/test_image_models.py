"""Tests for image creator models."""

from datetime import UTC, datetime

import pytest

from appkit_imagecreator.backend.models import (
    GeneratedImage,
    GeneratedImageData,
    GeneratedImageModel,
    GenerationInput,
    ImageGenerator,
    ImageGeneratorResponse,
    ImageModel,
    ImageResponseState,
)


class TestImageGeneratorModel:
    """Test suite for ImageGeneratorModel."""

    @pytest.mark.asyncio
    async def test_create_image_generator_model(
        self, image_generator_model_factory
    ) -> None:
        """ImageGeneratorModel can be created with required fields."""
        # Act
        model = await image_generator_model_factory(
            model_id="test-dall-e",
            model="dall-e-3",
            label="DALL-E 3",
            processor_type="appkit_imagecreator.backend.generators.openai.OpenAIImageGenerator",
        )

        # Assert
        assert model.id is not None
        assert model.model_id == "test-dall-e"
        assert model.model == "dall-e-3"
        assert model.label == "DALL-E 3"
        assert model.active is True

    @pytest.mark.asyncio
    async def test_api_key_encrypted(self, image_generator_model_factory) -> None:
        """API key is stored encrypted."""
        # Arrange
        plain_key = "sk-test-key-12345"

        # Act
        model = await image_generator_model_factory(api_key=plain_key)

        # Assert
        assert model.api_key == plain_key  # Decrypts when accessed
        # Note: Actual encryption is tested at the database level

    @pytest.mark.asyncio
    async def test_to_image_model_conversion(
        self, image_generator_model_factory
    ) -> None:
        """to_image_model converts DB entity to runtime ImageModel."""
        # Arrange
        model = await image_generator_model_factory(
            model_id="test-model",
            model="dall-e-3",
            label="Test Model",
            required_role="premium",
            extra_config={"output_format": "png", "quality": "hd"},
        )

        # Act
        image_model = model.to_image_model()

        # Assert
        assert isinstance(image_model, ImageModel)
        assert image_model.id == "test-model"
        assert image_model.model == "dall-e-3"
        assert image_model.label == "Test Model"
        assert image_model.required_role == "premium"
        assert image_model.config == {"output_format": "png", "quality": "hd"}

    @pytest.mark.asyncio
    async def test_to_image_model_filters_non_api_keys(
        self, image_generator_model_factory
    ) -> None:
        """to_image_model excludes non-API keys from config."""
        # Arrange
        model = await image_generator_model_factory(
            extra_config={
                "on_azure": True,  # Non-API key (for instantiation only)
                "quality": "hd",  # API parameter
                "output_format": "png",  # API parameter
            }
        )

        # Act
        image_model = model.to_image_model()

        # Assert
        assert "on_azure" not in image_model.config
        assert image_model.config == {"quality": "hd", "output_format": "png"}

    @pytest.mark.asyncio
    async def test_default_values(self, image_generator_model_factory) -> None:
        """ImageGeneratorModel has correct default values."""
        # Act
        model = await image_generator_model_factory()

        # Assert
        assert model.active is True
        assert model.base_url is None
        assert model.required_role is None
        assert model.created_at is not None

    @pytest.mark.asyncio
    async def test_unique_model_id_constraint(
        self, image_generator_model_factory
    ) -> None:
        """model_id must be unique."""
        # Arrange
        model_id = "duplicate-model-id"
        await image_generator_model_factory(model_id=model_id)

        # Act & Assert
        with pytest.raises(Exception):  # IntegrityError
            await image_generator_model_factory(model_id=model_id)


class TestGeneratedImage:
    """Test suite for GeneratedImage."""

    @pytest.mark.asyncio
    async def test_create_generated_image(
        self, generated_image_factory, sample_image_bytes
    ) -> None:
        """GeneratedImage can be created with required fields."""
        # Act
        image = await generated_image_factory(
            user_id=1,
            prompt="A test image",
            model="dall-e-3",
            image_data=sample_image_bytes,
            width=1024,
            height=1024,
        )

        # Assert
        assert image.id is not None
        assert image.user_id == 1
        assert image.prompt == "A test image"
        assert image.model == "dall-e-3"
        assert image.image_data == sample_image_bytes
        assert image.width == 1024
        assert image.height == 1024

    @pytest.mark.asyncio
    async def test_default_values(self, generated_image_factory) -> None:
        """GeneratedImage has correct default values."""
        # Act
        image = await generated_image_factory()

        # Assert
        assert image.is_uploaded is False
        assert image.is_deleted is False
        assert image.content_type == "image/png"
        assert image.created_at is not None

    @pytest.mark.asyncio
    async def test_optional_fields(self, generated_image_factory) -> None:
        """Optional fields can be set."""
        # Act
        image = await generated_image_factory(
            enhanced_prompt="Enhanced version of prompt",
            style="artistic",
            quality="hd",
            config={"steps": 50, "guidance_scale": 7.5},
        )

        # Assert
        assert image.enhanced_prompt == "Enhanced version of prompt"
        assert image.style == "artistic"
        assert image.quality == "hd"
        assert image.config == {"steps": 50, "guidance_scale": 7.5}

    @pytest.mark.asyncio
    async def test_soft_delete_pattern(self, generated_image_factory) -> None:
        """is_deleted flag enables soft delete pattern."""
        # Arrange
        image = await generated_image_factory()

        # Act
        image.is_deleted = True

        # Assert
        assert image.is_deleted is True


class TestGeneratedImageModel:
    """Test suite for GeneratedImageModel Pydantic model."""

    def test_from_db_entity(self, sample_image_bytes) -> None:
        """GeneratedImageModel can be created from GeneratedImage entity."""
        # Arrange
        db_image = GeneratedImage(
            id=1,
            user_id=2,
            prompt="Test prompt",
            model="dall-e-3",
            image_data=sample_image_bytes,
            content_type="image/png",
            width=1024,
            height=1024,
            created_at=datetime.now(UTC),
        )

        # Act
        pydantic_model = GeneratedImageModel.model_validate(db_image)

        # Assert
        assert pydantic_model.id == 1
        assert pydantic_model.user_id == 2
        assert pydantic_model.prompt == "Test prompt"
        assert pydantic_model.model == "dall-e-3"

    def test_image_url_computed_field(self, sample_image_bytes) -> None:
        """image_url computed field generates correct URL."""
        # Arrange
        model = GeneratedImageModel(
            id=42,
            user_id=1,
            prompt="Test",
            model="dall-e-3",
            width=1024,
            height=1024,
        )

        # Act
        url = model.image_url

        # Assert
        assert url.endswith("/api/images/42")
        assert "images/42" in url


class TestImageModel:
    """Test suite for ImageModel."""

    def test_create_image_model(self) -> None:
        """ImageModel can be created with required fields."""
        # Act
        model = ImageModel(
            id="test-model",
            model="dall-e-3",
            label="Test Model",
            config={"quality": "hd"},
            required_role="admin",
        )

        # Assert
        assert model.id == "test-model"
        assert model.model == "dall-e-3"
        assert model.label == "Test Model"
        assert model.config == {"quality": "hd"}
        assert model.required_role == "admin"

    def test_optional_fields_default_to_none(self) -> None:
        """Optional fields default to None."""
        # Act
        model = ImageModel(id="test", model="dall-e-3", label="Test")

        # Assert
        assert model.config is None
        assert model.required_role is None


class TestGenerationInput:
    """Test suite for GenerationInput."""

    def test_default_values(self) -> None:
        """GenerationInput has sensible defaults."""
        # Act
        input_data = GenerationInput(prompt="Generate an image")

        # Assert
        assert input_data.prompt == "Generate an image"
        assert input_data.negative_prompt == ""
        assert input_data.width == 1024
        assert input_data.height == 1024
        assert input_data.steps == 4
        assert input_data.n == 1
        assert input_data.seed == 0
        assert input_data.enhance_prompt is True
        assert input_data.reference_image_ids == []

    def test_custom_values(self) -> None:
        """GenerationInput accepts custom values."""
        # Act
        input_data = GenerationInput(
            prompt="Test prompt",
            negative_prompt="Avoid this",
            width=512,
            height=768,
            steps=50,
            n=4,
            seed=42,
            enhance_prompt=False,
            reference_image_ids=[1, 2, 3],
        )

        # Assert
        assert input_data.width == 512
        assert input_data.height == 768
        assert input_data.steps == 50
        assert input_data.n == 4
        assert input_data.seed == 42
        assert input_data.enhance_prompt is False
        assert input_data.reference_image_ids == [1, 2, 3]


class TestGeneratedImageData:
    """Test suite for GeneratedImageData."""

    def test_with_image_bytes(self, sample_image_bytes) -> None:
        """GeneratedImageData with image_bytes."""
        # Act
        data = GeneratedImageData(
            image_bytes=sample_image_bytes, content_type="image/png"
        )

        # Assert
        assert data.image_bytes == sample_image_bytes
        assert data.external_url is None
        assert data.content_type == "image/png"

    def test_with_external_url(self) -> None:
        """GeneratedImageData with external URL."""
        # Act
        data = GeneratedImageData(
            external_url="https://example.com/image.png", content_type="image/jpeg"
        )

        # Assert
        assert data.image_bytes is None
        assert data.external_url == "https://example.com/image.png"
        assert data.content_type == "image/jpeg"


class TestImageGeneratorResponse:
    """Test suite for ImageGeneratorResponse."""

    def test_success_response(self, sample_image_bytes) -> None:
        """ImageGeneratorResponse for successful generation."""
        # Arrange
        image_data = GeneratedImageData(image_bytes=sample_image_bytes)

        # Act
        response = ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            generated_images=[image_data],
            enhanced_prompt="An enhanced prompt",
        )

        # Assert
        assert response.state == ImageResponseState.SUCCEEDED
        assert len(response.generated_images) == 1
        assert response.enhanced_prompt == "An enhanced prompt"
        assert response.error == ""

    def test_failure_response(self) -> None:
        """ImageGeneratorResponse for failed generation."""
        # Act
        response = ImageGeneratorResponse(
            state=ImageResponseState.FAILED,
            generated_images=[],
            error="API rate limit exceeded",
        )

        # Assert
        assert response.state == ImageResponseState.FAILED
        assert response.generated_images == []
        assert response.error == "API rate limit exceeded"


class TestImageGenerator:
    """Test suite for ImageGenerator base class."""

    def test_format_prompt_without_negative(self) -> None:
        """_format_prompt with no negative prompt."""
        # Arrange
        model = ImageModel(id="test", model="dall-e-3", label="Test")
        generator = ImageGenerator(model=model, api_key="test-key")

        # Act
        result = generator._format_prompt("A beautiful sunset")

        # Assert
        assert result == "A beautiful sunset"

    def test_format_prompt_with_negative(self) -> None:
        """_format_prompt includes negative prompt."""
        # Arrange
        model = ImageModel(id="test", model="dall-e-3", label="Test")
        generator = ImageGenerator(model=model, api_key="test-key")

        # Act
        result = generator._format_prompt(
            "A beautiful sunset", negative_prompt="No people"
        )

        # Assert
        assert "## Image Prompt:" in result
        assert "A beautiful sunset" in result
        assert "## Negative Prompt" in result
        assert "No people" in result

    def test_aspect_ratio_square(self) -> None:
        """_aspect_ratio calculates 1:1 for square dimensions."""
        # Arrange
        model = ImageModel(id="test", model="dall-e-3", label="Test")
        generator = ImageGenerator(model=model, api_key="test-key")

        # Act
        ratio = generator._aspect_ratio(1024, 1024)

        # Assert
        assert ratio == "1:1"

    def test_aspect_ratio_landscape(self) -> None:
        """_aspect_ratio calculates 2:1 for landscape."""
        # Arrange
        model = ImageModel(id="test", model="dall-e-3", label="Test")
        generator = ImageGenerator(model=model, api_key="test-key")

        # Act
        ratio = generator._aspect_ratio(2048, 1024)

        # Assert
        assert ratio == "2:1"

    def test_aspect_ratio_portrait(self) -> None:
        """_aspect_ratio calculates 1:2 for portrait."""
        # Arrange
        model = ImageModel(id="test", model="dall-e-3", label="Test")
        generator = ImageGenerator(model=model, api_key="test-key")

        # Act
        ratio = generator._aspect_ratio(1024, 2048)

        # Assert
        assert ratio == "1:2"

    def test_create_generated_image_data(self, sample_image_bytes) -> None:
        """_create_generated_image_data creates correct structure."""
        # Arrange
        model = ImageModel(id="test", model="dall-e-3", label="Test")
        generator = ImageGenerator(model=model, api_key="test-key")

        # Act
        result = generator._create_generated_image_data(sample_image_bytes, "image/png")

        # Assert
        assert result.image_bytes == sample_image_bytes
        assert result.content_type == "image/png"

    @pytest.mark.asyncio
    async def test_generate_calls_perform_generation(self) -> None:
        """generate method calls _perform_generation."""
        # Arrange
        model = ImageModel(id="test", model="dall-e-3", label="Test")

        class TestGenerator(ImageGenerator):
            async def _perform_generation(self, input_data):
                return ImageGeneratorResponse(
                    state=ImageResponseState.SUCCEEDED, generated_images=[]
                )

        generator = TestGenerator(model=model, api_key="test-key")
        input_data = GenerationInput(prompt="Test")

        # Act
        response = await generator.generate(input_data)

        # Assert
        assert response.state == ImageResponseState.SUCCEEDED

    @pytest.mark.asyncio
    async def test_generate_handles_exceptions(self) -> None:
        """generate catches exceptions and returns failed response."""
        # Arrange
        model = ImageModel(id="test", model="dall-e-3", label="Test")

        class FailingGenerator(ImageGenerator):
            async def _perform_generation(self, input_data):
                raise ValueError("API error")

        generator = FailingGenerator(model=model, api_key="test-key")
        input_data = GenerationInput(prompt="Test")

        # Act
        response = await generator.generate(input_data)

        # Assert
        assert response.state == ImageResponseState.FAILED
        assert "API error" in response.error

    @pytest.mark.asyncio
    async def test_edit_requires_supports_edit_true(self) -> None:
        """edit returns error when supports_edit is False."""
        # Arrange
        model = ImageModel(id="test", model="dall-e-3", label="Test")
        generator = ImageGenerator(model=model, api_key="test-key", supports_edit=False)
        input_data = GenerationInput(prompt="Test")

        # Act
        response = await generator.edit(input_data, [])

        # Assert
        assert response.state == ImageResponseState.FAILED
        assert "nicht unterstützt" in response.error.lower()

    @pytest.mark.asyncio
    async def test_edit_calls_perform_edit(self) -> None:
        """edit method calls _perform_edit when supported."""
        # Arrange
        model = ImageModel(id="test", model="dall-e-3", label="Test")

        class TestGenerator(ImageGenerator):
            async def _perform_edit(self, input_data, reference_images):
                return ImageGeneratorResponse(
                    state=ImageResponseState.SUCCEEDED, generated_images=[]
                )

        generator = TestGenerator(model=model, api_key="test-key", supports_edit=True)
        input_data = GenerationInput(prompt="Test")

        # Act
        response = await generator.edit(input_data, [(b"fake", "image/png")])

        # Assert
        assert response.state == ImageResponseState.SUCCEEDED
