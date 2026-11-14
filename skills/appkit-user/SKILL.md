---
name: appkit-user
description: >
  appkit-user usage patterns: wiring the session guard (install_session_filter,
  add_session_guard, require_session), AuthenticationConfiguration (OAuth providers,
  public_routes, session cookie), the authenticated_page decorator, login and
  password-reset page factories, auth decorators and role gates, and shared-origin
  path prefix handling (session cookie name, app_storage_key for browser storage,
  OAuth redirect URLs). Apply automatically when adding login, OAuth providers,
  protected pages or REST routes, rx.LocalStorage fields, or serving an app below a
  frontend_path.
metadata:
  author: jens-rehpoehler
  version: "1.2"
  license: MIT
---

# appkit-user Best Practices

Authentication, sessions and user management for appkit apps. For the general
path prefix helpers (`public_path`, `public_url`, `strip_public_prefix`) see the
**appkit-commons** skill.

---

## 1. Wiring

One import wires the whole guard: HTTP page loads and REST routes via the ASGI
middleware, WebSocket events via the Reflex middleware.

```python
from appkit_user.authentication import add_session_guard, install_session_filter
from appkit_user.authentication.pages import (  # noqa: F401  registers routes
    azure_oauth_callback_page,
    github_oauth_callback_page,
)
from appkit_user.user_management.pages import (
    create_login_page,
    create_password_reset_confirm_page,
    create_password_reset_request_page,
)

from app.components.templates import default_layout  # layouts live in the app

create_login_page(default_layout)  # logo paths are app relative; prefixed internally
create_password_reset_request_page(default_layout)
create_password_reset_confirm_page(default_layout)

app = rx.App(api_transformer=[api_app, add_session_guard, add_https_middleware])
install_session_filter(app)
```

REST routes on the FastAPI app take the user from the session cookie:

```python
from appkit_user.authentication import RequiredSession  # Depends(require_session)


@router.get("/api/things")
async def list_things(user: RequiredSession) -> list[Thing]: ...
```

---

## 2. Configuration

```yaml
app:
  authentication:
    server_url: http://localhost
    server_port: 8080            # 0 or the scheme default is dropped
    session_timeout: 25          # minutes
    session_cookie_secure: true  # false only for non-TLS hosts other than localhost
    # session_cookie_name: ""    # "" = derived from frontend_path (see §5)
    # storage_key_prefix: ""     # "" = derived from frontend_path (see §5)
    public_routes:               # fnmatch globs, app relative; all else default-deny
      - /login
      - /password-reset
      - /password-reset/confirm
      - /oauth/*/callback
    oauth_providers:
      - provider: github
        client_id: secret:my-github-client-id
        client_secret: secret:my-github-client-secret
        # redirect_url: leave unset (see §6)
    password_reset:
      token_expiry_minutes: 10
      max_requests_per_hour: 3
    login_rate_limit:            # failed password logins, stored in auth_login_throttle
      enabled: true
      max_attempts: 5            # per normalized email within window_minutes
      max_attempts_per_client: 20  # per client IP (offices share one address)
      window_minutes: 15
      lockout_minutes: 15
```

`public_routes` are matched against the route **without** the path prefix.
Never write `/knai/login` there.

Behind a reverse proxy, Reflex (>= 0.10.1) ignores `X-Forwarded-For` unless
`trusted_proxy_hops` is set in the Reflex config, so `router.session.client_ip`
is the proxy address by default. Set it to the number of trusted proxies before
using the client IP for logging or rate limits. `router.headers.cookie` keeps
every repeated cookie header; parse it with `unquote` like the session cookie.

### Login throttle and forced reset

`LoginState.process_login` consults `get_login_throttle()`
(`appkit_user.authentication.login_throttle`) before checking the password.
A locked email or client is refused with a toast and no password check runs.
Only `invalid_credentials` counts as a failure; success clears the email's
counter. Counters are rows in `auth_login_throttle` (SHA-256 keys, fixed window;
the consuming app needs the Alembic migration that creates the table), so
workers and restarts share them. The client key uses `router.session.client_ip`,
so set `reflex.trusted_proxy_hops` behind a proxy or all users share the
proxy's bucket. `SessionCleanupService` prunes stale rows.

If the password is correct but `needs_password_reset` is set, no session is
created. The login issues an `ADMIN_FORCED` reset token
(`password_reset_token_repo.create_token`) and redirects to
`/password-reset/confirm?token=...`.

---

## 3. Pages

`authenticated_page` is the page decorator of appkit-user. It wraps the page in
`mn.theme_wrapper`, adds the session monitor (timeout detection) and the
`admin_only` gate, and appends `LoadingState` reset to `on_load`
(`mn.with_loading_reset`). The layout comes from the app as a `template` callable;
without one the page renders in a bare `mn.app_shell`.

```python
import appkit_mantine as mn
from appkit_user.authentication.templates import authenticated_page


def my_template(content: rx.Component) -> rx.Component:
    return mn.app_shell(
        mn.app_shell.navbar(app_navbar()),
        mn.app_shell.main(content),
        navbar={"width": 250, "breakpoint": "sm"},
    )


@authenticated_page(
    route="/settings",
    title="Settings",
    template=my_template,
    admin_only=True,
    on_load=SettingsState.on_load,
)
def settings_page() -> rx.Component:
    return mn.stack(...)
```

- `SessionFilter` gates the route before any `on_load` handler runs; an
  unauthenticated visitor never reaches the page handlers.
- `admin_only` only switches the rendered content to `default_fallback()`. Guard
  admin events with `@requires_admin` (see §4).
- Layouts such as a splash page or a page with a navbar live in the app
  (`app/components/templates.py`). They reuse `default_meta`
  (`appkit_user.authentication.templates`), `session_monitor()` and
  `default_fallback()` (`appkit_user.authentication.components`).
- `create_login_page`, `create_password_reset_request_page` and
  `create_password_reset_confirm_page` take the app's page decorator factory as
  their first argument. It is called as `layout(route=..., title=..., on_load=...)`
  and returns a page decorator (`PageLayout` protocol in
  `appkit_user.user_management.pages`).

---

## 4. Protecting UI and handlers

```python
from appkit_user.authentication.components.components import (
    requires_admin,
    requires_authenticated,
    requires_role,
)
from appkit_user.authentication import decorators as auth

requires_admin(admin_menu(), fallback=rx.fragment())  # UI gate only
requires_role(editor_panel(), role="editor")


class MyState(rx.State):
    @rx.event
    @auth.is_authenticated  # server-side check; redirects to login
    async def save(self) -> AsyncGenerator: ...

    @rx.event
    @auth.requires_admin  # same name as the UI gate; import the module
    async def purge(self) -> AsyncGenerator: ...
```

UI gates hide markup; they are not authorization. Every state handler or REST
route that reads or writes protected data checks on the server
(`@is_authenticated`, `@requires_admin`, `RequiredSession`).

---

## 5. Path prefix: cookie and browser storage

With `reflex.frontend_path: /knai`, several apps share one origin and therefore
one cookie jar and one `localStorage`. appkit-user derives distinct names:

| Item | Site root | Below `/knai` | Override |
| --- | --- | --- | --- |
| Session cookie | `reflex_session` | `knai_session` | `session_cookie_name` |
| Storage prefix | `""` | `knai_` | `storage_key_prefix` (`[A-Za-z0-9_]*`) |
| Auth token key | `_auth_token` | `knai__auth_token` | via prefix |
| OAuth state key | `_oauth_state` | `knai__oauth_state` | via prefix |
| Post-login redirect key | `login_redirect_to` | `knai_login_redirect_to` | via prefix |

**Every browser storage key in any app or package uses `app_storage_key()`:**

```python
from appkit_user.authentication.states import app_storage_key

# Define once, import in writer and reader
MY_RESULT_STORAGE_KEY = app_storage_key("my-result")


class MyState(rx.State):
    result: str = rx.LocalStorage(name=MY_RESULT_STORAGE_KEY, sync=True)


# JS writer (e.g. an OAuth popup) uses the same constant
rx.call_script(f"localStorage.setItem({json.dumps(MY_RESULT_STORAGE_KEY)}, data)")

mn.scroll_area.stateful(..., persist_key=app_storage_key("navbar_scroll_area"))
```

Rules:

- Never a literal `rx.LocalStorage(name="...")`, `rx.SessionStorage(name="...")`,
  `rx.Cookie(name="...")` or `localStorage.setItem("...")`.
- Names are resolved at import time and baked into the frontend export. Re-export
  after changing `frontend_path` or the prefix settings. Leftover unprefixed keys
  in the browser come from older builds or other apps and are harmless.
- Test import-time names in a fresh interpreter (`subprocess` that registers
  `AuthenticationConfiguration(..., storage_key_prefix="knai_")` before importing
  the state), not in-process. See `tests/test_auth_configuration.py`.
- Reflex-owned keys cannot be prefixed: sessionStorage `token`, localStorage
  `theme` / `last_compiled_theme`, `react-router-scroll-positions`.

---

## 6. Path prefix: routes, redirects, OAuth

- `self.router.url.path` carries the prefix and is client controlled. Compare
  routes via `strip_public_prefix(path)`; never authorize on it.
- `rx.redirect("/login")` and `rx.link(href="/login")` stay app relative; React
  Router adds the prefix. HTTP redirects in ASGI middleware use
  `public_path(LOGIN_ROUTE)`.
- `AuthenticationConfiguration.public_base_url` = `public_origin` + prefix
  (`https://x/knai`); not doubled when `server_url` already ends with it.
- OAuth `redirect_url` defaults to `<public_base_url>/oauth/<provider>/callback`.
  **Leave it unset.** An explicit value is used verbatim and skips the prefix;
  the callback then lands outside the app ("The server is configured with a
  public base URL of /knai/ ...").
- Register the prefixed callback at the provider. GitHub accepts any subpath of
  the registered URL, so registering the origin root covers all prefixes.
- MCP OAuth (appkit-assistant) uses its own callback `/assistant/mcp/callback`
  and handoff key `app_storage_key("mcp-oauth-result")`.

In-process tests switch the prefix with
`appkit_commons.testing.set_public_path_prefix(monkeypatch, "/knai")`.

---

## 7. Anti-Patterns

| Anti-pattern | Correct approach |
| --- | --- |
| `rx.LocalStorage(name="my-key")` | `rx.LocalStorage(name=app_storage_key("my-key"))` |
| Key string duplicated in JS and state | One module constant imported by both |
| `redirect_url: http://host/oauth/github/callback` in YAML | Leave unset; derived with prefix |
| `/knai/login` in `public_routes` | `/login` (matched app relative) |
| `router.url.path == "/login"` | `strip_public_prefix(router.url.path) == "/login"` |
| `rx.redirect(public_path("/login"))` | `rx.redirect("/login")` |
| UI gate (`requires_admin`) as the only check | Server-side `@requires_admin` / `RequiredSession` |
| Session cookie name hardcoded | `session_validation.session_cookie_name()` |
| Counting login failures in your own state or DB table | `get_login_throttle()` / `login_rate_limit` config |
| Trusting `X-Forwarded-For` / `client_ip` behind a proxy without config | Set `trusted_proxy_hops` to the trusted proxy count |
| `admin_only=True` as the only admin check on a page | Also `@requires_admin` on every admin event handler |
| Layout code (navbar, header) inside a reusable package | `template=` callable or a `PageLayout` passed in by the app |
