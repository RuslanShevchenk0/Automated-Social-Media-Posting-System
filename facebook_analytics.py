"""
Покращений модуль для роботи з аналітикою Facebook
"""

import requests
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

def get_post_analytics(post_id: str, page_token: str) -> dict:
    """
    Отримує детальну аналітику для поста
    
    Args:
        post_id: ID поста Facebook (формат: PAGE_ID_POST_ID)
        page_token: Токен доступу до сторінки
    
    Returns:
        dict: Статистика поста
    """
    try:
        logger.info(f"Запит аналітики для поста {post_id}")
        
        # Основний запит з детальними метриками
        url = f"https://graph.facebook.com/v18.0/{post_id}"
        params = {
            "fields": (
                "likes.summary(true),"
                "comments.summary(true),"
                "shares,"
                "reactions.summary(true),"
                "created_time,"
                "message,"
                "permalink_url"
            ),
            "access_token": page_token
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        # Якщо основний запит не спрацював, пробуємо альтернативні методи
        if response.status_code != 200:
            logger.warning(f"Основний запит повернув статус {response.status_code}")
            return try_alternative_analytics_methods(post_id, page_token)
        
        data = response.json()
        
        # Збираємо всі метрики
        likes = data.get("likes", {}).get("summary", {}).get("total_count", 0)
        comments = data.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares = data.get("shares", {}).get("count", 0)
        
        # Детальна інформація про реакції
        reactions_summary = data.get("reactions", {}).get("summary", {})
        total_reactions = reactions_summary.get("total_count", likes)
        
        # Спробуємо отримати insights (потребує спеціальних дозволів)
        insights = try_get_post_insights(post_id, page_token)
        
        result = {
            "success": True,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "created_time": data.get("created_time", ""),
            "reactions": {
                "total": total_reactions,
                "like": likes  # базова реакція
            },
            "impressions": insights.get("impressions", 0),
            "engaged_users": insights.get("engaged_users", 0),
            "clicks": insights.get("clicks", 0),
            "reach": insights.get("reach", 0),
            "permalink_url": data.get("permalink_url", "")
        }
        
        logger.info(
            f"Аналітика отримана: "
            f"лайки={likes}, коментарі={comments}, репости={shares}, "
            f"охоплення={result['reach']}"
        )
        
        return result
        
    except requests.exceptions.Timeout:
        logger.error(f"Таймаут при запиті аналітики для {post_id}")
        return get_empty_analytics_response()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Помилка запиту аналітики: {str(e)}")
        
        # Перевіряємо чи це помилка доступу
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_json = e.response.json()
                error_code = error_json.get('error', {}).get('code', 0)
                
                # Коди помилок доступу - повертаємо пусту але успішну відповідь
                if error_code in [10, 100, 190, 200, 803]:
                    logger.warning(f"Немає доступу до аналітики поста {post_id}")
                    return get_empty_analytics_response()
            except:
                pass
        
        return {
            "success": False,
            "error": str(e)
        }
    
    except Exception as e:
        logger.error(f"Неочікувана помилка: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def try_alternative_analytics_methods(post_id: str, page_token: str) -> dict:
    """
    Альтернативні методи отримання аналітики
    """
    try:
        # Метод 1: Через page feed
        parts = post_id.split('_')
        if len(parts) == 2:
            page_id = parts[0]
            
            url = f"https://graph.facebook.com/v18.0/{page_id}/posts"
            params = {
                "fields": "id,likes.summary(true),comments.summary(true),shares,reactions.summary(true)",
                "access_token": page_token,
                "limit": 100
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get('data', [])
                
                for post in posts:
                    if post.get('id') == post_id:
                        likes = post.get("likes", {}).get("summary", {}).get("total_count", 0)
                        comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
                        shares = post.get("shares", {}).get("count", 0)
                        reactions = post.get("reactions", {}).get("summary", {}).get("total_count", likes)
                        
                        logger.info(f"Аналітика отримана через feed: {likes}/{comments}/{shares}")
                        
                        return {
                            "success": True,
                            "likes": likes,
                            "comments": comments,
                            "shares": shares,
                            "reactions": {"total": reactions},
                            "impressions": 0,
                            "engaged_users": 0,
                            "clicks": 0,
                            "reach": 0,
                            "created_time": post.get("created_time", "")
                        }
        
        # Метод 2: Спрощений запит
        url = f"https://graph.facebook.com/v18.0/{post_id}"
        params = {
            "fields": "likes.summary(true),comments.summary(true),shares",
            "access_token": page_token
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            likes = data.get("likes", {}).get("summary", {}).get("total_count", 0)
            comments = data.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares = data.get("shares", {}).get("count", 0)
            
            return {
                "success": True,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "reactions": {"total": likes},
                "impressions": 0,
                "engaged_users": 0,
                "clicks": 0,
                "reach": 0,
                "created_time": ""
            }
        
    except Exception as e:
        logger.warning(f"Альтернативні методи не спрацювали: {str(e)}")
    
    return get_empty_analytics_response()


def try_get_post_insights(post_id: str, page_token: str) -> dict:
    """
    Спроба отримати детальні insights (потребує спеціальних дозволів)
    """
    try:
        url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
        params = {
            "metric": "post_impressions,post_engaged_users,post_clicks,post_reactions_by_type_total",
            "access_token": page_token
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            insights = {}
            
            for item in data.get('data', []):
                name = item.get('name')
                values = item.get('values', [])
                
                if values and len(values) > 0:
                    value = values[0].get('value', 0)
                    
                    if name == 'post_impressions':
                        insights['impressions'] = value
                    elif name == 'post_engaged_users':
                        insights['engaged_users'] = value
                    elif name == 'post_clicks':
                        insights['clicks'] = value
                    elif name == 'post_impressions_unique':
                        insights['reach'] = value
            
            return insights
    except:
        pass
    
    return {}


def get_empty_analytics_response() -> dict:
    """
    Повертає порожню але коректну відповідь
    """
    return {
        "success": True,
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "created_time": "",
        "reactions": {"total": 0},
        "impressions": 0,
        "engaged_users": 0,
        "clicks": 0,
        "reach": 0
    }


def get_page_posts_analytics(page_id: str, page_token: str, limit: int = 25) -> dict:
    """
    Отримує аналітику для всіх постів сторінки
    
    Args:
        page_id: ID сторінки
        page_token: Токен доступу
        limit: Кількість постів для отримання
    
    Returns:
        dict: Список постів з аналітикою
    """
    try:
        url = f"https://graph.facebook.com/v18.0/{page_id}/posts"
        params = {
            "fields": (
                "id,message,created_time,permalink_url,"
                "likes.summary(true),"
                "comments.summary(true),"
                "shares,"
                "reactions.summary(true)"
            ),
            "limit": limit,
            "access_token": page_token
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        posts = []
        
        for post in data.get('data', []):
            posts.append({
                "id": post.get("id"),
                "message": post.get("message", ""),
                "created_time": post.get("created_time", ""),
                "permalink_url": post.get("permalink_url", ""),
                "likes": post.get("likes", {}).get("summary", {}).get("total_count", 0),
                "comments": post.get("comments", {}).get("summary", {}).get("total_count", 0),
                "shares": post.get("shares", {}).get("count", 0),
                "reactions": post.get("reactions", {}).get("summary", {}).get("total_count", 0)
            })
        
        return {
            "success": True,
            "posts": posts
        }
        
    except Exception as e:
        logger.error(f"Помилка отримання постів сторінки: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "posts": []
        }