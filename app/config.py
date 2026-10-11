from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = Path(__file__).resolve().parent.parent / "data"

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"

    @property
    def experience_bank_path(self) -> Path:
        return self.data_dir / "experience_bank.yaml"

    @property
    def background_path(self) -> Path:
        return self.data_dir / "background.md"

    @property
    def resume_template_path(self) -> Path:
        return self.data_dir / "resume_template.tex"

    @property
    def output_dir(self) -> Path:
        return self.data_dir / "output"

    def provider(self) -> str | None:
        if self.openai_api_key:
            return "openai"
        if self.anthropic_api_key:
            return "anthropic"
        return None


settings = Settings()
