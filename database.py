"""
База даних для зберігання постів та аналітики
Покращена версія з індексами, валідацією та додатковими методами
+ Розширена аналітика для інтелектуального аналізу
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class Database:
    """Клас для роботи з базою даних"""
    
    def __init__(self, db_file="marketing_db.sqlite"):
        self.db_file = db_file
        self.init_database()
    
    def get_connection(self):
        """Отримує з'єднання з базою даних"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Ініціалізує структуру бази даних"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Выполнить миграции если нужно
        self._run_migrations(cursor)
        
        # Таблиця постів
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                link TEXT,
                image_urls TEXT,
                is_ai_generated BOOLEAN DEFAULT 0,
                ai_prompt TEXT,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scheduled_time TIMESTAMP,
                published_at TIMESTAMP,
                CHECK (length(content) > 0),
                CHECK (status IN ('draft', 'scheduled', 'published', 'failed'))
            )
        """)
        
        # Перевірка чи існує колонка image_urls
        cursor.execute("PRAGMA table_info(posts)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'image_urls' not in columns:
            logger.info("Додаємо колонку image_urls до таблиці posts...")
            cursor.execute("ALTER TABLE posts ADD COLUMN image_urls TEXT")
        
        # Таблиця публікацій (зв'язок пост - сторінка)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                page_id TEXT NOT NULL,
                page_name TEXT NOT NULL,
                facebook_post_id TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                published_at TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                CHECK (status IN ('pending', 'published', 'failed'))
            )
        """)
        
        # Таблиця аналітики - РОЗШИРЕНА
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publication_id INTEGER NOT NULL,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                engaged_users INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                reactions TEXT,
                hour_of_day INTEGER,
                day_of_week INTEGER,
                engagement_rate REAL DEFAULT 0.0,
                text_length INTEGER DEFAULT 0,
                has_link BOOLEAN DEFAULT 0,
                has_images BOOLEAN DEFAULT 0,
                image_count INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (publication_id) REFERENCES publications(id) ON DELETE CASCADE,
                CHECK (likes >= 0),
                CHECK (comments >= 0),
                CHECK (shares >= 0),
                CHECK (impressions >= 0),
                CHECK (hour_of_day IS NULL OR (hour_of_day >= 0 AND hour_of_day <= 23)),
                CHECK (day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6)),
                CHECK (engagement_rate >= 0.0)
            )
        """)
        
        # Додавання нових колонок якщо їх немає
        cursor.execute("PRAGMA table_info(analytics)")
        analytics_columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = {
            'hour_of_day': 'INTEGER',
            'day_of_week': 'INTEGER',
            'engagement_rate': 'REAL DEFAULT 0.0',
            'text_length': 'INTEGER DEFAULT 0',
            'has_link': 'BOOLEAN DEFAULT 0',
            'has_images': 'BOOLEAN DEFAULT 0',
            'image_count': 'INTEGER DEFAULT 0'
        }
        
        for col_name, col_type in new_columns.items():
            if col_name not in analytics_columns:
                logger.info(f"Додаємо колонку {col_name} до таблиці analytics...")
                cursor.execute(f"ALTER TABLE analytics ADD COLUMN {col_name} {col_type}")
        
        # Таблиця шаблонів постів
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                is_ai_prompt BOOLEAN DEFAULT 0,
                based_on_recommendations BOOLEAN DEFAULT 0,
                recommendation_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (length(name) > 0),
                CHECK (length(content) > 0),
                FOREIGN KEY (recommendation_id) REFERENCES ai_recommendations(id) ON DELETE SET NULL
            )
        """)

        # Перевірка і додавання нових колонок для шаблонів
        cursor.execute("PRAGMA table_info(templates)")
        template_columns = [column[1] for column in cursor.fetchall()]

        if 'based_on_recommendations' not in template_columns:
            logger.info("Додаємо колонку based_on_recommendations до таблиці templates...")
            cursor.execute("ALTER TABLE templates ADD COLUMN based_on_recommendations BOOLEAN DEFAULT 0")

        if 'recommendation_id' not in template_columns:
            logger.info("Додаємо колонку recommendation_id до таблиці templates...")
            cursor.execute("ALTER TABLE templates ADD COLUMN recommendation_id INTEGER")
        
        # Таблиця AI рекомендацій
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP NOT NULL,
                analyzed_posts_count INTEGER DEFAULT 0,
                recommendations_json TEXT NOT NULL,
                patterns_json TEXT,
                status TEXT DEFAULT 'completed',
                CHECK (status IN ('pending', 'completed', 'failed')),
                CHECK (analyzed_posts_count >= 0)
            )
        """)
        
        # Створення індексів для оптимізації запитів
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_status 
            ON posts(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_scheduled_time 
            ON posts(scheduled_time)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_created_at 
            ON posts(created_at DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_publications_post_id 
            ON publications(post_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_publications_status 
            ON publications(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analytics_publication_id 
            ON analytics(publication_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analytics_engagement_rate 
            ON analytics(engagement_rate DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_recommendations_created_at 
            ON ai_recommendations(created_at DESC)
        """)
        
        conn.commit()
        conn.close()

        logger.info("База даних ініціалізована з індексами")

    def _run_migrations(self, cursor):
        """Виконує міграції бази даних"""
        # Міграція 1: Створення таблиці користувачів
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone() is None:
            logger.info("Виконується міграція: додавання таблиці користувачів...")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    facebook_id TEXT UNIQUE NOT NULL,
                    email TEXT,
                    full_name TEXT,
                    profile_picture TEXT,
                    facebook_app_id TEXT,
                    facebook_app_secret TEXT,
                    facebook_access_token TEXT,
                    facebook_token_expires_at TEXT,
                    role TEXT DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_facebook_id ON users(facebook_id)")
            logger.info("Таблиця users створена")

        # Міграція 2: Додавання user_id до posts та publications
        cursor.execute("PRAGMA table_info(posts)")
        posts_columns = [col[1] for col in cursor.fetchall()]
        if 'user_id' not in posts_columns:
            logger.info("Додавання поля user_id до таблиці posts...")
            cursor.execute("ALTER TABLE posts ADD COLUMN user_id INTEGER")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id)")

        cursor.execute("PRAGMA table_info(publications)")
        pubs_columns = [col[1] for col in cursor.fetchall()]
        if 'user_id' not in pubs_columns:
            logger.info("Додавання поля user_id до таблиці publications...")
            cursor.execute("ALTER TABLE publications ADD COLUMN user_id INTEGER")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_publications_user_id ON publications(user_id)")

        # Міграція 3: Створення таблиці user_facebook_pages (ВИКОНУЄТЬСЯ ЗАВЖДИ)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_facebook_pages'")
        if cursor.fetchone() is None:
            logger.info("Виконується міграція: додавання таблиці user_facebook_pages...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_facebook_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    page_id TEXT NOT NULL,
                    page_name TEXT,
                    access_token TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, page_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_pages_user_id ON user_facebook_pages(user_id)")
            logger.info("Таблиця user_facebook_pages створена")

        # Міграція 4: Додавання полів facebook_app_id та facebook_app_secret до users
        cursor.execute("PRAGMA table_info(users)")
        users_columns = [col[1] for col in cursor.fetchall()]

        if 'facebook_app_id' not in users_columns:
            logger.info("Додавання поля facebook_app_id до таблиці users...")
            cursor.execute("ALTER TABLE users ADD COLUMN facebook_app_id TEXT")

        if 'facebook_app_secret' not in users_columns:
            logger.info("Додавання поля facebook_app_secret до таблиці users...")
            cursor.execute("ALTER TABLE users ADD COLUMN facebook_app_secret TEXT")

        # Міграція 5: Додавання полів facebook_access_token та facebook_token_expires_at
        cursor.execute("PRAGMA table_info(users)")
        users_columns = [col[1] for col in cursor.fetchall()]

        if 'facebook_access_token' not in users_columns:
            logger.info("Додавання поля facebook_access_token до таблиці users...")
            cursor.execute("ALTER TABLE users ADD COLUMN facebook_access_token TEXT")

        if 'facebook_token_expires_at' not in users_columns:
            logger.info("Додавання поля facebook_token_expires_at до таблиці users...")
            cursor.execute("ALTER TABLE users ADD COLUMN facebook_token_expires_at TEXT")

    def calculate_engagement_rate(self, likes: int, comments: int, shares: int, impressions: int) -> float:
        """
        Розраховує коефіцієнт залученості
        
        Формула: (лайки + коментарі × 2 + репости × 3) / покази
        
        Args:
            likes: кількість лайків
            comments: кількість коментарів
            shares: кількість репостів
            impressions: кількість показів
        
        Returns:
            float: коефіцієнт залученості
        """
        if impressions == 0:
            return 0.0
        
        engagement_score = likes + (comments * 2) + (shares * 3)
        rate = engagement_score / impressions
        
        return round(rate, 4)
    
    def extract_post_metadata(self, post_id: int) -> Dict:
        """
        Витягує метадані поста для аналітики
        
        Args:
            post_id: ID поста
            
        Returns:
            Dict: метадані поста
        """
        post = self.get_post_by_id(post_id)
        
        if not post:
            return {}
        
        # Аналіз контенту
        content = post.get('content', '')
        text_length = len(content)
        has_link = bool(post.get('link'))
        
        # Аналіз зображень
        image_urls = post.get('image_urls', [])
        if isinstance(image_urls, str):
            try:
                image_urls = json.loads(image_urls)
            except:
                image_urls = []
        
        has_images = bool(image_urls and len(image_urls) > 0)
        image_count = len(image_urls) if image_urls else 0
        
        # Час публікації
        published_at = post.get('published_at')
        hour_of_day = None
        day_of_week = None
        
        if published_at:
            try:
                pub_datetime = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                hour_of_day = pub_datetime.hour
                day_of_week = pub_datetime.weekday()  # 0 = понеділок
            except:
                pass
        
        return {
            'text_length': text_length,
            'has_link': has_link,
            'has_images': has_images,
            'image_count': image_count,
            'hour_of_day': hour_of_day,
            'day_of_week': day_of_week
        }
    
    def create_post(self, content: str, link: Optional[str] = None,
                   is_ai_generated: bool = False, ai_prompt: Optional[str] = None,
                   scheduled_time: Optional[datetime] = None,
                   image_urls: Optional[List[str]] = None,
                   user_id: Optional[int] = None) -> int:
        """
        Створює новий пост з валідацією
        
        Args:
            content: Текст поста
            link: Посилання (опціонально)
            is_ai_generated: Чи згенеровано AI
            ai_prompt: Промпт для AI
            scheduled_time: Час планування
            image_urls: Список URLs зображень
            
        Returns:
            int: ID створеного поста
            
        Raises:
            ValueError: Якщо дані невалідні
        """
        # Валідація
        if not content or len(content.strip()) == 0:
            raise ValueError("Контент поста не може бути пустим")
        
        if len(content) > 5000:
            raise ValueError("Контент поста занадто довгий (макс. 5000 символів)")
        
        if scheduled_time and scheduled_time < datetime.now():
            raise ValueError("Запланований час не може бути в минулому")
        
        # Конвертуємо список URLs в JSON
        image_urls_json = json.dumps(image_urls) if image_urls else None
        
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO posts (content, link, image_urls, is_ai_generated, ai_prompt, scheduled_time, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (content, link, image_urls_json, is_ai_generated, ai_prompt, scheduled_time, user_id))
        
        post_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Створено пост ID: {post_id}")
        return post_id
    
    def add_publication(self, post_id: int, page_id: str, page_name: str, user_id: Optional[int] = None) -> int:
        """
        Додає публікацію для поста

        Returns:
            int: ID публікації
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO publications (post_id, page_id, page_name, user_id)
            VALUES (?, ?, ?, ?)
        """, (post_id, page_id, page_name, user_id))
        
        publication_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return publication_id
    
    def update_publication_status(self, publication_id: int, status: str, 
                                  facebook_post_id: Optional[str] = None,
                                  error_message: Optional[str] = None):
        """Оновлює статус публікації"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        published_at = datetime.now() if status == 'published' else None
        
        cursor.execute("""
            UPDATE publications 
            SET status = ?, facebook_post_id = ?, error_message = ?, published_at = ?
            WHERE id = ?
        """, (status, facebook_post_id, error_message, published_at, publication_id))
        
        conn.commit()
        conn.close()
    
    def get_scheduled_posts(self) -> List[Dict]:
        """Отримує заплановані пости, готові до публікації"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT p.*, pub.id as publication_id, pub.page_id, pub.page_name
                FROM posts p
                JOIN publications pub ON p.id = pub.post_id
                WHERE p.status = 'scheduled'
                AND pub.status = 'pending'
                AND p.scheduled_time IS NOT NULL
                AND datetime(p.scheduled_time) <= datetime('now', 'localtime')
                ORDER BY p.scheduled_time
            """)
            
            posts = []
            for row in cursor.fetchall():
                post_dict = dict(row)
                # Парсимо image_urls з JSON
                if post_dict.get('image_urls'):
                    post_dict['image_urls'] = json.loads(post_dict['image_urls'])
                posts.append(post_dict)
            
            return posts
        except Exception as e:
            logger.error(f"Помилка в get_scheduled_posts: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_post_by_id(self, post_id: int) -> Optional[Dict]:
        """Отримує пост за ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            post = dict(row)
            # Парсимо image_urls з JSON
            if post.get('image_urls'):
                post['image_urls'] = json.loads(post['image_urls'])
            return post
        return None
    
    def get_all_posts(self, limit: int = 50, offset: int = 0, user_id: Optional[int] = None) -> List[Dict]:
        """Отримує всі пости з пагінацією та фільтром по користувачу"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if user_id is not None:
            cursor.execute("""
                SELECT * FROM posts
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM posts
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        posts = []
        for row in cursor.fetchall():
            post = dict(row)
            
            # Парсимо image_urls з JSON
            if post.get('image_urls'):
                post['image_urls'] = json.loads(post['image_urls'])
            
            # Додаємо інформацію про публікації
            cursor.execute("""
                SELECT * FROM publications WHERE post_id = ?
            """, (post['id'],))
            
            publications = [dict(pub) for pub in cursor.fetchall()]
            post['publications'] = publications
            
            posts.append(post)
        
        conn.close()
        return posts
    
    def update_post_status(self, post_id: int, status: str):
        """Оновлює статус поста"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE posts SET status = ? WHERE id = ?
        """, (status, post_id))
        
        conn.commit()
        conn.close()
    
    def save_analytics(self, publication_id: int, analytics_data: Dict):
        """
        Зберігає аналітику для публікації з автоматичним збагаченням даних
        
        Args:
            publication_id: ID публікації
            analytics_data: дані аналітики з Facebook
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Отримуємо post_id з publication
        cursor.execute("SELECT post_id FROM publications WHERE id = ?", (publication_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            logger.error(f"Публікація {publication_id} не знайдена")
            return
        
        post_id = result['post_id']
        
        # Витягуємо метадані поста
        metadata = self.extract_post_metadata(post_id)
        
        # Розраховуємо engagement rate
        likes = analytics_data.get('likes', 0)
        comments = analytics_data.get('comments', 0)
        shares = analytics_data.get('shares', 0)
        impressions = analytics_data.get('impressions', 0)
        
        engagement_rate = self.calculate_engagement_rate(likes, comments, shares, impressions)
        
        # Перевіряємо чи є вже запис
        cursor.execute("""
            SELECT id FROM analytics WHERE publication_id = ?
        """, (publication_id,))
        
        existing = cursor.fetchone()
        
        reactions_json = json.dumps(analytics_data.get('reactions', {}))
        
        if existing:
            # Оновлюємо існуючий запис
            cursor.execute("""
                UPDATE analytics 
                SET likes = ?, comments = ?, shares = ?, 
                    impressions = ?, engaged_users = ?, clicks = ?,
                    reactions = ?, engagement_rate = ?,
                    text_length = ?, has_link = ?, has_images = ?, image_count = ?,
                    hour_of_day = ?, day_of_week = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE publication_id = ?
            """, (
                likes, comments, shares,
                impressions,
                analytics_data.get('engaged_users', 0),
                analytics_data.get('clicks', 0),
                reactions_json,
                engagement_rate,
                metadata.get('text_length', 0),
                metadata.get('has_link', False),
                metadata.get('has_images', False),
                metadata.get('image_count', 0),
                metadata.get('hour_of_day'),
                metadata.get('day_of_week'),
                publication_id
            ))
        else:
            # Створюємо новий запис
            cursor.execute("""
                INSERT INTO analytics 
                (publication_id, likes, comments, shares, impressions, 
                 engaged_users, clicks, reactions, engagement_rate,
                 text_length, has_link, has_images, image_count,
                 hour_of_day, day_of_week)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                publication_id,
                likes, comments, shares,
                impressions,
                analytics_data.get('engaged_users', 0),
                analytics_data.get('clicks', 0),
                reactions_json,
                engagement_rate,
                metadata.get('text_length', 0),
                metadata.get('has_link', False),
                metadata.get('has_images', False),
                metadata.get('image_count', 0),
                metadata.get('hour_of_day'),
                metadata.get('day_of_week')
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Аналітика збережена для публікації ID: {publication_id} (ER: {engagement_rate})")
    
    def get_analytics_by_post(self, post_id: int) -> List[Dict]:
        """Отримує аналітику для всіх публікацій поста"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.*, pub.page_name, pub.facebook_post_id
            FROM analytics a
            JOIN publications pub ON a.publication_id = pub.id
            WHERE pub.post_id = ?
        """, (post_id,))
        
        analytics = []
        for row in cursor.fetchall():
            item = dict(row)
            item['reactions'] = json.loads(item['reactions']) if item['reactions'] else {}
            analytics.append(item)
        
        conn.close()
        return analytics
    
    def get_best_performing_posts(self, metric: str = 'likes', limit: int = 10) -> List[Dict]:
        """
        Отримує найкращі пости за метрикою
        
        Args:
            metric: 'likes', 'comments', 'shares', 'impressions', 'engaged_users', 'engagement_rate'
            limit: кількість постів
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Валідація метрики
        valid_metrics = ['likes', 'comments', 'shares', 'impressions', 'engaged_users', 'clicks', 'engagement_rate']
        if metric not in valid_metrics:
            metric = 'engagement_rate'
        
        # Для engagement_rate використовуємо AVG, для інших SUM
        aggregate = 'AVG' if metric == 'engagement_rate' else 'SUM'
        
        query = f"""
            SELECT p.*, {aggregate}(a.{metric}) as total_{metric},
                   AVG(a.engagement_rate) as avg_engagement_rate
            FROM posts p
            JOIN publications pub ON p.id = pub.post_id
            JOIN analytics a ON pub.id = a.publication_id
            WHERE p.status = 'published'
            GROUP BY p.id
            ORDER BY total_{metric} DESC
            LIMIT ?
        """
        
        cursor.execute(query, (limit,))
        
        posts = []
        for row in cursor.fetchall():
            post = dict(row)
            # Парсимо image_urls
            if post.get('image_urls'):
                post['image_urls'] = json.loads(post['image_urls'])
            posts.append(post)
        
        conn.close()
        
        return posts
    
    def get_overall_statistics(self, user_id: Optional[int] = None) -> Dict:
        """
        Отримує загальну статистику по всіх постах

        Args:
            user_id: ID користувача (якщо None - вся статистика)

        Returns:
            Dict з загальною статистикою
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Фільтр по користувачу
        user_filter = "WHERE user_id = ?" if user_id else ""
        user_params = (user_id,) if user_id else ()

        # Загальна кількість постів
        cursor.execute(f"SELECT COUNT(*) as total FROM posts {user_filter}", user_params)
        total_posts = cursor.fetchone()['total']

        # Опубліковані пости
        cursor.execute(f"SELECT COUNT(*) as published FROM posts {user_filter} {'AND' if user_id else 'WHERE'} status = 'published'",
                      user_params)
        published = cursor.fetchone()['published']

        # Заплановані пости
        cursor.execute(f"SELECT COUNT(*) as scheduled FROM posts {user_filter} {'AND' if user_id else 'WHERE'} status = 'scheduled'",
                      user_params)
        scheduled = cursor.fetchone()['scheduled']

        # Чернетки
        cursor.execute(f"SELECT COUNT(*) as drafts FROM posts {user_filter} {'AND' if user_id else 'WHERE'} status = 'draft'",
                      user_params)
        drafts = cursor.fetchone()['drafts']

        # Загальна аналітика з фільтром по користувачу
        if user_id:
            cursor.execute("""
                SELECT
                    COALESCE(SUM(a.likes), 0) as total_likes,
                    COALESCE(SUM(a.comments), 0) as total_comments,
                    COALESCE(SUM(a.shares), 0) as total_shares,
                    COALESCE(SUM(a.impressions), 0) as total_impressions,
                    COALESCE(AVG(a.likes), 0) as avg_likes,
                    COALESCE(AVG(a.comments), 0) as avg_comments,
                    COALESCE(AVG(a.shares), 0) as avg_shares,
                    COALESCE(AVG(a.engagement_rate), 0) as avg_engagement_rate
                FROM analytics a
                JOIN publications pub ON a.publication_id = pub.id
                JOIN posts p ON pub.post_id = p.id
                WHERE p.user_id = ?
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT
                    COALESCE(SUM(likes), 0) as total_likes,
                    COALESCE(SUM(comments), 0) as total_comments,
                    COALESCE(SUM(shares), 0) as total_shares,
                    COALESCE(SUM(impressions), 0) as total_impressions,
                    COALESCE(AVG(likes), 0) as avg_likes,
                    COALESCE(AVG(comments), 0) as avg_comments,
                    COALESCE(AVG(shares), 0) as avg_shares,
                    COALESCE(AVG(engagement_rate), 0) as avg_engagement_rate
                FROM analytics
            """)
        analytics = dict(cursor.fetchone())

        # Кількість AI-згенерованих постів
        cursor.execute(f"SELECT COUNT(*) as ai_posts FROM posts {user_filter} {'AND' if user_id else 'WHERE'} is_ai_generated = 1",
                      user_params)
        ai_posts = cursor.fetchone()['ai_posts']

        conn.close()

        return {
            'total_posts': total_posts,
            'published_posts': published,
            'scheduled_posts': scheduled,
            'draft_posts': drafts,
            'ai_generated_posts': ai_posts,
            'total_likes': int(analytics['total_likes']),
            'total_comments': int(analytics['total_comments']),
            'total_shares': int(analytics['total_shares']),
            'total_impressions': int(analytics['total_impressions']),
            'avg_likes': round(analytics['avg_likes'], 2),
            'avg_comments': round(analytics['avg_comments'], 2),
            'avg_shares': round(analytics['avg_shares'], 2),
            'avg_engagement_rate': round(analytics['avg_engagement_rate'], 4)
        }
    
    def create_template(self, name: str, content: str, is_ai_prompt: bool = False,
                       based_on_recommendations: bool = False, recommendation_id: Optional[int] = None) -> int:
        """Створює шаблон поста"""
        if not name or len(name.strip()) == 0:
            raise ValueError("Назва шаблону не може бути пустою")

        if not content or len(content.strip()) == 0:
            raise ValueError("Контент шаблону не може бути пустим")

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO templates (name, content, is_ai_prompt, based_on_recommendations, recommendation_id)
            VALUES (?, ?, ?, ?, ?)
        """, (name, content, is_ai_prompt, based_on_recommendations, recommendation_id))

        template_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return template_id
    
    def get_templates(self) -> List[Dict]:
        """Отримує всі шаблони"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM templates ORDER BY created_at DESC")

        templates = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return templates

    def delete_template(self, template_id: int):
        """Видаляє шаблон"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))

        conn.commit()
        conn.close()

        logger.info(f"Шаблон ID {template_id} видалено")

    def delete_post(self, post_id: int):
        """Видаляє пост та всі пов'язані дані (CASCADE)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Завдяки CASCADE, достатньо видалити тільки пост
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Пост ID {post_id} видалено")
    
    def export_to_json(self, filename: str = "backup.json") -> str:
        """
        Експортує всі дані в JSON файл
        
        Args:
            filename: Назва файлу для експорту
            
        Returns:
            str: Шлях до створеного файлу
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        data = {
            'export_date': datetime.now().isoformat(),
            'posts': [],
            'publications': [],
            'analytics': [],
            'templates': []
        }
        
        # Експорт постів
        cursor.execute("SELECT * FROM posts")
        for row in cursor.fetchall():
            post = dict(row)
            if post.get('image_urls'):
                post['image_urls'] = json.loads(post['image_urls'])
            data['posts'].append(post)
        
        # Експорт публікацій
        cursor.execute("SELECT * FROM publications")
        data['publications'] = [dict(row) for row in cursor.fetchall()]
        
        # Експорт аналітики
        cursor.execute("SELECT * FROM analytics")
        data['analytics'] = [dict(row) for row in cursor.fetchall()]
        
        # Експорт шаблонів
        cursor.execute("SELECT * FROM templates")
        data['templates'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Дані експортовано в {filename}")
        return filename
    
    def get_posts_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Отримує пости за діапазоном дат
        
        Args:
            start_date: Початкова дата
            end_date: Кінцева дата
            
        Returns:
            List[Dict]: Список постів
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM posts 
            WHERE created_at BETWEEN ? AND ?
            ORDER BY created_at DESC
        """, (start_date, end_date))
        
        posts = []
        for row in cursor.fetchall():
            post = dict(row)
            if post.get('image_urls'):
                post['image_urls'] = json.loads(post['image_urls'])
            posts.append(post)
        
        conn.close()
        
        return posts
    
    def save_recommendation(self, period_start: datetime, period_end: datetime,
                           analyzed_posts_count: int, recommendations: Dict,
                           patterns: Dict, status: str = 'completed') -> int:
        """
        Зберігає AI рекомендацію в базу даних
        
        Args:
            period_start: початок аналізованого періоду
            period_end: кінець періоду
            analyzed_posts_count: кількість проаналізованих постів
            recommendations: словник з рекомендаціями
            patterns: словник з виявленими патернами
            status: статус ('pending', 'completed', 'failed')
        
        Returns:
            int: ID створеного запису
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        recommendations_json = json.dumps(recommendations, ensure_ascii=False)
        patterns_json = json.dumps(patterns, ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO ai_recommendations 
            (period_start, period_end, analyzed_posts_count, 
             recommendations_json, patterns_json, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (period_start, period_end, analyzed_posts_count,
              recommendations_json, patterns_json, status))
        
        recommendation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Рекомендація збережена ID: {recommendation_id}")
        return recommendation_id
    
    def get_latest_recommendation(self) -> Optional[Dict]:
        """
        Отримує останню актуальну рекомендацію
        
        Returns:
            Optional[Dict]: рекомендація або None
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM ai_recommendations 
            WHERE status = 'completed'
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            rec = dict(row)
            rec['recommendations'] = json.loads(rec['recommendations_json'])
            rec['patterns'] = json.loads(rec['patterns_json']) if rec.get('patterns_json') else {}
            return rec
        
        return None
    
    def get_recommendations_history(self, limit: int = 10) -> List[Dict]:
        """
        Отримує історію рекомендацій
        
        Args:
            limit: кількість записів
        
        Returns:
            List[Dict]: список рекомендацій
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM ai_recommendations 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        
        recommendations = []
        for row in cursor.fetchall():
            rec = dict(row)
            rec['recommendations'] = json.loads(rec['recommendations_json'])
            rec['patterns'] = json.loads(rec['patterns_json']) if rec.get('patterns_json') else {}
            recommendations.append(rec)
        
        conn.close()
        
        return recommendations
    
    def check_recent_recommendation(self, days: int = 7) -> bool:
        """
        Перевіряє чи була рекомендація за останні N днів
        
        Args:
            days: кількість днів для перевірки
        
        Returns:
            bool: True якщо є свіжа рекомендація
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM ai_recommendations 
            WHERE created_at >= ? AND status = 'completed'
        """, (cutoff_date,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['count'] > 0

    # === Методы для работы с пользователями ===

    def create_user(self, facebook_id: str, email: Optional[str] = None,
                    full_name: Optional[str] = None, profile_picture: Optional[str] = None) -> int:
        """Создает нового пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (facebook_id, email, full_name, profile_picture, last_login)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (facebook_id, email, full_name, profile_picture))

        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Створено користувача ID: {user_id}")
        return user_id

    def get_user_by_facebook_id(self, facebook_id: str) -> Optional[Dict]:
        """Получает пользователя по Facebook ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE facebook_id = ?", (facebook_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Получает пользователя по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def update_user_login(self, user_id: int):
        """Обновляет время последнего входа"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

    def add_user_facebook_page(self, user_id: int, page_id: str, page_name: str, access_token: str):
        """Добавляет Facebook страницу пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO user_facebook_pages (user_id, page_id, page_name, access_token)
            VALUES (?, ?, ?, ?)
        """, (user_id, page_id, page_name, access_token))

        conn.commit()
        conn.close()

    def get_user_facebook_pages(self, user_id: int) -> List[Dict]:
        """Получает все Facebook страницы пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM user_facebook_pages WHERE user_id = ?
        """, (user_id,))

        pages = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return pages

    def update_facebook_app_credentials(self, user_id: int, app_id: str, app_secret: str):
        """Обновляет Facebook App credentials пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users
            SET facebook_app_id = ?, facebook_app_secret = ?
            WHERE id = ?
        """, (app_id, app_secret, user_id))

        conn.commit()
        conn.close()
        logger.info(f"Оновлено FB App credentials для користувача {user_id}")

    def get_facebook_app_credentials(self, user_id: int) -> Optional[Dict]:
        """Получает Facebook App credentials пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT facebook_app_id, facebook_app_secret
            FROM users WHERE id = ?
        """, (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row and row['facebook_app_id'] and row['facebook_app_secret']:
            return {
                "app_id": row['facebook_app_id'],
                "app_secret": row['facebook_app_secret']
            }
        return None

    def update_user_facebook_token(self, user_id: int, access_token: str, expires_in: int):
        """
        Зберігає Facebook access token користувача

        Args:
            user_id: ID користувача
            access_token: long-lived токен
            expires_in: час життя токена в секундах
        """
        from datetime import timedelta

        expires_at = datetime.now() + timedelta(seconds=expires_in)

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET facebook_access_token = ?,
                facebook_token_expires_at = ?
            WHERE id = ?
        """, (access_token, expires_at.isoformat(), user_id))
        conn.commit()
        conn.close()

        logger.info(f"✓ Facebook токен збережено для користувача {user_id}")

    def get_user_facebook_token(self, user_id: int) -> Optional[Dict]:
        """
        Отримує Facebook токен користувача

        Returns:
            dict: {"token": "...", "expires_at": "..."}
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT facebook_access_token, facebook_token_expires_at
            FROM users
            WHERE id = ?
        """, (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row and row['facebook_access_token']:
            return {
                'token': row['facebook_access_token'],
                'expires_at': row['facebook_token_expires_at']
            }
        return None

    def clear_user_facebook_token(self, user_id: int):
        """Видаляє Facebook токен користувача"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users
            SET facebook_access_token = NULL,
                facebook_token_expires_at = NULL
            WHERE id = ?
        """, (user_id,))
        conn.commit()
        conn.close()

        logger.info(f"✓ Facebook токен видалено для користувача {user_id}")

# Глобальний екземпляр бази даних
db = Database()