# Document Processing System

A comprehensive document processing system that extracts information from ביטוח לאומי (National Insurance Institute) forms using Azure Document Intelligence OCR and Azure OpenAI. The system provides an intuitive web interface for uploading documents, processing them with AI, and validating the extracted data.

## 🎯 Project Goal

This system automates the extraction of structured information from Hebrew and English insurance forms, providing:
- **OCR Processing**: Using Azure Document Intelligence for text extraction
- **AI-Powered Field Extraction**: Leveraging Azure OpenAI GPT-4o for intelligent data parsing
- **Multilingual Support**: Handling forms filled in both Hebrew and English
- **Validation System**: Comprehensive accuracy evaluation with AI-powered analysis
- **User-Friendly Interface**: Clean Streamlit web application with RTL support

## 🚀 What the System Does

1. **Document Upload**: Accept PDF/JPG files through web interface
2. **OCR Processing**: Extract text using Azure Document Intelligence
3. **Language Detection**: Automatically identify document language (Hebrew/English)
4. **Field Extraction**: Use GPT-4o to parse structured data into JSON format
5. **Data Validation**: Compare extracted data against ground truth with detailed metrics
6. **AI Analysis**: Generate improvement recommendations and accuracy insights

## 📋 Supported Fields

The system extracts the following information into a structured JSON format:

### JSON Output Structure
```json
{
  "lastName": "",
  "firstName": "",
  "idNumber": "",
  "gender": "",
  "dateOfBirth": {
    "day": "",
    "month": "",
    "year": ""
  },
  "address": {
    "street": "",
    "houseNumber": "",
    "entrance": "",
    "apartment": "",
    "city": "",
    "postalCode": "",
    "poBox": ""
  },
  "landlinePhone": "",
  "mobilePhone": "",
  "jobType": "",
  "dateOfInjury": {
    "day": "",
    "month": "",
    "year": ""
  },
  "timeOfInjury": "",
  "accidentLocation": "",
  "accidentAddress": "",
  "accidentDescription": "",
  "injuredBodyPart": "",
  "signature": "",
  "formFillingDate": {
    "day": "",
    "month": "",
    "year": ""
  },
  "formReceiptDateAtClinic": {
    "day": "",
    "month": "",
    "year": ""
  },
  "medicalInstitutionFields": {
    "healthFundMember": "",
    "natureOfAccident": "",
    "medicalDiagnoses": ""
  }
}
```

### Field Categories
- **Personal Details**: Name, ID, gender, birth date
- **Address Information**: Street, house number, city, postal code
- **Contact Details**: Landline and mobile phone numbers
- **Accident Details**: Date, time, location, description
- **Medical Information**: Injured body part, diagnoses
- **Form Metadata**: Filling dates, signatures

## 🏗️ Project Structure

```
Document-Processing-System/
├── code/
│   ├── ui/                              # User Interface Components
│   │   ├── document_extraction/         # Document processing UI module
│   │   │   ├── ui.py                   # Document extraction interface
│   │   │   ├── translations.py         # Extraction-specific text translations
│   │   │   └── __init__.py             # Module initialization
│   │   ├── validation/                  # Validation UI module
│   │   │   ├── ui.py                   # Validation interface with metrics display
│   │   │   ├── translations.py         # Validation-specific text translations
│   │   │   └── __init__.py             # Module initialization
│   │   ├── common/                      # Shared UI components
│   │   │   ├── translations.py         # Common text translations (errors, languages)
│   │   │   └── __init__.py             # Module initialization
│   │   ├── streamlit_app.py            # Main Streamlit application entry point
│   │   └── styles.css                  # CSS styling for RTL support and UI enhancement
│   ├── services/                        # Core Business Logic
│   │   ├── document_intelligence_service.py  # Azure Document Intelligence integration
│   │   ├── openai_service.py           # Azure OpenAI GPT-4o integration and language detection
│   │   └── validation_service.py       # Data validation and metrics calculation
│   ├── prompts/                         # AI Prompt Engineering
│   │   ├── field_extraction_prompt.py  # System prompts for field extraction
│   │   └── validation_judge_prompt.py  # System prompts for validation analysis
│   └── utils/                           # Utility Functions
│       ├── config.py                   # Configuration management from environment variables
│       ├── file_validator.py           # File format and size validation
│       ├── message_types.py            # Enum definitions for message types
│       └── text_preprocessor.py        # OCR text cleaning and preprocessing rules
├── phase1_data/                         # Test Documents
│   ├── 283_ex1.pdf                     # Example document 1
│   ├── 283_ex2.pdf                     # Example document 2  
│   ├── 283_ex3.pdf                     # Example document 3
│   ├── 283_extra1.pdf                  # Additional test document
│   └── 283_raw.pdf                     # Raw blank form template
├── templates/                           # JSON Templates
│   ├── empty_json_en.json              # Empty English field structure template
│   ├── empty_json_he.json              # Empty Hebrew field structure template
│   ├── 283_ex1_gt.json                 # Ground truth for example 1
│   ├── 283_ex2_gt.json                 # Ground truth for example 2
│   ├── 283_ex3_gt.json                 # Ground truth for example 3
│   └── 283_extra1_gt.json              # Ground truth for extra example
├── outputs/                             # Generated Results (auto-created)
├── temp/                                # Temporary file storage (auto-created)
├── .env.example                         # Environment variables template
├── requirements.txt                     # Python dependencies
└── README.md                           # This file
```

## 🛠️ Setup Instructions

### Prerequisites

- **Python 3.9+** (Tested with Python 3.10.6)
- **Azure Account** with Document Intelligence and OpenAI services
- **Git** for version control

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd Document-Processing-System
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file with your Azure credentials:
   
   ```env
   # Azure Document Intelligence Configuration
   AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
   AZURE_DOCUMENT_INTELLIGENCE_KEY=your-document-intelligence-key
   
   # Azure OpenAI Configuration  
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_KEY=your-openai-key
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
   AZURE_OPENAI_API_VERSION=2024-02-01
   AZURE_OPENAI_MAX_TOKENS=5000
   AZURE_OPENAI_TEMPERATURE=0.1
   
   # Application Configuration
   DEFAULT_LANGUAGE=en                    # Default UI language (en/he)
   SUPPORTED_LANGUAGES=en,he              # Comma-separated supported languages
   MAX_FILE_SIZE_MB=200                   # Maximum file upload size in MB
   ```

### Environment Variables Explained

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` | Azure Document Intelligence service endpoint | `https://your-resource.cognitiveservices.azure.com/` |
| `AZURE_DOCUMENT_INTELLIGENCE_KEY` | API key for Document Intelligence | `your-32-character-key` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI service endpoint | `https://your-resource.openai.azure.com/` |
| `AZURE_OPENAI_KEY` | API key for OpenAI service | `your-32-character-key` |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Name of your GPT model deployment | `gpt-4o` |
| `AZURE_OPENAI_API_VERSION` | OpenAI API version to use | `2024-02-01` |
| `AZURE_OPENAI_MAX_TOKENS` | Maximum tokens for AI responses | `5000` |
| `AZURE_OPENAI_TEMPERATURE` | AI creativity level (0.0-1.0) | `0.1` |
| `DEFAULT_LANGUAGE` | Default UI language | `en` or `he` |
| `SUPPORTED_LANGUAGES` | Supported UI languages | `en,he` |
| `MAX_FILE_SIZE_MB` | Maximum upload file size | `200` |

## 🏃‍♂️ Running the Application

1. **Start the Streamlit Application**
   ```bash
   streamlit run app.py
   ```

2. **Access the Web Interface**
   - Open your browser to `http://localhost:8501`
   - The application will launch with language selection and file upload interface

3. **Using the System**
   - Select your preferred language (English/Hebrew)
   - Upload a PDF or image file
   - Click "Start Processing" to extract data
   - View the extracted JSON results
   - Use the validation section to compare against ground truth data

## 🧪 Testing the System

Use the provided test documents in `phase1_data/` folder:
- Upload any of the example PDFs
- Compare results with corresponding ground truth files in `templates/`
- Test with both Hebrew and English filled forms

## 📊 Validation Features

The system includes comprehensive validation capabilities:
- **Accuracy Metrics**: Overall field matching percentage
- **Language Consistency**: Verification of detected vs expected language
- **Specialized Metrics**: Date recognition, phone number extraction, checkbox detection
- **AI Analysis**: GPT-4o powered evaluation with improvement suggestions
- **Detailed Reports**: Category-wise feedback and system strengths/weaknesses

## 🌐 Multilingual Support

- **Dynamic Language Switching**: Change language without losing current work
- **Bilingual Templates**: Support for both English and Hebrew field names
- **Automatic Detection**: AI-powered language detection for uploaded documents

## 📦 Dependencies

See `requirements.txt` for full dependency list:
- `streamlit>=1.28.0` - Web application framework
- `azure-ai-documentintelligence>=1.0.0` - Azure OCR service
- `openai>=1.3.0` - Azure OpenAI integration
- `python-dotenv>=1.0.0` - Environment variable management
- `azure-core>=1.29.0` - Azure SDK core functionality
