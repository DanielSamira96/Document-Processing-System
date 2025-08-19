from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.core.credentials import AzureKeyCredential
import logging

logger = logging.getLogger(__name__)

class DocumentIntelligenceService:
    def __init__(self, endpoint: str, key: str):
        self.endpoint = endpoint
        self.key = key
        self.client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )

    def analyze_document(self, document_path: str) -> AnalyzeResult:
        """
        
        """
        try:
            with open(document_path, "rb") as f:
                document_content = f.read()

            # Analyze document with key-value pairs feature
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=document_content,
                content_type="application/octet-stream",
                features=["keyValuePairs"]
            )

            result = poller.result()
            return result

        except Exception as e:
            logger.error(f"Error analyzing document: {str(e)}")
            raise e

    def convert_result_to_text(self, ocr_result: AnalyzeResult) -> str:
        """
        Converts the OCR result into a structured text format containing key-value pairs and raw lines.
        """
        try:
            if not ocr_result.pages:
                return None

            first_page = ocr_result.pages[0]

            key_value_lines = ["--- Key-Value Pairs: ---"]
            # Collect key-value pairs
            key_value_pairs = getattr(ocr_result, "key_value_pairs", [])
            if key_value_pairs:
                for kv in key_value_pairs:
                    if kv.key:
                        key_text = kv.key.content.strip()
                        value_text = kv.value.content.strip() if kv.value else ""
                        key_value_lines.append(f"{key_text}: {value_text}")
            else:
                key_value_lines.append("No key-value pairs detected.")

            # Collect raw lines
            raw_lines = ["--- Raw Lines: ---"]
            if first_page.lines:
                for line in first_page.lines:
                    raw_lines.append(f"{line.content.strip()}")
            else:
                raw_lines.append("No lines detected.")

            # Concatenate both sections
            full_text = "\n".join(key_value_lines) + "\n\n" + "\n".join(raw_lines)
            return full_text.strip()

        except Exception as e:
            logger.error(f"Error converting OCR result to text: {str(e)}")
            raise e

    def save_ocr_output(self, ocr_text_result: str, output_path: str) -> None:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(ocr_text_result)
            logger.info(f"OCR output saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving OCR output: {str(e)}")
            raise e
