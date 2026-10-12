# AGENT.md — AutoInsta Autonomous Agent Specification

This document defines the agentic behavior, decision heuristics, system prompts, and theoretical foundation governing the **AutoInsta** egocentric lifelogging and social ingestion agent.

---

## 1. Theoretical Foundation: The Zahavi Bypass

In evolutionary biology and sociology, **Zahavi's Costly Signaling Theory** states that an honest social signal must impose a non-negotiable metabolic and cognitive cost upon the sender (selective attention, aesthetic discernment, editing effort, social risk).

**AutoInsta** implements an engineered **Batesian mimicry agent**:
- **Marginal Cost to the Host**: Near zero. Captures are a passive byproduct of human locomotion and daily life.
- **Multimodal Filtration & Synthesis**: Delegated to Gemini 1.5 Flash (Vision-Language Model).
- **Perceived Signal Value**: High aesthetic relevance, contextual wit, natural storytelling, and real-world presence.

---

## 2. Core Agent Pipeline

```
[ POV Optical Ingestion ]
         │ (Android / Wearable / RTSP Stream)
         ▼
[ Stage 1: Edge Pre-Filtering ]
         │ (Pocket darkness & static motion suppression)
         ▼
[ Stage 2: Multimodal VLM Evaluation (Gemini 1.5 Flash) ]
         ├── 2.1 Privacy & Safety Gate
         ├── 2.2 Aesthetic & Narrative Scoring (0.0 to 10.0)
         └── 2.3 Persona-Calibrated Caption Synthesis
         ▼
[ Stage 3: Policy & Cooldown Enforcement ]
         │ (Min score >= 7.0, Cooldown >= 60m, Max 4 posts/24h)
         ▼
[ Stage 4: Social Injection ]
         └── (Instagram Feed / Story via Instagrapi or Meta Graph API)
```

---

## 3. Multimodal Decision Rubric

The agent evaluates incoming frames under strict structured JSON output rules:

### A. Privacy & Safety Gate (`safety_pass: bool`)
The agent MUST immediately reject any frame containing:
- Computer / phone screens displaying private chats, banking apps, emails, or credentials.
- Credit cards, ID cards, passports, or private paper documents.
- Intimate, private, or bathroom environments.
- Non-consensual close-up captures in vulnerable situations.

### B. Image Quality Gate (`quality_pass: bool`)
- Pure black or heavy darkness (pocket/purse occlusion).
- Extreme motion blur or lens obstruction where the scene cannot be recognized.

### C. Aesthetic & Social Interest Scoring (`social_score: float` [0.0 - 10.0])
- `0.0 - 4.9`: Mundane, static, empty floor/wall, uninteresting routine desk shots.
- `5.0 - 6.9`: Ordinary daily scenes, acceptable but lacking narrative spark.
- `7.0 - 8.4`: **Posting Candidate**. Good lighting, appetizing food, vibrant urban geometry, aesthetic coffee, interesting human activity, scenic view.
- `8.5 - 10.0`: **Exceptional Shot**. High photographic serendipity, striking composition, rare moment, poetic atmosphere.

---

## 4. Persona Calibration & Caption Synthesis

The agent generates spontaneous, first-person Instagram captions according to active persona profiles:

| Persona | Tone & Stylistic Guidelines |
| :--- | :--- |
| `spontaneous_chic` | Effortless, casual, quiet observations. Embraces ambient light, city walks, coffee. |
| `witty_minimalist` | Deadpan, punchy 1-liners, understated humor, observant brevity. |
| `candid_existential`| Philosophical reflections on modern routines, geometry, and fleeting time. |
| `poetic_flaneur` | Evocative, sensory descriptions of textures, skies, shadows, and fleeting moments. |
| `tech_nomad` | Focused on mobility, craft, urban workspaces, transit, and modern ergonomics. |

---

## 5. Security & Rate-Limiting Protocols

1. **Anti-Spam Throttling**: The agent enforces a minimum cooldown interval (default: 60 minutes) and daily maximum (default: 4 posts/24h) to avoid platform bans and prevent signal inflation.
2. **Session Persistence**: Instagrapi credentials and session cookies are serialized locally to eliminate repeated logins.
3. **Dry-Run Safety**: In `dry_run` mode, the agent simulates the full pipeline, storing generated captions and logs without contacting external Instagram servers.
