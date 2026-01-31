import enum

from appkit_assistant.backend.schemas import AIModel


class ContextSize(enum.StrEnum):
    """Enum for context size options."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PerplexityAIModel(AIModel):
    """AI model for Perplexity API."""

    search_context_size: ContextSize = ContextSize.MEDIUM
    search_domain_filter: list[str] = []


SONAR = PerplexityAIModel(
    id="sonar",
    text="Perplexity Sonar",
    icon="perplexity",
    model="sonar",
    stream=True,
)

SONAR_PRO = PerplexityAIModel(
    id="sonar-pro",
    text="Perplexity Sonar Pro",
    icon="perplexity",
    model="sonar-pro",
    stream=True,
    keywords=["sonar", "perplexity"],
)

SONAR_DEEP_RESEARCH = PerplexityAIModel(
    id="sonar-deep-research",
    text="Perplexity Deep Research",
    icon="perplexity",
    model="sonar-deep-research",
    search_context_size=ContextSize.HIGH,
    stream=True,
    keywords=["reasoning", "deep", "research", "perplexity"],
)

SONAR_REASONING = PerplexityAIModel(
    id="sonar-reasoning",
    text="Perplexity Reasoning",
    icon="perplexity",
    model="sonar-reasoning",
    search_context_size=ContextSize.HIGH,
    stream=True,
    keywords=["reasoning", "perplexity"],
)
