from backend.gemini_client import generate_text
from firebase_admin import firestore

class QueryAgent:
    """
    AGENT 8: Query Agent (your Doubt Agent)
    
    Answers citizen questions like:
    - "Where is the water department office?"
    - "How do I apply for a new electricity connection?"
    - "What is the status of complaint #XYZ123?"
    - "How long does road repair usually take?"
    
    Uses built-in knowledge + Firebase complaint data
    """
    
    def __init__(self):
        self.db = firestore.client()
        
        # Built-in government knowledge base
        # In real version this comes from RAG over documents
        self.knowledge_base = """
CIVIC SERVICES INFORMATION:

WATER DEPARTMENT:
- New connection: Apply online at city portal, takes 7-14 days
- Complaint: File online or call helpline, response within 24 hours
- Low pressure: Usually resolved within 48 hours
- Pipeline leak: Emergency response within 2 hours

ROADS DEPARTMENT:
- Pothole repair: Minor repairs 3-7 days, major repairs 14-30 days
- Road works complaint: Response within 48 hours
- Emergency road collapse: Immediate response

ELECTRICITY DEPARTMENT:
- Power outage: Report to city helpline, restoration within 4-8 hours
- New connection: 15-30 days processing
- Meter complaint: Inspection within 7 days
- Streetlight: Repair within 48-72 hours
- Electricity issues will be inspected within 2 days and appropriate action will be taken

GENERAL:
- All complaints receive a complaint ID for tracking
- Citizens can check status using their complaint ID
- Emergency issues are escalated within 1 hour
- Working hours: Monday to Saturday, 9am to 6pm
- Emergency helpline available 24/7
"""
    
    async def answer(self, 
                     question: str,
                     complaint_id: str = None) -> dict:
        """
        Answers citizen questions
        """
        
        # If they're asking about a specific complaint
        if complaint_id or any(
            word in question.lower() 
            for word in ['status', 'complaint', 'my issue', 'track']
        ):
            return await self._handle_status_query(
                question, complaint_id
            )
        
        # General question - answer from knowledge base
        return await self._answer_general(question)
    
    async def _handle_status_query(self,
                                    question: str,
                                    complaint_id: str = None) -> dict:
        
        if complaint_id:
            try:
                doc = self.db.collection('complaints').document(
                    complaint_id
                ).get()
                
                if doc.exists:
                    data = doc.to_dict()
                    
                    prompt = f"""
A citizen is asking about their complaint. Answer helpfully.

CITIZEN QUESTION: "{question}"

COMPLAINT DETAILS:
- ID: {complaint_id}
- Problem: {data.get('specific_problem')}
- Status: {data.get('status')}
- Department: {data.get('department')}
- Priority: {data.get('priority_level')}
- Filed on: {data.get('created_at')}
- Progress: {data.get('progress_updates', [])}

Write a friendly, clear response in maximum of 2-3 sentences.
Tell them the current status and what to expect next.
"""
                    answer = generate_text(prompt)
                    return {
                        "answer": answer.strip(),
                        "complaint_id": complaint_id,
                        "status": data.get('status'),
                        "source": "complaint_database"
                    }
            except:
                pass
        
        return {
            "answer": (
                "I couldn't find that complaint ID. "
                "Please check the ID and try again, or contact "
                "the helpline for assistance."
            ),
            "source": "system"
        }
    
    async def _answer_general(self, question: str) -> dict:
        
        prompt = f"""
You are a helpful assistant for a city civic services platform.

Use this information to answer the citizen's question:

{self.knowledge_base}

CITIZEN QUESTION: "{question}"

Give a clear, friendly answer in 2-3 sentences.
If their question is out of the context, direct them to contact
the relevant department's helpline.
Do not make up specific phone numbers or addresses.
"""
        
        try:
            answer = generate_text(prompt)
            return {
                "answer": answer.strip(),
                "source": "knowledge_base"
            }
        except Exception as e:
            return {
                "answer": (
                    "I'm sorry, I couldn't process your question right now. "
                    "Please contact your city's helpline for assistance."
                ),
                "source": "fallback",
                "error": str(e)
            }


query_agent = QueryAgent()