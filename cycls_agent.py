"""
CyclS Agent for Creative Campaign Generation
Handles user interaction, intent detection, and orchestrates the campaign generation flow.
"""

import re
import json
import os
import cycls
from openai import AsyncOpenAI
from pydantic import BaseModel


def extract_session_id(messages):
    """
    Extract session ID from assistant messages.
    
    Args:
        messages: List of message dicts from conversation history
        
    Returns:
        Session ID string if found, None otherwise
    """
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if isinstance(content, str):
                match = re.search(r"<!--s:(.+?)-->", content)
                if match:
                    return match.group(1)
    return None


# ✅ CONTEXT MODEL
class CampaignContext(BaseModel):
    """
    Data model for campaign context extracted from user input.
    
    Attributes:
        product: Name of the product/service
        description: Additional product description
        category: Product category (food, tech, fashion, etc.)
        audiences: List of target audience descriptions
        tone: Brand/campaign tone (professional, casual, humorous)
        region: Geographic target region
        goal: Campaign objective (awareness, engagement, conversion)
        output_language: Language for output (English/Arabic)
    """
    product: str | None = None
    description: str | None = None
    category: str | None = None
    audiences: list[str] = []
    tone: str | None = None
    region: str | None = None
    goal: str | None = None
    output_language: str = "English"


# ✅ PARSER
async def parse_user_message(message: str) -> CampaignContext:
    """
    Parse user message to extract campaign context using GPT.
    
    Args:
        message: User's input message
        
    Returns:
        CampaignContext object with extracted fields
        
    Note:
        Uses GPT-4o-mini with JSON response format.
        Missing fields are inferred or set to None.
    """
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
                    "- product\n"
                    "- description\n"
                    "- category\n"
                    "- audiences (array)\n"
                    "- tone\n"
                    "- region\n"
                    "- goal (awareness, engagement, conversion)\n"
                    "- output_language\n\n"
                    "Rules:\n"
                    "- Infer missing fields when possible\n"
                    "- Do NOT fail if missing\n"
                    "- audiences must be array\n"
                    "Return ONLY JSON."
                ),
            },
            {"role": "user", "content": message},
        ],
    )

    data = json.loads(r.choices[0].message.content)
    return CampaignContext(**data)


async def detect_intent(message: str):
    """
    Detect user intent from message.
    
    Args:
        message: User's input message
        
    Returns:
        "campaign_request" for campaign creation, "general_question" for general queries
    """
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    r = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify user intent:\n"
                    "1. campaign_request\n"
                    "2. general_question\n\n"
                    "Return ONLY one word."
                ),
            },
            {"role": "user", "content": message},
        ],
    )

    return r.choices[0].message.content.strip()


async def generate_followup_question(ctx, original_message: str):
    """
    Generate a follow-up question when critical campaign information is missing.
    
    Args:
        ctx: Current CampaignContext object
        original_message: Original user message
        
    Returns:
        Question string or "NO_QUESTION" if no clarification needed
        
    Priority order: Goal -> Audience -> Positioning
    """
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    r = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a marketing strategist focused on Riyadh, Saudi Arabia.\n\n"
                    "Decide if a clarification question is needed.\n\n"
                    "You can ask ONLY ONE question if critical info is missing.\n\n"
                    "Priority:\n"
                    "1. Goal (awareness vs conversion)\n"
                    "2. Audience specificity\n"
                    "3. Positioning (premium vs affordable vs trendy)\n\n"
                    "Rules:\n"
                    "- Ask only if necessary\n"
                    "- Keep it short\n"
                    "- If no question needed, return: NO_QUESTION\n"
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "context": ctx.model_dump(),
                    "message": original_message
                })
            },
        ],
    )

    return r.choices[0].message.content.strip()


@cycls.agent(
    image=cycls.Image().pip("openai").pip("python-dotenv").copy("app").copy(".env"),
    web=cycls.Web().auth(cycls.Clerk()),
    memory="2Gi",
)
async def creative_campaign_agent(context):
    """
    Main CyclS agent for creative campaign generation.
    
    Flow:
    1. Parse user message into CampaignContext
    2. Load memory from previous campaigns
    3. Generate campaign via ai_service.run_campaign()
    4. Stream results back to user
    
    Args:
        context: CyclS context object containing messages, session info, etc.
        
    Yields:
        Various message types: thinking status, step updates, narrative content
    """
    from app.services.ai_service import run_campaign
    from app.services.memory import load_memory

    # Initial status
    yield {"type": "thinking", "thinking": "Analyzing your campaign request..."}

    # Extract session ID for maintaining conversation state
    session_id = extract_session_id(context.messages)

    # Parse user message into structured context
    try:
        req = await parse_user_message(context.last_message)
        yield {"type": "step", "step": f"Parsed campaign context"}
    except Exception as e:
        yield {"type": "thinking", "thinking": "Failed to parse.", "done": True}
        yield f"Error: {str(e)}"
        return

    # Load memory from previous campaigns for context
    memory = load_memory()
    yield {"type": "step", "step": f"Loaded memory: {len(memory)} campaigns"}

    # Generate campaign and stream results
    try:
        async for chunk in run_campaign(req):
            if isinstance(chunk, dict):
                if chunk.get("type") == "step":
                    # Progress update
                    yield {"type": "step", "step": chunk.get("content", "")}
                elif chunk.get("type") == "narrative":
                    # Final campaign output
                    yield {"type": "thinking", "thinking": "Done.", "done": True}
                    content = chunk.get("content", "").replace("<br>", "\n")
                    yield content
                elif chunk.get("type") == "error":
                    # Error handling
                    yield {"type": "thinking", "thinking": "Error occurred.", "done": True}
                    yield chunk.get("content", "")
            else:
                # Pass through other chunk types
                yield chunk
    except Exception as e:
        yield {"type": "thinking", "thinking": "Error occurred.", "done": True}
        yield str(e)

    # Append session ID for conversation continuity
    if session_id:
        yield f"\u200B<!--s:{session_id}-->\u200B"


# creative_campaign_agent.local()
creative_campaign_agent.deploy()