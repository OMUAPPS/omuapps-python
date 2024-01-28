from omuserver.security import Permission
from omuserver.session import Session


class SessionPermission(Permission):
    def __init__(self, session: Session) -> None:
        self._session = session
