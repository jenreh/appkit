"""FastMCP server for BPMN 2.0 diagram generation and viewing.

Exposes MCP tools:
- generate_bpmn_diagram: Generate BPMN XML from natural language via LLM
- save_bpmn_diagram: Save pre-built BPMN XML and return viewer URLs

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
from appkit_mcp_bpmn.services.bpmn_layouter import add_diagram_layout
from appkit_mcp_bpmn.services.bpmn_validator import validate_bpmn_xml
from appkit_mcp_bpmn.services.bpmn_xml_builder import build_bpmn_xml
from appkit_mcp_commons.context import extract_user_id
from appkit_mcp_commons.exceptions import ValidationError
from appkit_mcp_commons.utils import get_openai_client

logger = logging.getLogger(__name__)

BPMN_PROCESS_JSON_PROMPT = """
Describe the following workflow as flat BPMN JSON.

Workflow: {description}

Output a JSON object with "steps" (flat ordered array) and "lanes" \\
(null or array of {{"name": "...", "steps": ["id1", ...]}}).

Each step has:
- "id": unique snake_case identifier
- "type": one of startEvent, endEvent, task, userTask, serviceTask, scriptTask, \\
manualTask, sendTask, receiveTask, businessRuleTask, callActivity, subProcess, \\
exclusive, parallel, inclusive, eventBased, merge, intermediateCatchEvent, \\
intermediateThrowEvent
- "label": human-readable name
- "branches": null, or array of {{"condition": "...", "target": "step_id"}} \\
for gateways
- "next": null (flow to next in list) or a step id (explicit jump)

Use type 'merge' to synchronize parallel branches.
Do NOT include sequence flows.
Output ONLY the raw JSON \u2014 no markdown fences, no explanation."""


def _get_user_id() -> int:
    """Return the current request's user ID, or -1 if no HTTP context exists."""
    try:
        request = get_http_request()
        return extract_user_id(request)
    except RuntimeError:
        return -1


def _create_result_msg(
    success: bool,
    error: str | None = None,
    diagram_id: str | None = None,
    download_url: str | None = None,
    view_url: str | None = None,
) -> str:
    """Create a JSON-serialized DiagramResult."""
    result = DiagramResult(
        success=success,
        error=error,
        id=diagram_id,
        download_url=download_url,
        view_url=view_url,
    )
    return json.dumps(result.model_dump(), default=str)


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
    if config is not None:
        cfg = config
    else:
        try:
            cfg = service_registry().get(BPMNConfig)
        except Exception:  # noqa: BLE001
            logger.warning("BPMNConfig not found in registry; using defaults")
            cfg = BPMNConfig()

    logger.info("Creating BPMN MCP server with storage mode: %s", cfg.storage_mode)
    generator = BPMNGenerator()
    storage = create_storage_backend(cfg.storage_mode, cfg.storage_dir)
    mcp = FastMCP(name)

    @mcp.resource(
        VIEW_URI,
        app=AppConfig(
            csp=ResourceCSP(resource_domains=["https://unpkg.com"]),
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
    async def generate_bpmn_diagram(
        description: str,
        diagram_type: str = "process",
    ) -> str:
        """Generate a BPMN 2.0 diagram from a natural language description.

        Uses an LLM to convert the description into valid BPMN 2.0 XML,
        validates the result, saves it to disk, and returns viewer URLs.

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

        if diagram_type not in cfg.diagram_types:
            valid_types = ", ".join(cfg.diagram_types)
            raise ValueError(
                f"Invalid diagram_type '{diagram_type}'. Must be one of: {valid_types}"
            )

        logger.info("generate_bpmn_diagram called: type=%s", diagram_type)

        try:
            openai_client = get_openai_client()
            process_json = await generator.generate(
                description,
                diagram_type,
                model=cfg.default_model,
                client=openai_client,
            )
            process_xml = build_bpmn_xml(process_json)
            laid_out_xml = add_diagram_layout(process_xml)
        except (RuntimeError, ValidationError) as exc:
            raise ValueError(f"Generation failed: {exc}") from exc

        return await _persist_and_respond(
            laid_out_xml,
            description,
            _get_user_id(),
            str(uuid.uuid4()),
            diagram_type,
            storage,
        )

    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
    async def save_bpmn_diagram(xml: str, prompt: str = "") -> str:
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
        return await _persist_and_respond(
            xml,
            prompt,
            _get_user_id(),
            str(uuid.uuid4()),
            "process",
            storage,
        )

    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
    async def get_bpmn_xml(diagram_id: str) -> str:
        """Retrieve the BPMN XML for a previously saved diagram.

        This tool is intended to be called from the BPMN viewer app
        to fetch diagram data without embedding XML in the tool result.

        Args:
            diagram_id: UUID of the diagram.

        Returns:
            The raw BPMN 2.0 XML string, or a JSON error.
        """
        if not diagram_id or not diagram_id.strip():
            return _create_result_msg(
                success=False, error="diagram_id must not be empty"
            )

        xml = await storage.load(diagram_id, _get_user_id())
        if xml is None:
            return _create_result_msg(
                success=False, error=f"Diagram '{diagram_id}' not found"
            )
        return xml

    @mcp.prompt()
    def bpmn_process_json(description: str) -> str:
        """Return instructions for generating BPMN process JSON."""
        return BPMN_PROCESS_JSON_PROMPT.format(description=description)

    return mcp


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
        info: DiagramInfo = await storage.save(
            normalised, prompt, user_id, diagram_id, diagram_type
        )
        return _create_result_msg(
            success=True,
            diagram_id=info.id,
            download_url=info.download_url,
            view_url=info.view_url,
        )
    except ValidationError as exc:
        raise ValueError(f"Validation failed: {exc}") from exc
    except (OSError, Exception) as exc:
        logger.exception("Failed to save diagram: %s", type(exc).__name__)
        raise ValueError(f"Storage error: {exc}") from exc


def _error_result(message: str) -> str:
    """Return a JSON error response."""
    return _create_result_msg(success=False, error=message)
