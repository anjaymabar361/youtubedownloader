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
        """Get cookies from browser - UPDATED FOR RAILWAY"""
        browsers = ['chrome', 'firefox', 'brave', 'edge', 'chromium', 'opera', 'vivaldi']
        
        for browser in browsers:
            try:
                # Coba dengan berbagai browser
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
                    timeout=15,
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
    
    def _download_with_ytdlp_aggressive(self, url, quality, format_type, concurrent_fragments):
        """AGGRESSIVE METHOD untuk bypass YouTube blocking"""
        try:
            # Setup save path
            home = os.path.expanduser("~")
            save_path = os.path.join(home, "Downloads", "YouTube_Downloads")
            os.makedirs(save_path, exist_ok=True)
            output_template = f'{save_path}/%(title)s.%(ext)s'
            
            # AGGRESSIVE BYPASS OPTIONS
            cmd = [
                'yt-dlp',
                '--no-warnings',
                '--newline',
                '--progress',
                # BYPASS OPTIONS MAXIMAL
                '--geo-bypass',
                '--geo-bypass-country', 'US',
                '--force-ipv4',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                '--referer', 'https://www.youtube.com/',
                '--sleep-interval', '3',
                '--max-sleep-interval', '8',
                '--retries', '15',
                '--fragment-retries', '15',
                '--skip-unavailable-fragments',
                '--concurrent-fragments', str(concurrent_fragments),
                '--throttled-rate', '100K',
                # Extractors khusus
                '--extractor-args', 'youtube:player_client=android,ios,web',
                '--youtube-include-dash-manifest',
                '--youtube-include-hls-manifest',
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
            
            print(f"🚀 AGGRESSIVE METHOD: {' '.join(cmd[:10])}...")
            
            # Run process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )
            
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
                print(f"📊 {line}")
            
            # Wait for completion
            return_code = process.wait()
            
            if return_code == 0:
                print("✅ Download successful with aggressive method")
                return True
            else:
                print(f"❌ Aggressive method failed with code: {return_code}")
                return False
                
        except Exception as e:
            print(f"💥 Aggressive method error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def download_video(self, url, quality='best', format_type='video', 
                      custom_path=None, max_speed=None, concurrent_fragments=5):
        """Download YouTube video dengan multiple fallback methods"""
        
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
        
        print(f"🎯 Starting download with AGGRESSIVE method for: {url}")
        
        # Langsung pakai AGGRESSIVE method (skip method biasa)
        success = self._download_with_ytdlp_aggressive(url, quality, format_type, concurrent_fragments)
        
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
                self.download_status['error_message'] = 'Failed after aggressive retries'
                self.last_update_time = time.time()
                print("💥 FINAL: All methods failed")
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
            if 'of' in line and 'in' in line:
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
            if 'has already been downloaded' in line or '100%' in line:
                with self.download_lock:
                    if self.download_status['progress'] < 100:
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
                if self.download_status['status'] == 'downloading':
                    self.download_status['status'] = 'error'
                    self.download_status['message'] = 'Process terminated unexpectedly'
                    self.download_status['error'] = True
            
            # Auto reset after 30 seconds
            if self.download_status['status'] in ['completed', 'error', 'cancelled']:
                elapsed = time.time() - self.last_update_time
                if elapsed > 30:
                    self.reset_status()
            
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
