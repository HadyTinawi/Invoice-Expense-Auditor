#!/bin/bash
# Master script to run all demo scripts for the Smart Invoice Auditor

# Set colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Make sure we're in the right directory
cd "$(dirname "$0")"
BASE_DIR=$(pwd)

# Function to print the menu
print_menu() {
    clear
    echo -e "${BOLD}${BLUE}=======================================================================${NC}"
    echo -e "${BOLD}${BLUE}=                 Smart Invoice Auditor Demo Menu                    =${NC}"
    echo -e "${BOLD}${BLUE}=======================================================================${NC}"
    echo -e "\n${BOLD}Please select an option:${NC}"
    echo -e "1. ${BOLD}Run All Features Demo${NC} (Comprehensive demonstration of all features)"
    echo -e "2. ${BOLD}Run Web Interface${NC} (Start the Streamlit web interface)"
    echo -e "3. ${BOLD}Run Comprehensive Test${NC} (Test all components of the system)"
    echo -e "4. ${BOLD}Run Audit Example${NC} (Demonstrate rule-based auditing)"
    echo -e "5. ${BOLD}Run Report Generator Test${NC} (Test report generation in different formats)"
    echo -e "6. ${BOLD}Exit${NC}"
    echo -e "\n${BOLD}Enter your choice [1-6]:${NC} "
}

# Function to run a command and wait for user to continue
run_command() {
    echo -e "\n${BOLD}${GREEN}Running: $1${NC}\n"
    eval $1
    echo -e "\n${BOLD}${YELLOW}Press Enter to continue...${NC}"
    read
}

# Main loop
while true; do
    print_menu
    read choice
    
    case $choice in
        1)
            run_command "./demo_all_features.sh"
            ;;
        2)
            echo -e "\n${BOLD}${YELLOW}Starting web interface. Press Ctrl+C to stop when done.${NC}\n"
            ./run_web_interface.sh
            echo -e "\n${BOLD}${YELLOW}Press Enter to continue...${NC}"
            read
            ;;
        3)
            run_command "python comprehensive_test.py"
            ;;
        4)
            run_command "python -m src.audit.audit_example"
            ;;
        5)
            # Create data directory if it doesn't exist
            mkdir -p "$BASE_DIR/data/reports"
            
            # Run report generator test
            echo -e "\n${BOLD}${GREEN}Testing report generation in different formats...${NC}\n"
            
            # Generate sample audit results if they don't exist
            if [ ! -f "$BASE_DIR/data/reports/comprehensive_test.json" ]; then
                echo "Creating sample audit results..."
                python comprehensive_test.py > /dev/null 2>&1
            fi
            
            # Generate reports in different formats
            echo "Generating text report..."
            python test_cli.py -i "$BASE_DIR/data/reports/comprehensive_test.json" -r "$BASE_DIR/data/reports/menu_text.txt" -f text
            
            echo "Generating HTML report..."
            python test_cli.py -i "$BASE_DIR/data/reports/comprehensive_test.json" -r "$BASE_DIR/data/reports/menu_html.html" -f html
            
            echo "Generating JSON report..."
            python test_cli.py -i "$BASE_DIR/data/reports/comprehensive_test.json" -r "$BASE_DIR/data/reports/menu_json.json" -f json
            
            echo -e "\n${BOLD}${GREEN}Reports generated successfully!${NC}"
            echo -e "Text report: $BASE_DIR/data/reports/menu_text.txt"
            echo -e "HTML report: $BASE_DIR/data/reports/menu_html.html"
            echo -e "JSON report: $BASE_DIR/data/reports/menu_json.json"
            
            echo -e "\n${BOLD}${YELLOW}Press Enter to continue...${NC}"
            read
            ;;
        6)
            echo -e "\n${BOLD}${GREEN}Thank you for using the Smart Invoice Auditor Demo!${NC}"
            exit 0
            ;;
        *)
            echo -e "\n${BOLD}${RED}Invalid option. Please try again.${NC}"
            sleep 2
            ;;
    esac
done