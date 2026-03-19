import importlib
from pathlib import Path

from .services import ArmyValidationService, CatalogService, HtmlExportService, OptionFormatter
from .session import SessionStateManager


class ArmyBuilderApp:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = Path(base_dir or Path(__file__).resolve().parent.parent)
        self.session = SessionStateManager()
        self.formatter = OptionFormatter()
        self.catalog_service = CatalogService(self.base_dir)
        self.validation_service = ArmyValidationService(self.formatter)
        self.export_service = HtmlExportService()

    def run(self) -> None:
        self.session.ensure_defaults()
        importlib.import_module("armybuilder.legacy_ui")
