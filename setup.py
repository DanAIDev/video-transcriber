#!/usr/bin/env python3
"""
Setup script for Azure Video Transcription Application
This script helps users set up their environment and Azure credentials.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 7):
        print("❌ Error: Python 3.7 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_ffmpeg():
    """Check if FFmpeg is installed."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg found: {version}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    print("❌ FFmpeg not found!")
    print("FFmpeg is required for video processing.")
    print("\nInstall FFmpeg:")
    print("  Windows: Download from https://ffmpeg.org/download.html")
    print("  macOS:   brew install ffmpeg")
    print("  Ubuntu:  sudo apt update && sudo apt install ffmpeg")
    return False

def install_requirements():
    """Install Python requirements."""
    print("\n📦 Installing Python requirements...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def setup_environment():
    """Set up environment file."""
    env_file = Path('.env')
    template_file = Path('.env.template')

    if env_file.exists():
        print("✅ .env file already exists")
        return True

    if template_file.exists():
        shutil.copy(template_file, env_file)
        print("✅ Created .env file from template")
        print("\n⚠️  IMPORTANT: Edit .env file with your Azure credentials!")
        print("   1. Open .env file in a text editor")
        print("   2. Replace 'your_speech_service_key_here' with your actual Azure key")
        print("   3. Replace 'your_service_region_here' with your Azure region")
        return True
    else:
        print("❌ .env.template file not found")
        return False

def test_installation():
    """Test if the installation works."""
    print("\n🧪 Testing installation...")
    try:
        # Test imports
        import azure.cognitiveservices.speech as speechsdk
        from moviepy.editor import VideoFileClip
        from dotenv import load_dotenv
        print("✅ All required packages imported successfully")

        # Test Azure SDK initialization (without actual credentials)
        try:
            # This will fail but should not crash
            config = speechsdk.SpeechConfig("test", "test")
            print("✅ Azure Speech SDK initialized")
        except:
            print("✅ Azure Speech SDK available")

        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def print_usage_instructions():
    """Print usage instructions."""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Get Azure Speech Service credentials:")
    print("   - Go to https://portal.azure.com")
    print("   - Create a Speech Service resource")
    print("   - Copy the Key and Region")
    print("\n2. Update .env file with your credentials")
    print("\n3. Test with a video file:")
    print("   python video_transcription_app.py path/to/your/video.mp4")
    print("\n4. For batch processing:")
    print("   python video_transcription_app.py --batch path/to/video/directory")
    print("\nSupported video formats: MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V")
    print("Supported languages: en-US, es-ES, fr-FR, de-DE, it-IT, pt-BR, ja-JP, ko-KR, zh-CN")

def main():
    """Main setup function."""
    print("🚀 Azure Video Transcription App Setup")
    print("="*50)

    success = True

    # Check Python version
    if not check_python_version():
        success = False

    # Check FFmpeg
    if not check_ffmpeg():
        success = False

    if not success:
        print("\n❌ Setup failed. Please fix the issues above and try again.")
        return False

    # Install requirements
    if not install_requirements():
        return False

    # Setup environment
    if not setup_environment():
        return False

    # Test installation
    if not test_installation():
        return False

    # Print instructions
    print_usage_instructions()

    return True

if __name__ == "__main__":
    main()
