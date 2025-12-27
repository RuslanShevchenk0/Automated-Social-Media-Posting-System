// Головний файл додатку

// Поточна сторінка
let currentPage = 'dashboard';

// Функція ініціалізації додатку (викликається після авторизації)
function initApp() {
    initNavigation();
    loadPage('dashboard');

    // Оновлення лічильника символів
    document.addEventListener('input', (e) => {
        if (e.target.id === 'post-content') {
            updateCharCount();
        }
    });
}

// Навігація
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            
            // Оновлюємо активний елемент
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            
            // Завантажуємо сторінку
            loadPage(page);
        });
    });
}

// Завантаження сторінки
async function loadPage(pageName) {
    currentPage = pageName;

    // Оновлюємо заголовок з перекладом
    document.getElementById('page-title').textContent = i18n.t(`nav_${pageName}`);
    
    // Завантажуємо контент
    const content = document.getElementById('content');
    
    try {
        if (Pages[pageName]) {
            const html = await Pages[pageName]();
            content.innerHTML = html;
            
            // Ініціалізуємо компоненти сторінки
            initPageComponents(pageName);
        } else {
            content.innerHTML = '<div class="alert alert-error">Сторінка не знайдена</div>';
        }
    } catch (error) {
        console.error('Load page error:', error);
        content.innerHTML = `<div class="alert alert-error">Помилка завантаження: ${error.message}</div>`;
    }
}

// Ініціалізація компонентів сторінки
function initPageComponents(pageName) {
    // Destroy previous charts before initializing new ones
    if (typeof destroyAllCharts === 'function') {
        destroyAllCharts();
    }

    if (pageName === 'create') {
        updateCharCount();
    } else if (pageName === 'analytics') {
        // Initialize analytics charts after a small delay to ensure DOM is ready
        setTimeout(() => {
            if (typeof initAnalyticsCharts === 'function') {
                initAnalyticsCharts();
            }
        }, 100);
    } else if (pageName === 'dashboard') {
        // Initialize dashboard chart
        setTimeout(() => {
            if (typeof initDashboardChart === 'function') {
                initDashboardChart();
            }
        }, 100);
    }
}

// Навігація програмно
function navigateTo(pageName) {
    const navItem = document.querySelector(`.nav-item[data-page="${pageName}"]`);
    if (navItem) {
        navItem.click();
    }
}

// Оновлення даних
async function refreshData() {
    await loadPage(currentPage);
    Utils.showMessage(i18n.t('data_updated'), 'success');
}

// ==================== СТВОРЕННЯ ПОСТА ====================

function toggleCreationMode() {
    const mode = document.querySelector('input[name="creation_mode"]:checked').value;
    const aiSection = document.getElementById('ai-prompt-section');
    
    if (mode === 'ai') {
        aiSection.style.display = 'block';
    } else {
        aiSection.style.display = 'none';
    }
}

function toggleSchedule() {
    const mode = document.querySelector('input[name="publish_mode"]:checked').value;
    const scheduleSection = document.getElementById('schedule-section');
    
    if (mode === 'schedule') {
        scheduleSection.style.display = 'block';
        
        // Встановлюємо мінімальну дату (зараз + 5 хвилин)
        const now = new Date();
        now.setMinutes(now.getMinutes() + 5);
        const minDate = now.toISOString().slice(0, 16);
        document.getElementById('scheduled-time').min = minDate;
    } else {
        scheduleSection.style.display = 'none';
    }
}

function updateCharCount() {
    const content = document.getElementById('post-content');
    const counter = document.getElementById('char-count');

    if (content && counter) {
        counter.textContent = content.value.length;
    }
}

// Функція для оновлення лічильника символів з рекомендаціями
async function updateCharCounter() {
    const content = document.getElementById('post-content');
    const counter = document.getElementById('char-count');
    const indicator = document.getElementById('length-recommendation');

    if (!content || !counter) return;

    const length = content.value.length;
    counter.textContent = length;

    // Якщо є блок рекомендацій, оновлюємо його
    if (indicator) {
        try {
            const recData = await API.recommendations.getLatest();
            const rec = recData.recommendation;

            if (rec && rec.recommendations && rec.recommendations.text_length) {
                const min = rec.recommendations.text_length.min;
                const max = rec.recommendations.text_length.max;

                let status = '';
                let color = '';
                let icon = '';

                if (length === 0) {
                    status = 'Почніть писати...';
                    color = '#94a3b8';
                    icon = '✏️';
                } else if (length < min) {
                    status = `Ще ${min - length} символів до оптимальної довжини`;
                    color = '#f59e0b';
                    icon = '⚠️';
                } else if (length >= min && length <= max) {
                    status = 'Оптимальна довжина!';
                    color = '#10b981';
                    icon = '✅';
                } else if (length > max && length <= max * 1.2) {
                    status = 'Трохи довго, але прийнятно';
                    color = '#f59e0b';
                    icon = '⚠️';
                } else {
                    status = `Занадто довго (перевищення на ${length - max} символів)`;
                    color = '#ef4444';
                    icon = '❌';
                }

                indicator.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 0.5rem; color: ${color};">
                        <span style="font-size: 1.25rem;">${icon}</span>
                        <span style="font-weight: 500;">${status}</span>
                    </div>
                `;
                indicator.style.background = `${color}15`;
                indicator.style.border = `1px solid ${color}40`;
            }
        } catch (e) {
            // Ігноруємо помилки завантаження рекомендацій
        }
    }
}

async function generateAIText() {
    const promptInput = document.getElementById('ai-prompt');
    const contentInput = document.getElementById('post-content');
    const minLengthInput = document.getElementById('min-length');
    const maxLengthInput = document.getElementById('max-length');
    const minLength = parseInt(minLengthInput.value);
    const maxLength = parseInt(maxLengthInput.value);

    const prompt = promptInput.value.trim();

    if (!prompt) {
        Utils.showMessage(i18n.t('enter_prompt'), 'error');
        return;
    }

    try {
        Utils.showLoading();

        // Зберігаємо значення мін/макс у localStorage
        localStorage.setItem('ai_min_length', minLength);
        localStorage.setItem('ai_max_length', maxLength);

        // Визначаємо мову для генерації
        const lang = i18n.getLang();

        // Генеруємо з урахуванням рекомендацій (useRecommendations = true за замовчуванням)
        const response = await API.generate(prompt, minLength, maxLength, true, lang);

        if (response.success && response.text) {
            contentInput.value = response.text;
            updateCharCount();
            // Оновлюємо також індикатор довжини якщо є
            if (typeof updateCharCounter === 'function') {
                updateCharCounter();
            }
            Utils.showMessage('Текст згенеровано успішно з урахуванням рекомендацій!', 'success');
        } else {
            throw new Error('Не вдалося згенерувати текст');
        }
    } catch (error) {
        console.error('Generate error:', error);
        Utils.showMessage('Помилка генерації: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

async function handleCreatePost(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    // Отримуємо дані
    const content = formData.get('content');
    const link = formData.get('link');
    const pageIds = Array.from(form.querySelectorAll('input[name="pages"]:checked'))
        .map(input => input.value);
    
    // Перевірка
    if (!content) {
        Utils.showMessage(i18n.t('enter_content'), 'error');
        return;
    }

    if (pageIds.length === 0) {
        Utils.showMessage(i18n.t('select_page'), 'error');
        return;
    }
    
    // Час публікації
    let scheduledTime = null;
    const publishMode = form.querySelector('input[name="publish_mode"]:checked').value;
    
    if (publishMode === 'schedule') {
        const scheduleInput = document.getElementById('scheduled-time');
        if (!scheduleInput.value) {
            Utils.showMessage('Вкажіть дату та час публікації', 'error');
            return;
        }
        scheduledTime = scheduleInput.value;
    }
    
    // Перевіряємо чи це AI генерація
    const creationMode = form.querySelector('input[name="creation_mode"]:checked').value;
    const isAiGenerated = creationMode === 'ai';
    const aiPrompt = isAiGenerated ? document.getElementById('ai-prompt').value : null;
    
    try {
        Utils.showLoading();
        
        // 1. Завантажуємо зображення на сервер
        let imageUrls = [];
        if (selectedImages.length > 0) {
            Utils.showMessage('Завантаження зображень...', 'info');
            
            for (const file of selectedImages) {
                try {
                    const result = await ImageAPI.uploadImage(file);
                    if (result.success) {
                        imageUrls.push(result.url);
                    }
                } catch (error) {
                    console.error('Image upload error:', error);
                }
            }
            
            if (imageUrls.length === 0 && selectedImages.length > 0) {
                Utils.showMessage('Не вдалося завантажити зображення', 'error');
                Utils.hideLoading();
                return;
            }
        }
        
        // 2. Створюємо пост з URLs зображень
        const response = await API.posts.create({
            content,
            link: link || null,
            is_ai_generated: isAiGenerated,
            ai_prompt: aiPrompt,
            scheduled_time: scheduledTime,
            page_ids: pageIds,
            image_urls: imageUrls
        });
        
        if (response.success) {
            Utils.showMessage(i18n.t('post_created_success'), 'success');
            
            // Очищаємо вибрані зображення
            clearSelectedImages();
            
            // Якщо публікуємо зараз
            if (publishMode === 'now') {
                await publishPost(response.post_id);
            } else {
                navigateTo('posts');
            }
        }
    } catch (error) {
        console.error('Create post error:', error);
        Utils.showMessage(i18n.t('post_creation_error') + ': ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

// ==================== ДІЇ З ПОСТАМИ ====================

async function publishPost(postId) {
    if (!await Utils.confirm(t('confirm_publish_post'))) {
        return;
    }
    
    try {
        Utils.showLoading();
        
        const response = await API.posts.publish(postId);
        
        if (response.success) {
            const successCount = response.results.filter(r => r.success).length;
            const totalCount = response.results.length;
            
            Utils.showMessage(i18n.t('post_published_on_pages', {successCount, totalCount}), 'success');
            
            // Оновлюємо список
            if (currentPage === 'posts') {
                await loadPage('posts');
            } else {
                navigateTo('posts');
            }
        }
    } catch (error) {
        console.error('Publish error:', error);
        Utils.showMessage('Помилка публікації: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

async function viewPost(postId) {
    try {
        Utils.showLoading();
        
        const response = await API.posts.getById(postId);
        
        if (response.success && response.post) {
            const post = response.post;
            
            // Створюємо модальне вікно
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-header">
                    <h3 class="modal-title">${i18n.t('post_details')}</h3>
                    <button onclick="closeModal()" style="background: none; border: none; color: var(--text-secondary); cursor: pointer; padding: 0.25rem; font-size: 24px;">
                        <i class="bi bi-x"></i>
                    </button>
                </div>

                <div class="modal-body">
                    <div style="margin-bottom: 1.5rem;">
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center;">
                            ${Utils.getStatusBadge(post.status)}
                            ${post.is_ai_generated ? '<span class="badge" style="background: #fef3c7; color: #92400e;"><i class="bi bi-robot"></i> AI</span>' : ''}
                            ${post.image_urls && post.image_urls.length > 0 ? `<span class="badge" style="background: #dbeafe; color: #1e40af;"><i class="bi bi-image"></i> ${post.image_urls.length} ${i18n.t('photo')}</span>` : ''}
                        </div>
                    </div>

                    <div style="margin-bottom: 1.5rem;">
                        <div style="font-weight: 600; margin-bottom: 0.75rem; color: var(--text);">${i18n.t('post_text')}</div>
                        <div style="padding: 1rem; background: white; border-radius: 0.5rem; border: 1px solid var(--border); line-height: 1.5; max-height: 400px; overflow-y: auto;">
                            ${post.content.trim()}
                        </div>
                    </div>

                    ${post.image_urls && post.image_urls.length > 0 ? `
                        <div style="margin-bottom: 1.5rem;">
                            <div style="font-weight: 600; margin-bottom: 0.75rem;">${i18n.t('images')}</div>
                            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.75rem;">
                                ${post.image_urls.map(url => `
                                    <img src="${url}" style="width: 100%; height: 150px; object-fit: cover; border-radius: 0.375rem; border: 1px solid var(--border); cursor: pointer;" onclick="window.open('${url}', '_blank')">
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    ${post.link ? `
                        <div style="margin-bottom: 1.5rem;">
                            <div style="font-weight: 600; margin-bottom: 0.75rem;">${i18n.t('link')}</div>
                            <a href="${post.link}" target="_blank" style="color: var(--primary); text-decoration: none; word-break: break-all;">
                                ${post.link} <i class="bi bi-box-arrow-up-right" style="font-size: 11px;"></i>
                            </a>
                        </div>
                    ` : ''}

                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem; margin-bottom: 1.5rem; padding: 1rem; background: var(--bg); border-radius: 0.375rem;">
                        <div>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 0.25rem;">${i18n.t('created')}</div>
                            <div style="font-weight: 600;">${Utils.formatDate(post.created_at)}</div>
                        </div>
                        ${post.scheduled_time ? `
                            <div>
                                <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 0.25rem;">${i18n.t('scheduled_for')}</div>
                                <div style="font-weight: 600;">${Utils.formatDate(post.scheduled_time)}</div>
                            </div>
                        ` : ''}
                        ${post.published_at ? `
                            <div>
                                <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 0.25rem;">${i18n.t('published')}</div>
                                <div style="font-weight: 600;">${Utils.formatDate(post.published_at)}</div>
                            </div>
                        ` : ''}
                    </div>

                    ${post.publications && post.publications.length > 0 ? `
                        <div style="margin-bottom: 1.5rem;">
                            <div style="font-weight: 600; margin-bottom: 0.75rem;">${i18n.t('publications_on_pages')}</div>
                            <div style="display: grid; gap: 0.5rem;">
                                ${post.publications.map(pub => `
                                    <div style="padding: 0.75rem; background: var(--bg); border-radius: 0.375rem; border: 1px solid var(--border);">
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <span style="font-weight: 500;">${pub.page_name}</span>
                                            ${Utils.getStatusBadge(pub.status)}
                                        </div>
                                        ${pub.facebook_post_id ? `
                                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 0.25rem;">
                                                ID: ${pub.facebook_post_id}
                                            </div>
                                        ` : ''}
                                        ${pub.error_message ? `
                                            <div style="color: var(--danger); margin-top: 0.5rem; font-size: 13px;">
                                                ${pub.error_message}
                                            </div>
                                        ` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    ${post.analytics && post.analytics.length > 0 ? `
                        ${post.analytics.map(analytics => `
                            <div style="margin-bottom: 1.5rem;">
                                <div style="font-size: 14px; font-weight: 600; margin-bottom: 0.75rem; color: var(--text);">
                                    ${i18n.t('statistics')}: ${analytics.page_name}
                                </div>
                                <div class="grid grid-3" style="margin-bottom: 0.5rem;">
                                    <div class="stat-card">
                                        <div>
                                            <div class="stat-icon"><i class="bi bi-hand-thumbs-up"></i></div>
                                            <div class="stat-value">${analytics.likes || 0}</div>
                                        </div>
                                        <div class="stat-label">${i18n.t('likes')}</div>
                                    </div>
                                    <div class="stat-card">
                                        <div>
                                            <div class="stat-icon"><i class="bi bi-chat-dots"></i></div>
                                            <div class="stat-value">${analytics.comments || 0}</div>
                                        </div>
                                        <div class="stat-label">${i18n.t('comments')}</div>
                                    </div>
                                    <div class="stat-card">
                                        <div>
                                            <div class="stat-icon"><i class="bi bi-arrow-repeat"></i></div>
                                            <div class="stat-value">${analytics.shares || 0}</div>
                                        </div>
                                        <div class="stat-label">${i18n.t('shares')}</div>
                                    </div>
                                </div>
                                <div style="font-size: 12px; color: var(--text-secondary); text-align: center;">
                                    ${i18n.t('updated')} ${Utils.formatRelativeTime(analytics.updated_at)}
                                </div>
                            </div>
                        `).join('')}
                    ` : ''}
                </div>
                
                <div class="modal-footer">
                    ${post.status === 'published' ? `
                        <button class="btn btn-secondary" onclick="refreshPostAnalytics(${postId});">
                            <i class="bi bi-arrow-clockwise"></i> ${i18n.t('update_data')}
                        </button>
                    ` : ''}
                    <button class="btn btn-secondary" onclick="closeModal()">${i18n.t('close')}</button>
                </div>
            `;
            
            showModal(modal);
        }
    } catch (error) {
        console.error('View post error:', error);
        Utils.showMessage(i18n.t('post_loading_error') + ': ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

async function deletePost(postId) {
    if (!await Utils.confirm(t('confirm_delete_post'))) {
        return;
    }
    
    try {
        Utils.showLoading();
        
        await API.posts.delete(postId);
        
        Utils.showMessage(i18n.t('post_deleted'), 'success');
        await loadPage('posts');
    } catch (error) {
        console.error('Delete error:', error);
        Utils.showMessage('Помилка видалення: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

// ==================== АНАЛІТИКА ====================

async function collectAnalytics() {
    try {
        Utils.showLoading();
        
        const response = await API.analytics.collect();
        
        if (response.success) {
            Utils.showMessage(
                `Аналітика зібрана: ${response.collected} успішно, ${response.errors} помилок`,
                response.errors === 0 ? 'success' : 'info'
            );
            
            await loadPage('analytics');
        }
    } catch (error) {
        console.error('Collect analytics error:', error);
        Utils.showMessage('Помилка збору аналітики: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

// ==================== ШАБЛОНИ ====================

function showCreateTemplateModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-header">
            <h3 class="modal-title">Створити шаблон</h3>
            <button onclick="closeModal()" style="background: none; border: none; color: var(--text-secondary); cursor: pointer; padding: 0.25rem; font-size: 24px;">
                <i class="bi bi-x"></i>
            </button>
        </div>

        <div class="modal-body">
            <form id="create-template-form" onsubmit="handleCreateTemplate(event)">
                <div class="form-group">
                    <label class="form-label">Назва шаблону</label>
                    <input type="text" name="name" class="form-control" required>
                </div>

                <div class="form-group">
                    <label class="form-label">Тип</label>
                    <div class="flex gap-2">
                        <label class="flex" style="align-items: center; gap: 0.5rem;">
                            <input type="radio" name="is_ai_prompt" value="false" checked>
                            <span>Готовий текст</span>
                        </label>
                        <label class="flex" style="align-items: center; gap: 0.5rem;">
                            <input type="radio" name="is_ai_prompt" value="true">
                            <span>AI Промпт</span>
                        </label>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label">Контент</label>
                    <textarea name="content" class="form-control" rows="5" required></textarea>
                </div>
            </form>
        </div>

        <div class="modal-footer">
            <button type="submit" form="create-template-form" class="btn btn-primary">Створити</button>
            <button type="button" class="btn btn-secondary" onclick="closeModal()">Скасувати</button>
        </div>
    `;

    showModal(modal);
}

async function handleCreateTemplate(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    try {
        Utils.showLoading();

        const response = await API.templates.create({
            name: formData.get('name'),
            content: formData.get('content'),
            is_ai_prompt: formData.get('is_ai_prompt') === 'true'
        });

        if (response.success) {
            Utils.showMessage('Шаблон створено', 'success');
            closeModal();
            await loadPage('templates');
        }
    } catch (error) {
        console.error('Create template error:', error);
        Utils.showMessage('Помилка створення шаблону: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

async function generateTemplatesFromAI() {
    if (!await Utils.confirm(t('confirm_generate_templates'))) {
        return;
    }

    try {
        Utils.showLoading('Генерація AI шаблонів...');

        const response = await API.request('/api/templates/generate-from-recommendations', {
            method: 'POST'
        });

        if (response.success) {
            Utils.showMessage(`Створено ${response.templates.length} шаблонів на основі AI рекомендацій`, 'success');
            await loadPage('templates');
        } else {
            Utils.showMessage(response.message || 'Помилка генерації шаблонів', 'error');
        }
    } catch (error) {
        console.error('Generate templates error:', error);
        Utils.showMessage('Помилка генерації шаблонів: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

async function useTemplate(templateId, content, isAiPrompt) {
    try {
        navigateTo('create');

        if (isAiPrompt) {
            setTimeout(async () => {
                const aiRadio = document.querySelector('input[name="creation_mode"][value="ai"]');
                const promptField = document.getElementById('ai-prompt');
                const contentField = document.getElementById('post-content');

                if (aiRadio) {
                    aiRadio.checked = true;
                    toggleCreationMode();
                }

                if (promptField) {
                    promptField.value = content;
                }

                Utils.showLoading('Генерація тексту з AI шаблону...');
                try {
                    const response = await API.posts.generateAI({
                        prompt: content,
                        min_length: 150,
                        max_length: 500,
                        use_recommendations: true
                    });

                    if (response.success && response.text && contentField) {
                        contentField.value = response.text;
                        updateCharCount();
                        Utils.showSuccess('Текст згенеровано на основі шаблону');
                    }
                } catch (error) {
                    Utils.showError('Помилка генерації: ' + error.message);
                } finally {
                    Utils.hideLoading();
                }
            }, 200);
        } else {
            setTimeout(() => {
                const contentField = document.getElementById('post-content');
                if (contentField) {
                    contentField.value = content;
                    updateCharCount();
                }
            }, 100);
        }
    } catch (error) {
        Utils.showError('Помилка: ' + error.message);
    }
}

async function deleteTemplate(templateId) {
    if (!confirm(t('confirm_delete_template'))) return;

    try {
        Utils.showLoading();
        await API.request(`/api/templates/${templateId}`, { method: 'DELETE' });
        Utils.showSuccess('Шаблон видалено');

        // Перезавантажуємо сторінку шаблонів
        const pageContent = await Pages.templates();
        const contentDiv = document.getElementById('content');
        if (contentDiv) {
            contentDiv.innerHTML = pageContent;
        }
    } catch (error) {
        Utils.showError('Помилка: ' + error.message);
    } finally {
        Utils.hideLoading();
    }
}

// ==================== НАЛАШТУВАННЯ ====================

async function saveAccessToken() {
    const tokenInput = document.getElementById('user-token-input');
    const token = tokenInput.value.trim();
    
    if (!token) {
        Utils.showMessage('Введіть токен доступу', 'error');
        return;
    }
    
    try {
        Utils.showLoading();
        
        // Відправляємо токен на сервер
        const response = await API.request('/api/config/token', {
            method: 'POST',
            body: JSON.stringify({ access_token: token })
        });
        
        if (response.success) {
            Utils.showMessage('Токен збережено успішно!', 'success');
            tokenInput.value = '';
            
            // Автоматично оновлюємо сторінки
            setTimeout(() => refreshPages(), 1000);
        }
    } catch (error) {
        console.error('Save token error:', error);
        Utils.showMessage('Помилка збереження токену: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

async function handleAddPage(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    try {
        Utils.showLoading();
        
        const response = await API.request('/api/pages/add', {
            method: 'POST',
            body: JSON.stringify({
                page_id: formData.get('page_id'),
                page_name: formData.get('page_name'),
                page_token: formData.get('page_token')
            })
        });
        
        if (response.success) {
            Utils.showMessage('Сторінку додано успішно!', 'success');
            form.reset();
            await loadPage('settings');
        }
    } catch (error) {
        console.error('Add page error:', error);
        Utils.showMessage('Помилка додавання сторінки: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

async function removePage(pageId) {
    if (!await Utils.confirm(t('confirm_remove_page'))) {
        return;
    }

    try {
        Utils.showLoading();

        const response = await API.request(`/api/pages/${pageId}`, {
            method: 'DELETE'
        });

        if (response.success) {
            Utils.showMessage('Сторінку видалено', 'success');
            await loadPage('settings');
        }
    } catch (error) {
        console.error('Remove page error:', error);
        Utils.showMessage('Помилка видалення сторінки: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

// ==================== FACEBOOK OAUTH ====================

async function connectFacebook() {
    try {
        const token = localStorage.getItem('jwt_token');
        if (!token) {
            Utils.showMessage('Потрібно авторизуватися', 'error');
            return;
        }

        // Редирект на OAuth endpoint з токеном
        window.location.href = `/api/auth/facebook/login?token=${token}`;
    } catch (error) {
        console.error('Connect Facebook error:', error);
        Utils.showMessage('Помилка підключення Facebook: ' + error.message, 'error');
    }
}

async function disconnectFacebook() {
    if (!await Utils.confirm(t('confirm_disconnect_facebook'))) {
        return;
    }

    try {
        Utils.showLoading();

        const response = await API.request('/api/auth/facebook/disconnect', {
            method: 'POST'
        });

        if (response.success) {
            Utils.showMessage('Facebook відключено', 'success');
            await loadPage('settings');
        }
    } catch (error) {
        console.error('Disconnect Facebook error:', error);
        Utils.showMessage('Помилка відключення: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

async function refreshFacebookPages() {
    try {
        Utils.showLoading();

        const response = await API.request('/api/auth/facebook/refresh-pages', {
            method: 'POST'
        });

        if (response.success) {
            Utils.showMessage(`Оновлено ${response.pages_count} сторінок`, 'success');
            await loadPage('settings');
        }
    } catch (error) {
        console.error('Refresh Facebook pages error:', error);
        Utils.showMessage('Помилка оновлення сторінок: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

// ==================== МОДАЛЬНІ ВІКНА ====================

function showModal(modalElement) {
    const overlay = document.getElementById('modal-overlay');
    overlay.innerHTML = '';
    overlay.appendChild(modalElement);
    overlay.classList.add('active');
    
    // Закриття по кліку на overlay
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeModal();
        }
    });
}

function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    overlay.classList.remove('active');
    overlay.innerHTML = '';
}

async function saveAppCredentials(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    const appId = formData.get('app_id').trim();
    const appSecret = formData.get('app_secret').trim();
    const accessToken = formData.get('access_token').trim();
    
    if (!accessToken) {
        Utils.showMessage('Введіть Access Token', 'error');
        return;
    }
    
    try {
        Utils.showLoading();
        
        const response = await API.request('/api/config/token', {
            method: 'POST',
            body: JSON.stringify({
                access_token: accessToken,
                app_id: appId || null,
                app_secret: appSecret || null
            })
        });
        
        if (response.success) {
            const tokenInfo = response.token_info;
            
            if (tokenInfo.is_long_lived) {
                Utils.showMessage(
                    `✓ Токен обмінено на Long-Lived! Дійсний ${tokenInfo.days_left} днів`,
                    'success'
                );
            } else {
                Utils.showMessage('Токен збережено', 'success');
            }
            
            form.reset();
            setTimeout(() => refreshPages(), 1000);
        }
    } catch (error) {
        console.error('Save credentials error:', error);
        Utils.showMessage('Помилка: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}


// ==================== ПОКРАЩЕНА АНАЛІТИКА ====================

/**
 * Оновлює аналітику для окремого поста
 */
async function refreshPostAnalytics(postId) {
    try {
        Utils.showLoading();
        
        const response = await API.analytics.collectForPost(postId);
        
        if (response.success) {
            const message = `Аналітику оновлено: ${response.collected} успішно, ${response.errors} помилок`;
            Utils.showMessage(message, response.errors === 0 ? 'success' : 'info');
            
            // Оновлюємо поточну сторінку
            await loadPage(currentPage);
            
            // Якщо це деталі поста, оновлюємо їх
            if (currentPage === 'posts') {
                await viewPost(postId);
            }
        }
    } catch (error) {
        console.error('Refresh analytics error:', error);
        Utils.showMessage('Помилка оновлення аналітики: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

/**
 * 🔄 Кнопка "Оновити все"
 * Оновлює аналітику для ВСІХ опублікованих постів (до 100 постів)
 */
async function refreshAllAnalytics() {
    if (!await Utils.confirm(t('confirm_refresh_all'))) {
        return;
    }
    
    try {
        Utils.showLoading();
        
        const response = await API.analytics.refreshAll();
        
        if (response.success) {
            if (response.total === 0) {
                Utils.showMessage(i18n.t('no_published_posts_to_update'), 'info');
            } else {
                Utils.showMessage(
                    `✅ ${response.message}\n` +
                    `Оброблено: ${response.total}, успішно: ${response.collected}, помилок: ${response.errors}`,
                    'success'
                );
            }
            
            // Оновлюємо сторінку
            await loadPage(currentPage);
        }
    } catch (error) {
        console.error('Refresh all analytics error:', error);
        Utils.showMessage('Помилка оновлення: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

// ==================== РЕКОМЕНДАЦІЇ ====================

async function generateNewRecommendations() {
    if (!await Utils.confirm(t('confirm_generate_recommendations'))) {
        return;
    }

    try {
        Utils.showLoading();

        // Спочатку перевіримо скільки у нас є постів з аналітикою
        const postsData = await API.posts.getAll();
        const publishedPosts = postsData.posts.filter(p => p.status === 'published');

        console.log('📊 Статистика перед генерацією рекомендацій:');
        console.log(`- Всього постів: ${postsData.posts.length}`);
        console.log(`- Опубліковано: ${publishedPosts.length}`);

        const response = await API.recommendations.generate(60, 10);

        console.log('📋 Відповідь API:', response);

        if (response.success) {
            Utils.showMessage(
                `✅ ${response.message}\n` +
                `Проаналізовано ${response.analyzed_count} постів`,
                'success'
            );

            // Оновлюємо сторінку
            await loadPage('recommendations');
        } else {
            Utils.showMessage(
                `❌ ${response.message || t('error_generation')}\n\n` +
                `${t('error_published_posts')} ${publishedPosts.length}\n` +
                t('error_refresh_analytics_hint'),
                'error'
            );
        }
    } catch (error) {
        console.error('Generate recommendations error:', error);
        Utils.showMessage('Помилка генерації: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

// ==================== ШАБЛОНИ ====================

async function applyRecommendationsToAI() {
    try {
        const recData = await API.recommendations.getLatest();
        const recommendation = recData.recommendation;

        if (!recommendation || !recommendation.recommendations.ai_insights) {
            Utils.showMessage(t('ai_recommendations_unavailable'), 'error');
            return;
        }

        const insights = recommendation.recommendations.ai_insights;
        const textLength = recommendation.recommendations.text_length;

        // Формуємо промпт на основі рекомендацій
        let recommendedPrompt = t('ai_prompt_intro') + '\n';

        if (insights.content_style) {
            recommendedPrompt += `\n${t('ai_prompt_style')}: ${insights.content_style}`;
        }
        if (insights.tone) {
            recommendedPrompt += `\n${t('ai_prompt_tone')}: ${insights.tone}`;
        }
        if (insights.effective_topics && insights.effective_topics.length > 0) {
            recommendedPrompt += `\n${t('ai_prompt_topics')}: ${insights.effective_topics.join(', ')}`;
        }
        if (insights.key_phrases && insights.key_phrases.length > 0) {
            recommendedPrompt += `\n${t('ai_prompt_phrases')}: ${insights.key_phrases.slice(0, 3).join(', ')}`;
        }
        if (insights.structure_tips) {
            recommendedPrompt += `\n${t('ai_prompt_structure')}: ${insights.structure_tips}`;
        }
        if (insights.emoji_usage) {
            recommendedPrompt += `\n${t('ai_prompt_emoji')}: ${insights.emoji_usage}`;
        }

        recommendedPrompt += `\n\n${t('ai_prompt_your_topic')}: `;

        // Вставляємо промпт у поле
        const promptInput = document.getElementById('ai-prompt');
        if (promptInput) {
            promptInput.value = recommendedPrompt;
            promptInput.focus();
            // Встановлюємо курсор в кінець
            promptInput.setSelectionRange(recommendedPrompt.length, recommendedPrompt.length);
        }

        // Оновлюємо мін/макс довжину
        const minLengthInput = document.getElementById('min-length');
        const maxLengthInput = document.getElementById('max-length');

        if (minLengthInput && textLength.min) {
            minLengthInput.value = textLength.min;
        }
        if (maxLengthInput && textLength.max) {
            maxLengthInput.value = textLength.max;
        }

        Utils.showMessage(t('ai_recommendations_applied'), 'success');
    } catch (error) {
        console.error('Apply recommendations error:', error);
        Utils.showMessage('Помилка: ' + error.message, 'error');
    }
}

async function generateTemplatesFromRecommendations() {
    if (!await Utils.confirm(t('confirm_create_templates_from_ai'))) {
        return;
    }

    try {
        Utils.showLoading();

        const response = await API.templates.generateFromRecommendations();

        if (response.success) {
            Utils.showMessage(
                `✅ ${response.message}\n` +
                `Створено ${response.templates.length} шаблонів`,
                'success'
            );

            // Оновлюємо сторінку шаблонів
            await loadPage('templates');
        } else {
            Utils.showMessage(response.message || 'Помилка генерації шаблонів', 'error');
        }
    } catch (error) {
        console.error('Generate templates error:', error);
        Utils.showMessage('Помилка генерації: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

// ==================== АНАЛІТИКА ====================

/**
 * 📊 Кнопка "Швидке оновлення"
 * Оновлює аналітику для постів за останні 7 днів (до 50 постів)
 */
async function quickRefreshAnalytics() {
    if (!await Utils.confirm(t('confirm_quick_refresh'))) {
        return;
    }

    try {
        Utils.showLoading();

        const response = await API.analytics.collect();

        if (response.success) {
            if (response.collected === 0 && response.errors === 0) {
                Utils.showMessage(i18n.t('no_posts_last_7_days'), 'info');
            } else {
                Utils.showMessage(
                    `✅ Аналітика оновлена за 7 днів\n` +
                    `Успішно: ${response.collected}, помилок: ${response.errors}`,
                    response.errors === 0 ? 'success' : 'info'
                );
            }
            
            // Оновлюємо сторінку
            await loadPage('analytics');
        }
    } catch (error) {
        console.error('Quick refresh analytics error:', error);
        Utils.showMessage('Помилка оновлення: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

/**
 * Показує детальну аналітику поста в модальному вікні
 */
async function showDetailedAnalytics(postId) {
    try {
        Utils.showLoading();
        
        const response = await API.analytics.getPostAnalytics(postId);
        
        if (response.success) {
            const { post, analytics, total } = response;
            
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.style.maxWidth = '800px';
            modal.innerHTML = `
                <div class="modal-header">
                    <h3 class="modal-title">📊 Детальна аналітика</h3>
                </div>
                
                <div>
                    <div class="card mb-2" style="background: var(--bg);">
                        <strong>Пост:</strong>
                        <p style="margin: 0.5rem 0;">${Utils.truncate(post.content, 200)}</p>
                        <small style="color: var(--text-secondary);">
                            Опубліковано: ${Utils.formatDate(post.published_at)}
                        </small>
                    </div>
                    
                    <div class="grid grid-4 mb-2" style="gap: 1rem;">
                        <div style="text-align: center; padding: 1rem; background: var(--bg); border-radius: 0.5rem;">
                            <div style="font-size: 2rem;">👍</div>
                            <div style="font-size: 1.5rem; font-weight: bold; margin: 0.5rem 0;">${Utils.formatNumber(total.likes)}</div>
                            <div style="color: var(--text-secondary); font-size: 0.875rem;">Лайків</div>
                        </div>
                        <div style="text-align: center; padding: 1rem; background: var(--bg); border-radius: 0.5rem;">
                            <div style="font-size: 2rem;">💬</div>
                            <div style="font-size: 1.5rem; font-weight: bold; margin: 0.5rem 0;">${Utils.formatNumber(total.comments)}</div>
                            <div style="color: var(--text-secondary); font-size: 0.875rem;">Коментарів</div>
                        </div>
                        <div style="text-align: center; padding: 1rem; background: var(--bg); border-radius: 0.5rem;">
                            <div style="font-size: 2rem;">🔄</div>
                            <div style="font-size: 1.5rem; font-weight: bold; margin: 0.5rem 0;">${Utils.formatNumber(total.shares)}</div>
                            <div style="color: var(--text-secondary); font-size: 0.875rem;">Репостів</div>
                        </div>
                        <div style="text-align: center; padding: 1rem; background: var(--bg); border-radius: 0.5rem;">
                            <div style="font-size: 2rem;">👁️</div>
                            <div style="font-size: 1.5rem; font-weight: bold; margin: 0.5rem 0;">${Utils.formatNumber(total.impressions)}</div>
                            <div style="color: var(--text-secondary); font-size: 0.875rem;">Показів</div>
                        </div>
                    </div>
                    
                    <button class="btn btn-secondary" onclick="closeModal()">${i18n.t('close')}</button>
                </div>
            `;
            
            showModal(modal);
        }
    } catch (error) {
        console.error('Show detailed analytics error:', error);
        Utils.showMessage('Помилка завантаження аналітики: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

/**
 * Фільтрує аналітику по періоду
 */
function filterAnalyticsByPeriod(period) {
    // Оновлюємо активну кнопку
    document.querySelectorAll('.filter-btn').forEach(btn => {
        if (btn.dataset.period == period) {
            btn.classList.remove('btn-secondary');
            btn.classList.add('btn-primary');
        } else {
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-secondary');
        }
    });

    // Фільтруємо пости по даті
    const rows = document.querySelectorAll('#best-posts-table tbody tr');
    const now = new Date();

    // Обчислюємо граничну дату для фільтра
    let cutoffDate = null;
    if (period !== 'all') {
        cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - parseInt(period));
    }

    console.log(`🔍 Фільтр: ${period}`);
    console.log(`📅 Поточна дата: ${now.toLocaleString('uk-UA')}`);
    if (cutoffDate) {
        console.log(`📅 Гранична дата: ${cutoffDate.toLocaleString('uk-UA')}`);
    }

    // Спочатку визначаємо які рядки показувати
    const rowsToShow = [];
    let hiddenCount = 0;

    rows.forEach((row, index) => {
        const postDateStr = row.dataset.postDate;

        if (!postDateStr) {
            console.warn(`⚠️ Пост #${index + 1}: немає дати`);
            row.style.display = 'none';
            hiddenCount++;
            return;
        }

        const postDate = new Date(postDateStr);

        if (isNaN(postDate.getTime())) {
            console.warn(`⚠️ Пост #${index + 1}: невалідна дата "${postDateStr}"`);
            row.style.display = 'none';
            hiddenCount++;
            return;
        }

        let showPost = true;

        if (period !== 'all') {
            // Порівнюємо дати напряму
            showPost = postDate >= cutoffDate;
            const daysAgo = (now - postDate) / (1000 * 60 * 60 * 24);
            console.log(`📝 Пост #${index + 1}: ${postDate.toLocaleDateString('uk-UA')} (${daysAgo.toFixed(1)} днів тому) - ${showPost ? '✓ показати' : '✗ приховати'}`);
        }

        if (showPost) {
            rowsToShow.push(row);
            row.style.display = '';
        } else {
            row.style.display = 'none';
            hiddenCount++;
        }
    });

    // Потім оновлюємо нумерацію
    rowsToShow.forEach((row, index) => {
        row.querySelector('td:first-child').textContent = index + 1;
    });

    console.log(`✅ Показано ${rowsToShow.length} постів, приховано ${hiddenCount}`);
}
