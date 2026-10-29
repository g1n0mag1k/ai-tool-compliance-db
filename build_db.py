#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds ai_tools_db.json — the public AI Tool Compliance Database.

This is the data-entry source of truth. Edit TOOLS below and re-run this
script to regenerate ai_tools_db.json and the CSV mirror. Do not hand-edit
the generated JSON/CSV directly; they will be overwritten.

Confidence levels (see README for full definition):
  "verified"          - confirmed against the vendor's own current published
                         policy page as of `last_verified`, with source URL(s).
  "general_knowledge" - reflects well-established, publicly reported vendor
                         behavior at the time of writing, but was not
                         individually re-verified against a live vendor page
                         in this build. Lower confidence; re-verify before
                         relying on it for a specific client engagement.

`baa_available` values: true | false | "conditional" (e.g., sales-managed
accounts only, or requires admin activation).
"""

import json
import csv
import datetime

TODAY = "2026-10-28"

TOOLS = []

def add(vendor, product, tier, tier_category, category,
        trains_default, opt_out, baa, baa_notes, dpa,
        retention, confidence, sources, last_verified, notes):
    tool_id = f"{vendor.lower().replace(' ', '-')}-{product.lower().replace(' ', '-').replace('.', '')}-{tier.lower().replace(' ', '-').replace('/', '-')}"
    TOOLS.append(dict(
        id=tool_id, vendor=vendor, product=product, tier=tier,
        tier_category=tier_category, category=category,
        trains_on_input_by_default=trains_default,
        training_opt_out_available=opt_out,
        baa_available=baa, baa_notes=baa_notes,
        dpa_available=dpa, data_retention_default=retention,
        confidence=confidence, source_urls=sources,
        last_verified=last_verified, notes=notes,
    ))

V = "verified"
G = "general_knowledge"

# =====================================================================
# GENERAL-PURPOSE LLM / CHATBOT PLATFORMS
# =====================================================================

add("OpenAI", "ChatGPT", "Free", "Consumer Free", "General-purpose chatbot",
    True, True, False,
    "OpenAI does not offer a BAA for Free, Plus, or Team tiers.",
    False, "Retained per account settings; subject to training unless opted out via Data Controls.",
    V, ["https://help.openai.com/en/articles/8660679"], TODAY,
    "An opt-out exists in ChatGPT's Data Controls, but training is on by default. Never approved for PHI.")

add("OpenAI", "ChatGPT", "Plus", "Consumer Paid", "General-purpose chatbot",
    True, True, False,
    "OpenAI does not offer a BAA for Free, Plus, or Team tiers.",
    False, "Retained per account settings; subject to training unless opted out via Data Controls.",
    V, ["https://help.openai.com/en/articles/8660679"], TODAY,
    "Same training/BAA posture as Free — paying for Plus does not itself unlock a BAA or training exclusion.")

add("OpenAI", "ChatGPT", "Team", "Business/Team", "General-purpose chatbot",
    False, "n/a (not trained by default)", False,
    "Business Data Terms exclude training by default; HIPAA Journal and third-party trackers report OpenAI will not sign a BAA at the Team tier even though training is off.",
    True, "90 days default (configurable), per OpenAI's Business Data Terms.",
    V, ["https://help.openai.com/en/articles/8660679"], TODAY,
    "Meaningfully better posture than Free/Plus (no training, DPA available), but still not HIPAA-eligible — do not treat as PHI-safe without an executed BAA.")

add("OpenAI", "ChatGPT", "Enterprise / Edu", "Enterprise", "General-purpose chatbot",
    False, "n/a (not trained by default)", "conditional",
    "OpenAI's own help center states sales-managed Enterprise/Edu accounts are BAA-eligible; some third-party trackers report OpenAI declining BAAs for ChatGPT even at Enterprise. Sources conflict — confirm directly with OpenAI sales before relying on this for a specific client.",
    True, "Configurable; not used for training by default.",
    V, ["https://help.openai.com/en/articles/8660679", "https://intuitionlabs.ai/articles/is-chatgpt-hipaa-compliant"], TODAY,
    "Treat as conditional/unresolved rather than a clean Yes until the specific client's sales-managed agreement is confirmed to include a signed BAA.")

add("OpenAI", "API Platform", "Pay-as-you-go / Enterprise", "API/Developer", "LLM API",
    False, "n/a (not trained by default since March 2023)", True,
    "OpenAI offers a BAA for API customers on sales-managed/qualifying accounts.",
    True, "Zero data retention available for qualifying use cases; standard retention otherwise 30 days (abuse monitoring).",
    V, ["https://help.openai.com/en/articles/8660679"], TODAY,
    "The most HIPAA-friendly OpenAI surface — relevant when a client's own product calls the OpenAI API directly, not when staff use the ChatGPT consumer app.")

add("Anthropic", "Claude.ai", "Free", "Consumer Free", "General-purpose chatbot",
    True, True, False,
    "Not covered — consumer plans (Free/Pro/Max) are explicitly excluded from Anthropic's BAA program.",
    False, "5-year retention if training is not opted out; 30 days if opted out, per Anthropic's Sept. 2025 consumer policy change.",
    V, ["https://support.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers"], TODAY,
    "As of Sept. 28, 2025, Anthropic trains on consumer conversations by default unless the user opts out — this reversed Anthropic's earlier no-training-by-default posture. Re-verify this periodically; it is a policy area that has already changed once.")

add("Anthropic", "Claude.ai", "Pro / Max", "Consumer Paid", "General-purpose chatbot",
    True, True, False,
    "Not covered — consumer plans are explicitly excluded from Anthropic's BAA program.",
    False, "5-year retention if training is not opted out; 30 days if opted out.",
    V, ["https://support.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers"], TODAY,
    "Same training/BAA posture as Free.")

add("Anthropic", "Claude", "Team", "Business/Team", "General-purpose chatbot",
    False, "n/a", False,
    "Anthropic's own BAA article does not list Team plans as BAA-eligible.",
    True, "Not used for training by default on commercial plans.",
    V, ["https://support.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers"], TODAY,
    "A step up from consumer tiers (no training by default, DPA available) but not BAA-eligible — do not use for PHI.")

add("Anthropic", "Claude", "Enterprise", "Enterprise", "General-purpose chatbot",
    False, "n/a", "conditional",
    "BAA available, but only after the account's Primary Owner explicitly activates HIPAA compliance and signs the BAA under Data & Privacy settings — not covered by default on a standard Enterprise plan.",
    True, "30-day retention requirement applies to \"Covered Models\" under the BAA once activated.",
    V, ["https://support.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers"], TODAY,
    "Confirm the specific client's Enterprise account has actually activated HIPAA compliance — the plan tier alone does not guarantee BAA coverage.")

add("Anthropic", "API Platform", "Commercial API", "API/Developer", "LLM API",
    False, "n/a", "conditional",
    "BAA available for HIPAA-ready API use, but the Primary Owner must sign the BAA and then contact Anthropic/Sales to activate it — not automatic.",
    True, "Not used for training by default; 30-day retention for Covered Models under an active BAA.",
    V, ["https://support.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers"], TODAY,
    "Relevant when a client's own product calls the Anthropic API directly.")

add("Google", "Gemini app", "Consumer (personal account)", "Consumer Free", "General-purpose chatbot",
    True, True, False,
    "Not covered — personal Google accounts fall outside any Workspace BAA regardless of what the organization has executed.",
    False, "Per Google's consumer privacy policy; subject to human review/training unless Gemini Apps Activity is managed.",
    G, [], TODAY,
    "A personal Gemini account is fully outside an organization's Workspace agreement even if the organization has a Workspace BAA — this is a common and serious confusion point for clients.")

add("Google", "Gemini for Google Workspace", "Business Standard/Plus, Enterprise (tenant add-on)", "Enterprise", "General-purpose chatbot (Workspace-integrated)",
    False, "n/a (not used for training)", "conditional",
    "Gemini for Workspace can support HIPAA workloads and is generally included in the scope of an executed Workspace BAA, but the organization's Workspace BAA must be signed and the Gemini add-on assigned by an admin — not automatic just because the license exists.",
    True, "Not used to train generative AI models; content not shared outside the domain without permission, per Google's Workspace Gemini FAQ.",
    V, ["https://knowledge.workspace.google.com/admin/gemini/gemini-for-google-workspace-faq"], TODAY,
    "Materially different posture from the consumer Gemini app — this is the Workspace-licensed version admins assign to specific users.")

add("Microsoft", "Copilot (consumer, copilot.microsoft.com)", "Free / Copilot Pro (personal Microsoft account)", "Consumer Paid", "General-purpose chatbot",
    True, True, False,
    "Not covered — personal Microsoft accounts are outside any organizational M365 agreement.",
    False, "Per Microsoft's consumer privacy policy.",
    G, [], TODAY,
    "Same confusion risk as personal Gemini: an employee signed into Copilot with a personal Microsoft account is not covered by the organization's M365 agreement.")

add("Microsoft", "Microsoft 365 Copilot", "M365 Business/Enterprise tenant license", "Enterprise", "General-purpose chatbot (M365-integrated)",
    False, "n/a (not used to train foundation models)", "conditional",
    "Use is governed by the Microsoft Products and Services Data Protection Addendum (DPA); HIPAA coverage depends on the organization's specific Online Services Terms / BAA, which varies by licensing agreement — confirm the client's own agreement explicitly covers Copilot.",
    True, "Microsoft states prompts, responses, and Graph-accessed data are not used to train foundation models.",
    V, ["https://learn.microsoft.com/copilot/microsoft-365/enterprise-data-protection"], TODAY,
    "Strong default data-handling posture (no training, tenant isolation, DPA), but BAA coverage specifics vary by the client's licensing agreement — don't assume automatic HIPAA coverage without checking.")

add("Perplexity AI", "Perplexity", "Free", "Consumer Free", "AI search / research assistant",
    True, True, False,
    "No BAA offered at consumer tiers.",
    False, "Subject to standard consumer retention/training per Perplexity's privacy policy.",
    G, [], TODAY,
    "Commonly used informally for “quick medical/legal reference lookups” — treat as unapproved for any query containing identifiable client/patient details.")

add("Perplexity AI", "Perplexity Enterprise Pro", "Enterprise", "Enterprise", "AI search / research assistant",
    False, "n/a", False,
    "No BAA program identified as of this writing.",
    True, "Enterprise tier excludes queries from training per Perplexity's enterprise terms.",
    G, [], TODAY,
    "Better data-handling posture than Free, but absent a BAA this should still be treated as not approved for PHI.")

add("xAI", "Grok", "Free / Premium (X / grok.com)", "Consumer Paid", "General-purpose chatbot",
    True, True, False,
    "No BAA program identified.",
    False, "Per xAI/X privacy policy; subject to training by default.",
    G, [], TODAY,
    "Increasingly used informally via the X app — worth including explicitly in staff AI-use surveys since it's easy to overlook.")

add("Mistral AI", "Le Chat", "Free / Pro", "Consumer Paid", "General-purpose chatbot",
    True, True, False,
    "No BAA program identified for the consumer product.",
    False, "Per Mistral's privacy policy.",
    G, [], TODAY,
    "EU-based vendor; may be subject to GDPR-specific considerations beyond HIPAA scope — flag for legal counsel if the client has EU patient/client data.")

add("Meta", "Meta AI", "Free (within Facebook/Instagram/WhatsApp)", "Consumer Free", "General-purpose chatbot",
    True, True, False,
    "No BAA program; not a business-oriented product.",
    False, "Per Meta's consumer privacy policy.",
    G, [], TODAY,
    "Easy to overlook because it's embedded in consumer social apps rather than used as a standalone “AI tool” — worth asking about explicitly in surveys.")

# =====================================================================
# MEETING / CALL TRANSCRIPTION & NOTETAKING
# =====================================================================

add("Otter.ai", "Otter.ai", "Free / Basic", "Consumer Free", "Meeting transcription",
    True, True, False,
    "No BAA offered at Free/Basic tiers.",
    False, "Retained indefinitely by default absent manual deletion; subject to training per free-tier terms.",
    G, [], TODAY,
    "High-risk when used to record patient calls or client consultations — live transcription of PHI/privileged conversations with no BAA is a frequent, serious finding.")

add("Otter.ai", "Otter.ai Business", "Business", "Business/Team", "Meeting transcription",
    False, "n/a", False,
    "No BAA program identified as of this writing — confirm directly with Otter.ai if a client specifically needs one.",
    True, "Business tier reportedly excludes content from training; verify current terms directly before relying on this for a PHI-handling client.",
    G, [], TODAY,
    "Even the Business tier should be treated as not approved for PHI/privileged content absent a confirmed BAA.")

add("Fireflies.ai", "Fireflies.ai", "Free", "Consumer Free", "Meeting transcription",
    True, True, False,
    "No BAA offered at the free tier.",
    False, "Recordings/transcripts retained per account settings; free-tier content may be used to improve the product.",
    G, [], TODAY,
    "Same risk pattern as Otter.ai Free — frequently found auto-joining clinical staff meetings or client calls without anyone realizing a transcript is being stored off-platform.")

add("Fireflies.ai", "Fireflies.ai Business", "Business", "Business/Team", "Meeting transcription",
    False, "n/a", False,
    "No BAA program identified as of this writing — confirm directly with Fireflies.ai.",
    True, "Business tier terms vary; verify current data-handling commitments directly.",
    G, [], TODAY,
    "Treat as not approved for PHI/privileged content absent a confirmed BAA.")

add("Zoom", "Zoom AI Companion", "Zoom Business (AI Companion add-on)", "Business/Team", "Meeting transcription & summarization",
    False, "n/a", "conditional",
    "Zoom offers a healthcare-specific BAA addendum covering AI Companion for qualifying Zoom for Healthcare accounts — not automatically included in a standard Zoom Business BAA. The addendum must be separately requested/executed.",
    True, "Per Zoom's data-handling terms for AI Companion; verify current retention settings in the admin console.",
    V, ["https://explore.zoom.us/en/industry/healthcare/"], TODAY,
    "A very common gap: organizations have a general Zoom BAA for video calls but have not executed the separate AI Companion healthcare addendum, while AI Companion is already summarizing PHI-containing visits.")

add("Fathom", "Fathom", "Free / Team", "Business/Team", "Meeting transcription",
    True, True, False,
    "No BAA program identified as of this writing.",
    False, "Per Fathom's privacy policy; verify current terms before use with sensitive content.",
    G, [], TODAY,
    "Growing in popularity for sales/client calls — ask about this specifically in staff surveys as it's newer and less commonly top-of-mind than Otter/Fireflies.")

add("Read AI", "Read.ai", "Free / Pro", "Business/Team", "Meeting transcription & analytics",
    True, True, False,
    "No BAA program identified as of this writing.",
    False, "Per Read AI's privacy policy.",
    G, [], TODAY,
    "Also captures sentiment/engagement analytics in addition to transcripts — broader data exposure than a transcript-only tool.")

add("Gong.io", "Gong", "Enterprise (sales call intelligence)", "Enterprise", "Call recording & sales analytics",
    False, "n/a", "conditional",
    "Enterprise B2B contracts can typically negotiate a DPA; BAA availability should be confirmed directly — Gong is primarily positioned for sales teams, not clinical/legal use.",
    True, "Per negotiated enterprise agreement.",
    G, [], TODAY,
    "Relevant mainly if a healthtech or legal-services client's own sales team records calls that reference patient/client details — less common as direct clinical/legal shadow IT.")

# =====================================================================
# MEDICAL SCRIBE / CLINICAL DOCUMENTATION (healthcare-specific)
# =====================================================================

add("Microsoft/Nuance", "Dragon Medical One", "Enterprise (cloud, healthcare-specific)", "Enterprise", "Clinical dictation",
    False, "n/a", True,
    "Purpose-built healthcare dictation platform; BAA is a standard part of the commercial agreement.",
    True, "Per Nuance/Microsoft's healthcare data-handling commitments.",
    G, [], TODAY,
    "Long-standing, purpose-built clinical tool — generally the safest category of AI tool a medical practice uses, by design rather than by accident.")

add("Abridge", "Abridge", "Enterprise (clinical ambient documentation)", "Enterprise", "AI medical scribe",
    False, "n/a", True,
    "Purpose-built clinical documentation platform marketed specifically to HIPAA-covered entities; BAA is standard to the commercial agreement.",
    True, "Per Abridge's healthcare-specific data-handling commitments — confirm current terms directly for a specific engagement.",
    G, [], TODAY,
    "Confirm the BAA has actually been executed for the specific client, not just that Abridge offers one as a vendor category.")

add("Nabla", "Nabla Copilot", "Enterprise (clinical ambient documentation)", "Enterprise", "AI medical scribe",
    False, "n/a", True,
    "Purpose-built clinical documentation platform; BAA is standard to the commercial agreement.",
    True, "Per Nabla's healthcare-specific data-handling commitments.",
    G, [], TODAY,
    "Confirm current BAA status directly — do not assume from category alone.")

add("Suki AI", "Suki Assistant", "Enterprise (clinical ambient documentation)", "Enterprise", "AI medical scribe",
    False, "n/a", True,
    "Purpose-built clinical documentation platform; BAA is standard to the commercial agreement.",
    True, "Per Suki's healthcare-specific data-handling commitments.",
    G, [], TODAY,
    "Confirm current BAA status directly for the specific client.")

add("Heidi Health", "Heidi", "Free / Pro", "Business/Team", "AI medical scribe",
    False, "conditional", "conditional",
    "Markets itself to clinicians; confirm whether the specific tier in use (free vs. paid clinic plan) includes a BAA — free-tier individual clinician use is a common gray area.",
    True, "Per Heidi's current terms — verify directly; varies meaningfully between free individual use and paid clinic agreements.",
    G, [], TODAY,
    "Increasingly adopted informally by individual physicians on the free tier before a practice has evaluated or approved it — worth asking about by name in physician surveys.")

# =====================================================================
# LEGAL-SPECIFIC AI TOOLS (relevant to the law-firm channel)
# =====================================================================

add("Thomson Reuters", "CoCounsel", "Enterprise (legal AI assistant)", "Enterprise", "Legal AI research & drafting",
    False, "n/a", "conditional",
    "Enterprise legal product; data-handling terms negotiated as part of the Thomson Reuters commercial agreement. BAA relevance depends on whether the firm's matters involve PHI (e.g., healthcare/med-mal practice) — confirm current terms directly.",
    True, "Per the firm's specific Thomson Reuters agreement.",
    G, [], TODAY,
    "For a healthcare-adjacent legal practice (med-mal defense, healthcare regulatory), confirm whether client matter documents containing PHI are in scope of any executed BAA.")

add("Harvey AI", "Harvey", "Enterprise (legal AI assistant)", "Enterprise", "Legal AI research & drafting",
    False, "n/a", "conditional",
    "Enterprise legal product aimed at large law firms; data-handling and BAA terms are negotiated per engagement — confirm directly, especially for smaller firms where standard terms may differ.",
    True, "Per the firm's specific Harvey agreement.",
    G, [], TODAY,
    "Primarily adopted by larger firms; less common at the 1-10 attorney firms that are Sui-Generis's primary law-firm channel target, but worth asking about.")

add("LexisNexis", "Lexis+ AI", "Enterprise (legal AI research)", "Enterprise", "Legal AI research & drafting",
    False, "n/a", "conditional",
    "Enterprise legal research product; confirm current data-handling and BAA terms directly with LexisNexis for the specific firm's agreement.",
    True, "Per the firm's specific LexisNexis agreement.",
    G, [], TODAY,
    "Common at firms that already subscribe to Lexis+ for research — confirm whether the AI features specifically are covered by the same data terms as core research.")

add("Spellbook", "Spellbook", "Business (contract review AI, Microsoft Word add-in)", "Business/Team", "Legal AI contract review",
    False, "conditional", "conditional",
    "Built on top of third-party LLMs (historically OpenAI/Anthropic models) — confirm current underlying model provider and whether Spellbook's own agreement with that provider excludes training on firm data, and whether Spellbook itself offers a BAA/DPA.",
    True, "Per Spellbook's current terms — verify directly, including which underlying LLM provider is used.",
    G, [], TODAY,
    "A good example of a “wrapper” tool: the compliance posture depends partly on Spellbook's own agreement with its underlying model provider, not just Spellbook's own policy page — worth asking about explicitly in vendor risk assessments.")

# =====================================================================
# WRITING / PRODUCTIVITY ASSISTANTS
# =====================================================================

add("Grammarly", "Grammarly", "Free", "Consumer Free", "Writing assistant",
    True, True, False,
    "No BAA at the free tier.",
    False, "Per Grammarly's consumer privacy policy; free-tier content may be used to improve the product absent opt-out.",
    G, [], TODAY,
    "Operates as a browser extension/add-in that can see text across many applications — broader exposure surface than a single destination tool.")

add("Grammarly", "Grammarly Business", "Business", "Business/Team", "Writing assistant",
    False, "n/a", False,
    "Grammarly does not offer a BAA; Business tier excludes content from training and offers a DPA.",
    True, "Business tier excludes submitted text from model training, per Grammarly's business terms.",
    G, [], TODAY,
    "A frequent “conditionally approved” answer: fine for general correspondence, but must remain PHI/privileged-content-free absent a BAA.")

add("Notion Labs", "Notion AI", "Add-on (Plus/Business/Enterprise plans)", "Business/Team", "Workspace AI assistant",
    False, "conditional", "conditional",
    "Notion offers HIPAA compliance (including BAA) on qualifying Enterprise plans with the add-on properly configured — not included by default on lower tiers; confirm current terms directly.",
    True, "Per Notion's current enterprise data-handling terms — verify directly for the specific plan.",
    G, [], TODAY,
    "If a client already uses Notion as their internal wiki/database, this is worth checking carefully since Notion AI can surface across the entire connected workspace.")

add("Jasper AI", "Jasper", "Business (marketing content AI)", "Business/Team", "Marketing content generation",
    False, "conditional", "conditional",
    "Enterprise-tier data-handling terms vary; confirm current BAA/DPA availability directly — primarily a marketing tool, lower likelihood of PHI/privileged exposure by design.",
    True, "Per Jasper's current enterprise terms.",
    G, [], TODAY,
    "Lower-risk category (marketing copy) but still worth a one-line confirmation that no patient/client identifiers are ever entered as example content.")

# =====================================================================
# TRANSLATION
# =====================================================================

add("DeepL", "DeepL", "Free", "Consumer Free", "Translation",
    True, True, False,
    "No BAA at the free tier.",
    False, "Free-tier submissions may be used to improve translation quality absent opt-out.",
    G, [], TODAY,
    "Frequently used informally by front-desk staff to translate patient instructions/intake forms — a common and easily-overlooked PHI exposure point.")

add("DeepL", "DeepL Pro / API", "Pro / API", "Business/Team", "Translation",
    False, "n/a", "conditional",
    "DeepL Pro and API tiers exclude submitted text from training by default and offer a DPA; BAA availability should be confirmed directly for healthcare use cases.",
    True, "Pro/API tiers do not use submitted text to improve translations, per DeepL's Pro terms.",
    G, [], TODAY,
    "A straightforward, low-cost upgrade path from the free tier that meaningfully improves data handling — a good candidate for a fast remediation win.")

# =====================================================================
# CODING ASSISTANTS
# =====================================================================

add("GitHub (Microsoft)", "GitHub Copilot", "Individual / Business / Enterprise", "Business/Team", "AI coding assistant",
    False, "conditional (Individual plan trains by default unless opted out; Business/Enterprise exclude training by default)", "conditional",
    "BAA relevance is narrow — primarily matters if source code itself could contain embedded PHI/PII (e.g., test fixtures with real patient data). Confirm current terms directly if that risk applies.",
    True, "Business/Enterprise tiers exclude code snippets from training by default; Individual plan trains unless the user opts out in settings.",
    G, [], TODAY,
    "Relevant to a healthtech SaaS client (like ClearPath) more than a medical/legal practice — flag specifically for engineering teams and check whether any test data includes real patient identifiers.")

add("Cursor (Anysphere)", "Cursor", "Free / Pro / Business", "Business/Team", "AI coding assistant (IDE)",
    False, "conditional", "conditional",
    "Business tier offers privacy-mode data handling; confirm current BAA/DPA terms directly if the client's codebase could contain embedded PHI/PII.",
    True, "Business tier reportedly excludes code from training by default; verify current terms directly.",
    G, [], TODAY,
    "Same risk category as GitHub Copilot — relevant mainly to engineering teams at a healthtech SaaS client.")

add("Amazon", "Amazon Q Developer", "Professional tier (AWS)", "Enterprise", "AI coding assistant",
    False, "n/a", "conditional",
    "Governed by the client's existing AWS enterprise agreement and AWS's HIPAA eligibility documentation; confirm Q Developer specifically is in scope of any existing AWS BAA.",
    True, "Per the client's AWS account agreement.",
    G, [], TODAY,
    "Relevant to healthtech clients already running production workloads on AWS under an AWS BAA — confirm the BAA's service scope explicitly includes Q Developer.")

# =====================================================================
# IMAGE / DESIGN GENERATION
# =====================================================================

add("Midjourney", "Midjourney", "Basic / Standard / Pro", "Consumer Paid", "AI image generation",
    True, "conditional (Pro/Mega plans offer 'stealth mode')", False,
    "No BAA program; not positioned as a business/enterprise data-handling product.",
    False, "Per Midjourney's terms; generated images are public by default below the Pro/Mega \"stealth\" tiers.",
    G, [], TODAY,
    "Low PHI/privileged-content risk by typical use case (marketing/design imagery), but flag if any uploaded reference images could contain patient photos or identifiable client materials.")

add("Adobe", "Adobe Firefly", "Individual / Business / Enterprise", "Business/Team", "AI image generation",
    False, "n/a", "conditional",
    "Enterprise tier offers IP indemnification and excludes content from training; BAA relevance is narrow given typical design use case — confirm if any uploaded reference material could contain patient/client identifiers.",
    True, "Enterprise tier excludes submitted content from training.",
    G, [], TODAY,
    "Low-risk category by typical use (marketing/design); same caveat as Midjourney about reference images.")

add("Canva", "Canva (Magic Studio AI features)", "Free", "Consumer Free", "AI-assisted design",
    False, "conditional", False,
    "No BAA program; not positioned for PHI/privileged content.",
    False, "Per Canva's free-tier terms.",
    G, [], TODAY,
    "Commonly approved for non-PHI design work only (patient education handouts, signage) — the restriction should explicitly prohibit entering any patient name, photo, or identifier.")

# =====================================================================
# CRM / SALES / CUSTOMER-FACING AI
# =====================================================================

add("Salesforce", "Einstein Copilot / Agentforce", "Enterprise (CRM AI add-on)", "Enterprise", "CRM AI assistant",
    False, "n/a", "conditional",
    "Governed by the client's existing Salesforce enterprise agreement; Salesforce offers HIPAA-compliant configurations and BAAs for Health Cloud specifically — confirm the AI features are explicitly in scope of any executed BAA, not just the base CRM.",
    True, "Per the client's Salesforce agreement.",
    G, [], TODAY,
    "Relevant if a client's intake/patient-relationship data lives in Salesforce — confirm AI feature scope separately from the base platform BAA.")

add("HubSpot", "HubSpot AI (Content Assistant, Chatspot)", "Professional / Enterprise", "Enterprise", "CRM/marketing AI assistant",
    False, "n/a", "conditional",
    "HubSpot does not broadly market BAA availability; confirm directly if any CRM records could contain PHI (uncommon for typical sales/marketing use, more relevant for patient-intake-adjacent workflows).",
    True, "Per HubSpot's enterprise data processing terms.",
    G, [], TODAY,
    "Lower-risk by typical use case (marketing/sales), but worth a direct check if the client routes any patient-facing communication through HubSpot.")

add("Intercom", "Fin AI Agent", "Business (customer support AI)", "Business/Team", "Customer support AI",
    False, "n/a", "conditional",
    "Confirm current BAA/DPA availability directly if the support channel could ever contain PHI (e.g., a patient portal support chat).",
    True, "Per Intercom's enterprise data processing terms.",
    G, [], TODAY,
    "Relevant for a healthtech SaaS client's own customer support tooling (like ClearPath) — check whether support transcripts could contain PHI shared by hospital-system end users.")

# =====================================================================
# SCHEDULING / CALENDAR AI
# =====================================================================

add("Clara Labs", "Clara", "Business (AI scheduling assistant)", "Business/Team", "Scheduling assistant",
    False, "n/a", "conditional",
    "Confirm current BAA/DPA terms directly — scheduling assistants typically see calendar metadata rather than clinical/matter content, which lowers but does not eliminate risk.",
    True, "Per Clara's current business terms.",
    G, [], TODAY,
    "Lower-risk category by design (sees scheduling metadata, not clinical notes), but confirm meeting titles/descriptions don't carry patient names.")

add("Reclaim.ai", "Reclaim.ai", "Business", "Business/Team", "Scheduling assistant",
    False, "n/a", False,
    "No BAA program identified as of this writing.",
    True, "Per Reclaim's current business terms.",
    G, [], TODAY,
    "Same risk profile as Clara — primarily calendar metadata, low but nonzero exposure.")

# =====================================================================
# SEARCH / RESEARCH AI (general productivity)
# =====================================================================

add("You.com", "You.com", "Free / Team", "Consumer Paid", "AI search assistant",
    True, True, False,
    "No BAA program identified.",
    False, "Per You.com's privacy policy.",
    G, [], TODAY,
    "Less common than Perplexity/ChatGPT for this use case but worth including in staff AI-tool surveys as a catch-all.")

add("Poe (Quora)", "Poe", "Free / Subscriber", "Consumer Paid", "Multi-model AI chat aggregator",
    True, True, False,
    "No BAA program; aggregates multiple third-party models (OpenAI, Anthropic, Google, etc.) under Poe's own terms, not the underlying model vendors' enterprise terms.",
    False, "Per Poe's privacy policy.",
    G, [], TODAY,
    "An important nuance: using Claude or GPT-4 “through Poe” does NOT inherit Anthropic's or OpenAI's enterprise/BAA terms — it is governed by Poe's own consumer-grade terms instead.")

print(f"Defined {len(TOOLS)} tool entries.")

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

DB = {
    "$schema": "./schema.json",
    "name": "ai-tool-compliance-db",
    "description": "Open-source reference database mapping AI tools to BAA/DPA availability, "
                   "default training behavior, and data retention posture, by product tier.",
    "maintainer": "Sui-Generis LLC (Andrew Rogers)",
    "license": "MIT",
    "version": "1.0.0",
    "generated": TODAY,
    "disclaimer": (
        "This database is a point-in-time reference compiled from public vendor documentation "
        "and third-party reporting. Vendor BAA, DPA, and training policies change frequently and "
        "without notice. This is NOT legal advice and NOT a substitute for confirming current terms "
        "directly with each vendor and, where PHI or privileged information is involved, with the "
        "client's own legal counsel before relying on any entry for a compliance decision. See the "
        "`confidence` and `last_verified` fields on each entry, and the README, before use."
    ),
    "tool_count": len(TOOLS),
    "tools": TOOLS,
}

with open("ai_tools_db.json", "w", encoding="utf-8") as f:
    json.dump(DB, f, indent=2, ensure_ascii=False)
print("Wrote ai_tools_db.json")

# CSV mirror — flattened, one row per tool, source_urls joined with " | ".
# Includes a blank `client_id` column so this file can be used directly (or
# with client_id filled in from an OAuth enumeration run) as the --allowlist
# input to gworkspace_oauth_enum.py.
CSV_FIELDS = ["id", "vendor", "product", "tier", "tier_category", "category",
              "trains_on_input_by_default", "training_opt_out_available",
              "baa_available", "baa_notes", "dpa_available", "data_retention_default",
              "confidence", "source_urls", "last_verified", "notes", "domain", "client_id"]

def guess_domain(vendor):
    overrides = {
        "OpenAI": "openai.com", "Anthropic": "anthropic.com", "Google": "google.com",
        "Microsoft": "microsoft.com", "Microsoft/Nuance": "nuance.com",
        "GitHub (Microsoft)": "github.com", "Perplexity AI": "perplexity.ai",
        "xAI": "x.ai", "Mistral AI": "mistral.ai", "Meta": "meta.com",
        "Otter.ai": "otter.ai", "Fireflies.ai": "fireflies.ai", "Zoom": "zoom.us",
        "Fathom": "fathom.video", "Read AI": "read.ai", "Gong.io": "gong.io",
        "Abridge": "abridge.com", "Nabla": "nabla.com", "Suki AI": "suki.ai",
        "Heidi Health": "heidihealth.com", "Thomson Reuters": "thomsonreuters.com",
        "Harvey AI": "harvey.ai", "LexisNexis": "lexisnexis.com", "Spellbook": "spellbook.legal",
        "Grammarly": "grammarly.com", "Notion Labs": "notion.so", "Jasper AI": "jasper.ai",
        "DeepL": "deepl.com", "Cursor (Anysphere)": "cursor.sh", "Amazon": "aws.amazon.com",
        "Midjourney": "midjourney.com", "Adobe": "adobe.com", "Canva": "canva.com",
        "Salesforce": "salesforce.com", "HubSpot": "hubspot.com", "Intercom": "intercom.com",
        "Clara Labs": "claralabs.com", "Reclaim.ai": "reclaim.ai", "You.com": "you.com",
        "Poe (Quora)": "poe.com",
    }
    return overrides.get(vendor, "")

with open("ai_tools_db.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=CSV_FIELDS, quoting=csv.QUOTE_ALL)
    w.writeheader()
    for t in TOOLS:
        row = dict(t)
        row["source_urls"] = " | ".join(t["source_urls"])
        row["domain"] = guess_domain(t["vendor"])
        row["client_id"] = ""
        w.writerow({k: row.get(k, "") for k in CSV_FIELDS})
print("Wrote ai_tools_db.csv")

# Quick integrity checks
ids = [t["id"] for t in TOOLS]
assert len(ids) == len(set(ids)), "Duplicate tool IDs found!"
verified_count = sum(1 for t in TOOLS if t["confidence"] == "verified")
print(f"Confidence: {verified_count} verified / {len(TOOLS) - verified_count} general_knowledge")
vendors = sorted(set(t["vendor"] for t in TOOLS))
print(f"Vendors covered ({len(vendors)}): {', '.join(vendors)}")
