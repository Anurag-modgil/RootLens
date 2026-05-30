import json
import logging
from typing import List, Dict, Any, Optional
import openai
from app.config import settings
from app.models import Incident, Log

logger = logging.getLogger("rootlens.rca")

class RootCauseAnalysisEngine:
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        
        # Initialize OpenAI client if valid key exists
        if self.api_key and self.api_key != "mock-key":
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("Using MOCK OpenAI client since OPENAI_API_KEY is not set or set to 'mock-key'.")

    def analyze_incident(
        self,
        incident: Incident,
        logs: List[Log],
        service_metadata: Dict[str, Any],
        historical_resolutions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Runs LLM Root-Cause Analysis on the incident, using cluster logs, service metadata,
        and historical solutions from RAG. Returns a structured dict.
        """
        logger.info(f"Running Root Cause Analysis for Incident ID: {incident.id}")

        # 1. Format prompt inputs
        log_samples_str = "\n".join([
            f"[{log.timestamp.isoformat()}] {log.service_name} - {log.log_level}: {log.message}"
            for log in logs[:10]
        ])

        service_metadata_str = json.dumps(service_metadata, indent=2)

        resolutions_str = ""
        if historical_resolutions:
            for idx, res in enumerate(historical_resolutions):
                resolutions_str += f"\n--- Solution {idx+1} (Score: {res['score']:.4f}) ---\n"
                resolutions_str += f"Title: {res['title']}\n"
                resolutions_str += f"Description: {res['description']}\n"
                resolutions_str += f"Solution: {res['solution']}\n"
        else:
            resolutions_str = "No similar historical incidents found."

        system_prompt = (
            "You are an expert site reliability engineer (SRE) and AI assistant for system diagnostics.\n"
            "Your task is to perform a detailed Root Cause Analysis (RCA) based on log entries, service metadata, and relevant historical incident resolutions.\n\n"
            "You MUST respond strictly with a valid JSON object containing these keys:\n"
            "{\n"
            '  "root_cause": "A concise explanation of the root cause.",\n'
            '  "confidence_score": 0.85,\n'
            '  "impact": "Detailed assessment of the failure\'s impact across services.",\n'
            '  "recommended_fix": "Precise recommendation or shell command to resolve the issue."\n'
            "}\n"
            "Do not return any other text, markdown formatting, or HTML tags. Just the raw JSON object."
        )

        user_prompt = (
            f"--- CURRENT INCIDENT ---\n"
            f"Title: {incident.title}\n"
            f"Description: {incident.description}\n\n"
            f"--- SERVICE METADATA ---\n"
            f"{service_metadata_str}\n\n"
            f"--- LOG SAMPLES ---\n"
            f"{log_samples_str}\n\n"
            f"--- RELEVANT HISTORICAL RESOLUTIONS ---\n"
            f"{resolutions_str}\n\n"
            f"Perform the RCA and return the JSON diagnostics output."
        )

        # 2. Call OpenAI API or fall back to mock
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                response_text = response.choices[0].message.content
                analysis = json.loads(response_text)
                logger.info(f"RCA completed successfully for Incident ID: {incident.id}")
                return analysis
            except Exception as e:
                logger.error(f"OpenAI API call failed: {str(e)}. Falling back to mock diagnostics.")

        # Mock response generator (semantic fallback)
        logger.info(f"Generating mock RCA diagnostics for Incident ID: {incident.id}")
        return self._generate_mock_rca(incident, logs)

    def _generate_mock_rca(self, incident: Incident, logs: List[Log]) -> Dict[str, Any]:
        """
        Generate realistic RCA output based on incident logs.
        """
        combined_logs = " ".join([l.message.lower() for l in logs])
        
        root_cause = "General service error or warning spike detected."
        recommended_fix = "echo 'Please inspect logs manually.'"
        impact = "Minor service degradation."
        confidence = 0.65

        if "db" in combined_logs or "connection" in combined_logs or "timeout" in combined_logs:
            root_cause = "Database connection pool exhaustion caused by high traffic spikes or slow queries."
            recommended_fix = "docker restart payment-gateway"
            impact = "Database connection timeouts blocking transactions."
            confidence = 0.92
        elif "space" in combined_logs or "disk" in combined_logs or "full" in combined_logs:
            root_cause = "Disk space exhaustion on app node '/var/log' partition."
            recommended_fix = "redis-cli flushall"
            impact = "Write operations failing, log writes blocking threads."
            confidence = 0.88

        return {
            "root_cause": root_cause,
            "confidence_score": confidence,
            "impact": impact,
            "recommended_fix": recommended_fix
        }
