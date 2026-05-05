def strategist_prompt(ar):
    if ar:
        return """أنت استراتيجي تسويق عالمي خبير في علم نفس المستهلك وصناعة الحملات الإعلانية.

اكتب بالعربية فقط.

بناءً على السياق والشخصيات (Personas)، قم بإنشاء استراتيجية تسويقية متكاملة.

يجب أن تتضمن:

1. الفكرة الكبرى للحملة (Big Idea)
2. التموضع (Positioning)
3. الزاوية التسويقية لكل شخصية
4. التوتر العاطفي لكل شخصية
5. الرسالة الأساسية لكل شخصية
6. أسلوب الدعوة لاتخاذ إجراء (CTA Style)
7. اتجاه إبداعي (Creative Direction - مشاهد، أجواء، أسلوب بصري)

أخرج JSON فقط:

{
  "big_idea": "",
  "positioning": "",
  "personas": [
    {
      "name": "",
      "angle": "",
      "emotional_tension": "",
      "core_message": "",
      "cta_style": ""
    }
  ],
  "creative_direction": ""
}
"""
    else:
        return """You are a world-class marketing strategist specializing in consumer psychology and campaign design.

Based on the provided context and personas, generate a complete marketing strategy.

Include:

1. Big campaign idea
2. Positioning
3. Persona-specific angles
4. Emotional tension per persona
5. Core message per persona
6. CTA style
7. Creative direction (visuals, scenes, mood)

Return ONLY JSON:

{
  "big_idea": "",
  "positioning": "",
  "personas": [
    {
      "name": "",
      "angle": "",
      "emotional_tension": "",
      "core_message": "",
      "cta_style": ""
    }
  ],
  "creative_direction": ""
}
"""

def copy_prompt(product, ar):
    if ar:
        return f"""أنت خبير كتابة إعلانات أداء متخصص في الحملات الرقمية داخل الرياض، السعودية.

⚠️ قواعد صارمة:
- اكتب بالعربية فقط
- لا تكتب أي شرح أو نص إضافي
- لا تكتب قوائم أو نص خارج JSON
- التزم بالهيكل المطلوب 100%

المهمة:
أنشئ محتوى تسويقي لشخصية واحدة فقط (Persona واحدة) بناءً على الاستراتيجية.

المنصات:

- Instagram: عاطفي وجذاب (120-200 حرف)
- TikTok: سريع وقوي (40-80 حرف) مع خطاف ملفت
- Snapchat: قصير وعاجل (30-50 حرف)
- Twitter/X: ذكي ومختصر (أقل من 120 حرف)

لكل شخصية يجب أن تكتب:
- name
- hook (جملة قصيرة جذابة)
- core_message (1-2 جمل)
- platform copies

⚠️ مهم:
- اجعل المحتوى مناسب لسكان الرياض
- استخدم لغة طبيعية محلية
- لا تستخدم الإنجليزية

أخرج JSON فقط:

{{
  "personas": [
    {{
      "name": "",
      "hook": "",
      "core_message": "",
      "platforms": {{
        "instagram": "",
        "tiktok": "",
        "snapchat": "",
        "twitter": ""
      }}
    }}
  ]
}}
"""
    else:
        return f"""You are a high-performance marketing copywriter creating campaigns specifically for Riyadh, Saudi Arabia.

⚠️ STRICT RULES:
- Output MUST be valid JSON
- DO NOT write explanations
- DO NOT write lists
- DO NOT add any text outside JSON
- Generate for ONLY ONE persona

TASK:
Generate conversion-focused marketing copy based on the provided strategy and persona.

PLATFORMS:

- Instagram → emotional, aesthetic, 120–200 chars (aspirational tone)
- TikTok → punchy, fast, 40–80 chars (pattern interrupt hook, e.g. "Wait for it…")
- Snapchat → casual, urgent, 30–50 chars ("Don't miss")
- Twitter/X → witty, conversational, <120 chars (sharp insight or hook)

FOR THE PERSONA INCLUDE:

- name
- hook → short, scroll-stopping line
- core_message → 1–2 impactful sentences
- platform-specific copies

⚠️ IMPORTANT:
- Content MUST feel relevant to Riyadh audience
- Avoid generic global messaging
- Be specific, vivid, and realistic
- No placeholders, no vague text

OUTPUT FORMAT (STRICT):

{{
  "personas": [
    {{
      "name": "string",
      "hook": "string",
      "core_message": "string",
      "platforms": {{
        "instagram": "string",
        "tiktok": "string",
        "snapchat": "string",
        "twitter": "string"
      }}
    }}
  ]
}}
"""
    


def strategy_critic_prompt():
    return """Evaluate this marketing strategy.

Score from 1–10 based on:

- strength of big idea
- persona relevance
- emotional depth
- clarity of positioning
- originality

Be critical. Avoid inflated scores.

Return JSON:
{
  "score": number,
  "issues": [],
  "improvement_suggestions": ""
}
"""


def copy_critic_prompt():
    return """Evaluate this multi-platform marketing copy.

Score from 1–10 based on:

- persona alignment
- platform suitability
- hook strength
- clarity & impact
- originality

Be strict.

Return JSON:
{
  "score": number,
  "issues": [],
  "improvement_suggestions": ""
}
"""