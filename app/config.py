try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""
    database_hostname: str = "localhost"
    database_username: str = "postgres"
    database_password: str = "postgres"
    database_name: str = "tradekub"
    database_port: str = "5432"
    secret_key: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    news_data_api_key: str = "pub_2223171d433ff38e0ba97b5fe05231fd2750d"

    model_config = {"env_file": ".env", "extra": "ignore"}




settings = Settings()

