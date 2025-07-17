"""
GPU acceleration per modelli HuggingFace
Detecta CUDA/MPS (Mac) automaticamente
Ottimizzato per batch processing
"""
import torch
from transformers import (
    pipeline,
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    AutoModelForCausalLM,
    AutoModelForSequenceClassification
)
from typing import List, Dict, Any, Optional, Union
import logging
import asyncio
from functools import lru_cache
import numpy as np

from src.core.dependencies import DIContainer
from src.core.monitoring import MetricsCollector

logger = logging.getLogger(__name__)


class GPUOptimizer:
    """
    GPU-accelerated optimizer per modelli AI
    Supporta CUDA (NVIDIA) e MPS (Apple Silicon)
    """
    
    def __init__(self, container: DIContainer):
        self.container = container
        self.config = container.resolve('config')
        self.metrics = container.resolve('metrics')
        
        # Detect best device
        self.device = self._detect_best_device()
        logger.info(f"GPU Optimizer using device: {self.device}")
        
        # Model cache
        self._models = {}
        self._tokenizers = {}
        
        # Batch settings ottimizzati per device
        self.batch_config = self._get_optimal_batch_config()
    
    def _detect_best_device(self) -> str:
        """Rileva il miglior device disponibile"""
        if torch.cuda.is_available():
            # NVIDIA GPU
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"CUDA device detected: {gpu_name}")
            
            # Log GPU memory
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info(f"GPU memory: {total_memory:.2f} GB")
            
            return "cuda"
            
        elif torch.backends.mps.is_available():
            # Apple Silicon GPU
            logger.info("Apple Silicon MPS device detected")
            return "mps"
            
        else:
            # CPU fallback
            logger.warning("No GPU detected, using CPU")
            return "cpu"
    
    def _get_optimal_batch_config(self) -> Dict[str, int]:
        """Determina configurazione batch ottimale per device"""
        if self.device == "cuda":
            # Check GPU memory
            if torch.cuda.is_available():
                memory_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
                
                if memory_gb >= 16:  # High-end GPU
                    return {
                        'title_batch': 64,
                        'description_batch': 32,
                        'sentiment_batch': 128,
                        'max_length': 512
                    }
                elif memory_gb >= 8:  # Mid-range GPU
                    return {
                        'title_batch': 32,
                        'description_batch': 16,
                        'sentiment_batch': 64,
                        'max_length': 256
                    }
                else:  # Low-end GPU
                    return {
                        'title_batch': 16,
                        'description_batch': 8,
                        'sentiment_batch': 32,
                        'max_length': 128
                    }
                    
        elif self.device == "mps":
            # Apple Silicon (conservativo per stabilità)
            return {
                'title_batch': 16,
                'description_batch': 8,
                'sentiment_batch': 32,
                'max_length': 256
            }
            
        else:
            # CPU (batch piccoli)
            return {
                'title_batch': 4,
                'description_batch': 2,
                'sentiment_batch': 8,
                'max_length': 128
            }
    
    @lru_cache(maxsize=3)
    def _get_model(self, model_name: str, model_type: str):
        """Carica e cacha modelli"""
        cache_key = f"{model_type}_{model_name}"
        
        if cache_key not in self._models:
            logger.info(f"Loading model {model_name} to {self.device}")
            
            if model_type == "seq2seq":
                model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            elif model_type == "causal":
                model = AutoModelForCausalLM.from_pretrained(model_name)
            elif model_type == "classification":
                model = AutoModelForSequenceClassification.from_pretrained(model_name)
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            
            # Move to device
            model = model.to(self.device)
            
            # Optimization for inference
            model.eval()
            if self.device == "cuda":
                model = model.half()  # FP16 for faster inference
            
            self._models[cache_key] = model
            
            # Load tokenizer
            self._tokenizers[cache_key] = AutoTokenizer.from_pretrained(model_name)
        
        return self._models[cache_key], self._tokenizers[cache_key]
    
    async def optimize_titles_batch(
        self,
        titles: List[str],
        categories: List[str],
        max_length: int = 80
    ) -> List[str]:
        """
        Ottimizza batch di titoli usando GPU
        
        Args:
            titles: Lista titoli originali
            categories: Lista categorie corrispondenti
            max_length: Lunghezza massima titolo
            
        Returns:
            Lista titoli ottimizzati
        """
        model_name = self.config.model_title
        model, tokenizer = self._get_model(model_name, "seq2seq")
        
        # Prepara input con template
        inputs = [
            f"optimize title for {cat}: {title}"
            for title, cat in zip(titles, categories)
        ]
        
        # Process in sub-batches per gestire memoria
        batch_size = self.batch_config['title_batch']
        optimized_titles = []
        
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i:i + batch_size]
            
            # Tokenize
            encoded = tokenizer(
                batch,
                max_length=self.batch_config['max_length'],
                truncation=True,
                padding=True,
                return_tensors="pt"
            ).to(self.device)
            
            # Generate
            with torch.no_grad():
                outputs = model.generate(
                    **encoded,
                    max_length=max_length,
                    num_beams=4,
                    length_penalty=1.0,
                    early_stopping=True
                )
            
            # Decode
            decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)
            optimized_titles.extend(decoded)
            
            # Free memory
            del encoded, outputs
            if self.device == "cuda":
                torch.cuda.empty_cache()
        
        # Log performance
        await self.metrics.increment(
            'gpu.titles_processed',
            len(titles),
            tags={'device': self.device}
        )
        
        return optimized_titles
    
    async def generate_descriptions_batch(
        self,
        titles: List[str],
        original_descriptions: List[str],
        categories: List[str]
    ) -> List[str]:
        """
        Genera descrizioni ottimizzate in batch
        
        Args:
            titles: Titoli prodotti
            original_descriptions: Descrizioni originali
            categories: Categorie prodotti
            
        Returns:
            Lista descrizioni ottimizzate
        """
        model_name = self.config.model_description
        model, tokenizer = self._get_model(model_name, "causal")
        
        # Template per generazione
        prompts = [
            f"Product: {title}\nCategory: {cat}\nOriginal: {desc[:100]}...\n"
            f"Generate an optimized product description:\n"
            for title, desc, cat in zip(titles, original_descriptions, categories)
        ]
        
        batch_size = self.batch_config['description_batch']
        generated_descriptions = []
        
        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i + batch_size]
            
            # Tokenize
            encoded = tokenizer(
                batch,
                max_length=self.batch_config['max_length'],
                truncation=True,
                padding=True,
                return_tensors="pt"
            ).to(self.device)
            
            # Generate
            with torch.no_grad():
                outputs = model.generate(
                    **encoded,
                    max_new_tokens=200,
                    temperature=0.8,
                    top_p=0.9,
                    do_sample=True
                )
            
            # Extract generated part only
            input_length = encoded['input_ids'].shape[1]
            generated_ids = outputs[:, input_length:]
            
            # Decode
            decoded = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)
            generated_descriptions.extend(decoded)
            
            # Free memory
            del encoded, outputs, generated_ids
            if self.device == "cuda":
                torch.cuda.empty_cache()
        
        return generated_descriptions
    
    async def extract_keywords_batch(
        self,
        texts: List[str],
        max_keywords: int = 10
    ) -> List[List[str]]:
        """
        Estrae keywords da batch di testi
        
        Args:
            texts: Lista testi da analizzare
            max_keywords: Max keywords per testo
            
        Returns:
            Lista di liste keywords
        """
        # Usa NER pipeline per keyword extraction
        try:
            ner_pipeline = pipeline(
                "ner",
                model="dslim/bert-base-NER",
                device=0 if self.device == "cuda" else -1
            )
            
            batch_size = self.batch_config['sentiment_batch']
            all_keywords = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                # Run NER
                batch_entities = ner_pipeline(batch)
                
                # Extract unique entities as keywords
                for entities in batch_entities:
                    keywords = list(set([
                        ent['word'].replace('##', '')
                        for ent in entities
                        if ent['score'] > 0.8
                    ]))[:max_keywords]
                    
                    all_keywords.append(keywords)
            
            return all_keywords
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            # Fallback semplice
            return [text.split()[:max_keywords] for text in texts]
    
    async def analyze_sentiment_batch(
        self,
        texts: List[str]
    ) -> List[float]:
        """
        Analizza sentiment per batch di testi
        
        Args:
            texts: Lista testi da analizzare
            
        Returns:
            Lista sentiment scores (-1 a 1)
        """
        model_name = self.config.model_sentiment
        
        # Crea pipeline sentiment
        sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model=model_name,
            device=0 if self.device == "cuda" else -1
        )
        
        batch_size = self.batch_config['sentiment_batch']
        all_sentiments = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Analyze
            results = sentiment_pipeline(batch)
            
            # Convert to normalized scores
            for result in results:
                if result['label'] == 'POSITIVE':
                    score = result['score']
                else:
                    score = -result['score']
                
                all_sentiments.append(score)
        
        return all_sentiments
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Ottieni utilizzo memoria GPU"""
        if self.device == "cuda" and torch.cuda.is_available():
            return {
                'allocated_gb': torch.cuda.memory_allocated() / 1e9,
                'reserved_gb': torch.cuda.memory_reserved() / 1e9,
                'max_allocated_gb': torch.cuda.max_memory_allocated() / 1e9
            }
        else:
            return {
                'allocated_gb': 0,
                'reserved_gb': 0,
                'max_allocated_gb': 0
            }
    
    def clear_cache(self):
        """Pulisci cache GPU"""
        if self.device == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            logger.info("GPU cache cleared")


class GPUBatchOptimizer(GPUOptimizer):
    """
    Versione ottimizzata per batch processing massivo
    Usa tecniche avanzate per massimizzare throughput
    """
    
    def __init__(self, container: DIContainer):
        super().__init__(container)
        
        # Pre-allocate tensors per performance
        self._preallocated_buffers = {}
        
        # Compile models con torch.compile se disponibile
        if hasattr(torch, 'compile') and self.device == "cuda":
            self._compile_models()
    
    def _compile_models(self):
        """Compila modelli per performance ottimali (PyTorch 2.0+)"""
        try:
            for key, model in self._models.items():
                logger.info(f"Compiling model {key} with torch.compile")
                self._models[key] = torch.compile(model, mode="reduce-overhead")
        except Exception as e:
            logger.warning(f"Model compilation failed: {e}")
    
    async def process_massive_batch(
        self,
        products: List[Dict[str, Any]],
        optimization_level: str = "balanced"
    ) -> List[Dict[str, Any]]:
        """
        Processa batch massivi con ottimizzazioni avanzate
        
        Args:
            products: Lista prodotti (può essere molto grande)
            optimization_level: "speed" | "balanced" | "quality"
            
        Returns:
            Lista prodotti ottimizzati
        """
        # Configura parametri in base al livello
        if optimization_level == "speed":
            # Massima velocità, qualità accettabile
            batch_multiplier = 2
            num_beams = 2
            temperature = 0.7
        elif optimization_level == "quality":
            # Massima qualità, velocità ridotta
            batch_multiplier = 0.5
            num_beams = 8
            temperature = 0.9
        else:  # balanced
            batch_multiplier = 1
            num_beams = 4
            temperature = 0.8
        
        # Estrai dati
        titles = [p.get('title', '') for p in products]
        descriptions = [p.get('description', '') for p in products]
        categories = [p.get('category', 'General') for p in products]
        
        # Process in parallelo
        tasks = [
            self.optimize_titles_batch(titles, categories),
            self.generate_descriptions_batch(titles, descriptions, categories),
            self.extract_keywords_batch([f"{t} {d}" for t, d in zip(titles, descriptions)]),
            self.analyze_sentiment_batch(descriptions)
        ]
        
        results = await asyncio.gather(*tasks)
        
        optimized_titles = results[0]
        optimized_descriptions = results[1]
        keywords_list = results[2]
        sentiments = results[3]
        
        # Combina risultati
        optimized_products = []
        for i, product in enumerate(products):
            optimized = product.copy()
            optimized.update({
                'optimized_title': optimized_titles[i],
                'optimized_description': optimized_descriptions[i],
                'keywords': keywords_list[i],
                'sentiment_score': sentiments[i],
                'optimization_metadata': {
                    'device': self.device,
                    'level': optimization_level,
                    'timestamp': asyncio.get_event_loop().time()
                }
            })
            optimized_products.append(optimized)
        
        # Log stats
        memory_stats = self.get_memory_usage()
        logger.info(
            f"Processed {len(products)} products. "
            f"GPU memory: {memory_stats['allocated_gb']:.2f}GB"
        )
        
        return optimized_products
