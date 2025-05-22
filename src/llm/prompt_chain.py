"""
LLM Prompt Chaining Middleware

This module implements a multi-step prompting process for clinical vignette analysis.
It orchestrates a series of LLM calls, each with specific tasks and structured outputs,
that build upon each other to produce a comprehensive analysis.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from src.llm.classification import parse_patient_text  # Import existing LLM integration
from src.core.models import PatientData

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define schemas for structured outputs
ENTITY_EXTRACTION_SCHEMA = {
    "symptoms": "list of symptoms mentioned in the vignette",
    "medical_problems": "list of medical problems or conditions mentioned",
    "medications": "list of medications mentioned",
    "vital_signs": "dictionary of vital signs with values",
    "demographics": {
        "age": "patient age if mentioned",
        "weight": "patient weight if mentioned (in kg)",
        "sex": "patient sex if mentioned"
    },
    "medical_history": "relevant past medical history",
    "clinical_context": "additional clinical context like location, transport mode"
}

SPECIALTY_ASSESSMENT_SCHEMA = {
    "identified_specialties_needed": [
        {
            "specialty_name": "name of the specialty",
            "likelihood_score": "numerical score from 0-100 indicating confidence",
            "supporting_evidence": "text explaining why this specialty is needed"
        }
    ]
}

EXCLUSION_EVALUATION_SCHEMA = {
    "exclusion_criteria_evaluation": [
        {
            "exclusion_rule_id": "identifier of the exclusion rule",
            "rule_text": "full text of the exclusion rule",
            "status": "one of: 'likely_met', 'likely_not_met', 'uncertain'",
            "confidence_score": "numerical score from 0-100",
            "evidence_from_vignette": "text explaining the evidence for this status determination"
        }
    ]
}

FINAL_OUTPUT_SCHEMA = {
    "extracted_clinical_entities": "output from step 1",
    "identified_specialties_needed": "output from step 2",
    "exclusion_criteria_evaluation": "output from step 3",
    "recommended_care_level": "one of: 'Regular', 'ICU', 'Specialized'",
    "confidence": "numerical score from 0-100",
    "explanation": "text explaining the overall recommendation"
}


class PromptChainOrchestrator:
    """
    Orchestrates a multi-step prompting process for clinical vignette analysis.
    """
    
    def __init__(self, llm_client, exclusion_criteria: Dict[str, Any]):
        """
        Initialize the orchestrator.
        
        Args:
            llm_client: Client for making LLM API calls
            exclusion_criteria: Dictionary of exclusion criteria by campus
        """
        self.llm_client = llm_client
        self.exclusion_criteria = exclusion_criteria
        
    def _construct_entity_extraction_prompt(self, vignette_text: str) -> str:
        """
        Construct the prompt for entity extraction.
        
        Args:
            vignette_text: Raw clinical vignette text
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""
        You are an expert clinical information extractor. Your task is to extract all relevant clinical information 
        from the following patient vignette. Think step-by-step and be thorough, but only include information 
        that is explicitly mentioned in the text.
        
        ## Patient Vignette:
        {vignette_text}
        
        ## Instructions:
        1. Extract all symptoms, medical problems, and medications mentioned in the vignette.
        2. Extract any vital signs with their values.
        3. Note any demographic information such as age, weight, and sex.
        4. Extract relevant past medical history.
        5. Note any clinical context like location or transport mode.
        
        ## Output Format:
        Provide your response as a JSON object with the following structure:
        {json.dumps(ENTITY_EXTRACTION_SCHEMA, indent=2)}
        
        Response:
        """
        return prompt
    
    def _construct_specialty_assessment_prompt(self, 
                                              extracted_entities: Dict[str, Any], 
                                              specialty_indicators: Dict[str, List[str]]) -> str:
        """
        Construct the prompt for specialty need assessment.
        
        Args:
            extracted_entities: Structured clinical entities from previous step
            specialty_indicators: Dictionary mapping specialties to their indicator terms
            
        Returns:
            Formatted prompt string
        """
        # Format extracted entities as text for the prompt
        entities_text = json.dumps(extracted_entities, indent=2)
        
        # Format specialty indicators for the prompt
        indicators_text = "\n".join([
            f"- {specialty}: {', '.join(indicators)}"
            for specialty, indicators in specialty_indicators.items()
        ])
        
        prompt = f"""
        You are an expert triage physician. Your task is to assess what medical specialties might be needed 
        based on the clinical information provided. Think step-by-step about each potential specialty need.
        
        ## Extracted Clinical Information:
        {entities_text}
        
        ## Specialty Need Indicators:
        The following are indicators that suggest a need for specific specialties:
        {indicators_text}
        
        ## Instructions:
        1. Based on the clinical information, identify which specialties might be needed for this patient.
        2. For each specialty, provide a likelihood score (0-100) and supporting evidence from the clinical information.
        3. Think step-by-step about why each specialty might be needed or not needed.
        4. Be comprehensive and consider all potential specialty needs suggested by the clinical information.
        
        ## Output Format:
        Provide your response as a JSON object with the following structure:
        {json.dumps(SPECIALTY_ASSESSMENT_SCHEMA, indent=2)}
        
        Response:
        """
        return prompt
    
    def _construct_exclusion_evaluation_prompt(self, 
                                              extracted_entities: Dict[str, Any],
                                              campus_name: str,
                                              campus_exclusions: Dict[str, Any]) -> str:
        """
        Construct the prompt for exclusion criteria evaluation.
        
        Args:
            extracted_entities: Structured clinical entities from previous step
            campus_name: Name of the campus being evaluated
            campus_exclusions: Exclusion criteria for the specified campus
            
        Returns:
            Formatted prompt string
        """
        # Format extracted entities as text for the prompt
        entities_text = json.dumps(extracted_entities, indent=2)
        
        # Format exclusion criteria for the prompt
        exclusions_text = ""
        exclusion_id = 1
        
        # General exclusions
        for exclusion in campus_exclusions.get("general_exclusions", []):
            exclusions_text += f"#{exclusion_id}. GENERAL: {exclusion}\n"
            exclusion_id += 1
        
        # Department-specific exclusions
        for dept, dept_data in campus_exclusions.get("departments", {}).items():
            for exclusion in dept_data.get("exclusions", []):
                exclusions_text += f"#{exclusion_id}. {dept.upper()}: {exclusion}\n"
                exclusion_id += 1
        
        prompt = f"""
        You are an expert transfer center physician. Your task is to evaluate whether this patient meets any 
        exclusion criteria for transfer to {campus_name}. Think step-by-step for each criterion.
        
        ## Extracted Clinical Information:
        {entities_text}
        
        ## Exclusion Criteria for {campus_name}:
        {exclusions_text}
        
        ## Instructions:
        1. For each numbered exclusion criterion, determine if it is 'likely_met', 'likely_not_met', or 'uncertain' based on the clinical information.
        2. Provide a confidence score (0-100) for your determination.
        3. For each criterion, cite specific evidence from the clinical information that supports your determination.
        4. Think step-by-step about how the clinical information relates to each criterion.
        
        ## Output Format:
        Provide your response as a JSON object with the following structure:
        {json.dumps(EXCLUSION_EVALUATION_SCHEMA, indent=2)}
        
        Response:
        """
        return prompt
    
    def _construct_final_recommendation_prompt(self,
                                              extracted_entities: Dict[str, Any],
                                              specialty_assessment: Dict[str, Any],
                                              exclusion_evaluation: Dict[str, Any]) -> str:
        """
        Construct the prompt for final recommendation.
        
        Args:
            extracted_entities: Structured clinical entities
            specialty_assessment: Specialty need assessment
            exclusion_evaluation: Exclusion criteria evaluation
            
        Returns:
            Formatted prompt string
        """
        # Combine all previous outputs for the prompt
        combined_data = {
            "extracted_clinical_entities": extracted_entities,
            "identified_specialties_needed": specialty_assessment.get("identified_specialties_needed", []),
            "exclusion_criteria_evaluation": exclusion_evaluation.get("exclusion_criteria_evaluation", [])
        }
        
        combined_text = json.dumps(combined_data, indent=2)
        
        prompt = f"""
        You are an expert transfer center physician making a final recommendation for patient transfer. 
        Your task is to synthesize all the analysis done so far and recommend an appropriate care level.
        
        ## Combined Analysis:
        {combined_text}
        
        ## Instructions:
        1. Based on all the information provided, determine the most appropriate care level for this patient.
        2. Consider the clinical entities, specialty needs, and exclusion criteria evaluations.
        3. Provide a confidence score (0-100) for your recommendation.
        4. Explain your reasoning in detail.
        
        ## Output Format:
        Provide your response as a JSON object with the following structure:
        {{
            "recommended_care_level": "one of: 'Regular', 'ICU', 'Specialized'",
            "confidence": "numerical score from 0-100",
            "explanation": "text explaining the overall recommendation"
        }}
        
        Response:
        """
        return prompt
    
    def _make_llm_call(self, prompt: str) -> str:
        """
        Make a call to the LLM API.
        
        Args:
            prompt: Formatted prompt string
            
        Returns:
            LLM response as a string
        """
        try:
            # This is a placeholder for the actual LLM API call
            # In a real implementation, this would use self.llm_client
            # to make the API call
            response = self.llm_client.generate(prompt)
            return response
        except Exception as e:
            logger.error(f"Error making LLM call: {e}")
            raise
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse a JSON response from the LLM.
        
        Args:
            response: LLM response string
            
        Returns:
            Parsed JSON as a dictionary
        """
        try:
            # Try to extract JSON from the response
            # This handles cases where the LLM might add additional text
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                logger.error("No JSON found in LLM response")
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            return {}
    
    def run_analysis_chain(self, vignette_text: str, campus_name: str) -> Dict[str, Any]:
        """
        Run the full analysis chain for a clinical vignette.
        
        Args:
            vignette_text: Raw clinical vignette text
            campus_name: Name of the campus being evaluated
            
        Returns:
            Comprehensive analysis as a dictionary
        """
        logger.info(f"Starting analysis chain for campus: {campus_name}")
        
        # Step 1: Entity extraction
        try:
            # First try using the existing parse_patient_text function as a fallback
            patient_data = parse_patient_text(vignette_text)
            
            # Convert PatientData to our expected entity extraction format
            extracted_entities = {
                "symptoms": [],
                "medical_problems": [],
                "medications": [],
                "vital_signs": {},
                "demographics": {
                    "age": getattr(patient_data, "age", None),
                    "weight": getattr(patient_data, "weight_kg", None),
                    "sex": getattr(patient_data, "sex", None)
                },
                "medical_history": patient_data.clinical_history if hasattr(patient_data, "clinical_history") else "",
                "clinical_context": ""
            }
            
            # Populate medical problems from chief complaint
            if hasattr(patient_data, "chief_complaint"):
                extracted_entities["medical_problems"].append(patient_data.chief_complaint)
            
            # Populate vital signs
            if hasattr(patient_data, "vital_signs") and patient_data.vital_signs:
                extracted_entities["vital_signs"] = patient_data.vital_signs
            
            logger.info("Used existing parse_patient_text for entity extraction")
        except Exception as e:
            logger.warning(f"Fallback method failed, using LLM for entity extraction: {e}")
            # If the fallback fails, use the LLM-based entity extraction
            entity_prompt = self._construct_entity_extraction_prompt(vignette_text)
            entity_response = self._make_llm_call(entity_prompt)
            extracted_entities = self._parse_json_response(entity_response)
            logger.info("Used LLM for entity extraction")
        
        # Step 2: Specialty need assessment
        # Get specialty indicators from exclusion criteria
        specialty_indicators = {}
        for campus_data in self.exclusion_criteria.get("campuses", {}).values():
            for dept, dept_data in campus_data.get("departments", {}).items():
                specialty_indicators[dept] = dept_data.get("conditions", [])
        
        specialty_prompt = self._construct_specialty_assessment_prompt(extracted_entities, specialty_indicators)
        specialty_response = self._make_llm_call(specialty_prompt)
        specialty_assessment = self._parse_json_response(specialty_response)
        logger.info("Completed specialty need assessment")
        
        # Step 3: Exclusion criteria evaluation
        # Get exclusion criteria for the specified campus
        campus_exclusions = {}
        for key, campus_data in self.exclusion_criteria.get("campuses", {}).items():
            if campus_name.lower() in key.lower() or key.lower() in campus_name.lower():
                campus_exclusions = campus_data
                break
        
        if not campus_exclusions:
            logger.warning(f"No exclusion criteria found for campus: {campus_name}")
            campus_exclusions = {"general_exclusions": [], "departments": {}}
        
        exclusion_prompt = self._construct_exclusion_evaluation_prompt(
            extracted_entities, campus_name, campus_exclusions
        )
        exclusion_response = self._make_llm_call(exclusion_prompt)
        exclusion_evaluation = self._parse_json_response(exclusion_response)
        logger.info("Completed exclusion criteria evaluation")
        
        # Step 4: Final recommendation
        recommendation_prompt = self._construct_final_recommendation_prompt(
            extracted_entities, specialty_assessment, exclusion_evaluation
        )
        recommendation_response = self._make_llm_call(recommendation_prompt)
        recommendation = self._parse_json_response(recommendation_response)
        logger.info("Completed final recommendation")
        
        # Combine all results into the final output
        final_output = {
            "extracted_clinical_entities": extracted_entities,
            "identified_specialties_needed": specialty_assessment.get("identified_specialties_needed", []),
            "exclusion_criteria_evaluation": exclusion_evaluation.get("exclusion_criteria_evaluation", []),
            "recommended_care_level": recommendation.get("recommended_care_level", ""),
            "confidence": recommendation.get("confidence", 0),
            "explanation": recommendation.get("explanation", "")
        }
        
        return final_output


def analyze_clinical_vignette(vignette_text: str, campus_name: str, llm_client, exclusion_criteria: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a clinical vignette for a specific campus.
    
    Args:
        vignette_text: Raw clinical vignette text
        campus_name: Name of the campus being evaluated
        llm_client: Client for making LLM API calls
        exclusion_criteria: Dictionary of exclusion criteria by campus
        
    Returns:
        Comprehensive analysis as a dictionary
    """
    orchestrator = PromptChainOrchestrator(llm_client, exclusion_criteria)
    try:
        result = orchestrator.run_analysis_chain(vignette_text, campus_name)
        return result
    except Exception as e:
        logger.error(f"Error analyzing clinical vignette: {e}")
        # Return a basic structure in case of error
        return {
            "extracted_clinical_entities": {},
            "identified_specialties_needed": [],
            "exclusion_criteria_evaluation": [],
            "recommended_care_level": "",
            "confidence": 0,
            "explanation": f"Error analyzing clinical vignette: {str(e)}"
        }
