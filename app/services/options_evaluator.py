"""
Options Evaluation Module
Evaluates different action options based on hypotheses and context
"""

import json
import os
from typing import List, Dict, Any
from openai import AsyncOpenAI

class OptionsEvaluator:
    """Evaluate multiple possible actions and choose the best"""
    
    def __init__(self, emotional_ai=None, hypothesis_gen=None):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.emotional_ai = emotional_ai
        self.hypothesis_gen = hypothesis_gen
    
    async def evaluate_options(self, messages: List[Dict], last_message: str,
                                context: Dict, hypotheses: List[Dict]) -> Dict:
        """
        Evaluate possible actions and select the best
        
        Returns:
            Dict with selected action, reasoning, and confidence
        """
        
        # Define possible actions
        possible_actions = [
            {
                "name": "generate_campaign",
                "description": "Generate full marketing campaign",
                "when_to_use": "When enough context exists (product, audience, goal)"
            },
            {
                "name": "ask_clarifying_question",
                "description": "Ask one specific follow-up question",
                "when_to_use": "When missing critical information"
            },
            {
                "name": "provide_guidance",
                "description": "Give marketing tips and suggestions",
                "when_to_use": "When user is exploring or learning"
            },
            {
                "name": "reframe_request",
                "description": "Help user clarify what they really need",
                "when_to_use": "When user seems confused or request is unclear"
            },
            {
                "name": "escalate_question",
                "description": "Ask multiple questions to gather full context",
                "when_to_use": "When completely missing essential information"
            }
        ]
        
        # Get emotional context if available
        emotion_impact = ""
        if self.emotional_ai:
            emotion = await self.emotional_ai.analyze_emotional_state(last_message, messages)
            emotion_impact = f"""
            User emotion: {emotion.get('primary_emotion')} (intensity: {emotion.get('emotional_intensity')}/10)
            Urgency level: {emotion.get('urgency_level')}/10
            
            Impact on options:
            - High urgency: prioritize fast actions
            - High frustration: avoid asking too many questions
            - Confusion: provide clear structure
            - Excitement: can generate campaign with less context
            """
        
        prompt = f"""
        As a strategic decision maker, evaluate which action to take.
        
        SITUATION:
        - Latest message: "{last_message}"
        - Extracted context: {json.dumps(context, indent=2)}
        
        HYPOTHESES ABOUT USER INTENT:
        {json.dumps(hypotheses[:2] if hypotheses else [], indent=2)}
        
        {emotion_impact}
        
        POSSIBLE ACTIONS:
        {json.dumps(possible_actions, indent=2)}
        
        Evaluate each option based on:
        1. Alignment with user's likely intent (from hypotheses)
        2. Information completeness (what we know vs need)
        3. User's emotional state
        4. Risk of wrong action
        5. Time to value for user
        
        For each action, provide:
        - Suitability score (0-100)
        - Reasoning
        - Risks
        - Expected outcome
        
        Then select the best action and provide:
        - Final decision
        - Confidence level
        - Specific action parameters (e.g., which question to ask)
        - Fallback plan if this action fails
        
        Return as JSON:
        {{
            "evaluations": [
                {{
                    "action": "action_name",
                    "score": 0-100,
                    "reasoning": "...",
                    "risks": ["risk1", "risk2"],
                    "expected_outcome": "..."
                }}
            ],
            "selected_action": {{
                "name": "action_name",
                "confidence": 0-100,
                "parameters": {{
                    "question": "specific question if asking",
                    "context_to_use": "what context to leverage"
                }},
                "reasoning_summary": "...",
                "fallback": "fallback action if this fails"
            }}
        }}
        
        Be decisive. If confidence > 70%, proceed. If lower, choose a safer option.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.3,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an expert strategic decision maker."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            evaluation = json.loads(response.choices[0].message.content)
            return evaluation
            
        except Exception as e:
            print(f"Options evaluation error: {e}")
            return self._fallback_evaluation(context, hypotheses)
    
    def _fallback_evaluation(self, context: Dict, hypotheses: List[Dict]) -> Dict:
        """Fallback evaluation without API call"""
        
        # Determine if we have enough info
        has_product = bool(context.get("product"))
        has_audience = bool(context.get("audiences"))
        has_goal = bool(context.get("goal"))
        
        info_score = sum([has_product, has_audience, has_goal])
        
        if info_score >= 2:
            selected_action = "generate_campaign"
            confidence = 70 + (info_score * 10)
        elif info_score == 1:
            selected_action = "ask_clarifying_question"
            confidence = 60
        else:
            selected_action = "escalate_question"
            confidence = 50
        
        # Determine question based on what's missing
        question = None
        if selected_action == "ask_clarifying_question":
            if not has_product:
                question = "Could you tell me more about your product?"
            elif not has_audience:
                question = "Who is your target audience for this campaign?"
            elif not has_goal:
                question = "What's the primary goal of this campaign?"
        
        return {
            "evaluations": [],
            "selected_action": {
                "name": selected_action,
                "confidence": confidence,
                "parameters": {"question": question},
                "reasoning_summary": f"Based on information completeness: {info_score}/3",
                "fallback": "ask_clarifying_question"
            }
        }