"""
Ollama LLM Integration Service.

Handles communication with local Ollama server for AI responses.
"""

import logging
import requests
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = getattr(settings, 'OLLAMA_MODEL', 'llama3')
OLLAMA_TIMEOUT = getattr(settings, 'OLLAMA_TIMEOUT', 120)  # 2 minutes timeout


class OllamaService:
    """
    Service class for interacting with Ollama LLM.
    """
    
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL
        self.timeout = OLLAMA_TIMEOUT
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> Optional[str]:
        """
        Generate a response from Ollama.
        
        Args:
            prompt: The user prompt/message
            system_prompt: Optional system instructions
            temperature: Creativity level (0.0 - 1.0)
            max_tokens: Maximum response length
            
        Returns:
            Generated response text or None if failed
        """
        try:
            # Build the full prompt with system context
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }
            
            url = f"{self.base_url}/api/generate"
            logger.info(f"Sending request to Ollama: {url}")
            
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            generated_text = result.get('response', '')
            
            logger.info(f"Ollama response received, length: {len(generated_text)}")
            return generated_text.strip()
            
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Ollama server. Is it running?")
            return None
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Ollama service: {e}")
            return None
    
    def is_available(self) -> bool:
        """
        Check if Ollama server is available.
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False


# Global service instance
ollama_service = OllamaService()
