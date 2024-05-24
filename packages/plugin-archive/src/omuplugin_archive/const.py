from omu.app import App
from omu.identifier import Identifier

from .version import VERSION

IDENTIFIER = Identifier.from_key("com.omuapps:archive/plugin")
APP = App(
    id=IDENTIFIER,
    version=VERSION,
)
