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
- **ASGI Middleware** - `ForceHTTPSMiddleware` (scheme from `X-Forwarded-Proto`) and `SecurityHeadersMiddleware` (nosniff, referrer policy, frame-ancestors, HSTS on https)
- **Service Registry** - Dependency injection container for managing application services
- **Secret Management** - `secret:` values from env, Azure Key Vault, AWS SSM, the macOS Keychain or the Windows Credential Manager, plus the `appkit-secrets` CLI for the local stores

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

| Extra | Adds |
| --- | --- |
| `azure` | Azure Key Vault provider (`azure-identity`, `azure-keyvault-secrets`) |
| `aws` | AWS SSM Parameter Store provider (`boto3[crt]`) |
| `windows` | Windows Credential Manager provider (`pywin32`, Windows only) |
| `cli` | The `appkit-secrets` command (`typer`) |

```bash
uv add "appkit-commons[azure,cli]"
```

The macOS Keychain provider needs no extra; it uses the built-in `security` tool.

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
    password="secret:db_password",
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

### Secret Providers

`secret:<name>` values are resolved by the provider in `SECRET_PROVIDER`. A `.env` file only needs the provider settings; the cloud providers use your existing `az login` or `aws login` session.

| `SECRET_PROVIDER` | Store | Lookup name with `SECRET_NAMESPACE=myapp` | Without namespace |
| --- | --- | --- | --- |
| `local` (default) | Environment / `.env` | `name`, `NAME`, `NA_ME` variants | same |
| `macos` | macOS Keychain | account `myapp`, service `name` | account `appkit` |
| `windows` | Windows Credential Manager | target `myapp:name` | `appkit:name` |
| `azure` | Azure Key Vault | `myapp-name` (lowercased) | `name` |
| `aws_ssm` | AWS SSM Parameter Store | `/myapp/name` | `name` |

Uncomment one block in `.env`:

```bash
# --- macos / windows
SECRET_PROVIDER=macos
SECRET_NAMESPACE=myapp

# --- azure, authenticate with `az login`
#SECRET_PROVIDER=azure
#SECRET_NAMESPACE=myapp
#AZURE_KEY_VAULT_URL=https://<your-vault>.vault.azure.net/

# --- aws_ssm, authenticate with `aws login --profile myapp-dev`
#SECRET_PROVIDER=aws_ssm
#SECRET_NAMESPACE=myapp/dev
#AWS_PROFILE=myapp-dev
#AWS_REGION=eu-central-1   # only needed if the profile sets no region
```

An unknown `SECRET_PROVIDER` value raises a `ValueError`.

> [!NOTE]
> `appkit_commons` loads `.env` with `override=True`, so values in `.env` win over the shell. Set `PYTHON_DOTENV_DISABLED=1` to use shell variables only.

### `appkit-secrets` CLI

Manages secrets in the macOS Keychain or the Windows Credential Manager (install the `cli` extra). The provider defaults to `SECRET_PROVIDER` when it is `macos`/`windows`, otherwise to the current platform; the namespace comes from `--namespace` or `SECRET_NAMESPACE`.

```bash
appkit-secrets add mn-db-password            # prompts twice, hidden
printf '%s' "$VALUE" | appkit-secrets update mn-db-password --stdin
appkit-secrets list                          # names only
appkit-secrets delete mn-db-password --yes
eval "$(appkit-secrets env)"                 # export all as MN_DB_PASSWORD=... for SECRET_PROVIDER=local
PROFILES=local appkit-secrets check          # every secret: in configuration/ present? exit 1 if not
appkit-secrets check --all-profiles          # config.yaml and every config.*.yaml
```

Values are never passed on the command line and never printed, except by `env`.

Shell completion covers commands, `--provider`, `--profiles`, the stored names for `update`/`delete`/`env`, and for `add` the names your configuration needs that are not stored yet. Initialize it in your shell start-up file:

```bash
eval "$(appkit-secrets completion zsh)"      # ~/.zshrc, after compinit
eval "$(appkit-secrets completion bash)"     # ~/.bashrc
appkit-secrets completion fish | source      # ~/.config/fish/config.fish
appkit-secrets completion powershell | Out-String | Invoke-Expression   # $PROFILE
```

Without a shell argument the shell is taken from `$SHELL`. `appkit-secrets --install-completion` also works where the shell can be auto-detected.

### Logging Configuration

Customize logging output:

```python
from appkit_commons.configuration import setup_logging

setup_logging(
    level="INFO",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    file="app.log",
    max_file_size="10 MB",
    backup_count=5,
)
```

---

## 📋 API Reference

### Configuration

- `BaseConfig` - Base class for all configuration objects
- `load_configuration()` - Load configuration from YAML and environment
- `setup_logging()` - Initialize logging system
- `get_secret()` - Resolve a secret through the configured `SECRET_PROVIDER`
- `SecretProvider` - Enum of provider names (`local`, `azure`, `aws_ssm`, `macos`, `windows`)

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
- Azure Key Vault and AWS SSM for production, macOS Keychain and Windows Credential Manager for local development
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
