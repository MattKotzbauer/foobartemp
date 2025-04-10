"""
Class for recognizing hand input from camera.

Mediapipe usage: https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python
"""

import numpy as np
import cv2

import mediapipe as mp

VisionRunningMode = mp.tasks.vision.RunningMode


class HandInput:
    def __init__(self):
        self.capture = cv2.VideoCapture(0)
        self.last_frame = None

        # Mediapipe methods
        mp_hands = mp.solutions.hands
        self.hands = mp_hands.Hands(
            running_mode=VisionRunningMode.LIVE_STREAM,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarks = [None, None]

        # Error handling
        if not self.capture.isOpened():
            print("Error: Could not open camera.")

    def get_frame(self):
        """
        Captures a frame from the camera and returns it
        Return type: (has_frame: bool, frame_data: np.ndarray)
        """
        if not self.capture.isOpened():
            return None
        ret, frame = self.capture.read()
        if not ret:
            return None

        # Flip frame vertically and use RGB (not BGR)
        frame = frame[::-1, :, [2, 1, 0]]
        self.last_frame = frame
        return frame

    def get_gesture(self):
        frame = self.last_frame
        if frame is None:
            return None

        # Detect landmarks using mediapipe
        results = self.hands.process(frame)
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                print(hand_landmarks)

        return None

    def release(self):
        """
        Releases the camera resource
        """
        if self.capture.isOpened():
            self.capture.release()
