# SupportHub 1.59.5 — Contract Coverage Removal History Preservation

## Purpose

Correct contract product, module, and service coverage removal so unused rules are removed while ticket history remains valid.

## Correction

- Deletes a selected coverage rule when no ticket for a client linked to the contract matches its scoped product, module, service, branch, environment, or ticket type.
- Retires a rule instead of deleting it when matching ticket history exists for a linked contract client, preserving the coverage record, its revisions, and an audit entry.
- Applies the rule consistently to both single-rule and grouped product/module/service removal.
- Replaces the incorrect renewal warning with the API's actual failure message and identifies client request timeouts clearly.

## Deployment

- Deploy this release over 1.59.4.
- No database migration is required; the database head remains `0177_ticket_archive`.
