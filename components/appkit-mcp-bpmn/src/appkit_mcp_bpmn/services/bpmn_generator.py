"""LLM-powered BPMN process JSON generator.

The LLM produces a simple JSON process description using OpenAI
structured outputs (Pydantic ``response_format``).  Downstream
modules (``bpmn_xml_builder`` and ``bpmn_layouter``) convert that
JSON into valid BPMN 2.0 XML with layout coordinates.
"""

import json
import logging
import re
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import ValidationError

from appkit_mcp_bpmn.models import BpmnProcessJson
from appkit_mcp_bpmn.services.repair_bpmn_json import repair_bpmn_json

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

        raw_text: str | None = None
        response = None

        try:
            logger.info("Sending structured parse request to LLM (model=%s)...", model)
            response = await client.responses.parse(
                model=model,
                instructions=self._system_prompt,
                input=user_prompt,
                text_format=BpmnProcessJson,
            )

            parsed = response.output_parsed
            if parsed is None:
                raw_text = getattr(response, "output_text", None)
                logger.warning(
                    "LLM returned no parsed output (refusal or empty). raw_text=%s",
                    raw_text[:200] if raw_text else None,
                )
                raise RuntimeError("LLM returned empty structured response")

            logger.debug("Structured parse succeeded")
            return parsed

        except ValidationError as val_err:
            # Structured parse validated the schema but Pydantic
            # model validators (process rules) rejected the result.
            if response is not None:
                raw_text = getattr(response, "output_text", None)
            logger.warning(
                "Structured output failed Pydantic validation: %s",
                val_err,
            )
            return await self._retry_with_error_context(
                client, model, user_prompt, raw_text, str(val_err)
            )

        except RuntimeError:
            # Re-raise our own RuntimeErrors (empty response) as-is
            raise

        except Exception as exc:
            logger.error(
                "BPMN generation failed (%s): %s",
                type(exc).__name__,
                exc,
            )
            raise RuntimeError("Failed to generate BPMN diagram via LLM") from exc

    async def _retry_with_error_context(
        self,
        client: AsyncOpenAI,
        model: str,
        user_prompt: str,
        raw_text: str | None,
        error_reason: str,
    ) -> BpmnProcessJson:
        """Retry LLM call with error feedback for self-correction.

        Uses ``responses.create`` with relaxed JSON schema so the
        deterministic ``repair_bpmn_json`` helper can fix minor issues
        before Pydantic validation.
        """
        error_parts = ["\n\nYour previous output was malformed."]
        error_parts.append(f"Validation error: {error_reason}")
        if raw_text:
            error_parts.append(f"\nYour output:\n{raw_text}")
        error_parts.append("Please fix the JSON and ensure it is valid.")
        error_context = "\n".join(error_parts)

        retry_message = (
            f"{error_context}\n\n"
            "Output ONLY valid JSON. Reminder: every gateway "
            "branch path must be non-empty. If a branch is "
            "pass-through, insert a NoOp task in path "
            "(type='task', label='Continue')."
        )

        try:
            logger.info("Retrying LLM request with error context...")
            raw_resp = await client.responses.create(
                model=model,
                instructions=self._system_prompt,
                input=[
                    {"role": "user", "content": user_prompt},
                    {"role": "user", "content": retry_message},
                ],
            )

            retry_text = raw_resp.output_text
            if not retry_text:
                raise RuntimeError("Retry returned empty response")

            logger.debug("Retry LLM raw output length: %d chars", len(retry_text))
            data = json.loads(retry_text)
            data = repair_bpmn_json(data)
            return BpmnProcessJson.model_validate(data)

        except Exception as fallback_exc:
            logger.error(
                "Retry also failed (%s): %s",
                type(fallback_exc).__name__,
                fallback_exc,
            )
            raise RuntimeError(
                "LLM returned invalid BPMN JSON and fallback repair failed"
            ) from fallback_exc
