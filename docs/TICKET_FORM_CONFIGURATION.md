# Ticket creation form configuration

Administrators can open **Administration → Ticket Form Settings** to control the
employee ticket-creation experience.

- **Show** controls whether a field appears on the form.
- **Mandatory** requires a value in both the browser and backend API.
- Making a field mandatory automatically keeps it visible.
- Core fields (ticket type, client, subject, description, impact, and urgency) are
  always visible and mandatory.
- Ticket Type supports an administrator-selected automatic value. The initial
  system default is **Service Request** (`SERVICE_REQUEST`).
- Permission-controlled assignment and priority fields only appear for users who
  have the corresponding permission.
- Module depends on Product, and Subcategory depends on Category. Hiding a parent
  in the administration page also hides its child.
- The rules apply to the employee form and employee API creation. The separate
  client portal form retains its own safe, reduced field set.

The form is organized into a main issue area and a right-side **Additional
information** panel containing caller, branch, team, engineer, and followers.
Every configuration change is recorded as
`ticket_form.configuration.updated` in the audit trail.
