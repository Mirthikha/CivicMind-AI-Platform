from backend.gemini_client import generate_text

class ClassificationAgent:
    """
    AGENT 1: Classification Agent
    First agent that runs for every complaint.
    Decides: EMERGENCY or NORMAL
    """
    
    def __init__(self):
        self.emergency_keywords = [
            "gas leak", "gas smell", "fire", "burning",
            "flood", "flooding", "collapse", "collapsed",
            "explosion", "electric shock", "electrocution",
            "trapped", "building collapse", "road collapse",
            "sinkhole", "unconscious"
        ]
    
    async def classify(self, complaint_text: str) -> dict:
        
        # Step 1: Check keywords first (instant, no AI needed)
        text_lower = complaint_text.lower()
        for keyword in self.emergency_keywords:
            if keyword in text_lower:
                return {
                    "type": "emergency",
                    "reason": f"Emergency keyword detected: '{keyword}'",
                    "confidence": 0.98,
                    "method": "keyword_detection"
                }
        
        # Step 2: Ask Gemini for unclear cases
        prompt = f"""
You are a classification system for a city civic complaint platform.

Read this complaint and classify it as EMERGENCY or NORMAL.

EMERGENCY = Immediate threat to human life RIGHT NOW.
Only these qualify: gas leaks, fires, building collapse, 
flooding trapping people, live electrical wires touching people.

A pothole, broken streetlight, garbage, or water supply issue
is NEVER an emergency even if it caused past accidents.

NORMAL = Important problem but not immediately dangerous.
Examples: potholes, garbage, broken streetlight, water supply issue.

CITIZEN COMPLAINT: "{complaint_text}"

Reply in EXACTLY this format, nothing else:
TYPE: EMERGENCY or NORMAL
REASON: one sentence why
CONFIDENCE: number between 0.0 and 1.0
"""
        
        try:
            result_text = generate_text(prompt)
            lines = result_text.strip().split('\n')
            
            complaint_type = "normal"
            reason = "Standard civic complaint"
            confidence = 0.80
            
            for line in lines:
                line = line.strip()
                if line.startswith("TYPE:"):
                    value = line.replace("TYPE:", "").strip().upper()
                    complaint_type = "emergency" if "EMERGENCY" in value else "normal"
                elif line.startswith("REASON:"):
                    reason = line.replace("REASON:", "").strip()
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(
                            line.replace("CONFIDENCE:", "").strip()
                        )
                    except:
                        confidence = 0.80
            
            return {
                "type": complaint_type,
                "reason": reason,
                "confidence": confidence,
                "method": "ai_classification"
            }
            
        except Exception as e:
            print(f"Classification error: {e}")
            return {
                "type": "normal",
                "reason": "Classification unavailable, defaulted to normal",
                "confidence": 0.50,
                "method": "fallback"
            }


classification_agent = ClassificationAgent()