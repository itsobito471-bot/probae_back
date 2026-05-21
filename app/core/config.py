from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "ProBae API"
    environment: str = "development"
    database_url: str
    redis_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Email Settings
    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: int = 465
    mail_server: str = "smtp.gmail.com"



    r2_account_id: str
    r2_access_key: str
    r2_secret_key: str
    r2_bucket_name: str

    # Loads variables from the .env file in the root directory
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Instantiate settings to be imported across the app
settings = Settings()