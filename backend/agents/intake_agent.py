from backend.gemini_client import generate_text, generate_with_image

class IntakeAgent:
    """
    AGENT 2: Intake Agent
    Reads raw complaint (text + optional photo)
    Extracts clean structured information
    """
    
    async def process(self,
                      complaint_text: str,
                      location: str,
                      image_bytes: bytes = None) -> dict:
        
        if image_bytes:
            return await self._process_with_image(
                complaint_text, location, image_bytes
            )
        else:
            return await self._process_text_only(
                complaint_text, location
            )
    
    async def _process_text_only(self, text: str, location: str) -> dict:
        
        # Change the prompt definition inside _process_text_only to this:
        prompt = f"""
You are an intake officer for a city civic complaint system.

Extract structured information from this citizen complaint.

COMPLAINT: "{text}"
LOCATION: "{location}"

STRICT ROUTING RULES:
- If the text mentions "pothole", "road", "street", "tarmac", or "asphalt", you MUST set DEPARTMENT to Roads.
- If the text mentions "leak", "pipe", "water", "drainage", or "sewer", you MUST set DEPARTMENT to Water.

Reply in EXACTLY this format, one per line:
ISSUE_TYPE: water or road or electricity or sanitation or other
SEVERITY: low or medium or high
SPECIFIC_PROBLEM: one clear sentence describing the exact problem
AFFECTED_AREA: where exactly is this problem
DEPARTMENT: Water or Roads or Electricity or other
URGENCY_HOURS: number only - hours before this becomes critical
SEVERITY_SCORE: number 1-10 only
PEOPLE_AFFECTED: estimated number of people affected
"""
        
        try:
            response_text = generate_text(prompt)
            return self._parse(response_text, text, location, False)
        except Exception as e:
            print(f"Intake error: {e}")
            return self._default(text, location)
    
    async def _process_with_image(self,
                                   text: str,
                                   location: str,
                                   image_bytes: bytes) -> dict:
        # Change the prompt definition inside _process_with_image to this:
        prompt = f"""
You are an intake officer for a city civic complaint system.

A citizen sent a complaint WITH a photo.
Look at the image AND read the text.

COMPLAINT TEXT: "{text}"
LOCATION: "{location}"

STRICT ROUTING RULES:
- If the text or image shows a "pothole", "road", "street", "tarmac", or "asphalt", you MUST set DEPARTMENT to Roads.
- If the text or image shows a "leak", "pipe", "water", "drainage", or "sewer", you MUST set DEPARTMENT to Water.

Reply in EXACTLY this format:
IMAGE_OBSERVATION: what damage or problem you see in the photo
ISSUE_TYPE: water or road or electricity or sanitation or other
SEVERITY: low or medium or high
SPECIFIC_PROBLEM: describe combining what you see and what they wrote
AFFECTED_AREA: where is this problem
DEPARTMENT: Water or Roads or Electricity or other
URGENCY_HOURS: number only
SEVERITY_SCORE: number 1-10 only
PEOPLE_AFFECTED: estimated number only
"""
        
        try:
            response_text = generate_with_image(prompt, image_bytes)
            return self._parse(response_text, text, location, True)
        except Exception as e:
            print(f"Vision error: {e}")
            return await self._process_text_only(text, location)
    
    def _parse(self, response_text, original, location, has_image):
        result = self._default(original, location)
        result["has_image"] = has_image
        
        for line in response_text.strip().split('\n'):
            line = line.strip()
            if ':' not in line:
                continue
            key, _, value = line.partition(':')
            key = key.strip().upper()
            value = value.strip()
            
            if key == "ISSUE_TYPE":
                result["issue_type"] = value.lower()
            elif key == "SEVERITY" and "SCORE" not in key:
                result["severity"] = value.lower()
            elif key == "SPECIFIC_PROBLEM":
                result["specific_problem"] = value
            elif key == "AFFECTED_AREA":
                result["affected_area"] = value
            elif key == "DEPARTMENT":
                result["department"] = value.strip().capitalize()
            elif key == "URGENCY_HOURS":
                try:
                    result["urgency_hours"] = int(value)
                except:
                    pass
            elif key == "SEVERITY_SCORE":
                try:
                    result["severity_score"] = int(value)
                except:
                    pass
            elif key == "PEOPLE_AFFECTED":
                try:
                    result["people_affected"] = int(value)
                except:
                    pass
            elif key == "IMAGE_OBSERVATION":
                result["image_observation"] = value
        
        return result
    
    def _default(self, text, location):
        return {
            "original_complaint": text,
            "location": location,
            "has_image": False,
            "issue_type": "other",
            "severity": "medium",
            "specific_problem": text,
            "affected_area": location,
            "department": "other",
            "urgency_hours": 48,
            "severity_score": 5,
            "people_affected": 10,
            "image_observation": None
        }


intake_agent = IntakeAgent()