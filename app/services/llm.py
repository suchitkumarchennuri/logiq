"""Interface layer around the local LLM used for answer generation."""

from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock
from typing import Iterable, Optional

from app.core.config import get_settings

try:
    from llama_cpp import Llama  # type: ignore
except ImportError:  # pragma: no cover - optional dependency at runtime
    Llama = None  # type: ignore


DEFAULT_SYSTEM_PROMPT = (
    "You are Logiq, an assistant that explains application logs clearly and accurately. "
    "Use only the provided logs as evidence."
)


logger = logging.getLogger(__name__)


class LLMService:
    """Lazy wrapper around `llama_cpp` that falls back to deterministic summaries."""

    def __init__(
        self,
        model_path: Optional[str],
        *,
        n_ctx: int = 4096,
        n_threads: int = 0,
        n_gpu_layers: int = 0,
        batch_size: int = 512,
        temperature: float = 0.1,
        top_p: float = 0.9,
    ) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self.batch_size = batch_size
        self.temperature = temperature
        self.top_p = top_p
        self._lock = Lock()
        self._llm: Optional[Llama] = None
        self._load_failed = False
        self._load_error: Optional[str] = None

    def _ensure_model(self) -> Optional[Llama]:
        if self._llm is not None:
            return self._llm

        if self.model_path is None:
            self._load_error = "No LLM model path configured."
            return None

        if self._load_failed:
            return None

        if not self.model_path.exists():
            logger.warning(
                "LLM model path %s does not exist; falling back to extractive summaries.",
                self.model_path,
            )
            self._load_error = f"Model file {self.model_path} does not exist."
            return None

        if Llama is None:
            logger.warning(
                "llama_cpp is not installed; falling back to extractive summaries."
            )
            self._load_error = "llama_cpp Python bindings are not installed."
            return None

        with self._lock:
            if self._llm is None and not self._load_failed:
                try:
                    self._llm = Llama(
                        model_path=str(self.model_path),
                        n_ctx=self.n_ctx,
                        n_threads=self.n_threads,
                        n_gpu_layers=self.n_gpu_layers,
                        n_batch=self.batch_size,
                        embedding=False,
                    )
                    self._load_error = None
                except Exception as exc:  # pragma: no cover - defensive runtime guard
                    logger.error(
                        "Failed to load LLM model from %s: %s", self.model_path, exc, exc_info=True
                    )
                    self._load_failed = True
                    self._load_error = str(exc)
                    self._llm = None
        return self._llm

    def build_prompt(self, question: str, logs: Iterable[dict]) -> str:
        """Assemble the prompt passed to the model."""

        parts = [f"System: {DEFAULT_SYSTEM_PROMPT}",
                 f"User question: {question}"]
        formatted_logs = []
        for item in logs:
            formatted_logs.append(
                f"- [{item['log_timestamp']}] {item['service']} {item['level']}: {item['message']}"
            )
        if formatted_logs:
            parts.append("Relevant logs:\n" + "\n".join(formatted_logs))
        parts.append("Respond with a concise answer that references the logs.")
        return "\n\n".join(parts)

    def generate(self, question: str, logs: Iterable[dict]) -> str:
        """Return an answer string derived from the provided context."""

        llm = self._ensure_model()
        logs_list = list(logs)

        if llm is None:
            return self._fallback_answer(question, logs_list)

        prompt = self.build_prompt(question, logs_list)
        response = llm.create_completion(
            prompt=prompt,
            max_tokens=512,
            temperature=self.temperature,
            top_p=self.top_p,
            stop=["System:", "User:", "Assistant:"],
        )
        text = response.get("choices", [{}])[0].get("text", "").strip()
        if not text:
            return self._fallback_answer(question, logs_list)
        return text

    def _fallback_answer(self, question: str, logs: Iterable[dict]) -> str:
        """Simple extractive fallback when no model is available."""

        logs_list = list(logs)
        if not logs_list:
            return "No relevant logs were found to answer the question."

        reason = self._load_error or "Unable to access the configured LLM."
        summary_lines = [
            f"{reason} Returning raw log details instead.",
            f"Question: {question}",
            "Top matching logs:",
        ]
        for item in logs_list:
            summary_lines.append(
                f"- {item['log_timestamp']} [{item['service']}:{item['level']}] {item['message']}"
            )
        return "\n".join(summary_lines)


_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Return a process-wide LLM service instance."""

    global _llm_service
    if _llm_service is None:
        settings = get_settings()
        _llm_service = LLMService(
            settings.llm_model_path,
            n_ctx=settings.llm_n_ctx,
            n_threads=settings.llm_n_threads,
            n_gpu_layers=settings.llm_n_gpu_layers,
            batch_size=settings.llm_batch_size,
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
        )
    return _llm_service
