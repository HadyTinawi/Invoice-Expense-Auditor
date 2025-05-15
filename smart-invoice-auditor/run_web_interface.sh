#!/bin/bash
# Script to run the Streamlit web interface for the Smart Invoice Auditor

# Set colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Make sure we're in the right directory
cd "$(dirname "$0")"

echo -e "${BOLD}${BLUE}=======================================================================${NC}"
echo -e "${BOLD}${BLUE}= Starting Smart Invoice Auditor Web Interface                        =${NC}"
echo -e "${BOLD}${BLUE}=======================================================================${NC}"

echo -e "\n${BOLD}${YELLOW}This script will start the Streamlit web interface for the Smart Invoice Auditor.${NC}"
echo -e "${BOLD}${YELLOW}You can access the interface by opening a web browser and navigating to:${NC}"
echo -e "${BOLD}${GREEN}http://localhost:8501${NC}"
echo -e "\n${BOLD}${YELLOW}The web interface allows you to:${NC}"
echo -e "- Upload and process invoices"
echo -e "- Apply policy rules"
echo -e "- View audit results"
echo -e "- Generate detailed reports in different formats"
echo -e "- Filter issues by source and severity"
echo -e "\n${BOLD}${YELLOW}Press Ctrl+C to stop the server when you're done.${NC}"

echo -e "\n${BOLD}${BLUE}Starting Streamlit server...${NC}"
streamlit run src/app.py