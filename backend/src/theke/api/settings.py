from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..crud import setting as setting_crud
from ..schemas.setting import (
    SummaryPromptResponse,
    SummaryPromptUpdate,
    ModelSettingResponse,
    ModelSettingUpdate,
    AvailableModelsResponse
)
from ..core.config import settings as config_settings

router = APIRouter()


@router.get("/summary-prompt", response_model=SummaryPromptResponse)
async def get_summary_prompt(db: Session = Depends(get_db)):
    """Get the current summary prompt"""
    try:
        prompt = setting_crud.get_setting_value(
            db,
            "summary_prompt",
            default=config_settings.SUMMARY_PROMPT
        )
        return SummaryPromptResponse(prompt=prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary prompt: {str(e)}")


@router.put("/summary-prompt")
async def update_summary_prompt(update: SummaryPromptUpdate, db: Session = Depends(get_db)):
    """Update the summary prompt"""
    try:
        setting_crud.create_or_update_setting(db, "summary_prompt", update.prompt)
        return {"message": "Summary prompt updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update summary prompt: {str(e)}")


@router.get("/available-models", response_model=AvailableModelsResponse)
async def get_available_models():
    """Get available Anthropic models"""
    try:
        # Anthropic Claude models
        # Based on https://docs.anthropic.com/en/docs/about-claude/models
        models = [
            {
                "id": "claude-3-5-sonnet-20241022",
                "name": "Claude 3.5 Sonnet (Latest)",
                "description": "Most intelligent model with strong vision capabilities"
            },
            {
                "id": "claude-3-5-haiku-20241022",
                "name": "Claude 3.5 Haiku",
                "description": "Fastest and most cost-effective model"
            },
            {
                "id": "claude-3-opus-20240229",
                "name": "Claude 3 Opus",
                "description": "Previous generation most intelligent model"
            },
            {
                "id": "claude-3-sonnet-20240229",
                "name": "Claude 3 Sonnet",
                "description": "Previous generation balanced model"
            },
            {
                "id": "claude-3-haiku-20240307",
                "name": "Claude 3 Haiku",
                "description": "Previous generation fastest model"
            }
        ]
        return AvailableModelsResponse(models=models)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available models: {str(e)}")


@router.get("/model", response_model=ModelSettingResponse)
async def get_model_setting(db: Session = Depends(get_db)):
    """Get the current model setting"""
    try:
        model = setting_crud.get_setting_value(
            db,
            "anthropic_model",
            default=config_settings.ANTHROPIC_MODEL
        )
        return ModelSettingResponse(model=model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model setting: {str(e)}")


@router.put("/model")
async def update_model_setting(update: ModelSettingUpdate, db: Session = Depends(get_db)):
    """Update the model setting"""
    try:
        setting_crud.create_or_update_setting(db, "anthropic_model", update.model)
        return {"message": "Model setting updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update model setting: {str(e)}")