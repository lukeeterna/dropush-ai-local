"""
Advanced Template Engine con Cookiecutter
Basato su: cookiecutter/cookiecutter v2.5.0
Ref: https://github.com/cookiecutter/cookiecutter
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from cookiecutter.exceptions import CookiecutterException
from pydantic import BaseModel, Field, ValidationError, field_validator, ConfigDict
import jinja2
from jinja2 import Environment, FileSystemLoader, select_autoescape

class TemplateConfig(BaseModel):
    """Configurazione template con validazione Pydantic"""
    template_id: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., pattern="^(jewelry|electronics|home|health)$")
    language: str = Field("it", pattern="^(it|en|de|fr|es)$")
    version: str = Field("1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "template_id": "jewelry_premium_v1",
                "category": "jewelry",
                "language": "it",
                "version": "1.0.0"
            }
        }
    )

class TemplateData(BaseModel):
    """Dati per rendering template con validazione"""
    product_name: str = Field(..., min_length=3, max_length=200)
    features: List[str] = Field(..., min_length=1, max_length=10)
    benefits: List[str] = Field(default_factory=list)
    price: float = Field(..., gt=0, le=10000)
    category: str
    brand: Optional[str] = None
    
    @field_validator('features', 'benefits')
    @classmethod
    def validate_items(cls, v):
        if isinstance(v, list):
            for item in v:
                if len(item) > 500:
                    raise ValueError('Feature/benefit too long (max 500 chars)')
        return v

class TemplateRegistry:
    """Registry per gestione centralizzata dei template"""
    
    def __init__(self):
        self._templates: Dict[str, TemplateConfig] = {}
        self._categories: Dict[str, List[str]] = {
            'jewelry': [],
            'electronics': [],
            'home': [],
            'health': []
        }
    
    def register(self, config: TemplateConfig) -> None:
        """Registra un nuovo template"""
        self._templates[config.template_id] = config
        if config.category in self._categories:
            if config.template_id not in self._categories[config.category]:
                self._categories[config.category].append(config.template_id)
    
    def get(self, template_id: str) -> Optional[TemplateConfig]:
        """Ottiene configurazione template"""
        return self._templates.get(template_id)
    
    def list_by_category(self, category: str) -> List[str]:
        """Lista template per categoria"""
        return self._categories.get(category, [])
    
    def exists(self, template_id: str) -> bool:
        """Verifica se template esiste"""
        return template_id in self._templates


class AdvancedTemplateEngine:
    """
    Template engine enterprise con supporto multi-template,
    validazione, caching e versioning
    """
    
    def __init__(self, base_path: str = "./templates", cache: Optional[Any] = None):
        self.base_path = Path(base_path)
        self.cache = cache
        self._ensure_directories()
        
        # Jinja2 environment per template semplici
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.base_path)),
            autoescape=select_autoescape(['html', 'xml']),
            cache_size=50
        )
        
        # Template registry
        self._registry: Dict[str, TemplateConfig] = {}
        self._load_registry()
        
    def _mock_cookiecutter(self, template, extra_context=None, no_input=True, output_dir=None):
        """Mock cookiecutter per testing"""
        return {"project_name": "mock_project", "files": []}

    def _ensure_directories(self):
        """Crea struttura directory se non esiste"""
        dirs = ['jewelry', 'electronics', 'home', 'health']
        for d in dirs:
            (self.base_path / d).mkdir(parents=True, exist_ok=True)
            
    def _load_registry(self):
        """Carica registry template da file"""
        registry_file = self.base_path / "registry.json"
        if registry_file.exists():
            with open(registry_file) as f:
                data = json.load(f)
                for item in data:
                    config = TemplateConfig(**item)
                    self._registry[config.template_id] = config
                    
    def register_template(self, config: TemplateConfig, template_dir: str):
        """Registra nuovo template"""
        # Validate template exists
        template_path = self.base_path / config.category / template_dir
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
            
        # Add to registry
        self._registry[config.template_id] = config
        self._save_registry()
        
    def _save_registry(self):
        """Salva registry su file"""
        registry_file = self.base_path / "registry.json"
        data = [config.dict() for config in self._registry.values()]
        with open(registry_file, 'w') as f:
            json.dump(data, f, indent=2)
            
    async def render_template(
        self,
        template_id: str,
        data: Dict[str, Any],
        output_format: str = "html"
    ) -> str:
        """
        Render template con validazione e caching
        """
        # Validate template exists
        if template_id not in self._registry:
            raise ValueError(f"Template not found: {template_id}")
            
        config = self._registry[template_id]
        
        # Validate data
        try:
            validated_data = TemplateData(**data, category=config.category)
        except ValidationError as e:
            raise ValueError(f"Invalid template data: {e}")
            
        # Check cache
        if self.cache:
            cache_key = f"template:{template_id}:{hash(str(validated_data.dict()))}"
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
                
        # Render based on type
        if output_format == "cookiecutter":
            result = await self._render_cookiecutter(config, validated_data)
        else:
            result = await self._render_jinja(config, validated_data)
            
        # Cache result
        if self.cache:
            await self.cache.set(cache_key, result, ttl=3600)
            
        return result
        
    async def _render_cookiecutter(self, config: TemplateConfig, data: TemplateData) -> str:
        """Render usando cookiecutter per template complessi"""
        template_path = self.base_path / config.category / config.template_id
        
        try:
            # Prepare context
            context = {
                'cookiecutter': data.dict()
            }
            
            # Render
            output_dir = self._mock_cookiecutter(
                str(template_path),
                extra_context=context,
                no_input=True,
                output_dir="/tmp/rendered_templates"
            )
            
            # Read rendered content
            # (implementation depends on template structure)
            
        except CookiecutterException as e:
            raise RuntimeError(f"Template rendering failed: {e}")
            
    async def _render_jinja(self, config: TemplateConfig, data: TemplateData) -> str:
        """Render usando Jinja2 per template semplici"""
        template_file = f"{config.category}/{config.template_id}.j2"
        
        try:
            template = self.jinja_env.get_template(template_file)
            return template.render(**data.dict())
        except jinja2.TemplateError as e:
            raise RuntimeError(f"Jinja rendering failed: {e}")
