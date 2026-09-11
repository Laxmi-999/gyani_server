from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    secret_key :str
    algorithm:str = 'HS256'
    access_token_expire_minutes: int = 60
    refresh_token_expire_days:int =7
    redis_host: str = "127.0.0.1"
    redis_port: int = 6380
    redis_db: int = 0
   
    model_config = SettingsConfigDict(
    env_file=".env", 
    extra="ignore",
    env_prefix="",
    case_sensitive=False
    )

settings = Settings()