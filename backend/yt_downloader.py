#!/usr/bin/env python3
"""
YouTube Downloader Backend - Fixed & Optimized Version
"""
import os
import subprocess
import threading
import time
import re
import json
from datetime import datetime
from pathlib import Path

class YouTubeDownloader:
    def __init__(self):
        self.current_process = None
        self.download_status = {
            'status': 'idle',
            'progress': 0,
            'message': 'Ready to download',
            'filename': '',
            'filepath': '',
            'error': False,
            'error_message': '',
            'speed': '0 KB/s',
            'eta': '--:--',
            'filesize': '0 MB',
            'downloaded': '0 MB'
        }
        self.download_lock = threading.Lock()
        self.last_update_time = time.time()
        self.current_url = None
        self.output_path = None

    def reset_status(self):
        """Reset download status to idle"""
        with self.download_lock:
            self.download_status = {
                'status': 'idle',
                'progress': 0,
                'message': 'Ready to download',
                'filename': '',
                'filepath': '',
                'error': False,
                'error_message': '',
                'speed': '0 KB/s',
                'eta': '--:--',
                'filesize': '0 MB',
                'downloaded': '0 MB'
            }
            self.current_url = None
            self.output_path = None
            self.current_process = None

    def get_browser_cookies(self):
        """Get cookies from browser - optimized with shorter timeout"""
        # Prioritaskan browser yang paling umum
        browsers = ['chrome', 'firefox', 'chromium']

        for browser in browsers:
            try:
                cmd = [
                    'yt-dlp',
                    '--cookies-from-browser', browser,
                    '--dump-json',
                    '--no-warnings',
                    '--simulate',
                    '--geo-bypass',
                    'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=8,  # Kurangi timeout dari 15 ke 8
                    env={**os.environ, 'DISPLAY': ':0', 'DBUS_SESSION_BUS_ADDRESS': ''}
                )

                if result.returncode == 0:
                    print(f"✅ Found cookies from: {browser}")
                    return browser
            except Exception as e:
                print(f"❌ Browser {browser}: {str(e)[:50]}")
                continue

        print("⚠️ No browser cookies found, using fallback method")
        return None

    def _extract_video_id(self, url):
        """Extract video ID dari URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:shorts\/)([0-9A-Za-z_-]{11})'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _check_ffmpeg(self):
        """Check if ffmpeg is installed"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return True
        except:
            pass
        return False

    def _download_with_ytdlp_aggressive(self, url, quality, format_type, concurrent_fragments, custom_path=None):
        """Optimized method untuk download YouTube video"""
        try:
            # Setup save path: prioritaskan custom_path
            if custom_path and os.path.isdir(os.path.dirname(custom_path)):
                save_path = custom_path
            else:
                home = os.path.expanduser("~")
                save_path = os.path.join(home, "Downloads", "YouTube_Downloads")

            os.makedirs(save_path, exist_ok=True)
            output_template = f'{save_path}/%(title)s.%(ext)s'

            # Cek FFmpeg
            has_ffmpeg = self._check_ffmpeg()
            if not has_ffmpeg:
                print("⚠️ FFmpeg tidak ditemukan! Merge video+audio dan konversi MP3 mungkin gagal.")

            # OPTIMIZED BYPASS OPTIONS — tanpa sleep interval, tanpa throttle cap
            cmd = [
                'yt-dlp',
                '--no-warnings',
                '--newline',
                '--progress',
                '--geo-bypass',
                '--geo-bypass-country', 'US',
                '--force-ipv4',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                '--referer', 'https://www.youtube.com/',
                '--retries', '10',
                '--fragment-retries', '10',
                '--skip-unavailable-fragments',
                '--concurrent-fragments', str(concurrent_fragments),
                '--extractor-args', 'youtube:player_client=android,ios,web',
                '--compat-options', 'no-youtube-unavailable-video',
                '--no-check-certificate',
                '-o', output_template
            ]

            # Format selection dengan FALLBACK
            if format_type == 'video':
                if quality == 'best':
                    cmd.extend(['-f', 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/bestvideo[height<=720]+bestaudio/best[height<=720]/best'])
                elif quality == '720p':
                    cmd.extend(['-f', 'bestvideo[height<=720]+bestaudio/best[height<=720]/bestvideo[height<=480]+bestaudio'])
                elif quality == '480p':
                    cmd.extend(['-f', 'bestvideo[height<=480]+bestaudio/best[height<=480]/bestvideo[height<=360]+bestaudio'])
                elif quality == '360p':
                    cmd.extend(['-f', 'bestvideo[height<=360]+bestaudio/best[height<=360]/worstvideo+worstaudio'])
                cmd.extend(['--merge-output-format', 'mp4'])
            elif format_type == 'audio':
                cmd.extend(['-f', 'bestaudio[acodec=mp4a]/bestaudio/bestaudio/best', '-x', '--audio-format', 'mp3', '--audio-quality', '320K'])

            cmd.append(url)

            print(f"🚀 Optimized download: {url}")
            print(f"📁 Save path: {save_path}")
            print(f"⚡ Concurrent fragments: {concurrent_fragments}")

            # SIMPAN KE self.current_process untuk cancel & monitoring
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )

            with self.download_lock:
                self.current_process = process

            # Monitor progress
            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if not line:
                    continue

                # Check for cancel
                with self.download_lock:
                    if self.download_status['status'] == 'cancelled':
                        process.terminate()
                        break

                # Parse progress
                self._parse_line(line)
                # print(f"📊 {line}")  # opsional — matikan biar log ga banjir

            # Wait for completion
            return_code = process.wait()

            with self.download_lock:
                self.current_process = None

            if return_code == 0:
                print(f"✅ Download successful to: {save_path}")
                return True
            else:
                print(f"❌ Download failed with code: {return_code}")
                return False

        except Exception as e:
            print(f"💥 Download error: {e}")
            import traceback
            traceback.print_exc()
            with self.download_lock:
                self.current_process = None
            return False

    def download_video(self, url, quality='best', format_type='video',
                      custom_path=None, max_speed=None, concurrent_fragments=5):
        """Download YouTube video"""

        # Reset status
        with self.download_lock:
            self.current_url = url
            self.download_status = {
                'status': 'starting',
                'progress': 0,
                'message': 'Preparing download...',
                'filename': '',
                'filepath': '',
                'error': False,
                'error_message': '',
                'speed': '0 KB/s',
                'eta': '--:--',
                'filesize': '0 MB',
                'downloaded': '0 MB'
            }
            self.last_update_time = time.time()

        print(f"🎯 Starting download: {url}")

        # Panggil dengan custom_path
        success = self._download_with_ytdlp_aggressive(
            url, quality, format_type, concurrent_fragments, custom_path
        )

        with self.download_lock:
            if success:
                self.download_status['status'] = 'completed'
                self.download_status['progress'] = 100
                self.download_status['message'] = 'Download completed successfully!'
                self.last_update_time = time.time()
                print("🎉 FINAL: Download completed!")
                return True
            else:
                self.download_status['status'] = 'error'
                self.download_status['error'] = True
                self.download_status['error_message'] = 'Download gagal setelah beberapa percobaan'
                self.download_status['message'] = 'Download gagal'
                self.last_update_time = time.time()
                print("💥 FINAL: Download failed")
                return False

    def _parse_line(self, line):
        """Parse yt-dlp output line for progress info"""
        try:
            # Set status ke 'downloading' saat progress terdeteksi
            if '[download]' in line and '%' in line:
                with self.download_lock:
                    if self.download_status['status'] not in ['downloading', 'completed', 'cancelled', 'error']:
                        self.download_status['status'] = 'downloading'
                        self.download_status['message'] = 'Downloading...'

                # Parse percentage
                match = re.search(r'(\d+\.?\d*)%', line)
                if match:
                    percent = float(match.group(1))
                    with self.download_lock:
                        self.download_status['progress'] = percent
                        if self.download_status['status'] == 'downloading':
                            self.download_status['message'] = f'Downloading: {percent:.1f}%'

            # Parse speed
            if 'at' in line and ('MiB/s' in line or 'KiB/s' in line or 'B/s' in line):
                match = re.search(r'at\s+([\d\.]+\s*[KMG]?i?B/s)', line)
                if match:
                    speed = match.group(1)
                    with self.download_lock:
                        self.download_status['speed'] = speed

            # Parse ETA
            if 'ETA' in line:
                match = re.search(r'ETA\s+([\d:]+)', line)
                if match:
                    eta = match.group(1)
                    with self.download_lock:
                        self.download_status['eta'] = eta
                elif 'ETA' in line and 'Unknown' in line:
                    with self.download_lock:
                        self.download_status['eta'] = '--:--'

            # Parse filename
            if 'Destination:' in line or '[Merger]' in line:
                if 'Destination:' in line:
                    filename = line.split('Destination:', 1)[1].strip()
                else:
                    filename = line.split('[Merger]', 1)[1].strip()

                with self.download_lock:
                    self.download_status['filename'] = os.path.basename(filename)
                    self.download_status['filepath'] = filename

            # Parse file size and downloaded
            if 'of' in line and 'at' in line:
                match = re.search(r'of\s+([\d\.]+\s*[KMG]?i?B)', line)
                if match:
                    with self.download_lock:
                        self.download_status['filesize'] = match.group(1)

                match = re.search(r'(\d+\.?\d*)%\s*of', line)
                if match:
                    downloaded_val = match.group(1)
                    with self.download_lock:
                        self.download_status['downloaded'] = f"{downloaded_val}%"

            # Parse when download complete
            if 'has already been downloaded' in line:
                with self.download_lock:
                    self.download_status['progress'] = 100

            # Update last update time
            with self.download_lock:
                self.last_update_time = time.time()

        except Exception as e:
            print(f"⚠️ Parse error: {e}")

    def get_status(self):
        """Get current download status"""
        with self.download_lock:
            # Check if process is still alive
            if self.current_process and self.current_process.poll() is not None:
                rc = self.current_process.poll()
                # Process has exited but we're still showing downloading
                if self.download_status['status'] == 'downloading':
                    if rc == 0:
                        self.download_status['status'] = 'completed'
                        self.download_status['progress'] = 100
                        self.download_status['message'] = 'Download completed!'
                    else:
                        self.download_status['status'] = 'error'
                        self.download_status['message'] = f'Process exited with code {rc}'
                        self.download_status['error'] = True
                        self.download_status['error_message'] = f'yt-dlp exit code: {rc}'

            # Auto reset after 30 seconds for terminal states
            if self.download_status['status'] in ['completed', 'error', 'cancelled']:
                elapsed = time.time() - self.last_update_time
                if elapsed > 30:
                    saved = self.download_status.copy()
                    self.reset_status()

            return self.download_status.copy()

    def cancel_download(self):
        """Cancel current download"""
        with self.download_lock:
            if self.download_status['status'] in ['completed', 'error', 'cancelled', 'idle']:
                return False
            self.download_status['status'] = 'cancelled'
            self.download_status['message'] = 'Download cancelled by user'
            self.download_status['progress'] = 0
            self.download_status['speed'] = '0 KB/s'
            self.download_status['eta'] = '--:--'
            self.download_status['error'] = False
            self.download_status['error_message'] = ''
            self.last_update_time = time.time()

            process = self.current_process

        # Kill process outside lock
        if process and process.poll() is None:
            try:
                print("🛑 Cancelling download...")
                process.terminate()
                # Give it a moment, then force kill
                time.sleep(0.5)
                if process.poll() is None:
                    process.kill()
                print("✅ Download cancelled successfully")
                return True
            except Exception as e:
                print(f"❌ Cancel error: {e}")
                return False

        return True  # status sudah di-set cancelled

# Global instance
downloader = YouTubeDownloader()
