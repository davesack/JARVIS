# cogs/media_ingest.py

import discord
from discord import app_commands
from discord.ext import commands
import logging

from utils.mediawatcher.mediawatcher import create_mediawatcher
from config import MEDIA_ROOT, MEDIAWATCHER_DATA, DROPBOX_WATCH_ROOT

logger = logging.getLogger(__name__)


class MediaIngestCog(commands.Cog, name="MediaIngest"):
    """Media pipeline processing commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Initialize MediaWatcher 4.0
        self.mediawatcher = create_mediawatcher(
            media_root=MEDIA_ROOT,
            data_root=MEDIAWATCHER_DATA,
            incoming_dir=MEDIA_ROOT / "_incoming",
            dropbox_dir=DROPBOX_WATCH_ROOT
        )
        
        logger.info("[MediaIngest] Initialized with MediaWatcher 4.0")
    
    @app_commands.command(name="media_pipeline", description="Process all incoming media files")
    @app_commands.guilds(discord.Object(id=944107844205154355))
    async def media_pipeline(self, interaction: discord.Interaction):
        """Process all files in incoming and Dropbox folders"""
        await interaction.response.defer()
        
        try:
            # Process all incoming files
            results = self.mediawatcher.process_incoming()
            
            # Calculate statistics
            total = len(results)
            success_count = sum(1 for r in results if r.success)
            error_count = total - success_count
            
            # Build embed
            embed = discord.Embed(
                title="📁 Media Pipeline Complete",
                color=discord.Color.green() if error_count == 0 else discord.Color.orange()
            )
            
            embed.add_field(name="Total Files", value=str(total), inline=True)
            embed.add_field(name="✅ Success", value=str(success_count), inline=True)
            embed.add_field(name="❌ Errors", value=str(error_count), inline=True)
            
            # Show errors if any
            if error_count > 0:
                error_details = []
                for result in results:
                    if not result.success:
                        error_details.append(f"• {result.original_path.name}: {result.error}")
                
                # Limit to first 10 errors
                if len(error_details) > 10:
                    error_details = error_details[:10]
                    error_details.append(f"... and {len(error_details) - 10} more")
                
                embed.add_field(
                    name="Errors",
                    value="\n".join(error_details) if error_details else "None",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"[MediaIngest] Pipeline failed: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Pipeline failed: {e}")


async def setup(bot):
    await bot.add_cog(MediaIngestCog(bot))