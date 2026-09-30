import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "REPOEVOLUTION"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Directory Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PROMPTS_DIR: Path = BASE_DIR / "prompts"
    DATA_DIR: Path = BASE_DIR / "data"
    FAISS_INDEX_DIR: Path = DATA_DIR / "faiss_index"

    # LLM Settings
    GEMINI_API_KEY: str = ""
    DEFAULT_GEMINI_MODEL: str = "gemini-2.5-flash"

    # Embedding Settings
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_prompt_template(self, template_name: str) -> str:
        prompt_path = self.PROMPTS_DIR / template_name
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        raise FileNotFoundError(f"Prompt template {template_name} not found in {self.PROMPTS_DIR}")


settings = Settings()
