# cogs/media_repair.py

"""
Discord commands for MediaWatcher repair functionality.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging

from utils.mediawatcher.mediawatcher import create_mediawatcher
from config import MEDIA_ROOT, MEDIAWATCHER_DATA, DROPBOX_WATCH_ROOT

logger = logging.getLogger(__name__)


class MediaRepairCog(commands.Cog, name="MediaRepair"):
    """Media library repair and maintenance commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Initialize MediaWatcher
        self.mediawatcher = create_mediawatcher(
            media_root=MEDIA_ROOT,
            data_root=MEDIAWATCHER_DATA,
            incoming_dir=MEDIA_ROOT / "_incoming",
            dropbox_dir=DROPBOX_WATCH_ROOT
        )
        
        logger.info("[MediaRepair] Initialized")
    
    @app_commands.command(
        name="media_scan",
        description="Scan media library for issues (wrong format, missing thumbnails, etc.)"
    )
    @app_commands.guilds(discord.Object(id=944107844205154355))
    async def media_scan(self, interaction: discord.Interaction, slug: str = None):
        """Scan media library for issues"""
        await interaction.response.defer()
        
        try:
            # Scan for issues
            issues, summary = self.mediawatcher.scan_for_issues(slug_filter=slug)
            
            total_issues = len(issues)
            
            # Build embed
            embed = discord.Embed(
                title="🔍 Media Library Scan",
                color=discord.Color.blue() if total_issues == 0 else discord.Color.orange()
            )
            
            if slug:
                embed.description = f"Scanned: **{slug}**"
            else:
                embed.description = "Scanned entire library"
            
            if total_issues == 0:
                embed.add_field(
                    name="✅ No Issues Found",
                    value="Your library is perfectly organized!",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Total Issues",
                    value=str(total_issues),
                    inline=False
                )
                
                # Show breakdown by type
                for issue_type, count in summary.items():
                    display_name = issue_type.replace("_", " ").title()
                    embed.add_field(
                        name=display_name,
                        value=str(count),
                        inline=True
                    )
                
                # Show sample issues (first 5)
                if total_issues <= 5:
                    sample_issues = issues
                else:
                    sample_issues = issues[:5]
                
                issue_list = "\n".join([
                    f"• {issue.description}" 
                    for issue in sample_issues
                ])
                
                if total_issues > 5:
                    issue_list += f"\n... and {total_issues - 5} more"
                
                embed.add_field(
                    name="Sample Issues",
                    value=issue_list[:1024] if issue_list else "None",
                    inline=False
                )
                
                embed.set_footer(
                    text="Use /media_repair to fix these issues"
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"[MediaRepair] Scan failed: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Scan failed: {e}")
    
    @app_commands.command(
        name="media_repair",
        description="Repair media library issues (converts, renames, generates thumbnails)"
    )
    @app_commands.guilds(discord.Object(id=944107844205154355))
    async def media_repair(
        self,
        interaction: discord.Interaction,
        slug: str = None,
        dry_run: bool = True
    ):
        """Repair media library"""
        await interaction.response.defer()
        
        try:
            # Create progress message
            mode = "🔍 DRY RUN" if dry_run else "🔧 REPAIR"
            progress_msg = await interaction.followup.send(
                f"{mode} in progress...",
                wait=True
            )
            
            # Scan and repair
            issues, stats = self.mediawatcher.scan_and_repair(
                slug_filter=slug,
                dry_run=dry_run
            )
            
            # Build final embed
            embed = discord.Embed(
                title=f"{mode} Complete",
                color=discord.Color.blue() if dry_run else discord.Color.green()
            )
            
            if slug:
                embed.description = f"Processed: **{slug}**"
            else:
                embed.description = "Processed entire library"
            
            if len(issues) == 0:
                embed.add_field(
                    name="✅ No Issues Found",
                    value="Library is clean!",
                    inline=False
                )
            else:
                # Stats
                embed.add_field(
                    name="Issues Found",
                    value=str(stats.total_scanned),
                    inline=True
                )
                
                if not dry_run:
                    embed.add_field(
                        name="Converted",
                        value=str(stats.files_converted),
                        inline=True
                    )
                    embed.add_field(
                        name="Renamed",
                        value=str(stats.files_renamed),
                        inline=True
                    )
                    embed.add_field(
                        name="Thumbnails",
                        value=str(stats.thumbnails_generated),
                        inline=True
                    )
                    embed.add_field(
                        name="Compressed",
                        value=str(stats.files_compressed),
                        inline=True
                    )
                
                embed.add_field(
                    name="Errors",
                    value=str(stats.errors),
                    inline=True
                )
                
                if dry_run:
                    embed.set_footer(
                        text="This was a dry run. Use dry_run=False to apply changes."
                    )
                else:
                    embed.set_footer(
                        text="✅ Changes applied! Originals backed up to _repair_backup/"
                    )
            
            await progress_msg.edit(content=None, embed=embed)
            
        except Exception as e:
            logger.error(f"[MediaRepair] Repair failed: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Repair failed: {e}")
    
    @app_commands.command(
        name="media_test_ffmpeg",
        description="Test ffmpeg and ffprobe paths"
    )
    @app_commands.guilds(discord.Object(id=944107844205154355))
    async def test_ffmpeg(self, interaction: discord.Interaction):
        """Test ffmpeg installation"""
        await interaction.response.defer()
        
        try:
            from config import FFMPEG_PATH, FFPROBE_PATH
            import subprocess
            
            embed = discord.Embed(
                title="🔧 FFmpeg Path Test",
                color=discord.Color.blue()
            )
            
            # Test ffmpeg
            try:
                result = subprocess.run(
                    [str(FFMPEG_PATH), '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version = result.stdout.split('\n')[0]
                    embed.add_field(
                        name="✅ FFmpeg",
                        value=f"Path: `{FFMPEG_PATH}`\n{version}",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="❌ FFmpeg",
                        value=f"Path: `{FFMPEG_PATH}`\nFailed to run",
                        inline=False
                    )
            except Exception as e:
                embed.add_field(
                    name="❌ FFmpeg",
                    value=f"Path: `{FFMPEG_PATH}`\nError: {e}",
                    inline=False
                )
            
            # Test ffprobe
            try:
                result = subprocess.run(
                    [str(FFPROBE_PATH), '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version = result.stdout.split('\n')[0]
                    embed.add_field(
                        name="✅ FFprobe",
                        value=f"Path: `{FFPROBE_PATH}`\n{version}",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="❌ FFprobe",
                        value=f"Path: `{FFPROBE_PATH}`\nFailed to run",
                        inline=False
                    )
            except Exception as e:
                embed.add_field(
                    name="❌ FFprobe",
                    value=f"Path: `{FFPROBE_PATH}`\nError: {e}",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"[MediaRepair] FFmpeg test failed: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Test failed: {e}")


async def setup(bot):
    await bot.add_cog(MediaRepairCog(bot))
