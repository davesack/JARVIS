#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS Arena - External Rankings Scraper (FINAL VERSION)
Scrapes 4 ranking sources for ghost voting weights & discovery

Sources:
1. CelebBattles - Competitive rankings
2. CelebEconomy - Market momentum  
3. CelebBattleLeague - Competitive resume
4. Babepedia - Top 100, Most Viewed, Instagram rankings

Usage:
    python external_scraper_FINAL.py
    
Output:
    data/arena/external_data_combined.json
"""

import json
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import time
from bs4 import BeautifulSoup
import re
import sys
import io

# Force UTF-8 encoding for stdout/stderr on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent to path for imports
# Use .resolve() to get absolute path (handles relative __file__ from subprocess)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import arena_config


class ExternalRankingsScraper:
    """Scrape external ranking sources for ghost voting"""
    
    def __init__(self):
        self.data_dir = Path(arena_config.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().isoformat()
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def scrape_celebbattles(self) -> Dict:
        """Scrape CelebBattles rankings"""
        print("ðŸŽ¯ Scraping CelebBattles...")
        try:
            r = requests.get('https://celebbattles.github.io/rankings.json', timeout=10, headers=self.headers)
            r.raise_for_status()
            rankings = r.json()
            print(f"  âœ… Found {len(rankings)} ranked celebs")
            return {'rankings': rankings, 'scraped_at': self.timestamp}
        except Exception as e:
            print(f"  âŒ Error: {e}")
            return {'error': str(e), 'scraped_at': self.timestamp}
    
    def scrape_celeb_economy(self) -> Dict:
        """Scrape CelebEconomy Google Sheet"""
        print("ðŸ’° Scraping CelebEconomy...")
        try:
            url = 'https://docs.google.com/spreadsheets/d/1UXUSGQpki-snq2PLZ18zvhZf_1ByHEshljwVyxEuRPM/export?format=csv&gid=1002695080'
            df = pd.read_csv(url)
            df.columns = df.columns.str.lower().str.strip()
            print(f"  âœ… Found {len(df)} entries")
            return {'raw_data': df.to_dict('records'), 'row_count': len(df), 'scraped_at': self.timestamp}
        except Exception as e:
            print(f"  âŒ Error: {e}")
            return {'error': str(e), 'scraped_at': self.timestamp}
    
    def scrape_battle_league(self) -> Dict:
        """Scrape CelebBattleLeague Google Sheet"""
        print("ðŸ† Scraping CelebBattleLeague...")
        try:
            url = 'https://docs.google.com/spreadsheets/d/1OcPTG6MMm8tTnXUWN6hwy8G7sEvKC2lGC09IzSGOaDk/export?format=csv&gid=0'
            df = pd.read_csv(url)
            df.columns = df.columns.str.lower().str.strip()
            print(f"  âœ… Found {len(df)} entries")
            return {'raw_data': df.to_dict('records'), 'row_count': len(df), 'scraped_at': self.timestamp}
        except Exception as e:
            print(f"  âŒ Error: {e}")
            return {'error': str(e), 'scraped_at': self.timestamp}
    
    def scrape_babepedia_rankings(self) -> Dict:
        """Scrape Babepedia Top 100, Most Viewed, Instagram rankings"""
        print("ðŸ‘‘ Scraping Babepedia...")
        data = {'top_100': [], 'most_viewed': [], 'instagram_top': [], 'scraped_at': self.timestamp}
        
        try:
            print("  ðŸ“Š Fetching Top 100...")
            data['top_100'] = self._scrape_babepedia_list('https://www.babepedia.com/top100')
            time.sleep(2)
            
            print("  ðŸ‘€ Fetching Most Viewed...")
            data['most_viewed'] = self._scrape_babepedia_list('https://www.babepedia.com/mostviewed100')
            time.sleep(2)
            
            print("  ðŸ“¸ Fetching Instagram Top...")
            data['instagram_top'] = self._scrape_babepedia_list('https://www.babepedia.com/instagramtop100followercount')
            
            print(f"  âœ… Total: {len(data['top_100']) + len(data['most_viewed']) + len(data['instagram_top'])} entries")
        except Exception as e:
            print(f"  âŒ Error: {e}")
            data['error'] = str(e)
        
        return data
    
    def _scrape_babepedia_list(self, url: str, limit: int = 100) -> List[Dict]:
        """Scrape a Babepedia ranking list"""
        results = []
        try:
            r = requests.get(url, timeout=15, headers=self.headers)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Find profile cards
            profiles = soup.find_all('div', class_=re.compile(r'(profile|babe|card)'))[:limit]
            
            for i, profile in enumerate(profiles, 1):
                try:
                    name_elem = profile.find(['h2', 'h3', 'a'])
                    if not name_elem:
                        continue
                    
                    name = name_elem.get_text(strip=True)
                    
                    # Extract rank
                    rank_elem = profile.find(text=re.compile(r'#?\d+'))
                    rank = int(re.search(r'\d+', rank_elem).group()) if rank_elem else i
                    
                    # Extract rating
                    rating = None
                    rating_elem = profile.find(text=re.compile(r'\d+\.\d+/10'))
                    if rating_elem:
                        rating_match = re.search(r'(\d+\.\d+)', rating_elem)
                        rating = float(rating_match.group(1)) if rating_match else None
                    
                    results.append({'rank': rank, 'name': name, 'rating': rating})
                except:
                    continue
        except Exception as e:
            print(f"    âŒ Failed: {e}")
        
        return results
    
    def scrape_all(self) -> Dict:
        """Scrape all external ranking sources"""
        print("=" * 80)
        print("ðŸš€ SCRAPING EXTERNAL RANKINGS (FOR GHOST VOTING)")
        print("=" * 80)
        
        results = {
            'celebbattles': self.scrape_celebbattles(),
            'celeb_economy': self.scrape_celeb_economy(),
            'battle_league': self.scrape_battle_league(),
            'babepedia': self.scrape_babepedia_rankings(),
            'scrape_completed_at': datetime.now().isoformat()
        }
        
        # Save
        output_file = self.data_dir / 'external_data_combined.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print("=" * 80)
        print(f"âœ… SCRAPING COMPLETE")
        print(f"ðŸ“ Saved to: {output_file}")
        print("=" * 80)
        
        return results


if __name__ == "__main__":
    scraper = ExternalRankingsScraper()
    scraper.scrape_all()
