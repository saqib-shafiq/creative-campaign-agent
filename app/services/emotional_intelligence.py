"""
Emotional Intelligence Module
Analyzes and adapts to user emotions for better interactions
"""

import re
from typing import Dict, List, Any
from openai import AsyncOpenAI
import os

class EmotionalIntelligence:
    """Understand and respond to user emotions"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.emotion_history = []
    
    async def analyze_emotional_state(self, message: str, history: List[Dict]) -> Dict[str, Any]:
        """
        Analyze user's emotional state from message and history
        
        Returns:
            Dict with emotion, intensity, concerns, etc.
        """
        # Prepare history (last 3 exchanges)
        recent_history = history[-3:] if len(history) > 3 else history
        
        prompt = f"""
        Analyze the emotional state of this marketing professional based on their message.
        
        CURRENT MESSAGE: "{message}"
        
        PREVIOUS EXCHANGES:
        {self._format_history(recent_history)}
        
        Provide analysis as JSON:
        {{
            "primary_emotion": "excitement|frustration|confusion|confidence|hesitation|urgency|casual",
            "emotional_intensity": 1-10,
            "underlying_concerns": "what they might be worried about but not saying",
            "communication_style": "direct|indirect|detailed|brief|technical|casual",
            "trust_level": 1-10,
            "urgency_level": 1-10,
            "response_adaptation": {{
                "should_match_emotion": true/false,
                "suggested_tone": "empathetic|enthusiastic|professional|reassuring|urgent",
                "emoji_usage": "none|minimal|moderate|high",
                "formality_level": "very_formal|formal|casual|very_casual"
            }}
        }}
        
        Base this purely on language patterns, word choice, punctuation, and message length.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.3,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an expert in emotional intelligence and communication analysis."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            # Store in history
            self.emotion_history.append({
                "timestamp": datetime.now(),
                "message": message[:100],
                "analysis": analysis
            })
            
            return analysis
            
        except Exception as e:
            # Fallback to basic analysis
            return self._basic_emotion_analysis(message)
    
    def adapt_response_tone(self, response: str, emotional_analysis: Dict) -> str:
        """
        Adapt response based on emotional analysis
        """
        if not emotional_analysis:
            return response
        
        emotion = emotional_analysis.get("primary_emotion", "")
        intensity = emotional_analysis.get("emotional_intensity", 5)
        adaptation = emotional_analysis.get("response_adaptation", {})
        
        # Handle high frustration
        if emotion == "frustration" and intensity > 6:
            prefix = "I understand this can be frustrating. Let me help you work through it.\n\n"
            response = prefix + response
            # Simplify language
            response = response.replace("Additionally,", "").replace("Furthermore,", "")
            
        # Match excitement
        elif emotion == "excitement" and intensity > 6:
            # Add exclamation marks and emojis
            if not response.endswith("!"):
                response = response.replace(".", "!").replace("?", "!")
            if adaptation.get("emoji_usage") == "moderate":
                response += " 🎉"
                
        # Handle confusion
        elif emotion == "confusion":
            # Add structure and clarification
            response = "Let me break this down clearly:\n\n" + response
            if "?" not in response:
                response += "\n\nDoes that help clarify?"
                
        # Handle urgency
        elif emotion == "urgency" and emotional_analysis.get("urgency_level", 0) > 6:
            # Be more direct and action-oriented
            response = f"Quick response: {response}"
            response = response.replace("I think", "I recommend")
            response = response.replace("perhaps", "")
            
        # Handle hesitation/low confidence
        elif emotion == "hesitation":
            # Add reassurance
            response = "Great question! " + response
            response += "\n\nI'm here to help you through every step."
            
        # Default: adjust formality
        formality = adaptation.get("formality_level", "casual")
        if formality == "formal" and "I'm" in response:
            response = response.replace("I'm", "I am")
            response = response.replace("it's", "it is")
        elif formality == "casual" and "I am" in response:
            response = response.replace("I am", "I'm")
            response = response.replace("it is", "it's")
        
        return response
    
    def _format_history(self, history: List[Dict]) -> str:
        """Format conversation history for analysis"""
        formatted = []
        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]  # Limit length
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)
    
    def _basic_emotion_analysis(self, message: str) -> Dict:
        """Fallback basic analysis without API call"""
        message_lower = message.lower()
        
        # Simple keyword-based detection
        emotions = {
            "excitement": ["excited", "amazing", "great", "wow", "love", "perfect"],
            "frustration": ["frustrated", "annoying", "why", "not working", "error"],
            "confusion": ["confused", "unclear", "don't understand", "what do you mean"],
            "urgency": ["urgent", "asap", "quick", "fast", "now", "immediately"],
            "hesitation": ["maybe", "not sure", "perhaps", "could", "might"]
        }
        
        detected = "casual"
        max_score = 0
        
        for emotion, keywords in emotions.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > max_score:
                max_score = score
                detected = emotion
        
        intensity = min(10, max_score * 3)
        
        return {
            "primary_emotion": detected,
            "emotional_intensity": intensity,
            "underlying_concerns": "Unclear from basic analysis",
            "communication_style": "casual" if len(message) < 100 else "detailed",
            "trust_level": 5,
            "urgency_level": intensity if detected == "urgency" else 3,
            "response_adaptation": {
                "should_match_emotion": True,
                "suggested_tone": "empathetic" if detected == "frustration" else "professional",
                "emoji_usage": "minimal",
                "formality_level": "casual"
            }
        }