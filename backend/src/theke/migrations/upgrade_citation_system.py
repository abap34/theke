"""
Citation System Enhancement Migration Script
Upgrades the database schema to support the enhanced citation system design.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict


def upgrade_database(db_path: str = "data/theke.db"):
    """Upgrade database schema for enhanced citation system"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add new columns to papers table
        print("Upgrading papers table...")

        # Check if columns already exist
        cursor.execute("PRAGMA table_info(papers)")
        existing_columns = [row[1] for row in cursor.fetchall()]

        if "external_ids" not in existing_columns:
            cursor.execute("ALTER TABLE papers ADD COLUMN external_ids TEXT")
            print("Added external_ids column to papers table")

        if "citation_count" not in existing_columns:
            cursor.execute("ALTER TABLE papers ADD COLUMN citation_count INTEGER")
            print("Added citation_count column to papers table")

        if "reference_count" not in existing_columns:
            cursor.execute("ALTER TABLE papers ADD COLUMN reference_count INTEGER")
            print("Added reference_count column to papers table")

        # Add new columns to citations table
        print("Upgrading citations table...")

        cursor.execute("PRAGMA table_info(citations)")
        existing_columns = [row[1] for row in cursor.fetchall()]

        if "extraction_source" not in existing_columns:
            cursor.execute(
                'ALTER TABLE citations ADD COLUMN extraction_source TEXT DEFAULT "unknown"'
            )
            print("Added extraction_source column to citations table")

        if "confidence_score" not in existing_columns:
            cursor.execute(
                "ALTER TABLE citations ADD COLUMN confidence_score REAL DEFAULT 0.0"
            )
            print("Added confidence_score column to citations table")

        if "page_number" not in existing_columns:
            cursor.execute("ALTER TABLE citations ADD COLUMN page_number INTEGER")
            print("Added page_number column to citations table")

        # Update existing data
        print("Updating existing data...")

        # Convert old external_id to external_ids format
        cursor.execute(
            "SELECT id, external_id FROM papers WHERE external_id IS NOT NULL"
        )
        papers_with_external_id = cursor.fetchall()

        for paper_id, external_id in papers_with_external_id:
            # Try to determine the source of external_id
            external_ids = {}
            if external_id.startswith("arXiv:"):
                external_ids["arxiv"] = external_id
            elif external_id.startswith("PMC"):
                external_ids["pubmed"] = external_id
            else:
                external_ids["other"] = external_id

            cursor.execute(
                "UPDATE papers SET external_ids = ? WHERE id = ?",
                (json.dumps(external_ids), paper_id),
            )

        # Update citation status values
        cursor.execute(
            'UPDATE citations SET status = "pending" WHERE status = "unresolved"'
        )
        cursor.execute(
            'UPDATE citations SET status = "resolved" WHERE status = "resolved"'
        )

        # Set default extraction_source for existing citations
        cursor.execute(
            'UPDATE citations SET extraction_source = "legacy" WHERE extraction_source IS NULL OR extraction_source = ""'
        )

        conn.commit()
        print("Database upgrade completed successfully!")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def downgrade_database(db_path: str = "data/theke.db"):
    """Downgrade database schema (remove new columns)"""

    print("Warning: Downgrade will result in data loss for new columns!")
    confirmation = input("Are you sure you want to proceed? (yes/no): ")

    if confirmation.lower() != "yes":
        print("Downgrade cancelled.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # SQLite doesn't support DROP COLUMN directly, so we need to recreate tables
        print("Downgrading to previous schema...")

        # This is a simplified downgrade - in production, you'd want more careful handling
        # For now, we'll just update the status values back
        cursor.execute(
            'UPDATE citations SET status = "unresolved" WHERE status = "pending"'
        )

        conn.commit()
        print(
            "Basic downgrade completed. Note: New columns are still present but unused."
        )

    except Exception as e:
        print(f"Error during downgrade: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade_database()
    else:
        upgrade_database()
