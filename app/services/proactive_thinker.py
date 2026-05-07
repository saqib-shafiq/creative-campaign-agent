"""
Proactive Thinking Module
Anticipates user needs and prepares resources in advance
"""

import json
import os
from typing import Dict, List, Any
from openai import AsyncOpenAI
from datetime import datetime

class ProactiveThinker:
    """Anticipate user needs and prepare preemptive responses"""
    
    def __init__(self, emotional_ai=None, hypothesis_gen=None):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.emotional_ai = emotional_ai
        self.hypothesis_gen = hypothesis_gen
        self.prepared_resources = {}
    
    async def anticipate_needs(self, messages: List[Dict], last_message: str,
                                context: Dict, hypotheses: List[Dict]) -> Dict:
        """
        Anticipate what the user will need next
        
        Returns:
            Dict with anticipated needs and pre-prepared resources
        """
        
        # Get top hypotheses
        top_hypotheses = hypotheses[:2] if hypotheses else []
        
        prompt = f"""
        Anticipate what this marketing professional will need next.
        
        CURRENT STATE:
        - Latest message: "{last_message}"
        - Context gathered: {json.dumps(context, indent=2)}
        
        MOST LIKELY INTENT (from hypotheses):
        {json.dumps(top_hypotheses, indent=2)}
        
        Based on typical marketing campaign workflows, anticipate:
        
        1. MOST LIKELY NEXT NEED (70-80% probability)
           - What specific resource or information will they need?
           - When will they need it? (immediately, next step, later)
           - Prepare response template or resource
        
        2. POSSIBLE NEXT NEEDS (15-25% probability each)
           - Alternative paths they might take
           - Edge cases to prepare for
        
        3. UNLIKELY BUT IMPORTANT (5% probability)
           - Critical edge cases that would be costly to miss
        
        For each anticipated need, provide:
        - Need description
        - Probability
        - Prepared resource (template, question, or action)
        - Trigger condition (what user action would prompt this)
        - Time estimate for preparation
        
        Format as JSON:
        {{
            "primary_anticipation": {{
                "need": "what they'll need",
                "probability": 0-100,
                "prepared_resource": "template or pre-computed content",
                "trigger": "condition that triggers this",
                "time_to_prepare": "seconds"
            }},
            "secondary_anticipations": [
                {{
                    "need": "...",
                    "probability": 0-100,
                    "prepared_resource": "...",
                    "trigger": "..."
                }}
            ],
            "edge_cases": [
                {{
                    "scenario": "...",
                    "prepared_response": "..."
                }}
            ],
            "resource_caching_recommendations": [
                "what to pre-load or pre-compute"
            ]
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.4,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a proactive strategist who always thinks 3 steps ahead."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            anticipation = json.loads(response.choices[0].message.content)
            
            # Cache prepared resources
            self._cache_resources(anticipation)
            
            return anticipation
            
        except Exception as e:
            print(f"Proactive thinking error: {e}")
            return self._fallback_anticipation(context)
    
    def _cache_resources(self, anticipation: Dict):
        """Cache prepared resources for quick access"""
        # Cache primary anticipation
        if "primary_anticipation" in anticipation:
            primary = anticipation["primary_anticipation"]
            need = primary.get("need", "")
            resource = primary.get("prepared_resource", "")
            if resource:
                self.prepared_resources[need] = {
                    "resource": resource,
                    "cached_at": datetime.now(),
                    "trigger": primary.get("trigger", "")
                }
        
        # Cache secondary anticipations
        for secondary in anticipation.get("secondary_anticipations", []):
            need = secondary.get("need", "")
            resource = secondary.get("prepared_resource", "")
            if resource:
                self.prepared_resources[need] = {
                    "resource": resource,
                    "cached_at": datetime.now(),
                    "trigger": secondary.get("trigger", "")
                }
    
    def get_cached_resource(self, need: str) -> str:
        """Retrieve cached resource if available and fresh"""
        cached = self.prepared_resources.get(need)
        
        if cached:
            # Check if cache is still fresh (less than 5 minutes old)
            age = (datetime.now() - cached["cached_at"]).seconds
            if age < 300:  # 5 minutes
                return cached["resource"]
        
        return None
    
    async def prepare_proactive_response(self, current_action: str, 
                                          user_message: str) -> str:
        """
        Prepare a response that includes proactive suggestions
        
        Args:
            current_action: What we're currently doing (generating, asking, etc.)
            user_message: User's last message
            
        Returns:
            Enhanced response with proactive elements
        """
        
        # Check if we have cached resources that might be relevant
        relevant_needs = []
        for need, cached in self.prepared_resources.items():
            if any(keyword in user_message.lower() for keyword in need.lower().split()):
                relevant_needs.append((need, cached))
        
        if not relevant_needs:
            return None
        
        prompt = f"""
        Enhance this response with proactive suggestions.
        
        CURRENT ACTION: {current_action}
        USER MESSAGE: {user_message}
        
        CACHED RESOURCES THAT MIGHT BE RELEVANT:
        {json.dumps([{"need": n, "resource": r["resource"][:200]} for n, r in relevant_needs])}
        
        Create a natural, helpful proactive addition that:
        1. Anticipates their next likely question
        2. Offers additional value without being pushy
        3. Keeps the conversation flowing naturally
        
        Return just the proactive addition (1-2 sentences).
        Example: "By the way, once we have your campaign, I can also help you plan the rollout schedule."
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.6,
                messages=[
                    {"role": "system", "content": "You add helpful, natural proactive suggestions."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception:
            return None
    
    def _fallback_anticipation(self, context: Dict) -> Dict:
        """Fallback anticipation without API call"""
        
        anticipation = {
            "primary_anticipation": {
                "need": "campaign refinement or iteration",
                "probability": 75,
                "prepared_resource": "Would you like me to adjust the tone, audience focus, or add more platforms?",
                "trigger": "user receives campaign and wants changes",
                "time_to_prepare": "0"
            },
            "secondary_anticipations": [
                {
                    "need": "platform-specific optimization tips",
                    "probability": 50,
                    "prepared_resource": "I can also provide best practices for each platform if needed.",
                    "trigger": "user asks about platform strategy"
                },
                {
                    "need": "competitor comparison",
                    "probability": 30,
                    "prepared_resource": "Would you like me to analyze how this compares to competitors in Riyadh?",
                    "trigger": "user mentions competition"
                }
            ],
            "edge_cases": [],
            "resource_caching_recommendations": [
                "Common platform character limits",
                "Riyadh cultural do's and don'ts"
            ]
        }
        
        self._cache_resources(anticipation)
        return anticipation