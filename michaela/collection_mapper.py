"""
Collection-Based Bulk Plex Mapping
===================================

Map entire Plex collections to celebrities instead of one-by-one.

Features:
- Map entire collections with one command
- Filter by Plex tags
- Auto-discover all videos in collection
- Support for sub-collections
"""

import requests
from typing import List, Dict, Optional
from plex_integration import PlexIntegration
from plex_friend_integration import PlexMediaMapper


class CollectionMapper:
    """
    Bulk map Plex collections to celebrities
    
    Usage:
    !map_collection "Chloe Lamb" chloe-lamb
    !map_collection "Chloe Lamb - Topless" chloe-lamb topless
    """
    
    def __init__(self):
        self.plex = PlexIntegration()
        self.mapper = PlexMediaMapper()
    
    def get_all_collections(self, library_key: int) -> List[Dict]:
        """
        Get all collections in a library
        
        Args:
            library_key: Library section key
            
        Returns:
            List of collections with their info
        """
        try:
            url = f"{self.plex.server_url}/library/sections/{library_key}/collections"
            response = requests.get(url, headers=self.plex.headers)
            
            if response.status_code == 200:
                data = response.json()
                collections = data.get('MediaContainer', {}).get('Metadata', [])
                
                return [
                    {
                        'rating_key': col.get('ratingKey'),
                        'title': col.get('title'),
                        'item_count': col.get('childCount', 0)
                    }
                    for col in collections
                ]
            
            return []
            
        except Exception as e:
            print(f"[COLLECTION_MAPPER] Error getting collections: {e}")
            return []
    
    def get_collection_items(self, collection_key: int) -> List[int]:
        """
        Get all video rating keys in a collection
        
        Args:
            collection_key: Collection rating key
            
        Returns:
            List of video rating keys
        """
        try:
            url = f"{self.plex.server_url}/library/collections/{collection_key}/children"
            response = requests.get(url, headers=self.plex.headers)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('MediaContainer', {}).get('Metadata', [])
                
                return [item.get('ratingKey') for item in items]
            
            return []
            
        except Exception as e:
            print(f"[COLLECTION_MAPPER] Error getting collection items: {e}")
            return []
    
    def get_video_tags(self, rating_key: int) -> List[str]:
        """
        Get all tags for a video
        
        Args:
            rating_key: Video rating key
            
        Returns:
            List of tag names
        """
        try:
            url = f"{self.plex.server_url}/library/metadata/{rating_key}"
            response = requests.get(url, headers=self.plex.headers)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('MediaContainer', {}).get('Metadata', [])
                
                if items:
                    item = items[0]
                    tags = item.get('Genre', [])  # Plex stores tags as "Genre"
                    return [tag.get('tag', '') for tag in tags]
            
            return []
            
        except Exception as e:
            print(f"[COLLECTION_MAPPER] Error getting video tags: {e}")
            return []
    
    def bulk_map_collection(
        self,
        collection_name: str,
        celebrity_slug: str,
        library_key: int = 1,
        required_tags: List[str] = None,
        nsfw: bool = True
    ) -> Dict:
        """
        Bulk map an entire collection to a celebrity
        
        Args:
            collection_name: Name of Plex collection
            celebrity_slug: Celebrity identifier
            library_key: Library section (default 1)
            required_tags: Only map videos with these tags
            nsfw: Mark as NSFW content
            
        Returns:
            Dict with mapping results
        """
        
        # Find the collection
        collections = self.get_all_collections(library_key)
        
        target_collection = None
        for col in collections:
            if col['title'].lower() == collection_name.lower():
                target_collection = col
                break
        
        if not target_collection:
            return {
                'success': False,
                'error': f"Collection '{collection_name}' not found"
            }
        
        # Get all videos in collection
        video_keys = self.get_collection_items(target_collection['rating_key'])
        
        if not video_keys:
            return {
                'success': False,
                'error': f"No videos found in collection"
            }
        
        # Filter by tags if specified
        if required_tags:
            filtered_keys = []
            
            for key in video_keys:
                video_tags = self.get_video_tags(key)
                
                # Check if video has all required tags
                if all(req_tag.lower() in [t.lower() for t in video_tags] for req_tag in required_tags):
                    filtered_keys.append(key)
            
            video_keys = filtered_keys
        
        if not video_keys:
            return {
                'success': False,
                'error': f"No videos matched tag filter: {required_tags}"
            }
        
        # Map all videos
        mapped_count = 0
        
        for rating_key in video_keys:
            # Get tags for this video
            video_tags = self.get_video_tags(rating_key)
            
            # Add to mapper
            self.mapper.add_video(
                celebrity_slug=celebrity_slug,
                rating_key=rating_key,
                nsfw=nsfw,
                tags=video_tags
            )
            
            mapped_count += 1
        
        return {
            'success': True,
            'collection_name': target_collection['title'],
            'celebrity_slug': celebrity_slug,
            'mapped_count': mapped_count,
            'total_available': len(video_keys),
            'nsfw': nsfw,
            'tags_filter': required_tags
        }
    
    def list_available_collections(self, library_key: int = 1) -> List[Dict]:
        """
        List all collections in library with item counts
        
        Args:
            library_key: Library section
            
        Returns:
            List of collection info
        """
        return self.get_all_collections(library_key)


# Discord commands for collection mapping
class CollectionMappingCommands:
    """
    Discord commands for bulk collection mapping
    """
    
    def __init__(self):
        self.mapper = CollectionMapper()
    
    async def list_collections(self, ctx, library_key: int = 1):
        """
        List all Plex collections
        
        Usage: !list_collections
        Usage: !list_collections 2
        """
        
        collections = self.mapper.list_available_collections(library_key)
        
        if not collections:
            await ctx.send("❌ No collections found")
            return
        
        msg = f"📚 **Plex Collections (Library {library_key}):**\n\n"
        
        for col in collections:
            msg += f"**{col['title']}** - {col['item_count']} videos\n"
        
        # Split if too long
        if len(msg) > 1900:
            msg = msg[:1900] + "\n\n... (truncated)"
        
        await ctx.send(msg)
    
    async def map_collection(
        self,
        ctx,
        collection_name: str,
        celebrity_slug: str,
        tags: str = None,
        nsfw: str = "yes"
    ):
        """
        Bulk map entire collection to celebrity
        
        Usage: 
        !map_collection "Chloe Lamb" chloe-lamb
        !map_collection "Chloe Lamb" chloe-lamb "topless,solo"
        !map_collection "Anna Kendrick SFW" anna-kendrick "" no
        """
        
        # Parse tags
        tag_list = []
        if tags and tags.strip():
            tag_list = [t.strip() for t in tags.split(',')]
        
        # Parse NSFW
        nsfw_bool = nsfw.lower() in ['yes', 'y', 'true', 'nsfw', '1']
        
        await ctx.send(f"⏳ Mapping collection **{collection_name}** to `{celebrity_slug}`...")
        
        # Do the bulk mapping
        result = self.mapper.bulk_map_collection(
            collection_name=collection_name,
            celebrity_slug=celebrity_slug,
            library_key=1,  # Default to library 1
            required_tags=tag_list if tag_list else None,
            nsfw=nsfw_bool
        )
        
        if result['success']:
            msg = f"✅ **Mapped {result['mapped_count']} videos**\n\n"
            msg += f"Collection: {result['collection_name']}\n"
            msg += f"Celebrity: `{result['celebrity_slug']}`\n"
            msg += f"NSFW: {result['nsfw']}\n"
            
            if result['tags_filter']:
                msg += f"Tags filter: {', '.join(result['tags_filter'])}\n"
            
            await ctx.send(msg)
        else:
            await ctx.send(f"❌ {result['error']}")
    
    async def show_collection_tags(self, ctx, collection_name: str):
        """
        Show all unique tags in a collection
        
        Usage: !collection_tags "Chloe Lamb"
        """
        
        # Find collection
        collections = self.mapper.list_available_collections(library_key=1)
        
        target = None
        for col in collections:
            if col['title'].lower() == collection_name.lower():
                target = col
                break
        
        if not target:
            await ctx.send(f"❌ Collection '{collection_name}' not found")
            return
        
        # Get all videos
        video_keys = self.mapper.get_collection_items(target['rating_key'])
        
        # Collect all unique tags
        all_tags = set()
        
        for key in video_keys:
            tags = self.mapper.get_video_tags(key)
            all_tags.update(tags)
        
        if not all_tags:
            await ctx.send(f"❌ No tags found in collection '{collection_name}'")
            return
        
        msg = f"🏷️ **Tags in '{collection_name}':**\n\n"
        msg += ", ".join(sorted(all_tags))
        
        await ctx.send(msg)


# Example usage in Michaela cog:
"""
# Add to __init__:
self.collection_mapper = CollectionMappingCommands()

# Add commands:

@commands.command(name="list_collections")
async def list_collections(self, ctx, library_key: int = 1):
    await self.collection_mapper.list_collections(ctx, library_key)

@commands.command(name="map_collection")
async def map_collection(self, ctx, collection_name: str, celebrity_slug: str, tags: str = None, nsfw: str = "yes"):
    '''
    Map entire Plex collection to celebrity
    
    Usage:
    !map_collection "Chloe Lamb" chloe-lamb
    !map_collection "Chloe Lamb" chloe-lamb "topless,solo"
    !map_collection "Anna SFW" anna-kendrick "" no
    '''
    await self.collection_mapper.map_collection(ctx, collection_name, celebrity_slug, tags, nsfw)

@commands.command(name="collection_tags")
async def show_collection_tags(self, ctx, *, collection_name: str):
    '''Show all tags in a collection'''
    await self.collection_mapper.show_collection_tags(ctx, collection_name)
"""
