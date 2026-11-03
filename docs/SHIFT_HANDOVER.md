# Ticket Shift Handover

Shift handover is a tracked ticket workflow for work that must continue with the night shift or the next support shift.

- The assigned engineer or an authorized dispatcher selects **Hand over ticket**.
- A receiving engineer, follow-up time, and handover reason are recorded.
- The ticket changes to `PENDING_INTERNAL`; its pending reason is prefixed with `Shift handover` and remains Millensys-accountable for SLA purposes.
- When requested, ownership is reassigned to the receiving engineer and the normal assignment history is recorded.
- The recipient receives a shift-handover notification.
- The receiving engineer selects **Mark handed over** to acknowledge the transfer.
- Every handover retains sender, recipient, reason, follow-up time, status, completion actor, and timestamps in `ticket_shift_handovers`.

Tickets with handover history appear under **Tickets → Shift handover**. Pending handovers are also counted by the **Shift handovers** dashboard KPI card, which opens that tab.
