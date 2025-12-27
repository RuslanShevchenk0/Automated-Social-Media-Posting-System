/**
 * Модуль авторизации через Facebook
 */

class AuthManager {
    constructor() {
        this.TOKEN_KEY = 'jwt_token';
        this.USER_KEY = 'user_data';
    }

    /**
     * Проверяет наличие токена
     */
    isAuthenticated() {
        return !!this.getToken();
    }

    /**
     * Получает токен из localStorage
     */
    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    }

    /**
     * Сохраняет токен в localStorage
     */
    setToken(token) {
        localStorage.setItem(this.TOKEN_KEY, token);
    }

    /**
     * Получает данные пользователя из localStorage
     */
    getUser() {
        const userData = localStorage.getItem(this.USER_KEY);
        return userData ? JSON.parse(userData) : null;
    }

    /**
     * Сохраняет данные пользователя
     */
    setUser(userData) {
        localStorage.setItem(this.USER_KEY, JSON.stringify(userData));
    }

    /**
     * Удаляет токен и данные пользователя
     */
    logout() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_KEY);
        window.location.href = '/';
    }

    /**
     * Редирект на Google авторизацію
     */
    loginWithGoogle() {
        window.location.href = '/api/auth/google/login';
    }

    /**
     * Обработка токена из URL (для обратной совместимости)
     */
    handleCallback() {
        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get('token');

        if (token) {
            this.setToken(token);
            window.history.replaceState({}, document.title, '/');
            return true;
        }

        // Перевірка Facebook OAuth callback
        const facebookConnected = urlParams.get('facebook_connected');
        const facebookError = urlParams.get('facebook_error');

        if (facebookConnected === 'true') {
            window.history.replaceState({}, document.title, '/');
            // Показати повідомлення після завантаження
            setTimeout(() => {
                if (typeof Utils !== 'undefined') {
                    Utils.showMessage('Facebook успішно підключено!', 'success');
                }
            }, 500);
            return false;
        }

        if (facebookError === 'true') {
            window.history.replaceState({}, document.title, '/');
            setTimeout(() => {
                if (typeof Utils !== 'undefined') {
                    Utils.showMessage('Помилка підключення Facebook', 'error');
                }
            }, 500);
            return false;
        }

        return false;
    }

    /**
     * Получает информацию о текущем пользователе с сервера
     */
    async fetchUserInfo() {
        try {
            const response = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${this.getToken()}`
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    this.logout();
                    return null;
                }
                throw new Error('Failed to fetch user info');
            }

            const data = await response.json();
            if (data.success) {
                this.setUser(data.user);
                return data.user;
            }

            return null;
        } catch (error) {
            console.error('Error fetching user info:', error);
            return null;
        }
    }

    /**
     * Показує UI авторизації
     */
    showLoginUI() {
        const container = document.getElementById('auth-container');
        if (!container) return;

        container.innerHTML = `
            <div style="display: flex; min-height: 100vh; width: 100%;">
                <!-- Left Side - Auth Block -->
                <div id="auth-left-panel" style="width: 40%; display: flex; align-items: center; justify-content: center; padding: 2rem; background: linear-gradient(to bottom right, #f9fafb, #f3f4f6);">
                    <div style="width: 100%; max-width: 28rem;">
                        <!-- Logo and Title -->
                        <div style="margin-bottom: 3rem;">
                            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
                                <img src="/static/icon.ico" alt="Icon" style="width: 48px; height: 48px; border-radius: 12px;">
                                <div>
                                    <h1 style="font-size: 1.5rem; font-weight: 700; color: #1f2937; margin: 0;">AutoPosting</h1>
                                    <p style="font-size: 0.875rem; color: #6b7280; margin: 0;">Automation Posting</p>
                                </div>
                            </div>
                        </div>

                        <!-- Auth Card -->
                        <div style="background: white; border-radius: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,0.1); padding: 2rem; border: 1px solid #e5e7eb;">
                            <h2 style="font-size: 1.75rem; font-weight: 600; margin: 0 0 0.75rem 0; color: #1f2937;" data-i18n="auth_welcome">${i18n.t('auth_welcome')}</h2>
                            <p style="margin: 0 0 2rem 0; color: #6b7280; font-size: 1rem;" data-i18n="auth_description">${i18n.t('auth_description')}</p>

                            <!-- Google Sign In Button -->
                            <button
                                onclick="authManager.loginWithGoogle()"
                                style="width: 100%; background: white; color: #374151; font-weight: 500; padding: 0.875rem 1.5rem; border-radius: 0.5rem; border: 2px solid #d1d5db; display: flex; align-items: center; justify-content: center; gap: 0.75rem; transition: all 0.2s; cursor: pointer; font-size: 1rem;"
                                onmouseover="this.style.background='#f9fafb'; this.style.borderColor='#60a5fa'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.1)';"
                                onmouseout="this.style.background='white'; this.style.borderColor='#d1d5db'; this.style.boxShadow='none';"
                            >
                                <svg width="24" height="24" viewBox="0 0 24 24">
                                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                                </svg>
                                <span data-i18n="auth_google_signin">${i18n.t('auth_google_signin')}</span>
                            </button>

                            <!-- Divider -->
                            <div style="margin: 1.5rem 0; display: flex; align-items: center;">
                                <div style="flex: 1; border-top: 1px solid #d1d5db;"></div>
                                <span style="padding: 0 1rem; font-size: 0.9375rem; color: #6b7280;" data-i18n="auth_secure_login">${i18n.t('auth_secure_login')}</span>
                                <div style="flex: 1; border-top: 1px solid #d1d5db;"></div>
                            </div>

                            <!-- Info Text -->
                            <p style="font-size: 0.8125rem; color: #6b7280; text-align: center; margin: 0;" data-i18n="auth_terms">${i18n.t('auth_terms')}</p>
                        </div>

                        <!-- Footer Note -->
                        <p style="margin: 1.5rem 0 0 0; text-align: center; font-size: 0.875rem; color: #6b7280;">
                            <span data-i18n="auth_have_questions">${i18n.t('auth_have_questions')}</span> <a href="#" style="color: #3b82f6; text-decoration: none;" data-i18n="auth_contact_us">${i18n.t('auth_contact_us')}</a>
                        </p>

                        <!-- Language Selector -->
                        <div style="display: flex; justify-content: center; margin-top: 1.5rem;">
                            <div class="lang-selector" style="position: relative;">
                                <button class="btn btn-icon" id="auth-lang-toggle" onclick="toggleAuthLangDropdown(event)" style="background: transparent; border: 1px solid #d1d5db; color: #6b7280; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; transition: all 0.2s;"
                                    onmouseover="this.style.borderColor='#3b82f6'; this.style.color='#3b82f6';"
                                    onmouseout="this.style.borderColor='#d1d5db'; this.style.color='#6b7280';">
                                    <i class="bi bi-translate"></i>
                                    <span id="auth-lang-indicator">UA</span>
                                    <i class="bi bi-chevron-down" style="font-size: 10px; margin-left: 4px;"></i>
                                </button>
                                <div class="lang-dropdown" id="auth-lang-dropdown" style="position: absolute; left: 50%; transform: translateX(-50%); bottom: 100%; margin-bottom: 0.5rem; background: white; border-radius: 0.5rem; box-shadow: 0 10px 25px rgba(0,0,0,0.15); border: 1px solid #e5e7eb; min-width: 160px; display: none; z-index: 1000;">
                                    <div class="lang-option" onclick="setAuthLanguage('uk')" onmouseover="this.style.background='#f9fafb'" onmouseout="this.style.background='white'" style="padding: 0.75rem 1rem; display: flex; align-items: center; gap: 0.75rem; cursor: pointer; transition: background 0.2s; border-bottom: 1px solid #f3f4f6;">
                                        <span class="lang-flag" style="font-size: 1.125rem;">🇺🇦</span>
                                        <span style="flex: 1; color: #1f2937; font-weight: 500; font-size: 0.875rem;">Українська</span>
                                        <i class="bi bi-check lang-check" id="auth-check-uk" style="font-size: 1rem; color: #3b82f6; display: none;"></i>
                                    </div>
                                    <div class="lang-option" onclick="setAuthLanguage('en')" onmouseover="this.style.background='#f9fafb'" onmouseout="this.style.background='white'" style="padding: 0.75rem 1rem; display: flex; align-items: center; gap: 0.75rem; cursor: pointer; transition: background 0.2s;">
                                        <span class="lang-flag" style="font-size: 1.125rem;">🇬🇧</span>
                                        <span style="flex: 1; color: #1f2937; font-weight: 500; font-size: 0.875rem;">English</span>
                                        <i class="bi bi-check lang-check" id="auth-check-en" style="font-size: 1rem; color: #3b82f6; display: none;"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Right Side - Info Block -->
                <div id="auth-right-panel" style="width: 60%; display: none; align-items: center; justify-content: center; padding: 3rem; background: linear-gradient(to bottom right, #dbeafe, #bfdbfe);">
                    <div style="max-width: 36rem;">
                        <div style="margin-bottom: 2rem;">
                            <h2 style="font-size: 2.25rem; font-weight: 700; color: #1f2937; margin: 0 0 1rem 0; line-height: 1.2;">
                                Smart Social Media <span style="color: #3b82f6;">Posting</span>
                            </h2>
                            <p style="font-size: 1.125rem; color: #4b5563; margin: 0 0 2rem 0;" data-i18n="auth_right_subtitle">
                                ${i18n.t('auth_right_subtitle')}
                            </p>
                        </div>

                        <!-- Features Grid -->
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; margin-bottom: 2rem;">
                            <div style="background: rgba(255,255,255,0.8); backdrop-filter: blur(8px); border-radius: 0.75rem; padding: 1.25rem; border: 1px solid #bfdbfe;">
                                <div style="width: 2.5rem; height: 2.5rem; background: #dbeafe; border-radius: 0.5rem; display: flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;">
                                    <i class="bi bi-calendar-check" style="font-size: 1.25rem; color: #3b82f6;"></i>
                                </div>
                                <h3 style="font-weight: 600; color: #1f2937; margin: 0 0 0.25rem 0; font-size: 1rem;" data-i18n="auth_feature_schedule">${i18n.t('auth_feature_schedule')}</h3>
                                <p style="font-size: 0.875rem; color: #4b5563; margin: 0;" data-i18n="auth_feature_schedule_desc">${i18n.t('auth_feature_schedule_desc')}</p>
                            </div>

                            <div style="background: rgba(255,255,255,0.8); backdrop-filter: blur(8px); border-radius: 0.75rem; padding: 1.25rem; border: 1px solid #bfdbfe;">
                                <div style="width: 2.5rem; height: 2.5rem; background: #dbeafe; border-radius: 0.5rem; display: flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;">
                                    <i class="bi bi-bar-chart" style="font-size: 1.25rem; color: #3b82f6;"></i>
                                </div>
                                <h3 style="font-weight: 600; color: #1f2937; margin: 0 0 0.25rem 0; font-size: 1rem;" data-i18n="auth_feature_analytics">${i18n.t('auth_feature_analytics')}</h3>
                                <p style="font-size: 0.875rem; color: #4b5563; margin: 0;" data-i18n="auth_feature_analytics_desc">${i18n.t('auth_feature_analytics_desc')}</p>
                            </div>

                            <div style="background: rgba(255,255,255,0.8); backdrop-filter: blur(8px); border-radius: 0.75rem; padding: 1.25rem; border: 1px solid #bfdbfe;">
                                <div style="width: 2.5rem; height: 2.5rem; background: #dbeafe; border-radius: 0.5rem; display: flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;">
                                    <i class="bi bi-lightning" style="font-size: 1.25rem; color: #3b82f6;"></i>
                                </div>
                                <h3 style="font-weight: 600; color: #1f2937; margin: 0 0 0.25rem 0; font-size: 1rem;" data-i18n="auth_feature_ai">${i18n.t('auth_feature_ai')}</h3>
                                <p style="font-size: 0.875rem; color: #4b5563; margin: 0;" data-i18n="auth_feature_ai_desc">${i18n.t('auth_feature_ai_desc')}</p>
                            </div>

                            <div style="background: rgba(255,255,255,0.8); backdrop-filter: blur(8px); border-radius: 0.75rem; padding: 1.25rem; border: 1px solid #bfdbfe;">
                                <div style="width: 2.5rem; height: 2.5rem; background: #dbeafe; border-radius: 0.5rem; display: flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;">
                                    <i class="bi bi-people" style="font-size: 1.25rem; color: #3b82f6;"></i>
                                </div>
                                <h3 style="font-weight: 600; color: #1f2937; margin: 0 0 0.25rem 0; font-size: 1rem;" data-i18n="auth_feature_multi">${i18n.t('auth_feature_multi')}</h3>
                                <p style="font-size: 0.875rem; color: #4b5563; margin: 0;" data-i18n="auth_feature_multi_desc">${i18n.t('auth_feature_multi_desc')}</p>
                            </div>
                        </div>

                        <!-- Stats -->
                        <div style="display: flex; align-items: flex-end; gap: 2rem;">
                            <div>
                                <div style="font-size: 1.875rem; font-weight: 700; color: #3b82f6;">24/7</div>
                                <div style="font-size: 0.875rem; color: #4b5563;">Automation</div>
                            </div>
                            <div style="width: 1px; height: 3rem; background: #d1d5db;"></div>
                            <div>
                                <div style="font-size: 1.875rem; font-weight: 700; color: #3b82f6;">AI</div>
                                <div style="font-size: 0.875rem; color: #4b5563;">Insights</div>
                            </div>
                            <div style="width: 1px; height: 3rem; background: #d1d5db;"></div>
                            <div>
                                <div style="font-size: 3rem; font-weight: 700; color: #3b82f6; line-height: 1;">∞</div>
                                <div style="font-size: 0.875rem; color: #4b5563; margin-top: 0.25rem;">Posts</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        container.style.display = 'flex';

        // Initialize language UI
        setTimeout(() => {
            updateAuthLangUI();
        }, 50);
    }

    /**
     * Ховає UI авторизації і показує основний інтерфейс
     */
    showMainUI(user) {
        const authContainer = document.getElementById('auth-container');
        if (authContainer) {
            authContainer.style.display = 'none';
        }

        const appContainer = document.getElementById('app-container');
        if (appContainer) {
            appContainer.style.display = 'flex';
        }

        // Отображаем информацию о пользователе
        this.displayUserInfo(user);
    }

    /**
     * Отображает информацию о пользователе в UI
     */
    displayUserInfo(user) {
        const userInfoElement = document.getElementById('user-info');
        if (!userInfoElement) {
            console.error('user-info element not found!');
            return;
        }

        const userName = user.full_name || user.name || 'User';
        const userEmail = user.email || '';

        // Если есть Google аватар - используем прокси, иначе - ui-avatars
        let profilePic;
        if (user.profile_picture && user.profile_picture.includes('googleusercontent.com')) {
            profilePic = `/api/auth/avatar-proxy?url=${encodeURIComponent(user.profile_picture)}`;
        } else if (user.profile_picture) {
            profilePic = user.profile_picture;
        } else {
            profilePic = `https://ui-avatars.com/api/?name=${encodeURIComponent(userName)}&background=3b82f6&color=fff&size=40`;
        }

        const fallbackUrl = `https://ui-avatars.com/api/?name=${encodeURIComponent(userName)}&background=3b82f6&color=fff&size=40`;

        userInfoElement.innerHTML = `
            <div class="user-profile">
                <img src="${profilePic}"
                     alt="${userName}"
                     class="user-avatar"
                     onerror="this.onerror=null; this.src='${fallbackUrl}';">
                <div class="user-details">
                    <span class="user-name">${userName}</span>
                    <span class="user-email">${userEmail}</span>
                </div>
                <button class="btn btn-secondary btn-sm btn-logout" onclick="authManager.logout()">
                    <i class="fas fa-sign-out-alt"></i> <span data-i18n="logout">Вихід</span>
                </button>
            </div>
        `;
    }

    /**
     * Инициализация при загрузке страницы
     */
    async init() {
        // Проверяем наличие токена в URL
        const hasNewToken = this.handleCallback();

        // Если токен есть (новый или старый)
        if (this.isAuthenticated()) {
            // Получаем информацию о пользователе
            const user = await this.fetchUserInfo();

            if (user) {
                this.showMainUI(user);
                return true;
            } else {
                // Токен невалидный
                this.logout();
                this.showLoginUI();
                return false;
            }
        } else {
            // Нет токена - показываем форму входа
            this.showLoginUI();
            return false;
        }
    }
}

// Глобальный экземпляр
const authManager = new AuthManager();

// Language toggle functions for auth page
function toggleAuthLangDropdown(event) {
    if (event) {
        event.stopPropagation();
    }

    const dropdown = document.getElementById('auth-lang-dropdown');
    if (!dropdown) {
        console.error('Auth lang dropdown not found');
        return;
    }

    const isActive = dropdown.style.display === 'block';
    if (isActive) {
        dropdown.style.display = 'none';
    } else {
        dropdown.style.display = 'block';
    }
}

function setAuthLanguage(lang) {
    i18n.setLang(lang);

    // Close dropdown first
    const dropdown = document.getElementById('auth-lang-dropdown');
    if (dropdown) {
        dropdown.style.display = 'none';
    }

    // Re-render the auth page with new translations
    authManager.showLoginUI();

    // Update the language UI after re-render
    setTimeout(() => {
        updateAuthLangUI();
    }, 50);
}

function updateAuthLangUI() {
    const lang = i18n.getLang();
    const indicator = document.getElementById('auth-lang-indicator');
    if (indicator) {
        indicator.textContent = lang === 'uk' ? 'UA' : 'EN';
    }

    const checkUk = document.getElementById('auth-check-uk');
    const checkEn = document.getElementById('auth-check-en');
    if (checkUk && checkEn) {
        checkUk.style.display = lang === 'uk' ? 'inline-block' : 'none';
        checkEn.style.display = lang === 'en' ? 'inline-block' : 'none';
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('auth-lang-dropdown');
    const toggle = document.getElementById('auth-lang-toggle');
    if (dropdown && toggle && !toggle.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.style.display = 'none';
    }
});
