# Smart Invoice Auditor

An intelligent invoice processing and auditing system that uses OCR to extract data from invoice PDFs and images, then audits them for errors and policy violations.

## Features

- **OCR Processing**: Extract data from PDF and image files (PNG, JPG, TIFF)
- **Intelligent Auditing**: Check invoices for calculation errors, policy violations, and suspicious patterns
- **Multiple UIs**: Choose between the full interface or a simplified version
- **AI-Powered Analysis**: Use LangChain agents to detect complex issues
- **Policy Enforcement**: Apply company expense policies automatically
- **Duplicate Detection**: Identify potential duplicate invoices to prevent double payments

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Make sure Tesseract OCR is installed:
   - macOS: `brew install tesseract`
   - Ubuntu: `sudo apt install tesseract-ocr`
   - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

## Configuration

1. Copy `.env.example` to `.env` and add your API keys:
   ```
   OPENAI_API_KEY=your-api-key-here
   OPENAI_MODEL=gpt-4o
   ```

2. (Optional) Add AWS credentials for Textract-based OCR:
   ```
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_REGION=us-east-1
   ```

## Running the Application

Use the provided runner script:

```
./run.py [options]
```

Options:
- `--simple`: Run the simplified UI version
- `--port PORT`: Specify the port (default: 7865)
- `--demo`: Run in demo mode with sample files
- `--debug`: Enable verbose debugging

Or run directly:

- **Original UI**: `python app.py`
- **Simplified UI**: `python simple_app.py`

## UI Versions

### Original UI
The full interface with all advanced features, suitable for power users.

### Simple UI
A streamlined, single-page interface designed for ease of use, with:
- Multiple file upload capability
- Clear display of results and issues
- Simplified controls

## Project Structure

```
smart-invoice-auditor/
├── app.py                  # Original full UI application
├── simple_app.py           # Simplified UI application
├── run.py                  # Runner script with options
├── src/
│   ├── ocr/                # OCR processing modules
│   ├── models/             # Data models and utilities
│   ├── agent/              # AI agent components
│   │   ├── auditor.py      # Main auditor agent
│   │   ├── workflow.py     # LangGraph workflow
│   │   └── tools.py        # Agent tools
│   ├── policy/             # Policy management
│   └── main.py             # CLI entry point
├── data/
│   └── policies/           # Policy definition files
├── samples/                # Sample invoices for testing
└── logs/                   # Application logs
```

## Creating Policy Files

Policies are defined in JSON format under `data/policies/`. Each policy file should include rules like:

```json
{
  "allowed_categories": ["Office Supplies", "Software", "Hardware"],
  "max_item_prices": {
    "Office Supplies": 100.00,
    "Software": 2000.00,
    "Hardware": 3000.00
  },
  "forbidden_categories": ["Entertainment"],
  "max_amount": 5000.00,
  "date_rules": {
    "max_age_days": 90
  },
  "tax_rate": 0.0825
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 