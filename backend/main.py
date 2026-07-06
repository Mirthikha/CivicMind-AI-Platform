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
from backend.gemini_client import generate_text

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

        # ── AGENT 1: Classify ──
        classification = await classification_agent.classify(
            complaint_text
        )

        # ── EMERGENCY PATH ──
        if classification["type"] == "emergency":
            emergency_record = {
                "id": complaint_id,
                "type": "emergency",
                "complaint_text": complaint_text,
                "location": location,
                "citizen_name": citizen_name,
                "citizen_contact": citizen_contact,
                "classification_reason": classification["reason"],
                "status": "emergency_escalated",
                "priority": "CRITICAL",
                "priority_level": "critical",
                "color_code": "red",
                "created_at": datetime.now().isoformat(),
                "department": "emergency"
            }
            db.collection('emergencies').document(
                complaint_id
            ).set(emergency_record)

            return JSONResponse({
                "success": True,
                "complaint_id": complaint_id,
                "type": "emergency",
                "message": (
                    "🚨 Emergency detected! Officials have been "
                    "alerted immediately."
                ),
                "status": "emergency_escalated"
            })

        # ── NORMAL PATH ──

        # AGENT 2: Intake
        intake = await intake_agent.process(
            complaint_text, location, image_bytes
        )

        # AGENT 3: Intelligence
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

        # AGENT 5: Prioritization + Budget
        priority_result = await prioritization_agent.prioritize(
            intake, intelligence
        )

        # AGENT 4: Explainability
        explanation = await explainability_agent.explain(
            intake,
            intelligence,
            priority_result["priority_score"]
        )

        # ── BUILD COMPLETE RECORD ──
        budget = priority_result.get("budget", {})

        complaint_record = {
            # Identity
            "id": complaint_id,
            "type": "normal",
            "created_at": datetime.now().isoformat(),

            # Citizen info
            "citizen_name": citizen_name,
            "citizen_contact": citizen_contact,

            # Complaint content
            "original_complaint": complaint_text,
            "location": location,
            "has_image": image_bytes is not None,

            # Intake analysis
            "issue_type": intake.get("issue_type"),
            "severity": intake.get("severity"),
            "severity_score": intake.get("severity_score"),
            "specific_problem": intake.get("specific_problem"),
            "affected_area": intake.get("affected_area"),
            "department": intake.get("department"),
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

            "explanation": explanation.get("explanation"),
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
    result = await tracking_agent.update_status(
        complaint_id, new_status, update_note, updated_by
    )
    return JSONResponse(result)


@app.get("/api/officials/dashboard")
async def get_dashboard_data():
    """
    Full dashboard data for city admin.
    Includes stats, emergencies, high priority items.
    """
    try:
        # Get all complaints
        all_docs = list(
            db.collection('complaints').limit(200).stream()
        )
        all_complaints = [d.to_dict() for d in all_docs]

        # Get emergencies
        e_docs = list(db.collection('emergencies').stream())
        emergencies = [d.to_dict() for d in e_docs]

        # Calculate stats
        total = len(all_complaints)
        by_status = {}
        by_dept = {}
        by_priority = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        total_budget_min = 0
        total_budget_max = 0

        for c in all_complaints:
            status = c.get('status', 'submitted') or 'submitted'
            by_status[status] = by_status.get(status, 0) + 1

            dept = c.get('department', 'other') or 'other'
            by_dept[dept] = by_dept.get(dept, 0) + 1

            # Secure safe fallback string loop if level is missing or None
            level = c.get('priority_level', 'low')
            if not level: 
                level = 'low'
            level = level.lower()
            if level in by_priority:
                by_priority[level] += 1

            total_budget_min += c.get('budget_min', 0) or 0
            total_budget_max += c.get('budget_max', 0) or 0

        # Cross-department alerts
        cross_dept_alerts = [
            c for c in all_complaints
            if c.get('cross_dept_links', {}).get('linked')
        ]

        # High priority unresolved
        urgent = [
            c for c in all_complaints
            if c.get('priority_level') in ['critical', 'high']
            and c.get('status') not in ['resolved', 'closed']
        ]

        def format_inr(amount):
            if amount >= 10000000:
                return f"₹{amount/10000000:.1f}Cr"
            elif amount >= 100000:
                return f"₹{amount/100000:.1f}L"
            elif amount >= 1000:
                return f"₹{amount/1000:.0f}K"
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
                "total_budget_range": (
                    f"{format_inr(total_budget_min)} – "
                    f"{format_inr(total_budget_max)}"
                )
            },
            "emergencies": emergencies,
            "urgent_complaints": urgent[:10],
            "cross_dept_alerts": cross_dept_alerts[:5],
            "all_complaints": all_complaints
        })

    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@app.get("/api/officials/ratings")
async def get_ratings():
    """Department performance ratings."""
    result = await feedback_agent.get_department_ratings()
    return JSONResponse(result)


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
    result = await feedback_agent.submit_feedback(
        complaint_id, rating, comment, citizen_name
    )
    return JSONResponse(result)


@app.get("/api/feedback/ratings")
async def get_public_ratings():
    """Public ratings display."""
    result = await feedback_agent.get_department_ratings()
    return JSONResponse(result)


# ═══════════════════════════════════════════════════════
# QUERY ENDPOINT (Citizen Q&A)
# ═══════════════════════════════════════════════════════

@app.post("/api/query")
async def citizen_query(
    question: str = Form(...),
    complaint_id: str = Form(None)
):
    """Answers citizen questions using AI securely."""
    try:
        # 1. Clean up placeholder inputs
        if complaint_id:
            complaint_id = complaint_id.strip()
            if not complaint_id or complaint_id.lower() in ["null", "undefined", ""]:
                complaint_id = None

        # 2. Build a high-context master prompt for Gemini
        master_prompt = f"""
        You are CivicMind AI, an intelligent urban governance assistant. 
        The citizen is asking the following question regarding city operations or public works:
        "{question}"
        """
        
        if complaint_id:
            
            complaint_doc = db.collection('complaints').document(complaint_id).get()
            if complaint_doc.exists:
                cd = complaint_doc.to_dict()
                master_prompt += f"\nContext: The user is tracking complaint ID {complaint_id}. System status is '{cd.get('status')}', department assigned is '{cd.get('department')}', and the automated diagnosis summary is: '{cd.get('explanation')}'."
            else:
                return {"success": True, "answer": f"I checked our Firestore database, but I couldn't find a complaint record matching the ID '{complaint_id}'. Please verify the characters and try tracking again."}

        master_prompt += "\nProvide a helpful, polite, professional, and highly specific response to the citizen's question."

        ai_response = generate_text(master_prompt)
        
        return {"success": True, "answer": ai_response.strip()}

    except Exception as e:
        print(f"[Query API Crash]: {e}")
        return {"success": False, "answer": "I'm having trouble communicating with our core intelligence agents. Please check back shortly."}


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
    Returns data formatted specifically for the cross-department graph visualization.
    Only includes nodes that participate in a cross-department linkage.
    """
    try:
        # Stream live complaints collection from database
        docs = db.collection('complaints').stream()
        
        nodes = []      # Relational target nodes 
        edges = []      # Directional link connections
        groups = []     # Aggregated cluster meta
        
        node_ids = set()  # Prevent duplicate node additions
        
        for doc in docs:
            data = doc.to_dict()
            complaint_id = doc.id
            cross_links = data.get('cross_dept_links', {})
            
            # 🌟 FIXED: Enforce a strict gate check. Only build graph assets 
            # if the Intelligence Agent confirmed an active cross-department link!
            if cross_links.get('linked'):
                root_cause = data.get('root_cause', {})
                linked_ids = cross_links.get('linked_ids', [])
                departments = cross_links.get('departments_involved', [])
                underlying = cross_links.get('underlying_issue', 'Unknown')
                
                # 1. Safely add the primary anchor complaint node inside the check
                if complaint_id not in node_ids:
                    nodes.append({
                        "id": complaint_id,
                        "label": complaint_id,
                        "problem": data.get('specific_problem', '')[:50],
                        "location": data.get('location', ''),
                        "department": data.get('department', 'other'),
                        "priority": data.get('priority_level', 'low'),
                        "priority_score": data.get('priority_score', 0),
                        "status": data.get('status', 'submitted'),
                        "severity": data.get('severity', 'medium'),
                        "type": "complaint"
                    })
                    node_ids.add(complaint_id)
                
                # 2. Generate the centralized ROOT CAUSE cluster node hub
                root_node_id = f"root_{complaint_id}"
                if root_node_id not in node_ids:
                    nodes.append({
                        "id": root_node_id,
                        "label": "Root Cause",
                        "problem": root_cause.get('root_cause', underlying)[:60],
                        "location": data.get('location', ''),
                        "department": "multiple",
                        "departments_involved": departments,
                        "confidence": root_cause.get('confidence', 0.7),
                        "failure_risk": root_cause.get('failure_risk', 'medium'),
                        "recommended_action": root_cause.get('recommended_action', ''),
                        "underlying_issue": underlying,
                        "type": "root_cause"
                    })
                    node_ids.add(root_node_id)
                
                # Edge connection: Anchor complaint → Root cause center
                edges.append({
                    "from": complaint_id,
                    "to": root_node_id,
                    "label": "caused by"
                })
                
                # 3. Process and loop secondary linked complaint assets
                for linked_id in linked_ids:
                    if linked_id and linked_id not in node_ids:
                        linked_doc = db.collection('complaints').document(linked_id).get()
                        
                        if linked_doc.exists:
                            ld = linked_doc.to_dict()
                            nodes.append({
                                "id": linked_id,
                                "label": linked_id,
                                "problem": ld.get('specific_problem', '')[:50],
                                "location": ld.get('location', ''),
                                "department": ld.get('department', 'other'),
                                "priority": ld.get('priority_level', 'low'),
                                "status": ld.get('status', 'submitted'),
                                "type": "complaint"
                            })
                            node_ids.add(linked_id)
                        
                        # Edge connection: Linked complaint → Root cause center
                        edges.append({
                            "from": linked_id,
                            "to": root_node_id,
                            "label": "caused by"
                        })
                
                # Keep groups structure aligned for custom summary displays
                groups.append({
                    "root_cause_id": root_node_id,
                    "complaint_ids": [complaint_id] + linked_ids,
                    "departments": departments,
                    "root_cause_text": root_cause.get('root_cause', underlying),
                    "confidence": root_cause.get('confidence', 0.7),
                    "failure_risk": root_cause.get('failure_risk', 'medium')
                })
        
        # Recalculate summary totals exclusively for visible nodes
        dept_summary = {}
        for node in nodes:
            if node["type"] == "complaint":
                dept = node.get("department", "other")
                dept_summary[dept] = dept_summary.get(dept, 0) + 1
        
        return JSONResponse({
            "success": True,
            "nodes": nodes,
            "edges": edges,
            "groups": groups,
            "total_complaints": len([n for n in nodes if n["type"] == "complaint"]),
            "total_root_causes": len([n for n in nodes if n["type"] == "root_cause"]),
            "cross_dept_count": len(groups),
            "department_summary": dept_summary
        })
        
    except Exception as e:
        print(f"[Graph] Error compilation exception: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


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



    
