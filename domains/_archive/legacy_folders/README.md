# Legacy Domain Folders — Archive

## What is this?

These folders are legacy domain output artifacts from early analysis runs.

They are **not tracked** by `domain_state.json` and are **not used** by the domain engine.

## Why archived here?

Moved during **SLICE-07** cleanup (2026-04-02) to remove clutter from `domains/` root.  
The engine reads from `domain_state.json` keys — folder names in `domains/` are not scanned.

## Contents

28 PascalCase folders from pre-v3 analysis:

Client, Converter, Customer, Database, Economic, GatewayAPI, Import, Inbound, Infobip, Job,
Maintenance, Map, Notify, Operations, Pipeline, Profile, Prospect, Queue, Scheduled, Send,
SendGrid, Sms, Standard, Status, Strex, Subscribe, Unsubscribe, User

## Status

Read-only reference. Do not run engine against these folders.  
May be deleted after confirming content is absorbed into tracked domains.
