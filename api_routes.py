"""
API маршрути для FastAPI сервера
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Header
from fastapi.responses import RedirectResponse, Response
from datetime import datetime
import logging
import asyncio
import os
import shutil
import uuid
import httpx
from typing import Optional

from database import db
from facebook_config import fb_config
from facebook_manager import FacebookManager
from facebook_analytics import get_post_analytics
from text_generator import generate_post_text
from api_models import (
    PostCreate, PostUpdate, AIGenerateRequest,
    TemplateCreate, TokenUpdate, PageAdd, UserLogin, FacebookAppCredentials
)
from auth_google import GoogleOAuth, JWTHandler
from auth_facebook import FacebookOAuth
import secrets

logger = logging.getLogger(__name__)

# Тимчасове сховище для OAuth state
oauth_states = {}

# Директорія для завантажень
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Створюємо роутер
router = APIRouter()


# ==================== DEPENDENCY: АВТОРИЗАЦИЯ ====================

async def get_current_user(authorization: Optional[str] = Header(None)) -> int:
    """
    Dependency для проверки авторизации
    Извлекает user_id из JWT токена

    Args:
        authorization: Header "Authorization: Bearer <token>"

    Returns:
        int: user_id

    Raises:
        HTTPException: Если не авторизован
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme"
            )

        payload = JWTHandler.decode_access_token(token)
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        return user_id

    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format"
        )


# ==================== АВТОРИЗАЦИЯ ====================

@router.get("/auth/google/login")
async def google_login():
    """Редирект на Google для авторизації"""
    login_url = GoogleOAuth.get_login_url()
    return RedirectResponse(url=login_url)


@router.get("/auth/google/callback")
async def google_callback(code: str):
    """Обробка відповіді від Google після авторизації"""
    try:
        # Обмінюємо code на access token
        access_token = await GoogleOAuth.exchange_code_for_token(code)

        # Отримуємо інформацію про користувача
        user_info = await GoogleOAuth.get_user_info(access_token)

        # Перевіряємо чи є користувач в БД (використовуємо google_id)
        user = db.get_user_by_facebook_id(user_info['google_id'])

        if user:
            # Оновлюємо час входу
            db.update_user_login(user['id'])
            user_id = user['id']
            logger.info(f"Користувач {user_id} увійшов в систему")
        else:
            # Створюємо нового користувача
            user_id = db.create_user(
                facebook_id=user_info['google_id'],
                email=user_info.get('email'),
                full_name=user_info.get('full_name'),
                profile_picture=user_info.get('profile_picture')
            )
            logger.info(f"Створено нового користувача {user_id}")

        # Створюємо JWT токен
        jwt_token = JWTHandler.create_access_token({"user_id": user_id})

        # Редирект на frontend з токеном
        return RedirectResponse(url=f"/?token={jwt_token}")

    except Exception as e:
        logger.error(f"Помилка авторизації: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/me")
async def get_current_user_info(user_id: int = Depends(get_current_user)):
    """Получает информацию о текущем пользователе"""
    try:
        user = db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Получаем страницы пользователя
        pages = db.get_user_facebook_pages(user_id)

        return {
            "success": True,
            "user": {
                "id": user['id'],
                "facebook_id": user['facebook_id'],
                "email": user.get('email'),
                "full_name": user.get('full_name'),
                "profile_picture": user.get('profile_picture'),
                "role": user.get('role'),
                "created_at": user.get('created_at'),
                "last_login": user.get('last_login')
            },
            "pages": pages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения данных пользователя: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/logout")
async def logout(user_id: int = Depends(get_current_user)):
    """Выход из системы"""
    return {"success": True, "message": "Logged out"}


@router.get("/auth/avatar-proxy")
async def avatar_proxy(url: str):
    """Проксирует Google аватары для обхода CORS"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                return Response(
                    content=response.content,
                    media_type=response.headers.get("content-type", "image/jpeg"),
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Access-Control-Allow-Origin": "*"
                    }
                )
            else:
                raise HTTPException(status_code=404, detail="Avatar not found")
    except Exception as e:
        logger.error(f"Error proxying avatar: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load avatar")


@router.get("/auth/facebook/login")
async def facebook_login(token: str = None):
    """Редирект користувача на Facebook для авторизації"""
    try:
        # Отримуємо user_id з токену
        if not token:
            raise HTTPException(status_code=401, detail="Token required")

        payload = JWTHandler.decode_access_token(token)
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Генеруємо унікальний state для безпеки
        state = secrets.token_urlsafe(32)
        oauth_states[state] = user_id

        # Отримуємо URL для редиректу
        login_url = FacebookOAuth.get_login_url(state)

        return RedirectResponse(url=login_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Facebook login error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/facebook/callback")
async def facebook_callback(code: str, state: str):
    """Обробка відповіді від Facebook після авторизації"""
    try:
        # Перевіряємо state
        user_id = oauth_states.pop(state, None)
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid state")

        # 1. Обмінюємо code на short-lived token
        short_token = await FacebookOAuth.exchange_code_for_token(code)

        # 2. Обмінюємо на long-lived token (60 днів)
        long_token_data = await FacebookOAuth.exchange_for_long_lived_token(short_token)

        # 3. Зберігаємо токен в базу
        db.update_user_facebook_token(
            user_id,
            long_token_data['token'],
            long_token_data['expires_in']
        )

        # 4. Отримуємо список Facebook Pages
        pages = await FacebookOAuth.get_user_pages(long_token_data['token'])

        # 5. Зберігаємо сторінки в базу
        for page in pages:
            db.add_user_facebook_page(
                user_id=user_id,
                page_id=page['id'],
                page_name=page['name'],
                access_token=page['access_token']
            )

        logger.info(f"✓ Facebook підключено для користувача {user_id}, сторінок: {len(pages)}")

        # 6. Редиректимо назад у фронтенд
        return RedirectResponse(url="http://localhost:8000/?facebook_connected=true")

    except Exception as e:
        logger.error(f"Facebook OAuth error: {str(e)}")
        return RedirectResponse(url="http://localhost:8000/?facebook_error=true")


@router.get("/auth/facebook/status")
async def facebook_status(user_id: int = Depends(get_current_user)):
    """Перевіряє чи підключений Facebook"""
    try:
        token_info = db.get_user_facebook_token(user_id)
        pages = db.get_user_facebook_pages(user_id)

        return {
            "connected": token_info is not None,
            "pages_count": len(pages),
            "expires_at": token_info['expires_at'] if token_info else None
        }
    except Exception as e:
        logger.error(f"Facebook status error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/facebook/disconnect")
async def facebook_disconnect(user_id: int = Depends(get_current_user)):
    """Відключає Facebook"""
    try:
        db.clear_user_facebook_token(user_id)
        return {"success": True, "message": "Facebook відключено"}
    except Exception as e:
        logger.error(f"Facebook disconnect error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/facebook/refresh-pages")
async def refresh_facebook_pages(user_id: int = Depends(get_current_user)):
    """Оновлює список Facebook Pages без повторної авторизації"""
    try:
        # Отримуємо існуючий токен користувача
        token_info = db.get_user_facebook_token(user_id)

        if not token_info:
            raise HTTPException(
                status_code=400,
                detail="Facebook не підключено. Спочатку підключіть свій акаунт."
            )

        # Перевіряємо чи не протух токен
        if token_info.get('expires_at'):
            expires_at = datetime.fromisoformat(token_info['expires_at'])
            if expires_at < datetime.now():
                raise HTTPException(
                    status_code=401,
                    detail="Токен протух. Будь ласка, підключіть Facebook заново."
                )

        # Отримуємо свіжий список сторінок з Facebook
        pages = await FacebookOAuth.get_user_pages(token_info['token'])

        # Видаляємо старі сторінки користувача
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_facebook_pages WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        # Зберігаємо нові сторінки
        for page in pages:
            db.add_user_facebook_page(
                user_id=user_id,
                page_id=page['id'],
                page_name=page['name'],
                access_token=page['access_token']
            )

        logger.info(f"✓ Оновлено список сторінок для користувача {user_id}: {len(pages)} сторінок")

        return {
            "success": True,
            "message": f"Оновлено {len(pages)} сторінок",
            "pages_count": len(pages)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Facebook refresh pages error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ЗАВАНТАЖЕННЯ ЗОБРАЖЕНЬ ====================

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """Завантажує зображення на сервер"""
    try:
        # Перевірка типу файлу
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Файл має бути зображенням")

        # Генеруємо унікальне ім'я
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # Зберігаємо файл
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Повертаємо URL
        file_url = f"/uploads/{unique_filename}"

        logger.info(f"✓ Зображення завантажено: {file_url}")

        return {
            "success": True,
            "url": file_url,
            "filename": unique_filename
        }

    except Exception as e:
        logger.error(f"Помилка завантаження зображення: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-image/{filename}")
async def delete_image(filename: str):
    """Видаляє зображення з сервера"""
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)

        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"✓ Зображення видалено: {filename}")
            return {"success": True}
        else:
            raise HTTPException(status_code=404, detail="Файл не знайдено")

    except Exception as e:
        logger.error(f"Помилка видалення зображення: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ПОСТИ ====================

@router.get("/posts")
async def get_posts(limit: int = 50, offset: int = 0, user_id: int = Depends(get_current_user)):
    """Отримує список постів користувача"""
    try:
        posts = db.get_all_posts(limit=limit, offset=offset, user_id=user_id)
        return {"success": True, "posts": posts}
    except Exception as e:
        logger.error(f"Помилка отримання постів: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/posts/{post_id}")
async def get_post(post_id: int, user_id: int = Depends(get_current_user)):
    """Отримує деталі поста"""
    try:
        post = db.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Пост не знайдено")

        # Проверка прав доступа
        if post.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        # Отримуємо публікації
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM publications WHERE post_id = ?", (post_id,))
        publications = [dict(row) for row in cursor.fetchall()]
        conn.close()

        post['publications'] = publications

        # Отримуємо аналітику якщо опубліковано
        if post['status'] == 'published':
            analytics = db.get_analytics_by_post(post_id)
            post['analytics'] = analytics

        return {"success": True, "post": post}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Помилка отримання поста: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/posts")
async def create_post(data: PostCreate, user_id: int = Depends(get_current_user)):
    """Створює новий пост"""
    try:
        # Парсимо час якщо є
        scheduled_time = None
        if data.scheduled_time:
            scheduled_time = datetime.fromisoformat(data.scheduled_time.replace('Z', '+00:00'))

        # Створюємо пост з URLs зображень та user_id
        post_id = db.create_post(
            content=data.content,
            link=data.link,
            is_ai_generated=data.is_ai_generated,
            ai_prompt=data.ai_prompt,
            scheduled_time=scheduled_time,
            image_urls=data.image_urls,
            user_id=user_id
        )

        # Получаем страницы пользователя из БД
        user_pages = db.get_user_facebook_pages(user_id)

        # Додаємо публікації для кожної сторінки користувача
        for page_id in data.page_ids:
            page = next((p for p in user_pages if p['page_id'] == page_id), None)
            if page:
                db.add_publication(post_id, page['page_id'], page['page_name'], user_id)

        # Встановлюємо статус
        if scheduled_time:
            db.update_post_status(post_id, 'scheduled')
        else:
            db.update_post_status(post_id, 'draft')

        return {"success": True, "post_id": post_id}
    except Exception as e:
        logger.error(f"Помилка створення поста: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/posts/{post_id}")
async def update_post(post_id: int, data: PostUpdate, user_id: int = Depends(get_current_user)):
    """Оновлює пост"""
    try:
        post = db.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Пост не знайдено")

        # Проверка прав доступа
        if post.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        conn = db.get_connection()
        cursor = conn.cursor()

        updates = []
        values = []

        if data.content is not None:
            updates.append("content = ?")
            values.append(data.content)

        if data.link is not None:
            updates.append("link = ?")
            values.append(data.link)

        if data.scheduled_time is not None:
            scheduled_time = datetime.fromisoformat(data.scheduled_time.replace('Z', '+00:00'))
            updates.append("scheduled_time = ?")
            values.append(scheduled_time)

        if updates:
            values.append(post_id)
            query = f"UPDATE posts SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()

        conn.close()

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Помилка оновлення поста: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/posts/{post_id}")
async def delete_post(post_id: int, user_id: int = Depends(get_current_user)):
    """Видаляє пост з бази даних та з Facebook"""
    try:
        # Отримуємо інформацію про пост та його публікації
        post = db.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Пост не знайдено")

        # Проверка прав доступа
        if post.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        # Отримуємо всі публікації поста
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM publications WHERE post_id = ?
        """, (post_id,))
        publications = [dict(row) for row in cursor.fetchall()]
        conn.close()

        # Получаем страницы пользователя из БД
        user_pages = db.get_user_facebook_pages(user_id)

        # Видаляємо пости з Facebook для кожної публікації
        deleted_count = 0
        failed_count = 0

        for pub in publications:
            if pub['facebook_post_id'] and pub['status'] == 'published':
                # Знаходимо токен сторінки пользователя
                page_token = None
                for page in user_pages:
                    if page['page_id'] == pub['page_id']:
                        page_token = page['access_token']
                        break

                if page_token:
                    try:
                        # Создаем временный токен для удаления
                        fb_manager = FacebookManager(page_token)

                        # Видаляємо пост з Facebook
                        success = fb_manager.delete_post(pub['facebook_post_id'], page_token)

                        if success:
                            deleted_count += 1
                            logger.info(f"✓ Пост {pub['facebook_post_id']} видалено з Facebook (сторінка: {pub['page_name']})")
                        else:
                            failed_count += 1
                            logger.warning(f"✗ Не вдалося видалити пост {pub['facebook_post_id']} з Facebook")
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"✗ Помилка видалення поста {pub['facebook_post_id']} з Facebook: {str(e)}")
                else:
                    logger.warning(f"⚠ Токен для сторінки {pub['page_id']} не знайдено")

        # Видаляємо пост з бази даних (CASCADE видалить всі пов'язані записи)
        db.delete_post(post_id)

        # Формуємо повідомлення про результат
        message_parts = ["Пост видалено з бази даних"]
        if deleted_count > 0:
            message_parts.append(f"видалено з Facebook: {deleted_count}")
        if failed_count > 0:
            message_parts.append(f"не вдалося видалити з Facebook: {failed_count}")

        message = " | ".join(message_parts)

        return {
            "success": True,
            "message": message,
            "deleted_from_facebook": deleted_count,
            "failed_deletions": failed_count
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Помилка видалення поста: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/posts/{post_id}/publish")
async def publish_post_now(post_id: int, user_id: int = Depends(get_current_user)):
    """Публікує пост негайно"""
    try:
        post = db.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Пост не знайдено")

        # Проверка прав доступа
        if post.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        # Отримуємо публікації
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM publications
            WHERE post_id = ? AND status = 'pending'
        """, (post_id,))
        publications = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not publications:
            raise HTTPException(status_code=400, detail="Немає сторінок для публікації")

        # Получаем страницы пользователя
        user_pages = db.get_user_facebook_pages(user_id)

        results = []

        # Перевіряємо чи є зображення
        image_urls = post.get('image_urls', [])
        has_images = image_urls and len(image_urls) > 0

        for pub in publications:
            # Находим токен страницы пользователя
            page_token = None
            for page in user_pages:
                if page['page_id'] == pub['page_id']:
                    page_token = page['access_token']
                    break

            if not page_token:
                results.append({"page": pub['page_name'], "success": False, "error": "Токен не знайдено"})
                continue

            fb_manager = FacebookManager(page_token)

            # Конвертуємо URLs в локальні шляхи
            if has_images:
                image_paths = []
                for url in image_urls:
                    if url.startswith('/uploads/'):
                        # Конвертуємо відносний URL в локальний шлях
                        local_path = url.replace('/uploads/', 'uploads/')
                        image_paths.append(local_path)
                    else:
                        # Якщо це повний URL, пропускаємо
                        logger.warning(f"Пропускаємо не-локальний URL: {url}")

                # Публікуємо з зображеннями (локальні файли)
                result = await asyncio.to_thread(
                    fb_manager.publish_post_with_images,
                    page_id=pub['page_id'],
                    page_token=page_token,
                    message=post['content'],
                    image_paths=image_paths,
                    link=post.get('link')
                )
            else:
                # Публікуємо без зображень
                result = await asyncio.to_thread(
                    fb_manager.publish_post,
                    page_id=pub['page_id'],
                    page_token=page_token,
                    message=post['content'],
                    link=post.get('link')
                )


            if result['success']:
                db.update_publication_status(pub['id'], 'published', result['post_id'])

                # Збираємо початкову аналітику
                try:
                    initial_analytics = await asyncio.to_thread(
                        get_post_analytics,
                        post_id=result['post_id'],
                        page_token=page_token
                    )

                    if initial_analytics.get('success'):
                        db.save_analytics(pub['id'], initial_analytics)
                        logger.info(f"Початкова аналітика збережена для поста {result['post_id']}")
                except Exception as e:
                    logger.warning(f"Не вдалося зібрати початкову аналітику: {str(e)}")

                results.append({"page": pub['page_name'], "success": True, "post_id": result['post_id']})
            else:
                db.update_publication_status(pub['id'], 'failed', error_message=result.get('error'))
                results.append({"page": pub['page_name'], "success": False, "error": result.get('error')})

        # Оновлюємо статус поста
        db.update_post_status(post_id, 'published')

        return {"success": True, "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Помилка публікації: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AI ГЕНЕРАЦІЯ ====================

@router.post("/generate")
async def generate_text(data: AIGenerateRequest):
    """Генерує текст за допомогою AI з урахуванням рекомендацій"""
    try:
        # Визначаємо мову промпту
        lang = data.lang if hasattr(data, 'lang') else 'uk'

        # Адаптуємо промпт для мови
        prompt = data.prompt
        if lang == 'en' and not any(word in prompt.lower() for word in ['write', 'create', 'generate']):
            # Якщо мова англійська, але промпт не містить англійських слів - додаємо вказівку
            prompt = f"Write in English: {prompt}"

        text = await generate_post_text(
            prompt=prompt,
            min_length=data.min_length,
            max_length=data.max_length,
            use_recommendations=data.use_recommendations,
            lang=lang
        )
        return {"success": True, "text": text}
    except Exception as e:
        logger.error(f"Помилка генерації: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== СТОРІНКИ ====================

@router.post("/config/token")
async def update_access_token(data: TokenUpdate):
    """Оновлює user access token і обмінює на long-lived"""
    try:
        # Якщо передані app_id і app_secret - зберігаємо
        if data.app_id and data.app_secret:
            fb_config.config['app_id'] = data.app_id
            fb_config.config['app_secret'] = data.app_secret

        # Зберігаємо токен (автоматично обмінюємо на long-lived якщо є app credentials)
        fb_config.set_credentials(
            fb_config.config.get('app_id', ''),
            fb_config.config.get('app_secret', ''),
            data.access_token,
            auto_exchange=True
        )

        # Отримуємо інфо про токен
        token_info = fb_config.get_token_info()

        return {
            "success": True,
            "message": "Токен збережено",
            "token_info": token_info
        }
    except Exception as e:
        logger.error(f"Помилка збереження токену: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/token-info")
async def get_token_info():
    """Отримує інформацію про поточний токен"""
    try:
        token_info = fb_config.get_token_info()
        return {
            "success": True,
            "token_info": token_info
        }
    except Exception as e:
        logger.error(f"Помилка отримання інфо токена: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pages")
async def get_pages(user_id: int = Depends(get_current_user)):
    """Отримує список сторінок користувача"""
    try:
        pages = db.get_user_facebook_pages(user_id)
        return {"success": True, "pages": pages}
    except Exception as e:
        logger.error(f"Помилка отримання сторінок: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pages/add")
async def add_page_manually(data: PageAdd, user_id: int = Depends(get_current_user)):
    """Додає сторінку вручну"""
    try:
        # Добавляем страницу в БД для текущего пользователя
        db.add_user_facebook_page(
            user_id=user_id,
            page_id=data.page_id,
            page_name=data.page_name,
            access_token=data.page_token
        )
        logger.info(f"Користувач {user_id} додав сторінку {data.page_name}")
        return {"success": True, "message": "Сторінку додано"}
    except Exception as e:
        logger.error(f"Помилка додавання сторінки: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/pages/{page_id}")
async def remove_page(page_id: str, user_id: int = Depends(get_current_user)):
    """Видаляє сторінку"""
    try:
        # Удаляем страницу из БД для текущего пользователя
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM user_facebook_pages
            WHERE user_id = ? AND page_id = ?
        """, (user_id, page_id))
        conn.commit()
        conn.close()

        logger.info(f"Користувач {user_id} видалив сторінку {page_id}")
        return {"success": True, "message": "Сторінку видалено"}
    except Exception as e:
        logger.error(f"Помилка видалення сторінки: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pages/refresh")
async def refresh_pages():
    """Оновлює список сторінок з Facebook"""
    try:
        user_token = fb_config.config.get('access_token', '')
        if not user_token:
            raise HTTPException(status_code=400, detail="Токен доступу не налаштовано")

        fb_manager = FacebookManager(user_token)
        pages = fb_manager.get_user_pages()

        if not pages:
            raise HTTPException(status_code=500, detail="Не вдалося отримати сторінки")

        # Оновлюємо конфігурацію
        fb_config.config["pages"] = []
        for page in pages:
            fb_config.add_page(page['id'], page['name'], page['access_token'])

        return {"success": True, "pages": pages}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Помилка оновлення сторінок: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== АНАЛІТИКА ====================

@router.post("/analytics/collect")
async def collect_analytics(user_id: int = Depends(get_current_user)):
    """Збирає аналітику для всіх опублікованих постів користувача"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT pub.id, pub.facebook_post_id, pub.page_id
            FROM publications pub
            JOIN posts p ON pub.post_id = p.id
            WHERE pub.status = 'published'
            AND pub.facebook_post_id IS NOT NULL
            AND pub.user_id = ?
        """, (user_id,))

        publications = [dict(row) for row in cursor.fetchall()]
        conn.close()

        success_count = 0
        error_count = 0

        # Получаем страницы пользователя
        user_pages = db.get_user_facebook_pages(user_id)

        for pub in publications:
            try:
                # Находим токен страницы пользователя
                page_token = None
                for page in user_pages:
                    if page['page_id'] == pub['page_id']:
                        page_token = page['access_token']
                        break

                if not page_token:
                    error_count += 1
                    continue

                analytics = await asyncio.to_thread(
                    get_post_analytics,
                    post_id=pub['facebook_post_id'],
                    page_token=page_token
                )

                if analytics.get('success'):
                    db.save_analytics(pub['id'], analytics)
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Помилка збору аналітики: {str(e)}")
                error_count += 1

        return {
            "success": True,
            "collected": success_count,
            "errors": error_count
        }
    except Exception as e:
        logger.error(f"Помилка збору аналітики: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analytics/collect/{post_id}")
async def collect_post_analytics(post_id: int, user_id: int = Depends(get_current_user)):
    """Збирає аналітику для конкретного поста"""
    try:
        post = db.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Пост не знайдено")

        # Проверка прав доступа
        if post.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT pub.id, pub.facebook_post_id, pub.page_id
            FROM publications pub
            WHERE pub.post_id = ?
            AND pub.status = 'published'
            AND pub.facebook_post_id IS NOT NULL
        """, (post_id,))

        publications = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not publications:
            raise HTTPException(status_code=400, detail="Немає опублікованих публікацій")

        # Получаем страницы пользователя
        user_pages = db.get_user_facebook_pages(user_id)

        success_count = 0
        error_count = 0
        results = []

        for pub in publications:
            try:
                # Находим токен страницы пользователя
                page_token = None
                for page in user_pages:
                    if page['page_id'] == pub['page_id']:
                        page_token = page['access_token']
                        break

                if not page_token:
                    error_count += 1
                    results.append({
                        "publication_id": pub['id'],
                        "success": False,
                        "error": "Не знайдено токен"
                    })
                    continue

                analytics = await asyncio.to_thread(
                    get_post_analytics,
                    post_id=pub['facebook_post_id'],
                    page_token=page_token
                )

                if analytics.get('success'):
                    db.save_analytics(pub['id'], analytics)
                    success_count += 1
                    results.append({
                        "publication_id": pub['id'],
                        "success": True,
                        "likes": analytics.get('likes', 0),
                        "comments": analytics.get('comments', 0),
                        "shares": analytics.get('shares', 0)
                    })
                else:
                    error_count += 1
                    results.append({
                        "publication_id": pub['id'],
                        "success": False,
                        "error": analytics.get('error', 'Невідома помилка')
                    })

            except Exception as e:
                logger.error(f"Помилка збору аналітики для публікації {pub['id']}: {str(e)}")
                error_count += 1
                results.append({
                    "publication_id": pub['id'],
                    "success": False,
                    "error": str(e)
                })

        return {
            "success": True,
            "collected": success_count,
            "errors": error_count,
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Помилка збору аналітики поста: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/post/{post_id}")
async def get_post_analytics_data(post_id: int, user_id: int = Depends(get_current_user)):
    """Отримує аналітику для конкретного поста"""
    try:
        post = db.get_post_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Пост не знайдено")

        # Проверка прав доступа
        if post.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        analytics = db.get_analytics_by_post(post_id)

        # Підраховуємо загальну статистику
        total = {
            "likes": sum(a.get('likes', 0) for a in analytics),
            "comments": sum(a.get('comments', 0) for a in analytics),
            "shares": sum(a.get('shares', 0) for a in analytics),
            "impressions": sum(a.get('impressions', 0) for a in analytics),
            "engaged_users": sum(a.get('engaged_users', 0) for a in analytics),
            "clicks": sum(a.get('clicks', 0) for a in analytics)
        }

        return {
            "success": True,
            "post": post,
            "analytics": analytics,
            "total": total
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Помилка отримання аналітики: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analytics/refresh-all")
async def refresh_all_analytics():
    """Оновлює аналітику для всіх опублікованих постів (без обмеження за датою)"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # ВИПРАВЛЕНИЙ ЗАПИТ - без фільтра по датах, сортування по pub.published_at
        cursor.execute("""
            SELECT DISTINCT pub.id, pub.facebook_post_id, pub.page_id, p.id as post_id
            FROM publications pub
            JOIN posts p ON pub.post_id = p.id
            WHERE pub.status = 'published'
            AND pub.facebook_post_id IS NOT NULL
            AND pub.facebook_post_id != ''
            ORDER BY pub.published_at DESC
            LIMIT 100
        """)

        publications = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not publications:
            return {
                "success": True,
                "message": "Немає опублікованих постів для оновлення",
                "collected": 0,
                "errors": 0,
                "total": 0
            }

        logger.info(f"Оновлення аналітики для {len(publications)} публікацій")

        success_count = 0
        error_count = 0

        for i, pub in enumerate(publications, 1):
            try:
                # Показуємо прогрес кожні 10 постів
                if i % 10 == 0:
                    logger.info(f"Оброблено {i}/{len(publications)}...")

                page_token = fb_config.get_page_token(pub['page_id'])
                if not page_token:
                    logger.warning(f"Немає токена для сторінки {pub['page_id']}")
                    error_count += 1
                    continue

                analytics = await asyncio.to_thread(
                    get_post_analytics,
                    post_id=pub['facebook_post_id'],
                    page_token=page_token
                )

                if analytics.get('success'):
                    db.save_analytics(pub['id'], analytics)
                    success_count += 1
                    logger.debug(
                        f"✓ Публікація {pub['id']}: "
                        f"👍{analytics.get('likes', 0)} "
                        f"💬{analytics.get('comments', 0)} "
                        f"🔄{analytics.get('shares', 0)}"
                    )

                    # Затримка між запитами
                    await asyncio.sleep(0.5)
                else:
                    error_count += 1
                    logger.warning(f"Не вдалося отримати аналітику для {pub['id']}: {analytics.get('error')}")

            except Exception as e:
                logger.error(f"Помилка для публікації {pub['id']}: {str(e)}")
                error_count += 1

        message = f"Оновлено аналітику для {success_count} з {len(publications)} публікацій"
        logger.info(f"✓ {message}. Помилок: {error_count}")

        return {
            "success": True,
            "message": message,
            "collected": success_count,
            "errors": error_count,
            "total": len(publications)
        }

    except Exception as e:
        logger.error(f"Помилка оновлення аналітики: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analytics/collect-recent")
async def collect_recent_analytics():
    """Оновлює аналітику тільки для свіжих постів (за останні 7 днів)"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Запит тільки для свіжих постів
        cursor.execute("""
            SELECT DISTINCT pub.id, pub.facebook_post_id, pub.page_id, p.id as post_id
            FROM publications pub
            JOIN posts p ON pub.post_id = p.id
            WHERE pub.status = 'published'
            AND pub.facebook_post_id IS NOT NULL
            AND pub.facebook_post_id != ''
            AND pub.published_at > datetime('now', '-7 days')
            ORDER BY pub.published_at DESC
        """)

        publications = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not publications:
            return {
                "success": True,
                "message": "Немає свіжих постів за останні 7 днів",
                "collected": 0,
                "errors": 0,
                "total": 0
            }

        logger.info(f"Оновлення аналітики для {len(publications)} свіжих публікацій")

        success_count = 0
        error_count = 0

        for pub in publications:
            try:
                page_token = fb_config.get_page_token(pub['page_id'])
                if not page_token:
                    error_count += 1
                    continue

                analytics = await asyncio.to_thread(
                    get_post_analytics,
                    post_id=pub['facebook_post_id'],
                    page_token=page_token
                )

                if analytics.get('success'):
                    db.save_analytics(pub['id'], analytics)
                    success_count += 1
                    await asyncio.sleep(0.5)
                else:
                    error_count += 1

            except Exception as e:
                logger.error(f"Помилка: {str(e)}")
                error_count += 1

        message = f"Оновлено {success_count} свіжих публікацій"

        return {
            "success": True,
            "message": message,
            "collected": success_count,
            "errors": error_count,
            "total": len(publications)
        }

    except Exception as e:
        logger.error(f"Помилка оновлення: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/summary")
async def get_analytics_summary(user_id: int = Depends(get_current_user)):
    """Отримує зведену аналітику користувача"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Загальна статистика
        cursor.execute("""
            SELECT
                COUNT(DISTINCT p.id) as total_posts,
                COALESCE(SUM(a.likes), 0) as total_likes,
                COALESCE(SUM(a.comments), 0) as total_comments,
                COALESCE(SUM(a.shares), 0) as total_shares,
                COALESCE(SUM(a.impressions), 0) as total_impressions,
                COALESCE(AVG(a.engagement_rate), 0) as avg_engagement_rate
            FROM posts p
            JOIN publications pub ON p.id = pub.post_id
            LEFT JOIN analytics a ON pub.id = a.publication_id
            WHERE p.status = 'published'
            AND p.user_id = ?
        """, (user_id,))

        summary = dict(cursor.fetchone())

        # Найкращі пости з усіма необхідними полями (використовуємо published_at з publications)
        cursor.execute("""
            SELECT
                p.id,
                p.content,
                COALESCE(pub.published_at, p.published_at) as published_at,
                p.is_ai_generated,
                p.image_urls,
                COALESCE(SUM(a.likes), 0) as total_likes,
                COALESCE(SUM(a.comments), 0) as total_comments,
                COALESCE(SUM(a.shares), 0) as total_shares,
                COALESCE(SUM(a.impressions), 0) as total_impressions,
                COALESCE(AVG(a.engagement_rate), 0) as avg_engagement_rate
            FROM posts p
            JOIN publications pub ON p.id = pub.post_id
            LEFT JOIN analytics a ON pub.id = a.publication_id
            WHERE pub.status = 'published'
            AND p.user_id = ?
            GROUP BY p.id
            HAVING (total_likes + total_comments + total_shares) > 0
            ORDER BY avg_engagement_rate DESC, total_likes DESC
            LIMIT 10
        """, (user_id,))

        best_posts = [dict(row) for row in cursor.fetchall()]

        conn.close()

        logger.info(f"Analytics summary: {summary}")

        return {
            "success": True,
            "summary": summary,
            "best_posts": best_posts
        }
    except Exception as e:
        logger.error(f"Помилка отримання аналітики: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== РЕКОМЕНДАЦІЇ ====================

@router.get("/recommendations/latest")
async def get_latest_recommendation():
    """Отримує останню актуальну рекомендацію"""
    try:
        recommendation = db.get_latest_recommendation()

        if not recommendation:
            return {
                "success": True,
                "recommendation": None,
                "message": "Немає доступних рекомендацій"
            }

        return {
            "success": True,
            "recommendation": recommendation
        }
    except Exception as e:
        logger.error(f"Помилка отримання рекомендації: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/history")
async def get_recommendations_history(limit: int = 10):
    """Отримує історію рекомендацій"""
    try:
        recommendations = db.get_recommendations_history(limit=limit)

        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    except Exception as e:
        logger.error(f"Помилка отримання історії рекомендацій: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations/generate")
async def generate_recommendations(period_days: int = 7, limit: int = 10):
    """Ручний запуск генерації рекомендацій"""
    try:
        from analytics_recommender import recommender

        logger.info(f"Запуск генерації рекомендацій за {period_days} днів...")

        # Виконуємо повний аналіз
        result = await asyncio.to_thread(
            recommender.get_full_analysis,
            period_days=period_days,
            limit=limit,
            use_ai=True
        )

        if result['success']:
            return {
                "success": True,
                "message": f"Рекомендації згенеровано на основі {result['analyzed_count']} постів",
                "recommendations": result['recommendations'],
                "patterns": result['patterns'],
                "analyzed_count": result['analyzed_count']
            }
        else:
            return {
                "success": False,
                "message": result.get('message', 'Помилка генерації рекомендацій')
            }

    except Exception as e:
        logger.error(f"Помилка генерації рекомендацій: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/top-posts")
async def get_top_posts(days: int = 7, limit: int = 10, metric: str = 'engagement_rate'):
    """Отримує топ-пости за період"""
    try:
        from analytics_recommender import recommender

        # Валідація метрики
        valid_metrics = ['engagement_rate', 'likes', 'comments', 'shares', 'impressions']
        if metric not in valid_metrics:
            metric = 'engagement_rate'

        # Отримуємо топ-пости
        top_posts = await asyncio.to_thread(
            recommender.get_top_posts,
            period_days=days,
            limit=limit,
            metric=metric
        )

        return {
            "success": True,
            "posts": top_posts,
            "count": len(top_posts),
            "period_days": days,
            "metric": metric
        }
    except Exception as e:
        logger.error(f"Помилка отримання топ-постів: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ШАБЛОНИ ====================

@router.get("/templates")
async def get_templates():
    """Отримує всі шаблони"""
    try:
        templates = db.get_templates()
        return {"success": True, "templates": templates}
    except Exception as e:
        logger.error(f"Помилка отримання шаблонів: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates")
async def create_template(data: TemplateCreate):
    """Створює новий шаблон"""
    try:
        template_id = db.create_template(
            name=data.name,
            content=data.content,
            is_ai_prompt=data.is_ai_prompt,
            based_on_recommendations=data.based_on_recommendations,
            recommendation_id=data.recommendation_id
        )
        return {"success": True, "template_id": template_id}
    except Exception as e:
        logger.error(f"Помилка створення шаблону: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/templates/{template_id}")
async def delete_template(template_id: int):
    """Видаляє шаблон"""
    try:
        db.delete_template(template_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Помилка видалення шаблону: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/generate-from-recommendations")
async def generate_templates_from_recommendations():
    """Авто-генерація шаблонів на основі рекомендацій"""
    try:
        # Отримуємо останні рекомендації
        recommendation = db.get_latest_recommendation()

        if not recommendation:
            return {
                "success": False,
                "message": "Немає доступних рекомендацій для генерації шаблонів"
            }

        rec_id = recommendation['id']
        rec_data = recommendation['recommendations']

        # Генеруємо 3-5 шаблонів з різними темами
        topics = rec_data.get('ai_insights', {}).get('effective_topics', [])
        if not topics:
            topics = ['Мотивація', 'Поради', 'Новини']

        templates_created = []

        for i, topic in enumerate(topics[:3], 1):
            # Генеруємо текст шаблону з урахуванням рекомендацій
            from text_generator import generate_post_text

            prompt = f"Створи шаблон поста на тему: {topic}"
            content = await generate_post_text(
                prompt=prompt,
                min_length=rec_data['text_length']['min'],
                max_length=rec_data['text_length']['max'],
                use_recommendations=True
            )

            # Створюємо шаблон як AI промпт
            template_name = f"AI Шаблон: {topic}"
            template_id = db.create_template(
                name=template_name,
                content=prompt,
                is_ai_prompt=True,
                based_on_recommendations=True,
                recommendation_id=rec_id
            )

            templates_created.append({
                'id': template_id,
                'name': template_name,
                'topic': topic
            })

            logger.info(f"Створено шаблон #{template_id}: {template_name}")

        return {
            "success": True,
            "message": f"Створено {len(templates_created)} шаблонів на основі рекомендацій",
            "templates": templates_created
        }

    except Exception as e:
        logger.error(f"Помилка генерації шаблонів: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
