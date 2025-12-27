"""
Система планування та автоматичної публікації постів з покращеним збором аналітики
+ Автоматична генерація рекомендацій
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict
from database import db
from facebook_manager import FacebookManager
from facebook_config import fb_config
from facebook_analytics import get_post_analytics

logger = logging.getLogger(__name__)

class PostScheduler:
    """Клас для автоматичної публікації запланованих постів"""
    
    def __init__(self, check_interval: int = 60):
        """
        Args:
            check_interval: інтервал перевірки в секундах (за замовчуванням 60)
        """
        self.check_interval = check_interval
        self.is_running = False
        self.fb_manager = FacebookManager(fb_config.config.get('access_token', ''))
    
    async def start(self):
        """Запускає планувальник"""
        self.is_running = True
        logger.info("Планувальник постів запущено")
        
        while self.is_running:
            try:
                await self.check_and_publish_posts()
            except Exception as e:
                logger.error(f"Помилка в планувальнику: {str(e)}")
            
            await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Зупиняє планувальник"""
        self.is_running = False
        logger.info("Планувальник постів зупинено")
    
    async def check_and_publish_posts(self):
        """Перевіряє та публікує заплановані пости"""
        from datetime import datetime
        
        current_time = datetime.now()
        print(f"\n[{current_time.strftime('%H:%M:%S')}] Перевірка запланованих постів...")
        
        try:
            scheduled_posts = db.get_scheduled_posts()
            
            if not scheduled_posts:
                print(f"  → Немає постів готових до публікації")
                return
            
            print(f"  → Знайдено {len(scheduled_posts)} постів для публікації")
            logger.info(f"Знайдено {len(scheduled_posts)} постів для публікації")
            
            for post_data in scheduled_posts:
                try:
                    print(f"  → Публікація поста ID {post_data['id']} на сторінці '{post_data['page_name']}'...")
                    await self.publish_post(post_data)
                except Exception as e:
                    error_msg = str(e)
                    print(f"  ✗ Помилка публікації: {error_msg}")
                    logger.error(f"Помилка публікації поста ID {post_data['id']}: {error_msg}")
                    db.update_publication_status(
                        post_data['publication_id'],
                        'failed',
                        error_message=error_msg
                    )
        except Exception as e:
            print(f"  ✗ Критична помилка в check_and_publish_posts: {str(e)}")
            logger.error(f"Критична помилка: {str(e)}")
    
    async def publish_post(self, post_data: Dict):
        """
        Публікує пост на Facebook та одразу збирає початкову аналітику
        
        Args:
            post_data: дані поста з бази даних
        """
        post_id = post_data['id']
        publication_id = post_data['publication_id']
        page_id = post_data['page_id']
        
        print(f"    → Публікація поста ID {post_id} на сторінці {post_data['page_name']}")
        logger.info(f"Публікація поста ID {post_id} на сторінці {post_data['page_name']}")
        
        page_token = fb_config.get_page_token(page_id)
        
        if not page_token:
            error_msg = f"Не знайдено токен для сторінки {page_id}"
            print(f"    ✗ {error_msg}")
            logger.error(error_msg)
            db.update_publication_status(
                publication_id,
                'failed',
                error_message=error_msg
            )
            return
        
        print(f"    → Відправка запиту до Facebook API...")
        
        # Перевіряємо чи є зображення
        image_urls = post_data.get('image_urls')
        
        # Якщо image_urls це JSON-рядок, парсимо його
        if image_urls and isinstance(image_urls, str):
            try:
                image_urls = json.loads(image_urls)
            except:
                image_urls = []
        
        has_images = image_urls and len(image_urls) > 0
        
        # Публікуємо пост
        if has_images:
            # Конвертуємо URLs в локальні шляхи
            image_paths = []
            for url in image_urls:
                if url.startswith('/uploads/'):
                    # Конвертуємо відносний URL в локальний шлях
                    local_path = url.replace('/uploads/', 'uploads/')
                    image_paths.append(local_path)
                else:
                    logger.warning(f"Пропускаємо не-локальний URL: {url}")
            
            if image_paths:
                print(f"    → Публікація з {len(image_paths)} зображеннями...")
                result = await asyncio.to_thread(
                    self.fb_manager.publish_post_with_images,
                    page_id=page_id,
                    page_token=page_token,
                    message=post_data['content'],
                    image_paths=image_paths,
                    link=post_data.get('link')
                )
            else:
                # Якщо не вдалося сконвертувати URLs, публікуємо без зображень
                print(f"    → Не вдалося підготувати зображення, публікація тільки тексту...")
                result = await asyncio.to_thread(
                    self.fb_manager.publish_post,
                    page_id=page_id,
                    page_token=page_token,
                    message=post_data['content'],
                    link=post_data.get('link')
                )
        else:
            # Публікуємо без зображень
            result = await asyncio.to_thread(
                self.fb_manager.publish_post,
                page_id=page_id,
                page_token=page_token,
                message=post_data['content'],
                link=post_data.get('link')
            )
        
        if result['success']:
            print(f"    ✓ Пост успішно опублікований!")
            print(f"    → Facebook Post ID: {result['post_id']}")
            
            # Оновлюємо статус публікації
            db.update_publication_status(
                publication_id,
                'published',
                facebook_post_id=result['post_id']
            )
            
            # ✨ НОВЕ: Збираємо початкову аналітику через 5 секунд
            print(f"    → Очікування 5 сек перед збором початкової аналітики...")
            await asyncio.sleep(5)
            
            try:
                analytics = await asyncio.to_thread(
                    get_post_analytics,
                    post_id=result['post_id'],
                    page_token=page_token
                )
                
                if analytics.get('success'):
                    db.save_analytics(publication_id, analytics)
                    print(f"    ✓ Початкова аналітика збережена")
                    logger.info(f"Початкова аналітика збережена для {result['post_id']}")
            except Exception as e:
                logger.warning(f"Не вдалося зібрати початкову аналітику: {str(e)}")
            
            # Перевіряємо чи всі публікації цього поста завершені
            conn = db.get_connection()
            all_publications = conn.execute("""
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN status = 'published' THEN 1 ELSE 0 END) as published
                FROM publications WHERE post_id = ?
            """, (post_id,)).fetchone()
            conn.close()
            
            if all_publications['total'] == all_publications['published']:
                db.update_post_status(post_id, 'published')
                print(f"    ✓ Пост ID {post_id} повністю опублікований на всіх сторінках")
                logger.info(f"Пост ID {post_id} повністю опублікований")
            
            logger.info(f"✓ Пост успішно опублікований: {result['post_id']}")
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"    ✗ Помилка публікації: {error_msg}")
            db.update_publication_status(
                publication_id,
                'failed',
                error_message=error_msg
            )
            logger.error(f"✗ Помилка публікації: {error_msg}")


class AnalyticsCollector:
    """Клас для регулярного збору аналітики опублікованих постів"""
    
    def __init__(self, check_interval: int = 1800):  # За замовчуванням 30 хвилин
        """
        Args:
            check_interval: інтервал збору аналітики в секундах (за замовчуванням 1800 = 30 хв)
        """
        self.check_interval = check_interval
        self.is_running = False
        self.fb_manager = FacebookManager(fb_config.config.get('access_token', ''))
    
    async def start(self):
        """Запускає збирач аналітики"""
        self.is_running = True
        logger.info(f"Збирач аналітики запущено (інтервал: {self.check_interval//60} хв)")
        
        while self.is_running:
            try:
                await self.collect_analytics()
            except Exception as e:
                logger.error(f"Помилка в збирачі аналітики: {str(e)}")
            
            await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Зупиняє збирач аналітики"""
        self.is_running = False
        logger.info("Збирач аналітики зупинено")
    
    async def collect_analytics(self):
        """Збирає аналітику для всіх опублікованих постів за останні 30 днів"""
        current_time = datetime.now()
        print(f"\n[{current_time.strftime('%H:%M:%S')}] Збір аналітики...")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Отримуємо публікації за останні 30 днів, сортуємо за датою оновлення аналітики
        cursor.execute("""
            SELECT pub.id, pub.facebook_post_id, pub.page_id,
                   p.published_at, a.updated_at as analytics_updated_at
            FROM publications pub
            JOIN posts p ON pub.post_id = p.id
            LEFT JOIN analytics a ON pub.id = a.publication_id
            WHERE pub.status = 'published' 
            AND pub.facebook_post_id IS NOT NULL
            AND p.published_at > datetime('now', '-30 days')
            ORDER BY 
                CASE 
                    WHEN a.updated_at IS NULL THEN 0
                    ELSE 1
                END,
                a.updated_at ASC
            LIMIT 50
        """)
        
        publications = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        if not publications:
            print("  → Немає публікацій для оновлення аналітики")
            return
        
        print(f"  → Оновлення аналітики для {len(publications)} публікацій...")
        logger.info(f"Збір аналітики для {len(publications)} публікацій")
        
        success_count = 0
        error_count = 0
        
        for i, pub in enumerate(publications, 1):
            try:
                # Показуємо прогрес
                if i % 10 == 0:
                    print(f"  → Оброблено {i}/{len(publications)}...")
                
                analytics = await self.collect_post_analytics(pub)
                
                if analytics:
                    success_count += 1
                else:
                    error_count += 1
                
                # Невелика затримка між запитами
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Помилка збору аналітики для публікації {pub['id']}: {str(e)}")
                error_count += 1
        
        print(f"  ✓ Завершено: {success_count} успішно, {error_count} помилок")
        logger.info(f"Збір аналітики завершено: {success_count} успішно, {error_count} помилок")
    
    async def collect_post_analytics(self, publication: Dict) -> bool:
        """
        Збирає аналітику для окремої публікації
        
        Returns:
            bool: True якщо успішно
        """
        page_token = fb_config.get_page_token(publication['page_id'])
        
        if not page_token:
            logger.warning(f"Не знайдено токен для сторінки {publication['page_id']}")
            return False
        
        try:
            analytics = await asyncio.to_thread(
                get_post_analytics,
                post_id=publication['facebook_post_id'],
                page_token=page_token
            )
            
            if analytics.get('success'):
                db.save_analytics(publication['id'], analytics)
                logger.debug(
                    f"Аналітика оновлена для публікації {publication['id']}: "
                    f"👍{analytics.get('likes', 0)} 💬{analytics.get('comments', 0)} "
                    f"🔄{analytics.get('shares', 0)}"
                )
                return True
            else:
                logger.warning(f"Не вдалося отримати аналітику: {analytics.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Помилка отримання аналітики: {str(e)}")
            return False


class RecommendationsScheduler:
    """Клас для автоматичної генерації AI-рекомендацій"""
    
    def __init__(self, check_interval: int = 86400):  # За замовчуванням 24 години
        """
        Args:
            check_interval: інтервал перевірки в секундах (за замовчуванням 86400 = 24 год)
        """
        self.check_interval = check_interval
        self.is_running = False
        # Налаштування: який день тижня та година для запуску (понеділок о 9:00)
        self.target_day = 0  # 0 = понеділок
        self.target_hour = 9
    
    async def start(self):
        """Запускає планувальник рекомендацій"""
        self.is_running = True
        logger.info(f"Планувальник рекомендацій запущено (перевірка кожні {self.check_interval//3600} год)")
        logger.info(f"Цільовий час: понеділок о {self.target_hour}:00")
        
        while self.is_running:
            try:
                await self.check_and_generate()
            except Exception as e:
                logger.error(f"Помилка в планувальнику рекомендацій: {str(e)}")
            
            await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Зупиняє планувальник"""
        self.is_running = False
        logger.info("Планувальник рекомендацій зупинено")
    
    async def check_and_generate(self):
        """Перевіряє чи потрібно генерувати рекомендації"""
        now = datetime.now()
        
        # Перевіряємо чи сьогодні цільовий день і година
        if now.weekday() != self.target_day or now.hour != self.target_hour:
            return
        
        print(f"\n[{now.strftime('%H:%M:%S')}] Перевірка необхідності генерації рекомендацій...")
        
        # Перевіряємо чи була рекомендація за останні 7 днів
        has_recent = db.check_recent_recommendation(days=7)
        
        if has_recent:
            print("  → Свіжа рекомендація вже існує, пропускаємо")
            logger.info("Свіжа рекомендація вже існує")
            return
        
        # Генеруємо нові рекомендації
        await self.generate_recommendations()
    
    async def generate_recommendations(self):
        """Генерує AI-рекомендації на основі топ-постів"""
        print("  → Запуск генерації AI-рекомендацій...")
        logger.info("Початок генерації AI-рекомендацій")
        
        try:
            from analytics_recommender import recommender
            
            # Виконуємо повний аналіз за останні 7 днів, топ-10 постів, з AI
            result = recommender.get_full_analysis(
                period_days=7,
                limit=10,
                use_ai=True
            )
            
            if result['success']:
                print(f"  ✓ Рекомендації успішно згенеровано!")
                print(f"  → Проаналізовано {result['analyzed_count']} постів")
                
                if result.get('ai_insights'):
                    print("  ✓ AI-інсайти отримано")
                
                logger.info(f"✓ Рекомендації згенеровано: {result['analyzed_count']} постів")
            else:
                print(f"  ✗ {result['message']}")
                logger.warning(f"Не вдалося згенерувати рекомендації: {result['message']}")
                
        except Exception as e:
            print(f"  ✗ Помилка генерації: {str(e)}")
            logger.error(f"Помилка генерації рекомендацій: {str(e)}")


# Глобальні екземпляри
post_scheduler = PostScheduler()
# Збирач аналітики з інтервалом 30 хвилин
analytics_collector = AnalyticsCollector(check_interval=1800)
# Генератор рекомендацій - перевірка кожні 24 години
recommendations_scheduler = RecommendationsScheduler(check_interval=86400)