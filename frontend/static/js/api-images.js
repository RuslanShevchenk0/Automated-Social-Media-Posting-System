// API для роботи з зображеннями

const ImageAPI = {
    /**
     * Завантажує зображення на сервер
     */
    async uploadImage(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch('/api/upload-image', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Помилка завантаження');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Upload error:', error);
            throw error;
        }
    },
    
    /**
     * Завантажує кілька зображень
     */
    async uploadMultiple(files) {
        const uploads = [];
        
        for (const file of files) {
            try {
                const result = await this.uploadImage(file);
                uploads.push(result);
            } catch (error) {
                console.error(`Помилка завантаження ${file.name}:`, error);
            }
        }
        
        return uploads;
    },
    
    /**
     * Видаляє зображення з сервера
     */
    async deleteImage(filename) {
        try {
            const response = await fetch(`/api/delete-image/${filename}`, {
                method: 'DELETE'
            });
            
            return await response.json();
        } catch (error) {
            console.error('Delete error:', error);
            throw error;
        }
    }
};
