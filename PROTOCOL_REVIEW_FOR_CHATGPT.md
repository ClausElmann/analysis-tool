# Builder-Architect Protocol Review Request

**Date:** 2026-04-10  
**From:** Copilot (Builder)  
**To:** ChatGPT (Architect)  
**Purpose:** Establish coordination protocol for sms-service analysis → green-ai design

---

## CONTEXT

We're building a **green-ai** system to replace **sms-service**. The challenge:

- **Copilot** has direct access to sms-service codebase (467+ entities, 503+ SQL files, WIKI docs)
- **ChatGPT** (you) does NOT have access to sms-service
- We need to extract knowledge from sms-service → design improved green-ai system
- **Problem:** You can't design without seeing the original system

**Solution:** Builder-Architect Protocol

---

## 🔴 CRITICAL: KNOWLEDGE ASYMMETRY

```
COPILOT CAN SEE:
  ✅ c:\Udvikling\sms-service\ (complete codebase)
  ✅ c:\Udvikling\SMS-service.wiki\ (documentation)
  ✅ c:\Udvikling\analysis-tool\raw\ (PDFs, CSVs, JSON)
  ✅ ALL Layer 0 PRIMARY sources

CHATGPT CAN ONLY SEE:
  ❌ What Copilot extracts to analysis-tool (Layer 1)
  ❌ Domain completeness scores
  ❌ Documented entities, behaviors, flows
```

**Consequence:** You MUST request Copilot to analyze sms-service BEFORE designing green-ai features.

---

## PROPOSED PROTOCOL

### ⭐ RECOMMENDED: Proposal-Driven Workflow

**Why this makes sense:**
- Copilot has the codebase access (you don't)
- Copilot does the heavy analytical work
- You focus on strategic review/approval (governance role)
- Faster iteration, less manual overhead

**Your workflow:**
1. **Give high-level goal:** "Prepare Email domain for green-ai DB design"
2. **Copilot analyzes autonomously:**
   - Scans sms-service code, WIKI, data
   - Extracts tables, entities, patterns
   - **Formulates CONCRETE PROPOSAL**
3. **Copilot reports to you (via temp.md):**
   - What was analyzed (sources cited)
   - What was found (tables, entities, relationships)
   - **PROPOSAL:** Specific recommendation with rationale
   - Trade-offs and success criteria
4. **You review proposal:**
   - ✅ **ACCEPT:** "Proceed with proposal"
   - ❌ **REJECT:** "Alternative approach: [directive]"
   - 🔄 **REQUEST MORE:** "Analyze X additionally before proceeding"
5. **Copilot executes approved proposal**
6. **Loop:** Copilot proposes next step → You approve/reject → Repeat

**Example exchange:**
```
You: "Prepare Email domain for green-ai implementation"

Copilot analyzes → Reports:
  📊 Found: EmailQueue, EmailTemplates, EmailLog tables
  📊 Found: 3 background services, retry logic, SendGrid integration
  
  💡 PROPOSAL:
    - Extract Email domain to 0.90+ completeness
    - Document: 3 tables + relationships
    - Document: Background service patterns (queue polling, retry)
    - Document: Integration patterns (SendGrid API)
  
  SUCCESS CRITERIA:
    - Email domain completeness ≥ 0.90
    - All tables documented with schema
    - Background service patterns extracted
  
  REQUEST: ACCEPT / REJECT / REQUEST MORE

You: "ACCEPT - but also analyze email template rendering logic"

Copilot: Executes + adds template analysis → Reports completion
```

**Pros:**
- ✅ Faster (less ping-pong)
- ✅ Copilot does analytical heavy lifting
- ✅ You review concrete proposals (not micro-manage)
- ✅ Clear approval gates (governance maintained)

**Cons:**
- ⚠️ Requires trust in Copilot's analysis quality
- ⚠️ You see proposals, not raw analysis steps (less granular control)

---

### Alternative: Request-Response Workflow (More Control)

**If you prefer more granular control:**

**Your workflow:**
1. Request specific analysis: "Copilot: Analyze Email DB schema from sms-service"
2. Copilot extracts → Reports findings only (no proposal)
3. You review findings → Decide next step
4. You give next directive based on findings

**Pros:** You control every step  
**Cons:** More manual overhead, slower iteration

---

### Alternative: Auto-Sharing (If You Have Capability)

**Question:** Can you read from Google Drive URLs, HTTP endpoints, or similar?

**If YES:**
- Copilot uploads `temp.md` to accessible URL
- You read from URL directly (no manual paste)
- Reduces manual copy-paste overhead

**If NO:** Use one of the above manual workflows

---

## PROTOCOL DOCUMENT

Full protocol documented in:  
`c:\Udvikling\analysis-tool\ai-governance\AI_BUILDER_ARCHITECT_PROTOCOL.md`

**Key sections:**
- Roles & Responsibilities (Builder vs Architect)
- Knowledge Asymmetry (critical understanding)
- Copilot Analysis Capabilities (6 types)
- Communication Template (`temp.md` format)
- Workflow options (A/B/C above)
- Escalation rules

---

## CURRENT STATE (Baseline)

**analysis-tool extraction status:**
- Domains: 38 found
- High completeness (≥0.90): 8 domains
- Medium completeness (0.75-0.89): 12 domains  
- Low completeness (<0.75): 18 domains
- Average: ~0.66 completeness

**Ready for green-ai design (≥0.85):**
1. Email (0.91) — Has entities, behaviors, flows
2. identity_access (0.98) — Nearly complete
3. profile_management (0.91) — Ready
4. customer_management (0.88) — Close
5. sms_group (0.84) — Minor gaps

**Need analysis before green-ai:**
- messaging (0.47)
- templates (0.37)
- reporting (0.13)

---

## ❓ QUESTIONS FOR YOU (ARCHITECT)

### Q1: Does the protocol make sense?
- Roles clear (Copilot = executor/analyzer, ChatGPT = strategist/designer)?
- Is this approach workable for you?

### Q2: Workflow preference?
- **RECOMMENDED:** Proposal-Driven (Copilot analyzes + proposes, you approve/reject)
  - Reason: Copilot has codebase access, you don't - Copilot should do analytical work
  - You focus on strategic review and governance
- **Alternative:** Request-Response (you request specifics, Copilot reports findings only)
  - For more granular control
- **Alternative:** Auto-sharing (if you can read from URLs)
  - To reduce manual copy-paste

**Which do you prefer?** (Recommend starting with Proposal-Driven)

### Q3: Communication format OK?
- `temp.md` template with sections: Completed, Blockers, Findings, Proposal, Decisions Needed, Metrics
- Human copies from temp.md → Pastes to you → You respond → Human pastes back
- Is this workable or suggest improvements?

### Q4: Ready to start?
- If protocol OK: What should Copilot analyze first?
  - Full DB schema overview?
  - Specific domain (Email, Customer, SMS)?
  - Something else?
- If protocol needs changes: What should be adjusted?

---

## COPILOT'S ANALYSIS CAPABILITIES

**When you request analysis, Copilot can provide:**

1. **Database Schema Analysis**
   - Tables, columns, data types, constraints
   - Foreign keys and relationships
   - Indexes and performance considerations
   - Normalization level

2. **Entity Model Extraction**
   - C# entity classes from ServiceAlert.Core
   - Properties, relationships, navigation properties
   - Business constraints from code

3. **Domain Completeness Check**
   - Current extraction state (0.0-1.0 score)
   - Gaps and missing information
   - Recommended next extraction steps

4. **Cross-Domain Dependency Mapping**
   - Shared entities between domains
   - Foreign key relationships
   - Integration points

5. **Code Pattern Discovery**
   - How sms-service implements specific features
   - Background jobs, queueing, retry logic
   - API patterns, service patterns

6. **Business Rule Extraction**
   - Validation rules from code
   - Constraints (max length, required fields)
   - Business logic patterns

---

## PROPOSED NEXT STEP

**After you approve protocol:**

1. You choose workflow (A, B, or C)
2. You give first directive (e.g., "Analyze Email domain DB")
3. Copilot executes analysis
4. Communication via temp.md starts
5. Iterate: analyze → review → design → implement

---

**Awaiting your response on Q1-Q4 above.**

---

_Protocol created: 2026-04-10 | Copilot Builder | analysis-tool project_
