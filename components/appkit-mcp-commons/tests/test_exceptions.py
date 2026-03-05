from appkit_mcp_commons.exceptions import (
    AuthenticationError,
    ExecutionError,
    MCPError,
    ValidationError,
)


def test_mcp_error_inheritance() -> None:
    """Test MCPError inheritance."""
    err = MCPError("base")
    assert isinstance(err, Exception)


def test_subclasses() -> None:
    """Test exception subclasses."""
    auth_err = AuthenticationError("auth")
    val_err = ValidationError("val")
    exec_err = ExecutionError("exec")

    assert isinstance(auth_err, MCPError)
    assert isinstance(val_err, MCPError)
    assert isinstance(exec_err, MCPError)
