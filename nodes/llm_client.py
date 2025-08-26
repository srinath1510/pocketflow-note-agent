#!/usr/bin/env python3
"""
LLM Client Wrapper: Provider-agnostic interface for different LLM services
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a chat completion response"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured"""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider"""
    
    def __init__(self):
        self.client = None
        self.logger = logging.getLogger(__name__)
        self._initialize()
    
    def _initialize(self):
        try:
            import anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.logger.info("Anthropic provider initialized")
            else:
                self.logger.warning("ANTHROPIC_API_KEY not found")
        except ImportError:
            self.logger.warning("Anthropic library not installed")
        except Exception as e:
            self.logger.error(f"Anthropic initialization failed: {str(e)}")
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")
        
        model = kwargs.get('model', 'claude-3-5-haiku-latest')
        max_tokens = kwargs.get('max_tokens', 1000)
        
        # Convert messages to Anthropic format
        system_message = ""
        user_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_message = msg['content']
            else:
                user_messages.append(msg)
        
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_message if system_message else "You are a helpful assistant.",
            messages=user_messages
        )
        
        return response.content[0].text
    
    def is_available(self) -> bool:
        return self.client is not None


class LLMClient:
    """
    Universal LLM client that automatically selects the best available provider
    """
    
    def __init__(self, preferred_provider: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.provider = None
        self.provider_name = None
        
        # Initialize providers (currently only added Anthropic)
        providers = {
            'anthropic': AnthropicProvider()
        }
        
        # user specified preferred LLM provider
        if preferred_provider and preferred_provider in providers:
            provider = providers[preferred_provider]
            if provider.is_available():
                self.provider = provider
                self.provider_name = preferred_provider
                self.logger.info(f"Using preferred LLM provider: {preferred_provider}")
                return
        
        # Otherwise, order of preference
        for name, provider in providers.items():
            if provider.is_available():
                self.provider = provider
                self.provider_name = name
                self.logger.info(f"Using LLM provider: {name}")
                return
        
        self.logger.error("No LLM providers available")
        raise RuntimeError("No LLM providers configured. Please set up at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, or run Ollama locally")
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a chat completion using the active provider"""
        if not self.provider:
            raise RuntimeError("No LLM provider available")
        
        try:
            return self.provider.chat_completion(messages, **kwargs)
        except Exception as e:
            self.logger.error(f"LLM request failed with {self.provider_name}: {str(e)}")
            raise
    
    def is_available(self) -> bool:
        """Check if any provider is available"""
        return self.provider is not None
    
    def get_provider_name(self) -> str:
        """Get the name of the active provider"""
        return self.provider_name or "none"
    
    def get_model_recommendations(self) -> Dict[str, str]:
        """Get recommended models for each provider"""
        recommendations = {
            'anthropic': 'claude-3-5-haiku-latest', 
        }
        return recommendations
    
    def set_provider_specific_defaults(self, **kwargs) -> Dict[str, Any]:
        """Set provider-specific defaults for requests"""
        defaults = kwargs.copy()

        if self.provider_name == 'anthropic':
            defaults.setdefault('model', 'claude-3-5-haiku-latest')
            defaults.setdefault('temperature', 0.3)
        
        return defaults

def get_llm_client(preferred_provider: Optional[str] = None) -> LLMClient:
    """
    Factory function to get an LLM client
    
    Args:
        preferred_provider: Preferred provider ('anthropic')
    
    Returns:
        Configured LLM client
    """
    # Allow configuration via environment variable
    if not preferred_provider:
        preferred_provider = os.getenv('LLM_PROVIDER')
    
    return LLMClient(preferred_provider)
