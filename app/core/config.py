from pydantic import BaseModel


class Settings(BaseModel):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    class Config:
        env_file = ".env"


settings = Settings()
