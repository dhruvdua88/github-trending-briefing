"""Curated plain-English write-ups, keyed by "owner/repo".

Every entry is optional: any repository that hits a board without one still
appears, using GitHub's own description and an explicit "no write-up yet"
label. Nothing here is invented from the repository name alone.

Fields:
    cat  : one of CAT_LABELS
    what : what the thing is, in plain words (1-2 sentences)
    use  : a concrete thing a non-coder would do with it
"""

CAT_LABELS = {
    "agents": "AI assistants",
    "design": "Design",
    "media": "Media",
    "money": "Money",
    "security": "Security",
    "dev": "Dev tools",
    "office": "Office work",
    "fun": "Fun",
}

CONTENT = {
    # ---------------------------------------------------------------- agents
    "debpalash/VoiceStudio": {
        "cat": "media",
        "what": "A free, local clone of ElevenLabs. It clones a voice, turns text into speech in that voice, dubs video into other languages and reads long documents aloud — on your own machine, so no per-minute bill and no voice clips on someone else's server.",
        "use": "Narrate a client explainer or a LinkedIn video without a subscription, and cut the same script in English and Hindi from one session.",
    },
    "Nutlope/hallmark": {
        "cat": "design",
        "what": "A set of written instructions you hand to an AI assistant (Claude Code, Cursor, Codex) so the pages it produces stop looking like generic AI output. Think of it as a pre-flight checklist that kills the template look.",
        "use": "Paste it into whichever AI tool builds your landing page or pitch deck, and the type, spacing and colour come out deliberate instead of default.",
    },
    "pbakaus/impeccable": {
        "cat": "design",
        "what": "A design language plus a companion tool that makes AI coding assistants measurably better at layout, hierarchy and typography. It sits between the assistant and the pixels, and corrects the choices assistants usually get wrong.",
        "use": "The reason a form or dashboard an AI builds for you stops arriving as five identical rounded cards with a soft grey shadow.",
    },
    "TauricResearch/TradingAgents": {
        "cat": "money",
        "what": "A research framework that simulates a trading desk: separate AI agents play analyst, researcher, trader and risk manager, argue their cases, and settle on a decision. It is a study tool for markets, not a money-printing machine.",
        "use": "Stress-test an investment idea by making it survive a fake debate first. Read it as education — nobody should connect this to a live brokerage account.",
    },
    "makecindy/cindy": {
        "cat": "agents",
        "what": "An open-source AI agent that runs out of the box and does tasks instead of chatting about them — connected to your own accounts, with a phone app so it keeps working while you are out.",
        "use": "Inbox triage, draft replies waiting in your outbox, or a checklist that keeps moving while you are at a client's office.",
    },
    "JetBrains/thinkrail": {
        "cat": "dev",
        "what": "A lightweight editor built for 'vibe coding': you describe what you want, the AI writes the code, but you still see the real file tree and every change. Nothing happens invisibly.",
        "use": "The best option for someone who doesn't code — the AI does the work, the editor keeps the receipts so a mistake cannot hide.",
    },
    "affaan-m/ECC": {
        "cat": "agents",
        "what": "An optimisation layer for AI agents: reusable skills, memory and session handling, so your assistant carries context forward instead of starting from zero every morning.",
        "use": "Set it up once and your assistant remembers how your firm words a covering letter, which folders matter, and what it must never touch.",
    },
    "pollen-robotics/microduck": {
        "cat": "fun",
        "what": "A small two-legged duck robot with open hardware designs and Rust firmware. Not AI, not productivity — a genuinely charming piece of engineering.",
        "use": "A desk companion, or the most effective way to get a teenager hooked on electronics and control systems.",
    },
    "Panniantong/Agent-Reach": {
        "cat": "agents",
        "what": "Gives an AI agent eyes on the open internet: it can read and search X, Reddit, YouTube, Bilibili and similar, then feed what it finds back into your workflow.",
        "use": "Track what clients and competitors are saying this week without scrolling yourself — hand the agent a topic and a short list of accounts.",
    },
    "multica-ai/andrej-karpathy-skills": {
        "cat": "agents",
        "what": "A single instruction file (a CLAUDE.md) that changes how a coding assistant behaves, distilled from Andrej Karpathy's notes on how he wants AI to write software.",
        "use": "Drop the file into a project folder and your assistant stops over-engineering, asks fewer pointless questions and writes smaller, clearer changes.",
    },
    "akitaonrails/ai-memory": {
        "cat": "agents",
        "what": "Long-term memory for AI coding assistants: a local store so a fresh session can pick up yesterday's project with its context and handoff notes intact.",
        "use": "Stop re-explaining the same three things to your assistant every single morning.",
    },
    "ruvnet/ruflo": {
        "cat": "agents",
        "what": "An agent harness for coordinating many agents as a swarm, with shared state and routing between them. The most infrastructure-heavy entry of its week.",
        "use": "Only worth the effort once a single assistant is already saving you hours and you want larger automated pipelines.",
    },
    "stablyai/orca": {
        "cat": "agents",
        "what": "A workbench for running a fleet of AI agents at once: give different jobs to different agents and watch them all work in parallel.",
        "use": "A rota for digital staff — one agent drafts, one checks, one formats, and you review the output at the end.",
    },
    "pingdotgg/t3code": {
        "cat": "agents",
        "what": "A control surface for the agents already installed on your computer, with iOS, Android, web and desktop apps — so a long task can keep running while you leave the desk.",
        "use": "Start something at the office, check on it from your phone, and pick up the finished file at home.",
    },
    "paperclipai/paperclip": {
        "cat": "agents",
        "what": "An open-source app for managing agents at work: assign tasks, watch progress, keep a record of what each one did.",
        "use": "The closest thing here to a staff roster for AI — useful once more than one agent is doing real work for you.",
    },
    "thedotmack/claude-mem": {
        "cat": "agents",
        "what": "Persistent memory across sessions: it captures what your agent did and replays the relevant part next time you open it.",
        "use": "Stop re-explaining the same project context every morning; the assistant starts where it left off.",
    },
    "DietrichGebert/ponytail": {
        "cat": "agents",
        "what": "A persona for your AI agent that makes it behave like the laziest senior developer in the room: the best code is the code you don't write.",
        "use": "A corrective if your assistant keeps proposing elaborate systems where a two-line change would do.",
    },
    "mksglu/context-mode": {
        "cat": "agents",
        "what": "Context-window optimisation for AI coding agents: it sandboxes verbose tool output and keeps long sessions from forgetting how they started.",
        "use": "If your assistant starts repeating itself an hour in, this is the fix — throw away the noise, keep the thread.",
    },
    "cursor/plugins": {
        "cat": "agents",
        "what": "Cursor's plugin specification plus the official plugins: a standard way to package instructions, tools and commands for that editor.",
        "use": "Read it before buying into any 'agent stack' — it shows what a plugin is allowed to do on your machine.",
    },
    "anthropics/claude-plugins-official": {
        "cat": "agents",
        "what": "Anthropic's managed directory of Claude Code plugins it considers high quality — a curated shelf rather than a free-for-all.",
        "use": "The safest starting point for adding capabilities to Claude Code; anything listed here has been reviewed by the vendor.",
    },

    # -------------------------------------------------------------- security
    "cloudflare/security-audit-skill": {
        "cat": "security",
        "what": "Cloudflare's instructions for making a coding agent perform a proper multi-stage security review of a codebase, with checks that are independently verified instead of taken on trust.",
        "use": "If a portal touches client KYC, PAN or bank data, run this review before it goes live — it is a checklist an accounting firm can actually defend.",
    },
    "NVIDIA/OpenShell": {
        "cat": "security",
        "what": "A private runtime for autonomous AI agents: it wraps an agent in a sandbox so its file and network access can be controlled rather than hoped for.",
        "use": "The reason to care: an agent can work on a real machine without being able to wander into client folders uninvited.",
    },
    "NationalSecurityAgency/ghidra": {
        "cat": "security",
        "what": "The NSA's reverse-engineering framework. Not new, not AI — a serious tool for taking compiled software apart to see what it does.",
        "use": "Due-diligence curiosity: check what a downloaded program actually contains before running it on a machine holding client data.",
    },
    "NVIDIA/SkillSpector": {
        "cat": "security",
        "what": "A security scanner for AI agent skills: it looks for vulnerable or malicious patterns in the instruction files people are told to paste into their assistants.",
        "use": "Run a skill through it before installing — the whole genre is 'paste this text file and trust it'.",
    },

    # ----------------------------------------------------------------- media
    "heygen-com/hyperframes": {
        "cat": "media",
        "what": "Builds video from HTML. You (or an AI) write a web page, and it renders as a video file — the same content, output as reel, ad or explainer.",
        "use": "Design one good template for firm announcements, then produce every future video from it without opening a video editor.",
    },
    "Comfy-Org/ComfyUI": {
        "cat": "media",
        "what": "The standard local workbench for image and video generation models, wired together as a visual node graph. This is the official repository behind ComfyUI.",
        "use": "Batch-generate social images, deck backgrounds or product shots on your own machine, with no per-image charge and no uploads.",
    },
    "alchaincyf/huashu-design": {
        "cat": "design",
        "what": "A Chinese-language design skill set: one sentence in an agent, a deliverable out — web page, app prototype, editable PPTX, infographic or animation.",
        "use": "Prototype a client-facing one-pager or a slide deck skeleton without opening design software.",
    },

    # ----------------------------------------------------------------- money
    "AgriciDaniel/claude-seo": {
        "cat": "money",
        "what": "A packaged SEO team for an AI assistant: 26 sub-skills and 19 sub-agents covering technical audits, keyword research and content planning.",
        "use": "Audit your firm's website against the searches clients actually type, and get a prioritised fix list before paying an agency for a first pass.",
    },
    "gitroomhq/postiz-app": {
        "cat": "media",
        "what": "Open-source social media scheduling with agents in the loop: draft a month of posts, review, then let it publish on a timetable.",
        "use": "Keep a firm LinkedIn presence without a weekly scramble — one planning session covers the month.",
    },

    # ------------------------------------------------------------ dev / data
    "Graphify-Labs/graphify": {
        "cat": "dev",
        "what": "Turns an entire codebase — plus its documents, SQL schemas, config files and PDFs — into a map you can question in plain language.",
        "use": "Ask 'where is GST calculated?' on an inherited accounting system rather than reading ten thousand lines of code to find out.",
    },
    "anomalyco/opencode": {
        "cat": "dev",
        "what": "A free, open-source coding agent: a terminal program where you describe a task and it edits the files in your project.",
        "use": "The zero-cost way to try an AI coding assistant before deciding whether to pay for one.",
    },
    "earthtojake/text-to-cad": {
        "cat": "dev",
        "what": "Gives an agent CAD superpowers: describe a part, get a 3D model file you can open in CAD software.",
        "use": "A bracket, a jig, a replacement clip — sketch it in words and get something a fabricator can quote.",
    },
    "tashfeenahmed/freellmapi": {
        "cat": "dev",
        "what": "One API in front of 34 free LLM providers and hundreds of free model endpoints, advertised at billions of tokens a month.",
        "use": "A cheap way to experiment with many models without five subscriptions — free tiers are free for a reason, so expect rough edges.",
    },
    "VectifyAI/PageIndex": {
        "cat": "dev",
        "what": "A reasoning-based document index for retrieval that avoids vector search: it builds a navigable tree of a long document instead.",
        "use": "Better answers over 200-page PDFs — contracts, Acts, manuals — where chunk-and-embed search loses the thread.",
    },
    "rohitg00/ai-engineering-from-scratch": {
        "cat": "dev",
        "what": "A structured course for learning AI engineering by building: from fundamentals to shipping something.",
        "use": "If you want your team to actually understand these tools rather than forwarding screenshots of them.",
    },
    "supabase/supabase": {
        "cat": "dev",
        "what": "The Postgres development platform: a hosted database with authentication, file storage and APIs. The unglamorous floor under a lot of AI apps.",
        "use": "Where the data actually lives when you hire someone to build you an internal tool.",
    },
    "wshobson/agents": {
        "cat": "agents",
        "what": "A plugin marketplace for agent skills across several harnesses — Claude Code, Codex, Cursor and friends — in one catalogue.",
        "use": "Browse what exists before building your own instruction files from scratch.",
    },
    "android/skills": {
        "cat": "dev",
        "what": "Google's own AI-optimised instructions for Android development, published as skill files rather than prose documentation.",
        "use": "Only relevant if you are building an Android app — but a good example of how vendors now ship 'how to use me' files for agents.",
    },

    # ---------------------------------------------------------------- office
    "anthropics/knowledge-work-plugins": {
        "cat": "office",
        "what": "Anthropic's own open-source plugins for knowledge workers — documents, spreadsheets, decks and research inside an AI assistant. The closest thing on this list to an accountant's actual daily work.",
        "use": "Start here if you want AI help with Excel reconciliations, board notes and client email rather than with building software.",
    },
    "nightly-labs/openbot": {
        "cat": "agents",
        "what": "A local-first desktop workspace for persistent AI teammates: the assistants live on your machine and keep working between sessions.",
        "use": "A middle ground between one chat window and a full agent platform.",
    },
}

# Used only when a repository arrives on a board without a write-up above.
# Matched case-insensitively against GitHub's own description and topics.
CAT_HINTS = [
    ("security", ["security", "vulnerab", "audit", "sandbox", "malware"]),
    ("money", ["trading", "finance", "financial", "seo", "market", "invest", "payment", "accounting"]),
    ("media", ["video", "voice", "audio", "image", "diffusion", "render", "speech", "tts", "music", "design"]),
    ("office", ["knowledge work", "spreadsheet", "document", "slides", "powerpoint", "excel", "pdf"]),
    ("dev", ["code", "codebase", "cli", "database", "sql", "compiler", "ide", "editor", "framework", "api", "cad", "android"]),
    ("fun", ["robot", "game", "toy", "duck"]),
]
