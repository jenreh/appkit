"""LLM-powered BPMN process JSON generator.

The LLM produces a flat JSON process description using OpenAI
structured outputs (``BpmnProcess`` schema).  Downstream modules
(``bpmn_xml_builder`` and ``bpmn_layouter``) convert that JSON into
valid BPMN 2.0 XML with layout coordinates.
"""

import json
import logging
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import ValidationError

from appkit_mcp_bpmn.models import BpmnProcess
from appkit_mcp_bpmn.services.repair_bpmn_json import repair_bpmn_json

logger = logging.getLogger(__name__)


def _make_strict_schema(schema: dict) -> dict:
    """Make a JSON schema compatible with OpenAI strict structured output.

    Recursively ensures every object has all properties listed in
    ``required`` and removes ``default`` keys (not allowed in strict
    mode).
    """
    schema = dict(schema)

    # Process $defs first
    if "$defs" in schema:
        schema["$defs"] = {
            k: _make_strict_schema(v) for k, v in schema["$defs"].items()
        }

    if schema.get("type") == "object" and "properties" in schema:
        schema["required"] = list(schema["properties"].keys())
        schema["additionalProperties"] = False
        schema["properties"] = {
            k: _make_strict_schema(v) for k, v in schema["properties"].items()
        }

    # $ref must not have sibling keywords in strict mode
    if "$ref" in schema:
        return {"$ref": schema["$ref"]}

    # Recurse into anyOf / items
    if "anyOf" in schema:
        schema["anyOf"] = [_make_strict_schema(s) for s in schema["anyOf"]]
    if "items" in schema and isinstance(schema["items"], dict):
        schema["items"] = _make_strict_schema(schema["items"])

    schema.pop("default", None)
    schema.pop("title", None)

    return schema


_SKILL_PATH = Path(__file__).resolve().parent.parent / "resources" / "SKILL.md"

_FALLBACK_SYSTEM_PROMPT = """\
You are a BPMN process designer.  Describe workflows as JSON.
Output ONLY the raw JSON — no markdown fences, no comments, no explanation.

Return a JSON object with "steps" (flat ordered array) and "lanes" (null or array).
Each step has: "id", "type", "label", "branches" (null or array), "next" (null or id).

Supported types: startEvent, endEvent, task, userTask, serviceTask, \
scriptTask, manualTask, sendTask, receiveTask, businessRuleTask, \
callActivity, subProcess, exclusive, parallel, inclusive, eventBased, \
merge, intermediateCatchEvent, intermediateThrowEvent.

Gateway branches: [{"condition": "...", "target": "step_id"}].
Use "next" for explicit jumps; null means flow to next step in list.
Use "merge" type to synchronize parallel branches.

Example:
{"steps": [
  {"id": "start", "type": "startEvent", "label": "Start",
   "branches": null, "next": null},
  {"id": "task_1", "type": "task", "label": "Do work",
   "branches": null, "next": null},
  {"id": "end", "type": "endEvent", "label": "Done",
   "branches": null, "next": null}
], "lanes": null}
"""


def _load_system_prompt() -> str:
    """Load the BPMN generation system prompt from SKILL.md.

    Reads the entire file as the system prompt.  Falls back to a
    built-in prompt if the file is not found.
    """
    if _SKILL_PATH.is_file():
        content = _SKILL_PATH.read_text(encoding="utf-8").strip()
        if content:
            logger.info("Loaded BPMN system prompt from SKILL.md")
            return content

    logger.info("Using fallback BPMN system prompt")
    return _FALLBACK_SYSTEM_PROMPT


def _build_initial_thread(user_prompt: str) -> list[dict[str, str]]:
    """Build the initial message thread."""
    return [{"role": "user", "content": user_prompt}]


def _build_retry_user_message(errors: list[str]) -> dict[str, str]:
    """Build a validator-aware retry prompt containing accumulated errors."""
    error_history = "\n".join(
        f"  Attempt {i + 1}: {msg}" for i, msg in enumerate(errors)
    )
    error_context = (
        "Your previous output was invalid and failed Pydantic schema validation.\n\n"
        f"Error:\n{error_history}\n\n"
        "TASK: Return a corrected JSON by minimally editing the MOST RECENT "
        "OUTPUT above.\n"
        "Output ONLY valid JSON."
    )
    return {"role": "user", "content": error_context}


class BPMNGenerator:
    """Generate BPMN process JSON from natural language via LLM."""

    def __init__(self) -> None:
        self._system_prompt = _load_system_prompt()

    async def _attempt_parse(
        self,
        client: AsyncOpenAI,
        model: str,
        thread: list[dict[str, str]],
    ) -> tuple[BpmnProcess, str]:
        """Send the current thread to the LLM and return parsed result + raw text.

        Uses ``responses.create()`` so that ``raw_text`` is always captured
        before any ``ValidationError`` from Pydantic can be raised.
        """
        response = await client.responses.create(
            model=model,
            instructions=self._system_prompt,
            input=thread,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "BpmnProcess",
                    "schema": _make_strict_schema(BpmnProcess.model_json_schema()),
                    "strict": True,
                }
            },
        )

        raw_text = response.output_text
        if not raw_text:
            logger.warning("LLM returned empty output text")
            raise RuntimeError("LLM returned empty structured response")

        logger.debug("Structured response received (%d chars)", len(raw_text))
        data = json.loads(raw_text)
        return BpmnProcess.model_validate(data), raw_text

    def _handle_fallback_repair(
        self, raw_text: str | None, max_retries: int, val_err: ValidationError
    ) -> BpmnProcess:
        if not raw_text:
            raise RuntimeError(
                f"LLM returned invalid BPMN JSON after {max_retries} retries."
            ) from val_err

        try:
            logger.info("Retries exhausted, attempting repair as final fallback...")
            data = json.loads(raw_text)
            data = repair_bpmn_json(data)
            return BpmnProcess.model_validate(data)
        except Exception as repair_err:
            logger.error("Repair fallback failed: %s", repair_err)
            raise RuntimeError(
                f"LLM returned invalid BPMN JSON after {max_retries} "
                "retries and fallback repair failed."
            ) from repair_err

    async def generate(
        self,
        description: str,
        diagram_type: str = "process",
        model: str = "gpt-4o",
        *,
        client: AsyncOpenAI | None = None,
        max_retries: int = 5,
        raw_prompt: bool = False,
    ) -> BpmnProcess:
        """Generate a BPMN process JSON from a description.

        Uses OpenAI structured outputs to guarantee the response
        matches the ``BpmnProcess`` schema exactly.  On validation
        failure, the generation is retried up to *max_retries* times
        using a stateless message thread with accumulated error history
        to educate the LLM on specific validation rules.

        Args:
            description: Human-readable workflow description.
            diagram_type: ``process``, ``collaboration``,
                or ``choreography``.
            model: LLM model name.
            client: Pre-configured ``AsyncOpenAI`` client.
            max_retries: Maximum number of retry attempts after the
                initial structured parse fails (default: 5).
            raw_prompt: If True, use *description* as-is without
                wrapping it in a "Generate a BPMN..." prefix.
                Useful for modification prompts that already
                contain full instructions.

        Returns:
            Parsed ``BpmnProcess`` model instance.

        Raises:
            RuntimeError: If LLM generation fails or all retries are
                exhausted.
        """
        if not client:
            raise RuntimeError(
                "OpenAI client not provided. "
                "Ensure the OpenAIClientService is registered."
            )

        if raw_prompt:
            user_prompt = description
        else:
            user_prompt = (
                f"Generate a BPMN {diagram_type} as flat JSON "
                "for the following workflow. Return only "
                "the JSON object.\n\n"
                f"{description}"
            )

        thread = _build_initial_thread(user_prompt)
        errors: list[str] = []
        raw_text: str | None = None

        for attempt in range(max_retries + 1):
            logger.debug(
                "Current thread for LLM:\n%s",
                "\n".join(msg["content"] for msg in thread),
            )

            try:
                logger.info(
                    "Attempt %d/%d with %d prior error(s)...",
                    attempt,
                    max_retries,
                    len(errors),
                )

                parsed, raw_text = await self._attempt_parse(client, model, thread)
                return parsed

            except ValidationError as val_err:
                errors.append(str(val_err))
                logger.warning(
                    "Structured output failed Pydantic validation (attempt %d): %s",
                    attempt,
                    val_err,
                )

                if attempt < max_retries:
                    if raw_text:
                        thread.append({"role": "assistant", "content": raw_text})
                    thread.append(_build_retry_user_message(errors))
                else:
                    return self._handle_fallback_repair(raw_text, max_retries, val_err)

            except RuntimeError:
                raise

            except Exception as exc:
                logger.error(
                    "BPMN generation failed (%s): %s",
                    type(exc).__name__,
                    exc,
                )
                raise RuntimeError("Failed to generate BPMN diagram via LLM") from exc

        raise RuntimeError("LLM failed to produce valid BPMN JSON")
