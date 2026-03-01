"""Root conftest — delegates to appkit_commons.testing for shared fixtures.

All common test infrastructure (database, service registry, secrets, logging)
lives in ``appkit_commons.testing`` so every component package can reuse it.
"""

pytest_plugins = ["appkit_commons.testing"]
