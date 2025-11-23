# appkit-commons

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Shared utilities and infrastructure for AppKit components.**

appkit-commons provides the foundational infrastructure used across all AppKit packages, including configuration management, database integration, logging, security utilities, and dependency injection. It serves as the common base layer that enables consistent behavior and shared functionality across the AppKit ecosystem.

---

## ✨ Features

- **Configuration Management** - YAML-based configuration with environment variable overrides and secret handling
- **Database Integration** - SQLAlchemy-based ORM with PostgreSQL support, connection pooling, and encryption
- **Logging Infrastructure** - Structured logging with color output and configurable levels
- **Security Utilities** - Password hashing with PBKDF2 and scrypt, secure random generation
- **Service Registry** - Dependency injection container for managing application services
- **Secret Management** - Support for local secrets and Azure Key Vault integration

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
pip install appkit-commons
```

Or with uv:

```bash
uv add appkit-commons
```

### Optional Dependencies

For Azure Key Vault support:

```bash
pip install appkit-commons[azure]
# or
uv add appkit-commons[azure]
```

### Dependencies

- `colorlog>=6.9.0` (colored logging)
- `cryptography>=46.0.2` (encryption utilities)
- `pydantic-settings>=2.10.1` (configuration management)
- `pyyaml==6.0.2` (YAML configuration)
- `sqlalchemy-utils==0.42.0` (database utilities)
- `sqlalchemy==2.0.41` (ORM)

---

## 🏁 Quick Start

### Basic Configuration

Create a configuration class extending `BaseConfig`:

```python
from appkit_commons.configuration import BaseConfig

class MyConfig(BaseConfig):
    app_name: str = "MyApp"
    debug: bool = False
    api_key: str = "secret:api_key"  # Will be resolved from secrets
```

Load configuration from YAML and environment:

```python
from appkit_commons.configuration import load_configuration

config = load_configuration(MyConfig, "config.yaml")
print(f"App: {config.app_name}, Debug: {config.debug}")
```

### Database Setup

Configure database connection:

```python
from appkit_commons.database import DatabaseConfig, create_session_manager

db_config = DatabaseConfig(
    type="postgresql",
    host="localhost",
    port=5432,
    name="myapp",
    username="user",
    password="secret:db_password"
)

session_manager = create_session_manager(db_config)

# Use in your code
with session_manager.session() as session:
    # Your database operations
    pass
```

### Logging Setup

Initialize logging with configuration:

```python
from appkit_commons.configuration import setup_logging

# Setup with default configuration
setup_logging()

# Or with custom config
setup_logging(log_level="DEBUG", log_file="app.log")
```

---

## 📖 Usage

### Configuration System

#### BaseConfig

All configuration classes should inherit from `BaseConfig`:

```python
from appkit_commons.configuration import BaseConfig

class AppConfig(BaseConfig):
    model_config = {"env_prefix": "MYAPP_"}

    database_url: str = "postgresql://localhost/mydb"
    api_timeout: int = 30
    features: dict[str, bool] = {"new_ui": True}
```

#### Secret Resolution

Use `secret:` prefix for sensitive values:

```python
class SecureConfig(BaseConfig):
    api_key: str = "secret:openai_api_key"  # Resolved from env or Key Vault
    db_password: str = "secret:database_password"
```

#### YAML Configuration

Configuration files support nested structures:

```yaml
# config.yaml
app:
  name: "MyApp"
  database:
    host: "localhost"
    port: 5432
  features:
    - "authentication"
    - "file_upload"
```

### Database Integration

#### Session Management

Use the session manager for database operations:

```python
from appkit_commons.database import create_session_manager

manager = create_session_manager(db_config)

# Get a session
with manager.session() as session:
    # Perform operations
    result = session.execute(text("SELECT 1"))
    print(result.scalar())
```

#### Entity Base Classes

Extend from `BaseEntity` for common database fields:

```python
from appkit_commons.database import BaseEntity
from sqlalchemy import Column, String

class User(BaseEntity):
    __tablename__ = "users"

    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
```

### Security Utilities

#### Password Hashing

```python
from appkit_commons.security import hash_password, verify_password

# Hash a password
hashed = hash_password("mypassword")

# Verify a password
is_valid = verify_password("mypassword", hashed)
```

#### Secure Random Generation

```python
from appkit_commons.security import generate_token

token = generate_token(length=32)
```

### Service Registry

#### Dependency Injection

Register and retrieve services:

```python
from appkit_commons.registry import service_registry

# Register a service
service_registry.register(MyService())

# Retrieve a service
service = service_registry.get(MyService)
```

---

## 🔧 Configuration

### Environment Variables

Configuration supports nested environment variables:

```bash
export MYAPP_APP__NAME="ProductionApp"
export MYAPP_DATABASE__HOST="prod-db.example.com"
export MYAPP_API__TIMEOUT="60"
```

### Azure Key Vault

For production secrets, configure Azure Key Vault:

```python
from appkit_commons.configuration import configure_azure_key_vault

configure_azure_key_vault(
    vault_url="https://myvault.vault.azure.net/",
    credential=None  # Uses DefaultAzureCredential
)
```

### Logging Configuration

Customize logging output:

```python
from appkit_commons.configuration import setup_logging

setup_logging(
    level="INFO",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    file="app.log",
    max_file_size="10 MB",
    backup_count=5
)
```

---

## 📋 API Reference

### Configuration

- `BaseConfig` - Base class for all configuration objects
- `load_configuration()` - Load configuration from YAML and environment
- `setup_logging()` - Initialize logging system
- `configure_azure_key_vault()` - Setup Azure Key Vault integration

### Database

- `DatabaseConfig` - Database connection configuration
- `create_session_manager()` - Create database session manager
- `BaseEntity` - Base class for database entities

### Security

- `hash_password()` - Hash passwords with PBKDF2 or scrypt
- `verify_password()` - Verify password against hash
- `generate_token()` - Generate secure random tokens

### Registry

- `service_registry` - Global service registry instance
- `ServiceRegistry` - Dependency injection container

---

## 🔒 Security

> [!IMPORTANT]
> Always use `SecretStr` for sensitive configuration values and the `secret:` prefix for automatic resolution from secure sources.

- Passwords are hashed using industry-standard algorithms (PBKDF2/scrypt)
- Database credentials support encryption at rest
- Azure Key Vault integration for production secret management
- Secure random generation for tokens and salts

---

## 🤝 Integration Examples

### With AppKit Components

appkit-commons is automatically integrated into other AppKit packages:

```python
# Configuration is inherited by appkit-user, appkit-assistant, etc.
from appkit_user.configuration import UserConfig

user_config = UserConfig()  # Extends BaseConfig automatically
```

### Custom Application Setup

Complete application bootstrap:

```python
from appkit_commons.configuration import load_configuration, setup_logging
from appkit_commons.database import create_session_manager
from appkit_commons.registry import service_registry

# Load config
config = load_configuration(MyAppConfig, "config.yaml")

# Setup logging
setup_logging(level=config.log_level)

# Setup database
db_manager = create_session_manager(config.database)
service_registry.register(db_manager)

# Your app logic here
```

---

## 📚 Related Components

- **[appkit-user](./../appkit-user)** - User authentication and authorization
- **[appkit-assistant](./../appkit-assistant)** - AI assistant functionality
- **[appkit-mantine](./../appkit-mantine)** - UI components
- **[appkit-imagecreator](./../appkit-imagecreator)** - Image generation workflows
