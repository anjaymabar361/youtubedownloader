#!/usr/bin/env python3
"""
YouTube Downloader Backend - Optimized Version
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

        # Dalam class YouTubeDownloader, tambah fungsi reset_status:
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
        """Check for browser cookies"""
        browsers = ['chrome', 'firefox', 'brave', 'edge', 'chromium']
        for browser in browsers:
            try:
                cmd = ['yt-dlp', '--cookies-from-browser', browser, '--dump-json', '--no-warnings', '--simulate']
                test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
                result = subprocess.run(cmd + [test_url], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return browser
            except Exception as e:
                continue
        return None
    
    def download_video(self, url, quality='best', format_type='video', 
                      custom_path=None, max_speed=None, concurrent_fragments=5):
        """Download YouTube video with optimizations"""
        
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
        
        try:
            # Setup save path - FIXED: Use custom path if provided
            if custom_path and os.path.exists(os.path.dirname(custom_path)):
                # If custom_path is a file path, use its directory
                if os.path.isdir(custom_path):
                    save_path = custom_path
                else:
                    save_path = os.path.dirname(custom_path)
            else:
                # Default download directory
                home = os.path.expanduser("~")
                save_path = os.path.join(home, "Downloads", "YouTube_Downloads")
            
            os.makedirs(save_path, exist_ok=True)
            self.output_path = save_path
            
            # Get cookies
            browser = self.get_browser_cookies()
            print(f"📊 Using browser cookies from: {browser}")
            
            # Output template - FIXED: More organized naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_template = f'{save_path}/%(title)s_{timestamp}.%(ext)s'
            
            # Build command
            cmd = [
                'yt-dlp',
                '--no-warnings',
                '--newline',
                '--progress',
                '--retries', '10',
                '--fragment-retries', '10',
                '--concurrent-fragments', str(concurrent_fragments),
                '--buffer-size', '16K',
                '--http-chunk-size', '5M',
                '-o', output_template
            ]
            
            # Add cookies if available
            if browser:
                cmd.extend(['--cookies-from-browser', browser])
            
            # Add speed limit if specified
            if max_speed and str(max_speed).strip() and max_speed != '0':
                cmd.extend(['--limit-rate', str(max_speed)])
                print(f"⚡ Speed limit set to: {max_speed}")
            
            # Add format-specific options
            if format_type == 'video':
                if quality == 'best':
                    cmd.extend(['-f', 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'])
                elif quality == '720p':
                    cmd.extend(['-f', 'bestvideo[height<=720]+bestaudio/best[height<=720]'])
                elif quality == '480p':
                    cmd.extend(['-f', 'bestvideo[height<=480]+bestaudio/best[height<=480]'])
                elif quality == '360p':
                    cmd.extend(['-f', 'bestvideo[height<=360]+bestaudio/best[height<=360]'])
                cmd.extend(['--merge-output-format', 'mp4'])
            elif format_type == 'audio':
                cmd.extend(['-f', 'bestaudio', '-x', '--audio-format', 'mp3', '--audio-quality', '0'])
            
            # Add URL
            cmd.append(url)
            
            with self.download_lock:
                self.download_status['status'] = 'downloading'
                self.download_status['message'] = f'Starting download with {concurrent_fragments} connections...'
                self.last_update_time = time.time()
            
            print(f"🚀 Starting download for: {url}")
            
            # Start process
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )
            
            # Monitor progress
            for line in iter(self.current_process.stdout.readline, ''):
                line = line.strip()
                if not line:
                    continue
                
                # Check for cancel
                with self.download_lock:
                    if self.download_status['status'] == 'cancelled':
                        self.current_process.terminate()
                        break
                
                # Parse progress
                self._parse_line(line)
                print(f"📊 {line}")
            
            # Wait for completion
            return_code = self.current_process.wait()
            
            with self.download_lock:
                if self.download_status['status'] == 'cancelled':
                    self.current_process = None
                    return False
                elif return_code == 0:
                    self.download_status['status'] = 'completed'
                    self.download_status['progress'] = 100
                    self.download_status['message'] = 'Download completed successfully!'
                    self.download_status['speed'] = '0 KB/s'
                    self.download_status['eta'] = '--:--'
                    self.last_update_time = time.time()
                    self.current_process = None
                    
                    # Update filename with full path
                    if self.download_status['filename'] and self.output_path:
                        full_path = os.path.join(self.output_path, self.download_status['filename'])
                        self.download_status['filepath'] = full_path
                    
                    print("✅ Download completed successfully!")
                    return True
                else:
                    self.download_status['status'] = 'error'
                    self.download_status['message'] = f'Download failed with code {return_code}'
                    self.download_status['error'] = True
                    self.download_status['error_message'] = f'Exit code: {return_code}'
                    self.last_update_time = time.time()
                    self.current_process = None
                    print(f"❌ Download failed with return code: {return_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Download error: {e}")
            import traceback
            traceback.print_exc()
            with self.download_lock:
                self.download_status['status'] = 'error'
                self.download_status['message'] = f'Error: {str(e)[:100]}'
                self.download_status['error'] = True
                self.download_status['error_message'] = str(e)
                self.last_update_time = time.time()
                self.current_process = None
            return False
    
    def _parse_line(self, line):
        """Parse yt-dlp output line for progress info"""
        try:
            # Parse percentage
            if '[download]' in line and '%' in line:
                match = re.search(r'(\d+\.?\d*)%', line)
                if match:
                    percent = float(match.group(1))
                    with self.download_lock:
                        self.download_status['progress'] = percent
            
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
            if 'Destination:' in line:
                filename = line.split('Destination:', 1)[1].strip()
                with self.download_lock:
                    self.download_status['filename'] = os.path.basename(filename)
                    self.download_status['filepath'] = filename
            
            # Parse file size and downloaded
            if 'of' in line and 'in' in line and 'ETA' in line:
                # Example: [download]  12.5% of   85.23MiB at    5.12MiB/s ETA 00:15
                match = re.search(r'of\s+([\d\.]+\s*[KMG]?i?B)', line)
                if match:
                    with self.download_lock:
                        self.download_status['filesize'] = match.group(1)
                
                match = re.search(r'(\d+\.?\d*%\s*of)', line)
                if match:
                    downloaded = match.group(0).replace('of', '').strip()
                    with self.download_lock:
                        self.download_status['downloaded'] = downloaded
            
            # Parse when download complete
            if 'has already been downloaded' in line:
                with self.download_lock:
                    self.download_status['status'] = 'completed'
                    self.download_status['progress'] = 100
                    self.download_status['message'] = 'Already downloaded'
            
            # Update message
            with self.download_lock:
                if self.download_status['progress'] > 0 and self.download_status['status'] == 'downloading':
                    self.download_status['message'] = f'Downloading: {self.download_status["progress"]:.1f}%'
                    self.last_update_time = time.time()
                    
        except Exception as e:
            print(f"⚠️ Parse error: {e}")
    
    def get_status(self):
        """Get current download status"""
        with self.download_lock:
            # Check if process is still alive
            if self.current_process and self.current_process.poll() is not None:
                if self.download_status['status'] == 'downloading':
                    self.download_status['status'] = 'error'
                    self.download_status['message'] = 'Process terminated unexpectedly'
                    self.download_status['error'] = True
            
            # Auto reset after 30 seconds
            if self.download_status['status'] in ['completed', 'error', 'cancelled']:
                elapsed = time.time() - self.last_update_time
                if elapsed > 30:
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
            
            return self.download_status.copy()
    
    def cancel_download(self):
        """Cancel current download"""
        with self.download_lock:
            if self.download_status['status'] in ['completed', 'error', 'cancelled', 'idle']:
                return False
        
        if self.current_process and self.current_process.poll() is None:
            try:
                print("🛑 Cancelling download...")
                self.current_process.terminate()
                
                with self.download_lock:
                    self.download_status['status'] = 'cancelled'
                    self.download_status['message'] = 'Download cancelled by user'
                    self.download_status['progress'] = 0
                    self.download_status['speed'] = '0 KB/s'
                    self.download_status['eta'] = '--:--'
                    self.download_status['error'] = False
                    self.download_status['error_message'] = ''
                    self.last_update_time = time.time()
                
                print("✅ Download cancelled successfully")
                return True
            except Exception as e:
                print(f"❌ Cancel error: {e}")
                return False
        
        return False

# Global instance
downloader = YouTubeDownloader()