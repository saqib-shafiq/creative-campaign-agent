"""
AI Service for Campaign Generation
Handles persona generation, strategy creation, copywriting, and quality control.
"""

from openai import AsyncOpenAI
import os
import json

from app.services.prompts import (
    strategist_prompt,
    copy_prompt,
    strategy_critic_prompt,
    copy_critic_prompt,
)
from app.services.memory import save_memory, memory_context


# ================= HELPERS =================

async def safe_completion(client, **kwargs):
    """
    Wrapper for OpenAI completion calls with consistent error handling.
    
    Args:
        client: AsyncOpenAI client instance
        **kwargs: Arguments for chat.completions.create
        
    Returns:
        OpenAI completion response
    """
    return await client.chat.completions.create(**kwargs)


def safe_json_parse(text):
    """
    Safely parse JSON from model output, handling markdown code blocks.
    
    Args:
        text: Raw text from model that may contain JSON
        
    Returns:
        Parsed dict or empty dict on failure
    """
    try:
        clean = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception:
        return {}


# ================= CONTEXT =================

async def complete_context(ctx):
    """
    Fill in missing context fields with sensible defaults.
    
    Args:
        ctx: CampaignContext object to complete
        
    Returns:
        Completed CampaignContext object
    """
    if not ctx.audiences:
        ctx.audiences = ["Young professionals in Riyadh"]

    if not ctx.goal:
        ctx.goal = "awareness"

    if not ctx.tone:
        ctx.tone = "Modern, culturally relevant, Saudi-focused"

    # FORCE REGION
    if not ctx.region:
        ctx.region = "Riyadh, Saudi Arabia"

    return ctx


async def generate_personas(client, ctx):
    """
    Generate marketing personas based on campaign context.
    
    Args:
        client: AsyncOpenAI client instance
        ctx: Completed CampaignContext object
        
    Returns:
        List of persona dicts with name, demographics, pain_points, desires, etc.
    """
    r = await safe_completion(
        client,
        model="gpt-4o-mini",
        temperature=0.6,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate 1 realistic marketing persona.\n\n"
                    "Each must include:\n"
                    "- name\n"
                    "- demographics\n"
                    "- psychographics\n"
                    "- pain_points\n"
                    "- desires\n"
                    "- buying_triggers\n"
                    "- objections\n\n"
                    "Return JSON: { \"personas\": [] }"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(ctx.model_dump(), ensure_ascii=False),
            },
        ],
    )

    data = safe_json_parse(r.choices[0].message.content)
    return data.get("personas", [])


# ================= CRITIC =================

async def run_critic(client, prompt, content):
    """
    Run quality evaluation on strategy or copy.
    
    Args:
        client: AsyncOpenAI client instance
        prompt: Critic prompt (strategy_critic_prompt or copy_critic_prompt)
        content: Content to evaluate (strategy or copy as JSON string)
        
    Returns:
        Dict with score, issues list, and improvement suggestions
    """
    r = await safe_completion(
        client,
        model="gpt-4o-mini",
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": content},
        ],
    )
    return safe_json_parse(r.choices[0].message.content)


# ================= MAIN =================

async def run_campaign(req):
    """
    Main campaign generation orchestrator.
    
    Flow:
    1. Complete context with defaults
    2. Generate audience personas
    3. Generate and refine strategy (with critic feedback)
    4. Generate and refine copy (with critic feedback)
    5. Save to memory
    6. Format and return output
    
    Args:
        req: CampaignContext object with campaign requirements
        
    Yields:
        Dict objects with 'type' and 'content' for streaming response
    """
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    ctx = await complete_context(req)
    is_arabic = ctx.output_language.lower() == "arabic"

    yield {"type": "step", "content": "Context enriched"}

    personas = await generate_personas(client, ctx)
    yield {"type": "step", "content": f"{len(personas)} personas created"}

    # ================= STRATEGY =================
    # Generate and refine strategy with critic feedback loop
    
    best_strategy = None
    best_score = -1
    improvement = ""

    for attempt in range(1):
        yield {"type": "step", "content": f"Strategy attempt {attempt + 1}"}

        # Generate initial strategy
        r1 = await safe_completion(
            client,
            model="gpt-4o-mini",
            temperature=0.7,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": strategist_prompt(is_arabic)},
                {
                    "role": "user",
                    "content": json.dumps({
                        "context": ctx.model_dump(),
                        "personas": personas,
                        "memory": memory_context()
                    }, ensure_ascii=False)
                },
            ],
        )

        strategy = safe_json_parse(r1.choices[0].message.content)

        # Evaluate with critic
        critic = await run_critic(
            client,
            strategy_critic_prompt(),
            json.dumps(strategy, ensure_ascii=False),
        )

        score = critic.get("score", 0)

        if score > best_score:
            best_score = score
            best_strategy = strategy

        if score >= 7:
            break

        improvement = critic.get("improvement_suggestions", "")

    # ================= COPYRIGHT =================
    # Generate and refine copy with critic feedback loop
    
    best_copy = None
    best_score = -1

    for attempt in range(1):
        yield {"type": "step", "content": f"Copyright attempt {attempt + 1}"}

        # Generate initial copy
        r2 = await safe_completion(
            client,
            model="gpt-4o-mini",
            temperature=0.85,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": copy_prompt(ctx.product or "Product", is_arabic)},
                {
                    "role": "user",
                    "content": json.dumps({
                        "strategy": best_strategy,
                        "personas": personas,
                        "context": ctx.model_dump()
                    }, ensure_ascii=False)
                },
            ],
        )

        campaign = safe_json_parse(r2.choices[0].message.content)
        
        # Evaluate with critic
        critic = await run_critic(
            client,
            copy_critic_prompt(),
            json.dumps(campaign, ensure_ascii=False)
        )

        score = critic.get("score", 0)

        if score > best_score:
            best_score = score
            best_copy = campaign

        if score >= 7:
            break

    # ================= SAVE =================
    # Store campaign data for future reference
    
    save_memory({
        "product": ctx.product,
        "audience": ctx.audiences,
        "tone": ctx.tone,
    })

    def format_output(personas, campaign):
        """
        Format final campaign output for display.
        
        Args:
            personas: List of generated personas
            campaign: Campaign dict with copy for each persona
            
        Returns:
            Formatted string with campaign focus, personas, and platform copy
        """
        lines = []

        lines.append("📍 Campaign Focus: Riyadh, Saudi Arabia\n")

        # Display created personas
        for i, p in enumerate(personas):
            lines.append(f"👤 Persona {i+1}: {p.get('name', 'Unknown')}")
            lines.append(f"- Pain Points: {p.get('pain_points', '')}")
            lines.append(f"- Desires: {p.get('desires', '')}\n")

        # Display campaign copy per persona
        if campaign and "personas" in campaign:
            for p in campaign["personas"]:
                lines.append(f"🎯 {p.get('name', '')}")
                lines.append(f"Hook: {p.get('hook', '')}")
                lines.append(f"Message: {p.get('core_message', '')}\n")

                platforms = p.get("platforms", {})

                lines.append("📱 Social media platforms copy:")

                if "instagram" in platforms:
                    lines.append(f"- Instagram: {platforms['instagram']}")

                if "tiktok" in platforms:
                    lines.append(f"- TikTok: {platforms['tiktok']}")

                if "snapchat" in platforms:
                    lines.append(f"- Snapchat: {platforms['snapchat']}")

                if "twitter" in platforms:
                    lines.append(f"- Twitter/X: {platforms['twitter']}")

                lines.append("\n" + "-"*40 + "\n")

        return "\n".join(lines)
    
    # ================= OUTPUT =================
    # Stream final formatted results
    
    yield {
        "type": "narrative",
        "content": format_output(personas, best_copy),
    }