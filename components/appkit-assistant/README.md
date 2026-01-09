# appkit-assistant

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**AI assistant component for Reflex applications with MCP server integration.**

appkit-assistant provides a complete conversational AI interface built on Reflex, featuring OpenAI and Perplexity integrations, Model Context Protocol (MCP) server management, and secure credential handling. It includes both backend processing services and ready-to-use UI components for building AI-powered applications.

![Assistant](https://raw.githubusercontent.com/jenreh/appkit/refs/heads/main/components/appkit-assistant/docs/assistant.png)

---

## ✨ Features

- **Multi-Model Support** - OpenAI Chat Completions, OpenAI Responses API, Perplexity, and fallback Lorem Ipsum processor
- **MCP Server Integration** - Manage and connect to Model Context Protocol servers as tools
- **System Prompt Management** - Versioned system prompts with admin editor interface
- **Secure Credential Management** - Encrypted storage and handling of API keys and server credentials
- **Reflex UI Components** - Pre-built assistant interface with composer, thread management, and message display
- **Streaming Responses** - Real-time streaming of AI responses with chunked content
- **Thread Management** - Persistent conversation threads with state management

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
pip install appkit-assistant
```

Or with uv:

```bash
uv add appkit-assistant
```

### Dependencies

- `appkit-commons` (shared utilities)
- `openai>=2.3.0` (OpenAI API client)

---

## 🏁 Quick Start

### Basic Setup

1. Configure your API keys in your application's configuration:

```python
from appkit_assistant.configuration import AssistantConfig

# In your app configuration
assistant_config = AssistantConfig(
    openai_api_key="your-openai-key",
    perplexity_api_key="your-perplexity-key",
    # Optional: custom OpenAI base URL
    openai_base_url="https://api.openai.com/v1"
)
```

2. Register processors with the ModelManager:

```python
from appkit_assistant.backend.model_manager import ModelManager
from appkit_assistant.backend.processors.openai_chat_completion_processor import OpenAIChatCompletionProcessor
from appkit_assistant.backend.processors.perplexity_processor import PerplexityProcessor

manager = ModelManager()
manager.register_processor("openai", OpenAIChatCompletionProcessor(assistant_config))
manager.register_processor("perplexity", PerplexityProcessor(assistant_config))
```

3. Use the assistant component in your Reflex app:

```python
import reflex as rx
from appkit_assistant.components import Assistant

def assistant_page():
    return rx.container(
        Assistant(),
        height="100vh"
    )
```

---

## 📖 Usage

### Model Management

The `ModelManager` singleton handles all AI processors and models:

```python
from appkit_assistant.backend.model_manager import ModelManager

manager = ModelManager()

# Get all available models
models = manager.get_all_models()

# Get a specific model
model = manager.get_model("gpt-4")

# Set default model
manager.set_default_model("gpt-4")
```

### Processing Messages

Process conversations using the registered processors:

```python
from appkit_assistant.backend.models import Message, MessageType

messages = [
    Message(role="user", content="Hello, how are you?", type=MessageType.TEXT)
]

async for chunk in manager.get_processor_for_model("gpt-4").process(messages, "gpt-4"):
    print(f"Received: {chunk.content}")
```

### MCP Server Management

Manage MCP servers for tool integration:

```python
from appkit_assistant.backend.models import MCPServer

mcp_server = MCPServer(
    name="my-server",
    command="python",
    args=["-m", "my_mcp_server"],
    headers={"Authorization": "Bearer token"}
)

# Use in processing
async for chunk in processor.process(messages, "gpt-4", mcp_servers=[mcp_server]):
    # Handle response with MCP tools
    pass
```

### UI Components

#### Assistant Interface

The main `Assistant` component provides a complete chat interface:

```python
from appkit_assistant.components import Assistant

def chat_page():
    return Assistant()
```

#### Individual Components

Use individual components for custom layouts:

```python
import reflex as rx
from appkit_assistant.components import ThreadList, composer

def custom_assistant():
    return rx.vstack(
        ThreadList(),
        composer(),
        spacing="4"
    )
```

#### MCP Server Management UI

Display and manage MCP servers:

```python
from appkit_assistant.components import mcp_servers_table

def servers_page():
    return mcp_servers_table()
```

#### System Prompt Editor

Admin interface for managing versioned system prompts:

```python
from appkit_assistant.components.system_prompt_editor import system_prompt_editor

def prompt_editor_page():
    return system_prompt_editor()
```

---

## 🔧 Configuration

### AssistantConfig

Configure API keys and settings:

```python
from appkit_assistant.configuration import AssistantConfig

config = AssistantConfig(
    openai_api_key="sk-...",
    openai_base_url="https://custom.openai.endpoint/v1",
    perplexity_api_key="pplx-...",
    google_api_key="AIza..."  # For future Google integrations
)
```

### Processor Registration

Register processors based on available credentials:

```python
from appkit_assistant.backend.processors import (
    OpenAIChatCompletionProcessor,
    PerplexityProcessor,
    LoremIpsumProcessor
)

manager = ModelManager()

if config.openai_api_key:
    manager.register_processor("openai", OpenAIChatCompletionProcessor(config))

if config.perplexity_api_key:
    manager.register_processor("perplexity", PerplexityProcessor(config))

# Always available fallback
manager.register_processor("lorem", LoremIpsumProcessor())
```

---

## 📋 API Reference

### Core Classes

- `ModelManager` - Singleton model and processor registry
- `Processor` - Abstract base for AI processors
- `AIModel` - Model metadata and configuration
- `Message` - Conversation message structure
- `MCPServer` - MCP server configuration

### Component API

- `Assistant` - Complete assistant interface
- `composer` - Message input component
- `ThreadList` - Conversation thread list
- `MessageComponent` - Individual message display
- `mcp_servers_table` - MCP server management table
- `system_prompt_editor` - Admin interface for system prompts


### State Management

- `ThreadState` - Individual thread state
- `ThreadListState` - Thread list management

---

## 🔒 Security

> [!IMPORTANT]
> API keys and MCP server credentials are handled securely using the appkit-commons configuration system. Never hardcode secrets in your code.

- Use `SecretStr` for sensitive configuration values
- Credentials are encrypted at rest when stored in the database
- MCP server headers support encrypted storage

---

## 🤝 Integration Examples

### With AppKit User Management

Combine with appkit-user for authenticated assistants:

```python
from appkit_user import authenticated, requires_role

@authenticated()
@requires_role("assistant_user")
def protected_assistant_page():
    return assistant.Assistant()
```

### Custom Processor Implementation

Implement your own AI processor:

```python
from appkit_assistant.backend.processor import Processor
from appkit_assistant.backend.models import AIModel, Chunk, Message

class CustomProcessor(Processor):
    def get_supported_models(self):
        return {
            "custom-model": AIModel(
                id="custom-model",
                text="Custom AI Model",
                icon="🤖"
            )
        }

    async def process(self, messages, model_id, files=None, mcp_servers=None):
        # Your AI processing logic here
        yield Chunk(content="Response from custom model", type="text")
```

---

## 📚 Related Components

- **[appkit-mantine](./../appkit-mantine)** - UI components used in the assistant interface
- **[appkit-user](./../appkit-user)** - User authentication and authorization
- **[appkit-commons](./../appkit-commons)** - Shared utilities and configuration
