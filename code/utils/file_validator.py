import os
import mimetypes
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FileValidator:
    ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'image/jpeg',
        'image/jpg', 
        'image/png'
    }
    
    def __init__(self, config):
        self.max_file_size = config.max_file_size
    
    def validate_file(self, file_path: str) -> bool:
        try:
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return False
            
            if not self._validate_extension(file_path):
                logger.error(f"Invalid file extension: {file_path}")
                return False
            
            if not self._validate_size(file_path):
                logger.error(f"File too large: {file_path}")
                return False
            
            if not self._validate_mime_type(file_path):
                logger.error(f"Invalid MIME type: {file_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {str(e)}")
            return False
    
    def _validate_extension(self, file_path: str) -> bool:
        extension = Path(file_path).suffix.lower()
        return extension in self.ALLOWED_EXTENSIONS
    
    def _validate_size(self, file_path: str) -> bool:
        file_size = os.path.getsize(file_path)
        return file_size <= self.max_file_size
    
    def _validate_mime_type(self, file_path: str) -> bool:
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type in self.ALLOWED_MIME_TYPES
    
    def get_validation_error_message(self, file_path: str, language: str = "en") -> str:
        messages = {
            "en": {
                "not_exists": "File does not exist.",
                "invalid_extension": f"Invalid file format. Allowed formats: {', '.join(self.ALLOWED_EXTENSIONS)}",
                "too_large": f"File too large. Maximum size: {self.max_file_size // (1024*1024)}MB",
                "invalid_mime": "Invalid file type."
            },
            "he": {
                "not_exists": "הקובץ לא קיים.",
                "invalid_extension": f"פורמט קובץ לא תקין. פורמטים מותרים: {', '.join(self.ALLOWED_EXTENSIONS)}",
                "too_large": f"הקובץ גדול מדי. גודל מקסימלי: {self.max_file_size // (1024*1024)}MB",
                "invalid_mime": "סוג קובץ לא תקין."
            }
        }
        
        if not os.path.exists(file_path):
            return messages[language]["not_exists"]
        
        if not self._validate_extension(file_path):
            return messages[language]["invalid_extension"]
        
        if not self._validate_size(file_path):
            return messages[language]["too_large"]
        
        if not self._validate_mime_type(file_path):
            return messages[language]["invalid_mime"]
        
        return ""