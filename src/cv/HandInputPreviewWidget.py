import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from kivy.clock import Clock as kivyClock
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.uix.image import Image

from imslib.core import BaseWidget, run
from imslib.gfxutil import topleft_label, resize_topleft_label

from HandInput import HandInput

import cv2


class HandInputPreviewWidget(BaseWidget):
    def __init__(self):
        super(HandInputPreviewWidget, self).__init__()

        self.hand_input = HandInput()

        # Create an Image widget to display the camera feed
        self.camera_view = Image()
        self.camera_view.size = Window.size
        self.add_widget(self.camera_view)

        self.info = topleft_label()
        self.add_widget(self.info)

        # Schedule the update method
        # kivyClock.schedule_interval(self.update_camera, 1.0 / 30.0)  # 30 FPS

    def update_camera(self):
        """
        Updates the camera view with the latest frame
        """
        frame = self.hand_input.get_frame()
        if frame is not None:
            # Convert the frame to a texture
            buf = frame.tobytes()

            # Create texture
            texture = Texture.create(
                size=(frame.shape[1], frame.shape[0]), colorfmt="rgb"
            )
            texture.blit_buffer(buf, colorfmt="rgb", bufferfmt="ubyte")

            # Display the texture in the Image widget
            self.camera_view.texture = texture

    def on_resize(self, size):
        resize_topleft_label(self.info)

    def on_update(self):
        self.info.text = f"time: {kivyClock.time():.2f}\nFPS: {kivyClock.get_fps():.2f}"
        self.update_camera()
        self.info.text += f"gesture: {self.hand_input.get_gesture()}"

    def on_stop(self):
        # Release camera resource
        self.hand_input.release()


if __name__ == "__main__":
    run(HandInputPreviewWidget())
