# appkit-imagecreator

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Multi-provider AI image generation component for Reflex applications.**

appkit-imagecreator provides a unified interface for generating images using multiple AI providers including Google Gemini (Imagen), OpenAI (DALL-E/GPT-Image), and Black Forest Labs (FLUX). It includes a complete Reflex UI for image generation workflows with prompt enhancement, parameter controls, and image management features.

![Image Creator](https://raw.githubusercontent.com/jenreh/appkit/refs/heads/main/components/appkit-imagecreator/docs/imagecreator.jpeg)

---

## ✨ Features

- **Multi-Provider Support** - Google Gemini Imagen, OpenAI GPT-Image-1/DALL-E, Black Forest Labs FLUX
- **Unified API** - Consistent interface across all image generation providers
- **Prompt Enhancement** - AI-powered prompt improvement using GPT models
- **Interactive UI** - Complete image generation interface with canvas, sidebar controls, and image gallery
- **Parameter Control** - Configurable image dimensions, steps, negative prompts, and seeds
- **Image Management** - Download, copy, and organize generated images
- **Error Handling** - Robust error handling and user feedback
- **Streaming Support** - Real-time generation progress and results

---

## 🚀 Installation

### As Part of AppKit Workspace

If you're using the full AppKit workspace:

```bash
git clone https://github.com/jenreh/appkit.git
cd appkit
uv sync
```

### Standalone Installation

Install from PyPI:

```bash
pip install appkit-imagecreator
```

Or with uv:

```bash
uv add appkit-imagecreator
```

### Dependencies

- `google-genai>=1.26.0` (Google Gemini API)
- `httpx>=0.28.1` (HTTP client)
- `appkit-commons` (shared utilities)
- `openai>=2.3.0` (OpenAI API)

---

## 🏁 Quick Start

### Basic Configuration

Configure API keys for your preferred providers:

```python
from appkit_imagecreator.configuration import ImageGeneratorConfig

config = ImageGeneratorConfig(
    google_api_key="secret:google_api_key",
    openai_api_key="secret:openai_api_key",
    blackforestlabs_api_key="secret:blackforestlabs_api_key",
    tmp_dir="./generated_images"  # Optional: custom temp directory
)
```

### Using the Image Generator

Generate images using the registry:

```python
from appkit_imagecreator.backend.generator_registry import generator_registry
from appkit_imagecreator.backend.models import GenerationInput

# Get a generator
generator = generator_registry.get("gpt-image-1")

# Create generation input
input_data = GenerationInput(
    prompt="A beautiful sunset over mountains",
    width=1024,
    height=1024,
    negative_prompt="blurry, low quality",
    steps=4,
    enhance_prompt=True
)

# Generate image
response = await generator.generate(input_data)
if response.state == "succeeded":
    print(f"Generated images: {response.images}")
else:
    print(f"Error: {response.error}")
```

### Using the UI Component

Add the image generator page to your Reflex app:

```python
import reflex as rx
from appkit_imagecreator.pages import image_generator_page

app = rx.App()
app.add_page(image_generator_page, title="Image Generator", route="/images")
```

---

## 📖 Usage

### Generator Registry

The registry manages all available image generators:

```python
from appkit_imagecreator.backend.generator_registry import generator_registry

# List all generators
generators = generator_registry.list_generators()
print(generators)
# [{"id": "gpt-image-1", "label": "OpenAI GPT-Image-1"}, ...]

# Get a specific generator
generator = generator_registry.get("imagen-3")

# Get default generator
default_gen = generator_registry.get_default_generator()
```

### Generation Input

Configure image generation parameters:

```python
from appkit_imagecreator.backend.models import GenerationInput

input_data = GenerationInput(
    prompt="A cyberpunk city at night with neon lights",
    width=1024,      # Image width
    height=1024,     # Image height
    negative_prompt="blurry, distorted, ugly",  # What to avoid
    steps=4,         # Generation steps (higher = better quality)
    n=1,            # Number of images to generate
    seed=42,        # Random seed for reproducible results
    enhance_prompt=True  # Use AI to improve the prompt
)
```

### Custom Generators

Implement your own image generator:

```python
from appkit_imagecreator.backend.models import ImageGenerator, GenerationInput, ImageGeneratorResponse, ImageResponseState

class CustomGenerator(ImageGenerator):
    def __init__(self, api_key: str, backend_server: str):
        super().__init__(
            id="custom-gen",
            label="Custom Generator",
            model="custom-model",
            api_key=api_key,
            backend_server=backend_server
        )

    async def _perform_generation(self, input_data: GenerationInput) -> ImageGeneratorResponse:
        # Your generation logic here
        # Save image to temp and return URL
        image_url = await self._save_image_to_tmp_and_get_url(
            image_bytes, "custom", "png"
        )
        return ImageGeneratorResponse(
            state=ImageResponseState.SUCCEEDED,
            images=[image_url]
        )

# Register your generator
generator_registry.register(CustomGenerator(api_key, backend_server))
```

### UI Components

#### Main Page

The complete image generator interface:

```python
from appkit_imagecreator.pages import image_generator_page

# Add to your app
app.add_page(image_generator_page, route="/image-generator")
```

#### Individual Components

Use specific UI components:

```python
from appkit_imagecreator.components.canvas import image_ui
from appkit_imagecreator.components.sidebar import sidebar

def custom_layout():
    return rx.flex(
        sidebar(),      # Generation controls
        image_ui(),     # Image display canvas
        flex_direction="row"
    )
```

---

## 🔧 Configuration

### ImageGeneratorConfig

Configure API keys and settings:

```python
from appkit_imagecreator.configuration import ImageGeneratorConfig

config = ImageGeneratorConfig(
    google_api_key="secret:google_gemini_key",
    openai_api_key="secret:openai_key",
    blackforestlabs_api_key="secret:bfl_key",
    openai_base_url="https://api.openai.com/v1",  # Optional custom endpoint
    tmp_dir="./tmp/images"  # Temp directory for generated images
)
```

### Provider-Specific Setup

#### Google Gemini

Requires `google_api_key` for Imagen models:

```python
# Uses Imagen 3.0 by default
generator = generator_registry.get("imagen-3")
```

#### OpenAI

Supports DALL-E and GPT-Image-1:

```python
# GPT-Image-1 (default)
gpt_gen = generator_registry.get("gpt-image-1")

# Custom OpenAI-compatible endpoint
config.openai_base_url = "https://your-endpoint.com/v1"
```

#### Black Forest Labs

FLUX models for high-quality generation:

```python
flux_gen = generator_registry.get("FLUX-1.1-pro")
```

---

## 📋 API Reference

### Core Classes

- `ImageGenerator` - Abstract base class for image generators
- `GenerationInput` - Input parameters for image generation
- `ImageGeneratorResponse` - Response containing generated images or errors
- `ImageGeneratorRegistry` - Registry managing all generators

### Generators

- `GoogleImageGenerator` - Google Gemini Imagen integration
- `OpenAIImageGenerator` - OpenAI DALL-E/GPT-Image integration
- `BlackForestLabsGenerator` - Black Forest Labs FLUX integration

### Component API

- `image_generator_page()` - Complete image generation page
- `image_ui()` - Main image display and controls
- `sidebar()` - Generation parameter controls
- `image_list()` - Generated image gallery

### State Management

- `CopyLocalState` - State for image copy/download operations

---

## 🔒 Security

> [!IMPORTANT]
> API keys are handled securely using the appkit-commons configuration system. Never hardcode secrets in your code.

- Use `SecretStr` for API key configuration
- Secrets resolved from environment variables or Key Vault
- Temporary images stored securely with unique filenames
- No sensitive data logged in generation processes

---

## 🤝 Integration Examples

### With AppKit User Management

Restrict image generation to authenticated users:

```python
from appkit_user import authenticated, requires_role
from appkit_imagecreator.pages import image_generator_page

@authenticated()
@requires_role("image_generator")
def protected_image_page():
    return image_generator_page()
```

### Custom Prompt Enhancement

Override prompt enhancement logic:

```python
class CustomGenerator(OpenAIImageGenerator):
    async def _enhance_prompt(self, prompt: str) -> str:
        # Your custom enhancement logic
        enhanced = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Enhance this image prompt: {prompt}"}]
        )
        return enhanced.choices[0].message.content
```

### Batch Generation

Generate multiple images with different parameters:

```python
async def batch_generate(prompts: list[str]) -> list[str]:
    generator = generator_registry.get("gpt-image-1")
    images = []

    for prompt in prompts:
        input_data = GenerationInput(prompt=prompt, n=1)
        response = await generator.generate(input_data)
        if response.state == "succeeded":
            images.extend(response.images)

    return images
```

---

## 📚 Related Components

- **[appkit-mantine](./../appkit-mantine)** - UI components used in the image generator interface
- **[appkit-user](./../appkit-user)** - User authentication for protected image generation
- **[appkit-commons](./../appkit-commons)** - Shared utilities and configuration
- **[appkit-assistant](./../appkit-assistant)** - AI assistant that can integrate with image generation
