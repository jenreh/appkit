# appkit-user

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Enterprise user management and authentication for Reflex applications.**

appkit-user provides comprehensive user authentication, authorization, and management capabilities for Reflex applications. It includes OAuth2 integration with GitHub and Azure, role-based access control (RBAC), multi-tenant user profiles, and secure session management.

---

## ✨ Features

- **OAuth2 Authentication** - GitHub and Azure OAuth2 providers with PKCE support
- **Role-Based Access Control** - Flexible RBAC with custom roles and permissions
- **Multi-Tenant Support** - User profiles organized by tenants and projects
- **Session Management** - Secure session handling with automatic cleanup
- **User Management UI** - Complete admin interface for user CRUD operations
- **Authentication Decorators** - Easy-to-use decorators for protecting routes and components
- **Profile Management** - User profile editing with role assignment
- **Security Features** - CSRF protection, secure redirects, and session validation

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
pip install appkit-user
```

Or with uv:

```bash
uv add appkit-user
```

### Dependencies

- `greenlet>=3.2.4` (async utilities)
- `appkit-commons` (shared utilities)
- `appkit-ui` (UI components)
- `requests_oauthlib>=2.0.0` (OAuth2 client)

---

## 🏁 Quick Start

### Basic OAuth Configuration

Configure OAuth providers in your application:

```python
from appkit_user.configuration import GithubOAuthConfig, AzureOAuthConfig

# GitHub OAuth
github_config = GithubOAuthConfig(
    client_id="your-github-client-id",
    client_secret="secret:github-client-secret",
    redirect_url="http://localhost:3000/auth/github/callback"
)

# Azure OAuth
azure_config = AzureOAuthConfig(
    client_id="your-azure-client-id",
    client_secret="secret:azure-client-secret",
    tenant_id="your-tenant-id",
    redirect_url="http://localhost:3000/auth/azure/callback"
)
```

### Protecting Routes

Use authentication decorators to protect your pages:

```python
import reflex as rx
from appkit_user.authentication.components import requires_authenticated, requires_role

# Require authentication
@requires_authenticated
def protected_page():
    return rx.text("This page requires login")

# Require specific role
@requires_role("admin")
def admin_page():
    return rx.text("Admin only content")

# Require admin privileges
@requires_admin
def super_admin_page():
    return rx.text("Super admin content")
```

### Login Integration

Add login functionality to your app:

```python
from appkit_user.authentication.components import login_form

def login_page():
    return login_form(
        header="My App",
        logo="/img/logo.svg",
        logo_dark="/img/logo_dark.svg"
    )
```

---

## 📖 Usage

### OAuth Configuration

#### GitHub OAuth

Configure GitHub OAuth application:

```python
from appkit_user.configuration import GithubOAuthConfig

config = GithubOAuthConfig(
    client_id="gh_oauth_client_id",
    client_secret="secret:github_oauth_secret",
    redirect_url="https://myapp.com/auth/github/callback",
    scopes=["user", "user:email", "read:org"]  # Optional custom scopes
)
```

#### Azure OAuth

Configure Azure AD application:

```python
from appkit_user.configuration import AzureOAuthConfig

config = AzureOAuthConfig(
    client_id="azure_client_id",
    client_secret="secret:azure_client_secret",
    tenant_id="tenant-id",  # or "common" for multi-tenant
    redirect_url="https://myapp.com/auth/azure/callback",
    is_public_client=False,  # Set to True for PKCE-only apps
    scopes=["openid", "profile", "email", "User.Read"]
)
```

### Authentication Decorators

#### Basic Authentication

```python
from appkit_user.authentication.components import requires_authenticated

@requires_authenticated
def dashboard():
    return rx.text("Welcome to your dashboard!")
```

#### Role-Based Access

```python
from appkit_user.authentication.components import requires_role

@requires_role("editor")
def content_editor():
    return rx.text("Content editor interface")

@requires_role("viewer", fallback=rx.text("Access denied"))
def reports():
    return rx.text("Reports dashboard")
```

#### Admin Access

```python
from appkit_user.authentication.components import requires_admin

@requires_admin
def admin_panel():
    return rx.text("Admin control panel")
```

### User Management

#### User Table

Display and manage users:

```python
from appkit_user.user_management.components import users_table

def user_management_page():
    return rx.vstack(
        rx.heading("User Management"),
        users_table(),
        spacing="4"
    )
```

#### User Profile

Manage user profiles and roles:

```python
from appkit_user.user_management.components import profile_roles, profile_state

def user_profile_page():
    return rx.vstack(
        rx.heading("User Profile"),
        profile_roles(),
        spacing="4"
    )
```

### Session Management

Access current user session:

```python
from appkit_user.authentication.states import UserSession

def current_user_info():
    return rx.vstack(
        rx.text(f"User: {UserSession.user.email}"),
        rx.text(f"Roles: {UserSession.user.roles}"),
        rx.text(f"Tenant: {UserSession.user.tenant_id}"),
        rx.text(f"Authenticated: {UserSession.is_authenticated}")
    )
```

---

## 🔧 Configuration

### OAuth Redirect URLs

Configure OAuth callback URLs in your Reflex app:

```python
# In rxconfig.py or main app file
app.add_page(
    oauth_login_splash,
    route="/auth/github/callback",
    title="GitHub Login"
)

app.add_page(
    oauth_login_splash,
    route="/auth/azure/callback",
    title="Azure Login"
)
```

### Custom OAuth Providers

Extend OAuth support for custom providers:

```python
from appkit_user.configuration import OAuthConfig, OAuthProvider

class CustomOAuthConfig(OAuthConfig):
    provider: OAuthProvider = "custom"
    auth_url: str = "https://custom.provider.com/oauth/authorize"
    token_url: str = "https://custom.provider.com/oauth/token"
    user_url: str = "https://custom.provider.com/api/user"
    scopes: list[str] = ["read", "write"]
```

### Multi-Tenant Setup

Configure tenant-based user isolation:

```python
# Users are automatically scoped by tenant_id
# Access current tenant
current_tenant = UserSession.user.tenant_id

# Filter data by tenant
tenant_users = get_users_by_tenant(current_tenant)
```

---

## 📋 API Reference

### Authentication Components

- `requires_authenticated()` - Decorator for authentication-required content
- `requires_role()` - Decorator for role-based access control
- `requires_admin()` - Decorator for admin-only content
- `login_form()` - Login form with OAuth providers
- `oauth_login_splash()` - OAuth callback splash screen
- `default_fallback()` - Default unauthorized access message

### User Management Components

- `users_table()` - User management table with CRUD operations
- `add_user_button()` - Button to add new users
- `update_user_button()` - Button to edit existing users
- `delete_user_button()` - Button to remove users
- `user_form_fields()` - Form fields for user creation/editing
- `profile_roles()` - User profile role management
- `profile_state()` - User profile state management

### Configuration Classes

- `OAuthConfig` - Base OAuth configuration
- `GithubOAuthConfig` - GitHub OAuth settings
- `AzureOAuthConfig` - Azure AD OAuth settings
- `OAuthProvider` - Enum of supported OAuth providers

### State Management

- `UserSession` - Current user session state
- `LoginState` - Login form state management

---

## 🔒 Security

> [!IMPORTANT]
> Always configure HTTPS in production and use secure secrets management. OAuth client secrets should never be hardcoded.

- **OAuth2 PKCE Support** - Proof Key for Code Exchange for enhanced security
- **Secure Redirects** - Configurable redirect URLs prevent open redirect attacks
- **Session Security** - Automatic session cleanup and validation
- **CSRF Protection** - Built-in CSRF tokens for forms
- **Role Validation** - Server-side role checking in addition to client-side decorators
- **Tenant Isolation** - Multi-tenant data isolation prevents cross-tenant access

---

## 🤝 Integration Examples

### Complete Authentication Flow

Set up a full authentication system:

```python
import reflex as rx
from appkit_user.authentication.components import (
    login_form,
    requires_authenticated,
    oauth_login_splash
)
from appkit_user.configuration import GithubOAuthConfig

# Configure OAuth
oauth_config = GithubOAuthConfig(
    client_id="your-client-id",
    client_secret="secret:your-client-secret"
)

# Public login page
def login():
    return login_form(
        header="My App",
        logo="/img/logo.svg",
        logo_dark="/img/logo_dark.svg"
    )

# Protected dashboard
@requires_authenticated
def dashboard():
    return rx.text(f"Welcome {UserSession.user.email}!")

# OAuth callback
def github_callback():
    return oauth_login_splash(
        provider="github",
        message="Signing in with GitHub..."
    )

# Add to app
app = rx.App()
app.add_page(login, route="/login")
app.add_page(dashboard, route="/dashboard")
app.add_page(github_callback, route="/auth/github/callback")
```

### User Management System

Create an admin user management interface:

```python
from appkit_user.user_management.components import users_table
from appkit_user.authentication.components import requires_admin

@requires_admin
def admin_users():
    return rx.vstack(
        rx.heading("User Management", size="5"),
        rx.flex(
            users_table(),
            direction="column",
            gap="4",
            width="100%"
        ),
        padding="6",
        spacing="4"
    )
```

### Role-Based Navigation

Dynamic navigation based on user roles:

```python
def navigation():
    return rx.hstack(
        rx.link("Home", href="/"),
        rx.cond(
            UserSession.is_authenticated,
            rx.hstack(
                rx.link("Dashboard", href="/dashboard"),
                rx.cond(
                    UserSession.user.roles.contains("admin"),
                    rx.link("Admin", href="/admin"),
                    rx.text("")  # Empty for non-admins
                ),
                rx.button("Logout", on_click=UserSession.logout)
            ),
            rx.link("Login", href="/login")
        )
    )
```

---

## 📚 Related Components

- **[appkit-commons](./../appkit-commons)** - Shared utilities and configuration
- **[appkit-ui](./../appkit-ui)** - UI components used in user management
- **[appkit-assistant](./../appkit-assistant)** - AI assistant with user authentication
- **[appkit-mantine](./../appkit-mantine)** - Form components for user management
