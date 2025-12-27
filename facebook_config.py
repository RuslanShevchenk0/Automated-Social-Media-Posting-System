"""
Конфігурація для роботи з Facebook API
"""

import os
import json
import requests
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

CONFIG_FILE = "facebook_credentials.json"

class FacebookConfig:
    """Клас для управління конфігурацією Facebook"""
    
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self):
        """Завантажує конфігурацію з файлу"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "app_id": "",
            "app_secret": "",
            "access_token": "",
            "token_expires_at": None,
            "pages": []
        }
    
    def save_config(self):
        """Зберігає конфігурацію у файл"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def exchange_for_long_lived_token(self, short_token):
        """
        Обмінює short-lived токен на long-lived (60 днів)
        
        Args:
            short_token: короткостроковий токен
            
        Returns:
            dict: інформація про токен (token, expires_in)
        """
        app_id = self.config.get('app_id')
        app_secret = self.config.get('app_secret')
        
        if not app_id or not app_secret:
            raise ValueError("App ID та App Secret мають бути налаштовані")
        
        logger.info("Обмін на long-lived токен...")
        
        url = "https://graph.facebook.com/v18.0/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": short_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            long_lived_token = data.get('access_token')
            expires_in = data.get('expires_in', 5184000)  # За замовчуванням 60 днів
            
            # Обчислюємо дату закінчення
            expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            
            logger.info(f"✓ Long-lived токен отримано. Дійсний до: {expires_at}")
            
            return {
                "token": long_lived_token,
                "expires_in": expires_in,
                "expires_at": expires_at
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка обміну токена: {str(e)}")
            raise
    
    def set_credentials(self, app_id, app_secret, access_token, auto_exchange=True):
        """
        Встановлює облікові дані
        
        Args:
            app_id: ID додатку Facebook
            app_secret: Secret ключ додатку
            access_token: токен доступу
            auto_exchange: автоматично обміняти на long-lived
        """
        self.config["app_id"] = app_id
        self.config["app_secret"] = app_secret
        
        # Якщо потрібно - обмінюємо на long-lived
        if auto_exchange and app_id and app_secret:
            try:
                token_info = self.exchange_for_long_lived_token(access_token)
                self.config["access_token"] = token_info["token"]
                self.config["token_expires_at"] = token_info["expires_at"]
                logger.info("✓ Токен автоматично обміняно на long-lived")
            except Exception as e:
                logger.warning(f"Не вдалося обміняти токен: {str(e)}")
                logger.info("Зберігаємо короткостроковий токен")
                self.config["access_token"] = access_token
                self.config["token_expires_at"] = None
        else:
            self.config["access_token"] = access_token
            self.config["token_expires_at"] = None
        
        self.save_config()
    
    def is_token_expired(self):
        """Перевіряє чи токен застарів"""
        expires_at = self.config.get("token_expires_at")
        
        if not expires_at:
            return None  # Невідомо
        
        try:
            expires_date = datetime.fromisoformat(expires_at)
            # Вважаємо що токен застарів за 7 днів до дати закінчення
            warning_date = expires_date - timedelta(days=7)
            
            if datetime.now() > expires_date:
                return True  # Застарів
            elif datetime.now() > warning_date:
                return "warning"  # Скоро застаріє
            else:
                return False  # Дійсний
        except:
            return None
    
    def get_token_info(self):
        """Повертає інформацію про токен"""
        expires_at = self.config.get("token_expires_at")
        
        if not expires_at:
            return {
                "has_token": bool(self.config.get("access_token")),
                "is_long_lived": False,
                "expires_at": None,
                "days_left": None,
                "status": "unknown"
            }
        
        try:
            expires_date = datetime.fromisoformat(expires_at)
            days_left = (expires_date - datetime.now()).days
            
            status = "expired" if days_left < 0 else (
                "warning" if days_left < 7 else "valid"
            )
            
            return {
                "has_token": True,
                "is_long_lived": True,
                "expires_at": expires_at,
                "days_left": days_left,
                "status": status
            }
        except:
            return {
                "has_token": bool(self.config.get("access_token")),
                "is_long_lived": False,
                "expires_at": None,
                "days_left": None,
                "status": "unknown"
            }
    
    def add_page(self, page_id, page_name, page_access_token):
        """Додає сторінку для публікацій"""
        page = {
            "id": page_id,
            "name": page_name,
            "access_token": page_access_token
        }
        
        # Перевірка чи сторінка вже існує
        existing = [p for p in self.config["pages"] if p["id"] == page_id]
        if not existing:
            self.config["pages"].append(page)
            self.save_config()
    
    def remove_page(self, page_id):
        """Видаляє сторінку"""
        self.config["pages"] = [p for p in self.config["pages"] if p["id"] != page_id]
        self.save_config()
    
    def get_pages(self):
        """Повертає список сторінок"""
        return self.config["pages"]
    
    def get_page_token(self, page_id):
        """Отримує токен доступу для конкретної сторінки"""
        for page in self.config["pages"]:
            if page["id"] == page_id:
                return page["access_token"]
        return None

# Глобальний екземпляр конфігурації
fb_config = FacebookConfig()