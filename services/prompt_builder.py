"""
PromptBuilder — design_doc §6 "LLM Prompt construction"

Combines structured patient fields and free-text clinical notes into a
single prompt string that instructs the LLM to return a JSON report.
"""


class PromptBuilder:
    """
    design_doc §6 — build(structured, free_text) → str

    structured: dict with keys age, gender, temperature, blood_pressure,
                heart_rate, symptoms (list), duration_days, existing_conditions (list)
    free_text:  clinician's free-form clinical notes
    """

    @staticmethod
    def build(structured: dict, free_text: str) -> str:
        symptoms_str = ", ".join(structured.get("symptoms") or []) or "none reported"
        conditions_str = (
            ", ".join(structured.get("existing_conditions") or []) or "none"
        )

        return (
            "You are a clinical decision support assistant.\n"
            "Analyze the following patient information and provide a structured report "
            "in JSON format.\n\n"
            "Patient Information:\n"
            f"- Age: {structured.get('age', 'unknown')}\n"
            f"- Gender: {structured.get('gender', 'unknown')}\n"
            f"- Temperature: {structured.get('temperature', 'unknown')}°C\n"
            f"- Blood Pressure: {structured.get('blood_pressure', 'unknown')}\n"
            f"- Heart Rate: {structured.get('heart_rate', 'unknown')} bpm\n"
            f"- Symptoms: {symptoms_str}\n"
            f"- Duration: {structured.get('duration_days', 'unknown')} days\n"
            f"- Existing Conditions: {conditions_str}\n\n"
            "Clinical Notes from Doctor:\n"
            f"{free_text or 'None provided.'}\n\n"
            "Return ONLY a JSON object with these fields:\n"
            "{\n"
            '  "summary": "...",\n'
            '  "differential_diagnosis": ["...", "..."],\n'
            '  "recommended_investigations": ["...", "..."],\n'
            '  "risk_factors": ["...", "..."]\n'
            "}"
        )
