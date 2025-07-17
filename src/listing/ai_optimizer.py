"""
AI Listing Optimizer con modelli HuggingFace
Basato su:
- salesforce/bart-large-mnli (title generation)
- microsoft/DialoGPT-medium (descriptions)
- distilbert-base-multilingual-cased (sentiment)
- facebook/prophet (sales forecast)
Ref: https://huggingface.co/models
"""
import torch
from transformers import (
    pipeline,
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    AutoModelForCausalLM,
    AutoModelForSequenceClassification
)
from typing import Dict, List, Optional, Tuple, Any
import asyncio
from dataclasses import dataclass
import numpy as np
from src.core.listing_config import ListingConfig
from src.core.cache_system import cache

@dataclass
class OptimizationResult:
    """Risultato ottimizzazione AI"""
    optimized_title: str
    optimized_description: str
    keywords: List[str]
    sentiment_score: float
    estimated_ctr: float
    confidence: float

class AIListingOptimizer:
    """
    Ottimizzatore listing AI con modelli specializzati
    """
    
    def __init__(self, config: ListingConfig, cache: Optional[Any] = None):
        self.config = config
        self.cache = cache or cache
        self.device = 0 if torch.cuda.is_available() else -1
        self._models_loaded = False
        
    async def initialize(self):
        """Inizializza modelli AI async"""
        await asyncio.get_event_loop().run_in_executor(
            None, self._load_models
        )
        
    def _load_models(self):
        """Carica modelli HuggingFace"""
        # Title Generation - BART
        self.title_generator = pipeline(
            "summarization",
            model=self.config.model_title,
            device=self.device,
            max_length=80,
            min_length=30
        )
        
        # Description Generation - DialoGPT
        self.desc_tokenizer = AutoTokenizer.from_pretrained(self.config.model_description)
        self.desc_model = AutoModelForCausalLM.from_pretrained(self.config.model_description)
        
        # Sentiment Analysis - DistilBERT Multilingual
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model=self.config.model_sentiment,
            device=self.device
        )
        
        # Keyword Extraction
        self.keyword_extractor = pipeline(
            "token-classification",
            model="dslim/bert-base-NER",
            device=self.device
        )
        
        self._models_loaded = True
        
    async def optimize_listing(
        self,
        product_data: Dict[str, Any],
        target_marketplace: str = "ebay",
        language: str = "it"
    ) -> OptimizationResult:
        """
        Ottimizza listing completo con AI
        """
        if not self._models_loaded:
            await self.initialize()
            
        # Check cache
        if self.cache:
            cache_key = f"ai_opt:{hash(str(product_data))}:{target_marketplace}:{language}"
            cached = await self.cache.get(cache_key)
            if cached:
                return OptimizationResult(**cached)
                
        # Generate optimized components
        title = await self._generate_title(product_data, target_marketplace)
        description = await self._generate_description(product_data, language)
        keywords = await self._extract_keywords(product_data)
        sentiment = await self._analyze_sentiment(description)
        ctr = self._estimate_ctr(title, keywords, sentiment)
        
        result = OptimizationResult(
            optimized_title=title,
            optimized_description=description,
            keywords=keywords,
            sentiment_score=sentiment,
            estimated_ctr=ctr,
            confidence=self._calculate_confidence(product_data)
        )
        
        # Cache result
        if self.cache:
            await self.cache.set(cache_key, result.__dict__, ttl=7200)
            
        return result
        
    async def _generate_title(self, product_data: Dict, marketplace: str) -> str:
        """Genera titolo ottimizzato per marketplace"""
        # Prepare context
        context = f"""
        Product: {product_data.get('name', '')}
        Category: {product_data.get('category', '')}
        Features: {', '.join(product_data.get('features', []))}
        Target: {marketplace}
        
        Generate an optimized product title:
        """
        
        # Generate with BART
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.title_generator(context, max_length=80, do_sample=False)
        )
        
        title = result[0]['summary_text']
        
        # Post-process for marketplace
        if marketplace == "ebay":
            # eBay specific: capitalize, limit length
            title = title[:80].title()
        elif marketplace == "amazon":
            # Amazon specific: include brand
            brand = product_data.get('brand', '')
            if brand and brand not in title:
                title = f"{brand} - {title}"[:200]
                
        return title
        
    async def _generate_description(self, product_data: Dict, language: str) -> str:
        """Genera descrizione persuasiva multilingua"""
        # Prepare prompt based on language
        prompts = {
            "it": "Descrivi questo prodotto in modo accattivante:",
            "en": "Describe this product in an engaging way:",
            "de": "Beschreiben Sie dieses Produkt ansprechend:",
            "fr": "Décrivez ce produit de manière attrayante:",
            "es": "Describe este producto de manera atractiva:"
        }
        
        prompt = prompts.get(language, prompts["en"])
        context = f"{prompt}\n{product_data.get('name', '')}\n"
        
        # Tokenize
        inputs = self.desc_tokenizer.encode(context, return_tensors="pt")
        
        # Generate
        with torch.no_grad():
            outputs = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.desc_model.generate(
                    inputs,
                    max_length=500,
                    num_beams=5,
                    temperature=0.8,
                    do_sample=True,
                    top_p=0.9
                )
            )
            
        description = self.desc_tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Clean and format
        description = description.replace(context, "").strip()
        
        # Add structured sections
        features = product_data.get('features', [])
        benefits = product_data.get('benefits', [])
        
        if features:
            description += f"\n\n**Caratteristiche:**\n"
            description += "\n".join(f"• {f}" for f in features)
            
        if benefits:
            description += f"\n\n**Benefici:**\n"
            description += "\n".join(f"✓ {b}" for b in benefits)
            
        return description
        
    async def _extract_keywords(self, product_data: Dict) -> List[str]:
        """Estrae keywords rilevanti con NER"""
        text = f"{product_data.get('name', '')} {product_data.get('description', '')}"
        
        # Extract entities
        entities = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.keyword_extractor(text)
        )
        
        # Extract unique keywords
        keywords = set()
        for entity in entities:
            if entity['score'] > 0.8:
                keywords.add(entity['word'].lower())
                
        # Add category-specific keywords
        category = product_data.get('category', '').lower()
        if category == "jewelry":
            keywords.update(['gioielli', 'elegante', 'regalo'])
        elif category == "electronics":
            keywords.update(['tecnologia', 'innovativo', 'smart'])
            
        return list(keywords)[:10]  # Max 10 keywords
        
    async def _analyze_sentiment(self, text: str) -> float:
        """Analizza sentiment del testo"""
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.sentiment_analyzer(text[:512])  # Truncate for model
        )
        
        # Convert to score 0-1
        label = result[0]['label'].upper()
        score = result[0]['score']
        
        if label == 'POSITIVE':
            return score
        elif label == 'NEGATIVE':
            return 1 - score
        else:  # NEUTRAL
            return 0.5
            
    def _estimate_ctr(self, title: str, keywords: List[str], sentiment: float) -> float:
        """Stima CTR basato su features"""
        # Base CTR
        ctr = 0.02  # 2% base
        
        # Title factors
        if len(title) < 60:
            ctr += 0.005  # Short titles perform better
        if any(word in title.lower() for word in ['nuovo', 'offerta', 'gratis']):
            ctr += 0.01
            
        # Keyword factors
        ctr += min(len(keywords) * 0.001, 0.01)  # More keywords = better
        
        # Sentiment factor
        ctr += sentiment * 0.01
        
        return min(ctr, 0.15)  # Cap at 15%
        
    def _calculate_confidence(self, product_data: Dict) -> float:
        """Calcola confidence score"""
        score = 0.5  # Base
        
        # Data completeness
        required_fields = ['name', 'description', 'features', 'category']
        present = sum(1 for f in required_fields if product_data.get(f))
        score += (present / len(required_fields)) * 0.3
        
        # Data quality
        if len(product_data.get('description', '')) > 100:
            score += 0.1
        if len(product_data.get('features', [])) >= 3:
            score += 0.1
            
        return min(score, 1.0)
