"""
CivicMind - Main FastAPI Application
This is the entry point that connects all agents to the web.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import pytz
from typing import Optional

IST = pytz.timezone('Asia/Kolkata')

load_dotenv()

# ─────────────────────────────────────────
# Initialize Firebase
# ─────────────────────────────────────────
if not firebase_admin._apps:
    # 1. Try Render's absolute secure container path first
    cred_path = "/etc/secrets/firebase_credentials.json"
    
    # 2. If not there, check the root project directory (where Render drops non-Docker secrets)
    if not os.path.exists(cred_path):
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cred_path = os.path.join(BASE_DIR, "firebase_credentials.json")
        
    # 3. Local fallback: check inside the backend directory itself
    if not os.path.exists(cred_path):
        cred_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "firebase_credentials.json"
        )
        
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

    db = firestore.client()

# ─────────────────────────────────────────
# Import All Agents
# ─────────────────────────────────────────
from agents.classification_agent import classification_agent
from agents.intake_agent import intake_agent
from agents.intelligence_agent import intelligence_agent
from agents.prioritization_agent import prioritization_agent
from agents.explainability_agent import explainability_agent
from agents.tracking_agent import tracking_agent
from agents.feedback_agent import feedback_agent
from agents.query_agent import query_agent
from gemini_client import generate_text
from agents.self_correction_agent import self_correction_agent

# ─────────────────────────────────────────
# Create FastAPI App
# ─────────────────────────────────────────
app = FastAPI(
    title="CivicMind API",
    description="AI-powered civic complaint intelligence platform",
    version="1.0.0"
)

# Allow React frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════
# AUTHENTICATION MOCKS (To support React login/registration)
# ═══════════════════════════════════════════════════════

@app.post("/api/auth/citizen-register")
async def citizen_register(registration_data: dict):
    email = registration_data.get("email")
    name = registration_data.get("name", "Citizen")
    phone = registration_data.get("phone", "")
    
    user_record = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "phone": phone
    }
    
    # Save the registered citizen details to your Firestore database
    db.collection('citizens').document(email).set(user_record)
    
    return {"user": user_record}

@app.post("/api/auth/citizen-login")
async def citizen_login(credentials: dict):
    email = credentials.get("email")
    
    # 1. Search for the user doc in your Firestore collection
    user_doc = db.collection('citizens').document(email).get()
    
    # 2. If it does NOT exist, stop the request and send a clear message back
    if not user_doc.exists:
        raise HTTPException(
            status_code=401, 
            detail="This email is not registered. Please create an account first!"
        )
    
    # 3. If it does exist, allow them in with their real database data
    user_data = user_doc.to_dict()
    return {"user": user_data}

@app.post("/api/auth/official-login")
async def official_login(credentials: dict):
    email = credentials.get("email", "").lower().strip()
    
    # Strictly determine department based on the test email accounts
    if "water" in email:
        dept = "Water Department"
    elif "road" in email or "roads" in email:
        dept = "Roads Department"
    elif "elec" in email or "electric" in email:
        dept = "Electricity Department"
    else:
        dept = "All Departments"
    
    return {
        "user": {
            "name": "City Official",
            "role": "official",
            "department": dept,
            "email": email
        }
    }

@app.get("/api/auth/citizen-complaints/{citizen_id}")
async def get_citizen_complaints(citizen_id: str):
    try:
        # Filter where the citizen_contact matches the logged-in citizen's identifier
        docs = db.collection('complaints').where(
            filter=firestore.FieldFilter('citizen_contact', '==', citizen_id)
        ).limit(10).stream()
        
        complaints = [doc.to_dict() for doc in docs]
        return {"complaints": complaints}
        
    except Exception as e:
        # Fallback to empty list or search by citizen_name if needed
        print(f"[Backend] Error filtering complaints: {e}")
        return {"complaints": []}

# ═══════════════════════════════════════════════════════
# PUBLIC ENDPOINTS (Citizens use these)
# ═══════════════════════════════════════════════════════

@app.post("/api/complaints/submit")
async def submit_complaint(
    complaint_text: str = Form(...),
    location: str = Form(...),
    citizen_name: str = Form(...),
    citizen_contact: str = Form(...),
    image: UploadFile = File(None)
):
    """
    Main endpoint - citizen submits a complaint.
    Runs through all agents and saves to Firebase.
    """
    try:
        # Read image if provided
        image_bytes = None
        if image and image.filename:
            image_bytes = await image.read()

        # Generate unique complaint ID
        complaint_id = "CM" + str(uuid.uuid4())[:6].upper()

        # ── AGENT 1: Classification ──
        classification = await self_correction_agent.execute_with_correction(
            "ClassificationAgent",
            classification_agent.classify,
            complaint_text,
            image_bytes,
            required_keys=["type"]
        )

        if classification.get("_fallback_used"):
            classification = await classification_agent.classify(complaint_text, image_bytes)

        # ── EMERGENCY PATH ──
        if str(classification.get("type", "")).upper() == "EMERGENCY":
            emergency_record = {
                "id": complaint_id,
                "complaint_id": complaint_id,
                "type": "emergency",
                "original_complaint": complaint_text,
                "problem": complaint_text,
                "location": location,
                "citizen_name": citizen_name,
                "citizen_contact": citizen_contact,
                "classification_reason": classification.get("reason", "Life-threatening incident detected."),
                "status": "emergency_escalated",
                "priority_level": "critical",
                "priority_score": 999,
                "color_code": "red",
                "department": "Emergency",
                "created_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
            }

            # 1. Save into 'emergencies' collection for emergency banners
            db.collection('emergencies').document(complaint_id).set(emergency_record)

            # 2. ALSO save into 'complaints' collection so citizen tracking and official queries find it!
            db.collection('complaints').document(complaint_id).set(emergency_record)

            return JSONResponse({
                "success": True,
                "complaint_id": complaint_id,
                "type": "emergency",
                "message": "🚨 Emergency detected! Officials have been alerted immediately.",
                "status": "emergency_escalated"
            })

        # ── NORMAL PATH ──

        # ── AGENT 2: Intake ──
        intake = await self_correction_agent.execute_with_correction(
            "IntakeAgent",
            intake_agent.process,
            complaint_text,
            location,
            image_bytes,
            required_keys=["department", "specific_problem", "severity_score"]
        )

        if intake.get("_fallback_used"):
            intake = await intake_agent.process(complaint_text, location, image_bytes)

        # ── AGENT 3: Intelligence ──
        intelligence = await self_correction_agent.execute_with_correction(
            "IntelligenceAgent",
            intelligence_agent.analyze,
            intake,
            required_keys=["root_cause"]
        )
        if intelligence.get("_fallback_used"):
            intelligence = await intelligence_agent.analyze(intake)

        # Handle duplicate
        if intelligence.get("is_duplicate"):
            dup_id = intelligence.get("duplicate_of")
            # Add this citizen to the existing complaint's cluster
            db.collection('complaints').document(dup_id).update({
                "cluster_size": firestore.Increment(1)
            })
            return JSONResponse({
                "success": True,
                "complaint_id": dup_id,
                "type": "duplicate",
                "message": (
                    "Your complaint matches an existing report. "
                    "We've added your report to strengthen the case."
                ),
                "status": "merged"
            })

        # ── AGENT 5: Prioritization ──
        priority_result = await self_correction_agent.execute_with_correction(
            "PrioritizationAgent",
            prioritization_agent.prioritize,
            intake,
            intelligence,
            required_keys=["priority_score", "priority_level", "budget"]
        )

        if priority_result.get("_fallback_used"):
            priority_result = await prioritization_agent.prioritize(intake, intelligence)

        # ── AGENT 4: Explainability ──
        p_score = priority_result.get("priority_score", 50) if isinstance(priority_result, dict) else 50
        explanation = await self_correction_agent.execute_with_correction(
            "ExplainabilityAgent",
            explainability_agent.explain,
            intake,
            intelligence,
            p_score,
            required_keys=["explanation"]
        )

        if explanation.get("_fallback_used"):
            explanation = await explainability_agent.explain(
                intake,
                intelligence,
                priority_result.get("priority_score", 50)
            )

        # ── BUILD COMPLETE RECORD ──
        budget = priority_result.get("budget", {})

        # Extract values with safe cross-agent fallbacks
        final_dept = classification.get("department") or intake.get("department") or "Other"
        final_dept = str(final_dept).strip().title() # Force matching title case (e.g. "Roads")

        final_priority = priority_result.get("priority_level") or classification.get("priority_level") or "Medium"
        final_priority = str(final_priority).strip().lower() # Force lowercase (e.g. "high")

        final_budget = budget.get("budget_range") or classification.get("budget_range") or "Under Review"

        # 🌟 Hardcoded fail-safe gate directly in the orchestrator script
        # If the text explicitly states a road pothole, guarantee it maps correctly
        lower_text = complaint_text.lower()
        if "pothole" in lower_text or "road damage" in lower_text:
            if final_dept == "Other" or not final_dept:
                final_dept = "Roads"
            if final_priority == "low":
                final_priority = "high"
            if final_budget == "Under Review":
                final_budget = "₹10,000 - ₹25,000"

        # Check self-correction telemetry
        any_corrected = (
            classification.get("_self_corrected", False) or
            intake.get("_self_corrected", False) or
            intelligence.get("_self_corrected", False) or
            priority_result.get("_self_corrected", False) or
            explanation.get("_self_corrected", False)
        )

        complaint_record = {
            # Identity
            "id": complaint_id,
            "type": "normal",
            "created_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
            "self_corrected": any_corrected,

            # Citizen info
            "citizen_name": citizen_name,
            "citizen_contact": citizen_contact,

            # Complaint content
            "original_complaint": complaint_text,
            "location": location,
            "has_image": image_bytes is not None,

            # Mapped Analytics Data Parameters
            "issue_type": intake.get("issue_type"),
            "severity": intake.get("severity"),
            "severity_score": intake.get("severity_score"),
            "specific_problem": intake.get("specific_problem"),
            "affected_area": intake.get("affected_area"),
            
            "department": final_dept,
            "priority_level": final_priority,
            "budget_range": final_budget,

            "urgency_hours": intake.get("urgency_hours"),
            "people_affected": intake.get("people_affected"),

            # Intelligence analysis
            "root_cause": intelligence.get("root_cause", {}),
            "cross_dept_links": intelligence.get("cross_dept_links", {}),
            "departments_involved": intelligence.get(
                "departments_involved", []
            ),
            "cluster_size": intelligence.get("cluster_size", 1),
            "fraud_flag": intelligence.get("fraud_flag", {}),

            # Priority
            "priority_score": priority_result.get("priority_score"),
            "priority_level": priority_result.get("priority_level"),
            "response_time_target": priority_result.get(
                "response_time_target"
            ),
            "color_code": priority_result.get("color_code"),
            "equity_flag": priority_result.get("equity_flag"),

            # Budget
            "budget_range": budget.get("budget_range"),
            "budget_min": budget.get("minimum_cost"),
            "budget_max": budget.get("maximum_cost"),
            "budget_immediate": budget.get("immediate_formatted"),
            "budget_permanent": budget.get("permanent_formatted"),
            "budget_timeline_days": budget.get("timeline_days"),
            "budget_justification": budget.get("cost_justification"),
            "budget_itemized": budget.get("itemized", []),

            # Explainability
            "explanation": explanation.get("explanation"),
            "explanation_text": explanation.get("explanation"),      
            "ai_explanation": explanation.get("explanation"),        
            "ai_reason": explanation.get("explanation"),

            "confidence_label": explanation.get("confidence_label"),
            "recommended_action": explanation.get("recommended_action"),
            "failure_risk": explanation.get("failure_risk"),

            # Status tracking
            "status": "submitted",
            "progress_updates": [],
            "resolved_at": None,
            "outcome_verified": None,
            "citizen_rating": None,
            "feedback_received": False,
            "last_updated": datetime.now().isoformat()
        }

        # Save to Firebase
        db.collection('complaints').document(
            complaint_id
        ).set(complaint_record)

        return JSONResponse({
            "success": True,
            "complaint_id": complaint_id,
            "type": "normal",
            "message": "Complaint submitted successfully!",
            "status": "submitted",
            "department": intake.get("department"),
            "priority": priority_result.get("priority_level"),
            "priority_score": priority_result.get("priority_score"),
            "budget_range": budget.get("budget_range"),
            "explanation": explanation.get("explanation"),
            "response_time": priority_result.get("response_time_target")
        })

    except Exception as e:
        print(f"[API] Submit error: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@app.get("/api/complaints/status/{complaint_id}")
async def get_complaint_status(complaint_id: str):
    """
    Citizens check their complaint status using their ID.
    """
    result = await self_correction_agent.execute_with_correction(
        agent_name="TrackingAgent",
        agent_func=tracking_agent.get_public_status,
        required_keys=["complaint"],
        complaint_id=complaint_id
    )
    if result.get("_fallback_used"):
        result = await tracking_agent.get_public_status(complaint_id)
    return JSONResponse(result)


@app.get("/api/complaints/all")
async def get_all_complaints():
    """
    Officials get all complaints sorted by priority.
    """
    try:
        complaints = []
        docs = db.collection('complaints').order_by(
            'priority_score',
            direction=firestore.Query.DESCENDING
        ).limit(100).stream()

        for doc in docs:
            complaints.append(doc.to_dict())

        emergencies = []
        e_docs = db.collection('emergencies').stream()
        for doc in e_docs:
            emergencies.append(doc.to_dict())

        return JSONResponse({
            "success": True,
            "complaints": complaints,
            "emergencies": emergencies,
            "total_complaints": len(complaints),
            "total_emergencies": len(emergencies)
        })

    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@app.get("/api/complaints/department/{dept}")
async def get_dept_complaints(dept: str):
    try:
        # Standardize formatting to capitalize the first letter (e.g., "water" -> "Water")
        formatted_dept = dept.strip().capitalize()

        # If admin supervising account, fetch everything directly
        if formatted_dept == "All Departments" or formatted_dept == "All":
            docs = db.collection('complaints').limit(50).stream()
        else:
            # Query using the clean capitalized name string
            docs = db.collection('complaints').where(
                filter=firestore.FieldFilter('department', '==', formatted_dept)
            ).limit(50).stream()

        complaints = [doc.to_dict() for doc in docs]
        
        # Double check with a fallback query if the list is empty (catches all lowercase records)
        if not complaints and formatted_dept != "All":
            docs_lower = db.collection('complaints').where(
                filter=firestore.FieldFilter('department', '==', dept.lower())
            ).limit(50).stream()
            complaints = [doc.to_dict() for doc in docs_lower]

        complaints.sort(key=lambda x: x.get('priority_score', 0), reverse=True)

        return JSONResponse({"success": True, "department": dept, "complaints": complaints})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════
# OFFICIALS ENDPOINTS
# ═══════════════════════════════════════════════════════

@app.post("/api/officials/update-status")
async def update_complaint_status(
    complaint_id: str = Form(...),
    new_status: str = Form(...),
    update_note: str = Form(...),
    updated_by: str = Form(...)
):
    """
    Officials update the status of a complaint.
    """
    result = await self_correction_agent.execute_with_correction(
        agent_name="TrackingAgent_Update",
        agent_func=tracking_agent.update_status,
        required_keys=["success"],
        complaint_id=complaint_id,
        new_status=new_status,
        update_note=update_note,
        updated_by=updated_by
    )
    if result.get("_fallback_used"):
        result = await tracking_agent.update_status(complaint_id, new_status, update_note, updated_by)
    return JSONResponse(result)


@app.get("/api/officials/dashboard")
async def get_dashboard_data():
    try:
        # 1. Fetch normal complaints and active emergencies
        all_docs = list(db.collection('complaints').limit(200).stream())
        all_complaints = [d.to_dict() for d in all_docs]

        e_docs = list(db.collection('emergencies').stream())
        emergencies = [d.to_dict() for d in e_docs]

        # 2. ✅ DE-DUPLICATE BY UNIQUE ID (Fixes double counting)
        complaint_dict = {}
        for c in all_complaints:
            cid = c.get('id') or c.get('complaint_id')
            if cid:
                complaint_dict[cid] = c

        # Overwrite/Ensure emergency documents are marked cleanly
        for e in emergencies:
            eid = e.get('id') or e.get('complaint_id')
            if eid:
                complaint_dict[eid] = e

        # This gives your true, deduplicated list
        combined_view = list(complaint_dict.values())

        total = len(combined_view)
        by_status = {}
        by_dept = {}
        by_priority = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        total_budget_min = 0
        total_budget_max = 0

        for c in combined_view:
            status = c.get('status', 'submitted') or 'submitted'
            by_status[status] = by_status.get(status, 0) + 1

            raw_dept = c.get('department', 'Other') or 'Other'
            raw_dept = str(raw_dept).strip().title()

            if raw_dept.lower() == "emergency":
                dept = "Emergency"
            else:
                dept = raw_dept

            by_dept[dept] = by_dept.get(dept, 0) + 1

            level = c.get('priority_level', 'low')
            if not level: 
                level = 'low'
            level = level.lower()
            if level in by_priority:
                by_priority[level] += 1

            total_budget_min += c.get('budget_min', 0) or 0
            total_budget_max += c.get('budget_max', 0) or 0

        cross_dept_alerts = [c for c in combined_view if c.get('cross_dept_links', {}).get('linked')]
        
        urgent = [
            c for c in combined_view
            if c.get('priority_level') in ['critical', 'high'] or c.get('department') == 'Emergency'
        ]
        urgent.sort(key=lambda x: x.get('priority_score', 999) if x.get('priority_level') == 'critical' else x.get('priority_score', 0), reverse=True)

        def format_inr(amount):
            if amount >= 10000000: return f"₹{amount/10000000:.1f}Cr"
            elif amount >= 100000: return f"₹{amount/100000:.1f}L"
            elif amount >= 1000: return f"₹{amount/1000:.0f}K"
            return f"₹{amount}"

        return JSONResponse({
            "success": True,
            "stats": {
                "total_complaints": total,
                "total_emergencies": len(emergencies),
                "by_status": by_status,
                "by_department": by_dept,
                "by_priority": by_priority,
                "cross_dept_alerts": len(cross_dept_alerts),
                "urgent_unresolved": len(urgent),
                "total_budget_range": f"{format_inr(total_budget_min)} – {format_inr(total_budget_max)}"
            },
            "emergencies": emergencies,
            "urgent_complaints": urgent[:15],
            "cross_dept_alerts": cross_dept_alerts[:5],
            "all_complaints": combined_view
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/feedback/ratings")
async def get_ratings():
    try:
        feedback_docs = list(db.collection('feedback').stream())
        ratings_list = [d.to_dict() for d in feedback_docs]
        return {"success": True, "ratings": ratings_list}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ═══════════════════════════════════════════════════════
# FEEDBACK ENDPOINTS
# ═══════════════════════════════════════════════════════

@app.post("/api/feedback/submit")
async def submit_feedback(
    complaint_id: str = Form(...),
    rating: int = Form(...),
    comment: str = Form(...),
    citizen_name: str = Form(...)
):
    """Citizen submits feedback after resolution."""
    result = await self_correction_agent.execute_with_correction(
        agent_name="FeedbackAgent",
        agent_func=feedback_agent.submit_feedback,
        required_keys=["success"],
        complaint_id=complaint_id,
        rating=rating,
        comment=comment,
        citizen_name=citizen_name
    )
    if result.get("_fallback_used"):
        result = await feedback_agent.submit_feedback(complaint_id, rating, comment, citizen_name)
    return JSONResponse(result)


@app.get("/api/feedback/ratings")
async def get_public_ratings():
    """Unified ratings endpoint returning both calculated stats and raw feedback."""
    try:
        # Get calculated averages per department from FeedbackAgent
        agent_result = await feedback_agent.get_department_ratings()
        
        # Stream raw feedback docs for fallback parsing
        feedback_docs = list(db.collection('feedback').stream())
        raw_ratings = [d.to_dict() for d in feedback_docs]

        return JSONResponse({
            "success": True,
            "department_ratings": agent_result.get("department_ratings", {}),
            "ratings": raw_ratings,
            "total_feedback": agent_result.get("total_feedback", len(raw_ratings))
        })
    except Exception as e:
        print(f"[Backend Ratings Exception]: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════
# QUERY ENDPOINT (Citizen Q&A)
# ═══════════════════════════════════════════════════════

@app.post("/api/query")
async def citizen_query(
    question: str = Form(...),
    complaint_id: Optional[str] = Form(None)  # Explicitly allow optional form text
):
    """Answers citizen questions using AI securely."""
    try:
        # Clean up empty strings or placeholders sent from the UI
        clean_id = None
        if complaint_id:
            stripped = complaint_id.strip()
            if stripped and stripped.lower() not in ["null", "undefined", "none", ""]:
                clean_id = stripped

        # Build a highly direct, contextual prompt for Gemini
        master_prompt = f"""
You are CivicMind AI, an intelligent, helpful, and empathetic urban governance assistant. 
A citizen has reached out with a query regarding municipal operations or public infrastructure.

CITIZEN QUESTION: "{question}"
"""

        # Inject context from the live database record if a valid ID was submitted
        if clean_id:
            complaint_doc = db.collection('complaints').document(clean_id).get()
            if complaint_doc.exists:
                cd = complaint_doc.to_dict()
                master_prompt += f"""
[LIVE SYSTEM CONTEXT TICKET #{clean_id}]
- Current Processing Status: {cd.get('status', 'Submitted')}
- Responsible Department: {cd.get('department', 'General Triage')}
- Automated Diagnostics: {cd.get('explanation', 'Under evaluation')}
- Recommended Action: {cd.get('recommended_action', 'Pending inspection')}
- SLA Target Timeline: {cd.get('response_time_target', 'Standard Queue')}

Please cross-reference this ticket telemetry directly in your answer to give the citizen specific tracking clarity.
"""
            else:
                master_prompt += f"\nNote: The user provided a complaint ID '{clean_id}', but it does not exist in our database systems yet. Advise them politely to check the spelling."

        master_prompt += "\nProvide a helpful, polite, professional, and highly specific response to the citizen's question. Avoid generic responses."

        # Self-Correcting text generator call
        ai_response = await self_correction_agent.execute_with_correction(
            agent_name="QueryAgent",
            agent_func=generate_text,
            min_text_length=15,
            prompt=master_prompt
        )

        if isinstance(ai_response, dict):
            ai_response = "I am ready to assist you with any questions regarding city services or your complaint status."

        return {
            "success": True, 
            "answer": ai_response.strip()
        }

    except Exception as e:
        print(f"[Query API Exception Details]: {e}")
        return {
            "success": False, 
            "answer": "I am experiencing temporary technical difficulties retrieving specific civic details right now. Please try again shortly."
        }

import asyncio
import json
from fastapi.responses import StreamingResponse

@app.post("/api/complaints/submit-stream")
async def submit_complaint_stream(
    complaint_text: str = Form(...),
    location: str = Form(...),
    citizen_name: str = Form(...),
    citizen_contact: str = Form(...),
    image: UploadFile = File(None)
):
    """
    Real Event Stream: Executes each agent sequentially and yields live intermediate telemetry!
    """
    async def pipeline_generator():
        try:
            # 0. Read Image
            image_bytes = await image.read() if image and image.filename else None
            complaint_id = "CM" + str(uuid.uuid4())[:6].upper()

            # ── AGENT 1: Classification ──
            yield f"data: {json.dumps({'stage': 'classification', 'status': 'running', 'message': 'Agent 1: Scanning issue type & safety risks...'})}\n\n"
            classification = await self_correction_agent.execute_with_correction(
                agent_name="ClassificationAgent",
                agent_func=classification_agent.classify,
                required_keys=["type"],
                complaint_text=complaint_text,
                image_bytes=image_bytes
            )
            if classification.get("_fallback_used"):
                classification = await classification_agent.classify(complaint_text, image_bytes)

            yield f"data: {json.dumps({'stage': 'classification', 'status': 'done', 'data': classification})}\n\n"

            # Emergency Check
            if str(classification.get("type", "")).upper() == "EMERGENCY":
                emergency_record = {
                    "id": complaint_id,
                    "complaint_id": complaint_id,
                    "type": "emergency",
                    "original_complaint": complaint_text,
                    "problem": complaint_text,
                    "location": location,
                    "citizen_name": citizen_name,
                    "citizen_contact": citizen_contact,
                    "status": "emergency_escalated",
                    "priority_level": "critical",
                    "department": "Emergency",
                    "created_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
                }
                db.collection('emergencies').document(complaint_id).set(emergency_record)
                db.collection('complaints').document(complaint_id).set(emergency_record)
                yield f"data: {json.dumps({'stage': 'complete', 'type': 'emergency', 'complaint_id': complaint_id, 'data': emergency_record})}\n\n"
                return

            # ── AGENT 2: Intake ──
            yield f"data: {json.dumps({'stage': 'intake', 'status': 'running', 'message': 'Agent 2: Parsing severity, issue type & location...'})}\n\n"
            intake = await self_correction_agent.execute_with_correction(
                agent_name="IntakeAgent",
                agent_func=intake_agent.process,
                required_keys=["department", "specific_problem", "severity_score"],
                complaint_text=complaint_text,
                location=location,
                image_bytes=image_bytes
            )
            if intake.get("_fallback_used"):
                intake = await intake_agent.process(complaint_text, location, image_bytes)

            yield f"data: {json.dumps({'stage': 'intake', 'status': 'done', 'data': intake})}\n\n"

            # ── AGENT 3: Intelligence ──
            yield f"data: {json.dumps({'stage': 'intelligence', 'status': 'running', 'message': 'Agent 3: Analyzing root cause & historical links...'})}\n\n"
            intelligence = await self_correction_agent.execute_with_correction(
                agent_name="IntelligenceAgent",
                agent_func=intelligence_agent.analyze,
                required_keys=["root_cause"],
                intake_data=intake
            )
            if intelligence.get("_fallback_used"):
                intelligence = await intelligence_agent.analyze(intake)

            yield f"data: {json.dumps({'stage': 'intelligence', 'status': 'done', 'data': intelligence})}\n\n"

            # ── AGENT 5: Prioritization & Budget ──
            yield f"data: {json.dumps({'stage': 'prioritization', 'status': 'running', 'message': 'Agent 5: Computing priority score & budget bounds...'})}\n\n"
            priority_result = await self_correction_agent.execute_with_correction(
                agent_name="PrioritizationAgent",
                agent_func=prioritization_agent.prioritize,
                required_keys=["priority_score", "priority_level", "budget"],
                intake_data=intake,
                intelligence_data=intelligence
            )
            if priority_result.get("_fallback_used"):
                priority_result = await prioritization_agent.prioritize(intake, intelligence)

            yield f"data: {json.dumps({'stage': 'prioritization', 'status': 'done', 'data': priority_result})}\n\n"

            # ── AGENT 4: Explainability ──
            yield f"data: {json.dumps({'stage': 'explainability', 'status': 'running', 'message': 'Agent 4: Formatting decision explanation...'})}\n\n"
            explanation = await self_correction_agent.execute_with_correction(
                agent_name="ExplainabilityAgent",
                agent_func=explainability_agent.explain,
                required_keys=["explanation"],
                intake_data=intake,
                intelligence_data=intelligence,
                priority_score=priority_result.get("priority_score", 50)
            )
            if explanation.get("_fallback_used"):
                explanation = await explainability_agent.explain(intake, intelligence, priority_result.get("priority_score", 50))

            yield f"data: {json.dumps({'stage': 'explainability', 'status': 'done', 'data': explanation})}\n\n"

            # Final Database Persistence
            budget = priority_result.get("budget", {})
            final_dept = (classification.get("department") or intake.get("department") or "Other").strip().title()
            final_priority = (priority_result.get("priority_level") or "medium").strip().lower()

            complaint_record = {
                "id": complaint_id,
                "created_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                "citizen_name": citizen_name,
                "citizen_contact": citizen_contact,
                "original_complaint": complaint_text,
                "location": location,
                "department": final_dept,
                "priority_level": final_priority,
                "priority_score": priority_result.get("priority_score"),
                "budget_range": budget.get("budget_range", "Under Review"),
                "budget_min": budget.get("minimum_cost", 0),
                "budget_max": budget.get("maximum_cost", 0),
                "root_cause": intelligence.get("root_cause", {}),
                "cross_dept_links": intelligence.get("cross_dept_links", {}),
                "explanation": explanation.get("explanation"),
                "recommended_action": explanation.get("recommended_action"),
                "self_corrected": classification.get("_self_corrected", False) or intake.get("_self_corrected", False) or priority_result.get("_self_corrected", False),
                "status": "submitted"
            }

            db.collection('complaints').document(complaint_id).set(complaint_record)

            yield f"data: {json.dumps({'stage': 'complete', 'status': 'success', 'complaint_id': complaint_id, 'data': complaint_record})}\n\n"

        except Exception as err:
            yield f"data: {json.dumps({'stage': 'error', 'message': str(err)})}\n\n"

    return StreamingResponse(pipeline_generator(), media_type="text/event-stream")
# ═══════════════════════════════════════════════════════
# OUTCOME VERIFICATION
# ═══════════════════════════════════════════════════════

@app.post("/api/complaints/verify/{complaint_id}")
async def verify_outcome(complaint_id: str):
    """Verify if a resolved complaint was actually fixed."""
    result = await tracking_agent.verify_outcome(complaint_id)
    return JSONResponse(result)

# ═══════════════════════════════════════════════════════
# CROSS-DEPARTMENT GRAPH ENDPOINT (FILTERS OUT ISOLATED TICKETS)
# ═══════════════════════════════════════════════════════

@app.get("/api/graph/cross-department")
async def get_cross_department_graph():
    """
    Returns tree nodes grouped by underlying root cause infrastructure problems.
    """
    try:
        docs = db.collection('complaints').stream()
        nodes = []
        edges = []
        groups = []
        node_ids = set()
        
        for doc in docs:
            data = doc.to_dict()
            complaint_id = doc.id
            cross_links = data.get('cross_dept_links', {})
            
            if cross_links and cross_links.get('linked'):
                root_cause = data.get('root_cause', {})
                linked_ids = cross_links.get('linked_ids', [])
                departments = cross_links.get('departments_involved', [])
                underlying = cross_links.get('underlying_issue', 'Sub-surface Asset Failure')
                
                root_node_id = f"root_{complaint_id}"
                
                # 1. Map Core Root Node
                if root_node_id not in node_ids:
                    nodes.append({
                        "id": root_node_id,
                        "label": "Root Cause Assessment",
                        "problem": root_cause.get('root_cause', underlying)[:60],
                        "department": "multiple",
                        "departments_involved": departments,
                        "confidence": root_cause.get('confidence', 0.85),
                        "failure_risk": root_cause.get('failure_risk', 'medium'),
                        "recommended_action": root_cause.get('recommended_action', 'Joint Inspection Required'),
                        "type": "root_cause"
                    })
                    node_ids.add(root_node_id)
                
                # 2. Map Primary Affected Ticket Node
                if complaint_id not in node_ids:
                    nodes.append({
                        "id": complaint_id,
                        "label": complaint_id,
                        "problem": data.get('specific_problem', 'Civic Issue')[:50],
                        "location": data.get('location', ''),
                        "department": data.get('department', 'other').lower().replace(' department', ''),
                        "priority": data.get('priority_level', 'medium'),
                        "status": data.get('status', 'submitted'),
                        "type": "complaint"
                    })
                    node_ids.add(complaint_id)
                
                # Draw direct line: Complaint node connecting to its Root Cause Hub
                edges.append({
                    "from": complaint_id,
                    "to": root_node_id,
                    "label": "linked to"
                })
                
                # 3. Map Secondary Dependent Affected Issues
                for linked_id in linked_ids:
                    if linked_id and linked_id not in node_ids:
                        linked_doc = db.collection('complaints').document(linked_id).get()
                        if linked_doc.exists:
                            ld = linked_doc.to_dict()
                            nodes.append({
                                "id": linked_id,
                                "label": linked_id,
                                "problem": ld.get('specific_problem', 'Collateral Damage Issue')[:50],
                                "location": ld.get('location', ''),
                                "department": ld.get('department', 'other').lower().replace(' department', ''),
                                "priority": ld.get('priority_level', 'medium'),
                                "status": ld.get('status', 'submitted'),
                                "type": "complaint"
                            })
                            node_ids.add(linked_id)
                            
                            edges.append({
                                "from": linked_id,
                                "to": root_node_id,
                                "label": "linked to"
                            })

                groups.append({
                    "root_cause_id": root_node_id,
                    "complaint_ids": [complaint_id] + linked_ids,
                    "departments": departments,
                    "root_cause_text": root_cause.get('root_cause', underlying),
                    "confidence": root_cause.get('confidence', 0.85),
                    "failure_risk": root_cause.get('failure_risk', 'medium')
                })
                
        return JSONResponse({
            "success": True,
            "nodes": nodes,
            "edges": edges,
            "groups": groups,
            "total_complaints": len([n for n in nodes if n["type"] == "complaint"]),
            "total_root_causes": len([n for n in nodes if n["type"] == "root_cause"]),
            "cross_dept_count": len(groups)
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 1. Locate the frontend/dist folder relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend", "dist")

# 2. Mount the compiled assets folder (JS/CSS files)
if os.path.exists(os.path.join(FRONTEND_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

# 3. Create a catch-all route to serve the React interface
@app.get("/{catchall:path}")
async def serve_frontend(catchall: str):
    # Let your API endpoints handle themselves safely
    if catchall.startswith("api"):
        return {"detail": "Not Found"}
        
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend build files missing. Make sure dist folder is uploaded."}


    
