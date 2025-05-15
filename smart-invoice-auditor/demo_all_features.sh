#!/bin/bash
# Demo script to showcase all features of the Smart Invoice Auditor system
# This script demonstrates the rule-based auditing, report generation, and agent-based features

# Set colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Function to print section headers
print_header() {
    echo -e "\n${BOLD}${BLUE}=======================================================================${NC}"
    echo -e "${BOLD}${BLUE}= $1${NC}"
    echo -e "${BOLD}${BLUE}=======================================================================${NC}"
}

# Function to print subsection headers
print_subheader() {
    echo -e "\n${BOLD}${YELLOW}--- $1 ---${NC}"
}

# Function to run a command with nice formatting
run_command() {
    echo -e "\n${BOLD}${GREEN}> $1${NC}"
    eval $1
    echo -e "${BOLD}${GREEN}Command completed.${NC}"
}

# Make sure we're in the right directory
cd "$(dirname "$0")"
BASE_DIR=$(pwd)
DATA_DIR="$BASE_DIR/data"
REPORTS_DIR="$DATA_DIR/reports"

# Create necessary directories
mkdir -p "$DATA_DIR/invoices"
mkdir -p "$DATA_DIR/policies"
mkdir -p "$REPORTS_DIR"

# Create a sample invoice JSON for testing
print_header "Setting up test data"
echo "Creating sample invoice data..."

cat > "$DATA_DIR/invoices/sample_invoice.json" << EOL
{
    "invoice_id": "INV-2023-006",
    "vendor": "IT Services Inc.",
    "date": "2023-08-15",
    "subtotal": 8000.00,
    "tax": 640.00,
    "total": 8640.00,
    "line_items": [
        {
            "description": "Server Hardware",
            "category": "hardware",
            "quantity": 1,
            "price": 5000.00
        },
        {
            "description": "IT Support (Monthly)",
            "category": "services",
            "quantity": 1,
            "price": 3000.00
        }
    ]
}
EOL

# Create a sample policy JSON for testing
echo "Creating sample policy data..."
cat > "$DATA_DIR/policies/sample_policy.json" << EOL
{
    "max_amount": 5000.00,
    "allowed_categories": [
        "office_supplies", 
        "electronics", 
        "software", 
        "furniture", 
        "consulting"
    ],
    "max_item_prices": {
        "office_supplies": 100.00,
        "electronics": 500.00,
        "software": 400.00,
        "furniture": 1000.00,
        "consulting": 350.00
    }
}
EOL

# 1. Rule-based auditing system
print_header "1. Rule-Based Auditing System"
print_subheader "Running comprehensive test script"
run_command "python comprehensive_test.py"

# 2. Report generator
print_header "2. Report Generator"
print_subheader "Generating reports in different formats"
run_command "python test_cli.py -i $REPORTS_DIR/comprehensive_test.json -r $REPORTS_DIR/demo_text.txt -f text"
run_command "python test_cli.py -i $REPORTS_DIR/comprehensive_test.json -r $REPORTS_DIR/demo_html.html -f html"
run_command "python test_cli.py -i $REPORTS_DIR/comprehensive_test.json -r $REPORTS_DIR/demo_json.json -f json"

# 3. Audit example
print_header "3. Audit Rules Example"
print_subheader "Demonstrating rule-based auditing"
run_command "python -m src.audit.audit_example"

# 4. Test with sample invoice
print_header "4. Testing with Sample Invoice"
print_subheader "Auditing sample invoice against policy"

# Run the main script with the sample invoice and policy
run_command "python src/main.py --invoice $DATA_DIR/invoices/sample_invoice.json --policy $DATA_DIR/policies/sample_policy.json --output $REPORTS_DIR/sample_audit_results.json --report $REPORTS_DIR/sample_report.html --report-format html"

# 5. Show report files
print_header "5. Generated Reports"
print_subheader "Listing all generated reports"
run_command "ls -lh $REPORTS_DIR"

# 6. Show report content samples
print_header "6. Report Content Samples"

print_subheader "Text Report Sample (First 10 lines)"
run_command "head -10 $REPORTS_DIR/demo_text.txt"

print_subheader "HTML Report Sample (First 10 lines)"
run_command "head -10 $REPORTS_DIR/demo_html.html"

print_subheader "JSON Report Sample (First 10 lines)"
run_command "head -10 $REPORTS_DIR/demo_json.json"

# 7. Summary
print_header "Demo Complete"
echo -e "${BOLD}The demo has showcased the following features:${NC}"
echo -e "1. ${BOLD}Rule-Based Auditing System${NC} - Comprehensive testing of all rule types"
echo -e "2. ${BOLD}Report Generator${NC} - Creating reports in text, HTML, and JSON formats"
echo -e "3. ${BOLD}Audit Rules Example${NC} - Demonstrating the rule-based auditing capabilities"
echo -e "4. ${BOLD}Sample Invoice Testing${NC} - Auditing a sample invoice against policy rules"
echo -e "5. ${BOLD}Report Generation${NC} - Generating detailed reports with explanations"
echo -e "\n${BOLD}${GREEN}All features have been successfully demonstrated!${NC}"
echo -e "\n${BOLD}Generated reports can be found in:${NC} $REPORTS_DIR"