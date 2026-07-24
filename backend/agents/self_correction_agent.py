import json
from typing import Callable, Any, Dict
from gemini_client import generate_text

class SelfCorrectionAgent:
    """
    AGENT 8: Universal Self-Correction Agent (Reflection & Healing Loop)
    Targeted quality controller that inspects ANY agent's output across CivicMind.
    """

    async def execute_with_correction(
        self,
        agent_name: str,
        agent_func: Callable[..., Any],
        *args,
        required_keys: list = None,
        min_text_length: int = 10,
        max_retries: int = 2,
        **kwargs
    ) -> Any:
        attempts = 0
        last_error = ""

        while attempts < max_retries:
            attempts += 1
            try:
                # 1. Run target agent function safely
                result = await agent_func(*args, **kwargs)

                # 2A. If string JSON returned but required_keys dictionary expected
                if isinstance(result, str) and required_keys:
                    clean_text = result.strip()
                    if "```json" in clean_text:
                        clean_text = clean_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean_text:
                        clean_text = clean_text.split("```")[1].split("```")[0].strip()
                    
                    try:
                        result = json.loads(clean_text)
                    except Exception:
                        if len(required_keys) == 1:
                            result = {required_keys[0]: clean_text}
                        else:
                            raise ValueError(f"Output was string but could not parse as JSON for keys: {required_keys}")

                # 2B. Validation for String Outputs (e.g. Chat/Query response)
                if isinstance(result, str) and not required_keys:
                    clean_str = result.strip()
                    if len(clean_str) < min_text_length or "technical difficulties" in clean_str.lower():
                        raise ValueError(f"Text output too short ({len(clean_str)} chars).")
                    return clean_str

                # 2C. Validation for Dictionary/JSON Outputs
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

                if attempts < max_retries:
                    context_input = kwargs.get("complaint_text") or kwargs.get("question") or (str(args[0]) if args else "")
                    correction_prompt = f"""
You previously attempted to process a civic task for agent '{agent_name}', but your output failed validation.

ERROR / FLAW: {last_error}
INPUT CONTEXT: "{context_input}"

Please fix this issue and return a valid response.
If a JSON payload is required, return ONLY valid JSON matching required keys: {required_keys or []}.
"""
                    try:
                        healed_text = generate_text(correction_prompt)
                        
                        if required_keys:
                            if "```json" in healed_text:
                                healed_text = healed_text.split("```json")[1].split("```")[0].strip()
                            elif "```" in healed_text:
                                healed_text = healed_text.split("```")[1].split("```")[0].strip()

                            try:
                                healed_json = json.loads(healed_text.strip())
                            except Exception:
                                if len(required_keys) == 1:
                                    healed_json = {required_keys[0]: healed_text.strip()}
                                else:
                                    raise

                            healed_json["_self_corrected"] = True
                            print(f"✅ [SelfCorrectionAgent] '{agent_name}' successfully self-healed on attempt {attempts + 1}!")
                            return healed_json
                        else:
                            print(f"✅ [SelfCorrectionAgent] '{agent_name}' text output successfully self-healed on attempt {attempts + 1}!")
                            return healed_text.strip()

                    except Exception as heal_err:
                        print(f"❌ [SelfCorrectionAgent] Self-healing failed: {heal_err}")

        print(f"🚨 [SelfCorrectionAgent] '{agent_name}' max retries reached. Returning direct fallback.")
        try:
            return await agent_func(*args, **kwargs)
        except Exception:
            if required_keys:
                fallback = {k: "Under Review" for k in required_keys}
                fallback["_fallback_used"] = True
                return fallback
            return "Processing request..."

self_correction_agent = SelfCorrectionAgent()