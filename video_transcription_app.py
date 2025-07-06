import os
import sys
import tempfile
import logging
from pathlib import Path
from typing import Tuple
import time
import shutil

# Required libraries - install with: pip install moviepy azure-cognitiveservices-speech python-dotenv
try:
    from moviepy.editor import VideoFileClip, AudioFileClip
    import azure.cognitiveservices.speech as speechsdk
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required library: {e}")
    print("Please install required libraries:")
    print("pip install moviepy azure-cognitiveservices-speech python-dotenv")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('transcription.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VideoTranscriptionApp:
    """
    A complete application for extracting audio from video files and 
    transcribing them using Azure Speech Services.
    """

    def __init__(self, azure_key: str, azure_region: str):
        """
        Initialize the transcription application.

        Args:
            azure_key: Azure Speech Service API key
            azure_region: Azure Speech Service region (e.g., 'eastus')
        """
        self.azure_key = azure_key
        self.azure_region = azure_region
        self.supported_video_formats = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
        self.supported_audio_formats = ['.wav', '.mp3', '.ogg', '.flac', '.m4a']
        self.temp_dir = tempfile.mkdtemp(prefix='video_transcription_')
        logger.info(f"Temporary directory created: {self.temp_dir}")

    def extract_audio_from_video(self, video_path: str, output_format: str = 'wav') -> str:
        """
        Extract audio from video file and convert to a format compatible with Azure Speech.

        Args:
            video_path: Path to the input video file
            output_format: Output audio format ('wav' recommended for Azure Speech)

        Returns:
            Path to the extracted audio file
        """
        try:
            video_path = Path(video_path)
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")

            if video_path.suffix.lower() not in self.supported_video_formats:
                raise ValueError(f"Unsupported video format: {video_path.suffix}")

            logger.info(f"Extracting audio from: {video_path}")

            # Load video file
            video_clip = VideoFileClip(str(video_path))

            # Extract audio
            audio_clip = video_clip.audio

            # Generate output filename
            audio_filename = f"{video_path.stem}_audio.{output_format}"
            audio_path = os.path.join(self.temp_dir, audio_filename)

            # Write audio file with settings optimized for Azure Speech
            # Azure Speech works best with 16kHz, 16-bit, mono WAV
            audio_clip.write_audiofile(
                audio_path,
                codec='pcm_s16le' if output_format == 'wav' else None,
                ffmpeg_params=['-ar', '16000', '-ac', '1'] if output_format == 'wav' else None,
                verbose=False,
                logger=None
            )

            # Clean up
            audio_clip.close()
            video_clip.close()

            logger.info(f"Audio extracted successfully: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            raise

    def transcribe_audio(self, audio_path: str, language: str = "en-US") -> Tuple[str, float]:
        """
        Transcribe audio file using Azure Speech Service.
        """
        try:
            logger.info(f"Starting transcription of: {audio_path}")
            speech_config = speechsdk.SpeechConfig(subscription=self.azure_key, region=self.azure_region)
            speech_config.speech_recognition_language = language
            audio_input = speechsdk.AudioConfig(filename=audio_path)
            speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

            transcription_text = ""
            done = False
            confidence_scores = []

            def session_started_callback(evt):
                logger.info(f"Recognition session started: {evt}")

            def session_stopped_callback(evt):
                nonlocal done
                logger.info(f"Recognition session stopped: {evt}")
                done = True

            def recognized_callback(evt):
                nonlocal transcription_text
                if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    transcription_text += evt.result.text + " "
                    confidence_scores.append(evt.result.json.get('NBest', [{}])[0].get('Confidence', 0))
                    logger.debug(f"Recognized: {evt.result.text}")
                elif evt.result.reason == speechsdk.ResultReason.NoMatch:
                    logger.warning("No speech could be recognized from the audio.")

            def canceled_callback(evt):
                nonlocal done
                logger.error(f"Recognition canceled: {evt.reason}")
                if evt.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"Error details: {evt.error_details}")
                done = True

            speech_recognizer.recognized.connect(recognized_callback)
            speech_recognizer.session_started.connect(session_started_callback)
            speech_recognizer.session_stopped.connect(session_stopped_callback)
            speech_recognizer.canceled.connect(canceled_callback)

            speech_recognizer.start_continuous_recognition()
            while not done:
                time.sleep(0.5)

            speech_recognizer.stop_continuous_recognition()

            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            logger.info(f"Transcription completed. Text length: {len(transcription_text)} characters")
            return transcription_text.strip(), avg_confidence

        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            raise

    def process_file(self, file_path: str, language: str = "en-US", save_audio: bool = False) -> dict:
        """
        Complete pipeline: process a video or audio file and transcribe it.
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        file_type = ""
        if file_path_obj.suffix.lower() in self.supported_video_formats:
            file_type = "video"
        elif file_path_obj.suffix.lower() in self.supported_audio_formats:
            file_type = "audio"
        else:
            raise ValueError(f"Unsupported file format: {file_path_obj.suffix}")

        if file_type == "video":
            return self.process_video(file_path, language, save_audio)
        else: # audio
            return self.process_audio(file_path, language)

    def process_audio(self, audio_path: str, language: str = "en-US") -> dict:
        """
        Complete pipeline for an audio file: transcribe it.
        """
        try:
            start_time = time.time()
            audio_file = Path(audio_path)

            # Transcribe audio
            transcription, confidence = self.transcribe_audio(audio_path, language)

            results = {
                'input_file': str(audio_file.absolute()),
                'file_type': 'audio',
                'file_size_mb': round(audio_file.stat().st_size / (1024 * 1024), 2),
                'transcription': transcription,
                'confidence_score': round(confidence, 4),
                'language': language,
                'processing_time_seconds': round(time.time() - start_time, 2),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }

            self._save_transcription_file(results)
            logger.info(f"Processing completed successfully in {results['processing_time_seconds']} seconds")
            return results

        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            raise

    def process_video(self, video_path: str, language: str = "en-US", save_audio: bool = False) -> dict:
        """
        Complete pipeline for a video file: extract audio and transcribe it.
        """
        try:
            start_time = time.time()
            video_file = Path(video_path)

            # Extract audio
            audio_path = self.extract_audio_from_video(video_path)

            # Transcribe audio
            transcription, confidence = self.transcribe_audio(audio_path, language)

            audio_file = Path(audio_path)
            results = {
                'input_file': str(video_file.absolute()),
                'file_type': 'video',
                'file_size_mb': round(video_file.stat().st_size / (1024 * 1024), 2),
                'audio_file': str(audio_file.absolute()) if save_audio else None,
                'transcription': transcription,
                'confidence_score': round(confidence, 4),
                'language': language,
                'processing_time_seconds': round(time.time() - start_time, 2),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }

            self._save_transcription_file(results)

            # Clean up temporary audio file if not saving
            if not save_audio and os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info("Temporary audio file cleaned up")

            logger.info(f"Processing completed successfully in {results['processing_time_seconds']} seconds")
            return results

        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            raise

    def _save_transcription_file(self, results: dict):
        """Saves the transcription results to a text file."""
        input_file = Path(results['input_file'])
        transcript_filename = f"{input_file.stem}_transcript.txt"
        transcript_path = input_file.parent / transcript_filename

        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(f"Transcription Results\n")
            f.write(f"{'=' * 50}\n\n")
            f.write(f"Source File: {results['input_file']}\n")
            f.write(f"File Size: {results['file_size_mb']} MB\n")
            f.write(f"Language: {results['language']}\n")
            f.write(f"Confidence Score: {results['confidence_score']}\n")
            f.write(f"Processing Time: {results['processing_time_seconds']} seconds\n")
            f.write(f"Timestamp: {results['timestamp']}\n\n")
            f.write(f"Transcription:\n")
            f.write(f"{'=' * 30}\n")
            f.write(f"{results['transcription']}\n")

        results['transcript_file'] = str(transcript_path)

    def _create_test_audio_clip(self, media_path: str, duration: int = 60) -> str:
        """Creates a temporary audio clip from the first part of a media file."""
        try:
            media_path = Path(media_path)
            logger.info(f"Creating a {duration}-second test clip from: {media_path}")

            if media_path.suffix.lower() in self.supported_video_formats:
                clip = VideoFileClip(str(media_path))
                audio_clip = clip.audio.subclip(0, min(duration, clip.audio.duration))
            elif media_path.suffix.lower() in self.supported_audio_formats:
                clip = AudioFileClip(str(media_path))
                audio_clip = clip.subclip(0, min(duration, clip.duration))
            else:
                 raise ValueError(f"Unsupported file format for test clip: {media_path.suffix}")

            test_audio_filename = f"{media_path.stem}_test_clip.wav"
            test_audio_path = os.path.join(self.temp_dir, test_audio_filename)

            audio_clip.write_audiofile(
                test_audio_path,
                codec='pcm_s16le',
                ffmpeg_params=['-ar', '16000', '-ac', '1'],
                verbose=False,
                logger=None
            )

            clip.close()
            audio_clip.close()

            logger.info(f"Test audio clip created successfully: {test_audio_path}")
            return test_audio_path

        except Exception as e:
            logger.error(f"Error creating test audio clip: {str(e)}")
            raise

    def process_file_test(self, file_path: str, language: str = "en-US") -> dict:
        """
        Test pipeline: transcribes the first minute of a video or audio file.
        """
        try:
            start_time = time.time()
            
            # Create a 1-minute audio clip for testing
            test_audio_path = self._create_test_audio_clip(file_path, duration=60)

            # Transcribe the test audio clip
            transcription, confidence = self.transcribe_audio(test_audio_path, language)

            input_file = Path(file_path)
            results = {
                'input_file': str(input_file.absolute()),
                'file_type': 'test_clip',
                'file_size_mb': round(input_file.stat().st_size / (1024 * 1024), 2),
                'transcription': transcription,
                'confidence_score': round(confidence, 4),
                'language': language,
                'processing_time_seconds': round(time.time() - start_time, 2),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }

            # Save transcription with a special name
            transcript_filename = f"{input_file.stem}_TEST_transcript.txt"
            transcript_path = input_file.parent / transcript_filename
            results['transcript_file'] = str(transcript_path)

            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"--- TEST TRANSCRIPTION (First 60 seconds) ---\n")
                f.write(f"Source File: {results['input_file']}\n")
                f.write(f"Language: {results['language']}\n")
                f.write(f"Confidence: {results['confidence_score']}\n")
                f.write(f"Processing Time: {results['processing_time_seconds']}s\n\n")
                f.write(f"Transcription:\n{'='*30}\n{results['transcription']}\n")

            # Clean up the temporary test audio file
            if os.path.exists(test_audio_path):
                os.remove(test_audio_path)
                logger.info(f"Cleaned up temporary test clip: {test_audio_path}")

            logger.info(f"Test processing completed successfully in {results['processing_time_seconds']} seconds")
            return results

        except Exception as e:
            logger.error(f"Error during test processing: {str(e)}")
            raise

    def batch_process(self, media_directory: str, language: str = "en-US", save_audio: bool = False) -> list:
        """
        Process multiple video or audio files in a directory.
        """
        try:
            media_dir = Path(media_directory)
            if not media_dir.exists() or not media_dir.is_dir():
                raise ValueError(f"Invalid directory: {media_directory}")

            # Find all media files
            media_files = []
            supported_formats = self.supported_video_formats + self.supported_audio_formats
            for ext in supported_formats:
                media_files.extend(media_dir.glob(f"*{ext}"))
                media_files.extend(media_dir.glob(f"*{ext.upper()}"))

            if not media_files:
                logger.warning(f"No media files found in {media_directory}")
                return []

            logger.info(f"Found {len(media_files)} media files to process")

            results = []
            for i, media_file in enumerate(media_files, 1):
                logger.info(f"Processing file {i}/{len(media_files)}: {media_file.name}")
                try:
                    result = self.process_file(str(media_file), language, save_audio)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process {media_file.name}: {str(e)}")
                    results.append({
                        'input_file': str(media_file),
                        'error': str(e),
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    })

            # Create summary report
            summary_path = media_dir / f"batch_transcription_summary_{int(time.time())}.txt"
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"Batch Transcription Summary\n")
                f.write(f"{'=' * 50}\n\n")
                f.write(f"Total files processed: {len(media_files)}\n")
                f.write(f"Successful: {len([r for r in results if 'error' not in r])}\n")
                f.write(f"Failed: {len([r for r in results if 'error' in r])}\n")
                f.write(f"Language: {language}\n")
                f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                for result in results:
                    if 'error' in result:
                        f.write(f"❌ {Path(result['input_file']).name}: {result['error']}\n")
                    else:
                        f.write(f"✅ {Path(result['input_file']).name}: {len(result['transcription'])} chars\n")

            logger.info(f"Batch processing completed. Summary saved to: {summary_path}")
            return results

        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            raise

    def cleanup(self):
        """Clean up temporary files and directories."""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory: {str(e)}")

def main():
    """Main function to run the application."""
    load_dotenv()
    azure_key = os.getenv('AZURE_SPEECH_KEY')
    azure_region = os.getenv('AZURE_SPEECH_REGION')

    if not azure_key or not azure_region:
        print("Error: Azure Speech Service credentials not found!")
        print("Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION environment variables, or create a .env file.")
        return

    app = VideoTranscriptionApp(azure_key, azure_region)

    try:
        if len(sys.argv) < 2:
            print("Usage:")
            print("  Single file: python video_transcription_app.py path/to/media.mp4 [language]")
            print("  Batch mode:  python video_transcription_app.py --batch path/to/directory [language]")
            print("  Test mode:   python video_transcription_app.py --test path/to/media.mp4 [language]")
            print("\nSupported languages: en-US, es-ES, fr-FR, de-DE, it-IT, pt-BR, ja-JP, ko-KR, zh-CN, pl-PL, ...")
            print("\nLanguage selection priority:")
            print("  1. Command-line argument [language]")
            print("  2. DEFAULT_LANGUAGE in .env file")
            print("  3. Fallback: en-US")
            return

        # Read language from CLI, .env, or fallback
        default_language = os.getenv('DEFAULT_LANGUAGE', 'en-US')

        # Test mode
        if sys.argv[1] == '--test':
            if len(sys.argv) < 3:
                print("Error: Please specify a file for test processing")
                return
            file_path = sys.argv[2]
            language = sys.argv[3] if len(sys.argv) > 3 else default_language
            print(f"Starting test processing of file: {file_path}")
            print(f"Language: {language}")
            logger.info(f"[TEST MODE] Using language: {language}")
            result = app.process_file_test(file_path, language)
            print(f"\nTest transcription completed!")
            print(f"Processing time: {result['processing_time_seconds']} seconds")
            print(f"Confidence score: {result['confidence_score']}")
            print(f"Test transcript saved to: {result['transcript_file']}")

        # Batch mode
        elif sys.argv[1] == '--batch':
            if len(sys.argv) < 3:
                print("Error: Please specify directory for batch processing")
                return
            directory = sys.argv[2]
            language = sys.argv[3] if len(sys.argv) > 3 else default_language
            print(f"Starting batch processing of directory: {directory}")
            print(f"Language: {language}")
            logger.info(f"[BATCH MODE] Using language: {language}")
            results = app.batch_process(directory, language)
            print(f"\nBatch processing completed!")
            print(f"Processed: {len(results)} files")
            print(f"Successful: {len([r for r in results if 'error' not in r])}")
            print(f"Failed: {len([r for r in results if 'error' in r])}")
        
        # Single file mode
        else:
            file_path = sys.argv[1]
            language = sys.argv[2] if len(sys.argv) > 2 else default_language
            print(f"Processing file: {file_path}")
            print(f"Language: {language}")
            logger.info(f"[SINGLE FILE MODE] Using language: {language}")
            result = app.process_file(file_path, language, save_audio=True)
            print(f"\nTranscription completed!")
            print(f"Processing time: {result['processing_time_seconds']} seconds")
            print(f"Confidence score: {result['confidence_score']}")
            print(f"Transcript saved to: {result['transcript_file']}")
            print(f"\nTranscription preview:")
            preview = result['transcription'][:500]
            print(f"{preview}{'...' if len(result['transcription']) > 500 else ''}")
    finally:
        app.cleanup()


if __name__ == "__main__":
    main()
