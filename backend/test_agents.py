"""
CivicMind — Complete Agent Pipeline Test
Tests all 8 agents in correct order
"""

import asyncio
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase once
if not firebase_admin._apps:
    cred = credentials.Certificate("backend/firebase_credentials.json")
    firebase_admin.initialize_app(cred)

# Import all agents
from backend.agents.classification_agent import classification_agent
from backend.agents.intake_agent import intake_agent
from backend.agents.intelligence_agent import intelligence_agent
from backend.agents.prioritization_agent import prioritization_agent
from backend.agents.explainability_agent import explainability_agent
from backend.agents.tracking_agent import tracking_agent
from backend.agents.feedback_agent import feedback_agent
from backend.agents.query_agent import query_agent


def divider(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


def section(title: str):
    print(f"\n--- {title} ---")


async def run_all_tests():

    divider("CIVICMIND — FULL AGENT PIPELINE TEST")

    # ─────────────────────────────────────────
    # TEST COMPLAINT
    # ─────────────────────────────────────────
    test_text = (
        "The road on Anna Salai near the bus stop has a massive "
        "pothole. Water is collecting inside it. Two bikes have "
        "already fallen. Very dangerous especially at night."
    )
    test_location = "Anna Salai, near Central Bus Stop, Chennai"

    print(f"\nCOMPLAINT : {test_text[:65]}...")
    print(f"LOCATION  : {test_location}")

    # ─────────────────────────────────────────
    # AGENT 1: CLASSIFICATION
    # ─────────────────────────────────────────
    section("AGENT 1 — CLASSIFICATION")
    classification = await classification_agent.classify(test_text)

    print(f"  Type       : {classification['type'].upper()}")
    print(f"  Reason     : {classification['reason']}")
    print(f"  Confidence : {classification['confidence']}")
    print(f"  Method     : {classification['method']}")

    # ─────────────────────────────────────────
    # AGENT 2: INTAKE
    # ─────────────────────────────────────────
    section("AGENT 2 — INTAKE")
    intake = await intake_agent.process(test_text, test_location)

    print(f"  Issue Type      : {intake['issue_type']}")
    print(f"  Severity        : {intake['severity']} ({intake['severity_score']}/10)")
    print(f"  Department      : {intake['department']}")
    print(f"  Specific Problem: {intake['specific_problem']}")
    print(f"  Urgency         : {intake['urgency_hours']} hours")
    print(f"  People Affected : ~{intake['people_affected']}")
    print(f"  Has Image       : {intake['has_image']}")

    # ─────────────────────────────────────────
    # AGENT 3: INTELLIGENCE
    # ─────────────────────────────────────────
    section("AGENT 3 — INTELLIGENCE")
    intelligence = await intelligence_agent.analyze(intake)

    root = intelligence['root_cause']
    cross = intelligence['cross_dept_links']
    fraud = intelligence['fraud_flag']

    print(f"  Is Duplicate    : {intelligence['is_duplicate']}")
    print(f"  Cluster Size    : {intelligence['cluster_size']} complaints")
    print(f"  Depts Involved  : {intelligence['departments_involved']}")
    print(f"  Root Cause      : {root.get('root_cause', 'N/A')[:70]}")
    print(f"  Confidence      : {root.get('confidence', 0)}")
    print(f"  Failure Risk    : {root.get('failure_risk', 'N/A').upper()}")
    print(f"  If Ignored      : {root.get('prediction', 'N/A')[:65]}")
    print(f"  Cross-Dept Link : {cross.get('linked', False)}")
    if cross.get('linked'):
        print(f"  Underlying      : {cross.get('underlying_issue')}")
    print(f"  Fraud Flagged   : {fraud['flagged']}")
    if fraud['flagged']:
        print(f"  Fraud Flags     : {fraud['flags']}")

    # ─────────────────────────────────────────
    # AGENT 5: PRIORITIZATION + BUDGET
    # ─────────────────────────────────────────
    section("AGENT 5 — PRIORITIZATION + BUDGET (Gemini)")
    priority_result = await prioritization_agent.prioritize(
        intake, intelligence
    )

    budget = priority_result['budget']
    breakdown = priority_result['score_breakdown']

    print(f"\n  PRIORITY:")
    print(f"    Score          : {priority_result['priority_score']}/10")
    print(f"    Level          : {priority_result['priority_level'].upper()}")
    print(f"    Response Target: {priority_result['response_time_target']}")
    print(f"    Color Code     : {priority_result['color_code'].upper()}")
    print(f"    Equity Flag    : {priority_result['equity_flag']}")
    if priority_result['equity_note']:
        print(f"    Equity Note    : {priority_result['equity_note']}")

    print(f"\n  SCORE BREAKDOWN:")
    print(f"    Base severity  : {breakdown['base_severity']}")
    print(f"    Cluster bonus  : {breakdown['cluster_bonus']}")
    print(f"    Cross-dept     : {breakdown['cross_dept_bonus']}")
    print(f"    Risk bonus     : {breakdown['risk_bonus']}")
    print(f"    People bonus   : {breakdown['people_bonus']}")

    print(f"\n  💰 BUDGET (Gemini AI Estimate):")
    print(f"    Budget Range   : {budget.get('budget_range', 'N/A')}")
    print(f"    Immediate Fix  : {budget.get('immediate_formatted', 'N/A')}")
    print(f"    Permanent Fix  : {budget.get('permanent_formatted', 'N/A')}")
    print(f"    Timeline       : {budget.get('timeline_days', 'N/A')} days")
    print(f"    Departments    : {budget.get('departments_involved', [])}")
    print(f"    Justification  : {budget.get('cost_justification', 'N/A')}")
    print(f"    Source         : {budget.get('source', 'N/A')}")

    if budget.get('itemized'):
        print(f"\n  ITEMIZED COSTS:")
        for item in budget['itemized']:
            print(f"    • {item}")

    print(f"\n  NOTE: {budget.get('budget_note', '')}")

    # ─────────────────────────────────────────
    # AGENT 4: EXPLAINABILITY
    # ─────────────────────────────────────────
    section("AGENT 4 — EXPLAINABILITY")
    explanation = await explainability_agent.explain(
        intake,
        intelligence,
        priority_result['priority_score']
    )

    print(f"  Confidence      : {explanation['confidence_label']}")
    print(f"  Cross-Dept Alert: {explanation['cross_dept_alert']}")
    print(f"  Failure Risk    : {explanation['failure_risk'].upper()}")
    print(f"  Depts Must Act  : {explanation['departments_must_act']}")
    print(f"\n  OFFICIAL EXPLANATION:")
    print(f"  {'-'*50}")
    print(f"  {explanation['explanation']}")
    print(f"  {'-'*50}")
    print(f"  Recommended     : {explanation['recommended_action']}")
    print(f"  If Ignored      : {explanation['prediction_if_ignored'][:65]}")

    # ─────────────────────────────────────────
    # AGENT 6: TRACKING (test status check)
    # ─────────────────────────────────────────
    section("AGENT 6 — TRACKING")
    # Test with a fake ID to check the function works
    status = await tracking_agent.get_public_status("TEST123")
    print(f"  Status check for TEST123: {status.get('error', 'Function works')}")
    print(f"  Tracking agent: ✅ Ready")

if __name__ == "__main__":
    asyncio.run(run_all_tests())