"""FastMCP server for BPMN 2.0 diagram generation and viewing.

Exposes MCP tools:
- generate_bpmn_diagram: Generate BPMN XML from natural language via LLM
- save_bpmn_diagram: Save pre-built BPMN XML and return viewer URLs
- update_bpmn_diagram: Modify an existing diagram via natural language prompt

Exposes MCP prompts:
- bpmn_process_json: JSON format specification for BPMN process generation
"""

import json
import logging
import uuid

from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP
from fastmcp.server.dependencies import get_http_request

from appkit_commons.registry import service_registry
from appkit_mcp_bpmn.backend.storage.base import DiagramInfo, StorageBackend
from appkit_mcp_bpmn.backend.storage.factory import create_storage_backend
from appkit_mcp_bpmn.configuration import BPMNConfig
from appkit_mcp_bpmn.models import DiagramResult
from appkit_mcp_bpmn.resources.bpmn_viewer import BPMN_VIEWER_HTML, VIEW_URI
from appkit_mcp_bpmn.services.bpmn_generator import BPMNGenerator
from appkit_mcp_bpmn.services.bpmn_json_extractor import extract_process_json
from appkit_mcp_bpmn.services.bpmn_layouter import add_diagram_layout
from appkit_mcp_bpmn.services.bpmn_storage import save_diagram  # noqa: PLC0415
from appkit_mcp_bpmn.services.bpmn_validator import validate_bpmn_xml
from appkit_mcp_bpmn.services.bpmn_xml_builder import build_bpmn_xml
from appkit_mcp_commons.context import extract_user_id
from appkit_mcp_commons.exceptions import ValidationError
from appkit_mcp_commons.utils import get_openai_client

logger = logging.getLogger(__name__)

_MAX_NAME_LENGTH = 128


def _get_user_id() -> int:
    """Return the current request's user ID, or -1 if no HTTP context exists."""
    try:
        request = get_http_request()
        return extract_user_id(request)
    except RuntimeError:
        return -1


def _resolve_config(config: BPMNConfig | None) -> BPMNConfig:
    """Return the given config or load from registry / use defaults."""
    if config is not None:
        return config
    try:
        return service_registry().get(BPMNConfig)
    except Exception:  # noqa: BLE001
        logger.warning("BPMNConfig not found in registry; using defaults")
        return BPMNConfig()


def create_bpmn_mcp_server(
    *,
    name: str = "appkit-bpmn",
    config: BPMNConfig | None = None,
) -> FastMCP:
    """Create and configure the FastMCP server for BPMN diagrams.

    Args:
        name: Server name for MCP registration.
        config: Optional BPMN configuration. Uses defaults if None.

    Returns:
        Configured FastMCP server instance.
    """
    config = _resolve_config(config)

    logger.warning("Creating BPMN MCP server with config: %s", config.storage_mode)
    generator = BPMNGenerator()
    storage = create_storage_backend(config.storage_mode, config.storage_dir)
    mcp = FastMCP(name)

    @mcp.resource(
        VIEW_URI,
        app=AppConfig(
            csp=ResourceCSP(
                resource_domains=[
                    "https://unpkg.com",
                ],
            ),
            prefers_border=False,
        ),
    )
    def bpmn_view() -> str:
        """BPMN diagram viewer using bpmn-js.

        Receives the tool result via ``ui/notifications/tool-result``
        and renders the BPMN XML inside the iframe.
        """
        return BPMN_VIEWER_HTML

    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
    async def new_bpmn_diagram(
        description: str,
        diagram_type: str = "process",
    ) -> str:
        """Create a brand-new BPMN 2.0 diagram from a natural language description.

        WARNING: This tool creates a NEW diagram from scratch and does
        NOT preserve any existing diagram.  If the user wants to rename,
        add, remove, or change steps in an existing diagram, use
        ``update_bpmn_diagram(diagram_id, update_prompt)`` instead.

        Args:
            description: Natural language workflow description
                (e.g. "Approve invoices over $5K, notify finance").
            diagram_type: Type of BPMN diagram — one of "process",
                "collaboration", or "choreography".

        Returns:
            JSON string with ``{success, id, download_url, view_url,
            error}``.
        """
        if not description or not description.strip():
            raise ValueError("Description must not be empty")

        if diagram_type not in config.diagram_types:
            raise ValueError(
                f"Invalid diagram_type '{diagram_type}'. "
                f"Must be one of: {', '.join(config.diagram_types)}"
            )

        logger.info(
            "new_bpmn_diagram called: type=%s",
            diagram_type,
        )

        try:
            openai_client = get_openai_client()
            process_json = await generator.generate(
                description,
                diagram_type,
                model=config.default_model,
                client=openai_client,
            )
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc

        # JSON → process-only XML → add BPMNDiagram layout → validate
        try:
            process_xml = build_bpmn_xml(process_json)
            laid_out_xml = add_diagram_layout(process_xml)
        except ValidationError as exc:
            raise ValueError(f"Build failed: {exc}") from exc

        user_id = _get_user_id()
        diagram_id = str(uuid.uuid4())
        return await _persist_and_respond(
            laid_out_xml, description, user_id, diagram_id, diagram_type, storage
        )

    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
    async def update_bpmn_diagram(
        diagram_id: str,
        update_prompt: str,
    ) -> str:
        """Modify an existing BPMN diagram using a natural language prompt.

        PREFERRED tool when the user wants to change, rename, add, or
        remove elements in a diagram that already exists.  The tool
        loads the stored XML internally — do NOT pass XML content.

        Args:
            diagram_id: UUID of the diagram to modify (from a previous
                ``new_bpmn_diagram`` or ``update_bpmn_diagram`` result).
            update_prompt: Natural language description of the changes
                to apply.  Do NOT pass XML here — describe changes in
                plain language (e.g. "Rename 'Review' to 'Final Review'
                and add a notification step after approval").

        Returns:
            JSON string with ``{success, id, name, download_url,
            view_url, error}``.
        """
        if not diagram_id or not diagram_id.strip():
            raise ValueError("diagram_id must not be empty")
        if not update_prompt or not update_prompt.strip():
            raise ValueError("update_prompt must not be empty")

        user_id = _get_user_id()
        return await _load_modify_and_save(
            diagram_id, update_prompt, user_id, generator, config, storage
        )

    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
    async def save_bpmn_diagram(
        xml: str,
        prompt: str = "",
    ) -> str:
        """Save an existing BPMN 2.0 XML diagram.

        Validates the XML, saves it to the configured storage backend, and
        returns viewer URLs.

        Args:
            xml: Complete BPMN 2.0 XML string.
            prompt: Optional natural language description for the diagram.

        Returns:
            JSON string with ``{success, id, download_url, view_url,
            error}``.
        """
        if not xml or not xml.strip():
            raise ValueError("XML must not be empty")

        logger.info("save_bpmn_diagram called")
        user_id = _get_user_id()
        diagram_id = str(uuid.uuid4())
        return await _persist_and_respond(
            xml, prompt, user_id, diagram_id, "process", storage
        )

    @mcp.tool(
        app=AppConfig(
            resource_uri=VIEW_URI,
            visibility=["app"],
        )
    )
    async def get_bpmn_xml(
        diagram_id: str,
    ) -> str:
        """Retrieve the BPMN XML for a previously saved diagram.

        This tool is intended to be called from the BPMN viewer app
        to fetch diagram data without embedding XML in the tool result.

        Args:
            diagram_id: UUID of the diagram to retrieve.

        Returns:
            The raw BPMN 2.0 XML string, or a JSON error.
        """
        return await _load_xml(diagram_id, _get_user_id(), storage)

    @mcp.tool(
        app=AppConfig(
            resource_uri=VIEW_URI,
            visibility=["app"],
        )
    )
    async def save_or_update(diagram_id: str, xml: str) -> str:
        """Save updated BPMN XML for an existing diagram (in-place).

        Validates the XML and overwrites the stored diagram.
        Called from the viewer when the user edits the diagram.

        Args:
            diagram_id: UUID of the diagram to update.
            xml: Complete BPMN 2.0 XML string to store.

        Returns:
            JSON string with ``{success, id, name, error}``.
        """
        return await _validate_and_update(diagram_id, xml, _get_user_id(), storage)

    @mcp.tool(
        app=AppConfig(
            resource_uri=VIEW_URI,
            visibility=["app"],
        )
    )
    async def rename_bpmn_diagram(
        diagram_id: str,
        name: str,
    ) -> str:
        """Rename a previously saved BPMN diagram.

        Validates the new name (1-128 characters, trimmed) and persists
        the update.  Intended to be called from the BPMN viewer when the
        user edits the diagram name inline.

        Args:
            diagram_id: UUID of the diagram to rename.
            name: New diagram name (1-128 characters).

        Returns:
            JSON string with ``{success, id, name, error}``.
        """
        user_id = _get_user_id()
        return await _validate_and_rename(diagram_id, name, user_id, storage)

    return mcp


async def _load_xml(
    diagram_id: str,
    user_id: int,
    storage: StorageBackend,
) -> str:
    """Load BPMN XML for a diagram by ID, returning an error JSON on failure."""
    if not diagram_id or not diagram_id.strip():
        return _error_result("diagram_id must not be empty")
    xml = await storage.load(diagram_id, user_id)
    if xml is None:
        return _error_result(f"Diagram '{diagram_id}' not found")
    return xml


async def _persist_and_respond(
    xml: str,
    prompt: str,
    user_id: int,
    diagram_id: str,
    diagram_type: str,
    storage: StorageBackend,
) -> str:
    """Validate BPMN XML, persist via *storage*, and return a JSON response.

    Args:
        xml: Raw BPMN XML string.
        prompt: Original natural language description (may be empty).
        user_id: Authenticated user identifier.
        diagram_id: Pre-generated UUID for the diagram.
        diagram_type: BPMN diagram type label.
        storage: Configured :class:`StorageBackend` instance.

    Returns:
        JSON-serialised :class:`DiagramResult`.
    """
    try:
        normalised = validate_bpmn_xml(xml)
    except ValidationError as exc:
        raise ValueError(f"Validation failed: {exc}") from exc

    # Derive diagram name from prompt (fallback to diagram ID prefix)
    name = (
        prompt.strip()[:128]
        if prompt and prompt.strip()
        else f"Diagram {diagram_id[:8]}"
    )

    try:
        info: DiagramInfo = await storage.save(
            normalised, prompt, user_id, diagram_id, diagram_type
        )
    except (OSError, Exception) as exc:
        logger.exception("Failed to save diagram: %s", type(exc).__name__)
        raise ValueError(f"Storage error: {exc}") from exc

    result = DiagramResult(
        success=True,
        id=info.id,
        name=name,
        download_url=info.download_url,
        view_url=info.view_url,
    )
    return json.dumps(result.model_dump(), default=str)


async def _load_modify_and_save(
    diagram_id: str,
    update_prompt: str,
    user_id: int,
    generator: BPMNGenerator,
    config: BPMNConfig,
    storage: StorageBackend,
) -> str:
    """Load a diagram, modify via LLM, and save as a new version.

    Args:
        diagram_id: UUID of the source diagram.
        update_prompt: Natural language modification description.
        user_id: Authenticated user identifier.
        generator: :class:`BPMNGenerator` instance for LLM calls.
        config: BPMN configuration (model name, etc.).
        storage: Configured :class:`StorageBackend` instance.

    Returns:
        JSON-serialised :class:`DiagramResult` for the new version.
    """
    logger.info("update_bpmn_diagram: id=%s user=%s", diagram_id, user_id)

    # 1. Load existing diagram XML
    xml = await storage.load(diagram_id, user_id)
    if xml is None:
        raise ValueError(f"Diagram '{diagram_id}' not found")

    # 2. Extract process JSON from XML
    try:
        process_json = extract_process_json(xml)
    except ValidationError as exc:
        raise ValueError(f"Failed to extract process JSON: {exc}") from exc

    # 3. Call LLM with existing JSON as context + update prompt
    current_json = json.dumps(process_json, indent=2)
    logger.debug("Update prompt with current JSON:\n%s", current_json)

    prompt = (
        "You are MODIFYING an existing BPMN diagram — NOT creating a "
        "new one.  You MUST start from the current JSON below and apply "
        "ONLY the requested changes.\n\n"
        f"CURRENT DIAGRAM JSON:\n```json\n{current_json}\n```\n\n"
        "STRICT RULES FOR MODIFICATION:\n"
        "1. Copy every step from the current JSON into your output "
        "unchanged, unless the user explicitly asks to modify it.\n"
        "2. Keep each step's id, type, label, branches, and next "
        "exactly as-is unless a change is requested.\n"
        "3. Branch conditions (the 'condition' field) are edge labels "
        "on the diagram.  Preserve them unless the user asks to "
        "rename or remove them.\n"
        "4. Preserve loopback edges (branches whose target points to "
        "an earlier step).  Never drop them.\n"
        "5. When adding new steps, insert them at the correct position "
        "in the steps array and update next/branches references.\n"
        "6. Return the COMPLETE JSON with ALL steps — both unchanged "
        "and modified.\n"
        f"\nREQUESTED CHANGES:\n{update_prompt}"
    )

    try:
        openai_client = get_openai_client()
        updated_process = await generator.generate(
            prompt,
            "process",
            model=config.default_model,
            client=openai_client,
            raw_prompt=True,
        )
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc

    # 4. JSON → XML → layout → validate
    try:
        process_xml = build_bpmn_xml(updated_process)
        laid_out_xml = add_diagram_layout(process_xml)
    except ValidationError as exc:
        raise ValueError(f"Build failed: {exc}") from exc

    # 5. Save as new version
    new_diagram_id = str(uuid.uuid4())
    return await _persist_and_respond(
        laid_out_xml, update_prompt, user_id, new_diagram_id, "process", storage
    )


async def _validate_and_update(
    diagram_id: str,
    xml: str,
    user_id: int,
    storage: StorageBackend,
) -> str:
    """Validate BPMN XML and update an existing diagram in storage.

    Args:
        diagram_id: UUID of the diagram to update.
        xml: Raw BPMN XML string.
        user_id: Authenticated user identifier.
        storage: Configured :class:`StorageBackend` instance.

    Returns:
        JSON-serialised :class:`DiagramResult`.
    """
    if not diagram_id or not diagram_id.strip():
        return _error_result("diagram_id must not be empty")
    if not xml or not xml.strip():
        return _error_result("XML must not be empty")

    try:
        normalised = validate_bpmn_xml(xml)
    except ValidationError as exc:
        return _error_result(f"Validation failed: {exc}")

    logger.info("save_or_update: id=%s user=%s", diagram_id, user_id)

    updated = await storage.update(diagram_id, user_id, normalised)
    if not updated:
        return _error_result(f"Diagram '{diagram_id}' not found")

    result = DiagramResult(success=True, id=diagram_id)
    return json.dumps(result.model_dump(), default=str)


async def _validate_and_rename(
    diagram_id: str,
    name: str,
    user_id: int,
    storage: StorageBackend,
) -> str:
    """Validate a new diagram name and persist through *storage*.

    Args:
        diagram_id: UUID of the diagram to rename.
        name: Raw name string (will be stripped).
        user_id: Authenticated user identifier.
        storage: Configured :class:`StorageBackend` instance.

    Returns:
        JSON-serialised :class:`DiagramResult`.
    """
    if not diagram_id or not diagram_id.strip():
        return _error_result("diagram_id must not be empty")

    trimmed = name.strip() if name else ""
    if not trimmed:
        return _error_result("Name must not be empty")
    if len(trimmed) > _MAX_NAME_LENGTH:
        return _error_result("Name must not exceed 128 characters")

    logger.info(
        "rename_bpmn_diagram: id=%s user=%s name=%s", diagram_id, user_id, trimmed
    )

    renamed = await storage.rename(diagram_id, user_id, trimmed)
    if not renamed:
        return _error_result(f"Diagram '{diagram_id}' not found")

    result = DiagramResult(success=True, id=diagram_id, name=trimmed)
    return json.dumps(result.model_dump(), default=str)


def _validate_and_save(xml: str, storage_dir: str) -> str:
    """Validate BPMN XML and persist to disk (synchronous, filesystem only).

    Kept for backwards compatibility with tests and external callers.
    New code should use :func:`_persist_and_respond` instead.

    Args:
        xml: Raw BPMN XML string.
        storage_dir: Target directory for file storage.

    Returns:
        JSON-serialised ``DiagramResult``.
    """

    try:
        normalised = validate_bpmn_xml(xml)
    except ValidationError as exc:
        raise ValueError(f"Validation failed: {exc}") from exc

    try:
        info = save_diagram(normalised, storage_dir)
    except OSError as exc:
        logger.exception("Failed to save diagram")
        raise ValueError(f"Storage error: {exc}") from exc

    result = DiagramResult(
        success=True,
        id=info["id"],
        download_url=info["download_url"],
        view_url=info["view_url"],
    )
    return json.dumps(result.model_dump(), default=str)


def _error_result(message: str) -> str:
    """Return a JSON error response."""
    result = DiagramResult(success=False, error=message)
    return json.dumps(result.model_dump(), default=str)
