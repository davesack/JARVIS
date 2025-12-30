"""
MediaWatcher 4.0 - Slug Resolution Engine

Resolves filenames, handles, and aliases to canonical slugs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from difflib import get_close_matches

from .mediawatcher_core import (
    FileMetadata,
    ResolutionResult,
    sanitize_slug
)

logger = logging.getLogger(__name__)


# ==============================================================================
# SLUG RESOLUTION ENGINE
# ==============================================================================

class SlugResolver:
    """
    Resolves slugs from various sources: filenames, aliases, Bluesky handles.
    
    Uses people.json and aliases.json as the source of truth.
    """
    
    def __init__(self, people_file: Path, aliases_file: Path):
        self.people_file = people_file
        self.aliases_file = aliases_file
        
        self.people: Set[str] = set()
        self.aliases: Dict[str, str] = {}
        
        self._load()
    
    def _load(self):
        """Load people and aliases from JSON files"""
        # Load people
        if self.people_file.exists():
            try:
                with self.people_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                # people.json is {slug: {name, metadata...}}
                self.people = set(data.keys())
                
                logger.info(f"[SlugResolver] Loaded {len(self.people)} people")
            except Exception as e:
                logger.error(f"[SlugResolver] Failed to load people.json: {e}")
                self.people = set()
        else:
            logger.warning(f"[SlugResolver] people.json not found: {self.people_file}")
            self.people = set()
        
        # Load aliases
        if self.aliases_file.exists():
            try:
                with self.aliases_file.open("r", encoding="utf-8") as f:
                    self.aliases = json.load(f)
                
                # Normalize all alias keys to lowercase
                self.aliases = {k.lower(): v for k, v in self.aliases.items()}
                
                logger.info(f"[SlugResolver] Loaded {len(self.aliases)} aliases")
            except Exception as e:
                logger.error(f"[SlugResolver] Failed to load aliases.json: {e}")
                self.aliases = {}
        else:
            logger.warning(f"[SlugResolver] aliases.json not found: {self.aliases_file}")
            self.aliases = {}
    
    def reload(self):
        """Reload people and aliases from disk"""
        self._load()
    
    def resolve(self, metadata: FileMetadata) -> ResolutionResult:
        """
        Resolve metadata to a canonical slug.
        
        Priority order:
        1. Direct slug match (slug in people database)
        2. Alias match (slug or handle in aliases)
        3. Handle match (Bluesky handle in aliases)
        4. Fuzzy match (close matches in people/aliases)
        5. Failed (needs manual intervention)
        
        Returns:
            ResolutionResult with slug and resolution method
        """
        # Try direct slug match
        if metadata.slug and metadata.slug in self.people:
            return ResolutionResult(
                success=True,
                slug=metadata.slug,
                method="direct",
                confidence=1.0
            )
        
        # Try alias match on slug
        if metadata.slug:
            slug_lower = metadata.slug.lower()
            if slug_lower in self.aliases:
                resolved = self.aliases[slug_lower]
                return ResolutionResult(
                    success=True,
                    slug=resolved,
                    method="alias",
                    confidence=1.0
                )
        
        # Try handle match (Bluesky)
        if metadata.handle:
            handle_lower = metadata.handle.lower()
            if handle_lower in self.aliases:
                resolved = self.aliases[handle_lower]
                return ResolutionResult(
                    success=True,
                    slug=resolved,
                    method="handle",
                    confidence=1.0
                )
        
        # Try fuzzy matching
        if metadata.slug:
            suggestions = self._fuzzy_match(metadata.slug)
            if suggestions:
                return ResolutionResult(
                    success=False,
                    slug=None,
                    method="fuzzy",
                    confidence=0.5,
                    suggestions=suggestions
                )
        
        # Failed to resolve
        return ResolutionResult(
            success=False,
            slug=None,
            method="failed",
            confidence=0.0,
            suggestions=[]
        )
    
    def _fuzzy_match(self, query: str, max_results: int = 5) -> List[str]:
        """
        Find close matches in people and aliases.
        
        Returns list of suggested slugs.
        """
        query_lower = query.lower()
        
        # Get close matches from people slugs
        people_matches = get_close_matches(
            query_lower,
            self.people,
            n=max_results,
            cutoff=0.6
        )
        
        # Get close matches from alias keys
        alias_matches = get_close_matches(
            query_lower,
            self.aliases.keys(),
            n=max_results,
            cutoff=0.6
        )
        
        # Combine and deduplicate
        all_matches = list(set(people_matches + [self.aliases[k] for k in alias_matches]))
        
        return all_matches[:max_results]
    
    def add_alias(self, alias: str, slug: str, save: bool = True) -> bool:
        """
        Add a new alias mapping.
        
        Args:
            alias: The alias/handle to map
            slug: The canonical slug to map to
            save: Whether to save to aliases.json immediately
        
        Returns:
            True if successful, False if slug doesn't exist
        """
        # Validate slug exists
        if slug not in self.people:
            logger.error(f"[SlugResolver] Cannot add alias '{alias}' → '{slug}': slug not in people database")
            return False
        
        # Add to memory
        alias_lower = alias.lower()
        self.aliases[alias_lower] = slug
        
        logger.info(f"[SlugResolver] Added alias: '{alias}' → '{slug}'")
        
        # Save to disk
        if save:
            self._save_aliases()
        
        return True
    
    def _save_aliases(self):
        """Save aliases to aliases.json"""
        try:
            with self.aliases_file.open("w", encoding="utf-8") as f:
                json.dump(self.aliases, f, indent=2, ensure_ascii=False)
            logger.info(f"[SlugResolver] Saved {len(self.aliases)} aliases")
        except Exception as e:
            logger.error(f"[SlugResolver] Failed to save aliases.json: {e}")
    
    def get_all_slugs(self) -> List[str]:
        """Get sorted list of all known slugs for autocomplete"""
        return sorted(self.people)
    
    def slug_exists(self, slug: str) -> bool:
        """Check if a slug exists in the people database"""
        return slug in self.people


# ==============================================================================
# GLOBAL RESOLVER INSTANCE
# ==============================================================================

_resolver: Optional[SlugResolver] = None

def get_resolver(people_file: Path, aliases_file: Path) -> SlugResolver:
    """Get or create the global resolver instance"""
    global _resolver
    if _resolver is None:
        _resolver = SlugResolver(people_file, aliases_file)
    return _resolver


def resolve_metadata(metadata: FileMetadata, resolver: SlugResolver) -> ResolutionResult:
    """
    Convenience function to resolve metadata using the resolver.
    
    Args:
        metadata: The file metadata to resolve
        resolver: The SlugResolver instance
    
    Returns:
        ResolutionResult
    """
    return resolver.resolve(metadata)
