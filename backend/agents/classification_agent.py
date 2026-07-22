import json
from backend.gemini_client import generate_text, generate_with_image

class ClassificationAgent:

    def __init__(self):
        self.emergency_keywords = [
            "gas leak", "gas smell", "fire", "burning",
            "flood", "flooding", "collapse", "collapsed",
            "explosion", "electric shock", "electrocution",
            "trapped", "building collapse", "road collapse",
            "sinkhole", "unconscious"
        ]
    
    async def classify(self, complaint_text: str, image_bytes: bytes = None) -> dict:
        
        # ── PATH A: KEYWORD CHECK ──
        if not image_bytes:
            text_lower = complaint_text.lower()
            for keyword in self.emergency_keywords:
                if keyword in text_lower:
                    return {
                        "type": "EMERGENCY", 
                        "reason": f"Emergency keyword detected: '{keyword}'",
                        "confidence": 0.98,
                        "method": "keyword_detection"
                    }
        
        # ── PATH B: AI MULTIMODAL / TEXT CLASSIFICATION ──
        prompt = f"""
You are the primary automated operational triage gateway for a municipal governance platform.
Your single responsibility is to analyze the provided input data streams and classify the ticket into a precise emergency tier.

[INPUT AVAILABILITY]
- You are receiving a text segment containing the citizen's description.
- You may also receive an accompanying image asset passed directly within the multimodal content stream.

[OPERATIONAL TAXONOMY & DECISION MATRIX]
1. EMERGENCY: An active, unfolding incident presenting an immediate, direct threat to human life RIGHT NOW. 
   - Exclusively limited to: active structural or building fires, catastrophic building or road collapses, major sinkholes, flash flooding actively trapping citizens or vehicles, uncontrolled gas leaks/vapors, or exposed high-voltage live electrical infrastructure.
2. NORMAL: Standard civic infrastructure degradation, maintenance requirements, public nuisances, or service disruptions.
   - Includes: Standard potholes, road defects, uncollected refuse, non-functional streetlights, or static municipal water supply latency.

[CRITICAL MULTIMODAL CONSTRAINTS]
- A maintenance defect (e.g., a deep pothole or dark street) is strictly NORMAL, regardless of emotional distress expressed in the text.
- VISUAL OVERRIDE STRATEGY: If an image is present, analyze the visual telemetry thoroughly alongside the text. If the text description is vague or ambiguous (e.g., "look at this", "help me"), but the image displays an active, undeniable life-threatening incident listed under EMERGENCY, you MUST classify the ticket as EMERGENCY.
- If the inputs consist of irrelevant content, gibberish, or empty data, classify the ticket as NORMAL and specify the irrelevance in the reason string.

CITIZEN TEXT DESCRIPTION: "{complaint_text}"

[OUTPUT FORMAT]
You must respond with a single valid JSON object matching this schema exactly. Do not output any conversational text, markdown formatting, or trailing data outside the JSON structure.

{{
    "type": "EMERGENCY",
    "reason": "A singular, objective sentence explaining the specific presence of an immediate life threat based on text/visual evidence.",
    "confidence_score": 1.0
}}
"""
        
        try:
            # Dynamically route based on whether visual data is present
            if image_bytes:
                result_text = generate_with_image(prompt, image_bytes)
                method_used = "ai_multimodal_classification"
            else:
                result_text = generate_text(prompt)
                method_used = "ai_text_classification"
            
            # Clean JSON formatting block if Gemini wraps it in markdown backticks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(result_text.strip())
            
            return {
                "type": str(data.get("type", "NORMAL")).strip().upper(), 
                "reason": data.get("reason", "Processed via AI engine."),
                "confidence": float(data.get("confidence_score", 0.85)),
                "method": method_used
            }
            
        except Exception as e:
            print(f"Classification error: {e}")
            return {
                "type": "normal",
                "reason": "Classification engine exception, defaulted securely to normal path.",
                "confidence": 0.50,
                "method": "fallback"
            }

classification_agent = ClassificationAgent()