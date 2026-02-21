from aiohttp import ClientSession
from fastapi import status
from typing import Literal, Optional

from config import settings, logger
from exceptions import ErrorRequestBitrix, ModelNoFoundException
from repositories.bitrix import BitrixRepository
from services.uow import UnitOfWorkService


class BitrixService:

    def __init__(self, http_session: ClientSession, repository: BitrixRepository, uow: UnitOfWorkService):
        self.http_session = http_session
        self.repository = repository
        self.uow = uow

    async def app_install(self, access, refresh):
        async with self.uow:
            try:
                auth = await self.repository.get_first(self.uow.session)
            except ModelNoFoundException:
                auth = await self.repository.add_one(
                    self.uow.session,
                    {
                        "name_app": "main",
                        "owner": 77297,
                        "client_secret": settings.bitrix.client_secret,
                        'client_id': settings.bitrix.client_id,
                        'access_token': settings.bitrix.access_token,
                        'refresh_token': settings.bitrix.refresh_token,
                    }
                )

            auth.access_token = access
            auth.refresh_token = refresh

        return await self.reboot_tokens()

    async def reboot_tokens(self) -> dict:
        """С помощью client_secret приложения можно обновить токены для дальнейшей работы приложения"""
        logger.info("reboot tokens")

        async with self.uow:
            auth = await self.repository.get_first(self.uow.session)

            response = await self.http_session.get(
                url=f"https://oauth.bitrix.info/oauth/token/",
                params={
                    'grant_type': 'refresh_token',
                    'client_id': auth.client_id,
                    'client_secret': auth.client_secret,
                    'refresh_token': auth.refresh_token,

                }
            )
            if response.status != 200:
                return {'status_code': response.status, 'error': 'Failed to update tokens.'}
            result = await response.json()

            auth.access_token = result['access_token']
            auth.refresh_token = result['refresh_token']

            return {'status_code': 200, 'result': result}

    async def get_tokens(self) -> dict:
        auth = await self.repository.get_first(self.uow.session)

        return {
            "access_token": auth.access_token,
            "refresh_token": auth.refresh_token
        }

    async def send_request(
        self,
        endpoint: str,
        method: Literal['get', 'post'] = 'post',
        auth_token: Optional[str] = None,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
    ) -> dict:
        url = f"{settings.bitrix.portal_url}rest/{endpoint}.json"

        if auth_token is None:
            auth =  await self.repository.get_first(self.uow.session)
            auth_token = auth.access_token

        params = {
            **(params or {}),
            "auth": auth_token,
        }

        async def _request():
            return await self.http_session.request(
                method=method,
                url=url,
                params=params,
                json=json,
            )

        response = await _request()

        if response.status != status.HTTP_200_OK:


            auth = await self.reboot_tokens()

            params["auth"] = auth["result"]['access_token']
            response = await _request()
            if response.status != status.HTTP_200_OK:
                raise ErrorRequestBitrix()

        return await response.json()
