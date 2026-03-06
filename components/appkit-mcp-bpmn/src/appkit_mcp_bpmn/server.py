"""FastMCP server for BPMN 2.0 diagram generation and viewing.

Exposes MCP tools:
- generate_bpmn_diagram: Generate BPMN XML from natural language via LLM
- save_bpmn_diagram: Save pre-built BPMN XML and return viewer URLs

Exposes MCP prompts:
- bpmn_process_json: JSON format specification for BPMN process generation
"""

import json
import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP

from appkit_commons.ai.openai_client_service import (
    get_openai_client_service,
)
from appkit_mcp_bpmn.configuration import BPMNConfig
from appkit_mcp_bpmn.models import DiagramResult
from appkit_mcp_bpmn.resources.bpmn_viewer import BPMN_VIEWER_HTML, VIEW_URI
from appkit_mcp_bpmn.services.bpmn_generator import BPMNGenerator
from appkit_mcp_bpmn.services.bpmn_layouter import add_diagram_layout
from appkit_mcp_bpmn.services.bpmn_storage import load_diagram, save_diagram
from appkit_mcp_bpmn.services.bpmn_validator import validate_bpmn_xml
from appkit_mcp_bpmn.services.bpmn_xml_builder import build_bpmn_xml
from appkit_mcp_commons.exceptions import ValidationError

logger = logging.getLogger(__name__)


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
    cfg = config or BPMNConfig()
    generator = BPMNGenerator()
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
            raise ValueError(
                f"Invalid diagram_type '{diagram_type}'. "
                f"Must be one of: {', '.join(cfg.diagram_types)}"
            )

        logger.info(
            "generate_bpmn_diagram called: type=%s",
            diagram_type,
        )

        try:
            openai_client = _get_openai_client()
            process_json = await generator.generate(
                description,
                diagram_type,
                model=cfg.default_model,
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

        return _validate_and_save(laid_out_xml, cfg.storage_dir)

    @mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
    async def save_bpmn_diagram(xml: str) -> str:
        """Save an existing BPMN 2.0 XML diagram.

        Validates the XML, saves it to the filesystem, and returns
        viewer URLs.

        Args:
            xml: Complete BPMN 2.0 XML string.

        Returns:
            JSON string with ``{success, id, download_url, view_url,
            error}``.
        """
        if not xml or not xml.strip():
            raise ValueError("XML must not be empty")

        logger.info("save_bpmn_diagram called")
        return _validate_and_save(xml, cfg.storage_dir)

    @mcp.tool(
        app=AppConfig(
            resource_uri=VIEW_URI,
            visibility=["app"],
        )
    )
    async def get_bpmn_xml(diagram_id: str) -> str:
        """Retrieve the BPMN XML for a previously saved diagram.

        This tool is intended to be called from the BPMN viewer app
        to fetch diagram data without embedding XML in the tool result.

        Args:
            diagram_id: UUID of the diagram to retrieve.

        Returns:
            The raw BPMN 2.0 XML string, or a JSON error.
        """
        if not diagram_id or not diagram_id.strip():
            return _error_result("diagram_id must not be empty")

        xml = load_diagram(diagram_id, cfg.storage_dir)
        if xml is None:
            return _error_result(f"Diagram '{diagram_id}' not found")
        return xml

    @mcp.prompt()
    def bpmn_process_json(description: str) -> str:
        """Return instructions for generating BPMN process JSON.

        Use this prompt to tell an LLM how to describe a workflow
        as a BPMN process JSON object that the ``generate_bpmn_diagram``
        tool can consume.

        Args:
            description: The workflow to describe.
        """
        return (
            "Describe the following workflow as flat BPMN JSON.\n\n"
            f"Workflow: {description}\n\n"
            'Output a JSON object with "steps" (flat ordered array) '
            'and "lanes" (null or array of '
            '{"name": "...", "steps": ["id1", ...]}).\n\n'
            "Each step has:\n"
            '- "id": unique snake_case identifier\n'
            '- "type": one of startEvent, endEvent, task, userTask, '
            "serviceTask, scriptTask, manualTask, sendTask, "
            "receiveTask, businessRuleTask, callActivity, "
            "subProcess, exclusive, parallel, inclusive, "
            "eventBased, merge, intermediateCatchEvent, "
            "intermediateThrowEvent\n"
            '- "label": human-readable name\n'
            '- "branches": null, or array of '
            '{"condition": "...", "target": "step_id"} '
            "for gateways\n"
            '- "next": null (flow to next in list) or '
            "a step id (explicit jump)\n\n"
            "Use type 'merge' to synchronize parallel branches.\n"
            "Do NOT include sequence flows.\n"
            "Output ONLY the raw JSON — "
            "no markdown fences, no explanation."
        )

    return mcp


def _validate_and_save(xml: str, storage_dir: str) -> str:
    """Validate BPMN XML and persist to disk.

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


def _get_openai_client() -> Any:
    """Get the OpenAI client from the service registry.

    Returns:
        AsyncOpenAI client instance or None.
    """
    try:
        service = get_openai_client_service()
        return service.create_client()
    except Exception as e:
        logger.warning("Failed to get OpenAI client: %s", e)
        return None


def _error_result(message: str) -> str:
    """Return a JSON error response."""
    result = DiagramResult(success=False, error=message)
    return json.dumps(result.model_dump(), default=str)
