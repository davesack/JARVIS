"""
Sleep Tracker
=============

Track sleep quality and correlate with mood/energy
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

UTC = timezone.utc


class SleepTracker:
    """
    Track sleep quality and detect trends
    """
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.sleep_log = []
        self._load()
    
    def log_sleep(
        self,
        quality: str,
        duration_hours: float = None,
        notes: str = None
    ):
        """
        Log sleep quality
        quality: 'terrible', 'poor', 'okay', 'good', 'great'
        """
        
        self.sleep_log.append({
            'date': datetime.now(UTC).date().isoformat(),
            'quality': quality,
            'duration_hours': duration_hours,
            'notes': notes,
            'timestamp': datetime.now(UTC).isoformat()
        })
        
        self._save()
    
    def get_recent_average(self, days: int = 7) -> dict:
        """Get average sleep quality over recent days"""
        
        recent = self.sleep_log[-days:]
        
        if not recent:
            return {'average': None, 'trend': 'unknown'}
        
        quality_map = {
            'terrible': 1,
            'poor': 2,
            'okay': 3,
            'good': 4,
            'great': 5
        }
        
        avg = sum(quality_map.get(s['quality'], 3) for s in recent) / len(recent)
        
        # Determine trend
        if len(recent) >= 3:
            first_half = recent[:len(recent)//2]
            second_half = recent[len(recent)//2:]
            
            first_avg = sum(quality_map.get(s['quality'], 3) for s in first_half) / len(first_half)
            second_avg = sum(quality_map.get(s['quality'], 3) for s in second_half) / len(second_half)
            
            if second_avg > first_avg + 0.5:
                trend = 'improving'
            elif second_avg < first_avg - 0.5:
                trend = 'worsening'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'average': avg,
            'trend': trend,
            'recent_entries': len(recent)
        }
    
    def get_sleep_context(self) -> str:
        """Get summary for Michaela's context"""
        
        if not self.sleep_log:
            return ""
        
        recent = self.get_recent_average(days=7)
        
        if recent['average'] is None:
            return ""
        
        quality_desc = {
            1: "very poor",
            2: "poor",
            3: "moderate",
            4: "good",
            5: "excellent"
        }
        
        avg_rounded = round(recent['average'])
        
        context = f"Sleep quality (7-day average): {quality_desc.get(avg_rounded, 'moderate')}"
        
        if recent['trend'] != 'stable' and recent['trend'] != 'insufficient_data':
            context += f" (trend: {recent['trend']})"
        
        # Check last night specifically
        if self.sleep_log:
            last_night = self.sleep_log[-1]
            context += f"\nLast night: {last_night['quality']}"
            if last_night.get('notes'):
                context += f" ({last_night['notes'][:50]})"
        
        return context
    
    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.sleep_log = json.load(f)
    
    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(self.sleep_log, f, indent=2)
