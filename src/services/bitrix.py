from aiohttp import ClientSession
from fastapi import status
from typing import Literal, Optional

from config import settings
from exceptions import ErrorRequestBitrix


class BitrixService:

    def __init__(self, http_session: ClientSession):
        self.http_session = http_session

    async def app_install(self, access, refresh):
        settings.bitrix.access_token = access
        settings.bitrix.refresh_token = refresh

        return await self.reboot_tokens()

    async def reboot_tokens(self) -> dict:
        """С помощью client_secret приложения можно обновить токены для дальнейшей работы приложения"""
        response = await self.http_session.get(
            url=f"https://oauth.bitrix.info/oauth/token/",
            params={
                'grant_type': 'refresh_token',
                'client_id': settings.bitrix.client_id,
                'client_secret': settings.bitrix.client_secret,
                'refresh_token': settings.bitrix.refresh_token,

            }
        )
        if response.status != 200:
            return {'status_code': response.status, 'error': 'Failed to update tokens.'}
        result = await response.json()

        settings.bitrix.access_token = result['access_token']
        settings.bitrix.refresh_token = result['refresh_token']

        print(f"ac {settings.bitrix.access_token}")
        print(f"ref {settings.bitrix.refresh_token}")

        return {'status_code': 200, 'result': result}

    @staticmethod
    def get_tokens() -> dict:
        return {
            "access_token": settings.bitrix.access_token,
            "refresh_token": settings.bitrix.refresh_token
        }

    async def send_request(
        self,
        endpoint: str,
        method: Literal['get', 'post'] = 'post',
        auth: str = settings.bitrix.access_token,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
    ) -> dict:
        url = f"{settings.bitrix.portal_url}rest/{endpoint}.json"

        params = {
            **(params or {}),
            "auth": auth,
        }

        async def _request():
            return await self.http_session.request(
                method=method,
                url=url,
                params=params,
                json=json,
            )

        response = await _request()

        if response.status == status.HTTP_401_UNAUTHORIZED:
            await self.reboot_tokens()
            params["auth"] = settings.bitrix.access_token
            response = await _request()
            if response.status != status.HTTP_200_OK:
                raise ErrorRequestBitrix()

        return await response.json()
