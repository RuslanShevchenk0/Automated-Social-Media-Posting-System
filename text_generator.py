"""
Генератор текстів для постів у Facebook
+ AI-аналіз успішних постів для рекомендацій
"""

import asyncio
import logging
import json
from typing import List, Dict
from g4f.client import Client
from g4f.Provider import DeepInfra

logger = logging.getLogger(__name__)

async def generate_post_text(prompt: str, min_length: int = 50, max_length: int = 500,
                            max_retries: int = 3, use_recommendations: bool = True, lang: str = None) -> str:
    """
    Генерує текст поста на основі промпту з урахуванням рекомендацій

    Args:
        prompt: тема або промпт для генерації
        min_length: мінімальна довжина тексту
        max_length: максимальна довжина тексту
        max_retries: кількість спроб
        use_recommendations: використовувати рекомендації AI
        lang: мова ('en' або 'uk'), якщо None - визначається автоматично

    Returns:
        str: згенерований текст
    """

    # Визначаємо мову
    if lang:
        is_english = (lang == 'en')
    else:
        # Автоматичне визначення з промпту
        is_english = any(word in prompt.lower() for word in ['write', 'create', 'generate', 'make', 'style', 'tone', 'topics']) if prompt else False

    # Якщо промпт порожній, генеруємо випадкову тему
    if not prompt or prompt.strip() == "":
        prompt = "Write a motivational post for social media" if is_english else "Напиши мотиваційний пост для соціальних мереж"

    # Базовий system prompt залежно від мови
    if is_english:
        system_content = f"You are a text generator for Facebook posts in English. Write meaningful posts with length from {min_length} to {max_length} characters."
    else:
        system_content = f"Ти - генератор текстів для постів у Facebook українською мовою. Пиши змістовні пости довжиною від {min_length} до {max_length} символів."

    # Якщо ввімкнено рекомендації, завантажуємо та додаємо їх
    if use_recommendations:
        try:
            from database import db
            recommendation = db.get_latest_recommendation()

            if recommendation and recommendation.get('recommendations'):
                rec = recommendation['recommendations']

                # Додаємо інформацію з рекомендацій до system prompt
                if is_english:
                    system_content += "\n\n📊 Recommendations based on analysis of most successful posts:"
                else:
                    system_content += "\n\n📊 Рекомендації на основі аналізу найуспішніших постів:"

                # Стиль контенту
                if rec.get('ai_insights') and rec['ai_insights'].get('content_style'):
                    label = "Style" if is_english else "Стиль"
                    system_content += f"\n• {label}: {rec['ai_insights']['content_style']}"

                # Тон
                if rec.get('ai_insights') and rec['ai_insights'].get('tone'):
                    label = "Tone" if is_english else "Тон"
                    system_content += f"\n• {label}: {rec['ai_insights']['tone']}"

                # Ефективні теми
                if rec.get('ai_insights') and rec['ai_insights'].get('effective_topics'):
                    topics = ', '.join(rec['ai_insights']['effective_topics'][:3])
                    label = "Effective topics" if is_english else "Ефективні теми"
                    system_content += f"\n• {label}: {topics}"

                # Ключові фрази
                if rec.get('ai_insights') and rec['ai_insights'].get('key_phrases'):
                    phrases = ', '.join(rec['ai_insights']['key_phrases'][:5])
                    label = "Key phrases" if is_english else "Ключові фрази"
                    system_content += f"\n• {label}: {phrases}"

                # Структура
                if rec.get('ai_insights') and rec['ai_insights'].get('structure_tips'):
                    label = "Structure" if is_english else "Структура"
                    system_content += f"\n• {label}: {rec['ai_insights']['structure_tips']}"

                # Емоджі
                if rec.get('ai_insights') and rec['ai_insights'].get('emoji_usage'):
                    label = "Emoji" if is_english else "Емоджі"
                    system_content += f"\n• {label}: {rec['ai_insights']['emoji_usage']}"

                # Заклики до дії
                if rec.get('ai_insights') and rec['ai_insights'].get('call_to_action'):
                    label = "Call to action" if is_english else "Заклики до дії"
                    system_content += f"\n• {label}: {rec['ai_insights']['call_to_action']}"

                # Довжина тексту з рекомендацій
                if rec.get('text_length'):
                    rec_min = rec['text_length']['min']
                    rec_max = rec['text_length']['max']
                    label = "Optimal length" if is_english else "Оптимальна довжина"
                    chars = "characters" if is_english else "символів"
                    system_content += f"\n• {label}: {rec_min}-{rec_max} {chars}"

                logger.info("✓ Рекомендації додано до промпту для генерації")

        except Exception as e:
            logger.warning(f"Не вдалося завантажити рекомендації: {str(e)}")
            # Продовжуємо без рекомендацій
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Спроба генерації {attempt + 1}/{max_retries}")
            
            client = Client(provider=DeepInfra)
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="Qwen/Qwen3-Coder-30B-A3B-Instruct",
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt}
                ],
                web_search=False
            )
            
            content = response.choices[0].message.content.strip()
            
            if not content:
                logger.warning("Отримано порожню відповідь")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                return "[Помилка: порожня відповідь]"
            
            logger.info(f"✓ Згенеровано текст довжиною {len(content)} символів")
            return content
            
        except Exception as e:
            logger.error(f"Помилка в спробі {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                return f"[Помилка генерації: {str(e)}]"
    
    return "[Не вдалося згенерувати текст]"


def analyze_successful_posts_sync(top_posts: List[Dict], lang: str = 'uk') -> Dict:
    """Синхронна версія аналізу постів"""
    try:
        from g4f.client import Client
        from g4f.Provider import DeepInfra

        if not top_posts or len(top_posts) < 3:
            error_msg = 'Need at least 3 posts' if lang == 'en' else 'Потрібно мінімум 3 пости'
            return {'success': False, 'error': error_msg}

        logger.info(f"AI-аналіз {len(top_posts)} постів...")

        # Detect language from post content
        if lang == 'auto':
            sample_text = ' '.join([p.get('content', '')[:100] for p in top_posts[:3]])
            en_indicators = ['the', 'and', 'for', 'with', 'our', 'your', 'this', 'that', 'are', 'was', 'were', 'have', 'has', 'been']
            lang = 'en' if any(f' {word} ' in f' {sample_text.lower()} ' for word in en_indicators) else 'uk'

        posts_data = []
        for i, post in enumerate(top_posts[:10], 1):
            if lang == 'en':
                posts_data.append({
                    'number': i,
                    'text': post.get('content', '')[:200],
                    'length': post.get('text_length', 0),
                    'engagement_rate': round(post.get('avg_engagement_rate', 0), 4),
                    'likes': post.get('total_likes', 0),
                    'comments': post.get('total_comments', 0)
                })
            else:
                posts_data.append({
                    'номер': i,
                    'текст': post.get('content', '')[:200],
                    'довжина': post.get('text_length', 0),
                    'engagement_rate': round(post.get('avg_engagement_rate', 0), 4),
                    'лайки': post.get('total_likes', 0),
                    'коментарі': post.get('total_comments', 0)
                })

        if lang == 'en':
            prompt = f"""Analyze {len(posts_data)} most successful posts:

{json.dumps(posts_data, ensure_ascii=False, indent=2)}

Respond ONLY with JSON:
{{
  "content_style": "style description",
  "effective_topics": ["topic1", "topic2"],
  "key_phrases": ["phrase1", "phrase2"],
  "tone": "tone description",
  "structure_tips": "tips",
  "emoji_usage": "how to use",
  "call_to_action": "recommendations"
}}"""
            system_msg = "You are a content analysis expert. Respond ONLY with JSON."
        else:
            prompt = f"""Проаналізуй {len(posts_data)} найуспішніших постів:

{json.dumps(posts_data, ensure_ascii=False, indent=2)}

Відповідай ТІЛЬКИ JSON:
{{
  "content_style": "стиль",
  "effective_topics": ["тема1", "тема2"],
  "key_phrases": ["фраза1", "фраза2"],
  "tone": "тон",
  "structure_tips": "поради",
  "emoji_usage": "як",
  "call_to_action": "чи потрібні"
}}"""
            system_msg = "Ти експерт з аналізу контенту. Відповідай ТІЛЬКИ JSON."

        client = Client(provider=DeepInfra)
        response = client.chat.completions.create(
            model="Qwen/Qwen3-Coder-30B-A3B-Instruct",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            web_search=False
        )

        ai_response = response.choices[0].message.content.strip()
        ai_analysis = _parse_ai_response(ai_response)

        if ai_analysis:
            logger.info("✓ AI-аналіз завершено")
            return {'success': True, 'analysis': ai_analysis, 'analyzed_posts_count': len(posts_data)}
        else:
            return {'success': False, 'error': 'Помилка парсингу'}

    except Exception as e:
        logger.error(f"Помилка AI-аналізу: {str(e)}")
        return {'success': False, 'error': str(e)}


async def analyze_successful_posts(top_posts: List[Dict]) -> Dict:
    """
    Аналізує успішні пости за допомогою AI для виявлення патернів
    
    Args:
        top_posts: список топ-постів з метриками
    
    Returns:
        Dict: структуровані рекомендації від AI
    """
    if not top_posts or len(top_posts) < 3:
        logger.warning("Недостатньо постів для AI-аналізу")
        return {
            'success': False,
            'error': 'Потрібно мінімум 3 пости для аналізу'
        }
    
    try:
        logger.info(f"Початок AI-аналізу {len(top_posts)} топ-постів...")
        
        # Формуємо дані постів для аналізу
        posts_data = []
        for i, post in enumerate(top_posts[:10], 1):  # Максимум 10 постів
            post_info = {
                'номер': i,
                'текст': post.get('content', '')[:200],  # Перші 200 символів
                'довжина': post.get('text_length', 0),
                'engagement_rate': round(post.get('avg_engagement_rate', 0), 4),
                'лайки': post.get('total_likes', 0),
                'коментарі': post.get('total_comments', 0),
                'репости': post.get('total_shares', 0),
                'покази': post.get('total_impressions', 0),
                'час_публікації': int(post.get('hour_of_day', 12)),
                'день_тижня': _get_day_name_uk(int(post.get('day_of_week', 0))),
                'є_посилання': bool(post.get('has_link', False)),
                'є_зображення': bool(post.get('has_images', False)),
                'кількість_зображень': int(post.get('image_count', 0))
            }
            posts_data.append(post_info)
        
        # Формуємо промпт для AI
        prompt = f"""Проаналізуй наступні {len(posts_data)} найуспішніших постів у Facebook за останній період:

{json.dumps(posts_data, ensure_ascii=False, indent=2)}

Твоє завдання:
1. Визнач спільні патерни успішних постів
2. Проаналізуй стиль написання, теми, структуру
3. Виділи ключові фрази та слова, що часто зустрічаються
4. Визнач найефективніші підходи до контенту

ДУЖЕ ВАЖЛИВО: Відповідай ТІЛЬКИ валідним JSON у такому форматі (без додаткового тексту):
{{
  "content_style": "короткий опис стилю (1-2 речення)",
  "effective_topics": ["тема1", "тема2", "тема3"],
  "key_phrases": ["фраза1", "фраза2", "фраза3"],
  "tone": "опис тону (діловий/неформальний/мотиваційний тощо)",
  "structure_tips": "рекомендації по структурі постів (2-3 речення)",
  "emoji_usage": "як використовувати емоджі (помірно/активно/не використовувати)",
  "call_to_action": "чи потрібні заклики до дії та які"
}}

Відповідай ЛИШЕ JSON, без markdown, без пояснень!"""

        # Викликаємо AI
        client = Client(provider=DeepInfra)
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="Qwen/Qwen3-Coder-30B-A3B-Instruct",
            messages=[
                {
                    "role": "system", 
                    "content": "Ти - експерт з аналізу контенту соціальних мереж. Аналізуй пости та давай структуровані рекомендації у форматі JSON. Відповідай ТІЛЬКИ валідним JSON без додаткового тексту."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            web_search=False
        )
        
        ai_response = response.choices[0].message.content.strip()
        logger.info(f"Отримано відповідь від AI: {ai_response[:200]}...")
        
        # Парсимо JSON відповідь
        ai_analysis = _parse_ai_response(ai_response)
        
        if ai_analysis:
            logger.info("✓ AI-аналіз успішно завершено")
            return {
                'success': True,
                'analysis': ai_analysis,
                'analyzed_posts_count': len(posts_data)
            }
        else:
            logger.warning("Не вдалося розпарсити відповідь AI")
            return {
                'success': False,
                'error': 'Не вдалося розпарсити відповідь AI'
            }
            
    except Exception as e:
        logger.error(f"Помилка AI-аналізу: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def _parse_ai_response(response: str) -> Dict:
    """
    Парсить відповідь AI, очищаючи від markdown та зайвого тексту
    
    Args:
        response: відповідь від AI
    
    Returns:
        Dict: розпарсений JSON або None
    """
    try:
        # Видаляємо markdown code blocks
        response = response.replace('```json', '').replace('```', '').strip()
        
        # Шукаємо JSON об'єкт
        start = response.find('{')
        end = response.rfind('}') + 1
        
        if start != -1 and end > start:
            json_str = response[start:end]
            parsed = json.loads(json_str)
            return parsed
        
        # Якщо не знайшли, пробуємо парсити як є
        return json.loads(response)
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {str(e)}")
        logger.error(f"Response was: {response[:500]}")
        return None
    except Exception as e:
        logger.error(f"Parse error: {str(e)}")
        return None


def _get_day_name_uk(day_index: int) -> str:
    """Конвертує номер дня в українську назву"""
    days = ['понеділок', 'вівторок', 'середа', 'четвер', 'п\'ятниця', 'субота', 'неділя']
    return days[day_index] if 0 <= day_index < 7 else 'невідомо'


async def generate_simple_post(topic: str = "") -> str:
    """
    Спрощена версія генерації (резервний варіант)
    """
    import random
    
    templates = [
        f"✨ {topic}\n\nЦе важлива тема для кожного підприємця. Дізнайтеся більше про те, як це може вплинути на ваш бізнес.\n\n#бізнес #маркетинг #успіх",

        f"💡 {topic}\n\nЦе може стати ключем до вашого успіху. Поділіться своїми думками в коментарях!\n\n#поради #розвиток #бізнестренди",

        f"🚀 {topic}\n\nДавайте обговоримо, як це змінює індустрію та які можливості відкриває.\n\n#інновації #тренди #маркетинг"
    ]
    
    return random.choice(templates)


# Тестова функція
async def test_generation():
    """Швидкий тест генерації"""
    print("Тестування генератора постів...\n")
    
    test_prompts = [
        "переваги соціальних мереж для бізнесу",
        "як підвищити продуктивність",
        "мотиваційна думка дня"
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n{'='*60}")
        print(f"Тест {i}: {prompt}")
        print('='*60)
        
        text = await generate_post_text(prompt, min_length=100, max_length=300)
        print(f"\nРезультат ({len(text)} символів):\n")
        print(text)
        print()


if __name__ == "__main__":
    asyncio.run(test_generation())