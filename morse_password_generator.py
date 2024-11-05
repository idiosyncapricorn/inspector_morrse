import speech_recognition as sr
import hashlib
import os
import random
import sqlite3
import tkinter as tk

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
running = False

def create_database():
    """Create a SQLite database and a table for passwords if it doesn't exist."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS passwords
                      (phrase TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    conn.close()

def to_morse(text):
    """Convert text to Morse code."""
    return ''.join(MORSE_MAP.get(char, "") for char in text.upper())

def generate_hashed_password(morse_code):
    """Generate a consistent hashed password based on the Morse code, with random capitalization and special characters throughout."""
    hash_object = hashlib.sha256(morse_code.encode())
    base_password = hash_object.hexdigest()[:12]  # Take the first 12 characters of the hash

    # Randomly capitalize some letters
    password_chars = [char.upper() if random.choice([True, False]) else char for char in base_password]

    # Add multiple special characters at random positions
    num_special_chars = random.randint(1, 3)  # Adjust the range for the number of special characters you want
    for _ in range(num_special_chars):
        special_char = random.choice(SPECIAL_CHARACTERS)
        position = random.randint(0, len(password_chars))
        password_chars.insert(position, special_char)

    # Convert the list back to a string
    password = ''.join(password_chars)
    return password


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

def generate_password_from_speech():
    global running
    recognizer = sr.Recognizer()
    passwords = load_passwords()  # Load existing passwords at the start

    # Capture audio from the microphone
    with sr.Microphone() as source:
        print("Please say something...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        # Convert speech to text
        speech_text = recognizer.recognize_google(audio)
        print("You said:", speech_text)

        # Convert text to Morse code
        morse_code = to_morse(speech_text)
        print("Morse code:", morse_code)

        # Check if the password already exists
        if speech_text in passwords:
            # If it exists, recall the existing password
            password = passwords[speech_text]
            print("Retrieved Password:", password)
        else:
            # Generate a new password and save it
            password = generate_hashed_password(morse_code)
            print("Generated Password:", password)

            # Store the password associated with the original phrase
            save_password(speech_text, password)

    except sr.UnknownValueError:
        print("Could not understand the audio.")
    except sr.RequestError as e:
        print(f"Error with the speech recognition service: {e}")

def toggle_speech_recognition():
    global running
    if running:
        print("Speech recognition stopped.")
        running = False
    else:
        print("Speech recognition started.")
        running = True
        generate_password_from_speech()

# Create the SQLite database and table if it doesn't exist
create_database()

# Create the Tkinter window
root = tk.Tk()
root.title("Password Generator")

# Create a button to start/stop the speech recognition
toggle_button = tk.Button(root, text="Toggle Speech Recognition", command=toggle_speech_recognition)
toggle_button.pack(pady=20)

# Run the Tkinter event loop
root.mainloop()
