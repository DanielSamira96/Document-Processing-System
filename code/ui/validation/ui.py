import streamlit as st
import re
from services.validation_service import ValidationService
from utils.message_types import MessageType
from .translations import VALIDATION_TEXTS


class ValidationUI:
    """UI component for validation and evaluation"""
    
    def __init__(self, validation_service, get_common_text_func):
        self.validation_service = validation_service
        self.get_common_text = get_common_text_func
    
    def get_text(self, key):
        """Get text for this component, with fallback to common texts"""
        language = st.session_state.get('language', 'en')
        
        # First try component-specific texts
        if key in VALIDATION_TEXTS:
            return VALIDATION_TEXTS[key].get(language, VALIDATION_TEXTS[key].get("en", ""))
        
        # Fallback to common texts
        return self.get_common_text(key)
    
    def render_validation_interface(self):
        """Render the validation and evaluation section"""
        st.divider()
        st.header(self.get_text("validation_title"))
        
        st.info(self.get_text("validation_instructions"))
        
        # Reorganized validation buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
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
            st.error(self.get_common_text("error_openai_config"))
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
                language = st.session_state.get('language', 'en')
                llm_evaluation = self.validation_service.get_llm_evaluation(expected_data, extracted_data, metrics, language)
                
                st.success(self.get_text("validation_complete"))
                
                # Store results in session state for display outside column constraint
                st.session_state['validation_metrics'] = metrics
                st.session_state['validation_evaluation'] = llm_evaluation
                
        except Exception as e:
            st.error(f"Validation error: {str(e)}")
    
    def render_validation_results(self):
        """Display validation results and metrics if available"""
        if 'validation_metrics' in st.session_state and 'validation_evaluation' in st.session_state:
            st.divider()
            self._display_validation_results(
                st.session_state['validation_metrics'], 
                st.session_state['validation_evaluation']
            )
    
    def _display_validation_results(self, metrics, llm_evaluation):
        """Display validation results and metrics"""
        st.subheader(self.get_text("validation_results"))
        
        # Full width layout for results and AI analysis
        results_col, analysis_col = st.columns([1, 1])
        
        with results_col:
            st.subheader(self.get_text("metrics_scores"))
            
            # Overall score from LLM
            overall_score = llm_evaluation.get("overall_score", {})
            text_rating = overall_score.get("text_rating", "N/A")
            # Capitalize first letter
            if text_rating != "N/A":
                text_rating = text_rating.capitalize()
            
            col1, col2 = st.columns([1, 1])
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
            
            col1, col2 = st.columns([1, 1])
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
                    # Try to get translation, fallback to formatted English
                    translated_category = self.get_text(category.replace('_', ' ').title()) or category.replace('_', ' ').title()
                    st.write(f"**{translated_category}:** {feedback}")
            
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