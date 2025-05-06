# Smart Invoice & Expense Auditor

## 🔍 Overview

The Smart Invoice & Expense Auditor is an AI-powered tool designed to automate the detection of billing errors, duplicate charges, and policy violations in invoice PDFs. By combining OCR technology with intelligent agent-based auditing, this system dramatically reduces manual review time and improves accuracy in expense management.

## ✨ Key Features

- **PDF Invoice Processing**: Upload and process invoice PDFs through a simple interface
- **Intelligent OCR**: Extract structured data from unstructured invoice documents
- **Policy Compliance Checking**: Automatically verify charges against vendor policies
- **Duplicate Detection**: Flag repeated invoice IDs and potential double-billing
- **Detailed Audit Reports**: Receive clear explanations for all flagged issues

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│  PDF Upload &   │    │  OCR Processing  │    │  Agent-Based Audit │
│  Management     │────►  & Extraction    │────►  & Analysis        │
└─────────────────┘    └──────────────────┘    └────────────────────┘
                                                        │
                       ┌──────────────────┐            ▼
                       │  Policy Storage  │    ┌────────────────────┐
                       │  & Management    │◄───┤  Results & Report  │
                       └──────────────────┘    │  Generation        │
                                               └────────────────────┘
```

## 🛠️ Technology Stack

- **OCR Engine**: Tesseract.js / AWS Textract
- **Agent Framework**: LangChain (Python) / LangGraph
- **Policy Input**: CSV/TXT data (static or scraped with Firecrawl MCP)
- **Issue Detection**: Rule-based logic + optional GPT-4o analysis
- **Frontend (Optional)**: Streamlit for demo purposes

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Required packages: `pip install -r requirements.txt`

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/smart-invoice-auditor.git
cd smart-invoice-auditor

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Usage

```bash
# Run with CLI interface
python src/main.py --invoice path/to/invoice.pdf --policy path/to/policy.csv

# Run with web interface (if implemented)
python src/app.py
```

## 📊 Examples & Use Cases

| Scenario | Example | Detection Method |
|----------|---------|------------------|
| Duplicate Invoice | Same invoice ID appears twice | Hash comparison + ID tracking |
| Price Mismatch | Charge doesn't match contracted rate | Policy lookup + comparison |
| Policy Violation | $200 charge when max allowed is $100 | Rule-based threshold check |

## 📁 Project Structure

```
smart-invoice-auditor/
├── src/
│   ├── ocr/              # OCR processing modules
│   ├── agent/            # Auditor agent implementation
│   ├── policy/           # Policy management and storage
│   ├── main.py           # CLI entry point
│   └── app.py            # Web interface (optional)
├── tests/                # Test suite
├── data/
│   ├── invoices/         # Example invoices for testing
│   └── policies/         # Sample vendor policies
├── notebooks/            # Jupyter notebooks for exploration
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## 🧪 Testing

```bash
# Run test suite
pytest

# Run with sample data
python src/main.py --demo
```

## 📝 Todo

- [ ] Implement basic OCR pipeline
- [ ] Build agent-based audit logic
- [ ] Create simple upload interface
- [ ] Add policy management system
- [ ] Develop reporting functionality
- [ ] Add test cases with example invoices


## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [LangChain](https://github.com/langchain-ai/langchain)
- [ExpressExpense](https://expressexpense.com) for sample receipt dataset