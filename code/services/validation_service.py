import json
import re
import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from .openai_service import OpenAIService
from prompts.validation_judge_prompt import VALIDATION_JUDGE_PROMPT
from utils.message_types import MessageType

logger = logging.getLogger(__name__)

@dataclass
class ValidationMetrics:
    overall_accuracy: float
    language_consistency: bool
    dates_accuracy: float
    phone_accuracy: float
    checkbox_accuracy: float
    empty_fields_accuracy: float
    structure_compliance: float
    total_fields: int
    correct_fields: int

class ValidationService:
    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service
        
        # Load template schemas
        self.templates = self._load_templates()
        
        # Define field categories
        self.date_fields = [
            "dateOfBirth", "dateOfInjury", "formFillingDate", "formReceiptDateAtClinic",
            "תאריך לידה", "תאריך הפגיעה", "תאריך מילוי הטופס", "תאריך קבלת הטופס בקופה"
        ]
        
        self.phone_fields = [
            "landlinePhone", "mobilePhone", "טלפון קווי", "טלפון נייד"
        ]
        
        self.checkbox_fields = [
            "gender", "accidentLocation", "healthFundMember",
            "מין", "מקום התאונה", "חבר בקופת חולים"
        ]
    
    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load template schemas for validation"""
        templates = {}
        try:
            # Load English template
            with open("templates/empty_json_en.json", "r", encoding="utf-8") as f:
                templates["en"] = json.load(f)
            
            # Load Hebrew template
            with open("templates/empty_json_he.json", "r", encoding="utf-8") as f:
                templates["he"] = json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading templates: {str(e)}")
            templates = {"en": {}, "he": {}}
            
        return templates
    
    def validate_json_file(self, json_content: str, get_text_func, expected_extraction_language: str = None) -> Tuple[Dict[str, Any], str, MessageType]:
        """Validate uploaded JSON file against template schema"""
        get_text = get_text_func
        
        try:
            # Try to parse JSON
            data = json.loads(json_content)
            
            # Check if it has the expected structure
            if not isinstance(data, dict):
                return None, get_text("json_not_dictionary"), MessageType.ERROR
            
            # Detect language and get appropriate template
            detected_lang = self.detect_json_language(data)
            template = self.templates.get(detected_lang, {})
            
            if not template:
                return None, get_text("no_template_available"), MessageType.ERROR
            
            # Validate structure against template
            is_valid, error_message = self._validate_structure(data, template)
            if not is_valid:
                return None, f"{get_text('structure_validation_failed')}: {error_message}", MessageType.ERROR
            
            # Check for language mismatch with extracted data
            message_type = MessageType.INFO
            success_message = get_text("valid_json_structure")
            
            if expected_extraction_language and expected_extraction_language != detected_lang:
                success_message = get_text("languages_mismatch").format(
                    extraction_lang=get_text(expected_extraction_language),
                    gt_lang=get_text(detected_lang)
                )
                message_type = MessageType.WARNING
            
            return data, success_message, message_type
            
        except json.JSONDecodeError as e:
            return None, f"{get_text('invalid_json_format')}: {str(e)}", MessageType.ERROR
        except Exception as e:
            return None, f"{get_text('validation_error')}: {str(e)}", MessageType.ERROR
    
    def _validate_structure(self, data: Dict[str, Any], template: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate JSON structure against template schema"""
        def check_structure(actual, expected, path=""):
            # Check for missing required fields
            for key, expected_value in expected.items():
                current_path = f"{path}.{key}" if path else key
                
                if key not in actual:
                    return False, f"Missing required field: {current_path}"
                
                actual_value = actual[key]
                
                # Check nested dictionaries
                if isinstance(expected_value, dict):
                    if not isinstance(actual_value, dict):
                        return False, f"Field {current_path} should be an object/dictionary"
                    
                    is_valid, error = check_structure(actual_value, expected_value, current_path)
                    if not is_valid:
                        return False, error
                
                # For leaf nodes, check type consistency
                elif isinstance(expected_value, str) and not isinstance(actual_value, str):
                    return False, f"Field {current_path} should be a string"
            
            # Check for extra fields that shouldn't be there
            for key in actual.keys():
                if key not in expected:
                    current_path = f"{path}.{key}" if path else key
                    return False, f"Unexpected field found: {current_path} (not in template schema)"
            
            return True, ""
        
        return check_structure(data, template)
    
    def detect_json_language(self, json_data: Dict[str, Any]) -> str:
        """Detect if JSON uses Hebrew or English field names"""
        hebrew_keys = ["שם משפחה", "שם פרטי", "מספר זהות", "מין"]
        english_keys = ["firstName", "lastName", "idNumber", "gender"]
        
        hebrew_count = sum(1 for key in hebrew_keys if key in json_data)
        english_count = sum(1 for key in english_keys if key in json_data)
        
        return "he" if hebrew_count > english_count else "en"
    
    def calculate_metrics(self, expected: Dict[str, Any], extracted: Dict[str, Any]) -> ValidationMetrics:
        """Calculate comprehensive validation metrics"""
        
        # Language consistency
        expected_lang = self.detect_json_language(expected)
        extracted_lang = self.detect_json_language(extracted)
        language_consistent = expected_lang == extracted_lang
        
        # Overall accuracy
        total_fields = 0
        correct_fields = 0
        
        # Flatten JSONs for comparison
        expected_flat = self._flatten_json(expected)
        extracted_flat = self._flatten_json(extracted)
        
        for key, expected_value in expected_flat.items():
            total_fields += 1
            extracted_value = extracted_flat.get(key, "")
            if self._values_match(expected_value, extracted_value):
                correct_fields += 1
        
        overall_accuracy = (correct_fields / total_fields) * 100 if total_fields > 0 else 0
        
        # Category-specific accuracies
        dates_accuracy = self._calculate_category_accuracy(expected_flat, extracted_flat, self.date_fields)
        phone_accuracy = self._calculate_category_accuracy(expected_flat, extracted_flat, self.phone_fields)
        checkbox_accuracy = self._calculate_category_accuracy(expected_flat, extracted_flat, self.checkbox_fields)
        
        # Empty fields accuracy
        empty_fields_accuracy = self._calculate_empty_fields_accuracy(expected_flat, extracted_flat)
        
        # Structure compliance
        structure_compliance = self._calculate_structure_compliance(expected, extracted)
        
        return ValidationMetrics(
            overall_accuracy=overall_accuracy,
            language_consistency=language_consistent,
            dates_accuracy=dates_accuracy,
            phone_accuracy=phone_accuracy,
            checkbox_accuracy=checkbox_accuracy,
            empty_fields_accuracy=empty_fields_accuracy,
            structure_compliance=structure_compliance,
            total_fields=total_fields,
            correct_fields=correct_fields
        )
    
    def _flatten_json(self, json_data: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
        """Flatten nested JSON structure"""
        items = []
        for key, value in json_data.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            
            if isinstance(value, dict):
                items.extend(self._flatten_json(value, new_key).items())
            else:
                items.append((new_key, value))
        
        return dict(items)
    
    def _values_match(self, expected: str, extracted: str) -> bool:
        """Check if two values match (exact match)"""
        return str(expected).strip() == str(extracted).strip()
    
    def _calculate_category_accuracy(self, expected_flat: Dict, extracted_flat: Dict, category_fields: List[str]) -> float:
        """Calculate accuracy for specific category of fields"""
        category_total = 0
        category_correct = 0
        
        for key, expected_value in expected_flat.items():
            # Check if this field belongs to the category
            field_in_category = False
            for category_field in category_fields:
                if category_field in key:
                    field_in_category = True
                    break
            
            if field_in_category:
                category_total += 1
                extracted_value = extracted_flat.get(key, "")
                if self._values_match(expected_value, extracted_value):
                    category_correct += 1
        
        return (category_correct / category_total) * 100 if category_total > 0 else 100
    
    def _calculate_empty_fields_accuracy(self, expected_flat: Dict, extracted_flat: Dict) -> float:
        """Calculate accuracy for empty fields recognition"""
        empty_total = 0
        empty_correct = 0
        
        for key, expected_value in expected_flat.items():
            if expected_value == "" or expected_value is None:
                empty_total += 1
                extracted_value = extracted_flat.get(key, "")
                if extracted_value == "" or extracted_value is None:
                    empty_correct += 1
        
        return (empty_correct / empty_total) * 100 if empty_total > 0 else 100
    
    def _calculate_structure_compliance(self, expected: Dict[str, Any], extracted: Dict[str, Any]) -> float:
        """Calculate structure compliance percentage accounting for both missing and extra fields"""
        def get_structure_keys(data, path=""):
            """Get all structural keys (field names) from nested dict"""
            keys = set()
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                keys.add(current_path)
                if isinstance(value, dict):
                    keys.update(get_structure_keys(value, current_path))
            return keys
        
        expected_keys = get_structure_keys(expected)
        extracted_keys = get_structure_keys(extracted)
        
        if not expected_keys:
            return 100.0
        
        # Count matching fields (correct structure)
        matching_keys = expected_keys.intersection(extracted_keys)
        
        # Count missing fields (fields expected but not in extracted)
        missing_keys = expected_keys - extracted_keys
        
        # Count extra fields (fields in extracted but not expected)
        extra_keys = extracted_keys - expected_keys
        
        # Calculate compliance score
        # Perfect score = all expected fields present AND no extra fields
        # Penalize for both missing and extra fields
        total_expected = len(expected_keys)
        correct_fields = len(matching_keys)
        penalty_for_extras = min(len(extra_keys), total_expected)  # Cap penalty at total expected
        
        # Score = (correct fields - extra fields penalty) / total expected fields
        effective_score = max(0, correct_fields - penalty_for_extras)
        return (effective_score / total_expected) * 100
    
    def get_llm_evaluation(self, expected: Dict[str, Any], extracted: Dict[str, Any], metrics: ValidationMetrics, user_language: str = "en") -> Dict[str, Any]:
        """Get LLM-as-a-judge evaluation"""
        try:
            # Language instruction
            language_instruction = "Please respond in Hebrew." if user_language == "he" else "Please respond in English."
            
            # Prepare the evaluation prompt
            user_prompt = f"""
EXPECTED_JSON:
{json.dumps(expected, ensure_ascii=False, indent=2)}

EXTRACTED_JSON:
{json.dumps(extracted, ensure_ascii=False, indent=2)}

CALCULATED_METRICS:
- Overall Accuracy: {metrics.overall_accuracy:.1f}%
- Language Consistency: {"Yes" if metrics.language_consistency else "No"}
- Dates Accuracy: {metrics.dates_accuracy:.1f}%
- Phone Numbers Accuracy: {metrics.phone_accuracy:.1f}%
- Checkbox Selection Accuracy: {metrics.checkbox_accuracy:.1f}%
- Empty Fields Recognition: {metrics.empty_fields_accuracy:.1f}%
- Structure Compliance: {metrics.structure_compliance:.1f}%
- Correct Fields: {metrics.correct_fields}/{metrics.total_fields}

{language_instruction}
Please provide your evaluation in the specified JSON format.
"""
            
            # Call LLM for evaluation
            response_text = self.openai_service.call_openai_api(
                VALIDATION_JUDGE_PROMPT, 
                user_prompt, 
                "json_object"
            )
            
            # Parse LLM response
            llm_evaluation = json.loads(response_text)
            return llm_evaluation
            
        except Exception as e:
            logger.error(f"Error getting LLM evaluation: {str(e)}")
            return {
                "overall_score": {"text_rating": "error", "numeric_score": 0},
                "summary": f"Error in LLM evaluation: {str(e)}"
            }