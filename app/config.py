from pydantic_settings import BaseSettings, settingConfigDict

class Settings(BaseSettings):
    database_url: str
    secrete_key :str
    algorithm:str = 'HS256'
    access_token_expire_minutes: int = 60

    model_config = settingConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensetive=False
    )
    settings = Settings()