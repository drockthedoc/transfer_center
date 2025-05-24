"""
Confidence Estimation Module for Transfer Center recommendations.

This module calculates legitimate confidence scores for recommendations
based on multiple factors including data completeness, proximity data,
scoring results, exclusion criteria, and clinical data.
"""

from typing import Any, Dict, List, Optional, Union


class ConfidenceEstimator:
    """
    Calculates legitimate confidence scores for transfer recommendations.
    
    This class implements a multi-factor scoring system that weighs different
    aspects of the recommendation to provide a meaningful confidence score,
    rather than using random or fallback values.
    """
    
    # Weights for different factors in confidence calculation
    WEIGHTS = {
        "data_completeness": 0.20,  # How complete is our input data?
        "clinical_clarity": 0.25,   # How clear/specific is the clinical presentation?
        "exclusion_clarity": 0.15,  # How confident are we about exclusion criteria?
        "proximity_data": 0.15,     # How good is our proximity/travel data?
        "scoring_results": 0.25,    # How many pediatric scores do we have?
    }
    
    @classmethod
    def calculate_confidence(
        cls,
        patient_data: Dict[str, Any],
        clinical_data: Dict[str, Any],
        exclusion_data: Optional[Dict[str, Any]] = None,
        proximity_data: Optional[Dict[str, Any]] = None,
        scoring_results: Optional[Dict[str, Any]] = None,
        campus_match_score: Optional[float] = None,
    ) -> float:
        """
        Calculate a weighted confidence score based on multiple factors.
        
        Args:
            patient_data: Dictionary of patient demographics and info
            clinical_data: Dictionary of clinical information (vitals, etc.)
            exclusion_data: Optional dictionary of exclusion evaluation results
            proximity_data: Optional dictionary of location/travel information
            scoring_results: Optional dictionary of pediatric scoring results
            campus_match_score: Optional campus match score (0-5)
            
        Returns:
            Confidence score as a percentage (0-100)
        """
        # Initialize factor scores
        factor_scores = {}
        
        # Calculate data completeness score
        factor_scores["data_completeness"] = cls._calculate_data_completeness(
            patient_data, clinical_data
        )
        
        # Calculate clinical clarity score
        factor_scores["clinical_clarity"] = cls._calculate_clinical_clarity(
            clinical_data
        )
        
        # Calculate exclusion clarity score
        factor_scores["exclusion_clarity"] = cls._calculate_exclusion_clarity(
            exclusion_data
        )
        
        # Calculate proximity data score
        factor_scores["proximity_data"] = cls._calculate_proximity_data(
            proximity_data
        )
        
        # Calculate scoring results score
        factor_scores["scoring_results"] = cls._calculate_scoring_results(
            scoring_results
        )
        
        # Apply weights to each factor
        weighted_score = 0.0
        for factor, score in factor_scores.items():
            weighted_score += score * cls.WEIGHTS[factor]
        
        # Apply campus match bonus (if available)
        if campus_match_score is not None:
            # Scale campus match from 0-5 to 0-1 and apply as a multiplier
            # A high campus match score can boost confidence, a low one reduces it
            match_factor = min(1.0, max(0.7, campus_match_score / 5.0))
            weighted_score *= match_factor
        
        # Convert to percentage and ensure it's within 0-100 range
        confidence = min(100.0, max(0.0, weighted_score * 100.0))
        
        return confidence
    
    @staticmethod
    def _calculate_data_completeness(
        patient_data: Dict[str, Any], clinical_data: Dict[str, Any]
    ) -> float:
        """
        Calculate a score (0-1) for the completeness of patient and clinical data.
        
        A higher score means more complete data, which should lead to higher confidence.
        """
        score = 0.0
        required_fields = 0
        
        # Check patient demographic fields
        patient_fields = ["age", "gender"]
        for field in patient_fields:
            required_fields += 1
            if field in patient_data and patient_data[field]:
                score += 1.0
        
        # Check vital signs
        vital_fields = ["hr", "rr", "bp", "temp", "o2"]
        for field in vital_fields:
            required_fields += 1
            if (
                "vital_signs" in clinical_data
                and field in clinical_data["vital_signs"]
                and clinical_data["vital_signs"][field]
            ):
                score += 1.0
        
        # Check clinical data
        clinical_fields = ["chief_complaint", "clinical_history"]
        for field in clinical_fields:
            required_fields += 1
            if field in clinical_data and clinical_data[field]:
                score += 1.0
        
        # Calculate percentage of required fields present
        return score / max(1, required_fields)
    
    @staticmethod
    def _calculate_clinical_clarity(clinical_data: Dict[str, Any]) -> float:
        """
        Calculate a score (0-1) for the clarity of clinical presentation.
        
        A clearer clinical picture leads to higher confidence in the recommendation.
        """
        score = 0.0
        total_points = 0
        
        # Check if chief complaint exists and is substantial
        if "chief_complaint" in clinical_data:
            total_points += 2
            complaint = clinical_data["chief_complaint"]
            if complaint and len(complaint) > 5:
                score += 1.0  # Basic complaint exists
                if len(complaint) > 20:
                    score += 1.0  # Detailed complaint
        
        # Check if clinical history exists and is substantial
        if "clinical_history" in clinical_data:
            total_points += 2
            history = clinical_data["clinical_history"]
            if history and len(history) > 10:
                score += 1.0  # Basic history exists
                if len(history) > 50:
                    score += 1.0  # Detailed history
        
        # Check vital signs completeness
        if "vital_signs" in clinical_data:
            vitals = clinical_data["vital_signs"]
            vital_fields = ["hr", "rr", "bp", "temp", "o2"]
            
            for field in vital_fields:
                total_points += 1
                if field in vitals and vitals[field]:
                    score += 1.0
        
        # Add points for suggested care level if it exists
        if "suggested_care_level" in clinical_data:
            total_points += 1
            score += 1.0
        
        # Calculate percentage
        return score / max(1, total_points)
    
    @staticmethod
    def _calculate_exclusion_clarity(exclusion_data: Optional[Dict[str, Any]]) -> float:
        """
        Calculate a score (0-1) for the clarity of exclusion criteria evaluation.
        
        Clear exclusion results lead to higher confidence in the recommendation.
        """
        if not exclusion_data:
            return 0.5  # Neutral score if no exclusion data
        
        score = 0.0
        total_points = 0
        
        # Check if exclusion criteria were evaluated
        if "exclusions_checked" in exclusion_data:
            exclusions = exclusion_data["exclusions_checked"]
            if exclusions:
                # Each evaluated exclusion adds to confidence
                total_points = len(exclusions)
                for exclusion in exclusions:
                    if "found" in exclusion:  # Clear result
                        score += 1.0
                    else:  # Unclear result
                        score += 0.5
        
        # If no exclusions were checked, use a neutral score
        if total_points == 0:
            return 0.5
        
        return score / total_points
    
    @staticmethod
    def _calculate_proximity_data(proximity_data: Optional[Dict[str, Any]]) -> float:
        """
        Calculate a score (0-1) for the quality of proximity/travel data.
        
        Better location and travel data leads to higher confidence.
        """
        if not proximity_data:
            return 0.3  # Below average score if no proximity data
        
        score = 0.0
        total_points = 0
        
        # Check for coordinates
        if "coordinates" in proximity_data:
            coords = proximity_data["coordinates"]
            total_points += 2
            if coords and "latitude" in coords and "longitude" in coords:
                score += 2.0
        
        # Check for address information
        if "addresses" in proximity_data:
            addresses = proximity_data["addresses"]
            total_points += 2
            if addresses:
                if "origin" in addresses and addresses["origin"]:
                    score += 1.0
                if "destination" in addresses and addresses["destination"]:
                    score += 1.0
        
        # Check for travel time estimates
        if "eta" in proximity_data:
            eta = proximity_data["eta"]
            total_points += 2
            if eta:
                if "minutes" in eta:
                    score += 1.0
                if "transport_mode" in eta:
                    score += 1.0
        
        # Check for traffic data
        if "traffic_report" in proximity_data:
            total_points += 1
            if proximity_data["traffic_report"]:
                score += 1.0
        
        # Check for weather data
        if "weather_report" in proximity_data:
            total_points += 1
            if proximity_data["weather_report"]:
                score += 1.0
        
        # If no proximity points were evaluated, use a low confidence
        if total_points == 0:
            return 0.3
        
        return score / total_points
    
    @staticmethod
    def _calculate_scoring_results(scoring_results: Optional[Dict[str, Any]]) -> float:
        """
        Calculate a score (0-1) based on the availability of pediatric scoring data.
        
        More scoring data leads to higher confidence in the recommendation.
        """
        if not scoring_results:
            return 0.3  # Below average score if no scoring data
        
        score = 0.0
        
        # Evaluate number of scoring systems used
        if "scores" in scoring_results:
            scores = scoring_results["scores"]
            num_scores = len(scores)
            
            # More scores = higher confidence, up to a maximum
            if num_scores >= 3:
                score = 1.0  # Full score for 3+ scoring systems
            elif num_scores == 2:
                score = 0.8  # Good score for 2 scoring systems
            elif num_scores == 1:
                score = 0.6  # Moderate score for 1 scoring system
            else:
                score = 0.3  # Low score for no scoring systems
            
            # Check score completeness
            complete_scores = 0
            for score_name, score_data in scores.items():
                # Check if score is numerical and has interpretation
                if isinstance(score_data.get("score"), (int, float)) and "interpretation" in score_data:
                    complete_scores += 1
            
            # Adjust score based on completeness
            if num_scores > 0:
                completeness_factor = complete_scores / num_scores
                score = score * (0.5 + 0.5 * completeness_factor)  # Weight completeness at 50%
        
        # Check for recommended care levels
        if "recommended_care_levels" in scoring_results and scoring_results["recommended_care_levels"]:
            score = min(1.0, score + 0.1)  # Small bonus for care level recommendations
        
        # Check for justifications
        if "justifications" in scoring_results and scoring_results["justifications"]:
            score = min(1.0, score + 0.1)  # Small bonus for justifications
        
        return score


def calculate_recommendation_confidence(
    recommendation_data: Dict[str, Any], 
    scoring_results: Optional[Dict[str, Any]] = None
) -> float:
    """
    Calculate a confidence score for a recommendation based on available data.
    
    This is a simplified wrapper around the ConfidenceEstimator class for easy integration.
    
    Args:
        recommendation_data: Dictionary containing recommendation details
        scoring_results: Optional dictionary containing pediatric scoring results
        
    Returns:
        Confidence score as a percentage (0-100)
    """
    # Extract necessary data components
    patient_data = recommendation_data.get("patient_demographics", {})
    
    clinical_data = {
        "chief_complaint": recommendation_data.get("chief_complaint", ""),
        "clinical_history": recommendation_data.get("clinical_history", ""),
        "vital_signs": recommendation_data.get("extracted_vital_signs", {}),
        "suggested_care_level": recommendation_data.get("care_level_assessment", {}).get("recommended_level", ""),
    }
    
    exclusion_data = recommendation_data.get("exclusion_criteria", {})
    
    # Check if travel_data exists in the recommendation
    proximity_data = None
    if "recommended_campus" in recommendation_data:
        campus_data = recommendation_data["recommended_campus"]
        if isinstance(campus_data, dict) and "travel_data" in campus_data:
            proximity_data = campus_data["travel_data"]
    
    # Extract campus match score if available
    campus_match_score = None
    if "recommended_campus" in recommendation_data:
        campus_data = recommendation_data["recommended_campus"]
        # Handle different possible data structures
        if isinstance(campus_data, dict):
            # Try to find scores in different potential locations
            if "scores" in campus_data:
                campus_scores = campus_data["scores"]
                if isinstance(campus_scores, dict) and "location" in campus_scores:
                    campus_match_score = campus_scores["location"]
            # Also try primary scores structure
            elif "primary" in campus_data and isinstance(campus_data["primary"], dict):
                primary = campus_data["primary"]
                if "location" in primary:
                    campus_match_score = primary["location"]
    
    # Calculate confidence
    return ConfidenceEstimator.calculate_confidence(
        patient_data=patient_data,
        clinical_data=clinical_data,
        exclusion_data=exclusion_data,
        proximity_data=proximity_data,
        scoring_results=scoring_results,
        campus_match_score=campus_match_score,
    )
