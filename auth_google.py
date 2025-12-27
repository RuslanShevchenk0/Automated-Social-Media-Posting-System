"""
Google OAuth авторизація та JWT токени
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict
import httpx
from jose import JWTError, jwt
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

# Конфігурація
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 днів

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")


class GoogleOAuth:
    """Клас для роботи з Google OAuth"""

    OAUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    @staticmethod
    def get_login_url(state: str = "") -> str:
        """
        Генерує URL для редиректа на Google

        Args:
            state: Опціональний state parameter для захисту від CSRF

        Returns:
            str: URL для авторизації
        """
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "scope": "openid email profile",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "state": state
        }

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{GoogleOAuth.OAUTH_URL}?{query_string}"

    @staticmethod
    async def exchange_code_for_token(code: str) -> str:
        """
        Обмінює authorization code на access token

        Args:
            code: Authorization code від Google

        Returns:
            str: Access token

        Raises:
            HTTPException: Якщо не вдалося отримати токен
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    GoogleOAuth.TOKEN_URL,
                    data={
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "redirect_uri": GOOGLE_REDIRECT_URI,
                        "code": code,
                        "grant_type": "authorization_code"
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Google token error: {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to get access token from Google"
                    )

                data = response.json()
                return data["access_token"]

            except Exception as e:
                logger.error(f"Error exchanging code for token: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to authenticate with Google"
                )

    @staticmethod
    async def get_user_info(access_token: str) -> Dict:
        """
        Отримує інформацію про користувача з Google

        Args:
            access_token: Google access token

        Returns:
            Dict: Інформація про користувача
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    GoogleOAuth.USER_INFO_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}"
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Google user info error: {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to get user info from Google"
                    )

                data = response.json()
                return {
                    "google_id": data["id"],
                    "email": data.get("email"),
                    "full_name": data.get("name"),
                    "profile_picture": data.get("picture")
                }

            except Exception as e:
                logger.error(f"Error getting user info: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get user information"
                )


class JWTHandler:
    """Клас для роботи з JWT токенами"""

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Створює JWT токен

        Args:
            data: Дані для кодування в токен
            expires_delta: Час життя токену

        Returns:
            str: JWT токен
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> Dict:
        """
        Декодує JWT токен

        Args:
            token: JWT токен

        Returns:
            Dict: Дані з токену

        Raises:
            HTTPException: Якщо токен невалідний
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: int = payload.get("user_id")

            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return payload

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
