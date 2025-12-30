"""
Plex Integration for JARVIS
============================

Connects to Plex Media Server and retrieves direct stream URLs
for videos to send in Discord without file size limits.

CRITICAL SECURITY:
- Only use in PRIVATE channels (Michaela's channel)
- NEVER post Plex content to public channels
- These are adult videos from Dave's private server
"""

import requests
from typing import Optional, List, Dict
import random


class PlexIntegration:
    """
    Handles all Plex Media Server interactions
    
    Features:
    - Get direct stream URLs
    - Query library for videos
    - Map celebrities to Plex media
    - Random video selection
    """
    
    def __init__(
        self,
        server_url: str = "http://192.168.1.156:32400",
        auth_token: str = "NTRxH9s1EyPBPF2UFqej"
    ):
        self.server_url = server_url.rstrip('/')
        self.auth_token = auth_token
        self.headers = {
            'X-Plex-Token': self.auth_token,
            'Accept': 'application/json'
        }
        
        print(f"[PLEX] Initialized: {self.server_url}")
    
    def test_connection(self) -> bool:
        """Test if we can connect to Plex"""
        try:
            url = f"{self.server_url}/identity"
            response = requests.get(url, headers=self.headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"[PLEX] Connected to: {data.get('MediaContainer', {}).get('friendlyName', 'Unknown')}")
                return True
            else:
                print(f"[PLEX] Connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[PLEX] Connection error: {e}")
            return False
    
    def get_libraries(self) -> List[Dict]:
        """Get all Plex libraries"""
        try:
            url = f"{self.server_url}/library/sections"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                libraries = data.get('MediaContainer', {}).get('Directory', [])
                return [
                    {
                        'key': lib.get('key'),
                        'title': lib.get('title'),
                        'type': lib.get('type')
                    }
                    for lib in libraries
                ]
            return []
            
        except Exception as e:
            print(f"[PLEX] Error getting libraries: {e}")
            return []
    
    def get_media_info(self, rating_key: int) -> Optional[Dict]:
        """
        Get detailed info about a specific media item
        
        Args:
            rating_key: The Plex rating key (media ID)
            
        Returns:
            Dict with media info or None
        """
        try:
            url = f"{self.server_url}/library/metadata/{rating_key}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('MediaContainer', {}).get('Metadata', [])
                
                if items:
                    item = items[0]
                    return {
                        'rating_key': item.get('ratingKey'),
                        'title': item.get('title'),
                        'duration': item.get('duration', 0) // 1000,  # Convert to seconds
                        'year': item.get('year'),
                        'thumb': item.get('thumb'),
                        'key': item.get('key')
                    }
            
            return None
            
        except Exception as e:
            print(f"[PLEX] Error getting media info: {e}")
            return None
    
    def get_stream_url(
        self,
        rating_key: int,
        quality: str = "720p"
    ) -> Optional[str]:
        """
        Get direct stream URL for a video
        
        Args:
            rating_key: The Plex rating key (media ID)
            quality: Desired quality (720p, 1080p, etc)
            
        Returns:
            Direct stream URL or None
        """
        try:
            # Get media info first
            media_info = self.get_media_info(rating_key)
            
            if not media_info:
                print(f"[PLEX] Media not found: {rating_key}")
                return None
            
            # Build stream URL
            # Plex uses /video/:/transcode/universal/start.m3u8 for streaming
            stream_url = (
                f"{self.server_url}/video/:/transcode/universal/start.m3u8"
                f"?path=/library/metadata/{rating_key}"
                f"&mediaIndex=0"
                f"&partIndex=0"
                f"&protocol=hls"
                f"&videoQuality=100"
                f"&X-Plex-Token={self.auth_token}"
            )
            
            return stream_url
            
        except Exception as e:
            print(f"[PLEX] Error getting stream URL: {e}")
            return None
    
    def get_direct_play_url(self, rating_key: int) -> Optional[str]:
        """
        Get direct play URL (not transcoded)
        Better for Discord since it's a direct file
        
        Args:
            rating_key: The Plex rating key
            
        Returns:
            Direct play URL or None
        """
        try:
            # Get media info
            url = f"{self.server_url}/library/metadata/{rating_key}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('MediaContainer', {}).get('Metadata', [])
                
                if items:
                    item = items[0]
                    media = item.get('Media', [])
                    
                    if media:
                        part = media[0].get('Part', [])
                        
                        if part:
                            file_path = part[0].get('key')
                            
                            if file_path:
                                # Build direct play URL
                                direct_url = (
                                    f"{self.server_url}{file_path}"
                                    f"?X-Plex-Token={self.auth_token}"
                                )
                                
                                return direct_url
            
            return None
            
        except Exception as e:
            print(f"[PLEX] Error getting direct play URL: {e}")
            return None
    
    def get_plex_web_url(self, rating_key: int) -> Optional[str]:
        """
        Get Plex web interface URL (fallback option)
        
        Args:
            rating_key: The Plex rating key
            
        Returns:
            Plex web URL or None
        """
        try:
            # Get server ID
            url = f"{self.server_url}/identity"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                machine_id = data.get('MediaContainer', {}).get('machineIdentifier')
                
                if machine_id:
                    web_url = (
                        f"{self.server_url}/web/index.html#!/server/{machine_id}"
                        f"/details?key=%2Flibrary%2Fmetadata%2F{rating_key}"
                    )
                    return web_url
            
            return None
            
        except Exception as e:
            print(f"[PLEX] Error getting web URL: {e}")
            return None
    
    def search_library(
        self,
        library_key: int,
        query: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search a library for videos
        
        Args:
            library_key: Library section key
            query: Search term (optional)
            limit: Max results
            
        Returns:
            List of video metadata
        """
        try:
            url = f"{self.server_url}/library/sections/{library_key}/all"
            
            params = {
                'type': 1,  # 1 = movies, 4 = episodes
                'limit': limit
            }
            
            if query:
                params['title'] = query
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('MediaContainer', {}).get('Metadata', [])
                
                return [
                    {
                        'rating_key': item.get('ratingKey'),
                        'title': item.get('title'),
                        'year': item.get('year'),
                        'duration': item.get('duration', 0) // 1000
                    }
                    for item in items
                ]
            
            return []
            
        except Exception as e:
            print(f"[PLEX] Error searching library: {e}")
            return []


class PlexMediaMapper:
    """
    Maps celebrities to their Plex media
    
    Stores which Plex rating keys belong to which celebrities
    """
    
    def __init__(self, mapping_file: str = "data/michaela/plex_media_map.json"):
        self.mapping_file = mapping_file
        self.media_map: Dict[str, Dict] = {}
        self._load()
    
    def _load(self):
        """Load media mapping from file"""
        import json
        import os
        
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    self.media_map = json.load(f)
                print(f"[PLEX_MAP] Loaded mappings for {len(self.media_map)} celebrities")
            except Exception as e:
                print(f"[PLEX_MAP] Error loading: {e}")
    
    def save(self):
        """Save media mapping to file"""
        import json
        import os
        
        os.makedirs(os.path.dirname(self.mapping_file), exist_ok=True)
        
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.media_map, f, indent=2)
            print(f"[PLEX_MAP] Saved mappings")
        except Exception as e:
            print(f"[PLEX_MAP] Error saving: {e}")
    
    def add_video(
        self,
        celebrity_slug: str,
        rating_key: int,
        nsfw: bool = True,
        tags: List[str] = None
    ):
        """Add a video to a celebrity's collection"""
        
        if celebrity_slug not in self.media_map:
            self.media_map[celebrity_slug] = {
                'nsfw_videos': [],
                'sfw_videos': [],
                'tagged_videos': {}
            }
        
        # Add to appropriate list
        if nsfw:
            if rating_key not in self.media_map[celebrity_slug]['nsfw_videos']:
                self.media_map[celebrity_slug]['nsfw_videos'].append(rating_key)
        else:
            if rating_key not in self.media_map[celebrity_slug]['sfw_videos']:
                self.media_map[celebrity_slug]['sfw_videos'].append(rating_key)
        
        # Add tags if provided
        if tags:
            for tag in tags:
                if tag not in self.media_map[celebrity_slug]['tagged_videos']:
                    self.media_map[celebrity_slug]['tagged_videos'][tag] = []
                
                if rating_key not in self.media_map[celebrity_slug]['tagged_videos'][tag]:
                    self.media_map[celebrity_slug]['tagged_videos'][tag].append(rating_key)
        
        self.save()
    
    def get_random_video(
        self,
        celebrity_slug: str,
        nsfw: bool = True,
        tag: str = None
    ) -> Optional[int]:
        """Get random video for a celebrity"""
        
        if celebrity_slug not in self.media_map:
            return None
        
        celeb_data = self.media_map[celebrity_slug]
        
        # Get from specific tag
        if tag and tag in celeb_data['tagged_videos']:
            videos = celeb_data['tagged_videos'][tag]
            return random.choice(videos) if videos else None
        
        # Get from NSFW or SFW
        videos = celeb_data['nsfw_videos'] if nsfw else celeb_data['sfw_videos']
        return random.choice(videos) if videos else None
    
    def get_video_count(self, celebrity_slug: str, nsfw: bool = True) -> int:
        """Get count of videos for a celebrity"""
        
        if celebrity_slug not in self.media_map:
            return 0
        
        videos = self.media_map[celebrity_slug]['nsfw_videos'] if nsfw else self.media_map[celebrity_slug]['sfw_videos']
        return len(videos)
    
    def has_videos(self, celebrity_slug: str) -> bool:
        """Check if celebrity has any videos"""
        
        if celebrity_slug not in self.media_map:
            return False
        
        celeb_data = self.media_map[celebrity_slug]
        total = len(celeb_data['nsfw_videos']) + len(celeb_data['sfw_videos'])
        return total > 0


# Example usage
if __name__ == "__main__":
    # Test connection
    plex = PlexIntegration()
    
    if plex.test_connection():
        print("\n✅ Plex connection successful!")
        
        # Get libraries
        libraries = plex.get_libraries()
        print(f"\n📚 Found {len(libraries)} libraries:")
        for lib in libraries:
            print(f"  - {lib['title']} (key: {lib['key']}, type: {lib['type']})")
        
        # Test getting a stream URL (use a known rating key)
        # stream_url = plex.get_direct_play_url(111992)
        # if stream_url:
        #     print(f"\n🎬 Stream URL: {stream_url}")
    else:
        print("\n❌ Failed to connect to Plex")
