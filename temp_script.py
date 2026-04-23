import re
with open("temp/README.md", encoding="utf-8") as f:
    content = f.read()
gateway_marker = "## COPILOT \u2192 ARCHITECT \u2014 ANALYSIS TOOL AS GATEWAY (2026-04-23)"
build_marker = "## COPILOT \u2192 ARCHITECT \u2014 BUILD EXECUTION PROTOCOL (2026-04-23)"
selfdef_marker = "## ANALYSIS TOOL SELF-DEFINITION"
g_start = content.index(gateway_marker)
b_start = content.index(build_marker)
s_start = content.index(selfdef_marker)
gateway_section = content[g_start:b_start]
build_section = content[b_start:s_start]
gateway_ref = gateway_marker + "\n\n> **PERMANENT SSOT \u2014 se:** `harvest/architect-review/gateway_protocol.md` (LOCKED)\n\n---\n\n"
build_ref = build_marker + "\n\n> **PERMANENT SSOT \u2014 se:** `harvest/architect-review/build_execution_protocol.md` (LOCKED)\n\n---\n\n"
content = content.replace(gateway_section, gateway_ref)
content = content.replace(build_section, build_ref)
with open("temp/README.md", "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
print(f"New file length: {len(content)}")
print(f"Gateway section length now: {content.index(build_marker) - content.index(gateway_marker)}")
