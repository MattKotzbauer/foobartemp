#####################################################################
#
# This software is to be used for MIT's class Interactive Music Systems only.
# Since this file may contain answers to homework problems, you MAY NOT release it publicly.
#
#####################################################################

import sys, os
sys.path.insert(0, os.path.abspath('..'))

from imslib.core import BaseWidget, run, lookup
from imslib.audio import Audio
from imslib.mixer import Mixer
from imslib.note import NoteGenerator
from imslib.wavegen import WaveGenerator
from imslib.wavesrc import WaveBuffer, WaveFile
from imslib.gfxutil import topleft_label, resize_topleft_label

from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.label import Label



class MainWidget(BaseWidget):
    def __init__(self):
        super(MainWidget, self).__init__()
        # (Killer Queen init.)
        song_base_path = './KillerQueen'
        gems_path = './improved_gems.txt'
        downbeats_path = './downbeats.txt'

        # (Game metadata init.)
        self.song_data = SongData(gems_path, downbeats_path)
        self.audio_ctrl = AudioController(song_base_path)
        self.game_display = GameDisplay(self.song_data, parent = self)
        self.canvas.add(self.game_display)
        self.player = Player(self.song_data, self.audio_ctrl, self.game_display)
        self.score_label = Label(
            text='Score: 0',
            pos_hint={'right': 0.98, 'top': 0.98},
            size_hint=(None, None),
            font_size='24sp',
            halign='right',
            color=(1, 1, 1, 1)
        )
        self.add_widget(self.score_label)
        
        self.info = topleft_label()
        self.add_widget(self.info)
        
    def on_key_down(self, keycode, modifiers):
        # play / pause toggle
        if keycode[1] == 'p':
            self.audio_ctrl.toggle()

        # button down
        button_idx = lookup(keycode[1], '12345', (0,1,2,3,4))
        if button_idx != None:
            lane = button_idx + 1
            self.game_display.on_button_down(lane)
            self.player.on_button_down(lane)
            print('down', button_idx)

    def on_key_up(self, keycode):
        # button up
        button_idx = lookup(keycode[1], '12345', (0,1,2,3,4))
        if button_idx != None:
            lane = button_idx + 1
            # (Trigger game display, player reactions)
            self.game_display.on_button_up(lane)
            self.player.on_button_up(lane)
            # print('up', button_idx) # (Debug print)
                        
    # handle changing displayed elements when window size changes
    # This function should call GameDisplay.on_resize
    def on_resize(self, win_size):
        # (Info pos.)
        resize_topleft_label(self.info)
        # (Game display update)
        self.game_display.on_resize(win_size)

        # (Score pos.)
        self.score_label.pos = (win_size[0] - 200, win_size[1] - 100)
        self.score_label.text_size = (200, None)

    def on_update(self):
        # (Audio control, player updates)
        self.audio_ctrl.on_update()
        now_time = self.audio_ctrl.get_time()
        self.player.on_update(now_time)

        # (Game metadata)
        self.game_display.on_update(now_time)
        self.info.text = 'Use p to play/pause\n'
        self.info.text += f'Time: {now_time:.2f}\n'
        self.info.text += f'Keys 1-5 to hit notes\n'
        # self.info.text += f'Score: {self.game_display.score}'


# Handles everything about Audio.
#   creates the main Audio object
#   load and plays solo and bg audio tracks
#   creates audio buffers for sound-fx (miss sound)
#   functions as the clock (returns song time elapsed)
class AudioController(object):
    def __init__(self, song_path):
        super(AudioController, self).__init__()
        # (Audio init.)
        self.audio = Audio(2)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)

        # (Background track)
        self.bg_track = WaveGenerator(WaveFile(song_path + "_bg.wav"))
        self.mixer.add(self.bg_track)

        # (Guitar solo)
        self.solo_track = WaveGenerator(WaveFile(song_path + "_solo.wav"))
        self.mixer.add(self.solo_track)

        # (Sq. wave denoting miss)
        # self.miss_sound = NoteGenerator(72, 0.3, 'square')

        # (Pause, unmute solo track by default)
        self.bg_track.pause()
        self.solo_track.pause()
        self.solo_muted = False
        self.solo_gain = 1.0
        
    # start / stop the song
    def toggle(self):
        # (Call wave generator toggles for both solo and bg)
        self.bg_track.play_toggle()
        self.solo_track.play_toggle()

    # mute / unmute the solo track
    def set_mute(self, mute):
        self.solo_muted = mute
        if mute:
            # (If we want to mute and have nonzero gain, set gain to 0)
            if not hasattr(self, 'solo_gain') or self.solo_track.get_gain() > 0:
                self.solo_gain = self.solo_track.get_gain()
                self.solo_track.set_gain(0)
        else:
            # (If we want to unmute, set gain to 1)
            curr_gain = self.solo_gain if hasattr(self, 'solo_gain') and self.solo_gain > 0 else 1.0
            self.solo_track.set_gain(curr_gain)
            
    # play a sound-fx (miss sound)
    def play_miss(self):
        # (Adds sq. wave to mixer and schedule to mute in .2sec)
        miss_sound = NoteGenerator(72, 0.3, 'square')
        self.mixer.add(miss_sound)
        Clock.schedule_once(lambda dt: miss_sound.note_off(), 0.2)

    # return current time (in seconds) of song
    def get_time(self):
        return self.bg_track.frame / float(Audio.sample_rate)

    # needed to update audio
    def on_update(self):
        self.audio.on_update()


# Holds data for gems and downbeats.
class SongData(object):
    def __init__(self, gems_filepath, downbeats_filepath):
        super(SongData, self).__init__()

        # (Populated from our Sonic Vis. annotations)
        self.gems = []
        self.downbeats = []

        self._parse_gems(gems_filepath)
        self._parse_downbeats(downbeats_filepath)
        
    def _parse_gems(self, filepath):
        # (Parse gem annotations from Sonic Vis.)
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    # (Index 0 is time)
                    time = float(parts[0])
                    # (Index 1 is lane)
                    lane = int(parts[1])
                    self.gems.append((time, lane))
    
    def _parse_downbeats(self, filepath):
        # (Parse downbeat annotations from Sonic Vis.)
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 1:
                    # (In this case, we only care about 0 index: time)
                    time = float(parts[0])
                    self.downbeats.append(time)

    def get_gems(self):
        return self.gems
    
    def get_downbeats(self):
        return self.downbeats
        
# Display for a single gem at a position with a hue or color
class GemDisplay(InstructionGroup):
    def __init__(self, lane, time, color):
        super(GemDisplay, self).__init__()

        self.lane = lane # (1-5)
        self.time = time
        self.state = 'normal' # (Can be 'normal', 'hit', or 'pass')

        # (Color, shape init.)
        self.color = Color(*color)
        self.add(self.color)
        self.gem = Ellipse(size=(30, 30))
        self.add(self.gem)

        # (Border init.)
        self.border_color = Color(1, 1, 1, 0.7)
        self.add(self.border_color)
        self.border = Line(width=2, circle=(0, 0, 15, 0, 360))
        self.add(self.border)

        # (Hit metadata)
        self.hit_effect = None
        self.hit_alpha = None
        self.hit_time = 0

        self.anim = None
        
    # change to display this gem being hit
    def on_hit(self):
        if self.state == 'normal':
            self.state = 'hit'

            # (Change to white)
            self.color.rgb = (1, 1, 1)
            if self.hit_effect is None:
                # (Edit alpha + border)
                self.hit_alpha = Color(1, 1, 1, 0.8)
                self.add(self.hit_alpha)
                self.hit_effect = Line(width=2, circle=(0, 0, 20, 0, 360))
                self.add(self.hit_effect)
            
            self.hit_time = 0
            
    # change to display a passed or missed gem
    def on_pass(self):
        if self.state == 'normal':
            self.state = 'pass'
            # (Grey out the gem and make more transparent)
            self.color.rgb = (0.5, 0.5, 0.5)
            self.border_color.a = 0.3

            
    # animate gem (position and animation) based on current time
    def on_update(self, now_time):
        # (Take y position as a differential from nowbar)
        time_diff = self.time - now_time
        window_height = Window.height
        seconds_on_screen = 2.0
        nowbar_pos_y = window_height * 0.2
        y_pos = nowbar_pos_y + (time_diff / seconds_on_screen) * (window_height - nowbar_pos_y)

        # (X pos. can be taken from window width / lanes)
        num_lanes = 5
        lane_width = Window.width / (num_lanes + 1)
        x_pos = self.lane * lane_width
        gem_size = self.gem.size
        self.gem.pos = (x_pos - gem_size[0]/2, y_pos - gem_size[1]/2)
        self.border.circle = (x_pos, y_pos, 15, 0, 360)

        # (Trigger anim if we haven't yet nullified hit_effect)
        if self.state == 'hit' and self.hit_effect is not None:
            self.hit_time += 1/60.0
            size = 15 + 30 * self.hit_time
            self.hit_alpha.a = max(0, 0.8 - self.hit_time * 2)
            self.hit_effect.circle = (x_pos, y_pos, size, 0, 360)

            # (Nullify hit effect if anim. has faded to 0)
            if self.hit_alpha.a <= 0:
                self.remove(self.hit_alpha)
                self.remove(self.hit_effect)
                self.hit_effect = None
                self.hit_alpha = None
        
        return 0 <= y_pos <= window_height

        
# Displays the location of a downbeat in the song
class DownbeatDisplay(InstructionGroup):
    def __init__(self, time):
        super(DownbeatDisplay, self).__init__()

        # (Kivy line init.)
        self.time = time
        self.color = Color(0.8, 0.8, 0.8)
        self.add(self.color)
        self.line = Line(width=1)
        self.add(self.line)
        
    # animate the position based on current time
    def on_update(self, now_time):
        # (Use time differential to take updated y pos.)
        time_diff = self.time - now_time
        window_height = Window.height
        window_width = Window.width
        seconds_on_screen = 2.0
        nowbar_pos_y = window_height * 0.2
        y_pos = nowbar_pos_y + (time_diff / seconds_on_screen) * (window_height - nowbar_pos_y)
        margin = window_width * 0.1
        # (Update points on line using updated y pos.)
        self.line.points = [margin, y_pos, window_width - margin, y_pos]
        return 0 <= y_pos <= window_height
        

# Displays one button on the nowbar
class ButtonDisplay(InstructionGroup):
    def __init__(self, lane, color):
        super(ButtonDisplay, self).__init__()

        # (Color, shape init.)
        self.lane = lane
        self.base_color = color
        self.pressed = False
        self.color = Color(*color)
        self.add(self.color)

        self.button = Ellipse()
        self.add(self.button)

        # (Weak white border init.)
        self.border_color = Color(1, 1, 1, 0.7)
        self.add(self.border_color)
        self.border = Line(width=2)
        self.add(self.border)

        self.on_resize((Window.width, Window.height))
        
    # displays when button is pressed down
    def on_down(self):
        self.pressed = True
        # (Bolden color and border)
        self.color.rgb = [min(1.0, c * 1.5) for c in self.base_color[:3]]
        self.border_color.a = 1.0
        self.on_resize((Window.width, Window.height))
        
    # back to normal state
    def on_up(self):
        self.pressed = False
        # (Return rgb, border to normal)
        self.color.rgb = self.base_color[:3]
        self.border_color.a = 0.7
        self.on_resize((Window.width, Window.height))
        
    # modify object positions based on new window size
    def on_resize(self, win_size):
        # (Fraction of lane size -> button radius)
        width, height = win_size
        num_lanes = 5
        lane_width = width / (num_lanes + 1)
        button_size = lane_width * 0.4

        nowbar_y = height * 0.2
        x_pos = self.lane * lane_width - button_size / 2
        y_pos = nowbar_y - button_size / 2

        # (If button is being pressed down, adjust the size accordingly)
        if self.pressed:
            button_size *= 1.1
            x_pos -= button_size * 0.05
            y_pos -= button_size * 0.05

        self.button.pos = (x_pos, y_pos)
        self.button.size = (button_size, button_size)

        # (Center within lane)
        center_x = x_pos + button_size / 2
        center_y = y_pos + button_size / 2
        radius = button_size / 2
        self.border.circle = (center_x, center_y, radius, 0, 360)

        
# Displays all game elements: nowbar, buttons, downbeats, gems
class GameDisplay(InstructionGroup):
    def __init__(self, song_data, parent = None):
        super(GameDisplay, self).__init__()

        # (Song data, colors init.)
        self.song_data = song_data
        self.parent = parent

        self.lane_colors = [
            (1, 0, 0), # (R)
            (0, 1, 0), # (G)
            (1, 1, 0), # (Y)
            (0, 0, 1), # (B)
            (1, 0, 1) # (P)
        ]

        # (Nowbar init.)
        self.nowbar_color = Color(1, 1, 1)
        self.add(self.nowbar_color)
        self.nowbar = Line(width=3)
        self.add(self.nowbar)

        # (Buttons init.)
        self.buttons = []
        for lane in range(1, 6):
            button = ButtonDisplay(lane, self.lane_colors[lane-1])
            self.add(button)
            self.buttons.append(button)

        # (Gems init.)
        self.gems = []
        for time, lane in song_data.get_gems():
            gem = GemDisplay(lane, time, self.lane_colors[lane-1])
            self.gems.append(gem)

        # (Downbeat bars init.)
        self.downbeats = []
        for time in song_data.get_downbeats():
            downbeat = DownbeatDisplay(time)
            self.downbeats.append(downbeat)

        self.score = 0

        self.on_resize((Window.width, Window.height))

            
    # called by Player when succeeded in hitting this gem.
    def gem_hit(self, gem_idx):
        if 0 <= gem_idx < len(self.gems):
            self.gems[gem_idx].on_hit()

    # called by Player on pass or miss.
    def gem_pass(self, gem_idx):
        if 0 <= gem_idx < len(self.gems):
            self.gems[gem_idx].on_pass()

    # called by Player on button down
    def on_button_down(self, lane):
        if 0 <= lane-1 < len(self.buttons):
            self.buttons[lane-1].on_down()

    # called by Player on button up
    def on_button_up(self, lane):
        if 0 <= lane-1 < len(self.buttons):
            self.buttons[lane-1].on_up()

    # called by Player to update score
    def set_score(self, score):
        self.score = score
        if hasattr(self.parent, 'score_label'):
            self.parent.score_label.text = f'Score: {score}'
        
    # for when the window size changes
    def on_resize(self, win_size):
        # (Adjust nowbar and buttons)
        width, height = win_size
        nowbar_y = height * 0.2
        margin = width * 0.1
        self.nowbar.points = [margin, nowbar_y, width - margin, nowbar_y]

        for button in self.buttons:
            button.on_resize(win_size)
        
    # call every frame to handle animation needs
    def on_update(self, now_time):
        seconds_ahead = 2.0
        seconds_behind = 0.5

        for i, gem in enumerate(self.gems):
            gem_time = gem.time

            # (If our gem should be spawned at the top, add it to our gems)
            if now_time - seconds_behind <= gem_time <= now_time + seconds_ahead:
                if gem not in self.children:
                    self.add(gem)

                visible = gem.on_update(now_time)

                if not visible and gem in self.children:
                    # (Conversely, if it's disappeared below the screen, remove it)
                    self.remove(gem)

            elif gem_time < now_time - seconds_behind and gem in self.children:
                self.remove(gem)


        for i, downbeat in enumerate(self.downbeats):
            # (Proceed identically for downbeats: if it should be spawned, do so)
            downbeat_time = downbeat.time
            
            if now_time - seconds_behind <= downbeat_time <= now_time + seconds_ahead:
                if downbeat not in self.children:
                    self.add(downbeat)
                
                visible = downbeat.on_update(now_time)
                
                if not visible and downbeat in self.children:
                    # (And if it should be removed, do so)
                    self.remove(downbeat)
            
            elif downbeat_time < now_time - seconds_behind and downbeat in self.children:
                self.remove(downbeat)
            

# Handles game logic and keeps track of score.
# Controls the GameDisplay and AudioCtrl based on what happens
class Player(object):
    def __init__(self, song_data, audio_ctrl, display):
        super(Player, self).__init__()
        # (Audio data + control init.)
        self.song_data = song_data
        self.audio_ctrl = audio_ctrl
        self.display = display

        # (Other metadata)
        self.slop_window = 0.1
        self.score = 0
        self.combo = 0

        self.gem_status = {} # (gem_idx -> status (None, 'hit', 'miss', 'pass'))
        for idx, _ in enumerate(self.song_data.get_gems()):
            self.gem_status[idx] = None

    # called by MainWidget
    def on_button_down(self, lane):
        now_time = self.audio_ctrl.get_time()
        valid_gems = []
        # (Attempt to strike gem)
        for idx, (time, gem_lane) in enumerate(self.song_data.get_gems()):
            if self.gem_status[idx] is None:
                if abs(time - now_time) < self.slop_window:
                    valid_gems.append((idx, gem_lane, abs(time - now_time)))

        # (If no gems are currently valid, miss by default)
        if not valid_gems:
            self.audio_ctrl.play_miss()
            self.audio_ctrl.set_mute(True)
            self.combo = 0
            return

        # (Dictate hit or miss based on closest lane)
        valid_gems.sort(key=lambda x: x[2])
        closest_idx, closest_lane, _ = valid_gems[0]

        if closest_lane == lane:
            # (Hit)
            self.gem_status[closest_idx] = 'hit'
            self.display.gem_hit(closest_idx)
            self.audio_ctrl.set_mute(False)

            self.combo += 1
            self.score += 100 * self.combo
            self.display.set_score(self.score)
        else:
            # (Miss)
            self.gem_status[closest_idx] = 'miss'
            self.display.gem_pass(closest_idx)
            self.audio_ctrl.play_miss()
            self.audio_ctrl.set_mute(True)
            self.combo = 0
                    
    # called by MainWidget
    def on_button_up(self, lane):
        self.display.on_button_up(lane)

    # needed to check for pass gems (ie, went past the slop window)
    def on_update(self, time):
        for idx, (gem_time, _) in enumerate(self.song_data.get_gems()):
            if self.gem_status[idx] is None and (time - gem_time) > self.slop_window:
                self.gem_status[idx] = 'pass'
                self.display.gem_pass(idx)
                self.audio_ctrl.set_mute(True)


if __name__ == "__main__":
    run(MainWidget())
