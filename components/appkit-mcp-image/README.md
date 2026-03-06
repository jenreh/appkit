# Image Generation MCP Server

A FastMCP server for generating and editing images using OpenAI's **gpt-image-1** and Azure **FLUX.1-Kontext-pro** models. This component is part of the **AppKit** platform and is designed to be integrated into the main application.

## Features

- **Text-to-Image Generation**: Create images from natural language prompts using multiple AI models
- **Image Editing & Inpainting**: Edit existing images with text prompts and optional masks (gpt-image-1)
- **Multiple Formats**: Output as PNG, JPEG, or WEBP with customizable quality
- **Prompt Enhancement**: Auto-refine prompts via LLM for better results

## Configuration

This component uses `AppKit`'s configuration system (`appkit_commons`) and is configured via `MCPImageGeneratorConfig`. The settings are loaded from `configuration/config.yaml` or environment variables mapped by `appkit_commons`.

### Settings

| Setting | Description | Default |
| :--- | :--- | :--- |
| `backend_server` | URL of the backend server (for retrieving images) | `http://localhost:8000` |
| `max_file_size_mb` | Maximum allowed file size for input images | `10` |
| `max_images_to_keep` | Storage retention limit for generated images | `50` |
| `generator` | Active image generator backend (`azure` or `google`) | `azure` |
| `azure_api_key` | Azure OpenAI API key | `None` |
| `azure_base_url` | Azure OpenAI endpoint URL | `None` |
| `azure_prompt_optimizer` | LLM model used for prompt enhancement (Azure) | `gpt-5-mini` |
| `azure_image_model` | Image generation model identifier (Azure) | `FLUX.1-Kontext-pro` |
| `google_api_key` | Google AI API key | `None` |
| `google_prompt_optimizer` | LLM model used for prompt enhancement (Google) | `gemini-2.0-flash-001` |
| `google_image_model` | Image generation model identifier (Google) | `imagen-4.0-generate-preview-06-06` |
| `auth_tokens` | List of MCP tokens and scopes for authentication | `[]` |

## Integration

This module is designed to be integrated into the main `AppKit` application rather than running standalone. The `create_image_mcp_server` function returns a configured `FastMCP` instance which is mounted by the main application.

### Usage in AppKit

In `app/app.py`, the server is initialized effectively as follows:

```python
from appkit_commons.registry import service_registry
from appkit_user.authentication.services import get_verifier
from appkit_mcp_image.server import create_image_mcp_server, init_generators
from appkit_mcp_image.configuration import MCPImageGeneratorConfig

# ... inside initialization ...
image_mcp_config = service_registry().get(MCPImageGeneratorConfig)
_generators = init_generators(image_mcp_config)

# Create and mount the MCP server
servers["/image"] = create_image_mcp_server(
    _generators[image_mcp_config.generator],
    auth=get_verifier(),
)
```

## Tools & API

### generate_image

Create images from text descriptions.

**Parameters:**

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `prompt` | string | required | Image description (max 32,000 chars) |
| `size` | string | `1024x1024` | Dimensions: `1024x1024`, `1536x1024`, `1024x1536`, or `auto` |
| `output_format` | string | `jpeg` | Output format: `png`, `jpeg`, or `webp` |
| `seed` | integer | `0` | Random seed for reproducibility (0 = random) |
| `enhance_prompt` | boolean | `true` | Auto-enhance prompt via LLM |
| `background` | string | `auto` | Background: `transparent`, `opaque`, or `auto` |

**Example:**

```python
generate_image(
    prompt="A serene mountain landscape at sunset with golden light reflecting off a lake",
    size="1536x1024",
    output_format="png",
    enhance_prompt=True
)
```

### edit_image

Edit existing images with text prompts and optional masks for inpainting.

**Parameters:**

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `prompt` | string | required | Description of desired edits (max 32,000 chars) |
| `image_paths` | array | required | Image URLs, file paths, or base64 data URLs (max 16) |
| `mask_path` | string | optional | Optional mask image for inpainting (transparent areas indicate edit zones) |
| `size` | string | `auto` | Output dimensions |
| `output_format` | string | `jpeg` | Output format: `png`, `jpeg`, or `webp` |
| `background` | string | `auto` | Background setting |

**Example:**

```python
edit_image(
    prompt="Add a vibrant rainbow across the sky",
    image_paths=["https://example.com/landscape.jpg"],
    mask_path="https://example.com/sky_mask.png",
    output_format="png"
)
```

## Image Input Formats

Supported input methods for `image_paths` parameter:

- **HTTP/HTTPS URLs**: `https://example.com/image.jpg`
- **Local file paths**: `/path/to/image.png`
- **Base64 data URLs**: `data:image/png;base64,iVBORw0KG...`

## Inpainting with Masks

For precise control over edits, use mask images:

1. Create a PNG image with alpha transparency
2. Transparent areas (alpha=0) mark regions to edit
3. Opaque areas remain unchanged
4. Mask dimensions must match the input image

## License

This project is licensed under the MIT License - see [LICENSE.md](LICENSE.md) for details.
