import asyncio
import json
from typing import Optional
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..crud import job as job_crud
from ..crud import paper as paper_crud
from ..services.llm_service import generate_summary
from ..schemas import paper as paper_schema


async def process_summary_generation(job_id: str):
    """Process summary generation job in background"""
    db = next(get_db())
    try:
        # Get job details
        job = job_crud.get_job(db, job_id)
        if not job or job.status != "pending":
            print(f"Job {job_id} not found or not pending")
            return

        # Start processing
        job_crud.start_job(db, job_id)
        
        # Get paper
        paper = paper_crud.get_paper(db, job.paper_id)
        if not paper:
            job_crud.fail_job(db, job_id, "Paper not found")
            return

        # Parse parameters
        parameters = json.loads(job.parameters) if job.parameters else {}
        custom_prompt = parameters.get("custom_prompt")

        try:
            # Update progress
            job_crud.update_job_status(
                db, job_id, "processing", 
                progress=25, 
                progress_message="要約を生成中..."
            )

            # Generate summary
            summary = await generate_summary(paper, custom_prompt=custom_prompt, db_session=db)

            # Update progress
            job_crud.update_job_status(
                db, job_id, "processing", 
                progress=75, 
                progress_message="論文を更新中..."
            )

            # Update paper with summary
            paper_update = paper_schema.PaperUpdate(summary=summary)
            updated_paper = paper_crud.update_paper(db, job.paper_id, paper_update)

            # Complete job
            result = {
                "summary": summary,
                "paper_id": job.paper_id
            }
            job_crud.complete_job(db, job_id, result)
            
            print(f"Summary generation completed for job {job_id}")

        except Exception as e:
            error_message = f"要約生成に失敗しました: {str(e)}"
            job_crud.fail_job(db, job_id, error_message)
            print(f"Summary generation failed for job {job_id}: {str(e)}")

    except Exception as e:
        print(f"Background task error for job {job_id}: {str(e)}")
        if 'job' in locals():
            job_crud.fail_job(db, job_id, f"システムエラー: {str(e)}")
    finally:
        db.close()


def start_background_task(job_id: str, task_type: str):
    """Start a background task based on type"""
    if task_type == "summary_generation":
        # Schedule the task
        asyncio.create_task(process_summary_generation(job_id))
    else:
        print(f"Unknown task type: {task_type}")


async def process_pending_jobs():
    """Process all pending jobs (for use with a scheduler)"""
    db = next(get_db())
    try:
        pending_jobs = job_crud.get_pending_jobs(db)
        
        for job in pending_jobs:
            print(f"Processing pending job: {job.id} ({job.type})")
            start_background_task(job.id, job.type)
            
    finally:
        db.close()