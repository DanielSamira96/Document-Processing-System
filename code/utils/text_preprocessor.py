import re
import logging

logger = logging.getLogger(__name__)

class TextPreprocessor:
    def __init__(self):
        # Define OCR correction rules
        self.correction_rules = [
            # Hebrew specific corrections
            (r'חתימהX', 'חתימה'),
            (r'Xחתימה', 'חתימה'),
            (r'חתימהx', 'חתימה'),
            (r'xחתימה', 'חתימה'),
            # Add more rules as needed

        ]
    
    def preprocess_text(self, text: str) -> str:
        """
        Apply preprocessing rules to clean OCR text before sending to LLM
        """
        try:
            processed_text = text
            
            # Apply all correction rules
            for pattern, replacement in self.correction_rules:
                processed_text = re.sub(pattern, replacement, processed_text)
            
            logger.info(f"Applied {len(self.correction_rules)} preprocessing rules")
            return processed_text
            
        except Exception as e:
            logger.error(f"Error in text preprocessing: {str(e)}")
            return text  # Return original text if preprocessing fails