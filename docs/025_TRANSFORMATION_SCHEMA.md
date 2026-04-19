# 025_transformation.json — Schema + Template

**Obligatorisk artefakt:** Skal eksistere i `domains/{domain}/025_transformation.json` FØR N-B BUILD starter.

**Formål:** Bevise at green-ai er et *redesign* — ikke en clone af legacy.

---

## Schema

```json
{
  "domain": "string",
  "transformation_date": "YYYY-MM-DD",
  "verdict": "REDESIGNED | CLONE_RISK | CLONE_STOP",
  "simplifications": [
    {
      "legacy_concept": "string — hvad hed det i sms-service",
      "green_ai_concept": "string — hvad hedder det i green-ai",
      "rationale": "string — hvorfor er det forenklet"
    }
  ],
  "merged_concepts": [
    {
      "legacy_concepts": ["string", "string"],
      "merged_into": "string",
      "rationale": "string"
    }
  ],
  "dropped_concepts": [
    {
      "legacy_concept": "string",
      "reason": "out_of_scope | replaced_by | not_needed"
    }
  ],
  "flow_redesign": [
    {
      "legacy_flow": "string — navn på legacy flow",
      "green_ai_flow": "string — navn på green-ai flow",
      "behavior_change": "NO | YES",
      "behavior_change_description": "string — kun udfyldt hvis YES"
    }
  ],
  "ux_improvements": [
    "string — beskrivelse af UX-forbedring"
  ],
  "clone_risk_check": {
    "before_summary": "string — kort beskrivelse af legacy design",
    "after_summary": "string — kort beskrivelse af green-ai design",
    "structural_similarity": "LOW | MEDIUM | HIGH",
    "verdict": "SAFE | BORDERLINE | CLONE_STOP"
  }
}
```

---

## Hard stop regel

```
IF clone_risk_check.verdict = "CLONE_STOP"
  OR verdict = "CLONE_STOP"
  OR clone_risk_check.structural_similarity = "HIGH"
→ NO TRANSFORMATION — RISK OF CLONE
→ Architect review PÅKRÆVET inden BUILD
```

---

## Minimumskrav

For at `verdict = "REDESIGNED"` er gyldigt:
- ≥1 `simplifications` ELLER ≥1 `merged_concepts`
- `clone_risk_check.structural_similarity` = LOW eller MEDIUM
- Alle flows har `behavior_change` sat eksplicit

---

## Eksempel (customer_administration)

```json
{
  "domain": "customer_administration",
  "transformation_date": "2026-04-19",
  "verdict": "REDESIGNED",
  "simplifications": [
    {
      "legacy_concept": "AssignRole + RemoveRole (separate endpoints)",
      "green_ai_concept": "SetUserRoleAccess (replace-semantics — én endpoint erstatter begge)",
      "rationale": "Legacy kræver to kald for at ændre rolle. green-ai sender komplet ønsket tilstand."
    }
  ],
  "merged_concepts": [
    {
      "legacy_concepts": ["CreateUser", "AssignToCustomer", "SetDefaultRole"],
      "merged_into": "CreateCustomerUser (one-step create)",
      "rationale": "Legacy spreder brugeroprettelse over 3 steps. green-ai gør det atomisk."
    }
  ],
  "dropped_concepts": [],
  "flow_redesign": [
    {
      "legacy_flow": "UserRoleManagementFlow",
      "green_ai_flow": "RoleAccessFlow",
      "behavior_change": "NO",
      "behavior_change_description": ""
    }
  ],
  "ux_improvements": [
    "Bruger oprettes og tilknyttes kunde i ét kald — ingen multi-step wizard behøves"
  ],
  "clone_risk_check": {
    "before_summary": "Separate CRUD endpoints per relation-tabel, ingen atomiske operationer",
    "after_summary": "Replace-semantics, one-step create, explicit reactivate flow",
    "structural_similarity": "LOW",
    "verdict": "SAFE"
  }
}
```
