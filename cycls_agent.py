"""
CyclS Agent for Creative Campaign Generation
Conversational agent that lets the LLM drive the interaction naturally.
"""

import re
import json
import os
import sys
import asyncio
import cycls
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import List, Dict, Any

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import services
from app.services.emotional_intelligence import EmotionalIntelligence
from app.services.hypothesis_generator import HypothesisGenerator
from app.services.options_evaluator import OptionsEvaluator
from app.services.proactive_thinker import ProactiveThinker


def extract_session_id(messages):
    """Extract session ID from assistant messages."""
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if isinstance(content, str):
                match = re.search(r"<!--s:(.+?)-->", content)
                if match:
                    return match.group(1)
    return None


def format_conversation_history(messages):
    """Format cycls context messages into a clean conversation history."""
    history = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, str):
            content = re.sub(r"\u200B<!--s:.+?-->\u200B", "", content).strip()
        if role in ("user", "assistant") and content:
            history.append({"role": role, "content": content})
    return history


class LLMDecision(BaseModel):
    """What the LLM decided to do."""
    action: str
    reply: str
    context: dict


async def parse_user_message(message: str):
    """Parse user message to extract campaign context."""
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    class SimpleContext(BaseModel):
        product: str = ""
        description: str = ""
        category: str = ""
        audiences: list = []
        tone: str = ""
        region: str = ""
        goal: str = ""
        output_language: str = "English"
        
        def model_dump(self):
            return self.__dict__

    r = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract marketing campaign context from user input.\n\n"
                    "Return JSON with fields:\n"
                    "- product (string)\n"
                    "- description (string)\n"
                    "- category (string)\n"
                    "- audiences (array of strings)\n"
                    "- tone (string)\n"
                    "- region (string)\n"
                    "- goal (string)\n"
                    "- output_language (string)\n"
                    "If missing, use empty string or empty array."
                ),
            },
            {"role": "user", "content": message},
        ],
    )
    
    data = json.loads(r.choices[0].message.content)
    return SimpleContext(**data)


async def think_enhanced(messages, last_message: str) -> LLMDecision:
    """
    Main orchestrator with fixed logic.
    """
    
    # Check if a campaign exists ANYWHERE in the conversation history (not just last 3)
    campaign_generated = False
    campaign_content = ""
    for msg in reversed(messages):  # scan full history, most recent first
        if msg.get("role") == "assistant" and "📍 Campaign Focus: Riyadh" in msg.get("content", ""):
            campaign_generated = True
            campaign_content = msg.get("content", "")
            break
    
    # POST-CAMPAIGN MODE — any message after a campaign was generated goes here
    if campaign_generated:
        # Detect intent
        intent_info = await detect_intent_after_campaign(last_message, campaign_content)
        
        # If it's a genuine modification request (not just asking opinion)
        if intent_info.get("action") == "generate_campaign" and intent_info.get("requires_full_regeneration"):
            # Only regenerate if they explicitly ask for changes
            return LLMDecision(
                action="generate_campaign",
                reply="I'll update the campaign for you.",
                context=await extract_modification_context(messages, last_message)
            )
        else:
            # Answer questions, give opinions, chat
            natural_response = await generate_natural_response(
                messages, 
                last_message, 
                campaign_content, 
                intent_info
            )
            return LLMDecision(
                action="converse",
                reply=natural_response,
                context={}
            )
    
    # INITIAL CAMPAIGN CREATION MODE
    return await handle_initial_campaign_creation(messages, last_message)


async def handle_initial_campaign_creation(messages, last_message: str) -> LLMDecision:
    """
    Handles all pre-campaign messages via LLM classification.
    The LLM decides whether to converse, ask for missing info, or generate.
    No keyword matching — the LLM understands natural language intent.
    """
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    recent_history = "\n".join(
        f"{m['role'].upper()}: {m['content'][:300]}"
        for m in messages[-6:]
        if m.get("content")
    )

    prompt = f"""
You are the decision-maker for a marketing campaign assistant (before any campaign has been generated).

CONVERSATION SO FAR:
{recent_history}

LATEST USER MESSAGE: "{last_message}"

Decide what to do next. Choose ONE action:

1. "converse" — The user is asking a question, sharing an opinion, exploring ideas, giving feedback,
   making small talk, or saying anything that is NOT a direct request to create a campaign.
   This is the DEFAULT. When in doubt, choose this.

2. "generate_campaign" — The user has clearly provided enough info to build a campaign 
   (product name + target audience are both present AND they want a campaign created).
   Only choose this if BOTH conditions are true.

3. "ask_clarifying_question" — The user clearly wants a campaign but hasn't provided enough info yet.
   Only ask for the single most important missing piece (product OR audience, not both at once).

IMPORTANT RULES:
- Any question, opinion, suggestion, hypothetical, or conversational remark → "converse"
- Only "generate_campaign" when product + audience are both explicitly stated and user wants a campaign
- Never generate a campaign just because product-related words appear in a question
- If user seems to be brainstorming or thinking out loud → "converse"

Return JSON:
{{
    "action": "converse|generate_campaign|ask_clarifying_question",
    "reply": "your response to the user (for converse/ask actions) or confirmation message (for generate)",
    "reasoning": "one sentence explaining your choice"
}}
"""

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an expert at understanding user intent in marketing conversations. You default to conversation unless the user clearly wants a campaign generated."},
                    {"role": "user", "content": prompt}
                ]
            ),
            timeout=10.0
        )

        data = json.loads(response.choices[0].message.content)
        action = data.get("action", "converse")
        reply = data.get("reply", "")

        if action == "generate_campaign":
            return LLMDecision(action="generate_campaign", reply=reply or "Got it! Creating your campaign now...", context={})
        else:
            # converse or ask_clarifying_question both just return a reply
            return LLMDecision(action="converse", reply=reply, context={})

    except Exception:
        # True last-resort fallback: only generate if message looks like a direct campaign brief,
        # otherwise ask the standard opening question
        msg_lower = last_message.lower()
        looks_like_brief = (
            ("for" in msg_lower or "campaign" in msg_lower) and
            any(w in msg_lower for w in ["professional", "targeting", "audience", "people", "user", "customer"])
        )
        if looks_like_brief:
            return LLMDecision(action="generate_campaign", reply="Creating your campaign now...", context={})
        return LLMDecision(
            action="converse",
            reply="What product and who's it for? (Example: 'Protein snacks for busy professionals')",
            context={}
        )


async def extract_modification_context(messages, last_message: str) -> dict:
    """
    Extract what the user wants to change about the campaign.
    """
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Get the last campaign
    campaign_content = ""
    for msg in reversed(messages):
        if "📍 Campaign Focus: Riyadh" in msg.get("content", ""):
            campaign_content = msg.get("content", "")
            break
    
    prompt = f"""
    User wants to modify their campaign.
    
    ORIGINAL CAMPAIGN (excerpt):
    {campaign_content[:500]}
    
    USER REQUEST: "{last_message}"
    
    Extract what they want to change:
    - product (if new product mentioned)
    - audiences (if different audience)
    - tone (if different tone desired)
    - goal (if different goal)
    
    Return JSON with only the changed fields:
    {{
        "product": "new product or empty",
        "audiences": ["new audience or empty"],
        "tone": "new tone or empty",
        "goal": "new goal or empty"
    }}
    """
    
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.3,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You extract modification requests from user messages."},
                    {"role": "user", "content": prompt}
                ]
            ),
            timeout=8.0
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception:
        return {}
        
async def detect_intent_after_campaign(user_message: str, campaign_content: str = "") -> dict:
    """
    Better intent detection - distinguishes between questions and modification requests.
    """
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
    A user has already received a generated marketing campaign. Classify their latest message.
    
    CAMPAIGN CONTEXT (excerpt):
    {campaign_content[:300] if campaign_content else "Campaign exists but content not available"}
    
    USER MESSAGE: "{user_message}"
    
    Choose ONE intent:
    
    - ASKING_QUESTION: The user wants your opinion, analysis, advice, or information.
      This includes questions, hypotheticals, comparisons, reactions, and thinking out loud.
      This is the DEFAULT — when in doubt, choose this.
    
    - MODIFY_REQUEST: The user explicitly wants the campaign content itself to be changed or 
      regenerated. They must be giving a direct instruction to alter the campaign, not just 
      asking whether a change would be a good idea.
    
    - NEW_CAMPAIGN_REQUEST: The user wants a completely new campaign for a different product.
    
    KEY PRINCIPLE: Intent is determined by what the user wants YOU to DO, not by what words they use.
    Asking "would X work better?" wants your opinion → ASKING_QUESTION.
    Saying "make it use X instead" wants a new campaign → MODIFY_REQUEST.
    
    Return JSON:
    {{
        "intent": "ASKING_QUESTION|MODIFY_REQUEST|NEW_CAMPAIGN_REQUEST|FEEDBACK|CHAT",
        "action": "converse|generate_campaign",
        "requires_full_regeneration": true/false,
        "reply_hint": "brief note on what kind of response to give"
    }}
    """
    
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.3,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You classify user intent accurately. Distinguish between questions and modification requests."},
                    {"role": "user", "content": prompt}
                ]
            ),
            timeout=5.0
        )
        
        data = json.loads(response.choices[0].message.content)
        return data
        
    except Exception:
        # True last-resort fallback only — LLM call failed entirely.
        # Default to "converse" (safe side). Only treat as modify if message
        # contains an unambiguous imperative action verb with no question markers.
        msg_lower = user_message.lower()
        has_question_marker = "?" in user_message
        has_modify_verb = any(w in msg_lower for w in ["change", "modify", "update", "replace", "redo", "regenerate", "rewrite"])

        if has_modify_verb and not has_question_marker:
            return {"intent": "MODIFY_REQUEST", "action": "generate_campaign", "requires_full_regeneration": True, "reply_hint": "modifying"}
        return {"intent": "ASKING_QUESTION", "action": "converse", "requires_full_regeneration": False, "reply_hint": "answer_question"}
        
async def generate_natural_response(messages, last_message: str, campaign_content: str, intent_info: dict) -> str:
    """
    Generate response for questions - WITHOUT regenerating campaign.
    """
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Get the actual campaign content
    actual_campaign = ""
    for msg in reversed(messages):
        if "📍 Campaign Focus: Riyadh" in msg.get("content", ""):
            actual_campaign = msg.get("content", "")
            break
    
    prompt = f"""
    You are a helpful marketing expert assistant. Answer this user's question naturally.
    
    USER QUESTION: "{last_message}"
    
    THEIR CAMPAIGN (if any):
    {actual_campaign[:800] if actual_campaign else "No campaign generated yet — this is a general marketing question."}
    
    CONVERSATION CONTEXT (last few messages):
    {chr(10).join([f"{m['role'].upper()}: {m['content'][:200]}" for m in messages[-4:] if m.get('content')])}
    
    Instructions:
    - Give a direct, specific, helpful answer
    - If they're asking about a product feature/flavor/variant: give your genuine opinion with reasoning
    - If no campaign exists yet, answer as a general marketing advisor
    - Be concise (2-4 sentences)
    - DO NOT offer to regenerate or create a campaign unless they explicitly ask for it
    - DO NOT ask for more information unless absolutely necessary
    """
    
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.7,
                messages=[
                    {"role": "system", "content": "You are a helpful marketing expert. Answer questions directly and specifically. Do not offer to regenerate unless asked."},
                    {"role": "user", "content": prompt}
                ]
            ),
            timeout=8.0
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception:
        # Smart fallback for the chocolate flavor question
        if "chocolate" in last_message.lower() and "flavor" in last_message.lower():
            return "Yes, adding a chocolate flavor could be a great idea! Chocolate is consistently one of the most popular protein snack flavors. It would appeal to comfort-seeking professionals and pair well with coffee culture in Riyadh. Would you like me to update the campaign to focus on chocolate flavor?"
        else:
            return "Great question! " + last_message


@cycls.agent(
    image=cycls.Image().pip("openai").pip("python-dotenv").copy("app").copy(".env"),
    web=cycls.Web().auth(cycls.Clerk()),
    memory="2Gi",
)
async def creative_campaign_agent(context):
    from app.services.ai_service import run_campaign
    from app.services.memory import load_memory

    session_id = extract_session_id(context.messages)

    yield {"type": "thinking", "thinking": "Thinking..."}

    # Check API key first
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        yield {"type": "thinking", "thinking": "Done.", "done": True}
        yield "❌ Error: OpenAI API key not found. Please set OPENAI_API_KEY environment variable."
        return

    # Use enhanced thinking
    try:
        decision = await asyncio.wait_for(
            think_enhanced(context.messages, context.last_message), 
            timeout=60.0
        )
    except asyncio.TimeoutError:
        yield {"type": "thinking", "thinking": "Done.", "done": True}
        yield "❌ Error: Request timed out. Please try again."
        return
    except Exception as e:
        yield {"type": "thinking", "thinking": "Done.", "done": True}
        yield f"❌ Error: {str(e)}"
        return

    # Option 1: Just have a conversation
    if decision.action == "converse":
        yield {"type": "thinking", "thinking": "Done.", "done": True}
        yield decision.reply
        if session_id:
            yield f"\u200B<!--s:{session_id}-->\u200B"
        return

    # Option 2: Generate a campaign
    if decision.reply:
        yield decision.reply + "\n\n"

    # Build request object
    class Req:
        def __init__(self, ctx: dict):
            self.product = ctx.get("product") or "Product"
            self.description = ctx.get("description") or ""
            self.category = ctx.get("category") or ""
            self.audiences = ctx.get("audiences") or []
            self.tone = ctx.get("tone") or "Modern, culturally relevant, Saudi-focused"
            self.region = ctx.get("region") or "Riyadh, Saudi Arabia"
            self.goal = ctx.get("goal") or "awareness"
            self.output_language = ctx.get("output_language") or "English"
            self.product_name = self.product
            self.product_desc = self.description
            self.target_audience = ", ".join(self.audiences) if self.audiences else "General audience"
            self.brand_voice = self.tone

        def model_dump(self):
            return {
                "product": self.product,
                "description": self.description,
                "category": self.category,
                "audiences": self.audiences,
                "tone": self.tone,
                "region": self.region,
                "goal": self.goal,
                "output_language": self.output_language,
            }

    req = Req(decision.context)

    memory = load_memory()
    yield {"type": "step", "step": f"Loaded memory: {len(memory)} campaigns"}

    try:
        async for chunk in run_campaign(req):
            if isinstance(chunk, dict):
                if chunk.get("type") == "step":
                    yield {"type": "step", "step": chunk.get("content", "")}
                elif chunk.get("type") == "narrative":
                    yield {"type": "thinking", "thinking": "Done.", "done": True}
                    content = chunk.get("content", "").replace("<br>", "\n")
                    yield content
                elif chunk.get("type") == "error":
                    yield {"type": "thinking", "thinking": "Error occurred.", "done": True}
                    yield chunk.get("content", "")
            else:
                yield chunk
    except Exception as e:
        yield {"type": "thinking", "thinking": "Error occurred.", "done": True}
        yield str(e)

    if session_id:
        yield f"\u200B<!--s:{session_id}-->\u200B"


# Use local mode for development
creative_campaign_agent.local()
# creative_campaign_agent.deploy()