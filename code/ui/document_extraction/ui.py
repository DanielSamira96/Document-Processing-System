import streamlit as st
import os
import json
from pathlib import Path
from services.document_intelligence_service import DocumentIntelligenceService
from services.openai_service import OpenAIService
from utils.file_validator import FileValidator
from utils.text_preprocessor import TextPreprocessor
from .translations import DOCUMENT_EXTRACTION_TEXTS


class DocumentExtractorUI:
    """UI component for document data extraction"""
    
    def __init__(self, config, get_common_text_func):
        self.config = config
        self.get_common_text = get_common_text_func
        self.file_validator = FileValidator(self.config)
        self.text_preprocessor = TextPreprocessor()
        
        # Initialize services
        self.ocr_service = None
        self.openai_service = None
        
        if self.config.azure_document_intelligence_endpoint and self.config.azure_document_intelligence_key:
            self.ocr_service = DocumentIntelligenceService(
                self.config.azure_document_intelligence_endpoint,
                self.config.azure_document_intelligence_key
            )
        
        if self.config.azure_openai_endpoint and self.config.azure_openai_key:
            self.openai_service = OpenAIService(
                self.config.azure_openai_endpoint,
                self.config.azure_openai_key,
                self.config.azure_openai_deployment_name,
                self.config.azure_openai_api_version,
                self.config.azure_openai_max_tokens,
                self.config.azure_openai_temperature
            )
    
    def get_text(self, key):
        """Get text for this component, with fallback to common texts"""
        language = st.session_state.get('language', 'en')
        
        # First try component-specific texts
        if key in DOCUMENT_EXTRACTION_TEXTS:
            return DOCUMENT_EXTRACTION_TEXTS[key].get(language, DOCUMENT_EXTRACTION_TEXTS[key].get("en", ""))
        
        # Fallback to common texts
        return self.get_common_text(key)
    
    def render_extraction_interface(self):
        """Render the document extraction interface"""
        # Create two columns layout
        controls_col, preview_col = st.columns([1, 1])
        
        with controls_col:
            st.subheader(self.get_text("file_upload_controls"))
            
            uploaded_file = st.file_uploader(
                self.get_text("upload_label"),
                type=['pdf', 'jpg', 'jpeg', 'png'],
                key="file_uploader",
                accept_multiple_files=False
            )
            
            # Store uploaded file in session state to persist across language changes
            if uploaded_file is not None:
                st.session_state['uploaded_file'] = uploaded_file
            
            # Use file from session state if available
            current_file = st.session_state.get('uploaded_file', uploaded_file)
            
            # Create columns for button and spinner (always visible)
            btn_col, spinner_col = st.columns([0.2, 0.8])
            
            with btn_col:
                process_clicked = st.button(self.get_text("process_button"), type="primary", use_container_width=True)
            
            if process_clicked:
                with spinner_col:
                    self._process_document(current_file)
        
        with preview_col:
            st.subheader(self.get_text("file_preview"))
            
            # Use the same current_file logic for preview
            current_file = st.session_state.get('uploaded_file', uploaded_file)
            
            if current_file is not None:
                self._display_file_preview(current_file)
            else:
                st.info(self.get_text("upload_file_preview"))
    
    def _process_document(self, current_file):
        """Process the uploaded document"""
        if current_file is None:
            st.warning(self.get_common_text("error_file"))
        elif not self.ocr_service:
            st.error(self.get_common_text("error_config"))
        elif not self.openai_service:
            st.error(self.get_common_text("error_openai_config"))
        else:
            try:
                with st.spinner(self.get_text("processing")):
                    temp_file_path = self._save_uploaded_file(current_file)
                    
                    if self.file_validator.validate_file(temp_file_path):
                        # Step 1: OCR Processing
                        ocr_result = self.ocr_service.analyze_document(temp_file_path)
                        ocr_text_result = self.ocr_service.convert_result_to_text(ocr_result)
                        
                        # Save OCR output - optional for debugging
                        # ocr_output_filename = f"{Path(current_file.name).stem}_ocr_output.txt"
                        # ocr_output_path = os.path.join("outputs", ocr_output_filename)
                        # os.makedirs("outputs", exist_ok=True)
                        # self.ocr_service.save_ocr_output(ocr_text_result, ocr_output_path)
                
                # Step 2: Text Preprocessing
                preprocessed_text = self.text_preprocessor.preprocess_text(ocr_text_result)
                
                # Step 3: LLM Field Extraction
                with st.spinner(self.get_text("llm_processing")):
                    detected_language = self.openai_service.detect_language(preprocessed_text)
                    extracted_data = self.openai_service.extract_fields(preprocessed_text, detected_language)
                    
                    if extracted_data:
                        # Store in session state for validation
                        st.session_state['extracted_data'] = extracted_data
                        st.session_state['detected_language'] = detected_language
                        
                        # Save extracted JSON - optional for debugging
                        # json_output_filename = f"{Path(current_file.name).stem}_extracted.json"
                        # json_output_path = os.path.join("outputs", json_output_filename)
                        # self.openai_service.save_extracted_data(extracted_data, json_output_path)
                        
                        st.success(self.get_text("llm_success"))
                        st.info(f"{self.get_text('language_detected')}: {self.get_common_text(detected_language)}")
                        
                    else:
                        st.error("Failed to extract fields from document")
                    
                    os.unlink(temp_file_path)
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    def _display_file_preview(self, uploaded_file):
        """Display preview of uploaded file (PDF or image)"""
        file_type = uploaded_file.type
        
        if file_type == "application/pdf":
            self._display_pdf_preview(uploaded_file)
        elif file_type in ["image/jpeg", "image/jpg", "image/png"]:
            self._display_image_preview(uploaded_file)
        else:
            st.warning("Preview not available for this file type")
    
    def _display_pdf_preview(self, uploaded_file):
        """Display PDF preview using base64 embedding"""
        try:
            import base64
            
            # Read PDF bytes
            pdf_bytes = uploaded_file.getvalue()
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            
            # Display PDF in embedded viewer
            pdf_display = f"""
            <iframe
                src="data:application/pdf;base64,{base64_pdf}"
                width="100%"
                height="500"
                type="application/pdf"
                style="border: 1px solid #e1e5e9; border-radius: 0.5rem;">
            </iframe>
            """
            
            st.markdown(pdf_display, unsafe_allow_html=True)
            
            # Show file info
            st.caption(f"📄 {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            
        except Exception as e:
            st.error(f"{self.get_text('error_displaying_pdf')}: {str(e)}")
            st.info(self.get_text("pdf_preview_not_available"))
    
    def _display_image_preview(self, uploaded_file):
        """Display image preview"""
        try:
            # Display image
            st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
            
            # Show file info
            st.caption(f"🖼️ {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            
        except Exception as e:
            st.error(f"{self.get_text('error_displaying_image')}: {str(e)}")
            st.info(self.get_text("image_preview_not_available"))
    
    def _save_uploaded_file(self, uploaded_file):
        """Save uploaded file to temporary location"""
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, uploaded_file.name)
        
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return temp_file_path

    def render_results_display(self):
        """Render extracted results display"""
        if 'extracted_data' in st.session_state and st.session_state.extracted_data:
            # Display JSON result section
            with st.expander(self.get_text("extracted_fields_json"), expanded=True):
                st.json(st.session_state.extracted_data)
            
            # Download button for JSON
            json_str = json.dumps(st.session_state.extracted_data, ensure_ascii=False, indent=2)
            st.download_button(
                label=self.get_text("download_json"),
                data=json_str,
                file_name="extracted_results.json",
                mime="application/json",
                key="persistent_download_json"
            )
            
            return True  # Indicate that results are available
        return False