from sqlalchemy.orm import Session


class Repository:
    """Repositories flush, but only the unit of work may commit."""

    def __init__(self, session: Session) -> None:
        self.session = session
