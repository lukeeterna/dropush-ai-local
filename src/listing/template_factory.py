"""
Factory e Builder pattern per template - VERSIONE MOCK SENZA COOKIECUTTER
"""
from abc import ABC, abstractmethod
from typing import Dict, Type, Optional, List, Any
import json
import os

class BaseTemplate(ABC):
    """Base class per tutti i template"""
    
    @abstractmethod
    def get_structure(self) -> Dict[str, Any]:
        """Ritorna struttura template"""
        pass
        
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """Valida dati per template"""
        pass

class JewelryTemplate(BaseTemplate):
    """Template specifico per gioielli"""
    
    def get_structure(self) -> Dict[str, Any]:
        return {
            "title": "{product_name} - {material} {style}",
            "sections": ["description", "features", "care_instructions"],
            "required_fields": ["product_name", "material", "style"]
        }
        
    def validate(self, data: Dict[str, Any]) -> bool:
        required = ["product_name", "material", "style"]
        return all(field in data for field in required)

class ElectronicsTemplate(BaseTemplate):
    """Template specifico per elettronica"""
    
    def get_structure(self) -> Dict[str, Any]:
        return {
            "title": "{brand} {product_name} - {model}",
            "sections": ["specifications", "features", "warranty"],
            "required_fields": ["product_name", "brand", "model"]
        }
        
    def validate(self, data: Dict[str, Any]) -> bool:
        required = ["product_name", "brand", "model"]
        return all(field in data for field in required)

class HomeTemplate(BaseTemplate):
    """Template specifico per casa"""
    
    def get_structure(self) -> Dict[str, Any]:
        return {
            "title": "{product_name} - {category}",
            "sections": ["description", "features", "dimensions"],
            "required_fields": ["product_name", "category"]
        }
        
    def validate(self, data: Dict[str, Any]) -> bool:
        required = ["product_name", "category"]
        return all(field in data for field in required)

class TemplateFactory:
    """Factory per creazione template"""
    
    _templates: Dict[str, Type[BaseTemplate]] = {
        "jewelry": JewelryTemplate,
        "electronics": ElectronicsTemplate,
        "home": HomeTemplate
    }
    
    @classmethod
    def register_template(cls, name: str, template_class: Type[BaseTemplate]):
        cls._templates[name] = template_class
        
    @classmethod
    def create_template(cls, category: str) -> BaseTemplate:
        template_class = cls._templates.get(category.lower())
        if not template_class:
            raise ValueError(f"Template for category {category} not found")
        return template_class()
        
    @classmethod
    def list_templates(cls) -> List[str]:
        return list(cls._templates.keys())

class TemplateBuilder:
    """Builder pattern per costruzione template"""
    
    def __init__(self):
        self._title = ""
        self._sections = {}
        self._metadata = {}
        
    def set_title(self, title: str) -> "TemplateBuilder":
        self._title = title
        return self
        
    def add_section(self, name: str, content: str) -> "TemplateBuilder":
        self._sections[name] = content
        return self
        
    def set_metadata(self, key: str, value: Any) -> "TemplateBuilder":
        self._metadata[key] = value
        return self
        
    def set_footer(self, footer: str) -> "TemplateBuilder":
        self._sections["footer"] = footer
        return self
        
    def build(self) -> str:
        """Costruisce il template finale"""
        template_parts = [self._title]
        
        for section_name, content in self._sections.items():
            template_parts.append(f"\n## {section_name.title()}\n{content}")
            
        return "\n".join(template_parts)

# Mock cookiecutter function se importato
def from_cookiecutter(*args, **kwargs):
    """Mock function per cookiecutter"""
    return {
        "project_name": "Mock Project",
        "version": "1.0.0"
    }
