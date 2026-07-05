from firebase_admin import firestore
from datetime import datetime
from backend.gemini_client import generate_text

class FeedbackAgent:
    """
    AGENT 7: Feedback Agent
    
    After a complaint is resolved:
    1. Citizen rates the service (1-5 stars)
    2. Ratings display publicly
    3. Generates department performance insights
    """
    
    def __init__(self):
        self.db = firestore.client()
    
    async def submit_feedback(self,
                               complaint_id: str,
                               rating: int,
                               comment: str,
                               citizen_name: str) -> dict:
        """
        Called when citizen submits feedback after resolution
        """
        
        if rating < 1 or rating > 5:
            return {"success": False, "error": "Rating must be 1-5"}
        
        try:
            # Get the original complaint
            doc = self.db.collection('complaints').document(
                complaint_id
            ).get()
            
            if not doc.exists:
                return {"success": False, "error": "Complaint not found"}
            
            complaint_data = doc.to_dict()
            
            # Save feedback
            feedback_record = {
                "complaint_id": complaint_id,
                "department": complaint_data.get('department'),
                "location": complaint_data.get('location'),
                "issue_type": complaint_data.get('issue_type'),
                "rating": rating,
                "comment": comment,
                "citizen_name": citizen_name,
                "submitted_at": datetime.now().isoformat()
            }
            
            # Save to feedback collection
            self.db.collection('feedback').add(feedback_record)
            
            # Update the complaint with feedback
            self.db.collection('complaints').document(
                complaint_id
            ).update({
                "citizen_rating": rating,
                "citizen_comment": comment,
                "feedback_received": True
            })
            
            # Generate thank you message
            stars = "⭐" * rating
            messages = {
                5: "Thank you! We're glad we could help quickly.",
                4: "Thank you for your feedback! We're always improving.",
                3: "Thank you. We'll work on improving our response time.",
                2: "We apologize for the experience. Your feedback helps us improve.",
                1: "We sincerely apologize. This feedback has been escalated to management."
            }
            
            return {
                "success": True,
                "message": messages.get(rating, "Thank you for your feedback!"),
                "stars": stars,
                "rating": rating
            }
            
        except Exception as e:
            print(f"  [Feedback] Error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_department_ratings(self, department: str = None) -> dict:
        """
        Get average ratings - shown on public dashboard
        Officials see this to track performance
        """
        
        try:
            feedback_ref = self.db.collection('feedback')
            
            if department:
                query = feedback_ref.where(
                    filter=firestore.FieldFilter(
                        'department', '==', department
                    )
                )
            else:
                query = feedback_ref
            
            docs = query.limit(100).stream()
            
            # Calculate ratings per department
            dept_ratings = {}
            
            for doc in docs:
                data = doc.to_dict()
                dept = data.get('department', 'other')
                rating = data.get('rating', 0)
                
                if dept not in dept_ratings:
                    dept_ratings[dept] = {
                        "total": 0,
                        "count": 0,
                        "comments": []
                    }
                
                dept_ratings[dept]["total"] += rating
                dept_ratings[dept]["count"] += 1
                if data.get('comment'):
                    dept_ratings[dept]["comments"].append(
                        data.get('comment')
                    )
            
            # Calculate averages
            result = {}
            for dept, data in dept_ratings.items():
                if data["count"] > 0:
                    avg = round(data["total"] / data["count"], 1)
                    result[dept] = {
                        "average_rating": avg,
                        "total_responses": data["count"],
                        "stars": "⭐" * round(avg),
                        "recent_comments": data["comments"][-3:]
                    }
            
            return {
                "success": True,
                "department_ratings": result,
                "total_feedback": sum(
                    d["count"] for d in dept_ratings.values()
                )
            }
            
        except Exception as e:
            print(f"  [Feedback] Ratings error: {e}")
            return {"success": False, "error": str(e)}


feedback_agent = FeedbackAgent()