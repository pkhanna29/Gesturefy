import os
import configparser
import spotipy
from spotipy.oauth2 import SpotifyOAuth # type: ignore
import cv2
import mediapipe as mp
import time
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton
from PyQt5.QtCore import Qt
import platform
if platform.system() == "Windows":
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
elif platform.system() == "Darwin":
    import sounddevice as sd
# Load Spotify configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Retrieve credentials from config file
CLIENT_ID = config['spotify']['client_id']
CLIENT_SECRET = config['spotify']['client_secret']
REDIRECT_URI = config['spotify']['redirect_uri']
SCOPE = config['spotify']['scope']

# Initialize Spotipy
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                               client_secret=CLIENT_SECRET,
                                               redirect_uri=REDIRECT_URI,
                                               scope=SCOPE))

# Initialize MediaPipe hands module
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)

# Your existing hand gesture functions (import from hand_gesture_detection.py)
from hand_gesture_detection import (is_closed_fist, is_open_fist, 
                                     is_pointing_right, is_pointing_left,
                                     is_pointing_up, is_pointing_down, 
                                     is_thumbs_up)

# Volume control functions using PyCaw
def set_volume(volume_change):
    if platform.system() == "Windows":
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        current_volume = volume.GetMasterVolumeLevelScalar()
        
        # volume set
        new_volume = current_volume + volume_change / 100.0
        new_volume = max(0.0, min(1.0, new_volume))  # Clamp volume between 0.0 and 1.0
        volume.SetMasterVolumeLevelScalar(new_volume, None)
    elif platform.system() == "Darwin":
        # Get current system volume
        current_volume = int(os.popen("osascript -e 'output volume of (get volume settings)'").read().strip())
        
        # Calculate new volume
        new_volume = current_volume + volume_change
        new_volume = max(0, min(100, new_volume))  # Clamp volume between 0 and 100
        
        # Set system volume using AppleScript
        os.system(f"osascript -e 'set volume output volume {new_volume}'")
        print(f"Volume set to {new_volume}%")
# Create the OverlayWindow class
class OverlayWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setGeometry(50, 0, 400, 100)  # Arbitrary values; adjust as needed
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Create button
        self.button = QPushButton('Use Hand Gestures', self)
        self.button.setGeometry(100, 20, 200, 60)  # Arbitrary values; adjust as needed
        self.button.clicked.connect(self.on_button_click)
        
        self.cap = None  # Initialize the video capture variable
        self.running = False  # Flag to check if gesture detection is running

    def on_button_click(self):
        if not self.running:  # If video capture is not initialized
            self.cap = cv2.VideoCapture(0)  # Initialize video capture
            if not self.cap.isOpened():
                print("Error: Could not open video capture.")
                return  # Exit the function if camera fails to open
            
            self.running = True  # Set the running flag
            self.button.setText('Stop using hand gestures')
            self.start_gesture_recognition()
        else:
            # Stop gesture recognition
            self.running = False  # Reset the running flag
            self.button.setText('Use Hand Gestures')

    def start_gesture_recognition(self):
        gesture_detected = None  # Store the currently detected gesture
        gesture_timeout = 2  # Timer for gesture recognition
        gesture_delay = 3  # Duration to recognize gesture
        gesture_printed = False  # Flag to control printing

        while self.running:  # Continuous loop for gesture recognition
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to capture frame")
                break

            # Flip the frame horizontally for a more intuitive user experience
            frame = cv2.flip(frame, 1)

            # Convert the frame to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame to detect hands
            results = hands.process(rgb_frame)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Check for different gestures
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    if is_closed_fist(hand_landmarks):
                        if not gesture_printed:  # Print only if not already printed
                            playback_info = sp.current_playback()  # Get current playback information
                            
                            # Check if a track is currently playing
                            if playback_info and playback_info['is_playing']:
                                print("A song is already playing. No action taken.")  # Inform that no action is taken
                            else:
                                devices = sp.devices()  # Get the list of available devices
                                
                                # Check for active devices
                                if devices['devices']:
                                    try:
                                        sp.start_playback()  # Play the song
                                        gesture_detected = "Closed Fist - Playing Song"
                                        gesture_timeout = time.time() + gesture_delay
                                        print(gesture_detected)  # Print gesture
                                        gesture_printed = True  # Set flag to prevent re-printing
                                    except Exception as e:
                                        print(f"Error starting playback: {e}")  # Print error message
                                else:
                                    print("No active devices found for playback.")  # Handle no active device case
                    elif is_pointing_down(hand_landmarks):
                        if not gesture_printed:
                            gesture_detected = "Pointing Down"
                            gesture_timeout = time.time() + gesture_delay
                            print(gesture_detected)
                            gesture_printed = True
                            set_volume(-10)  # Decrease volume
                    elif is_open_fist(hand_landmarks):
                        if not gesture_printed:  # Print only if not already printed
                            playback_info = sp.current_playback()  # Get current playback information
                            
                            # Check if a track is currently paused
                            if playback_info and not playback_info['is_playing']:
                                print("A song is already paused. No action taken.")  # Inform that no action is taken
                            else:
                                try:
                                    sp.pause_playback()  # Pause the song
                                    gesture_detected = "Open Fist - Pausing Song"
                                    gesture_timeout = time.time() + gesture_delay
                                    print(gesture_detected)  # Print gesture
                                    gesture_printed = True  # Set flag to prevent re-printing
                                except Exception as e:
                                    print(f"Error pausing playback: {e}")  # Print error message
                    elif is_thumbs_up(hand_landmarks):
                        if not gesture_printed:  # Print only if not already printed
                            # Get the current playback
                            current_playback = sp.current_playback()
                            
                            if current_playback and current_playback['item']:
                                track_id = current_playback['item']['id']  # Extract the track ID
                                
                                # Like the song
                                sp.current_user_saved_tracks_add([track_id])  # Pass the track ID
                                
                                gesture_detected = "Thumbs Up - Liked Song"
                                gesture_timeout = time.time() + gesture_delay
                                print(gesture_detected)  # Print gesture
                                gesture_printed = True  # Set flag to prevent re-printing
                            else:
                                print("No song is currently playing.")  # Handle case when no track is playing
                    elif is_pointing_up(hand_landmarks):
                        if not gesture_printed:
                            gesture_detected = "Pointing Up"
                            gesture_timeout = time.time() + gesture_delay
                            print(gesture_detected)
                            gesture_printed = True
                            set_volume(10)  # Increase volume
                    elif is_pointing_right(hand_landmarks):
                        if not gesture_printed:
                            gesture_detected = "Pointing Right"
                            gesture_timeout = time.time() + gesture_delay
                            print(gesture_detected)
                            gesture_printed = True
                            sp.next_track()  # Skip the song
                    elif is_pointing_left(hand_landmarks):
                        if not gesture_printed:
                            gesture_detected = "Pointing Left"
                            gesture_timeout = time.time() + gesture_delay
                            print(gesture_detected)
                            gesture_printed = True
                            sp.previous_track()  # Rewind the song

            # Display the detected gesture
            if gesture_detected:
                if time.time() < gesture_timeout:
                    cv2.putText(frame, gesture_detected, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 225, 0), 2)
                else:
                    gesture_detected = None
                    gesture_printed = False
            else:
                cv2.putText(frame, "No Hand Detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

            # Show the frame with drawn landmarks
            # cv2.imshow("Hand Gesture Detection", frame)

            # Check for 'q' key to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Release resources after exiting the loop
        self.cap.release()
        cv2.destroyAllWindows()

# Add the following lines to run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OverlayWindow()
    window.show()
    sys.exit(app.exec_())

