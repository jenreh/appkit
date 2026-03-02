class MCPError(Exception):
    """Base error for MCP operations."""


class AuthenticationError(MCPError):
    """Raised when authentication fails."""


class ValidationError(MCPError):
    """Raised when input validation fails."""


class ExecutionError(MCPError):
    """Raised when tool execution fails."""


class SecurityError(MCPError):
    """Raised when security checks fail."""
