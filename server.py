#!/usr/bin/env python3
"""
YouTube Downloader Pro - Main Server (Fixed)
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import threading
import os
import sys
import time
import json
import subprocess

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, 'backend')
sys.path.append(backend_dir)

try:
    from yt_downloader import downloader
    print("✅ Backend module loaded successfully")
except ImportError as e:
    print(f"❌ Error importing backend module: {e}")
    print(f"📁 Current directory: {current_dir}")
    print(f"📁 Backend directory: {backend_dir}")
    print(f"📁 Directory contents: {os.listdir(current_dir)}")
    if os.path.exists(backend_dir):
        print(f"📁 Backend contents: {os.listdir(backend_dir)}")
    raise

app = Flask(__name__, static_folder='frontend')
CORS(app)  # Enable CORS for all routes

# Download management
download_active = False
download_lock = threading.Lock()

def ensure_directories():
    """Create required directories if they don't exist"""
    frontend_dir = os.path.join(current_dir, 'frontend')
    os.makedirs(frontend_dir, exist_ok=True)

    downloads_dir = os.path.expanduser("~/Downloads/YouTube_Downloads")
    os.makedirs(downloads_dir, exist_ok=True)

    print(f"📂 Frontend directory: {frontend_dir}")
    print(f"📂 Downloads directory: {downloads_dir}")

# Frontend Routes
@app.route('/')
def index():
    """Serve main HTML page"""
    frontend_dir = os.path.join(current_dir, 'frontend')
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/<path:filename>')
def serve_frontend(filename):
    """Serve static files from frontend directory"""
    frontend_dir = os.path.join(current_dir, 'frontend')
    return send_from_directory(frontend_dir, filename)

# API Routes
@app.route('/api/download', methods=['POST'])
def start_download():
    """Start a new download"""
    global download_active

    try:
        data = request.get_json()

        if not data or 'url' not in data:
            return jsonify({'error': 'URL diperlukan'}), 400

        # Check if already downloading — dalam 1 lock
        with download_lock:
            if download_active:
                return jsonify({'error': 'Download sedang berjalan, tunggu atau batalkan dulu'}), 400
            download_active = True

        # Extract parameters
        url = data['url'].strip()
        quality = data.get('quality', 'best')
        format_type = data.get('format', 'video')
        custom_path = data.get('path', None)
        concurrent_fragments = data.get('concurrent_fragments', 5)

        print(f"📥 Download request received:")
        print(f"   URL: {url}")
        print(f"   Quality: {quality}")
        print(f"   Format: {format_type}")
        print(f"   Path: {custom_path}")
        print(f"   Concurrent fragments: {concurrent_fragments}")

        # Validate URL
        if 'youtube.com' not in url and 'youtu.be' not in url and 'm.youtube.com' not in url:
            with download_lock:
                download_active = False
            return jsonify({'error': 'URL YouTube tidak valid'}), 400

        # Validate concurrent fragments
        try:
            concurrent_fragments = int(concurrent_fragments)
            if concurrent_fragments < 1 or concurrent_fragments > 10:
                concurrent_fragments = 5
        except:
            concurrent_fragments = 5

        # Start download in separate thread
        def download_task():
            global download_active
            try:
                downloader.download_video(
                    url=url,
                    quality=quality,
                    format_type=format_type,
                    custom_path=custom_path,
                    concurrent_fragments=concurrent_fragments
                )
            except Exception as e:
                print(f"❌ Error in download thread: {e}")
                import traceback
                traceback.print_exc()
            finally:
                with download_lock:
                    download_active = False

        download_thread = threading.Thread(target=download_task)
        download_thread.daemon = True
        download_thread.start()

        return jsonify({
            'message': 'Download dimulai',
            'status': 'starting',
            'concurrent_fragments': concurrent_fragments
        }), 202

    except Exception as e:
        print(f"❌ Error in start_download: {e}")
        import traceback
        traceback.print_exc()
        with download_lock:
            download_active = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current download status"""
    try:
        status = downloader.get_status()
        return jsonify(status)
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Error getting status',
            'error': True
        }), 500

@app.route('/api/cancel', methods=['POST'])
def cancel_download():
    """Cancel current download"""
    global download_active
    try:
        success = downloader.cancel_download()
        if success:
            with download_lock:
                download_active = False
            return jsonify({
                'success': True,
                'message': 'Download berhasil dibatalkan'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Tidak ada download yang aktif'
            })
    except Exception as e:
        print(f"❌ Error cancelling download: {e}")
        with download_lock:
            download_active = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/is-busy', methods=['GET'])
def check_busy():
    """Check if server is busy downloading"""
    with download_lock:
        return jsonify({
            'busy': download_active,
            'status': 'downloading' if download_active else 'idle'
        })

@app.route('/api/check-cookies', methods=['GET'])
def check_cookies():
    """Check if browser cookies are available"""
    try:
        browser = downloader.get_browser_cookies()
        return jsonify({
            'has_cookies': browser is not None,
            'browser': browser or 'Tidak ditemukan'
        })
    except Exception as e:
        print(f"❌ Error checking cookies: {e}")
        return jsonify({
            'has_cookies': False,
            'browser': 'Error checking'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'service': 'YouTube Downloader Pro',
        'version': '2.1.0',
        'busy': download_active
    })

@app.route('/api/debug-test', methods=['GET'])
def debug_test():
    """Test yt-dlp connectivity"""
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    try:
        cmd = ['yt-dlp', '--version']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        # Cek ffmpeg
        ffmpeg_version = None
        try:
            ffmpeg_result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            if ffmpeg_result.returncode == 0:
                ffmpeg_version = ffmpeg_result.stdout.split('\n')[0]
        except:
            ffmpeg_version = 'Not found'

        return jsonify({
            'yt_dlp_version': result.stdout.strip() if result.returncode == 0 else 'Not found',
            'ffmpeg_version': ffmpeg_version,
            'error': result.stderr[:200] if result.returncode != 0 else None,
            'test_url': test_url,
            'time': time.time()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Ensure directories exist
    ensure_directories()

    # Check dependencies
    print("=" * 60)
    print("🚀 YouTube Downloader PRO")
    print("=" * 60)

    # Check yt-dlp
    try:
        import yt_dlp
        ver = getattr(yt_dlp, '__version__', 'unknown')
        print(f"✅ yt-dlp tersedia (v{ver})")
    except ImportError:
        print("❌ yt-dlp tidak ditemukan. Install: pip install yt-dlp")
        sys.exit(1)

    # Check ffmpeg
    print("🎬 Memeriksa FFmpeg...", end=' ')
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            ffver = result.stdout.split('\n')[0].split(' ')[2]
            print(f"✅ FFmpeg tersedia (v{ffver})")
        else:
            print("⚠️ Tidak ditemukan — video HD (1080p) dan MP3 mungkin gagal")
    except:
        print("⚠️ Tidak ditemukan — video HD (1080p) dan MP3 mungkin gagal")

    # Print startup information
    print(f"📂 Working directory: {current_dir}")
    print("🌐 http://localhost:5000")
    print("📁 ~/Downloads/YouTube_Downloads")
    print("=" * 60)

    # Run the server
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            threaded=True,
            use_reloader=False
        )
    except Exception as e:
        print(f"❌ Gagal memulai server: {e}")
        print("💡 Tips:")
        print("1. Port 5000 terpakai: ganti port=5000 ke port=5001")
        print("2. Pastikan yt-dlp terinstall: pip install yt-dlp")
