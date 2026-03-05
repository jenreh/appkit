# Image Generation MCP Server

A FastMCP server for generating and editing images using OpenAI's **gpt-image-1** and
Azure **FLUX.1-Kontext-pro** models. Deploy as an MCP tool or use REST endpoints for
flexible integration with AI assistants and applications.

## Features

- **Text-to-Image Generation**: Create images from natural language prompts using multiple AI models
- **Image Editing & Inpainting**: Edit existing images with text prompts and optional masks (gpt-image-1)
- **Multiple Formats**: Output as PNG, JPEG, or WEBP with customizable quality
- **Flexible Response Formats**: Receive results as MCP Images, Markdown, or Microsoft Adaptive Cards
- **Prompt Enhancement**: Auto-refine prompts via LLM for better results
- **Dual Protocol**: Access via MCP protocol for AI assistants or REST API for direct integration

## Quick Start

### Prerequisites

- Python 3.12 or later
- [**uv**](https://docs.astral.sh/uv/) package manager
- API keys:
  - **REQUIRED**: Azure OpenAI API key and endpoint (for gpt-image-1 model)
  - **OPTIONAL**: Google AI API key (for additional image generation capabilities)

### Installation

1. Clone and navigate to the project:

```bash
git clone <repository>
cd image.serv
```

1. Install dependencies:

```bash
uv sync
```

1. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your actual values
```

Or set them directly:

```bash
# REQUIRED: Azure OpenAI API Configuration
export OPENAI_API_KEY="your-azure-openai-api-key" # pragma: allowlist secret
export OPENAI_BASE_URL="https://your-resource-name.openai.azure.com"

# OPTIONAL: Google AI Configuration
export GOOGLE_API_KEY="your-google-api-key" # pragma: allowlist secret

# OPTIONAL: Backend server URL for image download URLs
export BACKEND_SERVER="http://localhost:8000"

# OPTIONAL: Temporary image storage directory
export TMP_PATH="./images"

# OPTIONAL: Default response format (image|markdown|adaptive_card)
export DEFAULT_RESPONSE_FORMAT="markdown"

# OPTIONAL: Logging level (DEBUG|INFO|WARNING|ERROR|CRITICAL)
export LOG_LEVEL="INFO"

# OPTIONAL: Server port
export PORT="8000"
```

## Usage

### Running the Server

Start the server for integration with Claude Desktop or other MCP clients:

```bash
uv run python -m server.server
```

The server will be available at `http://localhost:8000` with endpoints:

- `POST /api/v1/generate_image` - Generate images
- `POST /api/v1/edit_image` - Edit existing images
- `/api/docs` - OpenAPI Documenation

### MCP Configuration

```json
{
    "servers": {
        "image-generation": {
            "type": "http",
            "url": "http://localhost:8000/mcp/v1",
            "gallery": true
        }
    }
}
```

## Tools & API

### generate_image

Create images from text descriptions.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `prompt` | string | required | Image description (max 32,000 chars) |
| `size` | string | `auto` | Dimensions: `1024x1024`, `1536x1024`, `1024x1536`, or `auto` |
| `output_format` | string | `jpeg` | Output format: `png`, `jpeg`, or `webp` |
| `seed` | integer | `0` | Random seed for reproducibility (0 = random) |
| `enhance_prompt` | boolean | `true` | Auto-enhance prompt via LLM |
| `response_format` | string | `image` | Response type: `image`, `markdown`, or `adaptive_card` |
| `background` | string | `auto` | Background: `transparent`, `opaque`, or `auto` |

**Example:**

```python
generate_image(
    prompt="A serene mountain landscape at sunset with golden light reflecting off a lake",
    size="1536x1024",
    output_format="png",
    enhance_prompt=True,
    response_format="markdown"
)
```

### edit_image

Edit existing images with text prompts and optional masks for inpainting.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `prompt` | string | required | Description of desired edits (max 32,000 chars) |
| `image_paths` | array | required | Image URLs, file paths, or base64 data URLs (max 16) |
| `mask_path` | string | optional | PNG mask for inpainting (transparent = edit zones) |
| `size` | string | `auto` | Output dimensions |
| `output_format` | string | `jpeg` | Output format: `png`, `jpeg`, or `webp` |
| `background` | string | `auto` | Background setting |
| `response_format` | string | `image` | Response type: `image`, `markdown`, or `adaptive_card` |

**Example:**

```python
edit_image(
    prompt="Add a vibrant rainbow across the sky",
    image_paths=["https://example.com/landscape.jpg"],
    mask_path="https://example.com/sky_mask.png",
    output_format="png",
    response_format="markdown"
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

## Architecture

The server follows a clean, layered architecture:

```
MCP Client / REST Client
    ↓
FastMCP Server / FastAPI Routes
    ↓
Image Service Layer
    ↓
Image Generators (OpenAI, Google)
    ├── Prompt Enhancer
    ├── Image Processor
    └── Image Loader
```

### Key Components

- **mcp_server.py** - FastMCP tool definitions and server setup
- **server.py** - Unified MCP + REST API server
- **api/routes.py** - FastAPI REST endpoints
- **backend/image_service.py** - Core business logic
- **backend/generators/** - AI provider implementations
  - `openai.py` - OpenAI gpt-image-1 integration

## Development

### Running Tests

```bash
make test
```

Run with coverage:

```bash
make test-coverage
```

### Code Quality

Format and lint code:

```bash
make format
make check
```

### Available Commands

```bash
make help
```

## Response Formats

All endpoints support three response formats via the `response_format` parameter:

### Image Format

Returns raw image data suitable for display or processing.

### Markdown Format

Returns formatted markdown with embedded base64 images:

```markdown
# Generated Image

![Generated Image](http://localhost:8000/_uploads/...)
```

### Adaptive Card Format

Returns Microsoft Adaptive Card JSON for Teams or other platforms:

```json
{
  "type": "AdaptiveCard",
  "version": "1.4",
  "body": [
    {
      "type": "Image",
      "url": "http://localhost:8000/_uploads/..."
    }
  ]
}
```

## Error Handling

The API returns standard HTTP status codes:

- `200 OK` - Successful generation/editing
- `400 Bad Request` - Invalid parameters
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - API failure

Error responses include detailed messages:

```json
{
  "status": "error",
  "error": "Description of what went wrong",
  "metadata": {
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | - | Azure OpenAI key for gpt-image-1 |
| `OPENAI_BASE_URL` | Yes | - | Azure OpenAI endpoint URL (e.g., `https://your-resource-name.openai.azure.com`) |
| `GOOGLE_API_KEY` | No | - | Google AI key for image generation |
| `BACKEND_SERVER` | No | `http://localhost:8000` | Backend server URL for image download URLs (use `http://host.docker.internal:8000` in Docker) |
| `TMP_PATH` | No | `./images` | Directory for storing generated images (use `/app/images` in Docker) |
| `DEFAULT_RESPONSE_FORMAT` | No | `markdown` | Default response format: `image`, `markdown`, or `adaptive_card` |
| `LOG_LEVEL` | No | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` |
| `PORT` | No | `8000` | Server port |

## License

This project is licensed under the MIT License - see [LICENSE.md](LICENSE.md) for details.
