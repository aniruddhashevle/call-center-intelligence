from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    db_path: str = os.getenv("DB_PATH", "data/app.db")
    db_encryption_key: str | None = os.getenv("DB_ENCRYPTION_KEY")

    whisper_model_size: str = os.getenv("WHISPER_MODEL_SIZE", "base")

    confidence_threshold: float = float(
        os.getenv("CONFIDENCE_THRESHOLD", "0.5")
    )
    low_confidence_halt_ratio: float = float(
        os.getenv("LOW_CONFIDENCE_HALT_RATIO", "0.5")
    )

    max_retries_per_node: int = int(
        os.getenv("MAX_RETRIES_PER_NODE", "3")
    )
    llm_timeout_seconds: int = int(
        os.getenv("LLM_TIMEOUT_SECONDS", "60")
    )

    @property
    def llm_api_keys(self) -> list[str | None]:
        return [
            self.openai_api_key,
            self.google_api_key,
            self.groq_api_key,
        ]


def build_config() -> Config:
    return Config()