"""
Tagged Media Resolver
=====================

Interfaces with MediaWatcher tagging system
Allows Michaela to request media by tags dynamically

Supports your actual folder structure:
media/
├── <person-slug>/
│   ├── images/
│   │   ├── nsfw/
│   │   │   └── [nsfw images]
│   │   └── [sfw images]
│   ├── gifs/  (animated webp)
│   │   ├── nsfw/
│   │   │   └── [nsfw gifs]
│   │   └── [sfw gifs]
│   ├── videos/
│   │   ├── nsfw/
│   │   │   └── [nsfw videos]
│   │   └── [sfw videos]
│   └── private/  (Michaela only - all SFW)
│       └── [private collection]
│
└── unknown/
    ├── images/nsfw/<category>/
    ├── gifs/nsfw/<category>/
    └── videos/nsfw/<category>/
"""

from __future__ import annotations

import json
import os
import random
from typing import List, Optional, Dict


class TaggedMediaResolver:
    """
    Find media by tags from your existing MediaWatcher database
    Handles complex nested folder structure
    """
    
    def __init__(self, media_root: str, tags_db_path: str):
        self.media_root = media_root
        self.tags_db_path = tags_db_path
        self.tags_db = {}
        
        # Unknown categories for random sex acts
        self.unknown_categories = [
            "airtight", "anal", "blacked", "blowbang", "blowjob",
            "bukkake", "cuckold", "cum", "cum-face", "cum-swallow",
            "deepthroat", "dp", "frotting", "gangbang", "gloryhole",
            "spitroast"
        ]
        
        self._load_tags_db()
    
    def _load_tags_db(self):
        """
        Load existing tags database
        
        Expected format:
        {
            "media/michaela-miller/images/photo1.webp": {
                "tags": ["casual", "home"],
                "person": "michaela-miller",
                "nsfw": false,
                "type": "images"
            },
            "media/michaela-miller/images/nsfw/photo2.webp": {
                "tags": ["shower", "mirror"],
                "person": "michaela-miller",
                "nsfw": true,
                "type": "images"
            },
            "media/unknown/images/nsfw/blowjob/file1.webp": {
                "tags": ["blowjob"],
                "person": "unknown",
                "nsfw": true,
                "type": "images",
                "category": "blowjob"
            }
        }
        """
        if os.path.exists(self.tags_db_path):
            with open(self.tags_db_path, 'r', encoding='utf-8') as f:
                self.tags_db = json.load(f)
        else:
            # Create empty database
            self.tags_db = {}
            self._save_tags_db()
    
    def _save_tags_db(self):
        """Save tags database"""
        os.makedirs(os.path.dirname(self.tags_db_path), exist_ok=True)
        with open(self.tags_db_path, 'w', encoding='utf-8') as f:
            json.dump(self.tags_db, f, indent=2, ensure_ascii=False)
    
    def _detect_type_and_nsfw(self, filepath: str) -> tuple[str, bool]:
        """
        Detect media type and NSFW status from filepath structure
        
        Returns: (type, nsfw)
        type: "images", "gifs", "videos", or "private"
        nsfw: True if in nsfw/ subfolder
        """
        
        parts = filepath.split('/')
        
        # Check if nsfw
        nsfw = 'nsfw' in parts
        
        # Detect type
        if 'images' in parts:
            media_type = 'images'
        elif 'gifs' in parts:
            media_type = 'gifs'
        elif 'videos' in parts:
            media_type = 'videos'
        elif 'private' in parts:
            media_type = 'private'
        else:
            # Fallback to extension
            ext = os.path.splitext(filepath)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                media_type = 'images'
            elif ext in ['.mp4', '.webm', '.mov']:
                media_type = 'videos'
            else:
                media_type = 'unknown'
        
        return media_type, nsfw
    
    def find_media_by_tags(
        self,
        person_slug: str,
        required_tags: List[str] = None,
        any_tags: List[str] = None,
        exclude_tags: List[str] = None,
        nsfw: bool = None,
        media_type: str = None,
        prefer_private: bool = False
    ) -> Optional[str]:
        """
        Find media matching tag criteria
        
        Args:
            person_slug: Person to find media for
            required_tags: Must have ALL of these tags
            any_tags: Must have AT LEAST ONE of these tags
            exclude_tags: Must NOT have any of these tags
            nsfw: Filter by NSFW status (None = any)
            media_type: Filter by type: 'images', 'gifs', 'videos', 'private'
            prefer_private: For Michaela, prefer private/ folder
        
        Examples:
        - find_media_by_tags("michaela-miller", required_tags=["shower"])
        - find_media_by_tags("michaela-miller", any_tags=["ass", "booty"])
        - find_media_by_tags("michaela-miller", required_tags=["bed"], nsfw=True)
        - find_media_by_tags("michaela-miller", prefer_private=True)  # Michaela's private collection
        """
        
        candidates = []
        
        for filepath, metadata in self.tags_db.items():
            # Check person
            if metadata.get('person') != person_slug:
                continue
            
            # Check NSFW
            if nsfw is not None and metadata.get('nsfw') != nsfw:
                continue
            
            # Check media type
            if media_type:
                if metadata.get('type') != media_type:
                    continue
            
            # For Michaela, prefer private folder if requested
            if prefer_private and person_slug == "michaela-miller":
                if metadata.get('type') != 'private':
                    continue
            
            file_tags = set(metadata.get('tags', []))
            
            # Check required tags (must have ALL)
            if required_tags:
                if not all(tag in file_tags for tag in required_tags):
                    continue
            
            # Check any tags (must have AT LEAST ONE)
            if any_tags:
                if not any(tag in file_tags for tag in any_tags):
                    continue
            
            # Check exclude tags (must have NONE)
            if exclude_tags:
                if any(tag in file_tags for tag in exclude_tags):
                    continue
            
            candidates.append(filepath)
        
        if not candidates:
            return None
        
        # Weighted random selection (prefer files with more tag matches)
        if required_tags or any_tags:
            query_tags = set(required_tags or []) | set(any_tags or [])
            
            weighted = []
            for filepath in candidates:
                file_tags = set(self.tags_db[filepath].get('tags', []))
                match_count = len(query_tags & file_tags)
                
                # Bonus weight for private folder if prefer_private
                if prefer_private and self.tags_db[filepath].get('type') == 'private':
                    match_count += 10
                
                weighted.append((filepath, match_count))
            
            # Sort by match count
            weighted.sort(key=lambda x: x[1], reverse=True)
            
            # Pick from top matches
            top_matches = [f for f, _ in weighted[:5]]
            return random.choice(top_matches)
        else:
            # No tags specified - prefer private if requested
            if prefer_private:
                private_files = [f for f in candidates if self.tags_db[f].get('type') == 'private']
                if private_files:
                    return random.choice(private_files)
            
            return random.choice(candidates)
    
    def get_available_tags_for_person(self, person_slug: str) -> List[str]:
        """Get all tags available for a person"""
        
        tags = set()
        for filepath, metadata in self.tags_db.items():
            if metadata.get('person') == person_slug:
                tags.update(metadata.get('tags', []))
        
        return sorted(list(tags))
    
    def add_media_tags(
        self,
        filepath: str,
        person: str,
        tags: List[str],
        category: str = None
    ):
        """
        Add media to tags database
        
        Args:
            filepath: Full path like "media/michaela-miller/images/nsfw/file.webp"
            person: Person slug or "unknown"
            tags: List of tags
            category: For unknown media, the category (blowjob, anal, etc.)
        
        Auto-detects:
            - Media type (images/gifs/videos/private) from path
            - NSFW status from path (is it in nsfw/ folder?)
        
        Examples:
            # SFW image
            add_media_tags(
                "media/michaela-miller/images/casual1.webp",
                person="michaela-miller",
                tags=["casual", "home"]
            )
            
            # NSFW image
            add_media_tags(
                "media/michaela-miller/images/nsfw/shower1.webp",
                person="michaela-miller",
                tags=["shower", "mirror", "wet"]
            )
            
            # Private folder (Michaela only)
            add_media_tags(
                "media/michaela-miller/private/special1.webp",
                person="michaela-miller",
                tags=["intimate", "close"]
            )
            
            # Unknown category
            add_media_tags(
                "media/unknown/images/nsfw/blowjob/file1.webp",
                person="unknown",
                tags=["blowjob", "pov"],
                category="blowjob"
            )
        """
        
        # Auto-detect type and nsfw from filepath
        media_type, nsfw = self._detect_type_and_nsfw(filepath)
        
        # Build metadata
        metadata = {
            'person': person,
            'tags': tags,
            'nsfw': nsfw,
            'type': media_type
        }
        
        # Add category for unknown media
        if person == "unknown" and category:
            metadata['category'] = category
        
        self.tags_db[filepath] = metadata
        self._save_tags_db()
    
    def batch_add_folder(
        self,
        folder_path: str,
        person: str,
        default_tags: List[str],
        category: str = None
    ):
        """
        Add all files in a folder to tags database with default tags
        
        Useful for bulk tagging a directory
        
        Example:
            # Tag all Michaela's private photos
            batch_add_folder(
                "media/michaela-miller/private",
                person="michaela-miller",
                default_tags=["private", "intimate"]
            )
            
            # Tag all blowjob unknown media
            batch_add_folder(
                "media/unknown/images/nsfw/blowjob",
                person="unknown",
                default_tags=["blowjob"],
                category="blowjob"
            )
        """
        
        if not os.path.exists(folder_path):
            print(f"❌ Folder not found: {folder_path}")
            return
        
        count = 0
        for filename in os.listdir(folder_path):
            if filename.endswith(('.webp', '.jpg', '.jpeg', '.png', '.mp4', '.gif')):
                filepath = os.path.join(folder_path, filename)
                self.add_media_tags(
                    filepath=filepath,
                    person=person,
                    tags=default_tags.copy(),
                    category=category
                )
                count += 1
        
        print(f"✅ Tagged {count} files in {folder_path}")
    
    def persona_media(
        self,
        persona_slug: str,
        tags: List[str] = None,
        nsfw: bool = False,
        prefer_private: bool = False
    ) -> Optional[str]:
        """
        Convenience method - find media for a persona
        
        For Michaela, use prefer_private=True to pull from private/ folder
        """
        
        return self.find_media_by_tags(
            person_slug=persona_slug,
            any_tags=tags,
            nsfw=nsfw,
            prefer_private=prefer_private
        )
    
    def unknown_media(self, category: str) -> Optional[str]:
        """
        Find media from 'unknown' person by category
        
        Categories:
        - airtight, anal, blacked, blowbang, blowjob
        - bukkake, cuckold, cum, cum-face, cum-swallow
        - deepthroat, dp, frotting, gangbang, gloryhole, spitroast
        """
        
        return self.find_media_by_tags(
            person_slug="unknown",
            any_tags=[category],
            nsfw=True
        )
    
    def michaela_private(self, tags: List[str] = None) -> Optional[str]:
        """
        Special method for Michaela's private folder
        Always SFW, won't pull from main media pool
        """
        
        return self.find_media_by_tags(
            person_slug="michaela-miller",
            any_tags=tags,
            nsfw=False,
            prefer_private=True
        )
    
    def get_media_stats(self, person_slug: str) -> Dict[str, int]:
        """
        Get stats about media for a person
        
        Returns counts by type and NSFW status
        """
        
        stats = {
            'total': 0,
            'images_sfw': 0,
            'images_nsfw': 0,
            'gifs_sfw': 0,
            'gifs_nsfw': 0,
            'videos_sfw': 0,
            'videos_nsfw': 0,
            'private': 0
        }
        
        for filepath, metadata in self.tags_db.items():
            if metadata.get('person') != person_slug:
                continue
            
            stats['total'] += 1
            
            media_type = metadata.get('type', 'unknown')
            nsfw = metadata.get('nsfw', False)
            
            if media_type == 'private':
                stats['private'] += 1
            elif media_type == 'images':
                if nsfw:
                    stats['images_nsfw'] += 1
                else:
                    stats['images_sfw'] += 1
            elif media_type == 'gifs':
                if nsfw:
                    stats['gifs_nsfw'] += 1
                else:
                    stats['gifs_sfw'] += 1
            elif media_type == 'videos':
                if nsfw:
                    stats['videos_nsfw'] += 1
                else:
                    stats['videos_sfw'] += 1
        
        return stats
