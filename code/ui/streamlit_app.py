import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from services.validation_service import ValidationService
from services.openai_service import OpenAIService
from utils.config import Config
from ui.common import COMMON_TEXTS
from ui.document_extraction import DocumentExtractorUI
from ui.validation import ValidationUI

class DocumentProcessorUI:
    def __init__(self):
        self.config = Config()
        self.language = self.config.default_language
        
        # Initialize OpenAI service for validation
        if self.config.azure_openai_endpoint and self.config.azure_openai_key:
            self.openai_service = OpenAIService(
                self.config.azure_openai_endpoint,
                self.config.azure_openai_key,
                self.config.azure_openai_deployment_name,
                self.config.azure_openai_api_version,
                self.config.azure_openai_max_tokens,
                self.config.azure_openai_temperature
            )
            self.validation_service = ValidationService(self.openai_service)
        else:
            self.openai_service = None
            self.validation_service = None
        
        # Initialize UI components
        self.document_extractor = DocumentExtractorUI(self.config, self.get_text)
        self.validation_ui = ValidationUI(self.validation_service, self.get_text)
    
    def setup_page_config(self):
        st.set_page_config(
            page_title="Document Processing System",
            page_icon="📄",
            layout="wide",
            initial_sidebar_state="expanded"
        )

    def render_language_selector(self):
        available_languages = self.config.get_available_languages()

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            lang_keys = list(available_languages.keys())
            default_index = lang_keys.index(self.config.default_language) if self.config.default_language in lang_keys else 0
            
            selected_lang = st.selectbox(
                "Language / שפה",
                options=lang_keys,
                format_func=lambda x: available_languages[x],
                index=default_index,
                key="language_selector"
            )

        if "language" not in st.session_state:
            st.session_state.language = self.config.default_language

        if selected_lang != st.session_state.language:
            st.session_state.language = selected_lang
            st.rerun()

        self.language = st.session_state.language
    
    def get_text(self, key):
        """Get text from common translations"""
        return COMMON_TEXTS.get(key, {}).get(self.language, COMMON_TEXTS.get(key, {}).get("en", ""))
    
    
    def load_css(self):
        """Load CSS from external file"""
        if self.language == "he":
            try:
                css_path = Path(__file__).parent / "styles.css"
                with open(css_path, "r", encoding="utf-8") as f:
                    css_content = f.read()
                st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
            except Exception as e:
                # Fallback to no styling if CSS file is not found
                st.error(f"Could not load CSS file: {str(e)}")

    def render_main_interface(self):
        self.load_css()
        
        st.title(self.get_text("title"))
        st.subheader(self.get_text("subtitle"))
        
        # Use the document extractor component
        self.document_extractor.render_extraction_interface()
    
    
    def run(self):
        self.setup_page_config()
        self.render_language_selector()
        self.render_main_interface()
        
        # Display extracted results if available
        if self.document_extractor.render_results_display():
            # Show validation interface if we have extracted data
            self.validation_ui.render_validation_interface()
            
            # Display validation results if available
            self.validation_ui.render_validation_results()

if __name__ == "__main__":
    app = DocumentProcessorUI()
    app.run()