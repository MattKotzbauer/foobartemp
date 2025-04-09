#####################################################################
#
# This software is to be used for MIT's class Interactive Music Systems only.
# Since this file may contain answers to homework problems, you MAY NOT release it publicly.
#
#####################################################################
#
# Lab 6
# When you complete the lab, upload it to Canvas.
#
#####################################################################

import sys, os
sys.path.insert(0, os.path.abspath('..'))

from imslib.core import BaseWidget, run, lookup
from imslib.audio import Audio
from imslib.mixer import Mixer
from imslib.wavegen import WaveGenerator
from imslib.wavesrc import WaveFile
from imslib.gfxutil import topleft_label, resize_topleft_label, CLabelRect

from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.core.window import Window


#
# In this lab, you will write code for scrolling object in time to the music.
#
# The song is "SuperShort.wav" (first 30 seconds of Stevie Wonder's Superstition)
# The data file "SuperShort_beats.txt" was created in Sonic Visualizer and has a time
# instance at every beat.
#
# The goal is to play the song while objects (beat-markers) fall down the screen and land
# on the nowbar at every beat. You can see a screenshot of what the final lab looks like here:
# ../data/SuperShort_screengrab.png
#
# There are a few classes of interest:
#   AudioController: class that plays a song and reports back the time in that song.
#   SongData: class that reads a data file containing time-instances
#   BeatDisplay(InstructionGroup): class that draws a single beat-marker.
#   GameDisplay(InstructionGroup): class that draws the nowbar, and creates and animates instances of BeatDisplay
#
# Part 1: Write the function AudioController.get_time() to return the current time of the song. When
#         you play/pause the song (using 'p'), you should see the time display behaving correctly.
#
# Part 2: Create the nowbar in GameDisplay using a kivy Line object (with width=3).
#         Make the nowbar sit 20% up from the bottom of the screen, centered, with 10% margins on
#         either side of the Window by using the constants nowbar_h and nowbar_w_margin (see below).
#         Bonus: make the nowbar resize automatically when GameDisplay.on_resize is called().
#
# Part 3: Write the function time_to_ypos(time). This converts a time value (in seconds) to a y-pixel value.
#         time_to_ypos(0) should return the nowbar position. The amount of time covered by
#         the entire vertical span of the screen is the constant time_span (currently set to 2.0).
#         You can test this function with the first 4 beat positions, assuming a window height
#         of 600 (PCs / older macs) or 1200 (newer macs).
#
#         GameDisplay should print this when you run lab6.py for Window.height == 600
#           time:0.718, y-pixel:336
#           time:1.342, y-pixel:523
#           time:1.963, y-pixel:709
#           time:2.577, y-pixel:893
#
#         GameDisplay should print this when you run lab6.py for Window.height == 1200
#           time:0.718, y-pixel:671
#           time:1.342, y-pixel:1045
#           time:1.963, y-pixel:1418
#           time:2.577, y-pixel:1786
#
# Part 4: Finish the function BeatDisplay.on_update(now_time) so as to continually place the
#         beats markers in the correct place on screen based on the beat-marker's time-value and the
#         current song time (now_time). Note that here, on_update() takes an absolute time argument, NOT
#         a delta-time as used in previous systems. Use the constant beat_marker_len to compute the
#         line's horizontal span. There is also no need for KFAnim here. You map directly from now_time
#         to screen position. When this works, you should play the song and see the beat markers flowing down.
#         Then, play around with the constants below to see how these affect the display.
#
# Part 5: Right now, all BeatDisplays are being drawn all the time, even though most are off-screen.
#         Optimize your code so that BeatDisplay is only drawn (ie, is added to canvas) when it is
#         actually visible on screen. This requires two steps: 1) BeatDisplay.on_update() should
#         return True if the BeatDisplay is visible, False otherwise. 2) When GameDisplay.on_update()
#         updates the BeatDisplays, use the return value to add or remove the BeatDisplay.
#         Hint: You can test if object 'obj' is in the instruction group's draw list with: obj in self.children
#
# Part 6 (optional): use CLabelRect to add a number (the beat-number) to appear next to the beat line.

# configuration parameters:
nowbar_h = 0.2        # height of nowbar from the bottom of screen (as proportion of window height)
nowbar_w_margin = 0.1 # margin on either side of the nowbar (as proportion of window width)
time_span = 2.0       # time (in seconds) that spans the full vertical height of the Window
beat_marker_len = 0.2 # horizontal length of beat marker (as a proportion of window width)


class MainWidget(BaseWidget):
    def __init__(self):
        super(MainWidget, self).__init__()

        song_base_name = '../data/SuperShort'

        self.song_data  = SongData(song_base_name)
        self.audio_ctrl = AudioController(song_base_name)
        self.display    = GameDisplay(self.song_data)

        self.canvas.add(self.display)

        self.info = topleft_label()
        self.add_widget(self.info)

    def on_key_down(self, keycode, modifiers):
        # play / pause toggle
        if keycode[1] == 'p':
            self.audio_ctrl.toggle()

    # handle changing displayed elements when window size changes
    def on_resize(self, win_size):
        resize_topleft_label(self.info)
        self.display.on_resize(win_size)

    def on_update(self):
        self.audio_ctrl.on_update()

        # Note that in this system, on_update() is called with the song's current time. It does
        # NOT use dt (delta time).
        now = self.audio_ctrl.get_time()  # time of song in seconds.
        self.display.on_update(now)

        self.info.text = 'p: pause/unpause song\n'
        self.info.text += f'song time: {now:.2f}\n'
        self.info.text += f'num objects: {self.display.get_num_object()}'



# Handles everything about Audio.
#   creates the main python Audio object
#   load song track
#   functions as the clock (returns song time elapsed)
class AudioController(object):
    def __init__(self, song_path):
        super(AudioController, self).__init__()
        self.audio = Audio(2)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)

        # song
        self.track = WaveGenerator(WaveFile(song_path + ".wav"))
        self.mixer.add(self.track)

        # start paused
        self.track.pause()

    # start / stop the song
    def toggle(self):
        self.track.play_toggle()
        
    # return current time (in seconds) of song
    def get_time(self):
        # TODO write this
        return self.track.frame / Audio.sample_rate

    # needed to update audio
    def on_update(self):
        self.audio.on_update()


# for parsing gem text file: return (time, lane) from a single line of text
def beat_from_line(line):
    time, beat = line.strip().split('\t')
    return (float(time), int(beat))

# Holds data beats
class SongData(object):
    def __init__(self, song_base):
        super(SongData, self).__init__()
        self.beats = []

        beats_file = song_base + '_beats.txt'
        lines = open(beats_file).readlines()
        self.beats = [beat_from_line(l) for l in lines]

    def get_beats(self):
        return self.beats


# convert a time value to a y-pixel value (where time==0 is on the nowbar)
def time_to_ypos(time):
    # TODO write this
    nowbar_y = Window.height * nowbar_h
    pixels_per_second = (Window.height - nowbar_y) / time_span
    y_pos = nowbar_y + time * pixels_per_second
    return y_pos


# Displays a single beat on the screen as a short horizontal line
class BeatDisplay(InstructionGroup):
    def __init__(self, time, beat_num):
        super(BeatDisplay, self).__init__()

        self.time = time  # the timestamp (in seconds) of this beat in the song (ie, when does this beat occur?)
        self.color = Color(hsv=(.1, .8, 1)) # color of this beat line
        self.line = Line(width = 3) # line object to be drawn / animated in on_update()

        self.add(self.color)
        self.add(self.line)

    # animate the line (position) based on current time. The value now_time is in seconds
    # and is an absolute time position (not a delta time)
    def on_update(self, now_time):
        pass
        # TODO calculate Line's points and set them.
        td = self.time - now_time
        y_pos = time_to_ypos(td)

        center_x = Window.width / 2
        half_len = Window.width * beat_marker_len / 2
        left_x = center_x - half_len
        right_x = center_x + half_len

        self.line.points = [left_x, y_pos, right_x, y_pos]

        return 0 <= y_pos <= Window.height

# Displays game elements: nowbar and beats:
class GameDisplay(InstructionGroup):
    def __init__(self, song_data):
        super(GameDisplay, self).__init__()
        self.beat_data = song_data.get_beats()

        self.beats = [BeatDisplay(*b) for b in self.beat_data]
        for b in self.beats:
            self.add(b)

        # TODO write code to draw the nowbar here (make it a white line)
        self.nowbar = Line(width = 3)
        self.nowbar_color = Color(1,1,1)
        self.add(self.nowbar_color)
        self.add(self.nowbar)

        # (Initial pos.)
        left_margin = Window.width * nowbar_w_margin
        right_margin = Window.width * (1 - nowbar_w_margin)
        nowbar_y = Window.height * nowbar_h
        self.nowbar.points = [left_margin, nowbar_y, right_margin, nowbar_y]
        
        # test: print first 4 beat locations:
        print('Window size is:', Window.size)
        for b in self.beat_data[:4]:
            t = b[0]
            y = time_to_ypos(t)
            print(f'time:{t:.3f}, y-pixel:{y:.0f}')

    # when the window size changes:
    def on_resize(self, win_size):
        left_margin = Window.width * nowbar_w_margin
        right_margin = Window.width * (1 - nowbar_w_margin)
        nowbar_y = Window.height * nowbar_h
        self.nowbar.points = [left_margin, nowbar_y, right_margin, nowbar_y]


    def get_num_object(self):
        return len(self.children)

    # call every frame to handle animation needs. The value now_time is in seconds
    # and is an absolute time position (not a delta time)
    def on_update(self, now_time):
        for b in self.beats:
            vis = b.on_update(now_time)

            if vis and b not in self.children:
                self.add(b)
            elif not vis and b in self.children:
                self.remove(b)
            
            # TODO write optimization code here
            


if __name__ == "__main__":
    run(MainWidget())
