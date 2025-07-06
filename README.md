# Azure Video Transcription App

A Python application for automated video and audio transcription using Microsoft Azure Cognitive Services Speech-to-Text. This tool extracts audio from video files, transcribes speech to text, and supports multiple languages, batch processing, and a quick test mode.

---

## Features

- **Transcribe Video & Audio**: Supports popular video (e.g., `.mp4`, `.avi`, `.mkv`) and audio (e.g., `.wav`, `.mp3`, `.flac`) formats.
- **Azure Cognitive Services**: Uses Azure's robust Speech-to-Text API for accurate transcription.
- **Batch Processing**: Transcribe all media files in a directory with one command.
- **Test Mode**: Quickly transcribe just the first 60 seconds of any media file for verification.
- **Language Selection**: Specify transcription language via command line or `.env` file.
- **Detailed Logging**: All operations and errors are logged for easy troubleshooting.

---

## Prerequisites

- **Python 3.7 or higher**
- **FFmpeg** (required for audio/video processing)
    - Windows: [Download FFmpeg](https://ffmpeg.org/download.html) and add it to your PATH
    - macOS: `brew install ffmpeg`
    - Ubuntu: `sudo apt update && sudo apt install ffmpeg`
- **Azure Account** with a Speech Service resource ([Get started](https://portal.azure.com))
- **pip** (Python package manager)

---

## Automated Setup with `setup.py`

This project provides a `setup.py` script that:
- Checks your Python version
- Installs all required Python libraries
- Verifies FFmpeg installation and guides you if missing
- Creates a `.env` file for your Azure credentials and settings
- Prints usage instructions for the main app

**To set up everything automatically, just run:**
```sh
python setup.py
```

**It is highly recommended to run `python setup.py` before using the application!**

---

## Getting Started

### 1. Clone the Repository
```sh
git clone https://github.com/your-username/video-transcriber.git
cd video-transcriber
```

### 2. Run the Setup Script
```sh
python setup.py
```
_or, if you prefer manual installation:_
```sh
pip install -r requirements.txt
```

### 3. Configure Azure Credentials
- Edit the generated `.env` file:
  ```ini
  AZURE_SPEECH_KEY=your_azure_speech_key
  AZURE_SPEECH_REGION=your_azure_region
  DEFAULT_LANGUAGE=pl-PL  # or any supported language code
  ```

---

## Usage

### **Single File Transcription**
```sh
python video_transcription_app.py path/to/media.mp4 [language]
```
- `language` is optional (e.g., `pl-PL`). If omitted, uses `DEFAULT_LANGUAGE` from `.env` or defaults to `en-US`.

### **Batch Directory Transcription**
```sh
python video_transcription_app.py --batch path/to/directory [language]
```

### **Test Mode (First 60 Seconds Only)**
```sh
python video_transcription_app.py --test path/to/media.mp4 [language]
```

### **Example**
```sh
python video_transcription_app.py myvideo.mp4 pl-PL
```

---

## Supported Formats
- **Video:** `.mp4`, `.avi`, `.mkv`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`
- **Audio:** `.wav`, `.mp3`, `.ogg`, `.flac`, `.m4a`

## Supported Languages
- Any language supported by Azure Speech Service (e.g., `en-US`, `pl-PL`, `es-ES`, etc.)

---

## Output
- Transcripts are saved as `.txt` files in the same directory as the input file.
- Logs are written to `transcription.log`.

---

## Troubleshooting
- Ensure your Azure credentials and region are correct in `.env`.
- Check `transcription.log` for detailed error messages.
- For best results, use clear audio and specify the correct language.
- If you see FFmpeg errors, verify it is installed and on your PATH.

---

## License
MIT License

---

## Acknowledgements
- [Microsoft Azure Cognitive Services](https://azure.microsoft.com/en-us/services/cognitive-services/speech-to-text/)
- [MoviePy](https://zulko.github.io/moviepy/)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
