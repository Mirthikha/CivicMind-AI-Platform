from backend.gemini_client import generate_text

class ExplainabilityAgent:
    """
    AGENT 4: Explainability Agent
    
    EVERY decision shown to officials passes through here.
    
    Job: Turn AI analysis into plain English that any
    government official can understand and trust.
    
    This builds TRUST in the system.
    Without this, officials won't use AI recommendations.
    """
    
    async def explain(self,
                       intake_result: dict,
                       intelligence_result: dict,
                       priority_score: float) -> dict:
        
        root_cause = intelligence_result.get('root_cause', {})
        cross_links = intelligence_result.get('cross_dept_links', {})
        cluster_size = intelligence_result.get('cluster_size', 1)
        
        prompt = f"""
You are explaining an AI decision to a government official.
Be clear, factual, and specific. No technical jargon.

WHAT THE SYSTEM FOUND:
- Problem reported: {intake_result.get('specific_problem')}
- Location: {intake_result.get('location')}
- Severity: {intake_result.get('severity')} ({intake_result.get('severity_score')}/10)
- Related complaints in this area: {cluster_size}
- Departments that need to respond: {intelligence_result.get('departments_involved')}
- Root cause hypothesis: {root_cause.get('root_cause')}
- AI confidence in this analysis: {root_cause.get('confidence', 0.7)}
- Risk if ignored: {root_cause.get('failure_risk')}
- Priority score assigned: {priority_score}/10

Write a SHORT explanation (3-4 sentences) for the official that:
1. States clearly what problem was found and where
2. Explains WHY it got this priority level  
3. Mentions which departments must coordinate (if multiple)
4. States what should happen next

Write simply. Imagine explaining to a busy city manager.
"""
        
        try:
            explanation_text = generate_text(prompt)
            
            # Confidence level in plain English
            confidence = root_cause.get('confidence', 0.7)
            if confidence >= 0.85:
                confidence_label = "High confidence"
                confidence_color = "green"
            elif confidence >= 0.65:
                confidence_label = "Moderate confidence"
                confidence_color = "yellow"
            else:
                confidence_label = "Low confidence — human review recommended"
                confidence_color = "red"
            
            return {
                "explanation": explanation_text.strip(),
                "confidence_label": confidence_label,
                "confidence_color": confidence_color,
                "confidence_value": confidence,
                "key_evidence": root_cause.get('evidence', ''),
                "recommended_action": root_cause.get('recommended_action', ''),
                "prediction_if_ignored": root_cause.get('prediction', ''),
                "failure_risk": root_cause.get('failure_risk', 'medium'),
                "departments_must_act": intelligence_result.get(
                    'departments_involved', []
                ),
                "cross_dept_alert": cross_links.get('linked', False)
            }
            
        except Exception as e:
            print(f"  [Explainability] Error: {e}")
            return {
                "explanation": (
                    f"Complaint filed about {intake_result.get('specific_problem')} "
                    f"at {intake_result.get('location')}. "
                    f"Priority level: {priority_score}/10. "
                    f"Assigned to {intake_result.get('department')} department."
                ),
                "confidence_label": "Analysis unavailable",
                "confidence_color": "grey",
                "confidence_value": 0.5,
                "key_evidence": "",
                "recommended_action": "Manual review required",
                "prediction_if_ignored": "Unknown",
                "failure_risk": "medium",
                "departments_must_act": [intake_result.get('department')],
                "cross_dept_alert": False
            }


explainability_agent = ExplainabilityAgent()