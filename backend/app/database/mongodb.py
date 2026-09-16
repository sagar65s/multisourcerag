import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.core.config import Settings
from app.core.observability import logger


class MongoState:
    client: AsyncIOMotorClient | None = None
    database: AsyncIOMotorDatabase | None = None
    indexes_ready: bool = False
    last_error: str | None = None


mongo = MongoState()


class DatabaseUnavailableError(RuntimeError):
    """Raised when a request needs MongoDB while it is reconnecting."""


def _client_options(uri: str) -> dict[str, object]:
    """Build secure, cross-platform MongoDB client options.

    Atlas SRV connections enable TLS automatically.  Supplying certifi's CA
    bundle avoids relying on a stale or unavailable Windows certificate store
    while keeping certificate and hostname verification enabled.
    """

    options: dict[str, object] = {
        "serverSelectionTimeoutMS": 5_000,
        "connectTimeoutMS": 5_000,
        "socketTimeoutMS": 15_000,
        "appName": "multisource-ai",
    }
    normalized_uri = uri.lower()
    if normalized_uri.startswith("mongodb+srv://") or "tls=true" in normalized_uri or "ssl=true" in normalized_uri:
        options.update({"tls": True, "tlsCAFile": certifi.where()})
    return options


async def _ensure_indexes(database: AsyncIOMotorDatabase) -> None:
    await database.users.create_index([("uid", 1)], unique=True)
    await database.users.create_index([("last_login_at", -1)])
    await database.user_settings.create_index([("owner_id", 1)], unique=True)
    await database.workspaces.create_index([("owner_id", 1), ("updated_at", -1)])
    await database.workspaces.create_index([("owner_id", 1), ("name", 1)], unique=True)
    await database.documents.create_index([("owner_id", 1), ("workspace_id", 1), ("created_at", -1)])
    indexes = await database.processing_jobs.index_information()
    if "owner_id_1_document_id_1" in indexes:
        await database.processing_jobs.drop_index("owner_id_1_document_id_1")
    await database.processing_jobs.delete_many({"job_id": {"$exists": False}})
    await database.processing_jobs.create_index([("job_id", 1)], unique=True)
    await database.processing_jobs.create_index([("owner_id", 1), ("workspace_id", 1), ("updated_at", -1)])
    await database.processing_jobs.create_index([("owner_id", 1), ("status", 1), ("updated_at", -1)])
    await database.processing_jobs.create_index("expires_at", expireAfterSeconds=0, name="processing_job_retention")
    await database.document_chunks.create_index([("owner_id", 1), ("workspace_id", 1), ("text", "text")], name="authorized_chunk_text")
    await database.document_chunks.create_index([("owner_id", 1), ("workspace_id", 1), ("document_id", 1), ("chunk_id", 1)], unique=True)
    await database.website_sources.create_index([("owner_id", 1), ("workspace_id", 1), ("created_at", -1)])
    await database.website_sources.create_index([("owner_id", 1), ("workspace_id", 1), ("normalized_url", 1)], unique=True)
    await database.research_sessions.create_index([("owner_id", 1), ("created_at", -1)])
    await database.research_sessions.create_index([("owner_id", 1), ("kind", 1), ("updated_at", -1)])
    await database.document_artifacts.create_index([("owner_id", 1), ("workspace_id", 1), ("updated_at", -1)])
    await database.document_artifacts.create_index([("owner_id", 1), ("tool", 1), ("updated_at", -1)])
    await database.conversations.create_index([("owner_id", 1), ("updated_at", -1)])
    await database.messages.create_index([("owner_id", 1), ("conversation_id", 1), ("created_at", 1)])
    await database.saved_answers.create_index([("owner_id", 1), ("message_id", 1)], unique=True)
    await database.bookmarks.create_index([("owner_id", 1), ("message_id", 1), ("source.id", 1)], unique=True)
    await database.feedback.create_index([("owner_id", 1), ("message_id", 1)], unique=True)
    await database.provider_logs.create_index([("provider", 1), ("created_at", -1)])
    await database.provider_logs.create_index("expires_at", expireAfterSeconds=0, name="provider_log_retention")
    await database.search_logs.create_index([("provider", 1), ("created_at", -1)])
    await database.search_logs.create_index("expires_at", expireAfterSeconds=0, name="search_log_retention")
    await database.audit_logs.create_index([("actor_id", 1), ("created_at", -1)])
    await database.audit_logs.create_index("expires_at", expireAfterSeconds=0, name="audit_log_retention")
    await database.security_logs.create_index([("actor_id", 1), ("created_at", -1)])
    await database.security_logs.create_index("expires_at", expireAfterSeconds=0, name="security_log_retention")


async def connect_mongodb(settings: Settings) -> bool:
    if mongo.client is not None and mongo.database is not None:
        if not mongo.indexes_ready:
            try:
                await _ensure_indexes(mongo.database)
            except (PyMongoError, OSError, TimeoutError) as exc:
                logger.warning("mongodb_index_maintenance_deferred", error_type=type(exc).__name__)
            else:
                mongo.indexes_ready = True
                mongo.last_error = None
        return True
    client = AsyncIOMotorClient(settings.mongodb_uri, **_client_options(settings.mongodb_uri))
    database = client[settings.mongodb_database]
    try:
        await client.admin.command("ping")
    except (PyMongoError, OSError, TimeoutError):
        client.close()
        mongo.client = None
        mongo.database = None
        mongo.indexes_ready = False
        mongo.last_error = "MongoDB Atlas is unreachable; automatic reconnection is active"
        return False

    mongo.client = client
    mongo.database = database
    mongo.last_error = None
    try:
        await _ensure_indexes(database)
    except (PyMongoError, OSError, TimeoutError) as exc:
        # Index maintenance must not turn a healthy Atlas connection into a
        # complete application outage. It is retried by the maintenance loop.
        mongo.indexes_ready = False
        mongo.last_error = "Connected; MongoDB index maintenance is pending"
        logger.warning("mongodb_index_maintenance_deferred", error_type=type(exc).__name__)
    else:
        mongo.indexes_ready = True
    return True


async def disconnect_mongodb() -> None:
    if mongo.client is not None:
        mongo.client.close()
    mongo.client = None
    mongo.database = None
    mongo.indexes_ready = False


def get_database() -> AsyncIOMotorDatabase:
    if mongo.database is None:
        raise DatabaseUnavailableError("Database is temporarily unavailable. MultiSource AI is reconnecting automatically.")
    return mongo.database


def mongodb_status() -> dict[str, str | bool | None]:
    return {
        "connected": mongo.database is not None,
        "indexes_ready": mongo.indexes_ready,
        "message": mongo.last_error,
    }
