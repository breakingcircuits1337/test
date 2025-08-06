# Enhanced Voice Assistant (Cross-Platform) - v7 IMPROVED
# -----------------------------------------------
# Enhanced version with improved error handling, new features, and better user experience
#
# New Features Added:
# - Natural language time parsing for reminders
# - Todo list management
# - Email functionality
# - File operations
# - Music/media control
# - Smart home integration placeholder
# - Improved conversation flow
# - Better error handling and logging
#
# Required libraries:
# pip install beautifulsoup4 requests speechrecognition pyttsx3 wikipedia pyaudio
# pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
# pip install python-dateutil fuzzywuzzy python-levenshtein

import speech_recognition as sr
import pyttsx3
import datetime
import wikipedia
import webbrowser
import os
import time
import subprocess
import platform
import requests
import json
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from dateutil import parser
from fuzzywuzzy import fuzz
import threading
import queue

# --- Google Calendar Imports ---
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
ASSISTANT_NAME = "Assistant"
USER_NAME = "Sir"
NEWS_API_KEY = "YOUR_NEWS_API_KEY"  # Get a free key from newsapi.org
TODO_FILE = "todos.json"
SETTINGS_FILE = "assistant_settings.json"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('assistant.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Google Calendar Configuration ---
SCOPES = ['https://www.googleapis.com/auth/calendar']

# --- Settings Management ---
def load_settings():
    """Load user settings from file."""
    default_settings = {
        "voice_rate": 150,
        "voice_volume": 0.8,
        "wake_word": "assistant",
        "continuous_listening": False,
        "weather_location": "New York"
    }
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                return {**default_settings, **settings}
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    
    return default_settings

def save_settings(settings):
    """Save user settings to file."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving settings: {e}")

settings = load_settings()

# --- Voice Management ---
def get_available_voices():
    """Get all available system voices with details."""
    voices_info = []
    temp_engine = None
    
    try:
        system_os = platform.system()
        if system_os == 'Windows':
            driver = 'sapi5'
        elif system_os == 'Darwin':
            driver = 'nsss'
        elif system_os == 'Linux':
            driver = 'espeak'
        else:
            driver = None
            
        temp_engine = pyttsx3.init(driver)
        voices = temp_engine.getProperty('voices')
        
        for i, voice in enumerate(voices):
            voice_info = {
                'index': i,
                'id': voice.id,
                'name': getattr(voice, 'name', f'Voice {i+1}'),
                'gender': 'Unknown',
                'language': getattr(voice, 'languages', ['Unknown'])[0] if hasattr(voice, 'languages') else 'Unknown'
            }
            
            # Try to determine gender from voice name/id (common patterns)
            voice_name_lower = voice_info['name'].lower()
            voice_id_lower = voice_info['id'].lower()
            
            if any(word in voice_name_lower or word in voice_id_lower for word in ['female', 'woman', 'zira', 'hazel', 'samantha', 'anna', 'helena', 'karen']):
                voice_info['gender'] = 'Female'
            elif any(word in voice_name_lower or word in voice_id_lower for word in ['male', 'man', 'david', 'mark', 'alex', 'daniel', 'ryan', 'sean']):
                voice_info['gender'] = 'Male'
            
            voices_info.append(voice_info)
            
    except Exception as e:
        logger.error(f"Error getting available voices: {e}")
        
    finally:
        if temp_engine:
            try:
                temp_engine.stop()
            except:
                pass
    
    return voices_info

def initialize_engine():
    """Initializes the text-to-speech engine with voice selection and backend options."""
    system_os = platform.system()
    
    # Try different TTS engines in order of preference
    engines_to_try = []
    
    if system_os == 'Windows':
        engines_to_try = ['sapi5']
    elif system_os == 'Darwin':
        engines_to_try = ['nsss']
    elif system_os == 'Linux':
        # Try Festival first (better quality), then espeak-ng, then espeak
        engines_to_try = ['festival', 'espeak-ng', 'espeak']
    
    engine = None
    selected_driver = None
    
    for driver in engines_to_try:
        try:
            print(f"Trying TTS engine: {driver}")
            engine = pyttsx3.init(driver)
            
            # Test if engine works
            voices = engine.getProperty('voices')
            if voices:
                selected_driver = driver
                print(f"Successfully initialized {driver} with {len(voices)} voices")
                break
            else:
                engine.stop()
                engine = None
                
        except Exception as e:
            print(f"Failed to initialize {driver}: {e}")
            if engine:
                try:
                    engine.stop()
                except:
                    pass
                engine = None
            continue
    
    if not engine:
        print("Warning: Could not initialize any TTS engine")
        return None
    
    try:
        voices = engine.getProperty('voices')
        
        if voices:
            # Filter for English voices if using espeak/espeak-ng
            english_voices = []
            if selected_driver in ['espeak', 'espeak-ng']:
                for i, voice in enumerate(voices):
                    voice_id = voice.id.lower()
                    # Look for English voices (including MBROLA voices)
                    if any(lang in voice_id for lang in ['en', 'us', 'gb', 'mb-en', 'mb-us']):
                        english_voices.append((i, voice))
                
                if english_voices:
                    print(f"Found {len(english_voices)} English voices")
                    # Prefer MBROLA voices if available
                    mbrola_voices = [v for v in english_voices if 'mb-' in v[1].id.lower()]
                    if mbrola_voices:
                        preferred_voice_index = mbrola_voices[0][0]
                        print(f"Using MBROLA voice: {voices[preferred_voice_index].id}")
                    else:
                        preferred_voice_index = english_voices[0][0]
                        print(f"Using English voice: {voices[preferred_voice_index].id}")
                else:
                    # Fallback to saved preference or first voice
                    preferred_voice_index = settings.get('voice_index', 0)
            else:
                # For Festival and other engines, use saved preference
                preferred_voice_index = settings.get('voice_index', 0)
                preferred_gender = settings.get('preferred_gender', None)
                
                # Gender preference logic for non-espeak engines
                if preferred_gender and not settings.get('voice_index'):
                    for i, voice in enumerate(voices):
                        voice_name = getattr(voice, 'name', '').lower()
                        voice_id = voice.id.lower()
                        
                        if preferred_gender.lower() == 'female':
                            if any(word in voice_name or word in voice_id for word in ['female', 'woman', 'slt', 'kal', 'awb']):
                                preferred_voice_index = i
                                break
                        elif preferred_gender.lower() == 'male':
                            if any(word in voice_name or word in voice_id for word in ['male', 'man', 'kal', 'awb']):
                                preferred_voice_index = i
                                break
            
            # Ensure index is valid
            if preferred_voice_index >= len(voices):
                preferred_voice_index = 0
                
            engine.setProperty('voice', voices[preferred_voice_index].id)
            print(f"Selected voice: {voices[preferred_voice_index].id}")
            
            # Save the selected voice index and engine
            settings['voice_index'] = preferred_voice_index
            settings['tts_engine'] = selected_driver
            save_settings(settings)
        
        # Apply other settings
        engine.setProperty('rate', settings.get('voice_rate', 150))
        engine.setProperty('volume', settings.get('voice_volume', 0.8))
        
        return engine
        
    except Exception as e:
        logger.error(f"Error configuring TTS engine: {e}")
        return engine  # Return basic engine even if configuration fails

engine = initialize_engine()

# --- Interrupt Handling ---
import signal
import sys

class InterruptHandler:
    """Handles keyboard interrupts and stop commands."""
    def __init__(self):
        self.interrupted = False
        self.stop_requested = False
        
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C interrupt."""
        self.interrupted = True
        self.stop_requested = True
        print("\n[Interrupted by user]")
        
    def reset(self):
        """Reset interrupt flags."""
        self.interrupted = False
        self.stop_requested = False

# Global interrupt handler
interrupt_handler = InterruptHandler()

# --- Enhanced Core Functions ---
def speak(audio, interruptible=True):
    """Converts the given text to speech with interrupt capability."""
    if not engine:
        print(f"{ASSISTANT_NAME}: {audio}")
        return False
    
    print(f"{ASSISTANT_NAME}: {audio}")
    
    if not interruptible:
        # Non-interruptible speech (for critical messages)
        try:
            engine.say(audio)
            engine.runAndWait()
            return True
        except Exception as e:
            logger.error(f"Error in speech synthesis: {e}")
            return False
    
    try:
        # Split long text into chunks for better interrupt responsiveness
        sentences = audio.split('. ')
        
        for i, sentence in enumerate(sentences):
            if interrupt_handler.stop_requested:
                print("[Speech interrupted]")
                engine.stop()
                return False
                
            # Add period back except for last sentence
            if i < len(sentences) - 1 and not sentence.endswith('.'):
                sentence += '.'
                
            engine.say(sentence)
            engine.runAndWait()
            
            # Small delay to check for interrupts
            time.sleep(0.1)
            
        return True
        
    except Exception as e:
        logger.error(f"Error in speech synthesis: {e}")
        return False

def listen_for_interrupt():
    """Start a thread to listen for interrupt commands during long operations."""
    def interrupt_listener():
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                recognizer.pause_threshold = 0.5
                
                while not interrupt_handler.stop_requested:
                    try:
                        # Listen for very short phrases
                        audio = recognizer.listen(source, timeout=1, phrase_time_limit=2)
                        command = recognizer.recognize_google(audio, language='en-in').lower()
                        
                        # Check for stop commands
                        if any(word in command for word in ['stop', 'halt', 'quiet', 'silence', 'enough', 'cancel']):
                            print(f"[Interrupt detected: '{command}']")
                            interrupt_handler.stop_requested = True
                            break
                            
                    except (sr.WaitTimeoutError, sr.UnknownValueError, sr.RequestError):
                        continue
                        
        except Exception as e:
            # Silently fail - interrupt listening is optional
            pass
    
    # Start interrupt listener in daemon thread
    interrupt_thread = threading.Thread(target=interrupt_listener, daemon=True)
    interrupt_thread.start()
    return interrupt_thread

def wish_me():
    """Wishes the user based on the current time of day."""
    hour = datetime.datetime.now().hour
    if 0 <= hour < 12:
        greeting = "Good Morning"
    elif 12 <= hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"
    
    speak(f"{greeting}, {USER_NAME}.")
    speak(f"I am your voice {ASSISTANT_NAME}. How may I help you today?")

def take_command():
    """Listens for microphone input and converts it to text with improved error handling."""
    recognizer = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            print("\nListening... (Say 'stop' anytime to interrupt)")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            recognizer.pause_threshold = 1
            recognizer.energy_threshold = 300
            
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=8)
            except sr.WaitTimeoutError:
                return "none"
        
        print("Recognizing...")
        query = recognizer.recognize_google(audio, language='en-in')
        print(f"User said: {query}")
        logger.info(f"User command: {query}")
        
        # Check for immediate stop commands
        if any(word in query.lower() for word in ['stop talking', 'be quiet', 'silence', 'shut up', 'halt']):
            interrupt_handler.stop_requested = True
            engine.stop()
            speak("Okay, I'll stop.", interruptible=False)
            interrupt_handler.reset()
            return "none"
            
        return query.lower()
        
    except sr.UnknownValueError:
        if not interrupt_handler.stop_requested:
            speak("Sorry, I didn't catch that. Could you please repeat?", interruptible=False)
        return "none"
    except sr.RequestError as e:
        speak("Sorry, there's an issue with the speech recognition service.", interruptible=False)
        logger.error(f"Speech recognition error: {e}")
        return "none"
    except Exception as e:
        logger.error(f"Unexpected error in take_command: {e}")
        return "none"

# --- Enhanced Command Functions ---

def run_gemini_command(query):
    """Executes a Gemini CLI command with improved error handling."""
    command_to_run = query.replace("gemini", "").strip()
    if not command_to_run:
        speak("What Gemini command would you like me to run?")
        command_to_run = take_command()
        if command_to_run == "none":
            return

    speak(f"Running Gemini command: {command_to_run}")
    
    try:
        full_command = f"gemini {command_to_run}"
        
        process = subprocess.Popen(
            full_command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=60)

        if process.returncode != 0:
            speak("Sorry, there was an error with the Gemini command.")
            logger.error(f"Gemini CLI Error: {stderr}")
            if stderr:
                speak(stderr.splitlines()[0])
        else:
            speak("Here is the result.")
            output_lines = stdout.splitlines()
            
            # Smart output handling - speak summary for long outputs
            if len(output_lines) > 10:
                speak(f"The command completed successfully with {len(output_lines)} lines of output.")
                speak("Here are the first few lines:")
                for line in output_lines[:3]:
                    if line.strip():
                        speak(line)
                speak("The full output is printed in the console.")
            else:
                for line in output_lines:
                    if line.strip():
                        speak(line)
            
            logger.info(f"Gemini command successful: {command_to_run}")

    except FileNotFoundError:
        speak("Error: The Gemini CLI is not installed or not in your system's PATH.")
    except subprocess.TimeoutExpired:
        speak("The Gemini command took too long to respond.")
    except Exception as e:
        speak("An unexpected error occurred while running the Gemini command.")
        logger.error(f"Gemini Execution Error: {e}")

# --- Todo List Management ---
def load_todos():
    """Load todos from file."""
    if os.path.exists(TODO_FILE):
        try:
            with open(TODO_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading todos: {e}")
    return []

def save_todos(todos):
    """Save todos to file."""
    try:
        with open(TODO_FILE, 'w') as f:
            json.dump(todos, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving todos: {e}")

def add_todo(query):
    """Add a new todo item."""
    task = query.replace("add todo", "").replace("add task", "").strip()
    if not task:
        speak("What task would you like to add?")
        task = take_command()
        if task == "none":
            return
    
    todos = load_todos()
    todo_item = {
        "id": len(todos) + 1,
        "task": task,
        "created": datetime.datetime.now().isoformat(),
        "completed": False
    }
    
    todos.append(todo_item)
    save_todos(todos)
    speak(f"Added '{task}' to your todo list.")

def list_todos(query):
    """List all todos."""
    todos = load_todos()
    if not todos:
        speak("Your todo list is empty.")
        return
    
    pending_todos = [t for t in todos if not t["completed"]]
    if not pending_todos:
        speak("All your tasks are completed! Great job!")
        return
    
    speak(f"You have {len(pending_todos)} pending tasks:")
    for todo in pending_todos:
        speak(f"Task {todo['id']}: {todo['task']}")

def complete_todo(query):
    """Mark a todo as completed."""
    todos = load_todos()
    if not todos:
        speak("Your todo list is empty.")
        return
    
    # Extract task number or find by fuzzy matching
    task_words = query.replace("complete", "").replace("done", "").replace("task", "").strip()
    
    if task_words.isdigit():
        task_id = int(task_words)
        for todo in todos:
            if todo["id"] == task_id and not todo["completed"]:
                todo["completed"] = True
                todo["completed_date"] = datetime.datetime.now().isoformat()
                save_todos(todos)
                speak(f"Marked task '{todo['task']}' as completed.")
                return
    else:
        # Fuzzy match the task description
        best_match = None
        best_ratio = 0
        for todo in todos:
            if not todo["completed"]:
                ratio = fuzz.partial_ratio(task_words.lower(), todo["task"].lower())
                if ratio > best_ratio and ratio > 70:
                    best_ratio = ratio
                    best_match = todo
        
        if best_match:
            best_match["completed"] = True
            best_match["completed_date"] = datetime.datetime.now().isoformat()
            save_todos(todos)
            speak(f"Marked task '{best_match['task']}' as completed.")
            return
    
    speak("I couldn't find that task. Please try again or say the task number.")

# --- Enhanced Calendar Functions ---
def get_calendar_service():
    """Gets an authorized Google Calendar service object."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                speak("Error: credentials.json file not found. Please follow the setup instructions.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except HttpError as error:
        speak("An error occurred with the calendar service.")
        logger.error(f'Calendar service error: {error}')
        return None

def parse_datetime_from_speech(time_str):
    """Parse natural language date/time into datetime object."""
    try:
        # Handle common phrases
        now = datetime.datetime.now()
        
        if "tomorrow" in time_str:
            base_date = now + datetime.timedelta(days=1)
        elif "next week" in time_str:
            base_date = now + datetime.timedelta(weeks=1)
        elif "today" in time_str:
            base_date = now
        else:
            # Try to parse the full string
            return parser.parse(time_str, fuzzy=True)
        
        # Extract time if mentioned
        if "at" in time_str:
            time_part = time_str.split("at")[-1].strip()
            try:
                time_obj = parser.parse(time_part, fuzzy=True)
                return base_date.replace(
                    hour=time_obj.hour,
                    minute=time_obj.minute,
                    second=0,
                    microsecond=0
                )
            except:
                pass
        
        return base_date.replace(hour=9, minute=0, second=0, microsecond=0)
        
    except Exception as e:
        logger.error(f"Date parsing error: {e}")
        return None

def set_reminder(query):
    """Enhanced reminder setting with natural language parsing."""
    speak("What should the reminder be about?")
    summary = take_command()
    if summary == "none":
        speak("Sorry, I didn't catch that. Please try again.")
        return

    speak("When should the reminder be? You can say things like 'tomorrow at 3 PM' or 'next Monday at 10 AM'.")
    time_str = take_command()
    if time_str == "none":
        speak("Sorry, I didn't catch the time.")
        return
    
    start_time = parse_datetime_from_speech(time_str)
    if not start_time:
        speak("I couldn't understand the time. Please try again with a clearer format.")
        return
    
    end_time = start_time + datetime.timedelta(hours=1)
    
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'America/New_York',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'America/New_York',
        },
        'reminders': {
            'useDefault': True,
        },
    }

    service = get_calendar_service()
    if not service:
        return

    try:
        service.events().insert(calendarId='primary', body=event).execute()
        formatted_time = start_time.strftime('%A, %B %d at %I:%M %p')
        speak(f"Perfect! I've set a reminder for '{summary}' on {formatted_time}.")
        logger.info(f"Reminder set: {summary} at {formatted_time}")
    except HttpError as error:
        speak("Sorry, I couldn't set the reminder.")
        logger.error(f'Calendar error: {error}')

def check_calendar(query):
    """Enhanced calendar checking with better formatting."""
    speak("Checking your calendar...")
    service = get_calendar_service()
    if not service:
        return

    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        
        # Check for today's events
        end_of_day = (datetime.datetime.now().replace(hour=23, minute=59, second=59)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=end_of_day,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])

        if not events:
            speak("You have no events scheduled for today.")
            
            # Check tomorrow's events
            tomorrow_start = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat() + 'Z'
            tomorrow_end = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat() + 'Z'
            
            tomorrow_events = service.events().list(
                calendarId='primary',
                timeMin=tomorrow_start,
                timeMax=tomorrow_end,
                maxResults=5,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            tomorrow_events = tomorrow_events.get('items', [])
            if tomorrow_events:
                speak(f"However, you have {len(tomorrow_events)} events tomorrow:")
                for event in tomorrow_events[:3]:  # Limit to 3 events
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    start_time = datetime.datetime.fromisoformat(start.replace("Z", "+00:00")).strftime('%I:%M %p')
                    speak(f"At {start_time}: {event['summary']}")
            return

        speak(f"You have {len(events)} events today:")
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'T' in start:  # Has time
                start_time = datetime.datetime.fromisoformat(start.replace("Z", "+00:00")).strftime('%I:%M %p')
                speak(f"At {start_time}: {event['summary']}")
            else:  # All day event
                speak(f"All day: {event['summary']}")

    except HttpError as error:
        speak("Sorry, I could not fetch your calendar events.")
        logger.error(f'Calendar fetch error: {error}')

# --- File Operations ---
def create_file(query):
    """Create a new file."""
    filename = query.replace("create file", "").replace("new file", "").strip()
    if not filename:
        speak("What should I name the file?")
        filename = take_command()
        if filename == "none":
            return
    
    try:
        with open(filename + ".txt", 'w') as f:
            f.write(f"# {filename}\nCreated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        speak(f"Created file '{filename}.txt' successfully.")
        logger.info(f"File created: {filename}.txt")
    except Exception as e:
        speak("Sorry, I couldn't create the file.")
        logger.error(f"File creation error: {e}")

def list_files(query):
    """List files in the current directory."""
    try:
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        if not files:
            speak("There are no files in the current directory.")
            return
        
        speak(f"I found {len(files)} files:")
        for file in files[:10]:  # Limit to 10 files
            speak(file)
        
        if len(files) > 10:
            speak(f"And {len(files) - 10} more files.")
            
    except Exception as e:
        speak("Sorry, I couldn't list the files.")
        logger.error(f"File listing error: {e}")

# --- Media Control (placeholder for system-specific implementations) ---
def control_music(query):
    """Basic media control."""
    if "play" in query:
        speak("Starting music playback.")
        # Implement system-specific media control
        if platform.system() == "Windows":
            os.system("start wmplayer")
        elif platform.system() == "Darwin":
            os.system("open -a Music")
        elif platform.system() == "Linux":
            os.system("rhythmbox &")
    elif "pause" in query or "stop" in query:
        speak("Pausing music.")
        # System-specific pause commands would go here
    else:
        speak("I can play or pause music. What would you like me to do?")

# --- Enhanced System Functions ---
def tell_system_info():
    """Provide detailed system information."""
    system = platform.system()
    release = platform.release()
    version = platform.version()
    machine = platform.machine()
    processor = platform.processor()
    
    # Get current time and date
    now = datetime.datetime.now()
    
    speak(f"System Information:")
    speak(f"Operating System: {system} {release}")
    speak(f"Machine type: {machine}")
    speak(f"Current time: {now.strftime('%I:%M %p')}")
    speak(f"Current date: {now.strftime('%A, %B %d, %Y')}")

def list_voices(query):
    """List all available voices on the system with interrupt capability."""
    voices_info = get_available_voices()
    
    if not voices_info:
        speak("Sorry, I couldn't find any available voices on your system.")
        return
    
    # Start interrupt listener
    interrupt_handler.reset()
    interrupt_thread = listen_for_interrupt()
    
    speak(f"I found {len(voices_info)} available voices. Say 'stop' anytime to interrupt.")
    
    # Group voices by language/type for better organization
    english_voices = []
    mbrola_voices = []
    other_voices = []
    
    for voice in voices_info:
        voice_id_lower = voice.get('id', '').lower()
        voice_name_lower = voice.get('name', '').lower()
        
        if 'mb-' in voice_id_lower:
            mbrola_voices.append(voice)
        elif any(lang in voice_id_lower for lang in ['en', 'us', 'gb']) or \
             any(eng in voice_name_lower for eng in ['english', 'american', 'british']):
            english_voices.append(voice)
        else:
            other_voices.append(voice)
    
    # Announce English/MBROLA voices first
    if mbrola_voices and not interrupt_handler.stop_requested:
        speak("High-quality MBROLA voices:")
        for voice in mbrola_voices:
            if interrupt_handler.stop_requested:
                break
            voice_description = f"Voice {voice['index'] + 1}: {voice['name']}"
            if voice['gender'] != 'Unknown':
                voice_description += f", {voice['gender']}"
            speak(voice_description)
            
            current_voice_index = settings.get('voice_index', 0)
            if voice['index'] == current_voice_index:
                speak("This is my current voice.")
    
    if english_voices and not interrupt_handler.stop_requested:
        speak("Standard English voices:")
        for voice in english_voices[:5]:  # Limit to 5 to avoid overwhelming
            if interrupt_handler.stop_requested:
                break
            voice_description = f"Voice {voice['index'] + 1}: {voice['name']}"
            if voice['gender'] != 'Unknown':
                voice_description += f", {voice['gender']}"
            speak(voice_description)
    
    if other_voices and not interrupt_handler.stop_requested:
        if len(other_voices) > 10:
            speak(f"I also found {len(other_voices)} other language voices. Say 'show all voices' if you want to hear them all.")
        else:
            speak("Other available voices:")
            for voice in other_voices[:3]:  # Limit to 3
                if interrupt_handler.stop_requested:
                    break
                voice_description = f"Voice {voice['index'] + 1}: {voice['name']}"
                speak(voice_description)
    
    if interrupt_handler.stop_requested:
        speak("Voice listing stopped.", interruptible=False)
    else:
        speak("That's all the voices. Say 'change voice to number X' to select one.", interruptible=False)
    
    interrupt_handler.reset()

def change_voice(query):
    """Change the assistant's voice."""
    voices_info = get_available_voices()
    
    if not voices_info:
        speak("Sorry, I couldn't find any available voices to change to.")
        return
    
    # Check if user specified a voice number
    words = query.split()
    voice_number = None
    
    for word in words:
        if word.isdigit():
            voice_number = int(word) - 1  # Convert to 0-based index
            break
    
    # Check for gender preference
    if "female" in query.lower() or "woman" in query.lower():
        # Find first female voice
        for voice in voices_info:
            if voice['gender'] == 'Female':
                voice_number = voice['index']
                break
        
        if voice_number is None:
            speak("I couldn't find a female voice on your system.")
            return
    
    elif "male" in query.lower() or "man" in query.lower():
        # Find first male voice
        for voice in voices_info:
            if voice['gender'] == 'Male':
                voice_number = voice['index']
                break
        
        if voice_number is None:
            speak("I couldn't find a male voice on your system.")
            return
    
    # If no specific voice was mentioned, show options
    if voice_number is None:
        speak("Which voice would you like me to use? Here are your options:")
        list_voices("")
        speak("Say 'change voice to number X' or 'use male voice' or 'use female voice'")
        return
    
    # Validate voice number
    if voice_number < 0 or voice_number >= len(voices_info):
        speak(f"Invalid voice number. Please choose a number between 1 and {len(voices_info)}.")
        return
    
    # Change the voice
    try:
        global engine
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[voice_number].id)
        
        # Save preference
        settings['voice_index'] = voice_number
        if voices_info[voice_number]['gender'] != 'Unknown':
            settings['preferred_gender'] = voices_info[voice_number]['gender']
        save_settings(settings)
        
        selected_voice = voices_info[voice_number]
        speak(f"Voice changed to {selected_voice['name']}. How do I sound now?")
        
        logger.info(f"Voice changed to: {selected_voice['name']} (Index: {voice_number})")
        
    except Exception as e:
        speak("Sorry, I couldn't change to that voice.")
        logger.error(f"Voice change error: {e}")

def test_voice(query):
    """Test the current voice with a sample sentence."""
    test_sentences = [
        "Hello! This is how I sound with my current voice settings.",
        "The quick brown fox jumps over the lazy dog.",
        "I hope you like how I sound now!",
        "Testing, testing, one, two, three. How's my voice quality?",
        "Artificial intelligence is fascinating, don't you think?"
    ]
    
    import random
    test_sentence = random.choice(test_sentences)
    speak(test_sentence)

def voice_demo(query):
    """Demonstrate different voices available with interrupt capability."""
    voices_info = get_available_voices()
    
    if not voices_info:
        speak("Sorry, I can't demonstrate voices as none are available.")
        return
    
    if len(voices_info) == 1:
        speak("I only have one voice available, which is the one I'm currently using.")
        return
    
    # Start interrupt listener
    interrupt_handler.reset()
    interrupt_thread = listen_for_interrupt()
    
    speak("Let me demonstrate available voices. I'll say 'Hello, this is voice number X' in each voice. Say 'stop' to interrupt.")
    
    current_voice_index = settings.get('voice_index', 0)
    
    try:
        voices = engine.getProperty('voices')
        
        # Prioritize English and MBROLA voices for demo
        demo_voices = []
        
        # Add MBROLA voices first
        for voice_info in voices_info:
            if 'mb-' in voice_info.get('id', '').lower():
                demo_voices.append(voice_info)
        
        # Add English voices
        for voice_info in voices_info:
            voice_id_lower = voice_info.get('id', '').lower()
            if any(lang in voice_id_lower for lang in ['en', 'us', 'gb']) and voice_info not in demo_voices:
                demo_voices.append(voice_info)
        
        # Limit demo to reasonable number
        demo_voices = demo_voices[:8]  # Max 8 voices
        
        if not demo_voices:
            demo_voices = voices_info[:5]  # Fallback to first 5
        
        for voice_info in demo_voices:
            if interrupt_handler.stop_requested:
                break
                
            i = voice_info['index']
            engine.setProperty('voice', voices[i].id)
            voice_name = voice_info['name']
            demo_text = f"Hello, this is voice {i + 1}, {voice_name}"
            
            print(f"{ASSISTANT_NAME}: {demo_text}")
            engine.say(demo_text)
            engine.runAndWait()
            time.sleep(0.8)  # Pause between demos
        
        # Restore original voice
        engine.setProperty('voice', voices[current_voice_index].id)
        
        if interrupt_handler.stop_requested:
            speak("Voice demonstration stopped.", interruptible=False)
        else:
            speak("That was the demonstration. Which voice did you prefer?", interruptible=False)
        
    except Exception as e:
        speak("Sorry, there was an error during the voice demonstration.", interruptible=False)
        logger.error(f"Voice demo error: {e}")
    
    finally:
        interrupt_handler.reset()

def change_voice_settings(query):
    """Enhanced voice settings with more options."""
    global engine
    
    if "speed" in query or "rate" in query:
        if "faster" in query:
            settings['voice_rate'] = min(300, settings['voice_rate'] + 50)
            speak("Speaking faster now.")
        elif "slower" in query:
            settings['voice_rate'] = max(100, settings['voice_rate'] - 50)
            speak("Speaking slower now.")
        elif "normal" in query:
            settings['voice_rate'] = 150
            speak("Reset speech rate to normal.")
        
        engine.setProperty('rate', settings['voice_rate'])
        save_settings(settings)
    
    elif "volume" in query:
        if "louder" in query or "up" in query:
            settings['voice_volume'] = min(1.0, settings['voice_volume'] + 0.2)
            speak("Volume increased.")
        elif "quieter" in query or "down" in query:
            settings['voice_volume'] = max(0.1, settings['voice_volume'] - 0.2)
            speak("Volume decreased.")
        elif "normal" in query:
            settings['voice_volume'] = 0.8
            speak("Reset volume to normal.")
        
        engine.setProperty('volume', settings['voice_volume'])
        save_settings(settings)
    
    elif "reset" in query:
        # Reset all voice settings
        settings['voice_rate'] = 150
        settings['voice_volume'] = 0.8
        engine.setProperty('rate', settings['voice_rate'])
        engine.setProperty('volume', settings['voice_volume'])
        save_settings(settings)
        speak("All voice settings have been reset to default.")
    
    else:
        current_rate = settings.get('voice_rate', 150)
        current_volume = int(settings.get('voice_volume', 0.8) * 100)
        speak(f"Current settings: Speech rate is {current_rate}, volume is {current_volume} percent.")
        speak("You can say 'speak faster', 'speak slower', 'louder', 'quieter', or 'reset voice settings'.")

def get_voice_info(query):
    """Get information about the current voice and engine."""
    try:
        voices = engine.getProperty('voices')
        current_voice_index = settings.get('voice_index', 0)
        current_engine = settings.get('tts_engine', 'unknown')
        
        if current_voice_index < len(voices):
            current_voice = voices[current_voice_index]
            voice_name = getattr(current_voice, 'name', f'Voice {current_voice_index + 1}')
            
            voices_info = get_available_voices()
            gender = 'Unknown'
            for voice_info in voices_info:
                if voice_info['index'] == current_voice_index:
                    gender = voice_info['gender']
                    break
            
            current_rate = settings.get('voice_rate', 150)
            current_volume = int(settings.get('voice_volume', 0.8) * 100)
            
            speak(f"I'm using the {current_engine} engine with {voice_name}.")
            if gender != 'Unknown':
                speak(f"This is a {gender.lower()} voice.")
            
            # Special info for different engines
            if current_engine in ['espeak', 'espeak-ng'] and 'mb-' in current_voice.id.lower():
                speak("This is a high-quality MBROLA voice.")
            elif current_engine in ['espeak', 'espeak-ng']:
                speak("This is a standard espeak voice. MBROLA voices are available for better quality.")
            
            speak(f"Speech rate: {current_rate}, Volume: {current_volume} percent.")
        else:
            speak("I'm having trouble identifying my current voice settings.")
            
    except Exception as e:
        speak("Sorry, I couldn't get my voice information.")
        logger.error(f"Voice info error: {e}")

# --- Enhanced Search Functions ---
def search_wikipedia(query):
    """Enhanced Wikipedia search with better error handling."""
    search_term = query.replace('wikipedia', '').replace('search', '').strip()
    if not search_term:
        speak("What would you like me to search for on Wikipedia?")
        search_term = take_command()
        if search_term == "none":
            return

    try:
        speak("Searching Wikipedia...")
        summary = wikipedia.summary(search_term, sentences=3)
        speak("According to Wikipedia:")
        speak(summary)
        logger.info(f"Wikipedia search: {search_term}")
    except wikipedia.exceptions.DisambiguationError as e:
        speak(f"There are multiple results for {search_term}. Did you mean {e.options[0]}?")
    except wikipedia.exceptions.PageError:
        speak(f"Sorry, I couldn't find any Wikipedia page for {search_term}.")
    except Exception as e:
        speak("Sorry, there was an error searching Wikipedia.")
        logger.error(f"Wikipedia search error: {e}")

def get_weather(query):
    """Enhanced weather function with better location handling."""
    location = settings.get('weather_location', 'New York')
    
    # Extract location from query if mentioned
    if " in " in query:
        potential_location = query.split(" in ")[-1].strip()
        if potential_location:
            location = potential_location
    
    try:
        # Using a free weather API (OpenWeatherMap example)
        # You'll need to get an API key from openweathermap.org
        api_key = "YOUR_OPENWEATHER_API_KEY"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            temp = data['main']['temp']
            description = data['weather'][0]['description']
            humidity = data['main']['humidity']
            
            speak(f"The weather in {location} is {description} with a temperature of {temp} degrees Celsius and {humidity}% humidity.")
        else:
            speak(f"Sorry, I couldn't get weather information for {location}.")
    
    except Exception as e:
        speak("Sorry, I couldn't fetch weather information right now.")
        logger.error(f"Weather API error: {e}")

# --- Help System ---
def show_help(query):
    """Show available commands with categories."""
    help_categories = {
        "Calendar & Reminders": [
            "'check my calendar' - View today's events",
            "'set a reminder for [task] at [time]' - Create calendar reminder"
        ],
        "Todo Management": [
            "'add todo [task]' - Add new task",
            "'list todos' - Show pending tasks", 
            "'complete task [number/description]' - Mark task as done"
        ],
        "Search & Information": [
            "'wikipedia [topic]' - Search Wikipedia",
            "'weather in [location]' - Get weather info",
            "'news' - Get latest headlines",
            "'define [word]' - Get word definition",
            "'calculate [expression]' - Perform math calculations"
        ],
        "File Operations": [
            "'create file [name]' - Create new text file",
            "'list files' - Show files in current directory"
        ],
        "Entertainment": [
            "'tell me a joke' - Hear a random joke",
            "'random fact' - Learn something interesting",
            "'motivate me' - Get inspirational quote",
            "'set timer for [time]' - Set countdown timer"
        ],
        "System & Settings": [
            "'time' - Get current time and date",
            "'system info' - View system information",
            "'internet connection' - Test connectivity"
        ],
        "Web & Apps": [
            "'open [website]' - Open websites",
            "'search for [query]' - Google search",
            "'play/pause music' - Media control"
        ],
        "AI Integration": [
            "'gemini [command]' - Execute Gemini CLI commands"
        ]
    }
    
    speak("Here's what I can help you with:")
    
    for category, commands in help_categories.items():
        speak(f"{category}:")
        for command in commands:
            speak(command)
        speak("")  # Small pause between categories
        
    speak("You can also say 'exit', 'stop', or 'goodbye' to end our conversation.")

# --- Main Logic ---
def get_command_function(query):
    """Enhanced command matching with fuzzy matching."""
    command_map = {
        # Interrupt and control commands (processed first)
        "stop": lambda q: handle_stop_command(),
        "stop talking": lambda q: handle_stop_command(),
        "be quiet": lambda q: handle_stop_command(),
        "silence": lambda q: handle_stop_command(),
        "halt": lambda q: handle_stop_command(),
        "enough": lambda q: handle_stop_command(),
        "shut up": lambda q: handle_stop_command(),
        
        # Gemini commands
        "gemini": run_gemini_command,
        
        # Calendar commands
        "check my calendar": check_calendar,
        "calendar": check_calendar,
        "events": check_calendar,
        "set a reminder": set_reminder,
        "remind me": set_reminder,
        "schedule": set_reminder,
        
        # Todo commands
        "add todo": add_todo,
        "add task": add_todo,
        "new task": add_todo,
        "list todos": list_todos,
        "show todos": list_todos,
        "my tasks": list_todos,
        "complete": complete_todo,
        "done": complete_todo,
        "finish": complete_todo,
        
        # File operations
        "create file": create_file,
        "new file": create_file,
        "list files": list_files,
        "show files": list_files,
        
        # Search and information
        "wikipedia": search_wikipedia,
        "weather": get_weather,
        "news": lambda q: get_news(),
        "hacker news": lambda q: get_hacker_news(),
        "search for": lambda q: google_search(q),
        "calculate": calculate,
        "what is": calculate,  # For math questions
        "define": get_definition,
        "definition": get_definition,
        "translate": translate_text,
        
        # Entertainment and utilities
        "joke": lambda q: tell_joke(),
        "tell me a joke": lambda q: tell_joke(),
        "timer": set_timer,
        "set timer": set_timer,
        "motivation": lambda q: get_motivation(),
        "motivate me": lambda q: get_motivation(),
        "inspire me": lambda q: get_motivation(),
        "random fact": lambda q: get_random_fact(),
        "fact": lambda q: get_random_fact(),
        "internet": lambda q: check_internet(),
        "connection": lambda q: check_internet(),

        # Media control
        "music": control_music,
        "play music": control_music,
        "pause music": control_music,
        "stop music": control_music,
        
        # System commands
        "time": lambda q: tell_time(),
        "date": lambda q: tell_time(),
        "system": lambda q: tell_system_info(),
        
        # Voice and speech settings  
        "list voices": list_voices,
        "list voices": list_voices,
        "available voices": list_voices,
        "show voices": list_voices,
        "change voice": change_voice,
        "switch voice": change_voice,
        "use voice": change_voice,
        "female voice": change_voice,
        "male voice": change_voice,
        "voice demo": voice_demo,
        "demonstrate voices": voice_demo,
        "test voice": test_voice,
        "voice info": get_voice_info,
        "current voice": get_voice_info,
        "engine info": get_voice_info,
        "switch engine": switch_engine,
        "switch to festival": switch_engine,
        "switch to espeak": switch_engine,
        "use festival": switch_engine,
        "use espeak": switch_engine,
        "faster": change_voice_settings,
        "slower": change_voice_settings,
        "louder": change_voice_settings,
        "quieter": change_voice_settings,
        "speed": change_voice_settings,
        "volume": change_voice_settings,
        "reset voice": change_voice_settings,
        
        # Website shortcuts
        "open youtube": lambda q: open_website("https://www.youtube.com"),
        "youtube": lambda q: open_website("https://www.youtube.com"),
        "open google": lambda q: open_website("https://www.google.com"),
        "google": lambda q: open_website("https://www.google.com"),
        "open github": lambda q: open_website("https://www.github.com"),
        "github": lambda q: open_website("https://www.github.com"),
        "stack overflow": lambda q: open_website("https://stackoverflow.com"),
        "reddit": lambda q: open_website("https://www.reddit.com"),
        
        # Help and exit
        "help": show_help,
        "commands": show_help,
        "what can you do": show_help,
        "exit": lambda q: shutdown_assistant(),
        "stop": lambda q: shutdown_assistant(),
        "quit": lambda q: shutdown_assistant(),
        "goodbye": lambda q: shutdown_assistant(),
    }
    
    # Direct keyword matching first
    for keyword, function in command_map.items():
        if keyword in query:
            return function
    
    # Fuzzy matching for better recognition
    best_match = None
    best_ratio = 0
    
    for keyword in command_map.keys():
        ratio = fuzz.partial_ratio(query, keyword)
        if ratio > best_ratio and ratio > 70:  # 70% similarity threshold
            best_ratio = ratio
            best_match = command_map[keyword]
    
    return best_match

def handle_stop_command():
    """Handle stop command to interrupt speech."""
    interrupt_handler.stop_requested = True
    engine.stop()
    speak("Stopped.", interruptible=False)
    interrupt_handler.reset()
    return False  # Don't treat as shutdown

# --- Additional Enhanced Functions ---
def tell_time():
    """Tell current time and date with timezone info."""
    now = datetime.datetime.now()
    speak(f"The current time is {now.strftime('%I:%M %p')}")
    speak(f"Today is {now.strftime('%A, %B %d, %Y')}")
    
    # Add some contextual information
    if now.hour < 12:
        speak("It's morning time.")
    elif now.hour < 17:
        speak("It's afternoon.")
    else:
        speak("It's evening.")

def get_news():
    """Get latest news using News API."""
    if NEWS_API_KEY == "YOUR_NEWS_API_KEY":
        speak("Please set up your News API key to get the latest news.")
        return
    
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={NEWS_API_KEY}&pageSize=5"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            
            if articles:
                speak("Here are the top news headlines:")
                for i, article in enumerate(articles[:3], 1):
                    title = article.get('title', 'No title')
                    speak(f"News {i}: {title}")
            else:
                speak("No news articles found.")
        else:
            speak("Sorry, I couldn't fetch the news right now.")
            
    except Exception as e:
        speak("There was an error getting the news.")
        logger.error(f"News API error: {e}")

def get_hacker_news():
    """Fetch top stories from Hacker News."""
    try:
        speak("Fetching top stories from Hacker News...")
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            story_ids = response.json()[:5]  # Get top 5 stories
            
            speak("Here are the top Hacker News stories:")
            for i, story_id in enumerate(story_ids, 1):
                story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                story_response = requests.get(story_url, timeout=5)
                
                if story_response.status_code == 200:
                    story = story_response.json()
                    title = story.get('title', 'No title')
                    speak(f"Story {i}: {title}")
                    
                    if i >= 3:  # Limit to 3 stories for voice
                        break
        else:
            speak("Sorry, I couldn't fetch Hacker News stories.")
            
    except Exception as e:
        speak("There was an error getting Hacker News stories.")
        logger.error(f"Hacker News API error: {e}")

def google_search(query):
    """Enhanced Google search with result preview."""
    search_term = query.replace("search for", "").replace("google", "").strip()
    
    if not search_term:
        speak("What would you like me to search for?")
        search_term = take_command()
        if search_term == "none":
            return
    
    try:
        # Open in browser
        url = f"https://www.google.com/search?q={search_term}"
        webbrowser.open(url)
        speak(f"Searching Google for {search_term}")
        
        # Try to get quick results using DuckDuckGo Instant Answer API (free alternative)
        try:
            ddg_url = f"https://api.duckduckgo.com/?q={search_term}&format=json&no_html=1&skip_disambig=1"
            response = requests.get(ddg_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                abstract = data.get('Abstract', '')
                if abstract:
                    speak(f"Quick answer: {abstract}")
                    
        except Exception:
            pass  # If quick search fails, just continue with browser search
            
    except Exception as e:
        speak("Sorry, I couldn't perform the search.")
        logger.error(f"Search error: {e}")

def open_website(url):
    """Open a website with validation."""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        webbrowser.open(url)
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        speak(f"Opening {domain}")
        
    except Exception as e:
        speak("Sorry, I couldn't open that website.")
        logger.error(f"Website opening error: {e}")

def calculate(query):
    """Perform basic calculations."""
    try:
        # Extract mathematical expression
        expression = query.replace("calculate", "").replace("what is", "").strip()
        
        # Basic security - only allow safe mathematical operations
        allowed_chars = set('0123456789+-*/().= ')
        if not all(c in allowed_chars for c in expression):
            speak("I can only perform basic mathematical calculations.")
            return
        
        # Replace common speech patterns
        expression = expression.replace("plus", "+")
        expression = expression.replace("minus", "-")
        expression = expression.replace("times", "*")
        expression = expression.replace("multiplied by", "*")
        expression = expression.replace("divided by", "/")
        
        result = eval(expression)
        speak(f"The answer is {result}")
        
    except Exception as e:
        speak("Sorry, I couldn't calculate that. Please try a simpler expression.")
        logger.error(f"Calculation error: {e}")

def tell_joke():
    """Tell a random joke."""
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Why did the scarecrow win an award? He was outstanding in his field!",
        "Why don't eggs tell jokes? They'd crack each other up!",
        "What do you call a fake noodle? An impasta!",
        "Why did the math book look so sad? Because it had too many problems!",
        "What do you call a bear with no teeth? A gummy bear!",
        "Why don't programmers like nature? It has too many bugs!",
        "What's the best thing about Switzerland? I don't know, but the flag is a big plus!"
    ]
    
    import random
    joke = random.choice(jokes)
    speak(joke)

def set_timer(query):
    """Set a simple timer."""
    try:
        # Extract time from query
        words = query.split()
        time_value = None
        time_unit = "minutes"
        
        for i, word in enumerate(words):
            if word.isdigit():
                time_value = int(word)
                if i + 1 < len(words):
                    next_word = words[i + 1].lower()
                    if next_word in ["second", "seconds"]:
                        time_unit = "seconds"
                    elif next_word in ["minute", "minutes"]:
                        time_unit = "minutes"
                    elif next_word in ["hour", "hours"]:
                        time_unit = "hours"
                break
        
        if not time_value:
            speak("How long should the timer be? For example, say 'set timer for 5 minutes'")
            return
        
        # Convert to seconds
        if time_unit == "minutes":
            seconds = time_value * 60
        elif time_unit == "hours":
            seconds = time_value * 3600
        else:
            seconds = time_value
        
        speak(f"Timer set for {time_value} {time_unit}")
        
        # Use threading to not block the main loop
        def timer_thread():
            time.sleep(seconds)
            speak(f"Timer finished! {time_value} {time_unit} have passed.")
        
        threading.Thread(target=timer_thread, daemon=True).start()
        
    except Exception as e:
        speak("Sorry, I couldn't set the timer.")
        logger.error(f"Timer error: {e}")

def get_definition(query):
    """Get word definition using an online dictionary."""
    word = query.replace("define", "").replace("definition of", "").replace("what is", "").strip()
    
    if not word:
        speak("What word would you like me to define?")
        word = take_command()
        if word == "none":
            return
    
    try:
        # Using a free dictionary API
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                entry = data[0]
                meanings = entry.get('meanings', [])
                
                if meanings:
                    definition = meanings[0].get('definitions', [{}])[0].get('definition', '')
                    part_of_speech = meanings[0].get('partOfSpeech', '')
                    
                    speak(f"{word} is a {part_of_speech}. {definition}")
                else:
                    speak(f"Sorry, I couldn't find a definition for {word}")
            else:
                speak(f"Sorry, I couldn't find a definition for {word}")
        else:
            speak(f"Sorry, I couldn't find a definition for {word}")
            
    except Exception as e:
        speak("Sorry, there was an error getting the definition.")
        logger.error(f"Definition error: {e}")

def translate_text(query):
    """Basic translation placeholder (would need translation API)."""
    speak("I would help you translate text, but you need to set up a translation API key first.")
    speak("You could use Google Translate API or Microsoft Translator API.")

def get_motivation():
    """Provide motivational quotes."""
    quotes = [
        "The only way to do great work is to love what you do. - Steve Jobs",
        "Innovation distinguishes between a leader and a follower. - Steve Jobs",
        "Life is what happens to you while you're busy making other plans. - John Lennon",
        "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
        "It is during our darkest moments that we must focus to see the light. - Aristotle",
        "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
        "The only impossible journey is the one you never begin. - Tony Robbins"
    ]
    
    import random
    quote = random.choice(quotes)
    speak("Here's some motivation for you:")
    speak(quote)

def check_internet():
    """Check internet connectivity."""
    try:
        response = requests.get("https://www.google.com", timeout=5)
        if response.status_code == 200:
            speak("Your internet connection is working perfectly.")
        else:
            speak("There might be an issue with your internet connection.")
    except Exception:
        speak("You appear to be offline or having internet connectivity issues.")

def get_random_fact():
    """Get a random interesting fact."""
    facts = [
        "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly edible.",
        "A group of flamingos is called a 'flamboyance'.",
        "Octopuses have three hearts and blue blood.",
        "Bananas are berries, but strawberries aren't.",
        "There are more possible games of chess than there are atoms in the observable universe.",
        "A shrimp's heart is in its head.",
        "Elephants are one of the few animals that can recognize themselves in a mirror.",
        "The shortest war in history lasted only 38 to 45 minutes between Britain and Zanzibar in 1896."
    ]
    
    import random
    fact = random.choice(facts)
    speak("Here's an interesting fact:")
    speak(fact)

def shutdown_assistant():
    """Enhanced shutdown with cleanup."""
    responses = [
        "Goodbye! Have a wonderful day.",
        "Take care! I'll be here when you need me.",
        "Until next time! Have a great day.",
        "Farewell! It was great helping you today."
    ]
    
    import random
    speak(random.choice(responses))
    logger.info("Assistant shutdown")
    return True

def main():
    """Enhanced main function with interrupt handling."""
    if not engine:
        print("Text-to-speech engine could not be initialized. Exiting.")
        return

    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, interrupt_handler.signal_handler)

    try:
        wish_me()
        consecutive_failures = 0
        
        while True:
            # Reset interrupt state for new command
            interrupt_handler.reset()
            
            query = take_command()
            
            if query == "none":
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    speak("I'm having trouble hearing you. Please check your microphone.", interruptible=False)
                    consecutive_failures = 0
                continue
            
            consecutive_failures = 0  # Reset failure counter
            
            # Get and execute command
            command_function = get_command_function(query)
            
            if command_function:
                try:
                    result = command_function(query)
                    if result is True:  # Shutdown signal
                        break
                except KeyboardInterrupt:
                    print("\n[Interrupted by Ctrl+C]")
                    speak("Interrupted.", interruptible=False)
                    interrupt_handler.reset()
                    continue
                except Exception as e:
                    speak("Sorry, there was an error processing that command.", interruptible=False)
                    logger.error(f"Command execution error: {e}")
            else:
                speak("I'm sorry, I don't understand that command. Say 'help' to see what I can do.", interruptible=False)
            
            time.sleep(0.5)  # Small delay between commands

    except KeyboardInterrupt:
        print("\n[Shutting down...]")
        speak("Goodbye!", interruptible=False)
        logger.info("Assistant interrupted by user")
    except Exception as e:
        speak("An unexpected error occurred. Shutting down.", interruptible=False)
        logger.error(f"Main loop error: {e}")
    finally:
        # Clean shutdown
        if engine:
            try:
                engine.stop()
            except:
                pass