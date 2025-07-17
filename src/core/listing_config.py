"""
Configuration management con Pydantic BaseSettings
Basato su: samuelcolvin/pydantic v2.5.0+
Best practice: https://github.com/pydantic/pydantic
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, field_validator
from typing import Dict, Optional, List
import os

class ListingConfig(BaseSettings):
    """Configurazione centralizzata con validazione e type safety"""
    
    # API Keys (mai in chiaro)
    openai_api_key: Optional[SecretStr] = Field(None)
    huggingface_token: Optional[SecretStr] = Field(None, alias='HF_TOKEN')
    sentry_dsn: Optional[SecretStr] = Field(None)
    
    # Redis Configuration
    redis_url: str = Field('redis://localhost:6379')
    redis_password: Optional[SecretStr] = Field(None)
    cache_ttl: int = Field(3600, ge=60, le=86400)
    
    # AI Models Configuration
    model_title: str = Field('salesforce/bart-large-mnli')
    model_description: str = Field('microsoft/DialoGPT-medium', alias='MODEL_DESC')
    model_sentiment: str = Field('distilbert-base-multilingual-cased')
    
    # Template Configuration
    template_base_path: str = Field('./templates', alias='TEMPLATE_PATH')
    cookiecutter_config: Dict[str, str] = Field(default_factory=dict)
    
    # Retry Configuration
    max_retries: int = Field(5, ge=1, le=10)
    retry_delay: int = Field(2, ge=1, le=60)
    retry_backoff: float = Field(2.0, ge=1.0, le=5.0)
    
    # Monitoring
    prometheus_port: int = Field(8000)
    enable_metrics: bool = Field(True)
    
    @field_validator('redis_url')
    @classmethod
    def validate_redis_url(cls, v):
        if not v.startswith(('redis://', 'rediss://')):
            raise ValueError('Redis URL must start with redis:// or rediss://')
        return v
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'  # Ignora campi extra dalle variabili d'ambiente
    )
        
# Singleton pattern per config
_config: Optional[ListingConfig] = None

def get_config() -> ListingConfig:
    global _config
    if _config is None:
        _config = ListingConfig()
    return _config
