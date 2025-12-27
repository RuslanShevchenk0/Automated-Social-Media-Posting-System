// API модуль для взаємодії з backend
const API = {
    baseURL: '',

    // Получение токена авторизации
    getAuthToken() {
        return localStorage.getItem('jwt_token');
    },

    // Загальний метод для запитів
    async request(endpoint, options = {}) {
        try {
            const token = this.getAuthToken();
            const headers = {
                'Content-Type': 'application/json',
                ...options.headers,
            };

            // Добавляем токен авторизации если есть
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(this.baseURL + endpoint, {
                ...options,
                headers,
            });
            
            const data = await response.json();

            if (!response.ok) {
                // Если 401 - перенаправляем на авторизацию
                if (response.status === 401) {
                    if (typeof authManager !== 'undefined') {
                        authManager.logout();
                    }
                }
                throw new Error(data.detail || 'Помилка запиту');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },
    
    // Пости
    posts: {
        getAll: (limit = 50, offset = 0) => 
            API.request(`/api/posts?limit=${limit}&offset=${offset}`),
        
        getById: (id) => 
            API.request(`/api/posts/${id}`),
        
        create: (data) => 
            API.request('/api/posts', {
                method: 'POST',
                body: JSON.stringify(data),
            }),
        
        update: (id, data) => 
            API.request(`/api/posts/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data),
            }),
        
        delete: (id) => 
            API.request(`/api/posts/${id}`, {
                method: 'DELETE',
            }),
        
        publish: (id) => 
            API.request(`/api/posts/${id}/publish`, {
                method: 'POST',
            }),
    },
    
    // AI генерація
    generate: (prompt, minLength = 100, maxLength = 500, useRecommendations = true, lang = 'uk') =>
        API.request('/api/generate', {
            method: 'POST',
            body: JSON.stringify({
                prompt,
                min_length: minLength,
                max_length: maxLength,
                use_recommendations: useRecommendations,
                lang: lang,
            }),
        }),
    
    // Сторінки
    pages: {
        getAll: () => 
            API.request('/api/pages'),
        
        refresh: () => 
            API.request('/api/pages/refresh', {
                method: 'POST',
            }),
    },
    
    // Аналітика - ВИПРАВЛЕНО
    analytics: {
        // Швидке оновлення (за 7 днів, до 50 постів)
        collect: () => 
            API.request('/api/analytics/collect', { method: 'POST' }),
        
        // Оновити ВСІ пости (без обмеження по датам, до 100 постів)
        refreshAll: () => 
            API.request('/api/analytics/refresh-all', { method: 'POST' }),
        
        // Загальна статистика
        getSummary: () => 
            API.request('/api/analytics/summary'),
        
        // Аналітика конкретного поста
        getPostAnalytics: (postId) => 
            API.request(`/api/analytics/post/${postId}`),
        
        // Оновити аналітику для конкретного поста
        collectForPost: (postId) => 
            API.request(`/api/analytics/collect/${postId}`, { method: 'POST' }),
    },
    
    // Налаштування
    settings: {
        get: () => 
            API.request('/api/settings'),
        
        saveToken: (pageId, token) => 
            API.request('/api/settings/token', {
                method: 'POST',
                body: JSON.stringify({ page_id: pageId, access_token: token }),
            }),
        
        testConnection: (pageId) => 
            API.request(`/api/settings/test/${pageId}`, {
                method: 'POST',
            }),
    },
    
    // Шаблони
    // Рекомендації
    recommendations: {
        getLatest: () =>
            API.request('/api/recommendations/latest'),

        getHistory: (limit = 10) =>
            API.request(`/api/recommendations/history?limit=${limit}`),

        generate: (periodDays = 7, limit = 10) =>
            API.request(`/api/recommendations/generate?period_days=${periodDays}&limit=${limit}`, {
                method: 'POST',
            }),

        getTopPosts: (days = 7, limit = 10, metric = 'engagement_rate') =>
            API.request(`/api/analytics/top-posts?days=${days}&limit=${limit}&metric=${metric}`),
    },

    templates: {
        getAll: () =>
            API.request('/api/templates'),

        getById: (id) =>
            API.request(`/api/templates/${id}`),

        create: (data) =>
            API.request('/api/templates', {
                method: 'POST',
                body: JSON.stringify(data),
            }),

        generateFromRecommendations: () =>
            API.request('/api/templates/generate-from-recommendations', {
                method: 'POST',
            }),

        update: (id, data) =>
            API.request(`/api/templates/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data),
            }),

        delete: (id) =>
            API.request(`/api/templates/${id}`, {
                method: 'DELETE',
            }),
    },
};

// Утиліти
const Utils = {
    // Форматування дати
    formatDate(dateString) {
        if (!dateString) return t('not_specified');
        const date = new Date(dateString);
        const locale = i18n.getLang() === 'en' ? 'en-US' : 'uk-UA';
        return date.toLocaleString(locale, {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    },
    
    // Форматування відносного часу
    formatRelativeTime(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days} ${i18n.t('days_ago')}`;
        if (hours > 0) return `${hours} ${i18n.t('hours_ago')}`;
        if (minutes > 0) return `${minutes} ${i18n.t('minutes_ago')}`;
        return i18n.t('just_now');
    },
    
    // Скорочення тексту
    truncate(text, maxLength = 100) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },

    // Екранування HTML
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    // Показати повідомлення (Toast)
    showMessage(message, type = 'success') {
        // Створюємо контейнер якщо його немає
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        // Видаляємо старі toast якщо їх більше 3
        const existingToasts = container.querySelectorAll('.toast');
        if (existingToasts.length >= 3) {
            existingToasts[0].remove();
        }

        // Іконки для різних типів
        const icons = {
            success: '<i class="bi bi-check-circle-fill"></i>',
            error: '<i class="bi bi-x-circle-fill"></i>',
            info: '<i class="bi bi-info-circle-fill"></i>',
            warning: '<i class="bi bi-exclamation-triangle-fill"></i>'
        };

        // Створюємо toast
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.opacity = '0';
        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.info}</div>
            <div class="toast-content">${message}</div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <i class="bi bi-x"></i>
            </button>
        `;

        container.appendChild(toast);

        // Плавна поява через requestAnimationFrame
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
        });

        // Автоматичне видалення через 3.5 секунди
        setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 200);
        }, 3500);
    },

    // Показати завантаження
    showLoading(text = null) {
        if (!text) text = i18n.t('loading');
        let overlay = document.querySelector('.loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            document.body.appendChild(overlay);
        }

        overlay.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <div class="loading-text">${text}</div>
            </div>
        `;
        overlay.classList.add('active');
    },

    // Сховати завантаження
    hideLoading() {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.classList.remove('active');
        }
    },

    // Підтвердження дії
    async confirm(message, title = null) {
        return new Promise((resolve) => {
            // Створюємо діалог
            const dialog = document.createElement('div');
            dialog.className = 'confirm-dialog';
            dialog.innerHTML = `
                <div class="confirm-dialog-content">
                    <div class="confirm-dialog-header">
                        <div class="confirm-dialog-icon">
                            <i class="bi bi-question-circle"></i>
                        </div>
                        <div class="confirm-dialog-title">${title || t('confirmation')}</div>
                    </div>
                    <div class="confirm-dialog-body">${message}</div>
                    <div class="confirm-dialog-footer">
                        <button class="btn btn-secondary" id="confirm-cancel">${t('cancel')}</button>
                        <button class="btn btn-primary" id="confirm-ok">${t('confirm')}</button>
                    </div>
                </div>
            `;

            document.body.appendChild(dialog);
            setTimeout(() => dialog.classList.add('active'), 10);

            // Обробники кнопок
            const cleanup = (result) => {
                dialog.classList.remove('active');
                setTimeout(() => {
                    dialog.remove();
                    resolve(result);
                }, 150);
            };

            dialog.querySelector('#confirm-ok').onclick = () => cleanup(true);
            dialog.querySelector('#confirm-cancel').onclick = () => cleanup(false);
            dialog.onclick = (e) => {
                if (e.target === dialog) cleanup(false);
            };
        });
    },
    
    // Отримати бейдж статусу
    getStatusBadge(status) {
        const badges = {
            draft: `<span class="badge badge-draft">${t('status_draft')}</span>`,
            scheduled: `<span class="badge badge-scheduled">${t('status_scheduled')}</span>`,
            published: `<span class="badge badge-published">${t('published_badge')}</span>`,
            failed: `<span class="badge badge-failed">${t('status_failed')}</span>`,
        };
        return badges[status] || status;
    },
    
    // Форматування числа
    formatNumber(num) {
        if (!num) return '0';
        return num.toLocaleString('uk-UA');
    },
};

// CSS анімації (додамо в head якщо немає)
if (!document.querySelector('#animation-styles')) {
    const style = document.createElement('style');
    style.id = 'animation-styles';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}