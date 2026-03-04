"""LLM-powered BPMN process JSON generator.

The LLM produces a simple JSON process description using OpenAI
structured outputs (Pydantic ``response_format``).  Downstream
modules (``bpmn_xml_builder`` and ``bpmn_layouter``) convert that
JSON into valid BPMN 2.0 XML with layout coordinates.
"""

import logging
import re
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import ValidationError

from appkit_mcp_bpmn.models import BpmnProcessJson

logger = logging.getLogger(__name__)

_SKILL_PATH = Path(__file__).resolve().parent.parent / "resources" / "SKILL.md"

_FALLBACK_SYSTEM_PROMPT = """\
You are a BPMN process designer.  Describe workflows as JSON.
Output ONLY the raw JSON — no markdown fences, no comments, no explanation.

Return a JSON object with a single "process" key containing an ordered \
array of BPMN elements.  Each element has "type", "id", and an optional \
"label".  Gateways may include "branches" (array of {condition, path}) \
and "has_join" (boolean).

Supported types: startEvent, endEvent, task, userTask, serviceTask, \
scriptTask, manualTask, sendTask, receiveTask, businessRuleTask, \
callActivity, subProcess, exclusiveGateway, parallelGateway, \
inclusiveGateway, eventBasedGateway, intermediateCatchEvent, \
intermediateThrowEvent.

Do NOT include sequence flows — they are generated automatically.

Example:
{"process": [
  {"type": "startEvent", "id": "Event_Start", "label": "Start"},
  {"type": "userTask", "id": "Activity_Review", "label": "Review"},
  {"type": "endEvent", "id": "Event_End", "label": "Done"}
]}
"""


def _load_system_prompt() -> str:
    """Load the BPMN generation system prompt from SKILL.md.

    Falls back to a built-in prompt if the file is not found.
    """
    if _SKILL_PATH.is_file():
        content = _SKILL_PATH.read_text(encoding="utf-8")
        match = re.search(
            r"## LLM System Prompt\s*\n"
            r"(.*?)"
            r"(?=\n## (?:Best Practices|Common Pitfalls)|\Z)",
            content,
            re.DOTALL,
        )
        if match:
            logger.info("Loaded BPMN system prompt from SKILL.md")
            return match.group(1).strip()

    logger.info("Using fallback BPMN system prompt")
    return _FALLBACK_SYSTEM_PROMPT


class BPMNGenerator:
    """Generate BPMN process JSON from natural language via LLM."""

    def __init__(self) -> None:
        self._system_prompt = _load_system_prompt()

    async def generate(
        self,
        description: str,
        diagram_type: str = "process",
        model: str = "gpt-4o",
        *,
        client: AsyncOpenAI | None = None,
    ) -> BpmnProcessJson:
        """Generate a BPMN process JSON from a description.

        Uses OpenAI structured outputs to guarantee the response
        matches the ``BpmnProcessJson`` schema exactly.

        Args:
            description: Human-readable workflow description.
            diagram_type: ``process``, ``collaboration``,
                or ``choreography``.
            model: LLM model name.
            client: Pre-configured ``AsyncOpenAI`` client.

        Returns:
            Parsed ``BpmnProcessJson`` model instance.

        Raises:
            RuntimeError: If LLM generation fails or response is refused.
        """
        if not client:
            raise RuntimeError(
                "OpenAI client not provided. "
                "Ensure the OpenAIClientService is registered."
            )

        user_prompt = (
            f"Describe the following {diagram_type} workflow "
            f"as BPMN process JSON:\n\n{description}"
        )

        try:
            logger.info(
                "Sending request to LLM (model=%s, structured_output=True)...",
                model,
            )
            response = await client.responses.parse(
                model=model,
                input=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                text_format=BpmnProcessJson,
            )

            logger.info("LLM request finished")

        except ValidationError as exc:
            # Pydantic schema/validator failed (most common in structured output setups)
            logger.exception(
                "LLM returned invalid BPMN JSON (schema validation failed)"
            )
            raise RuntimeError(
                "LLM returned invalid BPMN JSON (schema validation failed)"
            ) from exc

        except Exception as exc:
            logger.exception("LLM generation failed")
            raise RuntimeError("Failed to generate BPMN diagram via LLM") from exc

        # ---- Extract parsed result ----
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise RuntimeError("LLM returned empty structured response")

        return parsed
