from __future__ import annotations

import os
from typing import Any, Dict, Optional

import aiohttp

from utils.bluesky import log


class BlueskyAPI:
    """
    Thin, reliable Bluesky API client.

    Responsibilities:
    - Authenticate (via app password)
    - Fetch feeds / profiles
    - Fetch post records
    """

    BASE_URL = "https://bsky.social/xrpc"

    def __init__(
        self,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self._external_session = session is not None

        self.session = session or aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

        # Read existing .env values
        self.handle = os.getenv("BSKY_HANDLE")
        self.app_password = os.getenv("BSKY_APP_PASSWORD")

        self.access_token: Optional[str] = None
        self.did: Optional[str] = None

        self.enabled = bool(self.handle and self.app_password)

        if self.enabled:
            log("BlueskyAPI initialized (app password auth)")
        else:
            log("BlueskyAPI DISABLED – missing BSKY_HANDLE or BSKY_APP_PASSWORD")

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------

    async def _login(self) -> None:
        """
        Authenticate using handle + app password
        """
        payload = {
            "identifier": self.handle,
            "password": self.app_password,
        }

        async with self.session.post(
            f"{self.BASE_URL}/com.atproto.server.createSession",
            json=payload,
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Bluesky login failed {resp.status}: {text}")

            data = await resp.json()

        self.access_token = data["accessJwt"]
        self.did = data.get("did")

        log(f"BlueskyAPI logged in as {self.handle}")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def _ensure_auth(self) -> None:
        if not self.enabled:
            raise RuntimeError("Bluesky API is not configured")

        if not self.access_token:
            await self._login()

    async def ensure_session(self) -> None:
        """
        Public method to ensure authentication and session are ready.
        Called by media download functions for compatibility.
        """
        await self._ensure_auth()

    async def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        await self._ensure_auth()

        url = f"{self.BASE_URL}/{endpoint}"
        async with self.session.get(
            url, headers=self._headers(), params=params
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(
                    f"Bluesky API GET failed {resp.status}: {text}"
                )
            return await resp.json()

    async def _post(
        self,
        endpoint: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        await self._ensure_auth()

        url = f"{self.BASE_URL}/{endpoint}"
        async with self.session.post(
            url, headers=self._headers(), json=payload
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(
                    f"Bluesky API POST failed {resp.status}: {text}"
                )
            return await resp.json()

    # ------------------------------------------------------------
    # Public API (unchanged)
    # ------------------------------------------------------------

    async def resolve_handle(self, handle: str) -> str:
        data = await self._get(
            "com.atproto.identity.resolveHandle",
            {"handle": handle},
        )
        did = data.get("did")
        if not did:
            raise RuntimeError(f"Failed to resolve handle: {handle}")
        return did

    async def get_author_feed(
        self,
        actor: str,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "actor": actor,
            "limit": limit,
        }
        if cursor:
            params["cursor"] = cursor

        return await self._get(
            "app.bsky.feed.getAuthorFeed",
            params,
        )

    async def get_post_thread(self, uri: str, depth: int = 0) -> Dict[str, Any]:
        return await self._get(
            "app.bsky.feed.getPostThread",
            {"uri": uri, "depth": depth},
        )

    async def get_post(self, uri: str) -> Dict[str, Any]:
        return await self._get(
            "com.atproto.repo.getRecord",
            {
                "repo": uri.split("/")[2],
                "collection": "app.bsky.feed.post",
                "rkey": uri.split("/")[-1],
            },
        )

    # ------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------

    async def close(self):
        if not self._external_session:
            await self.session.close()
