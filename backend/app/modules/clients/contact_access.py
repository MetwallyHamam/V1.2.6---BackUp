from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Contact, ContactClientLink


def contact_belongs_to_client(db: Session, contact: Contact, client_id: int) -> bool:
    """Return whether a contact is owned by or explicitly linked to a client."""
    if contact.client_id == client_id:
        return True
    return db.scalar(
        select(ContactClientLink.id).where(
            ContactClientLink.contact_id == contact.id,
            ContactClientLink.client_id == client_id,
        )
    ) is not None
