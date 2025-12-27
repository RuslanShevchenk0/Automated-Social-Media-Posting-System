"""
Pydantic моделі даних для API
"""

from pydantic import BaseModel
from typing import List, Optional


class PostCreate(BaseModel):
    content: str
    link: Optional[str] = None
    is_ai_generated: bool = False
    ai_prompt: Optional[str] = None
    scheduled_time: Optional[str] = None
    page_ids: List[str]
    image_urls: Optional[List[str]] = []


class PostUpdate(BaseModel):
    content: Optional[str] = None
    link: Optional[str] = None
    scheduled_time: Optional[str] = None


class AIGenerateRequest(BaseModel):
    prompt: str
    min_length: int = 100
    max_length: int = 500
    use_recommendations: bool = True
    lang: str = 'uk'


class TemplateCreate(BaseModel):
    name: str
    content: str
    is_ai_prompt: bool = False
    based_on_recommendations: bool = False
    recommendation_id: Optional[int] = None


class TokenUpdate(BaseModel):
    access_token: str
    app_id: Optional[str] = None
    app_secret: Optional[str] = None


class PageAdd(BaseModel):
    page_id: str
    page_name: str
    page_token: str


class UserLogin(BaseModel):
    email: str
    full_name: Optional[str] = None


class FacebookAppCredentials(BaseModel):
    app_id: str
    app_secret: str
