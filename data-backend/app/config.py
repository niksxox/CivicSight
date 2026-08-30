
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg2://civsight_user:civsight_pass@localhost:5432/civsight"
    )
    nearby_radius_meters: int = 1000
    ai_confidence_threshold: float = 0.65

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Import this singleton everywhere instead of re-reading env vars.
settings = Settings()
