import streamlit as st
import os
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from services.document_intelligence_service import DocumentIntelligenceService
from services.openai_service import OpenAIService
from utils.file_validator import FileValidator
from utils.config import Config
from utils.text_preprocessor import TextPreprocessor
from ui.translations import UI_TEXTS

class DocumentProcessorUI:
    def __init__(self):
        self.config = Config()
        self.file_validator = FileValidator(self.config)
        self.text_preprocessor = TextPreprocessor()
        self.language = self.config.default_language
        
        if self.config.azure_document_intelligence_endpoint and self.config.azure_document_intelligence_key:
            self.ocr_service = DocumentIntelligenceService(
                self.config.azure_document_intelligence_endpoint,
                self.config.azure_document_intelligence_key
            )
        else:
            self.ocr_service = None
        
        if self.config.azure_openai_endpoint and self.config.azure_openai_key:
            self.openai_service = OpenAIService(
                self.config.azure_openai_endpoint,
                self.config.azure_openai_key,
                self.config.azure_openai_deployment_name,
                self.config.azure_openai_api_version,
                self.config.azure_openai_max_tokens,
                self.config.azure_openai_temperature
            )
        else:
            self.openai_service = None
    
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
        return UI_TEXTS.get(key, {}).get(self.language, UI_TEXTS.get(key, {}).get("en", ""))
    
    def render_main_interface(self):
        if self.language == "he":
            st.markdown("""
            <style>
            .main-header {
                direction: rtl;
                text-align: right;
            }
            .stSelectbox > label {
                direction: rtl;
                text-align: right;
            }
            </style>
            """, unsafe_allow_html=True)
        
        st.title(self.get_text("title"))
        st.subheader(self.get_text("subtitle"))
        
        uploaded_file = st.file_uploader(
            self.get_text("upload_label"),
            type=['pdf', 'jpg', 'jpeg', 'png'],
            key="file_uploader",
            accept_multiple_files=False
        )
        
        if uploaded_file is not None:
            st.success(f"📁 {uploaded_file.name}")
            
            if st.button(self.get_text("process_button"), type="primary"):
                if not self.ocr_service:
                    st.error(self.get_text("error_config"))
                    return
                
                if not self.openai_service:
                    st.error(self.get_text("error_openai_config"))
                    return
                
                try:
                    with st.spinner(self.get_text("processing")):
                        temp_file_path = self._save_uploaded_file(uploaded_file)
                        
                        if self.file_validator.validate_file(temp_file_path):
                            # Step 1: OCR Processing
                            ocr_result = self.ocr_service.analyze_document(temp_file_path)
                            ocr_text_result = self.ocr_service.convert_result_to_text(ocr_result)
                            
                            # Save OCR output
                            ocr_output_filename = f"{Path(uploaded_file.name).stem}_ocr_output.txt"
                            ocr_output_path = os.path.join("outputs", ocr_output_filename)
                            os.makedirs("outputs", exist_ok=True)
                            self.ocr_service.save_ocr_output(ocr_text_result, ocr_output_path)
                    
                    # Step 2: Text Preprocessing
                    preprocessed_text = self.text_preprocessor.preprocess_text(ocr_text_result)
                    
                    # Step 3: LLM Field Extraction
                    with st.spinner(self.get_text("llm_processing")):
                        detected_language = self.openai_service.detect_language(preprocessed_text)
                        extracted_data = self.openai_service.extract_fields(preprocessed_text, detected_language)
                        
                        if extracted_data:
                            # Save extracted JSON
                            json_output_filename = f"{Path(uploaded_file.name).stem}_extracted.json"
                            json_output_path = os.path.join("outputs", json_output_filename)
                            self.openai_service.save_extracted_data(extracted_data, json_output_path)
                            
                            st.success(self.get_text("llm_success"))
                            st.info(f"{self.get_text('language_detected')}: {detected_language.upper()}")
                            
                            # Display JSON result
                            with st.expander("Extracted Fields (JSON)", expanded=True):
                                st.json(extracted_data)
                            
                            # Download button for JSON
                            json_str = json.dumps(extracted_data, ensure_ascii=False, indent=2)
                            st.download_button(
                                label=self.get_text("download_json"),
                                data=json_str,
                                file_name=json_output_filename,
                                mime="application/json",
                                type="secondary"
                            )
                        else:
                            st.error("Failed to extract fields from document")
                        
                        os.unlink(temp_file_path)
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            if st.button(self.get_text("process_button"), type="primary"):
                st.warning(self.get_text("error_file"))
    
    def _save_uploaded_file(self, uploaded_file):
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, uploaded_file.name)
        
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return temp_file_path
    
    def run(self):
        self.setup_page_config()
        self.render_language_selector()
        self.render_main_interface()

if __name__ == "__main__":
    app = DocumentProcessorUI()
    app.run()