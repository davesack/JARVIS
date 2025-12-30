#!/usr/bin/env python3
"""
JARVIS Arena - Metadata Scraper
Scrapes celebrity metadata from Boobpedia
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
from datetime import datetime
import time


class MetadataScraper:
    """Scrape celebrity metadata from Boobpedia"""
    
    def __init__(self, data_dir: str = "data/arena"):
        # User agent to avoid blocks
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        }
        
        # Rate limiting
        self.request_delay = 2
    
    def clean_text(self, text):
        """Remove unicode spaces and extra whitespace."""
        if not text:
            return text
        text = text.replace('\u00a0', ' ')
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def scrape_boobpedia(self, name: str, url: Optional[str] = None) -> Dict:
        """Scrape Boobpedia with correct HTML parsing and data cleaning."""
        print(f"  📚 Scraping Boobpedia for {name}...")
        
        if not url:
            slug = name.title().replace(' ', '_')
            url = f"https://www.boobpedia.com/boobs/{slug}"
            print(f"    🔗 URL: {url}")
        
        try:
            time.sleep(self.request_delay)
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            data = {
                'source': 'boobpedia',
                'url': url,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Get biography
            first_p = soup.find('p')
            if first_p:
                bio_text = self.clean_text(first_p.get_text())
                if len(bio_text) > 50:
                    data['biography'] = bio_text
            
            # Find infobox
            infobox = soup.find('table', {'class': 'infobox'})
            if not infobox:
                print(f"    ⚠️  No infobox found")
                return data
            
            # Parse infobox rows
            rows = infobox.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                
                if len(cells) != 2:
                    continue
                
                label = cells[0].get_text().strip().lower()
                value = self.clean_text(cells[1].get_text())
                
                if not label or not value:
                    continue
                
                # Parse each field
                if 'born' in label:
                    data['born'] = value
                    date_match = re.search(r'(\w+ \d+, \d{4})', value)
                    if date_match:
                        data['birthdate'] = date_match.group(1)
                    paren_match = re.search(r'\)(.+)$', value)
                    if paren_match:
                        place = paren_match.group(1).strip()
                        place = re.sub(r'^\(age\s*\d+\)', '', place).strip()
                        if place:
                            data['birthplace'] = place
                
                elif 'years active' in label or 'active' in label:
                    data['years_active'] = value
                
                elif 'ethnicity' in label:
                    data['ethnicity'] = value
                
                elif 'nationality' in label:
                    data['nationality'] = value
                
                elif 'measurements' in label:
                    inch_match = re.search(r'(\d+-\d+-\d+)in', value)
                    if inch_match:
                        data['measurements'] = inch_match.group(1)
                    else:
                        meas_match = re.search(r'(\d+-\d+-\d+)', value)
                        if meas_match:
                            data['measurements'] = meas_match.group(1)
                    
                    if data.get('measurements'):
                        parts = data['measurements'].split('-')
                        if len(parts) == 3:
                            data['bust'] = parts[0]
                            data['waist'] = parts[1]
                            data['hips'] = parts[2]
                
                elif 'bra' in label or 'cup' in label:
                    bra_match = re.search(r'(\d+[A-Z]+)', value)
                    if bra_match:
                        data['bra_size'] = bra_match.group(1)
                        cup_match = re.search(r'\d+([A-Z]+)', bra_match.group(1))
                        if cup_match:
                            data['cup_size'] = cup_match.group(1)
                
                elif 'boobs' in label:
                    data['boobs'] = value
                
                elif 'height' in label:
                    height_match = re.search(r'(\d+\s*ft\s*\d+\s*in)', value)
                    if height_match:
                        data['height'] = height_match.group(1)
                    ft_in_match = re.search(r'(\d+)\s*ft\s*(\d+)\s*in', value)
                    if ft_in_match:
                        data['height_ft'] = ft_in_match.group(1)
                        data['height_in'] = ft_in_match.group(2)
                    cm_match = re.search(r'(\d+\.?\d*)\s*m\)', value)
                    if cm_match:
                        data['height_cm'] = str(int(float(cm_match.group(1)) * 100))
                
                elif 'weight' in label:
                    lb_match = re.search(r'(\d+\s*lb)', value)
                    if lb_match:
                        data['weight'] = lb_match.group(1)
                        num_match = re.search(r'(\d+)', lb_match.group(1))
                        if num_match:
                            data['weight_lbs'] = num_match.group(1)
                    kg_match = re.search(r'(\d+)\s*kg', value)
                    if kg_match:
                        data['weight_kg'] = kg_match.group(1)
                
                elif 'body type' in label:
                    data['body_type'] = value
                
                elif 'eye color' in label or 'eye' in label:
                    data['eye_color'] = value
                
                elif label == 'hair':
                    data['hair_color'] = value
                
                elif 'shown' in label:
                    data['shown'] = value
                
                elif 'special' in label:
                    data['special'] = value
                
                elif 'also known as' in label:
                    data['aliases'] = value
            
            print(f"    ✅ Boobpedia: Found {len(data) - 3} fields")
            return data
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"    ⚠️  Boobpedia: Not found (404)")
                return {'source': 'boobpedia', 'error': 'not_found'}
            print(f"    ❌ Boobpedia: HTTP {e.response.status_code}")
            return {'source': 'boobpedia', 'error': str(e)}
        except Exception as e:
            print(f"    ❌ Boobpedia Error: {type(e).__name__}: {e}")
            return {'source': 'boobpedia', 'error': str(e)}
