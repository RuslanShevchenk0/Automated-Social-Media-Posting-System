"""
Facebook OAuth авторизація
"""

import os
import httpx
from typing import Dict
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# Конфігурація з .env
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
FACEBOOK_REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI")

class FacebookOAuth:
    """Клас для роботи з Facebook OAuth"""

    @staticmethod
    def get_login_url(state: str) -> str:
        """
        Генерує URL для редиректу на Facebook OAuth

        Args:
            state: user_id для ідентифікації після повернення

        Returns:
            str: URL для редиректу
        """
        scopes = [
            'pages_manage_posts',
            'pages_read_engagement',
            'pages_show_list',
            'pages_read_user_content',
            'read_insights'
        ]

        params = {
            'client_id': FACEBOOK_APP_ID,
            'redirect_uri': FACEBOOK_REDIRECT_URI,
            'scope': ','.join(scopes),
            'state': state,
            'response_type': 'code'
        }

        from urllib.parse import urlencode
        url = f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"
        logger.info(f"Facebook OAuth URL: {url}")
        logger.info(f"App ID: {FACEBOOK_APP_ID}")
        return url

    @staticmethod
    async def exchange_code_for_token(code: str) -> str:
        """
        Обмінює authorization code на access token

        Args:
            code: код отриманий від Facebook

        Returns:
            str: short-lived access token
        """
        url = "https://graph.facebook.com/v18.0/oauth/access_token"
        params = {
            'client_id': FACEBOOK_APP_ID,
            'client_secret': FACEBOOK_APP_SECRET,
            'redirect_uri': FACEBOOK_REDIRECT_URI,
            'code': code
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                logger.error(f"Facebook token exchange failed: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to get access token")

            data = response.json()
            return data['access_token']

    @staticmethod
    async def exchange_for_long_lived_token(short_token: str) -> Dict:
        """
        Обмінює short-lived token на long-lived (60 днів)

        Args:
            short_token: короткостроковий токен

        Returns:
            dict: {"token": "...", "expires_in": 5184000}
        """
        url = "https://graph.facebook.com/v18.0/oauth/access_token"
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': FACEBOOK_APP_ID,
            'client_secret': FACEBOOK_APP_SECRET,
            'fb_exchange_token': short_token
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                logger.error(f"Long-lived token exchange failed: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to get long-lived token")

            data = response.json()
            return {
                'token': data['access_token'],
                'expires_in': data.get('expires_in', 5184000)
            }

    @staticmethod
    async def get_user_pages(access_token: str) -> list:
        """
        Отримує список Facebook Pages користувача

        Args:
            access_token: токен доступу користувача

        Returns:
            list: список сторінок з токенами
        """
        url = "https://graph.facebook.com/v18.0/me/accounts"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                params={'access_token': access_token}
            )

            if response.status_code != 200:
                logger.error(f"Failed to get user pages: {response.text}")
                return []

            data = response.json()
            return data.get('data', [])
