
/**
 * YouTube Downloader Pro - Enhanced Frontend
 */
class YouTubeDownloaderUI {
    constructor() {
        this.isDownloading = false;
        this.statusInterval = null;
        this.initElements();
        this.bindEvents();
        this.checkCookies();
        this.checkServerBusy();
    }

    initElements() {
        this.elements = {
            urlInput: document.getElementById('urlInput'),
            pasteBtn: document.getElementById('pasteBtn'),
            formatSelect: document.getElementById('formatSelect'),
            qualitySelect: document.getElementById('qualitySelect'),
            downloadBtn: document.getElementById('downloadBtn'),
            cancelBtn: document.getElementById('cancelBtn'),
            statusDisplay: document.getElementById('statusDisplay'),
            speedText: document.getElementById('speedText'),
            etaText: document.getElementById('etaText'),
            sizeText: document.getElementById('sizeText'),
            downloadedText: document.getElementById('downloadedText'),
            progressContainer: document.getElementById('progressContainer'),
            progressFill: document.getElementById('progressFill'),
            progressText: document.getElementById('progressText'),
            progressMessage: document.getElementById('progressMessage'),
            statusMessage: document.getElementById('statusMessage'),
            fileInfo: document.getElementById('fileInfo'),
            fileName: document.getElementById('fileName'),
            fileLocation: document.getElementById('fileLocation'),
            fileStatus: document.getElementById('fileStatus'),
            notificationContainer: document.getElementById('notificationContainer'),
            statusIndicator: document.getElementById('statusIndicator')
        };
    }

    bindEvents() {
        this.elements.pasteBtn.addEventListener('click', () => this.pasteFromClipboard());
        this.elements.downloadBtn.addEventListener('click', () => this.startDownload());
        this.elements.cancelBtn.addEventListener('click', () => this.cancelDownload());
        this.elements.formatSelect.addEventListener('change', () => this.onFormatChange());
        
        this.elements.urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.startDownload();
        });
        
        // Cek server status setiap 10 detik
        setInterval(() => this.checkServerStatus(), 10000);
    }

    async pasteFromClipboard() {
        try {
            const text = await navigator.clipboard.readText();
            this.elements.urlInput.value = text;
            this.showNotification('URL berhasil ditempel!', 'success');
        } catch (err) {
            console.error('Gagal membaca clipboard:', err);
            this.showNotification('Gagal membaca clipboard', 'error');
        }
    }

    onFormatChange() {
        const format = this.elements.formatSelect.value;
        if (format === 'audio') {
            this.elements.qualitySelect.innerHTML = `
                <option value="best">Kualitas Terbaik (320kbps)</option>
            `;
        } else {
            this.elements.qualitySelect.innerHTML = `
                <option value="best">Terbaik (1080p atau lebih)</option>
                <option value="720p">HD 720p</option>
                <option value="480p">SD 480p</option>
                <option value="360p">360p</option>
            `;
        }
    }

    async checkCookies() {
        try {
            const response = await fetch('/api/check-cookies');
            const data = await response.json();
            if (!data.has_cookies) {
                this.showNotification('Browser cookies tidak ditemukan. Video dengan batasan usia mungkin gagal.', 'warning');
            }
        } catch (error) {
            console.error('Error checking cookies:', error);
        }
    }

    async checkServerBusy() {
        try {
            const response = await fetch('/api/is-busy');
            const data = await response.json();
            if (data.busy) {
                this.showNotification('Server sedang sibuk, tunggu sampai selesai', 'warning');
                this.startStatusPolling();
            }
        } catch (error) {
            console.error('Error checking server status:', error);
        }
    }

    async checkServerStatus() {
        if (!this.isDownloading) {
            try {
                const response = await fetch('/api/is-busy');
                const data = await response.json();
                if (data.busy && !this.isDownloading) {
                    // Jika server busy tapi UI tidak menunjukkan downloading
                    this.showNotification('Server sedang memproses download...', 'info');
                    this.isDownloading = true;
                    this.elements.downloadBtn.disabled = true;
                    this.elements.cancelBtn.disabled = false;
                    this.elements.progressContainer.style.display = 'block';
                    this.startStatusPolling();
                }
            } catch (error) {
                console.error('Error checking server status:', error);
            }
        }
    }

    async startDownload() {
        const url = this.elements.urlInput.value.trim();
        
        if (!url || !this.isValidYouTubeURL(url)) {
            this.showNotification('Masukkan URL YouTube yang valid!', 'error');
            return;
        }

        // PERBAIKAN: Cek status server dulu
        try {
            const busyResponse = await fetch('/api/is-busy');
            const busyData = await busyResponse.json();
            if (busyData.busy) {
                this.showNotification('Server sedang sibuk, tunggu sampai selesai', 'warning');
                return;
            }
        } catch (error) {
            console.error('Error checking server busy:', error);
            this.showNotification('Gagal menghubungi server', 'error');
            return;
        }

        // PERBAIKAN: Cek apakah sudah downloading
        if (this.isDownloading) {
            this.showNotification('Download sedang berjalan, tunggu atau batalkan dulu', 'warning');
            return;
        }

        const format = this.elements.formatSelect.value;
        const quality = this.elements.qualitySelect.value;

        // Update UI
        this.isDownloading = true;
        this.elements.downloadBtn.disabled = true;
        this.elements.cancelBtn.disabled = false;
        this.elements.progressContainer.style.display = 'block';
        this.updateStatus('Mempersiapkan download...', 'info');
        this.updateFileStatus('Memulai...');
        
        // Update status indicator
        if (this.elements.statusIndicator) {
            this.elements.statusIndicator.classList.remove('idle');
            this.elements.statusIndicator.classList.add('downloading');
            this.elements.statusIndicator.querySelector('.status-label').textContent = 'Mengunduh';
        }

        // Reset URL input setelah memulai (mencegah download beruntun)
        this.elements.urlInput.value = '';

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    format: format,
                    quality: quality,
                    concurrent_fragments: 5
                })
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Gagal memulai download');
            }

            this.showNotification('Download dimulai!', 'success');
            this.startStatusPolling();

        } catch (error) {
            this.showNotification(error.message || 'Terjadi kesalahan', 'error');
            this.resetUI();
        }
    }

    startStatusPolling() {
        if (this.statusInterval) clearInterval(this.statusInterval);

        this.statusInterval = setInterval(async () => {
            if (!this.isDownloading) {
                clearInterval(this.statusInterval);
                return;
            }

            try {
                const response = await fetch('/api/status');
                const status = await response.json();

                this.updateProgress(status);

                if (status.status === 'completed') {
                    this.showNotification('Download selesai! ✅', 'success');
                    this.updateFileStatus('Selesai');
                    clearInterval(this.statusInterval);
                    setTimeout(() => this.resetUI(), 5000);
                } 
                else if (status.status === 'error') {
                    this.showNotification(`Gagal: ${status.error_message || status.message}`, 'error');
                    this.updateFileStatus('Gagal');
                    clearInterval(this.statusInterval);
                    setTimeout(() => this.resetUI(), 3000);
                }
                else if (status.status === 'cancelled') {
                    this.showNotification('Download dibatalkan', 'warning');
                    this.updateFileStatus('Dibatalkan');
                    clearInterval(this.statusInterval);
                    setTimeout(() => this.resetUI(), 2000);
                }
                else if (status.status === 'idle') {
                    // Jika status idle tapi UI masih menunjukkan downloading
                    this.showNotification('Download selesai', 'info');
                    clearInterval(this.statusInterval);
                    setTimeout(() => this.resetUI(), 2000);
                }

            } catch (error) {
                console.error('Error fetching status:', error);
                // Coba lagi setelah error
            }
        }, 1000);
    }

    updateProgress(status) {
        // Update progress bar
        const progress = status.progress || 0;
        this.elements.progressFill.style.width = `${progress}%`;
        this.elements.progressText.textContent = `${progress.toFixed(1)}%`;
        
        // Update progress message
        this.elements.progressMessage.textContent = status.message || 'Memproses...';

        // Update speed and ETA
        if (status.speed && status.speed !== '0 KB/s') {
            document.getElementById('speedText').textContent = status.speed;
            this.elements.progressMessage.nextElementSibling.textContent = `Kecepatan: ${status.speed}`;
        }
        if (status.eta && status.eta !== '--:--') {
            document.getElementById('etaText').textContent = status.eta;
        }
        
        // Update file size
        if (status.filesize && status.filesize !== '0 MB') {
            document.getElementById('sizeText').textContent = status.filesize;
        }
        
        // Update downloaded amount
        if (status.downloaded && status.downloaded !== '0 MB') {
            document.getElementById('downloadedText').textContent = status.downloaded;
        }

        // Update status message
        this.updateStatus(status.message, status.status);

        // Update file info
        if (status.filename) {
            this.elements.fileName.textContent = status.filename;
        }
        
        // Update file status
        switch(status.status) {
            case 'downloading':
                this.updateFileStatus('Mengunduh...');
                break;
            case 'starting':
                this.updateFileStatus('Memulai...');
                break;
            case 'error':
                this.updateFileStatus('Gagal');
                break;
            case 'cancelled':
                this.updateFileStatus('Dibatalkan');
                break;
            case 'completed':
                this.updateFileStatus('Selesai');
                break;
            case 'idle':
                this.updateFileStatus('Siap');
                break;
        }
    }

    updateStatus(message, type = 'info') {
        const icon = this.getStatusIcon(type);
        this.elements.statusMessage.innerHTML = `
            <i class="fas fa-${icon}"></i>
            <span>${message}</span>
        `;
        
        // Update color based on status
        const colors = {
            'info': '#3182CE',
            'downloading': '#FF0000',
            'completed': '#38A169',
            'error': '#E53E3E',
            'cancelled': '#ED8936',
            'starting': '#3182CE',
            'idle': '#718096'
        };
        
        const iconElement = this.elements.statusMessage.querySelector('i');
        if (iconElement && colors[type]) {
            iconElement.style.color = colors[type];
        }
    }

    updateFileStatus(status) {
        this.elements.fileStatus.textContent = status;
        
        // Color coding and class
        const statusClasses = {
            'Memulai...': 'status-downloading',
            'Mengunduh...': 'status-downloading',
            'Selesai': 'status-ready',
            'Gagal': 'status-error',
            'Dibatalkan': 'status-cancelled',
            'Menunggu': 'status-ready',
            'Siap': 'status-ready'
        };
        
        // Remove all status classes
        this.elements.fileStatus.className = 'info-value';
        
        // Add appropriate class
        if (statusClasses[status]) {
            this.elements.fileStatus.classList.add(statusClasses[status]);
        }
    }

    getStatusIcon(type) {
        const icons = {
            'info': 'info-circle',
            'downloading': 'sync-alt fa-spin',
            'completed': 'check-circle',
            'error': 'exclamation-circle',
            'cancelled': 'ban',
            'starting': 'play-circle',
            'idle': 'check-circle'
        };
        return icons[type] || 'info-circle';
    }

    async cancelDownload() {
        if (!this.isDownloading) return;
        
        if (!confirm('Yakin ingin membatalkan download?')) return;

        try {
            const response = await fetch('/api/cancel', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Download berhasil dibatalkan', 'warning');
                this.isDownloading = false;
                clearInterval(this.statusInterval);
                this.updateStatus('Download dibatalkan oleh pengguna', 'cancelled');
                this.updateFileStatus('Dibatalkan');
                setTimeout(() => this.resetUI(), 2000);
            } else {
                this.showNotification(data.message || 'Gagal membatalkan', 'error');
            }
        } catch (error) {
            this.showNotification('Gagal membatalkan: ' + error.message, 'error');
        }
    }

    resetUI() {
        this.isDownloading = false;
        this.elements.downloadBtn.disabled = false;
        this.elements.cancelBtn.disabled = true;
        this.elements.progressContainer.style.display = 'none';
        this.elements.progressFill.style.width = '0%';
        this.elements.progressText.textContent = '0%';
        this.elements.progressMessage.textContent = '';
        
        // Reset status display
        document.getElementById('speedText').textContent = 'Menunggu...';
        document.getElementById('etaText').textContent = '--:--';
        document.getElementById('sizeText').textContent = '0 MB';
        document.getElementById('downloadedText').textContent = '0 MB';
        
        // Reset file info
        this.elements.fileName.textContent = '-';
        this.updateFileStatus('Menunggu');
        
        // Reset status indicator
        if (this.elements.statusIndicator) {
            this.elements.statusIndicator.classList.remove('downloading', 'error');
            this.elements.statusIndicator.classList.add('idle');
            this.elements.statusIndicator.querySelector('.status-label').textContent = 'Siap';
        }
        
        // Kosongkan input URL (PENTING: mencegah download beruntun)
        this.elements.urlInput.value = '';
        
        this.updateStatus('Masukkan URL YouTube untuk memulai download', 'info');
    }

    isValidYouTubeURL(url) {
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+/;
        return youtubeRegex.test(url);
    }

    showNotification(message, type = 'info') {
        // Create notification
        const notification = document.createElement('div');
        notification.className = 'notification';
        
        const icon = this.getNotificationIcon(type);
        const color = this.getNotificationColor(type);
        
        notification.innerHTML = `
            <div class="notification-content" style="
                background: ${this.getNotificationBgColor(type)};
                border-left: 4px solid ${color};
                color: white;
                padding: 15px 20px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                gap: 12px;
                min-width: 300px;
                max-width: 400px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.3);
            ">
                <i class="fas fa-${icon}" style="color: ${color}; font-size: 1.3rem;"></i>
                <span style="flex: 1; font-weight: 500;">${message}</span>
                <i class="fas fa-times" style="cursor: pointer; opacity: 0.8; font-size: 1rem;" onclick="this.parentElement.parentElement.remove()"></i>
            </div>
        `;
        
        // Style notification container
        if (!this.elements.notificationContainer) {
            this.elements.notificationContainer = document.createElement('div');
            this.elements.notificationContainer.id = 'notificationContainer';
            this.elements.notificationContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 10px;
            `;
            document.body.appendChild(this.elements.notificationContainer);
        }
        
        // Remove old notifications if too many
        const notifications = this.elements.notificationContainer.children;
        if (notifications.length > 3) {
            notifications[0].remove();
        }
        
        this.elements.notificationContainer.appendChild(notification);
        
        // Auto remove after 5 seconds
        const removeNotification = () => {
            notification.style.animation = 'slideOutRight 0.3s ease forwards';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        };
        
        const timeoutId = setTimeout(removeNotification, 5000);
        
        // Add click to dismiss to the close button
        notification.querySelector('.fa-times').addEventListener('click', () => {
            clearTimeout(timeoutId);
            removeNotification();
        });
    }

    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    getNotificationColor(type) {
        const colors = {
            'success': '#38A169',
            'error': '#E53E3E',
            'warning': '#ED8936',
            'info': '#3182CE'
        };
        return colors[type] || colors.info;
    }

    getNotificationBgColor(type) {
        const colors = {
            'success': 'rgba(56, 161, 105, 0.1)',
            'error': 'rgba(229, 62, 62, 0.1)',
            'warning': 'rgba(237, 137, 54, 0.1)',
            'info': 'rgba(49, 130, 206, 0.1)'
        };
        return colors[type] || colors.info;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    const downloader = new YouTubeDownloaderUI();
    window.youtubeDownloader = downloader; // Make accessible from console for debugging
    
    // Add some initial animation
    document.querySelector('.main-card').style.animation = 'fadeIn 0.8s ease-out';
});
