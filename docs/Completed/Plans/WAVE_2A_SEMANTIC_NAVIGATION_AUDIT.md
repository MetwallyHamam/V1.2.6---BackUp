# Wave 2A Semantic Navigation Audit

Status: complete for Wave 2A (2026-08-20)

## Converted

- Main desktop/mobile navigation items use router anchors with stable paths.
- User hierarchy cards and Create User use semantic links.
- Client access/edit icon actions use semantic links.
- Shared `SemanticLink` renders an accessible anchor with a stable `href`; its focused component test passes.
- Ticket numbers, portal request link lists, notification deep links, and executive contract drilldowns expose semantic destinations.

Imperative handlers retained by this audit are post-submit redirects, cancel/back commands, modal-only actions, downloads, destructive actions, chart-library callbacks with accessible evidence alternatives, and controls without stable destinations.
