"""
Система аналізу топ-постів та генерації рекомендацій
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import db

logger = logging.getLogger(__name__)

class AnalyticsRecommender:
    """Клас для аналізу патернів успішних постів та генерації рекомендацій"""
    
    def __init__(self, min_engagement_threshold: float = 0.01):
        """
        Args:
            min_engagement_threshold: мінімальний поріг engagement_rate для включення в аналіз
        """
        self.min_engagement_threshold = min_engagement_threshold
    
    def get_top_posts(self, period_days: int = 7, limit: int = 10, 
                      metric: str = 'engagement_rate') -> List[Dict]:
        """
        Отримує топ-пости за вказаний період
        
        Args:
            period_days: кількість днів для аналізу (за замовчуванням 7)
            limit: кількість постів для вибірки (за замовчуванням 10)
            metric: метрика для сортування ('engagement_rate', 'likes', 'comments', 'shares')
        
        Returns:
            List[Dict]: список топ-постів з повною аналітикою
        """
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Дата початку періоду
        start_date = datetime.now() - timedelta(days=period_days)
        
        # Валідація метрики
        valid_metrics = ['engagement_rate', 'likes', 'comments', 'shares', 'impressions']
        if metric not in valid_metrics:
            metric = 'engagement_rate'
        
        # Використовуємо AVG для engagement_rate, SUM для інших
        aggregate = 'AVG' if metric == 'engagement_rate' else 'SUM'
        
        query = f"""
            SELECT
                p.id,
                p.content,
                p.link,
                p.image_urls,
                COALESCE(pub.published_at, p.published_at) as published_at,
                p.is_ai_generated,
                {aggregate}(a.{metric}) as metric_value,
                AVG(a.engagement_rate) as avg_engagement_rate,
                SUM(a.likes) as total_likes,
                SUM(a.comments) as total_comments,
                SUM(a.shares) as total_shares,
                SUM(a.impressions) as total_impressions,
                AVG(a.hour_of_day) as hour_of_day,
                AVG(a.day_of_week) as day_of_week,
                AVG(a.text_length) as text_length,
                MAX(a.has_link) as has_link,
                MAX(a.has_images) as has_images,
                AVG(a.image_count) as image_count
            FROM posts p
            JOIN publications pub ON p.id = pub.post_id
            JOIN analytics a ON pub.id = a.publication_id
            WHERE pub.status = 'published'
            AND pub.published_at >= ?
            GROUP BY p.id
            HAVING metric_value > 0
                OR (total_likes + total_comments + total_shares) > 0
            ORDER BY metric_value DESC
            LIMIT ?
        """

        cursor.execute(query, (start_date, limit))
        
        posts = []
        for row in cursor.fetchall():
            post = dict(row)
            # Парсимо image_urls якщо є
            if post.get('image_urls'):
                import json
                try:
                    post['image_urls'] = json.loads(post['image_urls'])
                except:
                    post['image_urls'] = []
            posts.append(post)
        
        conn.close()
        
        logger.info(f"Знайдено {len(posts)} топ-постів за останні {period_days} днів")
        return posts
    
    def analyze_patterns(self, top_posts: List[Dict], lang: str = 'uk') -> Dict:
        """
        Аналізує патерни успішних постів
        
        Args:
            top_posts: список топ-постів
        
        Returns:
            Dict: виявлені патерни
        """
        if not top_posts:
            logger.warning("Немає постів для аналізу")
            return self._get_default_patterns()
        
        # Аналіз довжини тексту
        text_lengths = [p['text_length'] for p in top_posts if p.get('text_length')]
        avg_text_length = sum(text_lengths) / len(text_lengths) if text_lengths else 200
        min_text_length = min(text_lengths) if text_lengths else 100
        max_text_length = max(text_lengths) if text_lengths else 300
        
        # Аналіз часу публікації
        hours = [int(p['hour_of_day']) for p in top_posts if p.get('hour_of_day') is not None]
        hour_counts = {}
        for hour in hours:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # Топ-3 години
        best_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        best_hours_list = [h[0] for h in best_hours]
        
        # Аналіз днів тижня
        days = [int(p['day_of_week']) for p in top_posts if p.get('day_of_week') is not None]
        day_counts = {}
        for day in days:
            day_counts[day] = day_counts.get(day, 0) + 1
        
        # Топ-3 дні
        best_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        best_days_list = [self._get_day_name(d[0], lang) for d in best_days]
        
        # Аналіз використання зображень
        with_images = sum(1 for p in top_posts if p.get('has_images'))
        images_percentage = (with_images / len(top_posts)) * 100
        use_images = images_percentage > 50
        
        # Середня кількість зображень
        image_counts = [p['image_count'] for p in top_posts if p.get('image_count')]
        avg_image_count = sum(image_counts) / len(image_counts) if image_counts else 1
        
        # Аналіз використання посилань
        with_links = sum(1 for p in top_posts if p.get('has_link'))
        links_percentage = (with_links / len(top_posts)) * 100
        use_links = links_percentage > 50
        
        # Середній engagement rate
        avg_engagement = sum(p['avg_engagement_rate'] for p in top_posts) / len(top_posts)
        
        patterns = {
            'optimal_text_length': {
                'min': int(min_text_length * 0.9),
                'max': int(max_text_length * 1.1),
                'avg': int(avg_text_length)
            },
            'best_posting_hours': best_hours_list,
            'best_days': best_days_list,
            'use_images': use_images,
            'optimal_image_count': int(round(avg_image_count)),
            'use_links': use_links,
            'avg_engagement_rate': round(avg_engagement, 4),
            'analyzed_posts_count': len(top_posts),
            'images_percentage': round(images_percentage, 1),
            'links_percentage': round(links_percentage, 1)
        }
        
        logger.info(f"Патерни проаналізовано: {patterns}")
        return patterns
    
    def generate_recommendations(self, patterns: Dict, lang: str = 'uk') -> Dict:
        """
        Генерує рекомендації на основі виявлених патернів

        Args:
            patterns: виявлені патерни
            lang: мова рекомендацій ('uk' або 'en')

        Returns:
            Dict: структуровані рекомендації
        """
        if lang == 'en':
            img_word = 'image' if patterns['optimal_image_count'] == 1 else 'images'
            recommendations = {
                'text_length': {
                    'recommendation': f"Optimal text length: {patterns['optimal_text_length']['min']}-{patterns['optimal_text_length']['max']} characters",
                    'ideal': patterns['optimal_text_length']['avg'],
                    'min': patterns['optimal_text_length']['min'],
                    'max': patterns['optimal_text_length']['max']
                },
                'posting_time': {
                    'recommendation': f"Best posting hours: {', '.join(map(str, patterns['best_posting_hours']))}",
                    'hours': patterns['best_posting_hours'],
                    'days': patterns['best_days']
                },
                'images': {
                    'recommendation': f"{'Use' if patterns['use_images'] else 'Not necessary to use'} images",
                    'use': patterns['use_images'],
                    'optimal_count': patterns['optimal_image_count'],
                    'detail': f"Optimal: {patterns['optimal_image_count']} {img_word}"
                },
                'links': {
                    'recommendation': f"{'Add' if patterns['use_links'] else 'Not necessary to add'} links ({patterns['links_percentage']}%)",
                    'use': patterns['use_links'],
                    'percentage': patterns['links_percentage']
                },
                'engagement': {
                    'target': patterns['avg_engagement_rate'],
                    'detail': f"Target engagement rate: {patterns['avg_engagement_rate']:.2%}"
                },
                'summary': self._generate_summary(patterns, lang)
            }
        else:
            img_word = 'зображення' if patterns['optimal_image_count'] == 1 else 'зображень'
            recommendations = {
                'text_length': {
                    'recommendation': f"Оптимальна довжина тексту: {patterns['optimal_text_length']['min']}-{patterns['optimal_text_length']['max']} символів",
                    'ideal': patterns['optimal_text_length']['avg'],
                    'min': patterns['optimal_text_length']['min'],
                    'max': patterns['optimal_text_length']['max']
                },
                'posting_time': {
                    'recommendation': f"Найкращі години для публікації: {', '.join(map(str, patterns['best_posting_hours']))}",
                    'hours': patterns['best_posting_hours'],
                    'days': patterns['best_days']
                },
                'images': {
                    'recommendation': f"{'Використовуйте' if patterns['use_images'] else 'Не обов\'язково використовувати'} зображення",
                    'use': patterns['use_images'],
                    'optimal_count': patterns['optimal_image_count'],
                    'detail': f"Оптимально: {patterns['optimal_image_count']} {img_word}"
                },
                'links': {
                    'recommendation': f"{'Додавайте' if patterns['use_links'] else 'Не обов\'язково додавати'} посилання",
                    'use': patterns['use_links'],
                    'percentage': patterns['links_percentage']
                },
                'engagement': {
                    'target': patterns['avg_engagement_rate'],
                    'detail': f"Цільовий engagement rate: {patterns['avg_engagement_rate']:.2%}"
                },
                'summary': self._generate_summary(patterns, lang)
            }
        
        return recommendations
    
    def save_recommendations(self, recommendations: Dict, patterns: Dict, 
                            period_days: int = 7) -> bool:
        """
        Зберігає рекомендації в базу даних
        
        Args:
            recommendations: згенеровані рекомендації
            patterns: виявлені патерни
            period_days: період аналізу
        
        Returns:
            bool: успішність збереження
        """
        try:
            import json
            
            # Визначаємо період
            period_end = datetime.now()
            period_start = period_end - timedelta(days=period_days)
            
            # Зберігаємо в БД
            recommendation_id = db.save_recommendation(
                period_start=period_start,
                period_end=period_end,
                analyzed_posts_count=patterns['analyzed_posts_count'],
                recommendations=recommendations,
                patterns=patterns,
                status='completed'
            )
            
            logger.info(f"✓ Рекомендації збережено в БД (ID: {recommendation_id})")
            
            return True
            
        except Exception as e:
            logger.error(f"Помилка збереження рекомендацій: {str(e)}")
            return False
    
    def _get_day_name(self, day_index: int, lang: str = 'uk') -> str:
        """Конвертує номер дня в назву"""
        if lang == 'en':
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            return days[day_index] if 0 <= day_index < 7 else 'unknown'
        else:
            days = ['понеділок', 'вівторок', 'середа', 'четвер', 'п\'ятниця', 'субота', 'неділя']
            return days[day_index] if 0 <= day_index < 7 else 'невідомо'
    
    def _generate_summary(self, patterns: Dict, lang: str = 'uk') -> str:
        """Генерує короткий саммарі рекомендацій"""
        summary_parts = []

        if lang == 'en':
            # Text
            text_rec = f"Write posts {patterns['optimal_text_length']['min']}-{patterns['optimal_text_length']['max']} characters long"
            summary_parts.append(text_rec)

            # Time
            hours_str = ', '.join(map(str, patterns['best_posting_hours']))
            time_rec = f"Post at {hours_str} o'clock"
            summary_parts.append(time_rec)

            # Days
            days_str = ', '.join(patterns['best_days'])
            days_rec = f"Best days: {days_str}"
            summary_parts.append(days_rec)

            # Images
            if patterns['use_images']:
                img_word = 'image' if patterns['optimal_image_count'] == 1 else 'images'
                img_rec = f"Add {patterns['optimal_image_count']} {img_word}"
                summary_parts.append(img_rec)
        else:
            # Текст
            text_rec = f"Пишіть пости довжиною {patterns['optimal_text_length']['min']}-{patterns['optimal_text_length']['max']} символів"
            summary_parts.append(text_rec)

            # Час
            hours_str = ', '.join(map(str, patterns['best_posting_hours']))
            time_rec = f"Публікуйте о {hours_str} годині"
            summary_parts.append(time_rec)

            # Дні
            days_str = ', '.join(patterns['best_days'])
            days_rec = f"Найкращі дні: {days_str}"
            summary_parts.append(days_rec)

            # Зображення
            if patterns['use_images']:
                img_rec = f"Додавайте {patterns['optimal_image_count']} {'зображення' if patterns['optimal_image_count'] == 1 else 'зображень'}"
                summary_parts.append(img_rec)

        return '. '.join(summary_parts) + '.'
    
    def _get_default_patterns(self) -> Dict:
        """Повертає дефолтні патерни якщо недостатньо даних"""
        return {
            'optimal_text_length': {'min': 150, 'max': 300, 'avg': 200},
            'best_posting_hours': [9, 12, 18],
            'best_days': ['понеділок', 'середа', 'п\'ятниця'],
            'use_images': True,
            'optimal_image_count': 1,
            'use_links': False,
            'avg_engagement_rate': 0.0,
            'analyzed_posts_count': 0,
            'images_percentage': 0.0,
            'links_percentage': 0.0
        }
    
    def get_full_analysis(self, period_days: int = 7, limit: int = 10, use_ai: bool = True) -> Dict:
        """
        Виконує повний цикл аналізу та генерації рекомендацій
        
        Args:
            period_days: період для аналізу
            limit: кількість топ-постів
            use_ai: використовувати AI для глибокого аналізу текстів
        
        Returns:
            Dict: повний аналіз з рекомендаціями
        """
        logger.info(f"Початок аналізу топ-постів за {period_days} днів...")
        
        # Крок 1: Отримати топ-пости
        top_posts = self.get_top_posts(period_days=period_days, limit=limit)
        
        if not top_posts:
            logger.warning("Недостатньо даних для аналізу")
            return {
                'success': False,
                'message': 'Недостатньо опублікованих постів для аналізу',
                'recommendations': None
            }
        
        # Auto-detect language from posts
        sample_text = ' '.join([p.get('content', '')[:100] for p in top_posts[:3]])
        # Check for common English words
        en_indicators = ['the', 'and', 'for', 'with', 'our', 'your', 'this', 'that', 'are', 'was', 'were', 'have', 'has', 'been']
        lang = 'en' if any(f' {word} ' in f' {sample_text.lower()} ' for word in en_indicators) else 'uk'

        # Крок 2: Аналізувати патерни з мовою
        patterns = self.analyze_patterns(top_posts, lang)

        # Крок 3: Генерувати базові рекомендації з мовою
        recommendations = self.generate_recommendations(patterns, lang)

        # Крок 4: AI-аналіз текстів (якщо ввімкнено і достатньо постів)
        ai_insights = None
        if use_ai and len(top_posts) >= 3:
            try:
                from text_generator import analyze_successful_posts_sync

                logger.info("Запуск AI-аналізу текстів постів...")
                ai_result = analyze_successful_posts_sync(top_posts, lang=lang)

                if ai_result.get('success'):
                    ai_insights = ai_result.get('analysis', {})
                    recommendations['ai_insights'] = ai_insights
                    logger.info("✓ AI-аналіз успішно інтегровано")
                else:
                    logger.warning(f"AI-аналіз не вдався: {ai_result.get('error')}")

            except Exception as e:
                logger.error(f"Помилка AI-аналізу: {str(e)}")
        
        # Крок 5: Зберегти результати
        self.save_recommendations(recommendations, patterns, period_days)
        
        logger.info("Аналіз завершено успішно")
        
        return {
            'success': True,
            'top_posts': top_posts,
            'patterns': patterns,
            'recommendations': recommendations,
            'ai_insights': ai_insights,
            'period_days': period_days,
            'analyzed_count': len(top_posts)
        }


# Глобальний екземпляр
recommender = AnalyticsRecommender()


# Функція для швидкого тестування
def test_recommender():
    """Тестова функція для перевірки роботи"""
    print("="*70)
    print("Тест Analytics Recommender")
    print("="*70)
    
    result = recommender.get_full_analysis(period_days=30, limit=10)
    
    if result['success']:
        print(f"\n✓ Проаналізовано {result['analyzed_count']} постів")
        print(f"\nРекомендації:")
        print(f"- {result['recommendations']['text_length']['recommendation']}")
        print(f"- {result['recommendations']['posting_time']['recommendation']}")
        print(f"- {result['recommendations']['images']['recommendation']}")
        print(f"- {result['recommendations']['links']['recommendation']}")
        print(f"\nСаммарі: {result['recommendations']['summary']}")
    else:
        print(f"\n✗ {result['message']}")


if __name__ == "__main__":
    test_recommender()