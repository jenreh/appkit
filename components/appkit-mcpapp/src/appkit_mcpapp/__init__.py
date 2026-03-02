"""appkit-mcpapp - FastMCP 3.0-based MCP server component for appkit.

Provides a FastMCP server with user analytics tools:
- query_users_table: Dynamic SQL generation and execution
- generate_barchart: Interactive chart generation
"""

__version__ = "1.6.3"
__author__ = "Jens Rehpöhler"
__license__ = "MIT"

from appkit_mcpapp.server import create_mcp_server

__all__ = ["create_mcp_server"]
