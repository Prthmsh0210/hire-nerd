# database.py
import logging
import os
from datetime import datetime, timedelta # Added timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, field_validator, EmailStr # Added EmailStr
from typing import Optional, List, Any
from bson import ObjectId

MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "hisbandhr_db")

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file_path = os.path.join(LOG_DIR, f"hisbandhr_backend_{datetime.now().strftime('%Y-%m-%d')}.log")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if logger.hasHandlers():
    logger.handlers.clear()

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s")

file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any, _: Any = None):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError(f"Invalid ObjectId: {v}")

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema_obj: Any, handler: Any) -> dict:
        from pydantic.json_schema import JsonSchemaValue
        return JsonSchemaValue({'type': 'string', 'format': 'objectid'})


class MongoDBManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[Any] = None

    async def connect_to_database(self):
        logger.info(f"Attempting to connect to MongoDB at {MONGO_CONNECTION_STRING}...")
        try:
            self.client = AsyncIOMotorClient(
                MONGO_CONNECTION_STRING,
                serverSelectionTimeoutMS=5000,
                uuidRepresentation='standard'
            )
            await self.client.admin.command('ping')
            self.db = self.client[DATABASE_NAME]
            logger.info(f"Successfully connected to MongoDB, database: {DATABASE_NAME}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
            if self.client:
                self.client.close()
            self.client = None
            self.db = None

    async def close_database_connection(self):
        if self.client:
            logger.info("Closing MongoDB connection...")
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB connection closed and resources released.")

    def get_collection(self, collection_name: str):
        if self.db is not None:
            return self.db[collection_name]
        else:
            logger.error(f"Database not connected. Cannot get collection '{collection_name}'.")
            return None

db_manager = MongoDBManager()

class BaseDBModel(BaseModel):
    model_config = {
        "populate_by_name": True,
        "json_encoders": {
            ObjectId: str,
            PyObjectId: str
        },
        "arbitrary_types_allowed": True
    }

class JobDescriptionDB(BaseDBModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    filename: str
    parsed_text: str
    keywords: List[str] = Field(default_factory=list)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

class ResumeDB(BaseDBModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    jd_id: Optional[PyObjectId] = None
    session_id: Optional[str] = None
    filename: str
    parsed_text: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

class MatchResultDB(BaseDBModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    resume_id: PyObjectId
    jd_id: PyObjectId
    session_id: Optional[str] = None
    candidate_name: str
    jd_fit_score: int
    interview_score: float
    red_flags: List[str] = Field(default_factory=list)
    experience_summary: str
    matched_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('resume_id', 'jd_id', mode='before')
    @classmethod
    def validate_object_id_fields(cls, v: Any) -> ObjectId:
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, PyObjectId):
            return ObjectId(str(v))
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError(f"Field must be a valid ObjectId string or ObjectId instance: '{v}' (type: {type(v)})")

# NEW MODEL for scheduled interviews
class ScheduledInterviewDB(BaseDBModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    candidate_name: str
    candidate_email: EmailStr # Use EmailStr for validation
    interviewer_emails: List[EmailStr] # List of valid emails
    start_time: datetime
    end_time: datetime
    duration_minutes: int 
    google_meet_link: Optional[str] = None
    google_calendar_link: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Optional: jd_id and resume_id if you want to link back to the specific match
    jd_id: Optional[PyObjectId] = None
    resume_id: Optional[PyObjectId] = None