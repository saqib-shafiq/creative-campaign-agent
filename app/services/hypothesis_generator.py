"""
Hypothesis Generation Module
Generates multiple possible interpretations of user intent
"""

import json
import os
from typing import List, Dict, Any
from openai import AsyncOpenAI

class HypothesisGenerator:
    """Generate and evaluate multiple hypotheses about user intent"""
    
    def __init__(self, emotional_ai=None):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.emotional_ai = emotional_ai
    
    async def generate_hypotheses(self, messages: List[Dict], last_message: str, 
                                   context: Dict) -> List[Dict]:
        """
        Generate 3-5 different hypotheses about what the user wants
        
        Args:
            messages: Full conversation history
            last_message: Most recent user message
            context: Extracted context so far
            
        Returns:
            List of hypotheses with evidence and implications
        """
        
        # Get emotional analysis if available
        emotion_context = ""
        if self.emotional_ai:
            emotion = await self.emotional_ai.analyze_emotional_state(last_message, messages)
            emotion_context = f"\nUser emotional state: {emotion.get('primary_emotion')} (intensity: {emotion.get('emotional_intensity')}/10)"
        
        prompt = f"""
        As a senior marketing strategist, generate multiple hypotheses about what this user wants.
        
        CONVERSATION HISTORY:
        {self._format_conversation(messages[-5:])}
        
        LATEST MESSAGE: "{last_message}"
        
        EXTRACTED CONTEXT SO FAR:
        {json.dumps(context, indent=2)}
        
        {emotion_context}
        
        Generate 3-5 different plausible interpretations of the user's true intent:
        
        For each hypothesis, include:
        1. Hypothesis statement (what they REALLY want, not just what they said)
        2. Evidence from conversation (specific quotes or patterns)
        3. Probability (0-100%)
        4. Implications for our response (what this means for next steps)
        5. Key questions to validate this hypothesis
        
        Consider:
        - Hidden needs (what they're not saying)
        - Business context (ROI, timelines, stakeholders)
        - Expertise level (beginner vs expert)
        - Urgency (immediate vs planning)
        
        Format as JSON array:
        [
            {{
                "hypothesis": "string",
                "evidence": ["quote1", "quote2"],
                "probability": 0-100,
                "implications": {{
                    "action_needed": "what to do",
                    "avoid": "what not to do",
                    "next_question": "validation question if needed"
                }},
                "confidence_factors": ["factor1", "factor2"]
            }}
        ]
        
        The first hypothesis should be the most likely interpretation.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.5,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an expert at reading between the lines and understanding user intent."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            data = json.loads(response.choices[0].message.content)
            
            # Handle both array and object responses
            if isinstance(data, list):
                hypotheses = data
            elif isinstance(data, dict) and "hypotheses" in data:
                hypotheses = data["hypotheses"]
            else:
                hypotheses = [data] if data else []
            
            # Sort by probability
            hypotheses.sort(key=lambda x: x.get("probability", 0), reverse=True)
            
            return hypotheses
            
        except Exception as e:
            print(f"Hypothesis generation error: {e}")
            return self._fallback_hypotheses(last_message, context)
    
    def select_best_hypothesis(self, hypotheses: List[Dict]) -> Dict:
        """Select the most likely hypothesis based on probability and evidence"""
        if not hypotheses:
            return None
        
        # Get highest probability hypothesis
        best = max(hypotheses, key=lambda x: x.get("probability", 0))
        
        # If multiple have similar probability, choose the one with most evidence
        high_prob = [h for h in hypotheses if h.get("probability", 0) > 70]
        if len(high_prob) > 1:
            best = max(high_prob, key=lambda x: len(x.get("evidence", [])))
        
        return best
    
    def get_validation_question(self, hypotheses: List[Dict]) -> str:
        """Generate a question to validate the most likely hypothesis"""
        best = self.select_best_hypothesis(hypotheses)
        
        if best and best.get("implications", {}).get("next_question"):
            return best["implications"]["next_question"]
        
        # Default validation questions
        if hypotheses and len(hypotheses) > 0:
            primary = hypotheses[0]
            probability = primary.get("probability", 50)
            
            if probability < 70:
                return f"Just to confirm, {primary.get('hypothesis', '')[:100]}... Is that accurate?"
        
        return None
    
    def _format_conversation(self, messages: List[Dict]) -> str:
        """Format recent conversation for prompt"""
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:300]
            formatted.append(f"{role.upper()}: {content}")
        return "\n".join(formatted)
    
    def _fallback_hypotheses(self, message: str, context: Dict) -> List[Dict]:
        """Fallback hypotheses without API call"""
        hypotheses = [
            {
                "hypothesis": "User wants a complete marketing campaign",
                "evidence": ["Typical campaign request"],
                "probability": 70,
                "implications": {
                    "action_needed": "Gather full context and generate campaign",
                    "avoid": "Don't provide just tips or general advice",
                    "next_question": None
                },
                "confidence_factors": ["Direct request for campaign"]
            }
        ]
        
        # Adjust based on message length and context
        if len(message) < 30:
            hypotheses[0]["probability"] = 50
            hypotheses[0]["implications"]["next_question"] = "Could you tell me more about your product and target audience?"
        
        if context.get("product"):
            hypotheses[0]["probability"] = 85
            hypotheses[0]["evidence"].append(f"Product mentioned: {context['product']}")
        
        return hypotheses