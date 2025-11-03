from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


class SettingBase(BaseModel):
    key: str
    value: str


class SettingCreate(SettingBase):
    pass


class SettingUpdate(BaseModel):
    value: str


class Setting(SettingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SummaryPromptResponse(BaseModel):
    prompt: str


class SummaryPromptUpdate(BaseModel):
    prompt: str


class ModelInfo(BaseModel):
    id: str
    name: str
    description: str


class AvailableModelsResponse(BaseModel):
    models: List[Dict[str, Any]]


class ModelSettingResponse(BaseModel):
    model: str


class ModelSettingUpdate(BaseModel):
    model: str