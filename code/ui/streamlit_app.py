import streamlit as st
import os
import sys
import json
import re
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from services.document_intelligence_service import DocumentIntelligenceService
from services.openai_service import OpenAIService
from services.validation_service import ValidationService
from utils.message_types import MessageType
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
            self.validation_service = ValidationService(self.openai_service)
        else:
            self.openai_service = None
            self.validation_service = None
    
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
                            # Store in session state for validation
                            st.session_state['extracted_data'] = extracted_data
                            st.session_state['detected_language'] = detected_language
                            
                            # Save extracted JSON
                            json_output_filename = f"{Path(uploaded_file.name).stem}_extracted.json"
                            json_output_path = os.path.join("outputs", json_output_filename)
                            self.openai_service.save_extracted_data(extracted_data, json_output_path)
                            
                            st.success(self.get_text("llm_success"))
                            st.info(f"{self.get_text('language_detected')}: {detected_language.upper()}")
                            
                            # JSON will be displayed persistently in the run() method
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
    
    def render_validation_interface(self):
        """Render the validation and evaluation section"""
        st.divider()
        st.header(self.get_text("validation_title"))
        
        st.info("""
        **How to validate:** Upload your ground truth JSON file and start validation to compare system output with expected results. 
        You can download empty templates if needed to create the correct JSON structure.
        """)
        
        # Reorganized validation buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # st.write("**Upload Ground Truth:**")
            # Upload ground truth
            expected_file = st.file_uploader(
                self.get_text("upload_ground_truth"),
                type=['json'],
                key="expected_results"
            )
            
        with col2:
            st.write(self.get_text("templates_validator"))
            # Download templates side by side - very close together
            subcol1, subcol2, _ = st.columns([0.4, 0.4, 0.2])
            with subcol1:
                # Download empty English template
                with open("templates/empty_json_en.json", "r", encoding="utf-8") as f:
                    en_template = f.read()
                st.download_button(
                    label=self.get_text("download_empty_en"),
                    data=en_template,
                    file_name="empty_template_english.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with subcol2:
                # Download empty Hebrew template
                with open("templates/empty_json_he.json", "r", encoding="utf-8") as f:
                    he_template = f.read()
                st.download_button(
                    label=self.get_text("download_empty_he"),
                    data=he_template,
                    file_name="empty_template_hebrew.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            # Validation button and spinner side by side
            btn_col, spinner_col = st.columns([0.2, 0.8])
            with btn_col:
                if st.button(self.get_text("start_validation"), type="primary", use_container_width=True):
                    with spinner_col:
                        self._perform_validation(expected_file)
    
    def _perform_validation(self, expected_file):
        """Perform the validation process"""
        if not expected_file:
            st.warning(self.get_text("upload_expected_first"))
            return
        
        if not self.validation_service:
            st.error(self.get_text("error_openai_config"))
            return
        
        if 'extracted_data' not in st.session_state:
            st.warning("No extracted data found. Please process a document first.")
            return
        
        try:
            with st.spinner(self.get_text("validation_processing")):
                # Get extraction language from session state
                extraction_language = st.session_state.get('detected_language', 'en')
                
                # Validate uploaded JSON
                expected_content = expected_file.read().decode('utf-8')
                expected_data, message, message_type = self.validation_service.validate_json_file(
                    expected_content,
                    self.get_text,
                    extraction_language
                )
                
                if expected_data is None:
                    st.error(f"{self.get_text('invalid_json_file')}: {message}")
                    return
                
                # Show warning if languages don't match
                if message_type == MessageType.WARNING:
                    st.warning(message)
                
                # Calculate metrics
                extracted_data = st.session_state['extracted_data']
                metrics = self.validation_service.calculate_metrics(expected_data, extracted_data)
                
                # Get LLM evaluation with user's language
                llm_evaluation = self.validation_service.get_llm_evaluation(expected_data, extracted_data, metrics, self.language)
                
                st.success(self.get_text("validation_complete"))
                
                # Store results in session state for display outside column constraint
                st.session_state['validation_metrics'] = metrics
                st.session_state['validation_evaluation'] = llm_evaluation
                
        except Exception as e:
            st.error(f"Validation error: {str(e)}")
    
    def _display_validation_results(self, metrics, llm_evaluation):
        """Display validation results and metrics"""
        st.subheader("📊 Validation Results")
        
        # Full width layout for results and AI analysis
        results_col, analysis_col = st.columns([1, 1])
        
        with results_col:
            st.subheader("📈 Metrics & Scores")
            
            # Overall score from LLM
            overall_score = llm_evaluation.get("overall_score", {})
            text_rating = overall_score.get("text_rating", "N/A")
            # Capitalize first letter
            if text_rating != "N/A":
                text_rating = text_rating.capitalize()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("LLM Overall Rating", text_rating)
            with col2:
                st.metric("LLM Numeric Score", f"{overall_score.get('numeric_score', 0)}%")
            
            # Detailed metrics
            st.metric(
                self.get_text("overall_accuracy"),
                f"{metrics.overall_accuracy:.1f}%",
                help="Percentage of exactly matching fields"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    self.get_text("language_consistency"),
                    "✅" if metrics.language_consistency else "❌",
                    help="Whether output language matches expected language"
                )
                st.metric(
                    self.get_text("dates_accuracy"),
                    f"{metrics.dates_accuracy:.1f}%",
                    help="Accuracy in recognizing date fields"
                )
                st.metric(
                    self.get_text("checkboxes_accuracy"),
                    f"{metrics.checkbox_accuracy:.1f}%",
                    help="Accuracy in identifying selected checkboxes"
                )
                
            with col2:
                st.metric(
                    self.get_text("phones_accuracy"),
                    f"{metrics.phone_accuracy:.1f}%",
                    help="Accuracy in extracting phone numbers"
                )
                st.metric(
                    self.get_text("empty_fields"),
                    f"{metrics.empty_fields_accuracy:.1f}%",
                    help="Accuracy in recognizing empty fields"
                )
                st.metric(
                    self.get_text("structure_compliance"),
                    f"{metrics.structure_compliance:.1f}%",
                    help="Compliance with expected JSON structure"
                )
        
        with analysis_col:
            # LLM Analysis
            st.subheader("🤖 AI Analysis")
            if "category_analysis" in llm_evaluation:
                analysis = llm_evaluation["category_analysis"]
                
                for category, feedback in analysis.items():
                    st.write(f"**{category.replace('_', ' ').title()}:** {feedback}")
            
            # Summary and recommendations
            if "summary" in llm_evaluation:
                st.write(f"**📝 Summary:** {llm_evaluation['summary']}")
            
            if "improvement_focus" in llm_evaluation:
                st.write("**🎯 Improvement Focus:**")
                # Split improvement points by numbered items
                improvement_text = llm_evaluation["improvement_focus"]
                
                # Handle case where improvement_focus might not be a string
                if isinstance(improvement_text, str):
                    # Split by numbers (1., 2., 3., etc.)
                    points = re.split(r'\d+\.', improvement_text)
                    points = [point.strip() for point in points if point.strip()]
                    
                    for i, point in enumerate(points, 1):
                        st.write(f"{i}. {point}")
                else:
                    # If it's not a string, just display as is
                    st.write(str(improvement_text))
            
            if "critical_mistakes" in llm_evaluation:
                st.write(f"**⚠️ Critical Issues:** {llm_evaluation['critical_mistakes']}")
            
            if "system_strengths" in llm_evaluation:
                st.write(f"**✅ System Strengths:** {llm_evaluation['system_strengths']}")
    
    def run(self):
        self.setup_page_config()
        self.render_language_selector()
        self.render_main_interface()
        
        # Always show extracted JSON if we have data in session state
        if 'extracted_data' in st.session_state and st.session_state.extracted_data:
            # Display JSON result section
            with st.expander("Extracted Fields (JSON)", expanded=True):
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
            
            # Show validation interface
            self.render_validation_interface()
            
            # Display validation results outside column constraint (full width)
            if 'validation_metrics' in st.session_state and 'validation_evaluation' in st.session_state:
                st.divider()
                self._display_validation_results(
                    st.session_state['validation_metrics'], 
                    st.session_state['validation_evaluation']
                )

if __name__ == "__main__":
    app = DocumentProcessorUI()
    app.run()