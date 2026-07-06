from backend.gemini_client import generate_text
from firebase_admin import firestore
from datetime import datetime, timedelta


class IntelligenceAgent:
    """
    AGENT 3: Intelligence Agent
    The CORE differentiating agent.

    Jobs:
    1. Find similar complaints nearby
    2. Check if complaint is duplicate
    3. Link complaints across departments
    4. Generate root cause hypothesis
    5. Predict infrastructure failure
    6. Basic fraud detection
    """

    def __init__(self):
        self.db = firestore.client()

    async def analyze(self, intake_result: dict) -> dict:
        """
        Main function - runs all analysis steps.
        Input:  clean complaint record from IntakeAgent
        Output: full intelligence report
        """
        print(
            f"  [Intelligence] Analyzing: "
            f"{intake_result.get('location')}"
        )

        # Step 1: Find similar complaints
        similar = await self._find_similar_complaints(intake_result)
        print(f"  [Intelligence] Found {len(similar)} similar complaints")

        # Step 2: Check for duplicate
        is_dup, dup_id = self._check_duplicate(intake_result, similar)
        if is_dup:
            print(f"  [Intelligence] DUPLICATE of {dup_id}")
            return {
                "is_duplicate": True,
                "duplicate_of": dup_id,
                "similar_complaints": similar,
                "cross_dept_links": {},
                "root_cause": {},
                "fraud_flag": {"flagged": False, "flags": []},
                "cluster_size": len(similar),
                "departments_involved": []
            }

        # Step 3: Cross-department links
        cross_links = await self._find_cross_dept_links(
            intake_result, similar
        )
        print(
            f"  [Intelligence] Departments: "
            f"{cross_links.get('departments_involved', [])}"
        )

        # Step 4: Root cause
        root_cause = await self._generate_root_cause(
            intake_result, similar, cross_links
        )
        root_text = root_cause.get('root_cause', 'Unknown')
        print(f"  [Intelligence] Root cause: {root_text[:60]}...")

        # Step 5: Fraud check
        fraud = self._fraud_check(intake_result)

        return {
            "is_duplicate": False,
            "duplicate_of": None,
            "similar_complaints": similar,
            "cross_dept_links": cross_links,
            "root_cause": root_cause,
            "fraud_flag": fraud,
            "cluster_size": len(similar) + 1,
            "departments_involved": root_cause.get(
                "departments_involved",
                [intake_result.get("department", "other")]
            )
        }

    async def _find_similar_complaints(
        self, intake_result: dict
    ) -> list:
        """
        Search Firebase for complaints in the same area across ALL departments.
        """
        try:
            complaints_ref = self.db.collection('complaints')

            # FIX: Remove the restrictive department query filter to allow cross-dept lookups
            docs = complaints_ref.limit(50).stream()
            similar = []

            # Words to ignore when comparing locations
            stop_words = {
                'the', 'a', 'an', 'in', 'on', 'at',
                'near', 'road', 'street', 'and', 'of', 'to'
            }

            location_words = (
                set(intake_result.get('location', '').lower().split())
                - stop_words
            )

            for doc in docs:
                data = doc.to_dict()

                # Skip already resolved complaints
                if data.get('status') == 'resolved':
                    continue
                    
                # Skip comparing a complaint against itself
                if doc.id == intake_result.get('id'):
                    continue

                existing_words = (
                    set(data.get('location', '').lower().split())
                    - stop_words
                )

                common = location_words.intersection(existing_words)

                # Same area if at least 1 meaningful word matches
                if len(common) >= 1:
                    similar.append({
                        'id': doc.id,
                        'issue_type': data.get('issue_type'),
                        'specific_problem': data.get('specific_problem'),
                        'department': data.get('department'),
                        'location': data.get('location'),
                        'severity': data.get('severity'),
                        'status': data.get('status'),
                        'created_at': data.get('created_at')
                    })

            return similar

        except Exception as e:
            print(f"  [Intelligence] Error finding similar: {e}")
            return []

    def _check_duplicate(
        self,
        intake_result: dict,
        similar: list
    ) -> tuple:
        """
        Returns (True, complaint_id) if duplicate found.
        Returns (False, None) if not a duplicate.
        """
        for complaint in similar:
            same_type = (
                complaint.get('issue_type')
                == intake_result.get('issue_type')
            )
            not_closed = complaint.get('status') not in [
                'resolved', 'closed'
            ]
            if same_type and not_closed:
                return True, complaint.get('id')
        return False, None

    async def _find_cross_dept_links(
        self,
        intake_result: dict,
        similar: list
    ) -> dict:
        """
        KEY FEATURE: Finds if complaints from DIFFERENT departments
        might share the SAME underlying root cause.

        Example: water pressure + road cracking + basement flooding
        = all caused by one broken underground water main.
        """
        if not similar:
            return {
                "linked": False,
                "linked_ids": [],
                "departments_involved": [
                    intake_result.get("department", "other")
                ],
                "underlying_issue": "Single isolated complaint",
                "confidence": 0.5
            }

        # Build complaint summary for Gemini
        complaints_summary = ""
        for i, c in enumerate(similar[:5], 1):
            complaints_summary += (
                f"\nComplaint {i}: "
                f"{c.get('issue_type')} problem - "
                f"'{c.get('specific_problem')}' "
                f"(Dept: {c.get('department')})"
            )

        prompt = f"""
You are an infrastructure analyst for a city government.

A new complaint arrived. There are also existing complaints nearby.
Find if they share the same underlying infrastructure problem. Show they are similar only if the complain has a common cause that caused both the issues and are from the same area not only from the same city.

NEW COMPLAINT:
Type: {intake_result.get('issue_type')}
Problem: {intake_result.get('specific_problem')}
Location: {intake_result.get('location')}
Department: {intake_result.get('department')}

EXISTING COMPLAINTS IN SAME AREA:
{complaints_summary}

Example connection: Water pressure drop + Road cracking +
Basement flooding = all caused by one broken water main.

Reply in EXACTLY this format, nothing else:
LINKED: yes or no
REASON: one sentence
DEPARTMENTS_INVOLVED: comma separated e.g. water,roads
UNDERLYING_ISSUE: one sentence describing root infrastructure problem
CONFIDENCE: number 0.0 to 1.0
"""

        try:
            response = generate_text(prompt)

            result = {
                "linked": False,
                "linked_ids": [],
                "departments_involved": [
                    intake_result.get("department", "other")
                ],
                "underlying_issue": "No clear connection found",
                "confidence": 0.5
            }

            for line in response.strip().split('\n'):
                line = line.strip()
                if ':' not in line:
                    continue
                key, _, value = line.partition(':')
                key = key.strip().upper()
                value = value.strip()

                if key == "LINKED":
                    result["linked"] = value.lower() == "yes"
                    if result["linked"]:
                        result["linked_ids"] = [
                            c.get('id') for c in similar
                        ]
                elif key == "DEPARTMENTS_INVOLVED":
                    result["departments_involved"] = [
                        d.strip() for d in value.split(',')
                    ]
                elif key == "UNDERLYING_ISSUE":
                    result["underlying_issue"] = value
                elif key == "CONFIDENCE":
                    try:
                        result["confidence"] = float(value)
                    except ValueError:
                        result["confidence"] = 0.5

            return result

        except Exception as e:
            print(f"  [Intelligence] Cross-dept error: {e}")
            return {
                "linked": False,
                "linked_ids": [],
                "departments_involved": [
                    intake_result.get("department", "other")
                ],
                "underlying_issue": "Analysis unavailable",
                "confidence": 0.5
            }

    async def _generate_root_cause(
        self,
        intake_result: dict,
        similar: list,
        cross_links: dict
    ) -> dict:
        """
        Generates root cause hypothesis with confidence score
        and prediction of what happens if ignored.
        """
        cluster_count = len(similar) + 1

        prompt = f"""
You are a senior infrastructure engineer analyzing civic complaints. Find the root cause only if the complaints are related and are from the same area, not only same city.

CURRENT COMPLAINT:
Problem: {intake_result.get('specific_problem')}
Location: {intake_result.get('location')}
Issue Type: {intake_result.get('issue_type')}
Severity Score: {intake_result.get('severity_score')}/10

CONTEXT:
Total related complaints in area: {cluster_count}
Departments involved: {cross_links.get('departments_involved', [])}
Possible underlying issue: {cross_links.get('underlying_issue', 'Unknown')}

Provide engineering analysis.

Reply in EXACTLY this format:
ROOT_CAUSE: most likely cause in one clear sentence
CONFIDENCE: number 0.0 to 1.0
EVIDENCE: what patterns support this conclusion
DEPARTMENTS_INVOLVED: comma separated departments that must respond
RECOMMENDED_ACTION: what officials should do first
PREDICTION: what happens in 30 days if ignored
FAILURE_RISK: low or medium or high or critical
"""

        try:
            response = generate_text(prompt)

            result = {
                "root_cause": "Infrastructure issue requiring investigation",
                "confidence": 0.65,
                "evidence": f"Cluster of {cluster_count} related complaints",
                "departments_involved": cross_links.get(
                    "departments_involved",
                    [intake_result.get("department", "other")]
                ),
                "recommended_action": "Send inspection team to area",
                "prediction": "Issue will worsen without intervention",
                "failure_risk": "medium"
            }

            for line in response.strip().split('\n'):
                line = line.strip()
                if ':' not in line:
                    continue
                key, _, value = line.partition(':')
                key = key.strip().upper()
                value = value.strip()

                if key == "ROOT_CAUSE":
                    result["root_cause"] = value
                elif key == "CONFIDENCE":
                    try:
                        result["confidence"] = float(value)
                    except ValueError:
                        pass
                elif key == "EVIDENCE":
                    result["evidence"] = value
                elif key == "DEPARTMENTS_INVOLVED":
                    result["departments_involved"] = [
                        d.strip() for d in value.split(',')
                    ]
                elif key == "RECOMMENDED_ACTION":
                    result["recommended_action"] = value
                elif key == "PREDICTION":
                    result["prediction"] = value
                elif key == "FAILURE_RISK":
                    result["failure_risk"] = value.lower()

            return result

        except Exception as e:
            print(f"  [Intelligence] Root cause error: {e}")
            return {
                "root_cause": "Requires manual investigation",
                "confidence": 0.5,
                "evidence": "AI analysis unavailable",
                "departments_involved": [
                    intake_result.get("department", "other")
                ],
                "recommended_action": "Manual inspection required",
                "prediction": "Unknown without further data",
                "failure_risk": "medium"
            }

    def _fraud_check(self, intake_result: dict) -> dict:
        """
        Basic fraud detection rules.
        Full ML fraud detection = planned for v2.
        """
        flags = []

        # Rule 1: Complaint too vague
        problem = intake_result.get('specific_problem', '')
        if len(problem) < 15:
            flags.append("Complaint text too vague")

        # Rule 2: Severity mismatch
        if (intake_result.get('severity') == 'high'
                and intake_result.get('severity_score', 5) < 3):
            flags.append("Severity level mismatch detected")

        return {
            "flagged": len(flags) > 0,
            "flags": flags,
            "review_needed": len(flags) > 0,
            "note": "Basic rule-based check. ML fraud detection in v2."
        }


intelligence_agent = IntelligenceAgent()