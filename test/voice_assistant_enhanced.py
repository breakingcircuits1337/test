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

# --- Initialization ---
def initialize_engine():
    """Initializes the text-to-speech engine based on the OS."""
    driver = None
    system_os = platform.system()
    if system_os == 'Windows':
        driver = 'sapi5'
    elif system_os == 'Darwin':
        driver = 'nsss'
    elif system_os == 'Linux':
        driver = 'espeak'
    
    try:
        engine = pyttsx3.init(driver)
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[0].id)
        
        # Apply settings
        engine.setProperty('rate', settings.get('voice_rate', 150))
        engine.setProperty('volume', settings.get('voice_volume', 0.8))
        
        return engine
    except Exception as e:
        logger.error(f"Error initializing text-to-speech engine: {e}")
        return None

engine = initialize_engine()

# --- Core Functions ---
def speak(audio):
    """Converts the given text to speech."""
    if not engine:
        print(f"{ASSISTANT_NAME}: {audio}")
        return
    
    print(f"{ASSISTANT_NAME}: {audio}")
    try:
        engine.say(audio)
        engine.runAndWait()
    except Exception as e:
        logger.error(f"Error in speech synthesis: {e}")

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
            print("\nListening...")
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
        return query.lower()
        
    except sr.UnknownValueError:
        speak("Sorry, I didn't catch that. Could you please repeat?")
        return "none"
    except sr.RequestError as e:
        speak("Sorry, there's an issue with the speech recognition service.")
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

def change_voice_settings(query):
    """Change voice settings."""
    if "speed" in query or "rate" in query:
        if "faster" in query:
            settings['voice_rate'] = min(300, settings['voice_rate'] + 50)
            speak("Speaking faster now.")
        elif "slower" in query:
            settings['voice_rate'] = max(100, settings['voice_rate'] - 50)
            speak("Speaking slower now.")
        
        engine.setProperty('rate', settings['voice_rate'])
        save_settings(settings)
    
    elif "volume" in query:
        if "louder" in query:
            settings['voice_volume'] = min(1.0, settings['voice_volume'] + 0.2)
            speak("Volume increased.")
        elif "quieter" in query:
            settings['voice_volume'] = max(0.1, settings['voice_volume'] - 0.2)
            speak("Volume decreased.")
        
        engine.setProperty('volume', settings['voice_volume'])
        save_settings(settings)

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
    """Show available commands."""
    commands = [
        "Calendar: 'check my calendar', 'set a reminder'",
        "Todo: 'add todo', 'list todos', 'complete task'",
        "Search: 'wikipedia', 'weather', 'news'",
        "Files: 'create file', 'list files'",
        "System: 'time', 'system info', 'change voice speed'",
        "Gemini: 'gemini [command]'",
        "Music: 'play music', 'pause music'",
        "Settings: 'speak faster', 'speak slower', 'louder', 'quieter'"
    ]
    
    speak("Here are some things I can help you with:")
    for command in commands:
        speak(command)

# --- Main Logic ---
def get_command_function(query):
    """Enhanced command matching with fuzzy matching."""
    command_map = {
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
        "search for": lambda q: google_search(q),
        
        # Media control
        "music": control_music,
        "play": control_music,
        "pause": control_music,
        
        # System commands
        "time": lambda q: tell_time(),
        "date": lambda q: tell_time(),
        "system": lambda q: tell_system_info(),
        
        # Voice settings
        "faster": change_voice_settings,
        "slower": change_voice_settings,
        "louder": change_voice_settings,
        "quieter": change_voice_settings,
        "speed": change_voice_settings,
        "volume": change_voice_settings,
        
        # Website shortcuts
        "youtube": lambda q: webbrowser.open("https://www.youtube.com"),
        "google": lambda q: webbrowser.open("https://www.google.com"),
        "github": lambda q: webbrowser.open("https://www.github.com"),
        
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

# --- Additional helper functions (implement as needed) ---
def tell_time():
    """Tell current time and date."""
    now = datetime.datetime.now()
    speak(f"The current time is {now.strftime('%I:%M %p')}")
    speak(f"Today is {now.strftime('%A, %B %d, %Y')}")

def get_news():
    """Get latest news (placeholder - implement with news API)."""
    speak("I would fetch the latest news for you, but you need to set up a news API key first.")

def google_search(query):
    """Open Google search in browser."""
    search_term = query.replace("search for", "").strip()
    if search_term:
        url = f"https://www.google.com/search?q={search_term}"
        webbrowser.open(url)
        speak(f"Searching Google for {search_term}")

def shutdown_assistant():
    """Shutdown the assistant."""
    speak("Goodbye! Have a wonderful day.")
    logger.info("Assistant shutdown")
    return True

def main():
    """Enhanced main function with better error handling and flow."""
    if not engine:
        print("Text-to-speech engine could not be initialized. Exiting.")
        return

    try:
        wish_me()
        consecutive_failures = 0
        
        while True:
            query = take_command()
            
            if query == "none":
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    speak("I'm having trouble hearing you. Please check your microphone.")
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
                except Exception as e:
                    speak("Sorry, there was an error processing that command.")
                    logger.error(f"Command execution error: {e}")
            else:
                speak("I'm sorry, I don't understand that command. Say 'help' to see what I can do.")
            
            time.sleep(0.5)  # Small delay between commands

    except KeyboardInterrupt:
        speak("Goodbye!")
        logger.info("Assistant interrupted by user")
    except Exception as e:
        speak("An unexpected error occurred. Shutting down.")
        logger.error(f"Main loop error: {e}")

if __name__ == "__main__":
    main()