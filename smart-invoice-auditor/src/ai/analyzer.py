"""
AI Invoice Analyzer Module

This module uses LangChain to send invoice data to GPT-4o for intelligent analysis,
focusing on anomaly detection and providing detailed explanations.
"""

import os
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOpenAI as LegacyChatOpenAI


class AnomalyDetail(BaseModel):
    """Model for anomaly details"""
    anomaly_type: str = Field(description="Type of anomaly detected")
    description: str = Field(description="Detailed description of the anomaly")
    severity: str = Field(description="Severity level (low, medium, high)")
    confidence: float = Field(description="Confidence score (0.0 to 1.0)")
    affected_fields: List[str] = Field(description="List of affected invoice fields")
    recommendation: str = Field(description="Recommended action to address the anomaly")


class AnomalyAnalysisResult(BaseModel):
    """Model for the complete anomaly analysis result"""
    invoice_id: str = Field(description="ID of the analyzed invoice")
    anomalies_detected: bool = Field(description="Whether any anomalies were detected")
    anomaly_count: int = Field(description="Number of anomalies detected")
    anomalies: List[AnomalyDetail] = Field(description="List of detected anomalies")
    overall_assessment: str = Field(description="Overall assessment of the invoice")
    risk_score: float = Field(description="Overall risk score (0.0 to 1.0)")
    analysis_timestamp: str = Field(description="Timestamp of the analysis")


class InvoiceAnalyzer:
    """AI-powered invoice analyzer using LangChain and GPT-4o"""
    
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.0):
        """
        Initialize the invoice analyzer
        
        Args:
            model_name: Name of the OpenAI model to use
            temperature: Temperature setting for the model
        """
        self.model_name = model_name
        self.temperature = temperature
        self.llm = self._get_llm()
        self.output_parser = PydanticOutputParser(pydantic_object=AnomalyAnalysisResult)
    
    def _get_llm(self):
        """Get the language model based on configuration"""
        try:
            # Try to use the newer ChatOpenAI class
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=os.environ.get("OPENAI_API_KEY")
            )
        except ImportError:
            # Fall back to legacy ChatOpenAI if needed
            return LegacyChatOpenAI(
                model_name=self.model_name,
                temperature=self.temperature,
                openai_api_key=os.environ.get("OPENAI_API_KEY")
            )
    
    def _create_analysis_prompt(self, invoice_data: Dict[str, Any], 
                               vendor_history: Optional[List[Dict[str, Any]]] = None,
                               policy_data: Optional[Dict[str, Any]] = None) -> ChatPromptTemplate:
        """
        Create a prompt for invoice anomaly analysis
        
        Args:
            invoice_data: The invoice data to analyze
            vendor_history: Optional history of previous invoices from the same vendor
            policy_data: Optional policy data for the vendor
            
        Returns:
            ChatPromptTemplate for invoice analysis
        """
        # System message with detailed instructions
        system_template = """
        You are an Invoice Anomaly Detection Expert with years of experience in forensic accounting and fraud detection.
        Your task is to analyze invoice data and identify potential anomalies, irregularities, or suspicious patterns.
        
        Focus on detecting the following types of anomalies:
        1. Numerical inconsistencies (e.g., calculation errors, rounding issues)
        2. Unusual patterns compared to vendor history
        3. Policy violations or non-compliance
        4. Potential fraud indicators (e.g., duplicate invoices with slight modifications)
        5. Unusual dates, amounts, or descriptions
        6. Missing or incomplete critical information
        7. Unusual line item pricing or quantities
        
        For each anomaly you detect, provide:
        - A clear description of the anomaly
        - The severity level (low, medium, high)
        - Your confidence in the detection (0.0 to 1.0)
        - Which fields are affected
        - A recommendation for addressing the issue
        
        Be thorough in your analysis and explain your reasoning clearly.
        Provide an overall assessment of the invoice and a risk score from 0.0 (no risk) to 1.0 (high risk).
        
        {format_instructions}
        """
        
        # Human message with the invoice data
        human_template = """
        Please analyze this invoice data for anomalies:
        
        INVOICE DATA:
        {invoice_data}
        
        {vendor_history_section}
        
        {policy_section}
        
        Provide a detailed analysis identifying any anomalies, explaining your reasoning, and suggesting appropriate actions.
        """
        
        # Format vendor history section if provided
        vendor_history_section = ""
        if vendor_history:
            vendor_history_section = f"""
            VENDOR HISTORY:
            This vendor has {len(vendor_history)} previous invoices. Here is a summary:
            {json.dumps(vendor_history, indent=2)}
            """
        
        # Format policy section if provided
        policy_section = ""
        if policy_data:
            policy_section = f"""
            VENDOR POLICY:
            The following policy applies to this vendor:
            {json.dumps(policy_data, indent=2)}
            """
        
        # Create the prompt template
        return ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                system_template, 
                partial_variables={"format_instructions": self.output_parser.get_format_instructions()}
            ),
            HumanMessagePromptTemplate.from_template(
                human_template,
                partial_variables={
                    "invoice_data": json.dumps(invoice_data, indent=2),
                    "vendor_history_section": vendor_history_section,
                    "policy_section": policy_section
                }
            )
        ])
    
    def analyze_invoice(self, invoice_data: Dict[str, Any], 
                       vendor_history: Optional[List[Dict[str, Any]]] = None,
                       policy_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze an invoice for anomalies using GPT-4o
        
        Args:
            invoice_data: The invoice data to analyze
            vendor_history: Optional history of previous invoices from the same vendor
            policy_data: Optional policy data for the vendor
            
        Returns:
            Analysis results with detected anomalies
        """
        # Create the analysis prompt
        prompt = self._create_analysis_prompt(invoice_data, vendor_history, policy_data)
        
        # Get the chain
        chain = prompt | self.llm | self.output_parser
        
        try:
            # Run the chain
            result = chain.invoke({})
            
            # Convert to dict for consistency with the rest of the system
            if hasattr(result, "dict"):
                return result.dict()
            return result
        except Exception as e:
            # Handle any errors in the analysis
            return {
                "invoice_id": invoice_data.get("invoice_id", "UNKNOWN"),
                "anomalies_detected": True,
                "anomaly_count": 1,
                "anomalies": [{
                    "anomaly_type": "Analysis Error",
                    "description": f"Error during AI analysis: {str(e)}",
                    "severity": "medium",
                    "confidence": 1.0,
                    "affected_fields": ["all"],
                    "recommendation": "Review the invoice manually or try analysis again."
                }],
                "overall_assessment": "Analysis failed due to an error.",
                "risk_score": 0.5,
                "analysis_timestamp": datetime.now().isoformat()
            }


class InvoiceAnalysisService:
    """Service for analyzing invoices with AI"""
    
    def __init__(self, model_name: str = "gpt-4o", temperature: float = 0.0):
        """
        Initialize the invoice analysis service
        
        Args:
            model_name: Name of the OpenAI model to use
            temperature: Temperature setting for the model
        """
        self.analyzer = InvoiceAnalyzer(model_name, temperature)
    
    def analyze_invoice(self, invoice_data: Dict[str, Any], 
                       vendor_history: Optional[List[Dict[str, Any]]] = None,
                       policy_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze an invoice for anomalies
        
        Args:
            invoice_data: The invoice data to analyze
            vendor_history: Optional history of previous invoices from the same vendor
            policy_data: Optional policy data for the vendor
            
        Returns:
            Analysis results with detected anomalies
        """
        return self.analyzer.analyze_invoice(invoice_data, vendor_history, policy_data)
    
    def convert_to_audit_issues(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert AI analysis results to audit issues format
        
        Args:
            analysis_result: The AI analysis result
            
        Returns:
            List of issues in the format used by the audit system
        """
        issues = []
        
        for anomaly in analysis_result.get("anomalies", []):
            issues.append({
                "type": f"AI Anomaly: {anomaly.get('anomaly_type', 'Unknown')}",
                "description": anomaly.get("description", "No description provided"),
                "severity": anomaly.get("severity", "medium"),
                "confidence": anomaly.get("confidence", 0.5),
                "affected_fields": anomaly.get("affected_fields", []),
                "recommendation": anomaly.get("recommendation", ""),
                "source": "ai_analysis"
            })
        
        return issues


# Create a singleton instance for easy access
default_analyzer = InvoiceAnalysisService()


def analyze_invoice(invoice_data: Dict[str, Any], 
                   vendor_history: Optional[List[Dict[str, Any]]] = None,
                   policy_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyze an invoice for anomalies using the default analyzer
    
    Args:
        invoice_data: The invoice data to analyze
        vendor_history: Optional history of previous invoices from the same vendor
        policy_data: Optional policy data for the vendor
        
    Returns:
        Analysis results with detected anomalies
    """
    return default_analyzer.analyze_invoice(invoice_data, vendor_history, policy_data)


def get_analysis_issues(analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get issues from an analysis result in the format used by the audit system
    
    Args:
        analysis_result: The analysis result to convert
        
    Returns:
        List of issues in the format used by the audit system
    """
