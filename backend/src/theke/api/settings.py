from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..crud import setting as setting_crud
from ..schemas.setting import SummaryPromptResponse, SummaryPromptUpdate
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