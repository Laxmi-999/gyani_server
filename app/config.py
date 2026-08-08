from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    secret_key :str
    algorithm:str = 'HS256'
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensetive=False
    )

settings = Settings()