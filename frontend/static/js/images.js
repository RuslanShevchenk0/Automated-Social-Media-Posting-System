// Функції для роботи з зображеннями

// Глобальний масив для зберігання вибраних файлів
let selectedImages = [];

function handleImageSelect(event) {
    const files = Array.from(event.target.files);
    
    // Перевірка кількості
    if (selectedImages.length + files.length > 10) {
        Utils.showMessage('Максимум 10 зображень', 'error');
        return;
    }
    
    // Перевірка розміру кожного файлу (макс 5MB)
    const maxSize = 5 * 1024 * 1024; // 5MB
    for (const file of files) {
        if (file.size > maxSize) {
            Utils.showMessage(`Файл ${file.name} занадто великий (макс 5MB)`, 'error');
            return;
        }
    }
    
    // Додаємо файли
    selectedImages = selectedImages.concat(files);
    
    // Оновлюємо прев'ю
    updateImagePreview();
}

function updateImagePreview() {
    const preview = document.getElementById('image-preview');
    const counter = document.getElementById('image-count');
    
    if (!preview || !counter) return;
    
    // Оновлюємо лічильник
    if (selectedImages.length === 0) {
        counter.textContent = 'Не вибрано';
        counter.style.color = 'var(--text-secondary)';
    } else {
        counter.textContent = `Вибрано: ${selectedImages.length} ${selectedImages.length === 1 ? 'зображення' : 'зображень'}`;
        counter.style.color = 'var(--primary)';
    }
    
    // Очищаємо прев'ю
    preview.innerHTML = '';
    
    // Додаємо картки зображень
    selectedImages.forEach((file, index) => {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            const card = document.createElement('div');
            card.style.cssText = `
                position: relative;
                border: 2px solid var(--border);
                border-radius: 0.5rem;
                overflow: hidden;
                background: var(--bg);
            `;
            
            card.innerHTML = `
                <img src="${e.target.result}" 
                    style="width: 100%; height: 150px; object-fit: cover; display: block;">
                <button type="button" 
                    onclick="removeImage(${index})"
                    style="
                        position: absolute;
                        top: 0.5rem;
                        right: 0.5rem;
                        background: var(--danger);
                        color: white;
                        border: none;
                        border-radius: 50%;
                        width: 28px;
                        height: 28px;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 1rem;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    "
                    title="Видалити">
                    ✕
                </button>
                <div style="padding: 0.5rem; font-size: 0.75rem; color: var(--text-secondary);">
                    ${file.name}
                </div>
            `;
            
            preview.appendChild(card);
        };
        
        reader.readAsDataURL(file);
    });
}

function removeImage(index) {
    selectedImages.splice(index, 1);
    updateImagePreview();
    Utils.showMessage('Зображення видалено', 'success');
}

function clearSelectedImages() {
    selectedImages = [];
    updateImagePreview();
}
