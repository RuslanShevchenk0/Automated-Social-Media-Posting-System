// Обєкт з усіма сторінками
const Pages = {
    // ==================== ДАШБОРД ====================
    dashboard: async () => {
        try {
            Utils.showLoading();

            const [postsData, analyticsData, pagesData, recommendationData] = await Promise.all([
                API.posts.getAll(10, 0),
                API.analytics.getSummary(),
                API.pages.getAll(),
                API.recommendations.getLatest().catch(() => ({ recommendation: null }))
            ]);

            const posts = postsData.posts || [];
            const analytics = analyticsData.summary || {};
            const bestPosts = analyticsData.best_posts || [];
            // Трансформуємо дані для відображення
            const pages = (pagesData.pages || []).map(p => ({
                id: p.page_id,
                name: p.page_name || 'Без назви'
            }));
            const recommendation = recommendationData.recommendation;

            return `
                <div class="grid grid-4 mb-2">
                    <div class="stat-card">
                        <div>
                            <div class="stat-icon"><i class="bi bi-file-text"></i></div>
                            <div class="stat-value">${analytics.total_posts || 0}</div>
                        </div>
                        <div class="stat-label">${t('total_posts')}</div>
                    </div>
                    <div class="stat-card">
                        <div>
                            <div class="stat-icon"><i class="bi bi-hand-thumbs-up"></i></div>
                            <div class="stat-value">${Utils.formatNumber(analytics.total_likes || 0)}</div>
                        </div>
                        <div class="stat-label">${t('total_likes')}</div>
                    </div>
                    <div class="stat-card">
                        <div>
                            <div class="stat-icon"><i class="bi bi-chat-dots"></i></div>
                            <div class="stat-value">${Utils.formatNumber(analytics.total_comments || 0)}</div>
                        </div>
                        <div class="stat-label">${t('total_comments')}</div>
                    </div>
                    <div class="stat-card">
                        <div>
                            <div class="stat-icon"><i class="bi bi-arrow-repeat"></i></div>
                            <div class="stat-value">${Utils.formatNumber(analytics.total_shares || 0)}</div>
                        </div>
                        <div class="stat-label">${t('total_shares')}</div>
                    </div>
                </div>


                ${recommendation ? `
                    <div class="card mb-2" style="background: white; border: 1px solid var(--primary);">
                        <div class="card-header" style="border-bottom: 1px solid var(--border);">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h3 class="card-title" style="color: var(--primary); font-size: 14px;"><i class="bi bi-bullseye"></i> ${t('ai_insights')}</h3>
                                    <small style="color: var(--text-secondary); font-size: 12px;">${t('based_on_top_posts', {count: recommendation.analyzed_posts_count})}</small>
                                </div>
                                <button class="btn btn-sm btn-primary" onclick="navigateTo('recommendations')">
                                    ${t('view_details')} →
                                </button>
                            </div>
                        </div>

                        ${recommendation.recommendations.ai_insights ? `
                            <div style="margin-top: 0.75rem; padding: 1rem; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 0.5rem; border-left: 4px solid var(--primary);">
                                <div style="font-size: 15px; font-weight: 600; margin-bottom: 0.75rem; color: var(--primary);"><i class="bi bi-lightbulb"></i> ${t('style_and_tone')}</div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                                    ${recommendation.recommendations.ai_insights.content_style ? `
                                        <div>
                                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 0.25rem; font-weight: 600;">${t('style').toUpperCase()}</div>
                                            <div style="font-size: 14px; font-weight: 600; color: var(--text);">${recommendation.recommendations.ai_insights.content_style}</div>
                                        </div>
                                    ` : ''}
                                    ${recommendation.recommendations.ai_insights.tone ? `
                                        <div>
                                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 0.25rem; font-weight: 600;">${t('tone').toUpperCase()}</div>
                                            <div style="font-size: 14px; font-weight: 600; color: var(--text);">${recommendation.recommendations.ai_insights.tone}</div>
                                        </div>
                                    ` : ''}
                                </div>
                                ${recommendation.recommendations.ai_insights.effective_topics && recommendation.recommendations.ai_insights.effective_topics.length > 0 ? `
                                    <div style="margin-top: 0.75rem;">
                                        <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 0.5rem; font-weight: 600;">${t('topics').toUpperCase()}</div>
                                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                                            ${recommendation.recommendations.ai_insights.effective_topics.slice(0, 5).map(topic =>
                                                `<span style="padding: 0.375rem 0.75rem; background: white; border: 1px solid var(--primary); border-radius: 1rem; font-size: 13px; color: var(--text);">${topic}</span>`
                                            ).join('')}
                                        </div>
                                    </div>
                                ` : ''}
                            </div>
                        ` : ''}

                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-top: 0.75rem;">
                            <div style="padding: 0.75rem; background: var(--bg); border-radius: 0.375rem; text-align: center;">
                                <div style="color: var(--text); font-weight: 600; font-size: 14px;"><span style="color: var(--text-secondary); font-size: 11px; font-weight: 600;">${t('length_label')}</span> ${recommendation.recommendations.text_length.min}-${recommendation.recommendations.text_length.max}</div>
                            </div>

                            <div style="padding: 0.75rem; background: var(--bg); border-radius: 0.375rem; text-align: center;">
                                <div style="color: var(--text); font-weight: 600; font-size: 14px;"><span style="color: var(--text-secondary); font-size: 11px; font-weight: 600;">${t('time_label')}</span> ${recommendation.recommendations.posting_time?.hours?.slice(0, 2).map(h => h + ':00').join(', ') || 'N/A'}</div>
                            </div>

                            <div style="padding: 0.75rem; background: var(--bg); border-radius: 0.375rem; text-align: center;">
                                <div style="color: var(--text); font-weight: 600; font-size: 14px;"><span style="color: var(--text-secondary); font-size: 11px; font-weight: 600;">${t('photo_label')}</span> ${recommendation.recommendations.images.use ? recommendation.recommendations.images.optimal_count + ' ' + t('pieces_short') : t('optional')}</div>
                            </div>
                        </div>

                        ${recommendation.recommendations.summary ? `
                            <div style="margin-top: 0.75rem; padding: 0.75rem; background: var(--bg); border-radius: 0.375rem; border: 1px solid var(--border);">
                                <div style="font-size: 14px; color: var(--text-secondary); line-height: 1.5;">
                                    <i class="bi bi-lightbulb"></i> ${recommendation.recommendations.summary}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}

                <div class="grid grid-2">
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">${t('recent_posts_list')}</h3>
                        </div>
                        <div>
                            ${posts.slice(0, 5).map(post => `
                                <div class="post-item" style="margin-bottom: 1rem; padding: 1rem;">
                                    <div class="flex-between mb-1">
                                        <strong>${Utils.truncate(post.content, 50)}</strong>
                                        ${Utils.getStatusBadge(post.status)}
                                    </div>
                                    <div class="text-secondary" style="font-size: 0.875rem; color: var(--text-secondary);">
                                        ${Utils.formatDate(post.created_at)}
                                    </div>
                                </div>
                            `).join('')}
                            ${posts.length === 0 ? `<p style="text-align: center; color: var(--text-secondary);">${t('no_posts')}</p>` : ''}
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">${t('top_5_posts')}</h3>
                        </div>
                        <div>
                            ${bestPosts.map((post, index) => `
                                <div style="padding: 1rem; border-bottom: 1px solid var(--border);">
                                    <div class="flex-between mb-1">
                                        <span style="font-weight: 600;">${index + 1}. ${Utils.truncate(post.content, 40)}</span>
                                        <span style="color: var(--primary);"><i class="bi bi-hand-thumbs-up"></i> ${post.total_likes || 0}</span>
                                    </div>
                                </div>
                            `).join('')}
                            ${bestPosts.length === 0 ? '<p style="text-align: center; color: var(--text-secondary);">Немає даних</p>' : ''}
                        </div>
                    </div>
                </div>
                
                <div class="card mt-2">
                    <div class="card-header">
                        <h3 class="card-title">${t('connected_pages')} (${pages.length})</h3>
                    </div>
                    <div class="grid grid-3">
                        ${pages.map(page => `
                            <div style="padding: 1rem; border: 1px solid var(--border); border-radius: 0.5rem;">
                                <div style="font-weight: 600; margin-bottom: 0.5rem;">${page.name}</div>
                                <div style="font-size: 0.75rem; color: var(--text-secondary);">ID: ${page.id}</div>
                            </div>
                        `).join('')}
                        ${pages.length === 0 ? '<p style="text-align: center; color: var(--text-secondary);">Немає підключених сторінок</p>' : ''}
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Dashboard error:', error);
            return `<div class="alert alert-error">Помилка завантаження даних: ${error.message}</div>`;
        } finally {
            Utils.hideLoading();
        }
    },
    
    // ==================== СПИСОК ПОСТІВ ====================
    posts: async () => {
        try {
            Utils.showLoading();
            const data = await API.posts.getAll();
            const posts = data.posts || [];
            
            return `
                <div class="card">
                    <div class="card-header flex-between">
                        <h3 class="card-title">${t('all_posts')} (${posts.length})</h3>
                        <button class="btn btn-primary" onclick="navigateTo('create')">
                            <i class="bi bi-plus-circle"></i> ${t('create_post')}
                        </button>
                    </div>
                    
                    <div>
                        ${posts.map(post => `
                            <div class="post-item">
                                <div class="post-header">
                                    <div style="flex: 1;">
                                        <div class="flex gap-1 mb-1">
                                            ${Utils.getStatusBadge(post.status)}
                                            ${post.is_ai_generated ? '<span class="badge" style="background: #fef3c7; color: #92400e;"><i class="bi bi-robot"></i> AI</span>' : ''}
                                            ${post.image_urls && post.image_urls.length > 0 ? `<span class="badge" style="background: #dbeafe; color: #1e40af;"><i class="bi bi-image"></i> ${post.image_urls.length} фото</span>` : ''}
                                        </div>
                                        <div class="post-content">
                                            ${Utils.truncate(post.content, 200)}
                                        </div>
                                        <div class="post-meta">
                                            <span><i class="bi bi-calendar"></i> ${Utils.formatDate(post.created_at)}</span>
                                            ${post.scheduled_time ? `<span><i class="bi bi-clock"></i> ${Utils.formatDate(post.scheduled_time)}</span>` : ''}
                                            ${post.publications ? `<span><i class="bi bi-file-text"></i> ${post.publications.length} сторінок</span>` : ''}
                                        </div>
                                    </div>
                                    <div class="post-actions">
                                        ${post.status === 'draft' || post.status === 'scheduled' ? `
                                            <button class="btn btn-sm btn-success" onclick="publishPost(${post.id})">
                                                Опублікувати
                                            </button>
                                        ` : ''}
                                        <button class="btn btn-sm btn-secondary" onclick="viewPost(${post.id})">
                                            <i class="bi bi-eye"></i> ${t('view_button')}
                                        </button>
                                        <button class="btn btn-sm btn-icon-danger" onclick="deletePost(${post.id})" title="Видалити">
                                            <i class="bi bi-x-lg"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                        
                        ${posts.length === 0 ? `
                            <div style="text-align: center; padding: 3rem;">
                                <div style="font-size: 3rem; margin-bottom: 1rem;"><i class="bi bi-file-text"></i></div>
                                <h3>${t('no_posts')}</h3>
                                <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                                    ${t('create_first_post', {default: 'Створіть свій перший пост'})}
                                </p>
                                <button class="btn btn-primary" onclick="navigateTo('create')">
                                    ${t('create_post')}
                                </button>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Posts error:', error);
            return `<div class="alert alert-error">Помилка завантаження постів: ${error.message}</div>`;
        } finally {
            Utils.hideLoading();
        }
    },
    
    // ==================== СТВОРЕННЯ ПОСТА ====================
    create: async () => {
        try {
            const pagesData = await API.pages.getAll();
            // Трансформуємо дані для відображення
            const pages = (pagesData.pages || []).map(p => ({
                id: p.page_id,
                name: p.page_name || 'Без назви'
            }));

            // Завантажуємо рекомендації
            let recommendations = null;
            try {
                const recData = await API.recommendations.getLatest();
                recommendations = recData.recommendation;
            } catch (e) {
                console.log('Рекомендації недоступні:', e);
            }

            return `
                <div style="max-width: 100%; margin: 0 auto;">
                    ${recommendations ? `
                        <div class="card" style="margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <i class="bi bi-bullseye" style="font-size: 18px;"></i>
                                    <strong style="font-size: 15px;">${t('ai_insights')}</strong>
                                </div>
                                <button type="button" class="btn btn-sm btn-primary" onclick="applyRecommendationsToAI()">
                                    ${t('apply_to_prompt')}
                                </button>
                            </div>

                            ${recommendations.recommendations.ai_insights ? `
                                <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); padding: 1rem; border-radius: 0.5rem; margin-bottom: 0.75rem; border-left: 4px solid var(--primary);">
                                    <div style="font-size: 14px; font-weight: 600; margin-bottom: 0.75rem; color: var(--primary);"><i class="bi bi-lightbulb"></i> ${t('style_and_tone')}</div>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 0.75rem;">
                                        ${recommendations.recommendations.ai_insights.content_style ? `
                                            <div>
                                                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 0.25rem; font-weight: 600;">${t('style').toUpperCase()}</div>
                                                <div style="font-size: 14px; font-weight: 600; color: var(--text);">${recommendations.recommendations.ai_insights.content_style}</div>
                                            </div>
                                        ` : ''}
                                        ${recommendations.recommendations.ai_insights.tone ? `
                                            <div>
                                                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 0.25rem; font-weight: 600;">${t('tone').toUpperCase()}</div>
                                                <div style="font-size: 14px; font-weight: 600; color: var(--text);">${recommendations.recommendations.ai_insights.tone}</div>
                                            </div>
                                        ` : ''}
                                    </div>
                                    ${recommendations.recommendations.ai_insights.effective_topics && recommendations.recommendations.ai_insights.effective_topics.length > 0 ? `
                                        <div>
                                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 0.5rem; font-weight: 600;">${t('topics').toUpperCase()}</div>
                                            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                                                ${recommendations.recommendations.ai_insights.effective_topics.slice(0, 5).map(topic =>
                                                    `<span style="padding: 0.375rem 0.75rem; background: white; border: 1px solid var(--primary); border-radius: 1rem; font-size: 13px; color: var(--text);">${topic}</span>`
                                                ).join('')}
                                            </div>
                                        </div>
                                    ` : ''}
                                </div>
                            ` : ''}

                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem;">
                                <div style="padding: 0.75rem; background: var(--bg); border-radius: 0.375rem; text-align: center;">
                                    <div style="color: var(--text); font-weight: 600; font-size: 14px;"><span style="color: var(--text-secondary); font-size: 11px; font-weight: 600;">${t('length_label')}</span> ${recommendations.recommendations.text_length.min}-${recommendations.recommendations.text_length.max}</div>
                                </div>
                                <div style="padding: 0.75rem; background: var(--bg); border-radius: 0.375rem; text-align: center;">
                                    <div style="color: var(--text); font-weight: 600; font-size: 14px;"><span style="color: var(--text-secondary); font-size: 11px; font-weight: 600;">${t('time_label')}</span> ${recommendations.recommendations.posting_time?.hours?.slice(0, 2).map(h => h + ':00').join(', ') || 'N/A'}</div>
                                </div>
                                <div style="padding: 0.75rem; background: var(--bg); border-radius: 0.375rem; text-align: center;">
                                    <div style="color: var(--text); font-weight: 600; font-size: 14px;"><span style="color: var(--text-secondary); font-size: 11px; font-weight: 600;">${t('photo_label')}</span> ${recommendations.recommendations.images.use ? `${recommendations.recommendations.images.optimal_count} ${t('pieces_short')}` : t('optional')}</div>
                                </div>
                            </div>
                        </div>
                    ` : ''}

                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">${t('create_post')}</h3>
                        </div>

                    <form id="create-post-form" onsubmit="handleCreatePost(event)" style="padding-left: 2rem; padding-right: 2rem;">
                        <div class="form-group">
                            <label class="form-label">${t('creation_mode')}</label>
                            <div class="flex gap-2">
                                <label class="flex" style="align-items: center; gap: 0.5rem;">
                                    <input type="radio" name="creation_mode" value="manual" checked onchange="toggleCreationMode()">
                                    <span>${t('manual')}</span>
                                </label>
                                <label class="flex" style="align-items: center; gap: 0.5rem;">
                                    <input type="radio" name="creation_mode" value="ai" onchange="toggleCreationMode()">
                                    <span><i class="bi bi-robot"></i> ${t('ai_generation')}</span>
                                </label>
                            </div>
                        </div>

                        <div id="ai-prompt-section" style="display: none; background: var(--bg); padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
                            <div class="form-group">
                                <label class="form-label">${t('ai_prompt')}</label>
                                <textarea id="ai-prompt" class="form-control"
                                    placeholder="${t('ai_prompt_placeholder')}"></textarea>
                            </div>
                            <div class="grid grid-2">
                                <div class="form-group">
                                    <label class="form-label">${t('min_length')}</label>
                                    <input type="number" id="min-length" class="form-control" value="${localStorage.getItem('ai_min_length') || 100}" min="50" max="500">
                                </div>
                                <div class="form-group">
                                    <label class="form-label">${t('max_length')}</label>
                                    <input type="number" id="max-length" class="form-control" value="${localStorage.getItem('ai_max_length') || 300}" min="100" max="1000">
                                </div>
                            </div>
                            <button type="button" class="btn btn-primary" onclick="generateAIText()">
                                <i class="bi bi-robot"></i> ${t('generate_text')}
                            </button>
                        </div>

                        <div class="form-group">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                <label class="form-label" style="margin: 0;">${t('post_content')} *</label>
                                <div id="text-length-indicator" style="font-size: 0.875rem;">
                                    <span id="char-count">0</span> ${t('characters')}
                                </div>
                            </div>
                            <textarea id="post-content" name="content" class="form-control" required
                                placeholder="${t('post_content_placeholder')}" oninput="updateCharCount()"></textarea>
                        </div>

                        <div class="form-group">
                            <label class="form-label"><i class="bi bi-image"></i> ${t('images')} (${t('recommended', {default: 'опціонально'})})</label>
                            <div style="margin-bottom: 1rem;">
                                <input type="file" id="image-upload" accept="image/*" multiple
                                    style="display: none;" onchange="handleImageSelect(event)">
                                <button type="button" class="btn btn-secondary" onclick="document.getElementById('image-upload').click()">
                                    📁 ${t('select_images')}
                                </button>
                                <span id="image-count" style="margin-left: 1rem; color: var(--text-secondary); font-size: 0.875rem;">
                                    ${t('no_images_selected')}
                                </span>
                            </div>

                            <div id="image-preview" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 1rem;">
                                <!-- Прев'ю зображень -->
                            </div>

                            <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 1rem;">
                                <i class="bi bi-lightbulb"></i> ${t('image_hint')}
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">${t('link_optional')}</label>
                            <input type="url" name="link" class="form-control"
                                placeholder="https://example.com">
                        </div>

                        <div class="form-group">
                            <label class="form-label">${t('select_pages')} *</label>
                            <div class="checkbox-group">
                                ${pages.map(page => `
                                    <label class="checkbox-item">
                                        <input type="checkbox" name="pages" value="${page.id}">
                                        <span>${page.name}</span>
                                    </label>
                                `).join('')}
                            </div>
                            ${pages.length === 0 ? `
                                <div class="alert alert-info">
                                    ${t('no_pages')}. ${t('go_to', {default: 'Перейдіть в'})} <a href="#" onclick="navigateTo('settings')">${t('nav_settings')}</a>
                                </div>
                            ` : ''}
                        </div>

                        <div class="form-group">
                            <label class="form-label">${t('publish_mode')}</label>
                            <div class="flex gap-2">
                                <label class="flex" style="align-items: center; gap: 0.5rem;">
                                    <input type="radio" name="publish_mode" value="now" checked onchange="toggleSchedule()">
                                    <span>${t('publish_now')}</span>
                                </label>
                                <label class="flex" style="align-items: center; gap: 0.5rem;">
                                    <input type="radio" name="publish_mode" value="schedule" onchange="toggleSchedule()">
                                    <span>${t('schedule')}</span>
                                </label>
                            </div>
                        </div>
                        
                        <div id="schedule-section" style="display: none;">
                            <div class="form-group">
                                <label class="form-label">${t('date_time')}</label>
                                <input type="datetime-local" id="scheduled-time" class="form-control">
                            </div>
                        </div>

                        <div class="flex gap-2">
                            <button type="submit" class="btn btn-primary">
                                ✓ ${t('create_post')}
                            </button>
                            <button type="button" class="btn btn-secondary" onclick="navigateTo('posts')">
                                ${t('cancel')}
                            </button>
                        </div>
                    </form>
                </div>
            `;
        } catch (error) {
            console.error('Create page error:', error);
            return `<div class="alert alert-error">${t('loading_error')}: ${error.message}</div>`;
        }
    },
    
    // ==================== АНАЛІТИКА ====================

    analytics: async () => {
        try {
            Utils.showLoading();

            const [summaryData, postsData] = await Promise.all([
                API.analytics.getSummary(),
                API.posts.getAll()
            ]);

            const summary = summaryData.summary || {};
            const bestPosts = summaryData.best_posts || [];
            const posts = postsData.posts || [];
            const publishedPosts = posts.filter(p => p.status === 'published');

            return `
                <div class="card mb-2" style="padding: 0.75rem;">
                    <div class="flex-between" style="align-items: center;">
                        <div>
                            <h3 class="card-title">${t('post_analytics')}</h3>
                            <p style="margin: 0.25rem 0 0 0; font-size: 0.875rem; color: var(--text-secondary);">
                                ${t('published_posts')}: ${publishedPosts.length}
                            </p>
                        </div>
                        <div style="display: flex; gap: 0.5rem;">
                            <button class="btn btn-primary" onclick="refreshAllAnalytics()" title="${t('refresh_all_tooltip')}">
                                <i class="bi bi-arrow-repeat"></i> ${t('refresh_all')}
                            </button>
                            <button class="btn btn-secondary" onclick="quickRefreshAnalytics()" title="${t('quick_refresh_tooltip')}">
                                <i class="bi bi-bar-chart"></i> ${t('quick_refresh')}
                            </button>
                        </div>
                    </div>
                </div>

                <div class="alert alert-info mb-2">
                    <strong><i class="bi bi-lightbulb"></i> ${t('hint')}:</strong>
                    <ul style="margin: 0.5rem 0 0 1.5rem; padding: 0;">
                        <li><strong>"${t('refresh_all')}"</strong> - ${t('refresh_all_description')}</li>
                        <li><strong>"${t('quick_refresh')}"</strong> - ${t('quick_refresh_description')}</li>
                    </ul>
                </div>

                ${publishedPosts.length === 0 ? `
                    <div class="alert alert-warning">
                        <p><i class="bi bi-exclamation-circle"></i> ${t('no_published_posts')}</p>
                        <p>${t('publish_first_for_analytics')}</p>
                    </div>
                ` : ''}
                
                <div class="grid grid-4 mb-2" style="margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div>
                            <div class="stat-icon"><i class="bi bi-hand-thumbs-up"></i></div>
                            <div class="stat-value">${Utils.formatNumber(summary.total_likes || 0)}</div>
                        </div>
                        <div class="stat-label">${t('likes')}</div>
                    </div>

                    <div class="stat-card">
                        <div>
                            <div class="stat-icon"><i class="bi bi-chat-dots"></i></div>
                            <div class="stat-value">${Utils.formatNumber(summary.total_comments || 0)}</div>
                        </div>
                        <div class="stat-label">${t('comments')}</div>
                    </div>

                    <div class="stat-card">
                        <div>
                            <div class="stat-icon"><i class="bi bi-arrow-repeat"></i></div>
                            <div class="stat-value">${Utils.formatNumber(summary.total_shares || 0)}</div>
                        </div>
                        <div class="stat-label">${t('shares')}</div>
                    </div>

                    <div class="stat-card">
                        <div>
                            <div class="stat-icon"><i class="bi bi-eye"></i></div>
                            <div class="stat-value">${Utils.formatNumber(summary.total_impressions || 0)}</div>
                        </div>
                        <div class="stat-label">${t('impressions')}</div>
                    </div>
                </div>

                ${bestPosts.length > 0 ? `
                    <div class="grid grid-2 mb-2">
                        <div class="card">
                            <div class="card-header">
                                <h4 class="card-title" style="margin: 0;"><i class="bi bi-graph-up-arrow"></i> ${t('activity_dynamics')}</h4>
                                <p style="margin: 0.25rem 0 0 0; font-size: 0.875rem; color: var(--text-secondary);">${t('cumulative_growth')}</p>
                            </div>
                            <div style="padding: 0.75rem 1.5rem 1rem 1.5rem;">
                                <canvas id="activityChart" style="max-height: 300px;"></canvas>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-header">
                                <h4 class="card-title" style="margin: 0;"><i class="bi bi-pie-chart-fill"></i> ${t('engagement_distribution')}</h4>
                                <p style="margin: 0.25rem 0 0 0; font-size: 0.875rem; color: var(--text-secondary);">${t('type_ratio')}</p>
                            </div>
                            <div style="padding: 0.5rem 1.5rem 1rem 1rem;">
                                <canvas id="distributionChart" style="max-height: 280px;"></canvas>
                            </div>
                        </div>
                    </div>
                ` : ''}

                ${bestPosts.length > 0 ? `
                    <div class="card mb-2">
                        <div class="card-header flex-between">
                            <h4 class="card-title" style="margin: 0;"><i class="bi bi-trophy"></i> ${t('top_10_posts')}</h4>
                            <div style="display: flex; gap: 0.5rem;" id="period-filter">
                                <button class="btn btn-sm btn-primary filter-btn" data-period="all" onclick="filterAnalyticsByPeriod('all')">
                                    ${t('all_time')}
                                </button>
                                <button class="btn btn-sm btn-secondary filter-btn" data-period="30" onclick="filterAnalyticsByPeriod(30)">
                                    ${t('30_days')}
                                </button>
                                <button class="btn btn-sm btn-secondary filter-btn" data-period="7" onclick="filterAnalyticsByPeriod(7)">
                                    ${t('7_days')}
                                </button>
                            </div>
                        </div>
                        <div id="best-posts-table">
                            <div style="overflow-x: auto;">
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th style="width: 50px;">#</th>
                                            <th>${t('post')}</th>
                                            <th style="text-align: center; width: 100px;"><i class="bi bi-hand-thumbs-up"></i> ${t('likes')}</th>
                                            <th style="text-align: center; width: 100px;"><i class="bi bi-chat-dots"></i> ${t('comm_short')}</th>
                                            <th style="text-align: center; width: 100px;"><i class="bi bi-arrow-repeat"></i> ${t('shares_short')}</th>
                                            <th style="text-align: center; width: 120px;"><i class="bi bi-eye"></i> ${t('impressions')}</th>
                                            <th style="text-align: center; width: 80px;">${t('actions')}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${bestPosts.map((post, index) => `
                                            <tr data-post-id="${post.id}" data-post-date="${post.published_at}">
                                                <td style="font-weight: 600; color: var(--text-secondary);">${index + 1}</td>
                                                <td style="max-width: 350px;">
                                                    <div style="font-weight: 500; margin-bottom: 0.25rem; line-height: 1.4;">
                                                        ${Utils.truncate(post.content, 100)}
                                                    </div>
                                                    <div style="display: flex; gap: 0.75rem; align-items: center;">
                                                        <small style="color: var(--text-secondary);">
                                                            <i class="bi bi-calendar"></i> ${Utils.formatDate(post.published_at)}
                                                        </small>
                                                        ${post.is_ai_generated ? `<span class="badge" style="background: #fef3c7; color: #92400e;"><i class="bi bi-robot"></i>&nbsp;AI</span>` : ''}
                                                        ${post.image_urls && JSON.parse(post.image_urls || '[]').length > 0 ? `<span class="badge" style="background: #dbeafe; color: #1e40af;"><i class="bi bi-image" style="margin-right: 6px;"></i>${t('photo')}</span>` : ''}
                                                    </div>
                                                </td>
                                                <td style="text-align: center; font-weight: 600;">${Utils.formatNumber(post.total_likes || 0)}</td>
                                                <td style="text-align: center; font-weight: 600;">${Utils.formatNumber(post.total_comments || 0)}</td>
                                                <td style="text-align: center; font-weight: 600;">${Utils.formatNumber(post.total_shares || 0)}</td>
                                                <td style="text-align: center; font-weight: 600; color: var(--primary);">${Utils.formatNumber(post.total_impressions || 0)}</td>
                                                <td style="text-align: center;">
                                                    <button
                                                        class="btn btn-sm btn-secondary"
                                                        onclick="showDetailedAnalytics(${post.id})"
                                                        title="${t('detailed_analytics')}">
                                                        <i class="bi bi-bar-chart"></i>
                                                    </button>
                                                </td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <div class="card" style="background: linear-gradient(135deg, #fefce8 0%, #fef3c7 100%); border: 2px solid var(--warning);">
                        <div class="card-header">
                            <h4 class="card-title" style="color: #92400e;">📈 ${t('performance_dynamics')}</h4>
                        </div>

                        <div class="grid grid-2">
                            <div style="padding: 1.5rem; background: white; border-radius: 0.5rem;">
                                <h5 style="margin-bottom: 1rem; color: var(--text);">${t('avg_engagement_rate')}</h5>
                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    <div style="flex: 1;">
                                        <div style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 0.5rem;">${t('all_posts')}</div>
                                        <div style="font-size: 2rem; font-weight: 700; color: var(--text);">
                                            ${summary.avg_engagement_rate ? (summary.avg_engagement_rate * 100).toFixed(2) + '%' : 'N/A'}
                                        </div>
                                    </div>
                                    <div style="font-size: 2rem; color: var(--primary);">→</div>
                                    <div style="flex: 1; text-align: right;">
                                        <div style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 0.5rem;">${t('top_10')}</div>
                                        <div style="font-size: 2rem; font-weight: 700; color: var(--success);">
                                            ${bestPosts.length > 0 && bestPosts[0].avg_engagement_rate
                                                ? (bestPosts.reduce((sum, p) => sum + (p.avg_engagement_rate || 0), 0) / bestPosts.length * 100).toFixed(2) + '%'
                                                : 'N/A'}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div style="padding: 1.5rem; background: white; border-radius: 0.5rem;">
                                <h5 style="margin-bottom: 1rem; color: var(--text);"><i class="bi bi-lightbulb"></i> ${t('insights')}</h5>
                                <div style="font-size: 0.875rem; line-height: 1.6;">
                                    <p style="margin-bottom: 0.75rem;">
                                        <strong><i class="bi bi-bar-chart"></i> ${t('analyzed')}:</strong> ${publishedPosts.length} ${t('published_posts').toLowerCase()}
                                    </p>
                                    <p style="margin-bottom: 0.75rem;">
                                        <strong><i class="bi bi-eye"></i> ${t('avg_impressions')}:</strong> ${Utils.formatNumber(summary.avg_impressions || 0)} ${t('views').toLowerCase()}
                                    </p>
                                    <p style="margin: 0;">
                                        <strong><i class="bi bi-heart"></i> ${t('engagement')}:</strong> ${Utils.formatNumber(summary.total_likes + summary.total_comments + summary.total_shares || 0)} ${t('interactions').toLowerCase()}
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div style="margin-top: 1rem; padding: 1rem; background: white; border-radius: 0.5rem; border-left: 4px solid var(--primary);">
                            <strong style="display: block; margin-bottom: 0.5rem; color: var(--primary);"><i class="bi bi-lightbulb"></i> ${t('tip')}:</strong>
                            <p style="margin: 0; font-size: 0.875rem; color: var(--text-secondary);">
                                ${t('use_recommendations_page')}
                                <a href="#" onclick="navigateTo('recommendations'); return false;" style="color: var(--primary); text-decoration: underline; margin-left: 0.5rem;">
                                    ${t('go_to_recommendations')} →
                                </a>
                            </p>
                        </div>
                    </div>
                ` : publishedPosts.length > 0 ? `
                    <div class="alert alert-info">
                        <p><i class="bi bi-info-circle"></i> ${t('click_quick_refresh')}</p>
                    </div>
                ` : ''}
            `;
        } catch (error) {
            console.error('Load analytics error:', error);
            return `<div class="alert alert-error">${t('loading_analytics_error')}: ${error.message}</div>`;
        } finally {
            Utils.hideLoading();
        }
    },
    
    // ==================== ШАБЛОНИ ====================
    // ==================== РЕКОМЕНДАЦІЇ ====================
    recommendations: async () => {
        try {
            Utils.showLoading();

            const [latestData, topPostsData] = await Promise.all([
                API.recommendations.getLatest(),
                API.recommendations.getTopPosts(7, 10, 'engagement_rate')
            ]);

            const recommendation = latestData.recommendation;
            const topPosts = topPostsData.posts || [];

            return `
                <div class="card mb-2">
                    <div class="card-header flex-between">
                        <h3 class="card-title"><i class="bi bi-bullseye"></i> ${t('ai_recommendations')}</h3>
                        <button class="btn btn-primary" onclick="generateNewRecommendations()">
                            <i class="bi bi-stars"></i> ${t('generate_new')}
                        </button>
                    </div>

                ${recommendation ? `
                    <div style="padding: 0.75rem;">
                    <!-- Поточні рекомендації -->
                    <div style="margin-bottom: 1rem;">
                        <div class="card-header" style="padding: 0.75rem;">
                            <h4 class="card-title" style="margin: 0 0 0.25rem 0; font-size: 1.125rem;"><i class="bi bi-bar-chart"></i> ${t('current_recommendations')}</h4>
                            <small style="color: var(--text-secondary); font-size: 0.8rem;">
                                ${t('based_on')} ${recommendation.analyzed_posts_count} ${t('posts').toLowerCase()} | ${Utils.formatDate(recommendation.created_at)}
                            </small>
                        </div>

                        ${recommendation.recommendations.ai_insights ? `
                            <div style="padding: 0.75rem; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 0.5rem; margin-bottom: 0.75rem; border-left: 3px solid var(--primary);">
                                <div style="font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem; color: var(--primary);"><i class="bi bi-lightbulb"></i> ${t('style_and_tone')}</div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.5rem;">
                                    ${recommendation.recommendations.ai_insights.content_style ? `
                                        <div>
                                            <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.2rem; font-weight: 600;">${t('style').toUpperCase()}</div>
                                            <div style="font-size: 0.875rem; font-weight: 600; color: var(--text);">${recommendation.recommendations.ai_insights.content_style}</div>
                                        </div>
                                    ` : ''}
                                    ${recommendation.recommendations.ai_insights.tone ? `
                                        <div>
                                            <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.2rem; font-weight: 600;">${t('tone').toUpperCase()}</div>
                                            <div style="font-size: 0.875rem; font-weight: 600; color: var(--text);">${recommendation.recommendations.ai_insights.tone}</div>
                                        </div>
                                    ` : ''}
                                </div>
                                ${recommendation.recommendations.ai_insights.effective_topics && recommendation.recommendations.ai_insights.effective_topics.length > 0 ? `
                                    <div>
                                        <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.4rem; font-weight: 600;">${t('topics').toUpperCase()}</div>
                                        <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                                            ${recommendation.recommendations.ai_insights.effective_topics.slice(0, 5).map(topic =>
                                                `<span style="padding: 0.25rem 0.6rem; background: white; border: 1px solid var(--primary); border-radius: 1rem; font-size: 0.75rem; color: var(--text);">${topic}</span>`
                                            ).join('')}
                                        </div>
                                    </div>
                                ` : ''}
                                ${recommendation.recommendations.ai_insights.key_phrases && recommendation.recommendations.ai_insights.key_phrases.length > 0 ? `
                                    <div style="margin-top: 0.5rem;">
                                        <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.4rem; font-weight: 600;">${t('key_phrases').toUpperCase()}</div>
                                        <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                                            ${recommendation.recommendations.ai_insights.key_phrases.map(phrase =>
                                                `<span style="padding: 0.25rem 0.6rem; background: white; border: 1px solid var(--success); border-radius: 1rem; font-size: 0.75rem; color: var(--text);">"${phrase}"</span>`
                                            ).join('')}
                                        </div>
                                    </div>
                                ` : ''}
                                ${recommendation.recommendations.ai_insights.structure_tips ? `
                                    <div style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid rgba(59, 130, 246, 0.2);">
                                        <div style="font-size: 0.8rem; color: var(--text-secondary);">${recommendation.recommendations.ai_insights.structure_tips}</div>
                                    </div>
                                ` : ''}
                            </div>
                        ` : ''}

                        <div class="grid grid-3 mb-2">
                            <div style="padding: 0.75rem; background: var(--bg); border-radius: 0.5rem; border-left: 3px solid var(--primary);">
                                <div style="color: var(--text-secondary); font-size: 0.75rem; margin-bottom: 0.25rem;"><i class="bi bi-file-text"></i> ${t('length').toUpperCase()}</div>
                                <div style="font-size: 1rem; font-weight: 600; color: var(--text);">
                                    ${recommendation.recommendations.text_length.min}-${recommendation.recommendations.text_length.max}
                                </div>
                                <div style="font-size: 0.75rem; color: var(--text-secondary);">${t('characters')}</div>
                            </div>

                            <div style="padding: 0.75rem; background: var(--bg); border-radius: 0.5rem; border-left: 3px solid var(--success);">
                                <div style="color: var(--text-secondary); font-size: 0.75rem; margin-bottom: 0.25rem;"><i class="bi bi-clock"></i> ${t('hours').toUpperCase()}</div>
                                <div style="font-size: 1rem; font-weight: 600; color: var(--text);">
                                    ${recommendation.recommendations.posting_time?.hours?.slice(0, 3).map(h => h + ':00').join(', ') || 'N/A'}
                                </div>
                            </div>

                            <div style="padding: 0.75rem; background: var(--bg); border-radius: 0.5rem; border-left: 3px solid var(--warning);">
                                <div style="color: var(--text-secondary); font-size: 0.75rem; margin-bottom: 0.25rem;"><i class="bi bi-calendar"></i> ${t('days').toUpperCase()}</div>
                                <div style="font-size: 0.875rem; font-weight: 600; color: var(--text);">
                                    ${recommendation.recommendations.posting_time?.days?.slice(0, 3).join(', ') || 'N/A'}
                                </div>
                            </div>
                        </div>

                        <div class="grid grid-2">
                            <div style="padding: 0.75rem; background: var(--bg); border-radius: 0.5rem;">
                                <div style="font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;"><i class="bi bi-image"></i> ${t('images')}</div>
                                <p style="margin: 0; font-size: 0.8rem; color: var(--text-secondary);">
                                    ${recommendation.recommendations.images.recommendation} - ${recommendation.recommendations.images.detail}
                                </p>
                            </div>

                            <div style="padding: 0.75rem; background: var(--bg); border-radius: 0.5rem;">
                                <div style="font-size: 0.875rem; font-weight: 600; margin-bottom: 0.5rem;"><i class="bi bi-link"></i> ${t('links')}</div>
                                <p style="margin: 0; font-size: 0.8rem; color: var(--text-secondary);">
                                    ${recommendation.recommendations.links.recommendation} (${recommendation.recommendations.links.percentage}%)
                                </p>
                            </div>
                        </div>
                    </div>
                    </div>
                ` : `
                    <div style="padding: 0.75rem;">
                        <div style="padding: 2rem; text-align: center; color: var(--text-secondary);">
                            <i class="bi bi-info-circle" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                            <h3 style="margin-bottom: 0.5rem; color: var(--text);">${t('no_recommendations')}</h3>
                            <p style="margin-bottom: 0;">${t('need_published_posts_for_recommendations')}</p>
                        </div>
                    </div>
                `}
                </div>

                <!-- Топ-10 постів тижня -->
                ${topPosts.length > 0 ? `
                    <div class="card">
                        <div class="card-header">
                            <h4 class="card-title"><i class="bi bi-trophy"></i> ${t('top_10_week_posts')}</h4>
                        </div>

                        <div style="overflow-x: auto;">
                            <table class="table">
                                <thead>
                                    <tr>
                                        <th>#</th>
                                        <th>${t('post')}</th>
                                        <th style="text-align: center;">${t('engagement_rate')}</th>
                                        <th style="text-align: center;"><i class="bi bi-hand-thumbs-up"></i></th>
                                        <th style="text-align: center;"><i class="bi bi-chat-dots"></i></th>
                                        <th style="text-align: center;"><i class="bi bi-arrow-repeat"></i></th>
                                        <th style="text-align: center;"><i class="bi bi-eye"></i></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${topPosts.map((post, index) => `
                                        <tr>
                                            <td style="font-weight: 600;">${index + 1}</td>
                                            <td style="max-width: 300px;">
                                                <div style="margin-bottom: 0.25rem;">${Utils.truncate(post.content, 80)}</div>
                                                <small style="color: var(--text-secondary);">
                                                    ${post.text_length || 0} ${t('characters')}
                                                    ${post.has_images ? ' | <i class="bi bi-image"></i> ' + post.image_count : ''}
                                                    ${post.has_link ? ' | <i class="bi bi-link"></i>' : ''}
                                                </small>
                                            </td>
                                            <td style="text-align: center;">
                                                <span class="badge" style="background: var(--success); color: white;">
                                                    ${(post.avg_engagement_rate * 100).toFixed(2)}%
                                                </span>
                                            </td>
                                            <td style="text-align: center;">${Utils.formatNumber(post.total_likes || 0)}</td>
                                            <td style="text-align: center;">${Utils.formatNumber(post.total_comments || 0)}</td>
                                            <td style="text-align: center;">${Utils.formatNumber(post.total_shares || 0)}</td>
                                            <td style="text-align: center;">${Utils.formatNumber(post.total_impressions || 0)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                ` : ''}
            `;
        } catch (error) {
            console.error('Recommendations error:', error);
            return `<div class="alert alert-error">${t('loading_recommendations_error')}: ${error.message}</div>`;
        } finally {
            Utils.hideLoading();
        }
    },

    templates: async () => {
        try {
            const data = await API.templates.getAll();
            const templates = data.templates || [];

            return `
                <div class="card mb-2">
                    <div class="card-header flex-between">
                        <h3 class="card-title">${t('post_templates')} (${templates.length})</h3>
                        <div style="display: flex; gap: 0.5rem;">
                            <button class="btn btn-secondary" onclick="generateTemplatesFromAI()">
                                <i class="bi bi-robot"></i> ${t('generate_from_ai')}
                            </button>
                            <button class="btn btn-primary" onclick="showCreateTemplateModal()">
                                <i class="bi bi-plus-circle"></i> ${t('create_template')}
                            </button>
                        </div>
                    </div>

                    <div class="grid grid-2">
                        ${templates.map(template => `
                            <div class="card">
                                <div class="flex-between mb-1">
                                    <strong>${template.name.replace('🎯 ', '')}</strong>
                                    ${template.is_ai_prompt ? '<span class="badge" style="background: #fef3c7; color: #92400e;"><i class="bi bi-robot"></i> ' + t('ai_prompt') + '</span>' : ''}
                                </div>
                                <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                                    ${Utils.truncate(template.content, 100)}
                                </p>
                                <div style="display: flex; gap: 0.5rem;">
                                    <button class="btn btn-sm btn-secondary" onclick="useTemplate(${template.id}, \`${template.content.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`, ${template.is_ai_prompt})">
                                        ${t('use')}
                                    </button>
                                    <button class="btn btn-sm btn-icon-danger" onclick="deleteTemplate(${template.id})" title="${t('delete')}">
                                        <i class="bi bi-x-lg"></i>
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>

                    ${templates.length === 0 ? `
                        <div style="text-align: center; padding: 3rem;">
                            <div style="font-size: 3rem; margin-bottom: 1rem;"><i class="bi bi-file-earmark"></i></div>
                            <h3>${t('no_templates')}</h3>
                            <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                                ${t('create_templates_for_quick_posts')}
                            </p>
                        </div>
                    ` : ''}
                </div>
            `;
        } catch (error) {
            return `<div class="alert alert-error">${t('error')}: ${error.message}</div>`;
        }
    },
    
    // ==================== НАЛАШТУВАННЯ ====================

    settings: async () => {
        try {
            const data = await API.pages.getAll();
            const pages = data.pages || [];

            // Отримуємо статус підключення Facebook
            let facebookStatus = null;
            try {
                facebookStatus = await API.request('/api/auth/facebook/status');
            } catch (e) {
                console.error('Facebook status error:', e);
            }

            return `
                <div class="card mb-2">
                    <div class="card-header">
                        <h3 class="card-title"><i class="bi bi-facebook"></i> ${t('facebook_connection')}</h3>
                    </div>

                    ${facebookStatus && facebookStatus.connected ? `
                        <div style="padding: 1rem; background: #d1fae5; border-radius: 0.5rem; border-left: 4px solid #10b981; margin-bottom: 1rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div style="font-size: 1rem; font-weight: 600; color: #065f46; margin-bottom: 0.25rem;">
                                        <i class="bi bi-check-circle"></i> ${t('facebook_connected')}
                                    </div>
                                    <div style="font-size: 0.875rem; color: #047857;">
                                        ${t('found')} ${facebookStatus.pages_count} ${t('pages').toLowerCase()}
                                    </div>
                                    ${facebookStatus.expires_at ? `
                                        <div style="font-size: 0.75rem; color: #047857; margin-top: 0.25rem;">
                                            ${t('valid_until')}: ${new Date(facebookStatus.expires_at).toLocaleString(i18n.getLang() === 'uk' ? 'uk-UA' : 'en-US')}
                                        </div>
                                    ` : ''}
                                </div>
                                <button class="btn btn-secondary" onclick="disconnectFacebook()">
                                    <i class="bi bi-x-circle"></i> ${t('disconnect')}
                                </button>
                            </div>
                        </div>
                    ` : `
                        <div class="alert alert-info mb-2">
                            <strong><i class="bi bi-info-circle"></i> ${t('how_to_connect_facebook')}:</strong>
                            <ol style="margin: 0.5rem 0 0 1.5rem; padding: 0;">
                                <li>${t('fb_step_1')}</li>
                                <li>${t('fb_step_2')}</li>
                                <li>${t('fb_step_3')}</li>
                                <li>${t('fb_step_4')}</li>
                            </ol>
                        </div>

                        <div style="text-align: center; padding: 2rem;">
                            <button class="btn btn-primary" onclick="connectFacebook()" style="font-size: 1rem; padding: 0.75rem 1.5rem;">
                                <i class="bi bi-facebook" style="font-size: 1.25rem;"></i> ${t('connect_facebook')}
                            </button>
                        </div>
                    `}
                </div>

                <div class="card mb-2">
                    <div class="card-header flex-between">
                        <h3 class="card-title">${t('connected_pages')}</h3>
                        ${facebookStatus && facebookStatus.connected ? `
                            <button class="btn btn-primary" onclick="refreshFacebookPages()">
                                <i class="bi bi-arrow-repeat"></i> ${t('refresh_pages')}
                            </button>
                        ` : ''}
                    </div>

                    ${pages.length > 0 ? `
                        <div class="grid grid-2">
                            ${pages.map(page => `
                                <div class="card">
                                    <div class="flex-between mb-1">
                                        <h4 style="margin: 0;">${page.page_name || t('no_name')}</h4>
                                        <button class="btn btn-sm btn-icon-danger" onclick="removePage('${page.page_id}')" title="${t('delete')}">
                                            <i class="bi bi-x-lg"></i>
                                        </button>
                                    </div>
                                    <p style="font-size: 0.875rem; color: var(--text-secondary); margin: 0.5rem 0;">
                                        ID: ${page.page_id}
                                    </p>
                                    <div class="badge badge-published">✓ ${t('connected')}</div>
                                </div>
                            `).join('')}
                        </div>
                    ` : `
                        <div class="alert alert-info">
                            <p><strong>${t('no_connected_pages')}</strong></p>
                            <p>${facebookStatus && facebookStatus.connected ? t('click_refresh_to_load_pages') : t('connect_facebook_to_see_pages')}</p>
                        </div>
                    `}
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">${t('about_system')}</h3>
                    </div>
                    <p>${t('integrated_posting_system')}</p>
                    <div style="display: grid; gap: 0.5rem; margin-top: 1rem;">
                        <div><strong>${t('version')}:</strong> 1.0.0</div>
                        <div><strong>${t('tokens')}:</strong> Long-Lived (60 ${t('days').toLowerCase()})</div>
                    </div>
                </div>
            `;
        } catch (error) {
            return `<div class="alert alert-error">${t('error')}: ${error.message}</div>`;
        }
    },
};
