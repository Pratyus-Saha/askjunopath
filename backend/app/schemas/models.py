from pydantic import BaseModel, Field, field_validator
import re
from datetime import date, time

class BirthDataRequest(BaseModel):
    birth_date: str = Field(..., description="Birth date in YYYY-MM-DD format")
    birth_time: str = Field(..., description="Birth time in HH:MM format (24-hour)")
    birth_city: str = Field(..., min_length=2, max_length=100, description="City of birth")

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            raise ValueError("birth_date must be in YYYY-MM-DD format")
        try:
            parts = value.split("-")
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            # Check calendar validity
            date(year, month, day)
        except Exception:
            raise ValueError("birth_date is not a valid calendar date")
        return value

    @field_validator("birth_time")
    @classmethod
    def validate_birth_time(cls, value: str) -> str:
        if not re.match(r"^\d{2}:\d{2}$", value):
            raise ValueError("birth_time must be in HH:MM format")
        try:
            parts = value.split(":")
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                raise ValueError("Hour must be 0-23 and minute must be 0-59")
        except Exception:
            raise ValueError("birth_time contains invalid hour or minute values")
        return value

class ChartGenerateResponse(BaseModel):
    cache_status: str
    chart_id: str
    chart_fingerprint: str
    chart: dict
