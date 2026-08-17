"""Application database composition root."""

from dashboard.config import DATABASE_FILE
from dashboard.database_manager import DatabaseManager
from dashboard.initializer import DatabaseInitializer
from dashboard.repositories.analytics_repository import AnalyticsRepository
from dashboard.repositories.bulk_repository import BulkRepository
from dashboard.repositories.maintenance_repository import MaintenanceRepository
from dashboard.repositories.outreach_repository import OutreachRepository
from dashboard.repositories.prospect_repository import ProspectRepository
from dashboard.repositories.utility_repository import UtilityRepository


db = DatabaseManager(DATABASE_FILE)
DatabaseInitializer(db).initialize()

prospects = ProspectRepository(db)
outreach = OutreachRepository(db)
analytics = AnalyticsRepository(db)
bulk = BulkRepository(db)
maintenance = MaintenanceRepository(db)
utility = UtilityRepository(db)
