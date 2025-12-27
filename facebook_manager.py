"""
Менеджер для роботи з Facebook Graph API
"""

import requests
import logging
import os
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class FacebookManager:
    """Клас для взаємодії з Facebook API"""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
    
    def get_user_pages(self) -> List[Dict]:
        """
        Отримує список сторінок користувача
        
        Returns:
            List[Dict]: Список сторінок з ID, назвою та токенами
        """
        try:
            url = f"{self.BASE_URL}/me/accounts"
            params = {
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if "data" in data:
                pages = []
                for page in data["data"]:
                    pages.append({
                        "id": page["id"],
                        "name": page["name"],
                        "access_token": page["access_token"],
                        "category": page.get("category", "Unknown")
                    })
                return pages
            return []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка отримання сторінок: {str(e)}")
            return []
    
    def publish_post(self, page_id: str, page_token: str, message: str, 
                    link: Optional[str] = None, 
                    scheduled_time: Optional[datetime] = None) -> Dict:
        """
        Публікує пост на сторінці Facebook
        
        Args:
            page_id: ID сторінки Facebook
            page_token: Токен доступу до сторінки
            message: Текст повідомлення
            link: Посилання (опціонально)
            scheduled_time: Час для запланованої публікації (опціонально)
        
        Returns:
            Dict: Інформація про опублікований пост
        """
        try:
            url = f"{self.BASE_URL}/{page_id}/feed"
            
            data = {
                "message": message,
                "access_token": page_token
            }
            
            # Додати посилання якщо є
            if link:
                data["link"] = link
            
            # Заплановане публікування
            if scheduled_time:
                timestamp = int(scheduled_time.timestamp())
                data["published"] = False
                data["scheduled_publish_time"] = timestamp
            
            logger.info(f"Відправка запиту на {url}")
            logger.info(f"Дані запиту: message length={len(message)}, link={link}, scheduled={scheduled_time}")
            
            response = requests.post(url, data=data)
            
            # Логуємо відповідь для діагностики
            logger.info(f"Статус відповіді: {response.status_code}")
            
            try:
                response_json = response.json()
                logger.info(f"Відповідь JSON: {response_json}")
            except:
                logger.info(f"Відповідь текст: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            
            logger.info(f"Пост успішно опублікований. ID: {result.get('id')}")
            
            return {
                "success": True,
                "post_id": result.get("id"),
                "message": "Пост опубліковано успішно"
            }
            
        except requests.exceptions.RequestException as e:
            error_details = str(e)
            
            # Намагаємось отримати детальну помилку з відповіді
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    if 'error' in error_json:
                        error_details = f"{error_json['error'].get('message', str(e))} (код: {error_json['error'].get('code', 'unknown')})"
                        logger.error(f"Facebook API помилка: {error_json}")
                except:
                    error_details = e.response.text if hasattr(e.response, 'text') else str(e)
            
            logger.error(f"Помилка публікації поста: {error_details}")
            return {
                "success": False,
                "error": error_details,
                "message": "Помилка публікації"
            }
    
    def publish_post_with_images(self, page_id: str, page_token: str, message: str,
                                 image_paths: List[str],
                                 link: Optional[str] = None,
                                 scheduled_time: Optional[datetime] = None) -> Dict:
        """
        Публікує пост з зображеннями на Facebook
        
        Args:
            page_id: ID сторінки
            page_token: Токен доступу
            message: Текст поста
            image_paths: Список локальних шляхів до зображень
            link: Посилання (опціонально)
            scheduled_time: Час планування (опціонально)
        
        Returns:
            Dict: Результат публікації
        """
        try:
            logger.info(f"Публікація поста з {len(image_paths)} зображеннями")
            
            # Крок 1: Завантажуємо всі фото на Facebook (unpublished)
            photo_ids = []
            for i, img_path in enumerate(image_paths, 1):
                logger.info(f"Завантаження фото {i}/{len(image_paths)}: {img_path}")
                
                if not os.path.exists(img_path):
                    logger.error(f"✗ Файл не знайдено: {img_path}")
                    continue
                
                photo_url = f"{self.BASE_URL}/{page_id}/photos"
                
                # Відкриваємо файл та відправляємо
                with open(img_path, 'rb') as image_file:
                    files = {
                        'source': image_file
                    }
                    data = {
                        'published': 'false',  # Не публікуємо окремо
                        'access_token': page_token
                    }
                    
                    photo_response = requests.post(photo_url, files=files, data=data, timeout=30)
                
                photo_response.raise_for_status()
                photo_result = photo_response.json()
                
                if 'id' in photo_result:
                    photo_ids.append(photo_result['id'])
                    logger.info(f"✓ Фото завантажено: {photo_result['id']}")
                else:
                    logger.warning(f"✗ Не вдалося завантажити фото: {photo_result}")
            
            if not photo_ids:
                raise Exception("Не вдалося завантажити жодного зображення")
            
            logger.info(f"Завантажено {len(photo_ids)} фото: {photo_ids}")
            
            # Крок 2: Публікуємо пост з attached_media
            feed_url = f"{self.BASE_URL}/{page_id}/feed"
            
            feed_data = {
                "message": message,
                "access_token": page_token
            }
            
            # Додаємо зображення через attached_media
            for i, photo_id in enumerate(photo_ids):
                feed_data[f"attached_media[{i}]"] = f'{{"media_fbid":"{photo_id}"}}'
            
            # Додаємо посилання якщо є (опціонально)
            if link:
                feed_data["link"] = link
            
            # Заплановане публікування
            if scheduled_time:
                timestamp = int(scheduled_time.timestamp())
                feed_data["published"] = "false"
                feed_data["scheduled_publish_time"] = timestamp
            
            logger.info("Публікація поста з фото...")
            feed_response = requests.post(feed_url, data=feed_data, timeout=30)
            
            logger.info(f"Статус відповіді: {feed_response.status_code}")
            
            feed_response.raise_for_status()
            feed_result = feed_response.json()
            
            logger.info(f"Відповідь: {feed_result}")
            
            if 'id' in feed_result:
                logger.info(f"✓ Пост з фото успішно опублікований: {feed_result['id']}")
                return {
                    "success": True,
                    "post_id": feed_result['id'],
                    "photo_ids": photo_ids,
                    "message": "Пост з фото опубліковано"
                }
            else:
                raise Exception("Не отримано ID поста у відповіді")
            
        except requests.exceptions.RequestException as e:
            error_details = str(e)
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    if 'error' in error_json:
                        error_details = f"{error_json['error'].get('message', str(e))} (код: {error_json['error'].get('code', 'unknown')})"
                        logger.error(f"Facebook API помилка: {error_json}")
                except:
                    error_details = e.response.text if hasattr(e.response, 'text') else str(e)
            
            logger.error(f"Помилка публікації з фото: {error_details}")
            return {
                "success": False,
                "error": error_details,
                "message": "Помилка публікації з фото"
            }
        except Exception as e:
            logger.error(f"Неочікувана помилка: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Помилка публікації"
            }
    
    def get_post_insights(self, post_id: str, page_token: str) -> Dict:
        """
        Отримує аналітику для поста
        
        Args:
            post_id: ID поста
            page_token: Токен доступу до сторінки
        
        Returns:
            Dict: Статистика поста
        """
        try:
            url = f"{self.BASE_URL}/{post_id}"
            params = {
                "fields": "insights.metric(post_impressions,post_engaged_users,post_clicks,post_reactions_by_type_total),likes.summary(true),comments.summary(true),shares",
                "access_token": page_token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Парсинг insights
            insights = {}
            if "insights" in data and "data" in data["insights"]:
                for metric in data["insights"]["data"]:
                    metric_name = metric["name"]
                    metric_values = metric.get("values", [])
                    if metric_values:
                        insights[metric_name] = metric_values[0].get("value", 0)
            
            # Додаткова статистика
            likes = data.get("likes", {}).get("summary", {}).get("total_count", 0)
            comments = data.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares = data.get("shares", {}).get("count", 0)
            
            return {
                "success": True,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "impressions": insights.get("post_impressions", 0),
                "engaged_users": insights.get("post_engaged_users", 0),
                "clicks": insights.get("post_clicks", 0),
                "reactions": insights.get("post_reactions_by_type_total", {})
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка отримання аналітики: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_post(self, post_id: str, page_token: str) -> bool:
        """
        Видаляє пост
        
        Args:
            post_id: ID поста
            page_token: Токен доступу до сторінки
        
        Returns:
            bool: True якщо видалення успішне
        """
        try:
            url = f"{self.BASE_URL}/{post_id}"
            params = {
                "access_token": page_token
            }
            
            response = requests.delete(url, params=params)
            response.raise_for_status()
            
            logger.info(f"Пост {post_id} видалено")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка видалення поста: {str(e)}")
            return False
    
    def get_page_insights(self, page_id: str, page_token: str, 
                         metrics: Optional[List[str]] = None) -> Dict:
        """
        Отримує загальну аналітику сторінки
        
        Args:
            page_id: ID сторінки
            page_token: Токен доступу
            metrics: Список метрик для отримання
        
        Returns:
            Dict: Аналітика сторінки
        """
        if metrics is None:
            metrics = [
                "page_impressions",
                "page_engaged_users",
                "page_post_engagements",
                "page_fans"
            ]
        
        try:
            url = f"{self.BASE_URL}/{page_id}/insights"
            params = {
                "metric": ",".join(metrics),
                "access_token": page_token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            insights = {}
            if "data" in data:
                for metric in data["data"]:
                    metric_name = metric["name"]
                    metric_values = metric.get("values", [])
                    if metric_values:
                        insights[metric_name] = metric_values[0].get("value", 0)
            
            return {
                "success": True,
                "insights": insights
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка отримання аналітики сторінки: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }