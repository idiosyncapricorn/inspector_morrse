from flask import Flask, render_template, request, jsonify
import speech_recognition as sr
import hashlib
import random
import sqlite3
import sounddevice as sd
import numpy as np
import wave
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Morse code dictionary
MORSE_MAP = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..", " ": "/"
}

DATABASE_FILE = "passwords.db"
SPECIAL_CHARACTERS = "!@#$%^&*()-_+=<>?"

def initialize_database():
    """Create a SQLite database and a table for passwords if it doesn't exist."""
    logging.info("Initializing the database...")
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS passwords
                      (phrase TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    conn.close()
    logging.info("Database initialized successfully.")

def to_morse(text):
    """Convert text to Morse code."""
    return ''.join(MORSE_MAP.get(char, "") for char in text.upper())

def generate_hashed_password(morse_code):
    """Generate a consistent hashed password based on the Morse code."""
    hash_object = hashlib.sha256(morse_code.encode())
    base_password = hash_object.hexdigest()[:12]

    # Randomly capitalize some letters
    password_chars = [char.upper() if random.choice([True, False]) else char for char in base_password]

    # Add special characters at random positions
    num_special_chars = random.randint(1, 3)
    for _ in range(num_special_chars):
        special_char = random.choice(SPECIAL_CHARACTERS)
        position = random.randint(0, len(password_chars))
        password_chars.insert(position, special_char)

    return ''.join(password_chars)

def load_passwords():
    """Load existing passwords from the SQLite database."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT phrase, password FROM passwords")
    passwords = {phrase: password for phrase, password in cursor.fetchall()}
    conn.close()
    return passwords

def save_password(phrase, password):
    """Save a password to the SQLite database."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO passwords (phrase, password) VALUES (?, ?)", (phrase, password))
    conn.commit()
    conn.close()

def record_audio(filename, duration=5):
    """Record audio from the microphone and save it to a file."""
    logging.info("Recording...")
    sample_rate = 44100  # Sample rate in Hz
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float64')
    sd.wait()  # Wait until the recording is finished
    logging.info("Recording complete.")

    # Save the recording to a WAV file
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 2 bytes for 'int16'
        wf.setframerate(sample_rate)
        wf.writeframes((recording * 32767).astype(np.int16).tobytes())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_password', methods=['POST'])
def generate_password():
    """Handle recording audio, processing it to generate a password."""
    audio_filename = "recorded_audio.wav"
    record_audio(audio_filename, duration=5)  # Record for 5 seconds

    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_filename) as source:
        audio = recognizer.record(source)

    try:
        speech_text = recognizer.recognize_google(audio)
        logging.info(f"Recognized text: {speech_text}")
        
        morse_code = to_morse(speech_text)

        passwords = load_passwords()
        if speech_text in passwords:
            password = passwords[speech_text]
        else:
            password = generate_hashed_password(morse_code)
            save_password(speech_text, password)
            logging.info(f"New password generated and saved for phrase: {speech_text}")

        return jsonify({'status': 'success', 'password': password})

    except sr.UnknownValueError:
        logging.error('Could not understand the audio.')
        return jsonify({'status': 'error', 'message': 'Could not understand the audio.'})
    except sr.RequestError as e:
        logging.error(f'Speech recognition service error: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)})
    except Exception as e:
        logging.error(f'An unexpected error occurred: {str(e)}')
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred.'})

if __name__ == '__main__':
    # Check if the database file exists
    if not os.path.exists(DATABASE_FILE):
        initialize_database()  # Run this once to create the database
    else:
        logging.info("Database file exists. Checking for table...")
        # Check if the passwords table exists
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='passwords'")
            table_exists = cursor.fetchone() is not None
            conn.close()
            if not table_exists:
                logging.warning("The passwords table does not exist. Initializing the database.")
                initialize_database()
        except Exception as e:
            logging.error(f"Error checking for table existence: {str(e)}")
    
    app.run(debug=True)