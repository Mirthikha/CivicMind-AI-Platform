from backend.gemini_client import generate_text


class PrioritizationAgent:
    """
    AGENT 5: Prioritization + Budget Agent

    Uses Gemini for intelligent budget estimation.
    Considers actual problem context, not just fixed tables.
    """

    async def prioritize(self,
                         intake_result: dict,
                         intelligence_result: dict) -> dict:

        # Calculate priority score
        priority_data = self._calculate_priority(
            intake_result, intelligence_result
        )

        # Get Gemini budget estimate
        budget_data = await self._estimate_budget_with_gemini(
            intake_result, intelligence_result
        )

        # Combine both
        return {**priority_data, "budget": budget_data}

    def _calculate_priority(self,
                             intake_result: dict,
                             intelligence_result: dict) -> dict:

        severity_scores = {"low": 2, "medium": 5, "high": 8}
        base = severity_scores.get(
            intake_result.get('severity', 'medium'), 5
        )

        cluster_size = intelligence_result.get('cluster_size', 1)
        cluster_bonus = min(cluster_size * 0.4, 2.0)

        cross_links = intelligence_result.get('cross_dept_links', {})
        cross_bonus = 1.5 if cross_links.get('linked') else 0

        risk_bonuses = {
            "critical": 1.5, "high": 1.0,
            "medium": 0.5, "low": 0.0
        }
        root_cause = intelligence_result.get('root_cause', {})
        failure_risk = root_cause.get('failure_risk', 'medium')
        risk_bonus = risk_bonuses.get(failure_risk, 0.5)

        people = intake_result.get('people_affected', 10)
        people_bonus = min(people / 1000, 1.0)

        priority_score = round(
            min(
                base + cluster_bonus + cross_bonus
                + risk_bonus + people_bonus,
                10.0
            ), 1
        )

        if priority_score >= 8:
            level = "critical"
            response_time = "2 hours"
            color = "red"
        elif priority_score >= 6:
            level = "high"
            response_time = "12 hours"
            color = "orange"
        elif priority_score >= 4:
            level = "medium"
            response_time = "48 hours"
            color = "yellow"
        else:
            level = "low"
            response_time = "7 days"
            color = "green"

        equity_flag = (
            intake_result.get('severity') == 'high'
            and cluster_size <= 2
        )

        return {
            "priority_score": priority_score,
            "priority_level": level,
            "response_time_target": response_time,
            "color_code": color,
            "equity_flag": equity_flag,
            "equity_note": (
                "Area may be underreporting. Consider proactive inspection."
            ) if equity_flag else None,
            "score_breakdown": {
                "base_severity":    base,
                "cluster_bonus":    round(cluster_bonus, 2),
                "cross_dept_bonus": cross_bonus,
                "risk_bonus":       risk_bonus,
                "people_bonus":     round(people_bonus, 2)
            }
        }

    async def _estimate_budget_with_gemini(self,
                                            intake_result: dict,
                                            intelligence_result: dict) -> dict:

        departments = intelligence_result.get(
            'departments_involved',
            [intake_result.get('department', 'other')]
        )
        cluster_size = intelligence_result.get('cluster_size', 1)
        root_cause = intelligence_result.get('root_cause', {})

        prompt = f"""
You are a municipal budget estimation expert in India.

A civic complaint needs budget allocation. Estimate realistic costs.

COMPLAINT DETAILS:
Problem: {intake_result.get('specific_problem')}
Location: {intake_result.get('location')}
Issue Type: {intake_result.get('issue_type')}
Severity: {intake_result.get('severity')} ({intake_result.get('severity_score')}/10)
People Affected: {intake_result.get('people_affected')}
Departments Involved: {departments}
Number of Related Complaints: {cluster_size}
Root Cause: {root_cause.get('root_cause', 'Under investigation')}
Failure Risk: {root_cause.get('failure_risk', 'medium')}

Provide a realistic budget estimate in Indian Rupees (INR).
Consider: labor costs, materials, equipment, and coordination.
Use realistic Indian municipal government costs.

Reply in EXACTLY this format, nothing else:
MINIMUM_COST: number only in rupees e.g. 50000
MAXIMUM_COST: number only in rupees e.g. 200000
IMMEDIATE_ACTION_COST: cost for emergency/temporary fix only
PERMANENT_FIX_COST: cost for complete permanent solution
LABOR_COST: estimated labor portion
MATERIAL_COST: estimated materials portion
TIMELINE_DAYS: estimated days to complete permanent fix
COST_JUSTIFICATION: one sentence explaining the main cost drivers
ITEMIZED: list 3 main cost items separated by semicolons
"""

        try:
            response = generate_text(prompt)

            result = {
                "minimum_cost": 50000,
                "maximum_cost": 200000,
                "immediate_action_cost": 20000,
                "permanent_fix_cost": 150000,
                "labor_cost": 80000,
                "material_cost": 100000,
                "timeline_days": 7,
                "cost_justification": "Standard municipal repair costs",
                "itemized": [],
                "departments_involved": departments,
                "multi_dept": len(departments) > 1,
                "source": "gemini_estimate"
            }

            for line in response.strip().split('\n'):
                line = line.strip()
                if ':' not in line:
                    continue
                key, _, value = line.partition(':')
                key = key.strip().upper()
                value = value.strip()

                if key == "MINIMUM_COST":
                    try:
                        result["minimum_cost"] = int(value)
                    except ValueError:
                        pass
                elif key == "MAXIMUM_COST":
                    try:
                        result["maximum_cost"] = int(value)
                    except ValueError:
                        pass
                elif key == "IMMEDIATE_ACTION_COST":
                    try:
                        result["immediate_action_cost"] = int(value)
                    except ValueError:
                        pass
                elif key == "PERMANENT_FIX_COST":
                    try:
                        result["permanent_fix_cost"] = int(value)
                    except ValueError:
                        pass
                elif key == "LABOR_COST":
                    try:
                        result["labor_cost"] = int(value)
                    except ValueError:
                        pass
                elif key == "MATERIAL_COST":
                    try:
                        result["material_cost"] = int(value)
                    except ValueError:
                        pass
                elif key == "TIMELINE_DAYS":
                    try:
                        result["timeline_days"] = int(value)
                    except ValueError:
                        pass
                elif key == "COST_JUSTIFICATION":
                    result["cost_justification"] = value
                elif key == "ITEMIZED":
                    result["itemized"] = [
                        item.strip()
                        for item in value.split(';')
                        if item.strip()
                    ]

            # Add formatted display values
            result["budget_range"] = (
                f"{self._format_inr(result['minimum_cost'])} "
                f"– {self._format_inr(result['maximum_cost'])}"
            )
            result["immediate_formatted"] = self._format_inr(
                result["immediate_action_cost"]
            )
            result["permanent_formatted"] = self._format_inr(
                result["permanent_fix_cost"]
            )
            result["budget_note"] = (
                f"AI estimate based on {cluster_size} related complaint(s) "
                f"and site conditions. Subject to inspection."
            )

            return result

        except Exception as e:
            print(f"  [Budget] Gemini error: {e}")
            return {
                "minimum_cost": 50000,
                "maximum_cost": 200000,
                "budget_range": "₹50K – ₹2.0L",
                "immediate_formatted": "₹20K",
                "permanent_formatted": "₹1.5L",
                "timeline_days": 7,
                "cost_justification": "Default estimate (AI unavailable)",
                "itemized": [],
                "departments_involved": departments,
                "source": "fallback"
            }

    def _format_inr(self, amount: int) -> str:
        if amount >= 10000000:
            return f"₹{amount/10000000:.1f}Cr"
        elif amount >= 100000:
            return f"₹{amount/100000:.1f}L"
        elif amount >= 1000:
            return f"₹{amount/1000:.0f}K"
        else:
            return f"₹{amount}"


prioritization_agent = PrioritizationAgent()