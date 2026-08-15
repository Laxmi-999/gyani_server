from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    secret_key :str
    algorithm:str = 'HS256'
    access_token_expire_minutes: int = 60
    refresh_token_expire_days:int =7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False
    )

settings = Settings()