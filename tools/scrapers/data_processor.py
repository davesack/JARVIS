#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS Arena - External Data Processor (FINAL VERSION)
Processes external rankings into discovery scores & ghost voting weights

Input:  data/arena/external_data_combined.json
Output: data/arena/external_signals.db
        data/arena/discovery_candidates.json

Usage:
    python data_processor_FINAL.py
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass
import statistics
import sys
import io

# Force UTF-8 encoding for stdout/stderr on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import arena_config


@dataclass
class ExternalSignal:
    """External signal for a celebrity"""
    name: str
    
    # CelebBattles
    cb_rank: int = None
    cb_rating: int = None
    cb_win_pct: float = None
    cb_battles: int = None
    
    # CelebEconomy
    ce_tier: str = None
    ce_trend: str = None
    ce_market_cap: str = None
    
    # BattleLeague
    bl_tier: str = None
    bl_win_pct: float = None
    bl_seasons: int = None
    
    # Babepedia
    bp_top100_rank: int = None
    bp_top100_rating: float = None
    bp_most_viewed_rank: int = None
    bp_instagram_rank: int = None
    
    # Computed scores (0-100)
    competitive_score: float = 0.0
    momentum_score: float = 0.0
    resume_score: float = 0.0
    appeal_score: float = 0.0
    discovery_score: float = 0.0
    
    source_count: int = 0
    last_updated: str = ""


class ExternalDataProcessor:
    """Process external rankings into signals"""
    
    def __init__(self):
        self.data_dir = Path(arena_config.DATA_DIR)
        self.db_path = self.data_dir / "external_signals.db"
        self._init_database()
        
        self.discovery_weights = {
            'competitive': 0.30,
            'momentum': 0.25,
            'resume': 0.25,
            'appeal': 0.20
        }
    
    def _init_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS external_signals (
                    name TEXT PRIMARY KEY,
                    cb_rank INTEGER, cb_rating INTEGER, cb_win_pct REAL, cb_battles INTEGER,
                    ce_tier TEXT, ce_trend TEXT, ce_market_cap TEXT,
                    bl_tier TEXT, bl_win_pct REAL, bl_seasons INTEGER,
                    bp_top100_rank INTEGER, bp_top100_rating REAL, bp_most_viewed_rank INTEGER, bp_instagram_rank INTEGER,
                    competitive_score REAL, momentum_score REAL, resume_score REAL, appeal_score REAL, discovery_score REAL,
                    source_count INTEGER, last_updated TEXT
                )
            """)
            conn.commit()
    
    def process_all(self) -> Dict[str, ExternalSignal]:
        """Process all external data"""
        print("=" * 80)
        print("ðŸ”„ PROCESSING EXTERNAL DATA")
        print("=" * 80)
        
        # Load combined data
        data_file = self.data_dir / 'external_data_combined.json'
        if not data_file.exists():
            print(f"âŒ {data_file} not found. Run external_scraper_FINAL.py first!")
            return {}
        
        with open(data_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        signals = {}
        
        # Process each source
        signals = self._process_celebbattles(raw_data.get('celebbattles', {}), signals)
        signals = self._process_celeb_economy(raw_data.get('celeb_economy', {}), signals)
        signals = self._process_battle_league(raw_data.get('battle_league', {}), signals)
        signals = self._process_babepedia(raw_data.get('babepedia', {}), signals)
        
        # Calculate scores
        for signal in signals.values():
            signal.competitive_score = self._calc_competitive(signal)
            signal.momentum_score = self._calc_momentum(signal)
            signal.resume_score = self._calc_resume(signal)
            signal.appeal_score = self._calc_appeal(signal)
            signal.discovery_score = self._calc_discovery(signal)
            signal.last_updated = datetime.now().isoformat()
        
        # Save to DB
        self._save_signals(signals)
        
        # Find discovery candidates
        candidates = self._identify_candidates(signals)
        
        print(f"\nâœ… Processed {len(signals)} unique names")
        print(f"ðŸ” Found {len(candidates)} discovery candidates")
        
        return signals
    
    def _process_celebbattles(self, data: Dict, signals: Dict) -> Dict:
        """Process CelebBattles - handles multiple data formats"""
        if 'error' in data or not data.get('rankings'):
            return signals
        
        rankings = data['rankings']
        
        # Handle different possible formats from the API
        for i, entry in enumerate(rankings):
            name = None
            
            # Format 1: Entry is a dict with 'name' key
            if isinstance(entry, dict):
                name = entry.get('name')
                if name and name not in signals:
                    signals[name] = ExternalSignal(name=name)
                if name:
                    signals[name].cb_rank = entry.get('rank', i + 1)
                    signals[name].cb_rating = entry.get('rating')
                    signals[name].cb_win_pct = entry.get('win_pct')
                    signals[name].cb_battles = entry.get('battles')
                    signals[name].source_count += 1
            
            # Format 2: Entry is just a string (the name)
            elif isinstance(entry, str):
                name = entry
                if name not in signals:
                    signals[name] = ExternalSignal(name=name)
                signals[name].cb_rank = i + 1  # Use position as rank
                signals[name].source_count += 1
            
            else:
                print(f"  ⚠️  Unknown entry format: {type(entry)}")
                continue
        
        print(f"  ✅ CelebBattles: {len(rankings)} entries")
        return signals
    def _process_celeb_economy(self, data: Dict, signals: Dict) -> Dict:
        """Process CelebEconomy"""
        if 'error' in data or not data.get('raw_data'):
            return signals
        
        for entry in data['raw_data']:
            name = entry.get('name')
            if not name:
                continue
            
            if name not in signals:
                signals[name] = ExternalSignal(name=name)
            
            signals[name].ce_tier = entry.get('tier')
            signals[name].ce_trend = entry.get('trend')
            signals[name].ce_market_cap = entry.get('market_cap')
            signals[name].source_count += 1
        
        print(f"  âœ… CelebEconomy: {len(data['raw_data'])} entries")
        return signals
    
    def _process_battle_league(self, data: Dict, signals: Dict) -> Dict:
        """Process BattleLeague"""
        if 'error' in data or not data.get('raw_data'):
            return signals
        
        for entry in data['raw_data']:
            name = entry.get('name')
            if not name:
                continue
            
            if name not in signals:
                signals[name] = ExternalSignal(name=name)
            
            signals[name].bl_tier = entry.get('tier')
            signals[name].bl_win_pct = entry.get('win_pct')
            signals[name].bl_seasons = entry.get('seasons')
            signals[name].source_count += 1
        
        print(f"  âœ… BattleLeague: {len(data['raw_data'])} entries")
        return signals
    
    def _process_babepedia(self, data: Dict, signals: Dict) -> Dict:
        """Process Babepedia"""
        if 'error' in data:
            return signals
        
        # Top 100
        for entry in data.get('top_100', []):
            name = entry.get('name')
            if not name:
                continue
            
            if name not in signals:
                signals[name] = ExternalSignal(name=name)
            
            signals[name].bp_top100_rank = entry.get('rank')
            signals[name].bp_top100_rating = entry.get('rating')
            signals[name].source_count += 1
        
        # Most Viewed
        for entry in data.get('most_viewed', []):
            name = entry.get('name')
            if not name:
                continue
            
            if name not in signals:
                signals[name] = ExternalSignal(name=name)
            
            signals[name].bp_most_viewed_rank = entry.get('rank')
            if signals[name].bp_top100_rank is None:
                signals[name].source_count += 1
        
        # Instagram
        for entry in data.get('instagram_top', []):
            name = entry.get('name')
            if not name:
                continue
            
            if name not in signals:
                signals[name] = ExternalSignal(name=name)
            
            signals[name].bp_instagram_rank = entry.get('rank')
            if signals[name].bp_top100_rank is None and signals[name].bp_most_viewed_rank is None:
                signals[name].source_count += 1
        
        total = len(data.get('top_100', [])) + len(data.get('most_viewed', [])) + len(data.get('instagram_top', []))
        print(f"  âœ… Babepedia: {total} total entries")
        return signals
    
    def _calc_competitive(self, s: ExternalSignal) -> float:
        """Calculate competitive score (0-100)"""
        score = 0.0
        if s.cb_rank:
            if s.cb_rank <= 5:
                score += 50
            elif s.cb_rank <= 20:
                score += 45 - (s.cb_rank - 5) * 1.5
            elif s.cb_rank <= 50:
                score += 30 - (s.cb_rank - 20) * 0.5
            else:
                score += max(0, 15 - (s.cb_rank - 50) * 0.1)
        
        if s.cb_win_pct:
            score += min(25, s.cb_win_pct / 4)
        
        if s.cb_battles and s.cb_battles >= 50:
            score += min(15, s.cb_battles / 10)
        
        return min(100, score)
    
    def _calc_momentum(self, s: ExternalSignal) -> float:
        """Calculate momentum score (0-100)"""
        tier_scores = {'A': 85, 'B': 65, 'C': 45, 'D': 25}
        score = tier_scores.get(s.ce_tier, 0)
        
        if s.ce_trend == 'ðŸ“ˆ':
            score += 15
        elif s.ce_trend == 'ðŸ“‰':
            score -= 10
        
        return max(0, min(100, score))
    
    def _calc_resume(self, s: ExternalSignal) -> float:
        """Calculate resume score (0-100)"""
        tier_scores = {'Premier': 60, 'Championship': 45, 'League One': 30, 'League Two': 15}
        score = tier_scores.get(s.bl_tier, 0)
        
        if s.bl_win_pct:
            score += min(25, s.bl_win_pct / 4)
        
        return min(100, score)
    
    def _calc_appeal(self, s: ExternalSignal) -> float:
        """Calculate appeal score (0-100)"""
        score = 0.0
        
        if s.bp_top100_rank:
            if s.bp_top100_rank <= 10:
                score += 40
            elif s.bp_top100_rank <= 25:
                score += 35 - (s.bp_top100_rank - 10) * 0.3
            elif s.bp_top100_rank <= 50:
                score += 25 - (s.bp_top100_rank - 25) * 0.2
        
        if s.bp_top100_rating:
            score += (s.bp_top100_rating / 10.0) * 30
        
        if s.bp_most_viewed_rank and s.bp_most_viewed_rank <= 50:
            score += 20 - (s.bp_most_viewed_rank * 0.3)
        
        return min(100, score)
    
    def _calc_discovery(self, s: ExternalSignal) -> float:
        """Calculate discovery score"""
        score = (
            s.competitive_score * self.discovery_weights['competitive'] +
            s.momentum_score * self.discovery_weights['momentum'] +
            s.resume_score * self.discovery_weights['resume'] +
            s.appeal_score * self.discovery_weights['appeal']
        )
        
        if s.source_count >= 3:
            score *= 1.10
        elif s.source_count >= 2:
            score *= 1.05
        
        return min(100, score)
    
    def _save_signals(self, signals: Dict):
        """Save to database"""
        with sqlite3.connect(self.db_path) as conn:
            for s in signals.values():
                conn.execute("""
                    INSERT OR REPLACE INTO external_signals VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    s.name, s.cb_rank, s.cb_rating, s.cb_win_pct, s.cb_battles,
                    s.ce_tier, s.ce_trend, s.ce_market_cap, s.bl_tier, s.bl_win_pct, s.bl_seasons,
                    s.bp_top100_rank, s.bp_top100_rating, s.bp_most_viewed_rank, s.bp_instagram_rank,
                    s.competitive_score, s.momentum_score, s.resume_score, s.appeal_score,
                    s.discovery_score, s.source_count, s.last_updated
                ))
            conn.commit()
    
    def _identify_candidates(self, signals: Dict) -> List[Tuple[str, float]]:
        """Identify discovery candidates"""
        candidates = []
        
        for name, signal in signals.items():
            if signal.source_count >= 2 and signal.discovery_score >= 50:
                candidates.append((name, signal.discovery_score))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Save
        output = {
            'candidates': [{'name': n, 'score': s} for n, s in candidates],
            'generated_at': datetime.now().isoformat()
        }
        
        with open(self.data_dir / 'discovery_candidates.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        
        return candidates


if __name__ == "__main__":
    processor = ExternalDataProcessor()
    signals = processor.process_all()
    
    # Show top 10
    if signals:
        top = sorted(signals.items(), key=lambda x: x[1].discovery_score, reverse=True)[:10]
        print("\nðŸ” TOP 10 DISCOVERIES:")
        print("=" * 80)
        for name, s in top:
            print(f"{name:30} Score: {s.discovery_score:5.1f} | C:{s.competitive_score:4.0f} M:{s.momentum_score:4.0f} R:{s.resume_score:4.0f} A:{s.appeal_score:4.0f}")
