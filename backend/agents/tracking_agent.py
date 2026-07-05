from firebase_admin import firestore
from datetime import datetime
from backend.gemini_client import generate_text

class TrackingAgent:
    """
    AGENT 6: Tracking Agent
    
    Handles everything AFTER a complaint is filed:
    - Status updates when officials act
    - Progress updates visible to public
    - Outcome verification after resolution
    - Re-opens complaints if problem persists
    """
    
    def __init__(self):
        self.db = firestore.client()
    
    async def update_status(self,
                             complaint_id: str,
                             new_status: str,
                             update_note: str,
                             updated_by: str) -> dict:
        """
        Called when an official updates complaint status
        
        Statuses:
        submitted → under_review → in_progress → resolved
        """
        
        valid_statuses = [
            'submitted', 'under_review', 
            'in_progress', 'resolved', 'disputed'
        ]
        
        if new_status not in valid_statuses:
            return {"success": False, "error": "Invalid status"}
        
        try:
            # Create progress update record
            progress_entry = {
                "status": new_status,
                "note": update_note,
                "updated_by": updated_by,
                "timestamp": datetime.now().isoformat()
            }
            
            # Update in Firebase
            complaint_ref = self.db.collection('complaints').document(
                complaint_id
            )
            
            update_data = {
                "status": new_status,
                "last_updated": datetime.now().isoformat(),
                "progress_updates": firestore.ArrayUnion([progress_entry])
            }
            
            # If resolved, add resolution timestamp
            if new_status == "resolved":
                update_data["resolved_at"] = datetime.now().isoformat()
                update_data["outcome_verified"] = "pending"
            
            complaint_ref.update(update_data)
            
            return {
                "success": True,
                "complaint_id": complaint_id,
                "new_status": new_status,
                "message": f"Status updated to {new_status}",
                "progress_entry": progress_entry
            }
            
        except Exception as e:
            print(f"  [Tracking] Update error: {e}")
            return {"success": False, "error": str(e)}
    
    async def verify_outcome(self, complaint_id: str) -> dict:
        """
        Called 7 days after resolution to check if
        the problem was actually fixed.
        
        Checks:
        1. Has the same location filed a new similar complaint?
        2. If yes → mark as disputed and reopen
        """
        
        try:
            doc = self.db.collection('complaints').document(
                complaint_id
            ).get()
            
            if not doc.exists:
                return {"error": "Complaint not found"}
            
            data = doc.to_dict()
            location = data.get('location', '')
            issue_type = data.get('issue_type', '')
            resolved_at = data.get('resolved_at')
            
            # Check for re-complaints at same location
            recent_complaints = self.db.collection('complaints').where(
                filter=firestore.FieldFilter('issue_type', '==', issue_type)
            ).where(
                filter=firestore.FieldFilter('status', '!=', 'resolved')
            ).limit(10).stream()
            
            re_complaint_found = False
            for rc in recent_complaints:
                rc_data = rc.to_dict()
                if (rc.id != complaint_id and 
                        rc_data.get('location', '').lower() 
                        in location.lower()):
                    re_complaint_found = True
                    break
            
            if re_complaint_found:
                # Problem not actually fixed - reopen
                self.db.collection('complaints').document(
                    complaint_id
                ).update({
                    "status": "disputed",
                    "outcome_verified": "failed",
                    "outcome_note": (
                        "New complaint filed for same issue at same location. "
                        "Resolution disputed. Case reopened."
                    )
                })
                
                return {
                    "complaint_id": complaint_id,
                    "outcome": "disputed",
                    "message": "Resolution disputed - same issue re-reported",
                    "action": "Case reopened automatically"
                }
            else:
                # No re-complaint = likely fixed
                self.db.collection('complaints').document(
                    complaint_id
                ).update({
                    "outcome_verified": "success",
                    "outcome_note": (
                        "No re-complaints detected. "
                        "Resolution likely successful."
                    )
                })
                
                return {
                    "complaint_id": complaint_id,
                    "outcome": "verified",
                    "message": "Resolution verified successful",
                    "action": "Case closed"
                }
                
        except Exception as e:
            print(f"  [Tracking] Verify error: {e}")
            return {"error": str(e)}
    
    async def get_public_status(self, complaint_id: str) -> dict:
        """
        What citizens see when they check their complaint status
        Shows progress without exposing internal AI data
        """
        
        try:
            doc = self.db.collection('complaints').document(
                complaint_id
            ).get()
            
            if not doc.exists:
                # Check emergencies
                doc = self.db.collection('emergencies').document(
                    complaint_id
                ).get()
                if not doc.exists:
                    return {"error": "Complaint ID not found"}
            
            data = doc.to_dict()
            
            # Status messages in citizen-friendly language
            status_messages = {
                "submitted": "✅ Your complaint has been received and is being reviewed.",
                "under_review": "🔍 Officials are reviewing your complaint.",
                "in_progress": "🔧 Work is in progress to fix this issue.",
                "resolved": "✅ Your issue has been resolved.",
                "disputed": "🔄 Your complaint has been reopened for further review.",
                "EMERGENCY - IMMEDIATE ACTION REQUIRED": (
                    "🚨 Emergency services have been alerted immediately."
                )
            }
            
            current_status = data.get('status', 'submitted')
            
            return {
                "complaint_id": complaint_id,
                "status": current_status,
                "message": status_messages.get(
                    current_status, 
                    "Your complaint is being processed."
                ),
                "department": data.get('department'),
                "priority": data.get('priority_level'),
                "filed_on": data.get('created_at'),
                "last_updated": data.get('last_updated'),
                "progress_updates": data.get('progress_updates', []),
                "resolved_on": data.get('resolved_at'),
                "outcome": data.get('outcome_verified')
            }
            
        except Exception as e:
            return {"error": str(e)}


tracking_agent = TrackingAgent()