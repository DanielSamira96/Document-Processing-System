import json
import logging
import re
from typing import Optional, Dict, Any
from openai import AzureOpenAI
from prompts.field_extraction_prompt import get_system_prompt

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self, endpoint: str, key: str, deployment_name: str, api_version: str, max_tokens: int = 2000, temperature: float = 0.1):
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version=api_version
        )
        self.deployment_name = deployment_name
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    def detect_language(self, ocr_text: str) -> str:
        """Detect if the document is filled in Hebrew or English based on meaningful content"""
        try:
            # Words to ignore (system-generated from our OCR processing)
            ignore_words = {'Key', 'Value', 'Pairs', 'unselected', 'selected', 'Raw', 'Lines'}
            
            # Look for meaningful English words (not just single letters or whitespace)
            english_words = re.findall(r'\b[a-zA-Z]{2,}\b', ocr_text)
            # Filter out ignored words (case-insensitive)
            meaningful_words = [word for word in english_words if word not in ignore_words and len(word) >= 2]
            meaningful_english = len(meaningful_words)
            
            # Look for Hebrew characters in meaningful context
            hebrew_chars = len(re.findall(r'[\u0590-\u05FF]', ocr_text))
            
            # If we find meaningful English words, it's likely an English-filled form
            if meaningful_english > 0:
                return "en"
            # If no meaningful English but Hebrew characters exist, it's Hebrew-filled
            elif hebrew_chars > 0:
                return "he"
            else:
                # Default to English if unclear
                return "en"
                
        except Exception as e:
            logger.warning(f"Error detecting language: {str(e)}, defaulting to English")
            return "en"
    
    def extract_fields(self, ocr_text: str, language: str = None) -> Optional[Dict[str, Any]]:
        """Extract form fields from OCR text using Azure OpenAI"""
        try:
            # Auto-detect language if not provided
            if language is None:
                language = self.detect_language(ocr_text)
            
            logger.info(f"Processing document in language: {language}")
            
            # Get the appropriate system prompt with schema
            system_prompt = get_system_prompt(language)
            
            # Create user prompt with OCR content
            user_prompt = f"Extract the form fields from this OCR content:\n\n{ocr_text}"
            
            # Call Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            result_text = response.choices[0].message.content
            
            # Parse the JSON response
            try:
                result_json = json.loads(result_text)
                logger.info("Successfully extracted fields from document")
                return result_json
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from OpenAI response: {str(e)}")
                logger.error(f"Raw response: {result_text}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting fields: {str(e)}")
            raise e
    
    def save_extracted_data(self, extracted_data: Dict[str, Any], output_path: str) -> None:
        """Save extracted JSON data to file"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Extracted data saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving extracted data: {str(e)}")
            raise e