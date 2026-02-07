#!/usr/bin/env python3
"""
Setup script for YouTube Downloader Pro
"""
import os
import sys
import shutil

def create_structure():
    """Create the required folder structure"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Directories to create
    directories = [
        'backend',
        'frontend'
    ]
    
    print("📁 Creating folder structure...")
    for directory in directories:
        dir_path = os.path.join(base_dir, directory)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"  ✅ Created: {directory}")
        else:
            print(f"  📁 Already exists: {directory}")
    
    # Check for required files
    required_files = {
        'backend': ['__init__.py', 'yt_downloader.py'],
        'frontend': ['index.html', 'style.css', 'script.js'],
        'root': ['server.py', 'requirements.txt']
    }
    
    print("\n📄 Checking required files...")
    for location, files in required_files.items():
        for file in files:
            if location == 'root':
                file_path = os.path.join(base_dir, file)
            else:
                file_path = os.path.join(base_dir, location, file)
            
            if not os.path.exists(file_path):
                print(f"  ⚠️  Missing: {location}/{file}")
            else:
                print(f"  ✅ Found: {location}/{file}")
    
    return base_dir

def install_dependencies():
    """Install required Python packages"""
    print("\n📦 Installing dependencies...")
    
    # Check if pip is available
    try:
        import pip
    except ImportError:
        print("  ❌ pip not found. Please install pip first.")
        return False
    
    # Install from requirements.txt
    requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_file):
        print("  📄 Found requirements.txt")
        os.system(f"{sys.executable} -m pip install -r {requirements_file}")
    else:
        print("  ⚠️  requirements.txt not found, installing manually...")
        packages = [
            'flask==2.3.3',
            'flask-cors==4.0.0',
            'yt-dlp==2023.11.16'
        ]
        for package in packages:
            os.system(f"{sys.executable} -m pip install {package}")
    
    # Check yt-dlp installation
    try:
        import yt_dlp
        print("  ✅ yt-dlp installed successfully")
    except ImportError:
        print("  ❌ Failed to install yt-dlp")
    
    print("  ✅ Dependencies installed")
    return True

def check_ffmpeg():
    """Check if ffmpeg is installed"""
    print("\n🎬 Checking for ffmpeg...")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("  ✅ ffmpeg is installed")
            return True
    except:
        pass
    
    print("  ⚠️  ffmpeg not found or not in PATH")
    print("  💡 To install ffmpeg:")
    print("     Ubuntu/Debian: sudo apt-get install ffmpeg")
    print("     Mac: brew install ffmpeg")
    print("     Windows: Download from ffmpeg.org")
    return False

if __name__ == '__main__':
    import subprocess
    
    print("=" * 60)
    print("🚀 YouTube Downloader Pro - Setup")
    print("=" * 60)
    
    # Create structure
    base_dir = create_structure()
    
    # Install dependencies
    install_dependencies()
    
    # Check ffmpeg
    check_ffmpeg()
    
    print("\n" + "=" * 60)
    print("✅ Setup completed!")
    print("\n📋 Next steps:")
    print("1. Make sure all required files are in place:")
    print("   - backend/yt_downloader.py")
    print("   - frontend/index.html, style.css, script.js")
    print("   - server.py")
    print("2. Run the server:")
    print(f"   cd '{base_dir}'")
    print("   python server.py")
    print("3. Open in browser:")
    print("   http://localhost:5000")
    print("=" * 60)