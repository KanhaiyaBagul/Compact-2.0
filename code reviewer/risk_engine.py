#!/usr/bin/env python3
import subprocess
import logging
import json
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class RiskEngine:
    def __init__(self, repo_root: Path, llm_client=None):
        """
        Initialise the Risk Prediction Engine.
        
        Args:
            repo_root: Path to the repository to analyse.
            llm_client: Optional LLMClient instance for intelligence.
        """
        self.repo_root = repo_root
        self.llm_client = llm_client

    def _run_git(self, args: List[str]) -> str:
        """Run a git command in the repo root."""
        try:
            result = subprocess.run(
                ['git', '-C', str(self.repo_root)] + args,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode != 0:
                logger.warning(f"Git command failed (code {result.returncode}): {' '.join(args)}\n{result.stderr}")
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"Git execution error: {e}")
            return ""

    def get_commit_history(self, n: int = 50) -> str:
        """Get recent commit history for analysis context."""
        return self._run_git(['log', '--pretty=format:%h | %an | %ar | %s', f'-n {n}'])

    def get_file_churn(self, file_path: str) -> int:
        """Get change frequency (churn) for a specific file."""
        output = self._run_git(['rev-list', '--count', 'HEAD', '--', file_path])
        try:
            return int(output) if output else 0
        except ValueError:
            return 0

    def get_recent_hotspots(self, days: int = 30) -> List[Dict[str, Any]]:
        """Identify files with the most changes in the last X days."""
        output = self._run_git(['log', f'--since={days}.days', '--name-only', '--pretty=format:'])
        files = [f.strip() for f in output.split('\n') if f.strip()]
        
        counts = {}
        for f in files:
            counts[f] = counts.get(f, 0) + 1
            
        sorted_files = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [{"path": f, "changes": c} for f, c in sorted_files[:10]]

    def analyze_risk(self, file_paths: List[str] = None) -> Dict[str, Any]:
        """
        Analyse project risk based on commit history and file churn.
        
        Args:
            file_paths: Optional list of specific files to analyse. If None, looks at overall hotspots.
            
        Returns:
            Dictionary with 'score' (0-10) and 'reasoning'.
        """
        history = self.get_commit_history(30)
        
        if not file_paths:
            hotspots = self.get_recent_hotspots(30)
            file_paths = [h['path'] for h in hotspots]
        else:
            hotspots = [{"path": p, "changes": self.get_file_churn(p)} for p in file_paths]

        if not self.llm_client:
            # Simple heuristic fallback
            max_churn = max([h['changes'] for h in hotspots]) if hotspots else 0
            score = min(10.0, max_churn / 5.0)
            return {
                "score": round(score, 1),
                "reasoning": f"Calculated via local churn heuristic. Max file churn: {max_churn}. (No LLM connected)",
                "hotspots": hotspots[:5]
            }

        prompt = f"""
You are a software risk prediction engine. Analyse the risk level of the following project changes.

RECENT COMMIT HISTORY:
{history}

TOP CHURN/ACTIVITY FILES:
{json.dumps(hotspots, indent=2)}

TASK:
Based on the commit history (frequency of bug fixes, reverts, volatility) and file churn, predict a risk score from 0.0 to 10.0.
- 0.0 - 2.0: Very Stable (mostly docs, refactors, or new features with solid prefix)
- 2.1 - 5.0: Low Risk (normal development activity)
- 5.1 - 7.5: Medium Risk (frequent changes in core files, several bug fixes)
- 7.6 - 9.0: High Risk (high volatility, frequent regression fixes, large churn in critical paths)
- 9.1 - 10.0: Critical Risk (emergency patches, architectural instability, high failure rates)

RESPOND ONLY WITH A JSON OBJECT:
{{
  "score": <float>,
  "reasoning": "<1-2 sentence technical explanation in English>"
}}
"""
        try:
            response = self.llm_client.generate(prompt)
            # Robust JSON extraction
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                # Ensure score is within 0-10
                data["score"] = max(0.0, min(10.0, float(data.get("score", 5.0))))
                return data
            
            # Fallback for Malformed LLM response
            return {"score": 5.0, "reasoning": "Could not parse risk score from AI response."}
            
        except Exception as e:
            logger.error(f"LLM risk analysis failed: {e}")
            return {"score": 0.0, "reasoning": f"Analysis error: {str(e)}"}

if __name__ == "__main__":
    # Integration test for CLI usage
    logging.basicConfig(level=logging.INFO)
    
    # Simple mock or attempt to load from local config if available
    from pathlib import Path
    root = Path("../").resolve() # Default to one level up
    
    # Try to load real LLM client if config.yaml exists
    config_file = root / "code reviewer" / "config.yaml"
    client = None
    if config_file.exists():
        try:
            import yaml
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            from llm_client import create_client_from_config
            client = create_client_from_config(config)
        except Exception as e:
            print(f"Warning: Could not start LLM client: {e}")

    engine = RiskEngine(root, client)
    result = engine.analyze_risk()
    
    print("\n" + "="*40)
    print("--- RISK PREDICTION REPORT ---")
    print("="*40)
    print(f"SCORE: {result['score']}/10.0")
    print(f"REASON: {result['reasoning']}")
    print("="*40 + "\n")
