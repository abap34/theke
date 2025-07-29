from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional

from ..models.setting import Setting


def get_setting(db: Session, key: str) -> Optional[Setting]:
    """Get a setting by key"""
    return db.query(Setting).filter(Setting.key == key).first()


def get_setting_value(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a setting value by key, return default if not found"""
    setting = get_setting(db, key)
    return setting.value if setting else default


def create_or_update_setting(db: Session, key: str, value: str) -> Setting:
    """Create a new setting or update existing one"""
    setting = get_setting(db, key)
    
    if setting:
        # Update existing setting
        setting.value = value
    else:
        # Create new setting
        setting = Setting(key=key, value=value)
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    return setting


def delete_setting(db: Session, key: str) -> bool:
    """Delete a setting by key"""
    setting = get_setting(db, key)
    if setting:
        db.delete(setting)
        db.commit()
        return True
    return False


def get_all_settings(db: Session) -> list[Setting]:
    """Get all settings"""
    return db.query(Setting).all()


def initialize_default_settings(db: Session):
    """Initialize default settings if they don't exist"""
    from ..core.config import settings as config_settings
    
    # Check if summary_prompt setting exists, if not create it with default value
    if not get_setting(db, "summary_prompt"):
        create_or_update_setting(
            db, 
            "summary_prompt", 
            config_settings.SUMMARY_PROMPT
        )