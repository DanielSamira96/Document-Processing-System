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
    
    def get_columns_rtl(self, sizes):
        """Helper method to handle RTL column creation with reversed sizes
        sizes: list of sizes for st.columns()
        Returns: list of column objects in correct order for RTL/LTR
        """
        if self.language == "he":
            # For RTL: reverse the sizes and create columns
            reversed_sizes = list(reversed(sizes))
            cols = st.columns(reversed_sizes)
            # Return columns in reverse order so assignment works correctly
            return list(reversed(cols))
        else:
            # For LTR: normal order
            return list(st.columns(sizes))
    
    def render_main_interface(self):
        if self.language == "he":
            st.markdown("""
            <style>
            /* Main container RTL */
            .main .block-container {
                direction: rtl;
                text-align: right;
            }
            
            /* Selectbox and form elements */
            .stSelectbox > label, .stFileUploader > label {
                direction: rtl;
                text-align: right;
            }
            
            /* More specific selectors for titles and headers */
            .main h1, .main h2, .main h3, .main h4, .main h5, .main h6,
            [data-testid="stTitle"], 
            [data-testid="stSubheader"], 
            [data-testid="stHeader"],
            .stTitle, .stSubheader, .stHeader,
            div[data-testid="metric-container"] .metric-container,
            .element-container h1, .element-container h2, .element-container h3 {
                direction: rtl !important;
                text-align: right !important;
            }
            
            /* Buttons */
            .stButton > button {
                direction: rtl;
                text-align: center;
            }
            
            /* Spinner text */
            .stSpinner > div {
                direction: rtl;
                text-align: right;
            }
            
            /* Captions and help text */
            .caption, .help {
                direction: rtl;
                text-align: right;
            }
            
            /* Columns container */
            .row-widget {
                direction: rtl;
            }
            
            /* st.write content - more comprehensive selectors */
            .stWrite, [data-testid="stWrite"],
            .stMarkdown, [data-testid="stMarkdown"],
            [data-testid="stMarkdownContainer"],
            .element-container .stMarkdown,
            div[data-testid="element-container"] .stMarkdown {
                direction: rtl !important;
                text-align: right !important;
            }
            
            /* Success, error, warning, info messages */
            .stAlert {
                direction: rtl;
                text-align: right;
            }
            
            /* Metrics */
            .metric-container {
                direction: rtl;
                text-align: right;
            }
            
            /* Expander */
            .streamlit-expanderHeader {
                direction: rtl;
                text-align: right;
            }
            
            /* Download button */
            .stDownloadButton > button {
                direction: rtl;
                text-align: center;
            }
            
            /* JSON display */
            .stJson {
                direction: ltr; /* Keep JSON in LTR for readability */
                text-align: left;
            }
            
            </style>
            """, unsafe_allow_html=True)
        
        st.title(self.get_text("title"))
        st.subheader(self.get_text("subtitle"))
        
        # Create two columns layout - reverse order for RTL languages
        controls_col, preview_col = self.get_columns_rtl([1, 1])
        
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
            btn_col, spinner_col = self.get_columns_rtl([0.2, 0.8])
            
            with btn_col:
                process_clicked = st.button(self.get_text("process_button"), type="primary")
            
            if process_clicked:
                with spinner_col:
                    if current_file is None:
                        st.warning(self.get_text("error_file"))
                    elif not self.ocr_service:
                        st.error(self.get_text("error_config"))
                    elif not self.openai_service:
                        st.error(self.get_text("error_openai_config"))
                    else:
                        try:
                            with st.spinner(self.get_text("processing")):
                                temp_file_path = self._save_uploaded_file(current_file)
                                
                                if self.file_validator.validate_file(temp_file_path):
                                    # Step 1: OCR Processing
                                    ocr_result = self.ocr_service.analyze_document(temp_file_path)
                                    ocr_text_result = self.ocr_service.convert_result_to_text(ocr_result)
                                    
                                    # Save OCR output
                                    ocr_output_filename = f"{Path(current_file.name).stem}_ocr_output.txt"
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
                                    json_output_filename = f"{Path(current_file.name).stem}_extracted.json"
                                    json_output_path = os.path.join("outputs", json_output_filename)
                                    self.openai_service.save_extracted_data(extracted_data, json_output_path)
                                    
                                    st.success(self.get_text("llm_success"))
                                    st.info(f"{self.get_text('language_detected')}: {self.get_text(detected_language)}")
                                    
                                    # JSON will be displayed persistently in the run() method
                                else:
                                    st.error("Failed to extract fields from document")
                                
                                os.unlink(temp_file_path)
                            
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        
        with preview_col:
            st.subheader(self.get_text("file_preview"))
            
            # Use the same current_file logic for preview
            current_file = st.session_state.get('uploaded_file', uploaded_file)
            
            if current_file is not None:
                self._display_file_preview(current_file)
            else:
                st.info(self.get_text("upload_file_preview"))
    
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
            st.error(f"Error displaying PDF preview: {str(e)}")
            st.info("PDF preview not available, but file can still be processed.")
    
    def _display_image_preview(self, uploaded_file):
        """Display image preview"""
        try:
            # Display image
            st.image(uploaded_file, caption=uploaded_file.name, use_column_width=True)
            
            # Show file info
            st.caption(f"🖼️ {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            
        except Exception as e:
            st.error(f"Error displaying image preview: {str(e)}")
            st.info("Image preview not available, but file can still be processed.")
    
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
        
        st.info(self.get_text("validation_instructions"))
        
        # Reorganized validation buttons
        col1, col2 = self.get_columns_rtl([1, 1])
        
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
            subcol1, subcol2, _ = self.get_columns_rtl([0.4, 0.4, 0.2])
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
            btn_col, spinner_col = self.get_columns_rtl([0.2, 0.8])
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
        st.subheader(self.get_text("validation_results"))
        
        # Full width layout for results and AI analysis
        results_col, analysis_col = self.get_columns_rtl([1, 1])
        
        with results_col:
            st.subheader(self.get_text("metrics_scores"))
            
            # Overall score from LLM
            overall_score = llm_evaluation.get("overall_score", {})
            text_rating = overall_score.get("text_rating", "N/A")
            # Capitalize first letter
            if text_rating != "N/A":
                text_rating = text_rating.capitalize()
            
            col1, col2 = self.get_columns_rtl([1, 1])
            with col1:
                st.metric(self.get_text("llm_overall_rating"), text_rating)
            with col2:
                st.metric(self.get_text("llm_numeric_score"), f"{overall_score.get('numeric_score', 0)}%")
            
            # Detailed metrics
            st.metric(
                self.get_text("overall_accuracy"),
                f"{metrics.overall_accuracy:.1f}%",
                help=self.get_text("help_overall_accuracy")
            )
            
            col1, col2 = self.get_columns_rtl([1, 1])
            with col1:
                st.metric(
                    self.get_text("language_consistency"),
                    "✅" if metrics.language_consistency else "❌",
                    help=self.get_text("help_language_consistency")
                )
                st.metric(
                    self.get_text("dates_accuracy"),
                    f"{metrics.dates_accuracy:.1f}%",
                    help=self.get_text("help_dates_accuracy")
                )
                st.metric(
                    self.get_text("checkboxes_accuracy"),
                    f"{metrics.checkbox_accuracy:.1f}%",
                    help=self.get_text("help_checkboxes_accuracy")
                )
                
            with col2:
                st.metric(
                    self.get_text("phones_accuracy"),
                    f"{metrics.phone_accuracy:.1f}%",
                    help=self.get_text("help_phones_accuracy")
                )
                st.metric(
                    self.get_text("empty_fields"),
                    f"{metrics.empty_fields_accuracy:.1f}%",
                    help=self.get_text("help_empty_fields")
                )
                st.metric(
                    self.get_text("structure_compliance"),
                    f"{metrics.structure_compliance:.1f}%",
                    help=self.get_text("help_structure_compliance")
                )
        
        with analysis_col:
            # LLM Analysis
            st.subheader(self.get_text("ai_analysis_title"))
            if "category_analysis" in llm_evaluation:
                analysis = llm_evaluation["category_analysis"]
                
                for category, feedback in analysis.items():
                    st.write(f"**{category.replace('_', ' ').title()}:** {feedback}")
            
            # Summary and recommendations
            if "summary" in llm_evaluation:
                st.write(f"**{self.get_text('summary_label')}** {llm_evaluation['summary']}")
            
            if "improvement_focus" in llm_evaluation:
                st.write(f"**{self.get_text('improvement_focus_label')}**")
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
                st.write(f"**{self.get_text('critical_issues_label')}** {llm_evaluation['critical_mistakes']}")
            
            if "system_strengths" in llm_evaluation:
                st.write(f"**{self.get_text('system_strengths_label')}** {llm_evaluation['system_strengths']}")
    
    def run(self):
        self.setup_page_config()
        self.render_language_selector()
        self.render_main_interface()
        
        # Always show extracted JSON if we have data in session state
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