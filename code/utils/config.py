import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        
        self.azure_document_intelligence_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.azure_document_intelligence_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
        self.azure_openai_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        self.azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        
        # All implemented languages with their display names
        self.implemented_languages = {
            "en": "English",
            "he": "עברית"
        }
        
        # Validate and set default language
        default_lang = os.getenv("DEFAULT_LANGUAGE", "en")
        self.default_language = default_lang if default_lang in self.implemented_languages else "en"
        
        self.supported_languages = os.getenv("SUPPORTED_LANGUAGES", "en,he").split(",")
        self.max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "200"))
        self.max_file_size = self.max_file_size_mb * 1024 * 1024  # Convert MB to bytes
    
    def get_available_languages(self):
        """Returns only the languages that are both implemented and enabled"""
        return {lang: self.implemented_languages[lang] 
                for lang in self.supported_languages 
                if lang in self.implemented_languages}
    
    def is_azure_document_intelligence_configured(self):
        return bool(self.azure_document_intelligence_endpoint and self.azure_document_intelligence_key)
    
    def is_azure_openai_configured(self):
        return bool(self.azure_openai_endpoint and self.azure_openai_key)