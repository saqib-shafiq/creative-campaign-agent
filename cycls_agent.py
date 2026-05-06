"""
CyclS Agent for Creative Campaign Generation
Conversational agent that lets the LLM drive the interaction naturally.
"""

import re
import json
import os
import cycls
from openai import AsyncOpenAI
from pydantic import BaseModel


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
    """
    Format cycls context messages into a clean conversation history
    for the LLM to reason over.
    """
    history = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, str):
            # Strip hidden session markers
            content = re.sub(r"\u200B<!--s:.+?-->\u200B", "", content).strip()
        if role in ("user", "assistant") and content:
            history.append({"role": role, "content": content})
    return history


class LLMDecision(BaseModel):
    """What the LLM decided to do."""
    action: str          # "converse" | "generate_campaign"
    reply: str           # conversational reply or empty string if generating
    context: dict        # extracted campaign context if action is generate_campaign


async def think(messages, last_message: str) -> LLMDecision:
    """
    Let the LLM reason over the full conversation and decide:
    - Just reply conversationally (greet, ask a question, clarify, etc.)
    - Generate a campaign (when enough info is available)
    """
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    history = format_conversation_history(messages)

    r = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.7,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a friendly, expert marketing campaign strategist specializing in Saudi Arabia.\n\n"
                    "Your job is to help users generate creative marketing campaigns.\n\n"
                    "Based on the conversation history and the latest user message, decide what to do:\n\n"
                    "Option 1 — Just reply conversationally:\n"
                    "  - Greet the user warmly if it's the start\n"
                    "  - Ask clarifying questions naturally (one at a time)\n"
                    "  - Help them think through their product or audience\n"
                    "  - Respond to general marketing questions\n"
                    "  - Push back gently if something seems off\n\n"
                    "Option 2 — Generate a campaign:\n"
                    "  - Only when you have enough to work with: product name, some description, and a sense of the audience\n"
                    "  - You do NOT need every field — use your expertise to fill gaps\n\n"
                    "Return JSON:\n"
                    "{\n"
                    '  "action": "converse" or "generate_campaign",\n'
                    '  "reply": "your conversational message to the user (empty string if generating)",\n'
                    '  "context": {\n'
                    '    "product": "",\n'
                    '    "description": "",\n'
                    '    "category": "",\n'
                    '    "audiences": [],\n'
                    '    "tone": "",\n'
                    '    "region": "Riyadh, Saudi Arabia",\n'
                    '    "goal": "",\n'
                    '    "output_language": "English or Arabic"\n'
                    "  }\n"
                    "}\n\n"
                    "Be warm, concise, and human. Never list all missing fields at once."
                ),
            },
            *history,
            {"role": "user", "content": last_message},
        ],
    )

    data = json.loads(r.choices[0].message.content)
    return LLMDecision(
        action=data.get("action", "converse"),
        reply=data.get("reply", ""),
        context=data.get("context", {}),
    )


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

    # Let the LLM reason over the full conversation and decide what to do
    try:
        # Add timeout to prevent hanging
        import asyncio
        decision = await asyncio.wait_for(think(context.messages, context.last_message), timeout=30.0)
    except asyncio.TimeoutError:
        yield {"type": "thinking", "thinking": "Done.", "done": True}
        yield "❌ Error: Request timed out. Please try again."
        return
    except Exception as e:
        yield {"type": "thinking", "thinking": "Done.", "done": True}
        error_msg = str(e)
        if "connection" in error_msg.lower():
            yield "❌ Connection error: Unable to reach OpenAI API. Please check your internet connection and API key."
        else:
            yield f"❌ Error: {error_msg}"
        return

    # ── Option 1: Just have a conversation ──────────────────────────────────
    if decision.action == "converse":
        yield {"type": "thinking", "thinking": "Done.", "done": True}
        yield decision.reply
        if session_id:
            yield f"\u200B<!--s:{session_id}-->\u200B"
        return

    # ── Option 2: Generate a campaign ───────────────────────────────────────
    if decision.reply:
        # LLM may want to say something before generating (e.g. "Great, let me work on that!")
        yield decision.reply + "\n\n"

    # Build a simple namespace object from the LLM-extracted context
    # so ai_service.run_campaign() receives the right shape
    class Req:
        def __init__(self, ctx: dict):
            # Core fields expected by ai_service
            self.product = ctx.get("product") or "Product"
            self.description = ctx.get("description") or ""
            self.category = ctx.get("category") or ""
            self.audiences = ctx.get("audiences") or []
            self.tone = ctx.get("tone") or ctx.get("brand_voice") or "Modern, culturally relevant, Saudi-focused"
            self.region = ctx.get("region") or "Riyadh, Saudi Arabia"
            self.goal = ctx.get("goal") or "awareness"
            self.output_language = ctx.get("output_language") or "English"
            
            # Legacy/compatibility fields (in case any code expects these)
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


creative_campaign_agent.local()
# creative_campaign_agent.deploy()