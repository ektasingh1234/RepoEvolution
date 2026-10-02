import os
from abc import ABC, abstractmethod
from typing import List, Optional
from src.core.config import settings
from src.core.models import Citation, CodeEntity, CopilotResponse

try:
    from google import genai
    from google.genai import types
    HAVE_GEMINI_SDK = True
except ImportError:
    HAVE_GEMINI_SDK = False


from src.core.logging_config import get_logger

logger = get_logger(__name__)

class LLMProvider(ABC):
    """
    Abstract Base Class for LLM providers (GeminiProvider, OpenAIProvider, MockProvider).
    """

    @abstractmethod
    def generate_grounded_answer(
        self,
        question: str,
        retrieved_entities: List[CodeEntity],
        evidence_summary: str,
    ) -> CopilotResponse:
        """
        Generate grounded response from evidence context.
        """
        pass

    @abstractmethod
    def get_available_model_name(self) -> str:
        """Return the active model name being used."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if provider is currently initialized and operational without quota/auth errors."""
        pass

    def get_provider_name(self) -> str:
        """Return display name of LLM provider."""
        return self.__class__.__name__.replace("Provider", "")


class GeminiProvider(LLMProvider):
    """
    Gemini API implementation of LLMProvider.
    Uses google-genai SDK with dynamic model discovery/fallback.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        self.client = None
        self.active_model = settings.DEFAULT_GEMINI_MODEL
        self._available = False

        if HAVE_GEMINI_SDK and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                verified_model = self._verify_or_select_model()
                if verified_model:
                    self.active_model = verified_model
                    self._available = True
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini Client: {e}")
                self._available = False

    def is_available(self) -> bool:
        return self._available and self.client is not None

    def get_provider_name(self) -> str:
        return "Gemini" if self.is_available() else "Unavailable"

    def _verify_or_select_model(self) -> Optional[str]:
        """Verify configured model availability or select valid available model."""
        if not self.client:
            return None

        preferred_models = [
            "gemini-3.1-flash-lite",
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-flash-latest",
            "gemini-3.8-flash",
            "gemini-3.5-flash",
            settings.DEFAULT_GEMINI_MODEL,
        ]

        try:
            available_models = [m.name for m in self.client.models.list()]
            for pref in preferred_models:
                for avail in available_models:
                    if pref in avail:
                        candidate = avail.replace("models/", "")
                        try:
                            self.client.models.generate_content(model=candidate, contents="ping")
                            return candidate
                        except Exception as ping_err:
                            err_msg = str(ping_err).lower()
                            if "429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg:
                                logger.warning(f"Gemini API quota exhausted during model verification: {ping_err}")
                                return None
                            logger.info(f"Model {candidate} ping check failed: {ping_err}")
                            continue
            if available_models:
                for avail in available_models:
                    candidate = avail.replace("models/", "")
                    try:
                        self.client.models.generate_content(model=candidate, contents="ping")
                        return candidate
                    except Exception as ping_err:
                        err_msg = str(ping_err).lower()
                        if "429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg:
                            logger.warning(f"Gemini API quota exhausted during model verification: {ping_err}")
                            return None
                        continue
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg:
                logger.warning(f"Gemini API quota exhausted: {e}")
                return None
            logger.info(f"Model verification check failed: {e}")

        return None

    def get_available_model_name(self) -> str:
        return self.active_model if self.is_available() else "None"

    def generate_grounded_answer(
        self,
        question: str,
        retrieved_entities: List[CodeEntity],
        evidence_summary: str,
    ) -> CopilotResponse:
        # Construct citations list from retrieved entities
        citations = []
        for e in retrieved_entities:
            ref = f"{e.file_path}#L{e.start_line}-L{e.end_line}"
            citations.append(
                Citation(
                    source_type="file",
                    reference=ref,
                    file_path=e.file_path,
                    start_line=e.start_line,
                    end_line=e.end_line,
                    snippet=f"{e.signature} ({e.entity_type.value})",
                )
            )

        # Fallback if no LLM client or API key available or quota exhausted
        if not self.is_available():
            fallback_answer = (
                f"### [Offline Evidence-Grounded Analysis]\n\n"
                f"**Question:** {question}\n\n"
                f"*(Note: AI provider is currently offline or quota exhausted. Showing structured evidence retrieved directly from repository AST index.)*\n\n"
                f"#### Relevant Extracted Code Entities ({len(retrieved_entities)} retrieved):\n\n"
            )
            for idx, e in enumerate(retrieved_entities, 1):
                fallback_answer += (
                    f"{idx}. **`{e.name}`** (`{e.entity_type.value}` in `{e.file_path}:L{e.start_line}-L{e.end_line}`)\n"
                    f"   * Signature: `{e.signature}`\n"
                )
                if e.docstring:
                    fallback_answer += f"   * Docstring: *\"{e.docstring.strip()}\"*\n"
                fallback_answer += f"   * Dependencies: `{', '.join(e.dependencies) if e.dependencies else 'None'}`\n\n"

            return CopilotResponse(
                question=question,
                answer=fallback_answer,
                citations=citations,
                retrieved_entities=retrieved_entities,
                model_used="offline-evidence-retriever",
                groundedness_score=1.0,
            )

        # Build prompt using external system prompt template
        try:
            system_template = settings.get_prompt_template("system_copilot.txt")
        except FileNotFoundError:
            system_template = "Answer the user question using repository evidence below:\n<repository_evidence>\n{evidence_bundle}\n</repository_evidence>"

        full_prompt = system_template.format(evidence_bundle=evidence_summary)
        full_prompt += f"\n\nUser Question: {question}\n\nProvide your evidence-grounded answer:"

        models_to_try = [self.active_model]

        last_error = None
        for model in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=full_prompt,
                )
                answer_text = response.text or "No text returned by Gemini API."
                self.active_model = model

                return CopilotResponse(
                    question=question,
                    answer=answer_text,
                    citations=citations,
                    retrieved_entities=retrieved_entities,
                    model_used=model,
                    groundedness_score=0.95,
                )
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg:
                    self._available = False
                    logger.warning(f"Gemini API quota exhausted in generate_grounded_answer: {e}")
                    break
                logger.warning(f"Model {model} failed in generate_grounded_answer: {e}")
                last_error = e

        fallback_answer = (
            f"### [Offline Evidence-Grounded Analysis]\n\n"
            f"**Question:** {question}\n\n"
            f"*(Note: Gemini API quota has been reached. Showing structured evidence retrieved directly from repository AST index.)*\n\n"
            f"#### Relevant Extracted Code Entities ({len(retrieved_entities)} retrieved):\n\n"
        )
        for idx, e in enumerate(retrieved_entities, 1):
            fallback_answer += (
                f"{idx}. **`{e.name}`** (`{e.entity_type.value}` in `{e.file_path}:L{e.start_line}-L{e.end_line}`)\n"
                f"   * Signature: `{e.signature}`\n"
            )
            if e.docstring:
                fallback_answer += f"   * Docstring: *\"{e.docstring.strip()}\"*\n"
            fallback_answer += f"   * Dependencies: `{', '.join(e.dependencies) if e.dependencies else 'None'}`\n\n"

        return CopilotResponse(
            question=question,
            answer=fallback_answer,
            citations=citations,
            retrieved_entities=retrieved_entities,
            model_used="offline-evidence-retriever",
            groundedness_score=1.0,
        )
