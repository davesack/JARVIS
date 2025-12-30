"""
MediaWatcher 4.0 - Event Logging System

Structured JSON logging for all processing events.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .mediawatcher_core import ProcessResult

logger = logging.getLogger(__name__)


# ==============================================================================
# EVENT LOGGER
# ==============================================================================

class EventLogger:
    """
    Structured event logger for MediaWatcher.
    
    Writes events as JSON lines to a log file for programmatic parsing.
    """
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        Log a single event.
        
        Args:
            event_type: Type of event (process_start, process_complete, error, etc.)
            data: Event data dictionary
        """
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": event_type,
            "data": data
        }
        
        try:
            with self.log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"[EventLogger] Failed to write event: {e}")
    
    def log_process_complete(self, result: ProcessResult):
        """Log completion of file processing"""
        data = {
            "success": result.success,
            "original_file": str(result.original_path),
            "original_filename": result.original_path.name,
            "final_path": str(result.final_path) if result.final_path else None,
            "slug": result.slug,
            "stage_reached": result.stage_reached.value if result.stage_reached else None,
            "error": result.error,
            "size_mb": result.size_mb,
            "quality": result.quality,
            "processing_time_seconds": result.processing_time_seconds,
            "review_folder": result.review_folder,
            "review_reason": result.review_reason
        }
        
        event_type = "process_success" if result.success else "process_error"
        self.log_event(event_type, data)


# ==============================================================================
# GLOBAL LOGGER INSTANCE
# ==============================================================================

_event_logger: Optional[EventLogger] = None

def get_event_logger(log_file: Path) -> EventLogger:
    """Get or create the global event logger"""
    global _event_logger
    if _event_logger is None:
        _event_logger = EventLogger(log_file)
    return _event_logger
