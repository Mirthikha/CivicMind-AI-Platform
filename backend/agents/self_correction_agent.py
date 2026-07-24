import json
from typing import Callable, Any, Dict
from gemini_client import generate_text

class SelfCorrectionAgent:
    """
    AGENT 8: Universal Self-Correction Agent (Reflection & Healing Loop)
    
    Targeted quality controller that inspects ANY agent's output across CivicMind.
    If an output is invalid, missing keys, contains empty strings, or fails quality checks,
    it feeds the exact error back to Gemini to self-heal WITHOUT re-running the entire system.
    """

    async def execute_with_correction(
        self,
        agent_name: str,
        agent_func: Callable[..., Any],
        required_keys: list = None,
        min_text_length: int = 10,
        *args,
        max_retries: int = 2,
        **kwargs
    ) -> Any:
        attempts = 0
        last_error = ""

        while attempts < max_retries:
            attempts += 1
            try:
                # 1. Execute targeted agent task
                result = await agent_func(*args, **kwargs)

                # 2A. Validation for String/Text Outputs (e.g., QueryAgent, Explainability)
                if isinstance(result, str):
                    clean_str = result.strip()
                    if len(clean_str) < min_text_length or "technical difficulties" in clean_str.lower():
                        raise ValueError(f"Text output too short or contained error fallback ({len(clean_str)} chars).")
                    return result

                # 2B. Validation for Dictionary/JSON Outputs
                if isinstance(result, dict):
                    if required_keys:
                        missing = [k for k in required_keys if k not in result or result[k] in [None, ""]]
                        if missing:
                            raise ValueError(f"Missing or empty required keys: {missing}")

                    if attempts > 1:
                        result["_self_corrected"] = True
                        result["_correction_attempts"] = attempts

                    return result

                raise ValueError(f"Unexpected output type: {type(result)}")

            except Exception as e:
                last_error = str(e)
                print(f"⚠️ [SelfCorrectionAgent] Flaw detected in '{agent_name}' (Attempt {attempts}/{max_retries}): {last_error}")

                # If retries remain, attempt a targeted self-healing prompt
                if attempts < max_retries:
                    context_input = kwargs.get("complaint_text") or kwargs.get("question") or str(args)
                    correction_prompt = f"""
You previously attempted to process a civic task for agent '{agent_name}', but your output failed validation.

ERROR / FLAW: {last_error}
INPUT CONTEXT: "{context_input}"

Please fix this issue and return a valid, complete response. 
If a JSON payload is required, return ONLY valid JSON matching required keys: {required_keys or []}.
"""
                    try:
                        healed_text = generate_text(correction_prompt)
                        
                        # Try parsing as JSON first
                        if required_keys:
                            if "```json" in healed_text:
                                healed_text = healed_text.split("```json")[1].split("```")[0].strip()
                            elif "```" in healed_text:
                                healed_text = healed_text.split("```")[1].split("```")[0].strip()

                            healed_json = json.loads(healed_text.strip())
                            healed_json["_self_corrected"] = True
                            print(f"✅ [SelfCorrectionAgent] '{agent_name}' successfully self-healed on attempt {attempts + 1}!")
                            return healed_json
                        else:
                            # Return text output if string expected
                            print(f"✅ [SelfCorrectionAgent] '{agent_name}' text output successfully self-healed on attempt {attempts + 1}!")
                            return healed_text.strip()

                    except Exception as heal_err:
                        print(f"❌ [SelfCorrectionAgent] Self-healing failed: {heal_err}")

        print(f"🚨 [SelfCorrectionAgent] '{agent_name}' max retries reached.")
        if required_keys:
            return {"error": last_error, "_fallback_used": True}
        return "I am experiencing temporary technical difficulties processing your request."

self_correction_agent = SelfCorrectionAgent()