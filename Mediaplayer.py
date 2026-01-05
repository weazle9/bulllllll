import sys
import csv
import datetime
from datetime import datetime
import datetime
import os
import subprocess
import vlc
import random
from pynput.keyboard import Key, Listener
from pynput import keyboard
from time import sleep
import time
import re
import threading
from evdev import ecodes
import tkinter as tk
from tkinter import simpledialog
import socket
import json


import faulthandler

faulthandler.enable(open("crashlog.txt", "w"))

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QMessageBox, QHBoxLayout, \
    QLabel, QSizePolicy, QDialog, QInputDialog, QDesktopWidget
from PyQt5.QtCore import Qt, pyqtSlot, QTimer, QMetaObject, Q_ARG
from PyQt5.QtGui import QPixmap

import commercial_scheduler
from evdev import InputDevice, ecodes
from PyQt5.QtCore import QSocketNotifier


class SelectionDialog(QDialog):
    def __init__(self, prompt, options, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selection")
        self.selected_option = None
        self.layout = QVBoxLayout(self)

        self.label = QLabel(prompt, self)
        self.layout.addWidget(self.label)

        self.button_layout = QHBoxLayout()
        for option in options:
            button = QPushButton(str(option), self)
            button.clicked.connect(lambda checked, opt=option: self.select_option(opt))
            self.button_layout.addWidget(button)
        self.layout.addLayout(self.button_layout)

    def select_option(self, option):
        self.selected_option = option
        self.accept()


def get_selection(prompt, options):
    dialog = SelectionDialog(prompt, options)
    if dialog.exec_() == QDialog.Accepted:
        return dialog.selected_option
    return None


@pyqtSlot(int)
def show_overlay(self, duration):
    # Create the overlay as a child of your main widget so it appears properly
    overlay = QWidget(self)
    overlay.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    overlay.setStyleSheet("background-color: black;")
    overlay.setGeometry(self.rect())
    overlay.show()
    # Close the overlay after the specified duration (in milliseconds)
    QTimer.singleShot(duration, overlay.close)


class CustomMediaPlayer(QWidget):
    weekday = datetime.datetime.now().weekday()

    def __init__(self):
        super().__init__()

        # VLC setup
        self.instance = vlc.Instance(
            '--fullscreen',
            '--no-video-title-show',
            '--vout=x11',
            '--intf',
            '--no-osd',
            #           '--no-hw-accel',
            '--avcodec-hw=none',
            '--no-drop-late-frames',
            '--no-skip-frames',
            '--width=640',
            '--height=480')

        # self.instance = vlc.Instance()
        self.schedule_choices = {}

        # VLS specific ALSA device
        # self.instance = vlc.Instance('--aout=alsa', '--alsa-audio-device=plughw:1,0')

        # Vlc wiht ALSA
        # self.instance = vlc.Instance('--aout=alsa')
        self.player = self.instance.media_player_new()

        # PyQt setup
        self.layout = QVBoxLayout(self)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play_pause)
        self.layout.addWidget(self.play_button)

        self.skip_button = QPushButton("Old Live TV")
        self.skip_button.clicked.connect(self.play_live_tv_now)
        self.layout.addWidget(self.skip_button)

        self.kodi_button = QPushButton("Make Schedule")
        self.kodi_button.clicked.connect(self.create_kodi_schedule2)
        self.layout.addWidget(self.kodi_button)

        self.kodi_button = QPushButton("'Live' Schedule")
        self.kodi_button.clicked.connect(self.create_kodi_schedule)
        self.layout.addWidget(self.kodi_button)

        self.custom_schedule_unwatched_movie = QPushButton("Movie")
        self.custom_schedule_unwatched_movie.clicked.connect(self.create_custom_schedule_movie)
        self.layout.addWidget(self.custom_schedule_unwatched_movie)

        # Add the custom schedule unwatched button
        self.custom_schedule_unwatched_button = QPushButton("Sci-Fi")
        self.custom_schedule_unwatched_button.clicked.connect(self.create_custom_schedule_ph)
        self.layout.addWidget(self.custom_schedule_unwatched_button)

        # Add the custom schedule unwatched button
        self.custom_schedule_ph_button = QPushButton("Comedy Central")
        self.custom_schedule_ph_button.clicked.connect(self.create_custom_schedule_unwatched)
        self.layout.addWidget(self.custom_schedule_ph_button)

        # Add the custom schedule unwatched button
        self.custom_schedule_anime_button = QPushButton("ANIME")
        self.custom_schedule_anime_button.clicked.connect(self.create_custom_schedule_anime)
        self.layout.addWidget(self.custom_schedule_anime_button)

        self.custom_schedule_t_button = QPushButton("Toonami")
        self.custom_schedule_t_button.clicked.connect(self.create_custom_schedule_t)
        self.layout.addWidget(self.custom_schedule_t_button)

        self.create_custom_schedule_mi_button = QPushButton("Miguzi")
        self.create_custom_schedule_mi_button.clicked.connect(self.create_custom_schedule_mi)
        self.layout.addWidget(self.create_custom_schedule_mi_button)

        self.create_custom_schedule_as_button = QPushButton("Adult Swim")
        self.create_custom_schedule_as_button.clicked.connect(self.create_custom_schedule_as)
        self.layout.addWidget(self.create_custom_schedule_as_button)

        self.create_custom_schedule_nn_button = QPushButton("Nick @ Nite")
        self.create_custom_schedule_nn_button.clicked.connect(self.create_custom_schedule_nn)
        self.layout.addWidget(self.create_custom_schedule_nn_button)

        self.create_custom_schedule_sves_button = QPushButton("SVES")
        self.create_custom_schedule_sves_button.clicked.connect(self.create_custom_schedule_sves)
        self.layout.addWidget(self.create_custom_schedule_sves_button)

        self.create_custom_schedule_wb_button = QPushButton("Kids WB")
        self.create_custom_schedule_wb_button.clicked.connect(self.create_custom_schedule_wb)
        self.layout.addWidget(self.create_custom_schedule_wb_button)

        self.create_custom_schedule_fox_button = QPushButton("Fox Saturday")
        self.create_custom_schedule_fox_button.clicked.connect(self.create_custom_schedule_fox)
        self.layout.addWidget(self.create_custom_schedule_fox_button)

        self.setLayout(self.layout)

        # Timer to check media state
        self.timer = QTimer(self)
        self.timer.setInterval(100)  # Milliseconds
        self.timer.timeout.connect(self.check_media_state)

        self.playlist_files = []
        self.playlist = []

        # Load media data and schedule
        self.load_media_data()
        self.gap_durations = self.load_gap_durations()

        self.schedule_window = None  # Initialize
        self.schedule_block_window = None  # Initialize

        self.is_block_schedule = False

        self.current_show = None
        self.current_episode = None
        self.next_show = None
        self.next_episode = None
        self.current_block = None
        self.next_block = None
        self.is_random_block = False  # Flag to indicate random block selection
        self.random_block_intro_added = False
        self.schedule_block = False
        self.is_no_wb = False
        self.manual_block = None
        self.setFocusPolicy(Qt.StrongFocus)

        # Scale popup to screen size
        self.scale_popup_to_screen()

        self.setupGlobalShortcuts()
        self.setWindowTitle("Mediaplayer")

        self.load_movie_slots("Movie Slots.csv")

        self.channels = {
            "FOX": "Fox.m3u",
            "THE WB": "WB.m3u",
            "Toon Disney": "ToonDisney.m3u",
            "Music": "Music.m3u",
            "PowerHour": "Powerhouse.m3u",
            "ABC": "ABC.m3u",
            "Nickelodeon": "NICK.m3u",
            "Miguzi": "Miguzi.m3u",
            "Toonami": "Toonami.m3u",
            "Disney": "Disney.m3u",
            "Sci-Fi": "SciFi.m3u",
            "Anime" : "Anime.m3u"
        }

        self.sves_on = False

        # Track elapsed time for each channel
        self.channel_elapsed_time = {channel: 0 for channel in self.channels}
        self.channel_start_time = None  # Timestamp when a channel starts playing
        self.current_channel = None  # Track the currently playing channel

        self.channel_list = list(self.channels.keys())
        self.current_channel_index = 0
        self.start_time = None  # Track when user starts watching
        self.channel_timers = {channel: 0 for channel in self.channels}  # Track elapsed time per channel
        self.current_channel = None
        self.vlc_process = None  # Store VLC process

        self.global_elapsed_time = 0  # ✅ Global timer for all channels

        # Set up global keyboard listener
        self.keyboard_device = InputDevice("/dev/input/by-id/usb-_AirMouse-event-kbd")
        self.notifier = QSocketNotifier(self.keyboard_device.fileno(), QSocketNotifier.Read)
        self.notifier.activated.connect(self.handle_key_event)

        self.overlay_pid = None
        self.mpv_process = None

    def play_live_tv_now(self):
        now = datetime.datetime.now()
        day_start = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if now < day_start:
            day_start -= datetime.timedelta(days=1)

        current_time = int((now - day_start).total_seconds())
        self.channel_elapsed_time = {ch: current_time for ch in self.channels}
        self.global_elapsed_time = current_time
        self.channel_start_time = time.time()

        # Start with PowerHour (or any other you want)
        # self.current_channel_index = self.channel_list.index("PowerHour")
        # self.switch_channel("PowerHour", force_reset=True)
        self.get_playlist_duration("PowerHour")
        self.export_all_playlists_to_csv()
        self.get_playlist_duration("Toonami")
        self.get_playlist_duration("Miguzi")
        self.get_playlist_duration("ABC")
        self.get_playlist_duration("THE WB")
        self.get_playlist_duration("FOX")
        self.get_playlist_duration("Nickelodeon")
        self.get_playlist_duration("Disney")
        self.get_playlist_duration("Toon Disney")
        self.get_playlist_duration("Anime")
        self.get_playlist_duration("Music")
        self.get_playlist_duration("Sci-Fi")
        self.play_vlc()

    def setupGlobalShortcuts(self):
        # Toggle play/pause with a global shortcut
        # keyboard.add_hotkey('space', self.toggle_pause_play)
        pass
        # Skip to the next media file with a global shortcut

    def create_button(self, text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        button.setStyleSheet("font-size: 18px;")
        return button

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_button_font_sizes()

    def adjust_button_font_sizes(self):
        for button in self.findChildren(QPushButton):
            button.setStyleSheet(f"font-size: {self.height() // 25}px;")

    def scale_popup_to_screen(self):
        desktop = QDesktopWidget()
        screen_rect = desktop.availableGeometry(self)
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()

        # Set the window size to 50% of the screen's width and height
        self.setFixedSize(int(screen_width * 0.5), int(screen_height * 0.75))

    def get_duration(self, prompt, min_duration=2, max_duration=12):
        duration, okPressed = QInputDialog.getInt(self, "Enter Duration", prompt, min_duration, min_duration,
                                                  max_duration)
        if okPressed:
            return duration
        else:
            return None

    def create_custom_schedule_movie(self):
        # --- INLINE POPUP ---
        msg = QMessageBox(self)
        msg.setWindowTitle("Select Movie Type")
        msg.setText("What kind of movie do you want to watch?")

        toonami = msg.addButton("Toonami", QMessageBox.AcceptRole)
        disney = msg.addButton("Disney ", QMessageBox.AcceptRole)
        foxx = msg.addButton("Fox ", QMessageBox.AcceptRole)
        scifi = msg.addButton("Sci-Fi ", QMessageBox.AcceptRole)
        nick = msg.addButton("Nick ", QMessageBox.AcceptRole)
        theater = msg.addButton("Cartoon Theater", QMessageBox.AcceptRole)
        cancel = msg.addButton("Cancel", QMessageBox.RejectRole)

        msg.exec_()

        # Cancel pressed
        if msg.clickedButton() == cancel:
            print("Movie selection cancelled.")
            return

        # Determine block + intro
        intro_block = None

        if msg.clickedButton() == toonami:
            block = "Toonami Movie"
            intro_block = "Toonami Intro"

        elif msg.clickedButton() == disney:
            block = "Disney Movie"
            intro_block = "Disney Movie Intro"

        elif msg.clickedButton() == scifi:
            block = "Sci-Fi Movie"

        elif msg.clickedButton() == foxx:
            block = "Fox Movie"

        elif msg.clickedButton() == nick:
            block = "Nick Movie"
            intro_block = None  # Nick Movie has no intro unless you want one

        elif msg.clickedButton() == theater:
            block = "Cartoon Theater"
            intro_block = "Cartoon Theater Intro"

        else:
            return

        # --- Add intro ONLY if defined ---
        if intro_block:
            self.playlist.append(("elephant", "Rock", intro_block))

        self.is_random_block = True
        self.selected_block = block

        # --- Pick a movie from CSV block list ---
        movies = self.get_shows_for_block(block)
        if not movies:
            print(f"No movies available for block: {block}")
            return

        selected_movie = random.choice(movies)

        # pick 1 episode/group
        episodes = self.get_random_episode(selected_movie)

        if episodes:
            for ep_group in episodes:  # flatten list-of-lists
                for ep in ep_group:
                    self.playlist.append((selected_movie, ep, block))

        # finalize playlist
        self.finalize_playlist()

        print(f"Movie Selected: {selected_movie} ({block})")

    def create_custom_schedule_ph(self):
        self.is_random_block = True
        self.selected_block = "Sci-Fi"

        if True:
            num_shows = 8
            cartoon_network_shows = self.get_shows_for_block("Sci-Fi")
            selected_shows = random.sample(cartoon_network_shows, min(len(cartoon_network_shows), num_shows))
            for show in selected_shows:
                episodes = self.get_next_unwatched_episode(show)
                if episodes:
                    for episode in episodes:
                        self.playlist.append((show, episode, "Sci-Fi"))
                cartoon_network_shows.remove(show)

            # Finalize the playlist
            self.finalize_playlist()
            print("Custom Schedule Created (Unwatched):")
            for show, episode, block in self.playlist:
                print(f"Show: {show}, Episode: {episode}")

    def create_custom_schedule_t(self):
        self.is_random_block = True
        self.selected_block = "Toonami"

        selected_movie = "elephant"  # Replace with your desired show name
        specific_episode = "Rock"  # Replace with your desired episode filename
        self.playlist.append((selected_movie, specific_episode, "Toonami Intro"))

        play_movie = QMessageBox.question(self, "Play Movie", "Do you want to play a Special?",
                                          QMessageBox.Yes | QMessageBox.No)
        if play_movie == QMessageBox.Yes:
            duration = get_selection("How long would you like to watch Toonami (hours)?", range(0, 3))

            # Step 1: Specify duration for Cartoon Network
            if duration:
                num_shows = duration * 2
                if num_shows == 0:
                    pass
                else:
                    cartoon_network_shows = self.get_shows_for_block("Toonami")

                    for _ in range(num_shows):
                        if cartoon_network_shows:  # Ensure there are still shows left to choose
                            show = random.choice(cartoon_network_shows)
                            cartoon_network_shows.remove(show)  # Remove the selected show from the list

                            episodes = self.get_next_unwatched_episode(show)
                            if episodes:
                                for episode in episodes:
                                    self.playlist.append((show, episode, "Toonami"))

            cartoon_theater_shows = self.get_shows_for_block("Toonami Movie")
            selected_movie = random.choice(cartoon_theater_shows)
            episodes = self.get_random_episode(selected_movie)

            if episodes:
                cartoon_network_shows = self.get_shows_for_block("Toonami")

                # flatten list-of-lists exactly like normal shows
                for ep_group in episodes:
                    for ep in ep_group:
                        self.playlist.append((selected_movie, ep, "Toonami Movie"))

            for _ in range(4):

                if cartoon_network_shows:  # Ensure there are still shows left to choose
                    show = random.choice(cartoon_network_shows)
                    cartoon_network_shows.remove(show)  # Remove the selected show from the list

                    episodes = self.get_next_unwatched_episode(show)
                    if episodes:
                        for episode in episodes:
                            self.playlist.append((show, episode, "Toonami"))


        else:
            duration = get_selection("How long would you like to watch Toonami (hours)?", range(2, 6))

            # Step 1: Specify duration for Cartoon Network
            if duration:
                num_shows = duration * 2
                cartoon_network_shows = self.get_shows_for_block("Toonami")

                for _ in range(num_shows):
                    if cartoon_network_shows:  # Ensure there are still shows left to choose
                        show = random.choice(cartoon_network_shows)
                        cartoon_network_shows.remove(show)  # Remove the selected show from the list

                        episodes = self.get_next_unwatched_episode(show)
                        if episodes:
                            for episode in episodes:
                                self.playlist.append((show, episode, "Toonami"))

        # Finalize the playlist
        self.finalize_playlist()
        print("Custom Schedule Created (Unwatched):")
        for show, episode, block in self.playlist:
            print(f"Show: {show}, Episode: {episode}")

    def create_custom_schedule_mi(self):
        self.is_random_block = True
        self.selected_block = "miguzi"

        selected_movie = "elephant"  # Replace with your desired show name
        specific_episode = "Rock"  # Replace with your desired episode filename
        self.playlist.append((selected_movie, specific_episode, "Miguzi Intro"))

        duration = get_selection("How long would you like to watch Miguzi (hours)?", range(2, 4))

        # Step 1: Specify duration for Cartoon Network
        if duration:
            num_shows = duration * 2
            cartoon_network_shows = self.get_shows_for_block("Miguzi")

            for _ in range(num_shows):
                if cartoon_network_shows:  # Ensure there are still shows left to choose
                    show = random.choice(cartoon_network_shows)
                    cartoon_network_shows.remove(show)  # Remove the selected show from the list

                    episodes = self.get_next_unwatched_episode(show)
                    if episodes:
                        for episode in episodes:
                            self.playlist.append((show, episode, "Miguzi"))

        # Finalize the playlist
        self.finalize_playlist()
        print("Custom Schedule Created (Unwatched):")
        for show, episode, block in self.playlist:
            print(f"Show: {show}, Episode: {episode}")

    def create_custom_schedule_fox(self):
        self.is_random_block = True
        self.selected_block = "Fox"
        duration = get_selection("How long would you like to watch Fox (hours)?", range(2, 5))

        # Step 1: Specify duration for Cartoon Network
        if duration:
            num_shows = duration * 2
            cartoon_network_shows = self.get_shows_for_block("Fox")

            for _ in range(num_shows):
                if cartoon_network_shows:  # Ensure there are still shows left to choose
                    show = random.choice(cartoon_network_shows)
                    cartoon_network_shows.remove(show)  # Remove the selected show from the list

                    episodes = self.get_next_unwatched_episode(show)
                    if episodes:
                        for episode in episodes:
                            self.playlist.append((show, episode, "Fox"))

        # Finalize the playlist
        self.finalize_playlist()
        print("Custom Schedule Created (Unwatched):")
        for show, episode, block in self.playlist:
            print(f"Show: {show}, Episode: {episode}")

    def create_custom_schedule_as(self):
        self.is_random_block = True
        self.selected_block = "Adult Swim"

        selected_movie = "elephant"  # Replace with your desired show name
        specific_episode = "Rock"  # Replace with your desired episode filename
        self.playlist.append((selected_movie, specific_episode, "Adult Swim Intro"))
        cartoon_network_shows = self.get_shows_for_block("Adult Swim")



        # Step 1: Specify duration for Cartoon Network

        num_shows = 3 * 2
        episodes = self.get_next_unwatched_episode("Ghost in the Shell")
        if episodes:
            # only take the first unwatched episode
            episode = episodes[0]
            self.playlist.append(("Ghost in the Shell", episode, "Adult Swim"))
            cartoon_network_shows.remove('Ghost in the Shell')
        else:
            print("[WARN] No unwatched episodes found for Ghost in the Shell")

        for _ in range(num_shows):
            if cartoon_network_shows:  # Ensure there are still shows left to choose
                show = random.choice(cartoon_network_shows)
                cartoon_network_shows.remove(show)  # Remove the selected show from the list

                episodes = self.get_next_unwatched_episode(show)
                if episodes:
                    for episode in episodes:
                        self.playlist.append((show, episode, "Adult Swim"))

        # Finalize the playlist
        self.finalize_playlist()
        print("Custom Schedule Created (Unwatched):")
        for show, episode, block in self.playlist:
            print(f"Show: {show}, Episode: {episode}")

    def create_custom_schedule_anime(self):
        self.is_random_block = True

        num_shows = 4

        anime_shows = self.get_shows_for_block("ANIME").copy()
        ova_shows = self.get_shows_for_block("OVA").copy()

        for _ in range(num_shows):
            # 10% chance to pick OVA for THIS slot only
            if random.random() < 0.15 and ova_shows:
                block = "OVA"
                source = ova_shows
            else:
                block = "ANIME"
                source = anime_shows

            if not source:
                continue  # nothing left in this block

            show = random.choice(source)
            source.remove(show)

            episodes = self.get_next_unwatched_episode(show)
            if episodes:
                for episode in episodes:
                    self.playlist.append((show, episode, block))

        self.finalize_playlist()

        print("Custom Schedule Created (Unwatched):")
        for show, episode, block in self.playlist:
            print(f"Show: {show}, Episode: {episode}, Block: {block}")

    def create_custom_schedule_nn(self):
        self.is_random_block = True
        self.selected_block = "Nick at Nite"

        num_shows = 4 * 2
        cartoon_network_shows = self.get_shows_for_block("Nick at Nite")

        for _ in range(num_shows):
            if cartoon_network_shows:  # Ensure there are still shows left to choose
                show = random.choice(cartoon_network_shows)
                cartoon_network_shows.remove(show)  # Remove the selected show from the list

                episodes = self.get_next_unwatched_episode(show)
                if episodes:
                    for episode in episodes:
                        self.playlist.append((show, episode, "Nick at Nite"))

        # Finalize the playlist
        self.finalize_playlist()
        print("Custom Schedule Created (Unwatched):")
        for show, episode, block in self.playlist:
            print(f"Show: {show}, Episode: {episode}")

    def create_custom_schedule_sves(self):

    #todo: carton theater
        self.is_random_block = True
        self.selected_block = "SVES"

        selected_movie = "elephant"  # Replace with your desired show name
        specific_episode = "rock"  # Replace with your desired episode filename
        self.playlist.append((selected_movie, specific_episode, "SVES Intro"))


        num_shows = 6 * 2
        cartoon_network_shows = self.get_shows_for_block("SVES")

        for _ in range(num_shows):
            if cartoon_network_shows:  # Ensure there are still shows left to choose
                show = random.choice(cartoon_network_shows)
                cartoon_network_shows.remove(show)  # Remove the selected show from the list

                episodes = self.get_next_unwatched_episode(show)
                if episodes:
                    for episode in episodes:
                        self.playlist.append((show, episode, "SVES"))

        # Finalize the playlist
        self.finalize_playlist()
        print("Custom Schedule Created (Unwatched):")
        for show, episode, block in self.playlist:
            print(f"Show: {show}, Episode: {episode}")

    def create_custom_schedule_wb(self):
        self.is_random_block = True
        self.selected_block = "Kids WB"

        selected_movie = "elephant"  # Replace with your desired show name
        specific_episode = "rock"  # Replace with your desired episode filename
        self.playlist.append((selected_movie, specific_episode, "Kids WB Intro"))


        num_shows = 6 * 2
        cartoon_network_shows = self.get_shows_for_block("Kids WB")
        selected_shows = random.sample(cartoon_network_shows, min(len(cartoon_network_shows), num_shows))
        for show in selected_shows:
            episodes = self.get_next_unwatched_episode(show)
            if episodes:
                for episode in episodes:
                    self.playlist.append((show, episode, "Kids WB"))
            cartoon_network_shows.remove(show)

        # Finalize the playlist
        self.finalize_playlist()
        print("Custom Schedule Created (Unwatched):")
        for show, episode, block in self.playlist:
            print(f"Show: {show}, Episode: {episode}")

    def create_custom_schedule_unwatched(self):
        self.is_random_block = True
        self.selected_block = "Comedy"

        if True:
            num_shows = 4
            cartoon_network_shows = self.get_shows_for_block("Comedy Central")
            selected_shows = random.sample(cartoon_network_shows, min(len(cartoon_network_shows), num_shows))
            for show in selected_shows:
                episodes = self.get_next_unwatched_episode(show)
                if episodes:
                    for episode in episodes:
                        self.playlist.append((show, episode, "Comedy Central"))
                cartoon_network_shows.remove(show)

            # Finalize the playlist
            self.finalize_playlist()
            print("Custom Schedule Created (Unwatched):")
            for show, episode, block in self.playlist:
                print(f"Show: {show}, Episode: {episode}")




    def save_single_channel_ffmpeg_playlist(self, filename):
        """
        Write absolute paths to the M3U file so downstream parsing finds exact keys.
        """
        import os
        playlist_path = os.path.join(os.getcwd(), filename)
        try:
            with open(playlist_path, "w", encoding="utf-8") as f:
                for file_path in (getattr(self, "playlist_files", []) or []):
                    if not file_path:
                        continue
                    abs_path = os.path.abspath(file_path.strip())
                    f.write(f"{abs_path}\n")
            print(f":) FFmpeg playlist saved as {playlist_path}")
        except Exception as e:
            print(f"[save_single_channel_ffmpeg_playlist] Error saving playlist {playlist_path}: {e}")

    def list_zero_duration_files(self, limit=100):
        """
        Debug helper — lists files that parsed to 0 seconds so you can inspect CSV rows.
        """
        zeroes = []
        for path, sec in (getattr(self, "file_path_durations", {}) or {}).items():
            if not sec or int(sec) == 0:
                zeroes.append(path)
                if len(zeroes) >= limit:
                    break
        if zeroes:
            print(f"[list_zero_duration_files] Found {len(zeroes)} zero-duration entries (sample up to {limit}):")
            for p in zeroes:
                print("  -", p)
        else:
            print("[list_zero_duration_files] No zero-duration file paths found.")

    def create_kodi_music(self, current_time):
        self.playlist = []
        num_episodes = 200  # Calculate the number of episodes
        for _ in range(num_episodes):
            egg = self.get_random_music('Music')  # Fetch a random episode
            if egg:
                # Ensure a proper tuple is added to the playlist
                self.playlist.append(("Music", egg, "Video"))
            else:
                print("No valid music episode found.")
        # Finalize the playlist
        self.finalize_playlist()
        # for show, episode, block in self.playlist:
        #     print(f"Show: {show}, Episode: {episode}")
        self.save_single_channel_ffmpeg_playlist("Music.m3u")

    def save_selected_shows(self, filename="selected_shows.txt"):
        with open(filename, "w", encoding="utf-8") as f:
            last_show = None

            for show, _, _ in self.playlist:
                if show != last_show:
                    f.write(f"{show}\n")
                    last_show = show

        print(f"Saved condensed show list to {filename}")

    def lookup_gap_seconds(self, show, ep):
        key = f"{show} - {ep}"
        return self.gap_durations.get(key, 0)

    def load_movie_slots(self, path="Movie Slots.csv"):
        import csv

        self.movie_slots = {}

        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return

        # first row = slot counts per column
        slot_headers = []
        for cell in rows[0]:
            try:
                slot_headers.append(float(cell))
            except (ValueError, TypeError):
                slot_headers.append(None)

        # remaining rows = movie titles
        for row in rows[1:]:
            for idx, title in enumerate(row):
                if not title:
                    continue
                slots = slot_headers[idx]
                if slots is None:
                    continue
                self.movie_slots[title.strip()] = slots

    def build_grid_for_block(self, block_name, start_h, end_h, log_file="picked_shows.log"):
        """
        Build a schedule for one block.
        - Normal shows: A/B/C parts are grouped into a single 30-minute slot.
        - Movie blocks: pick exactly one movie and fill the entire block.
        - Special case: "What a Cartoon Show" → pick 3 episodes, one slot.
        - Adult Swim 15m shows: always pair two short shows into one slot.
        - Shows picked only once per channel: first appearance = unwatched,
          later appearances = rerun episodes.
        Logs debug info to console and file.
        """
        import datetime, random, math

        current = start_h * 3600
        end = end_h * 3600
        slot_len = 1800

        block_slots = int((end_h - start_h) * 2)
        usable_slots = block_slots - self.partial_spill
        if usable_slots < 0:
            usable_slots = 0

        # spill is now consumed
        self.partial_spill = 0
        shows = self.get_shows_for_block(block_name)
        if not shows:
            print(f"[build_grid_for_block] No shows found for {block_name}")
            return []

        # is_movie = show in self.movie_slots
        # slots_needed = int(self.movie_slots.get(show, 1))


        schedule = []
        used_shows = set()
        movie_blocks = {"Cartoon Theater", "Toonami Movie", "Disney Movie", "Toon Disney Movie", "Fox Movie", "Sci-Fi Movie", "Nick Movie", "ABC Movie"}
        preschool_blocks = {"Playhouse Disney", "Nick Jr"}
        short_shows = {
            "Frisky Dingo", "Space Ghost","Sealab 2021","Superjail!","Moral Orel",
            "Metalocalypse","China IL","The Brak Show","Harvey Birdman, Attorney At Law","Aqua Teen Hunger Force",
        }
        hour_shows = {"Smallville","Charmed","Dawsons Creek","Felicity","7th Heaven",
"Gilmore Girls","MADtv","Andromeda","Farscape","Firefly","First Wave",
"Stargate Atlantis","Stargate SG-1","The 4400","Dark Angel","X-Files","Kyle XY","House"}

        MOVIE_FILLERS = {
            "Disney Movie": "Brandy and Mr Whiskers",
            "Toon Disney Movie": "Brandy and Mr Whiskers",
            "Cartoon Theater": "What a Cartoon Show",
            "Toonami Movie": "What a Cartoon Show",
            "Nick Movie": "Oh Yeah Cartoons"
        }
        remaining_shows = shows[:]  # pool without repeats

        with open(log_file, "a", encoding="utf-8") as log:
            log.write(f"\n=== Block {block_name} ({start_h}:00–{end_h}:00) ===\n")

            # --- Normal block handling ---
            # effective_end = end - (self.partial_spill * (slot_len // 2))
            # while current < effective_end:
            slots_used = 0
            while slots_used < usable_slots:

                # while current < end:
            # while (current - start_h * 3600) < allowed_slots * slot_len:
                if not remaining_shows:
                    break

                slot_start = str(datetime.timedelta(seconds=current))
                slot_end = str(datetime.timedelta(seconds=current + slot_len))

                show = random.choice(remaining_shows)
                remaining_shows.remove(show)

                is_movie = block_name in movie_blocks and show in self.movie_slots

                if is_movie:
                    slots_raw = float(self.movie_slots[show])  # e.g. 2.5, 3.5
                    slots_consumed = math.ceil(slots_raw)  # 3, 4

                    eps = self.get_next_unwatched_episode(show, max_count=1)
                    if not eps:
                        continue

                    ep = eps[0]
                    used_shows.add(show)
                    self.channel_first_runs.add(show)

                    schedule.append((show, ep, block_name))

                    log.write(
                        f"[{block_name}] MOVIE {show} uses {slots_raw} → {slots_consumed} slots\n"
                    )

                    # how many slots this block can hold
                    block_slots = int((end_h - start_h) * 2)

                    # spill into NEXT block
                    self.partial_spill = max(0, slots_consumed - block_slots)

                    # cosmetic filler ONLY (does NOT affect math)
                    if slots_raw % 1 != 0 and block_name in MOVIE_FILLERS and block_name != "Nick Movie":

                        filler_show = MOVIE_FILLERS[block_name]

                        if filler_show == "What a Cartoon Show":
                            eps_sets = self.get_random_episode(
                                filler_show,
                                count=1,
                                unwatched_only=True,
                            )
                            if eps_sets:
                                flat_eps = [ep for group in eps_sets for ep in group]
                                for ep in flat_eps:
                                    schedule.append((filler_show, ep, block_name))
                        else:
                            eps2 = self.get_next_unwatched_episode(filler_show, max_count=1)
                            if eps2:
                                schedule.append((filler_show, eps2[0], block_name))

                    return schedule

                # --- Special case: House (1 hour episodes, 4 in a row = 8 slots) ---
                if block_name == "House":
                    eps_sets = self.get_next_unwatched_episode(show, max_count=4)
                    if not eps_sets:
                        msg = f"[{block_name}] No episodes for {show}, skipping slot {slot_start}-{slot_end}\n"
                        print(msg.strip());
                        log.write(msg)
                        slots_used += 1
                        continue

                    used_shows.add(show)
                    self.channel_first_runs.add(show)

                    for ep in eps_sets:
                        schedule.append((show, ep, block_name))
                        msg = f"[{block_name}] SPECIAL (House 1h) Slot {slot_start}-{slot_end}: {show} {ep}\n"
                        print(msg.strip());
                        log.write(msg)
                        # advance by 2 slots (1 hour)
                        current += slot_len * 2
                        slot_start = str(datetime.timedelta(seconds=current))
                        slot_end = str(datetime.timedelta(seconds=current + slot_len))
                    continue

                # --- Special case: Whose Line (6 × 30 min = 3 hours) ---
                if block_name == "Whos Line":
                    eps_sets = self.get_next_unwatched_episode(show, max_count=6)
                    if not eps_sets:
                        msg = f"[{block_name}] No episodes for {show}, skipping slot {slot_start}-{slot_end}\n"
                        print(msg.strip());
                        log.write(msg)
                        slots_used += 1
                        continue

                    used_shows.add(show)
                    self.channel_first_runs.add(show)

                    for ep in eps_sets:
                        schedule.append((show, ep, block_name))
                        msg = f"[{block_name}] SPECIAL (Whose Line) Slot {slot_start}-{slot_end}: {show} {ep}\n"
                        print(msg.strip());
                        log.write(msg)
                        slots_used += 1
                        slot_start = str(datetime.timedelta(seconds=current))
                        slot_end = str(datetime.timedelta(seconds=current + slot_len))
                    continue

                # --- Special case: What a Cartoon Show ---
                if show in ["What a Cartoon Show", 'Mickey Mouse']:
                    eps_sets = self.get_random_episode(show, count=3, unwatched_only=True)
                    if not eps_sets:
                        msg = f"[{block_name}] No episodes for {show}, skipping slot {slot_start}-{slot_end}\n"
                        print(msg.strip());
                        log.write(msg)
                        slots_used += 1
                        continue

                    used_shows.add(show)
                    self.channel_first_runs.add(show)

                    flat_eps = [ep for group in eps_sets for ep in group]
                    for ep in flat_eps:
                        schedule.append((show, ep, block_name))
                        msg = f"[{block_name}] SPECIAL Slot {slot_start}-{slot_end}: {show} {ep}\n"
                        print(msg.strip());
                        log.write(msg)

                    slots_used += 1
                    continue

                # --- Special case: Brandy and Mr Whiskers ---
                if show in ["Brandy and Mr Whiskers",'theweek3nders']:
                    eps_sets = self.get_next_unwatched_episode(show, max_count=2)
                    if not eps_sets:
                        msg = f"[{block_name}] No episodes for {show}, skipping slot {slot_start}-{slot_end}\n"
                        print(msg.strip());
                        log.write(msg)
                        slots_used += 1
                        continue

                    used_shows.add(show)
                    self.channel_first_runs.add(show)

                    for ep in eps_sets:
                        schedule.append((show, ep, block_name))
                        msg = f"[{block_name}] SPECIAL (brandy) Slot {slot_start}-{slot_end}: {show} {ep}\n"
                        print(msg.strip());
                        log.write(msg)
                        slots_used += 1
                        slot_start = str(datetime.timedelta(seconds=current))
                        slot_end = str(datetime.timedelta(seconds=current + slot_len))
                    continue

                # --- Special case: Bob the bulder ---
                if show == 'Bob the Builder':
                    eps_sets = self.get_random_episode(show, count=2, unwatched_only=True)
                    if not eps_sets:
                        msg = f"[{block_name}] No episodes for {show}, skipping slot {slot_start}-{slot_end}\n"
                        print(msg.strip());
                        log.write(msg)
                        slots_used += 1
                        continue

                    used_shows.add(show)
                    self.channel_first_runs.add(show)

                    flat_eps = [ep for group in eps_sets for ep in group]
                    for ep in flat_eps:
                        schedule.append((show, ep, block_name))
                        msg = f"[{block_name}] SPECIAL Slot {slot_start}-{slot_end}: {show} {ep}\n"
                        print(msg.strip());
                        log.write(msg)

                    slots_used += 1
                    continue

                # --- Special case: Infomercial (fill entire block with random "Info" clips) ---
                if block_name == "Infomercial":
                    pool = set()  # optional, avoids repeating the exact same file in this block
                    while current < end:
                        slot_start = str(datetime.timedelta(seconds=current))
                        slot_end = str(datetime.timedelta(seconds=current + slot_len))

                        ep_name = self.get_random_music("Info")  # ✅ reuse your music randomizer
                        if not ep_name:
                            msg = f"[{block_name}] ⚠️ No Infomercial clips found.\n"
                            print(msg.strip())
                            log.write(msg)
                            slots_used += 1
                            continue

                        if ep_name in pool:  # skip duplicates inside same block
                            continue
                        pool.add(ep_name)

                        schedule.append(("Info", ep_name, "Infomercial"))
                        # msg = f"[{block_name}] INFO Slot {slot_start}-{slot_end}: Infomercial {ep_name}\n"
                        # print(msg.strip())
                        # log.write(msg)

                        slots_used += 1
                    continue

                # --- Normal first-run vs rerun handling ---
                if block_name in preschool_blocks:
                    eps = self.get_random_episode(show, count=1, unwatched_only=False)
                    run_type = "FIRST-RUN"
                else:
                    if show not in self.channel_first_runs:
                        eps = self.get_next_unwatched_episode(show, max_count=1)
                        if eps:
                            self.channel_first_runs.add(show)
                            run_type = "FIRST-RUN"
                        else:
                            eps = self.get_rerun_episode(show, max_count=1)
                            run_type = "RERUN"
                    else:
                        eps = self.get_rerun_episode(show, max_count=1)
                        run_type = "RERUN"

                if not eps:
                    msg = f"[{block_name}] No episodes for {show}, skipping slot {slot_start}-{slot_end}\n"
                    print(msg.strip());
                    log.write(msg)
                    slots_used += 1
                    continue

                used_shows.add(show)

                # --- Special case: 15-minute Adult Swim shows ---
                if block_name == "Adult Swim" and show in short_shows:
                    # pick a second short show
                    second_show = random.choice(list(short_shows - {show}))
                    if second_show not in self.channel_first_runs:
                        eps2 = self.get_next_unwatched_episode(second_show, max_count=1)
                        if eps2:
                            self.channel_first_runs.add(second_show)
                            run_type2 = "FIRST-RUN"
                        else:
                            eps2 = self.get_rerun_episode(second_show, max_count=1)
                            run_type2 = "RERUN"
                    else:
                        eps2 = self.get_rerun_episode(second_show, max_count=1)
                        run_type2 = "RERUN"

                    if eps2:
                        used_shows.add(second_show)

                        for ep in eps:
                            schedule.append((show, ep, block_name))
                            msg = f"[{block_name}] {run_type} (15m) Slot {slot_start}-{slot_end}: {show} {ep}\n"
                            print(msg.strip());
                            log.write(msg)
                        for ep in eps2:
                            schedule.append((second_show, ep, block_name))
                            msg = f"[{block_name}] {run_type2} (15m pair) Slot {slot_start}-{slot_end}: {second_show} {ep}\n"
                            print(msg.strip());
                            log.write(msg)

                        slots_used += 1
                        continue

                # --- Normal 30-min shows ---
                for ep in eps:
                    if isinstance(ep, list):  # 🔥 unwrap nested lists
                        for sub_ep in ep:
                            schedule.append((show, sub_ep, block_name))
                            msg = f"[{block_name}] {run_type} Slot {slot_start}-{slot_end}: {show} {sub_ep}\n"
                            print(msg.strip())
                            log.write(msg)
                    else:
                        schedule.append((show, ep, block_name))
                        msg = f"[{block_name}] {run_type} Slot {slot_start}-{slot_end}: {show} {ep}\n"
                        print(msg.strip())
                        log.write(msg)

                slots_used += 1

            # debug summary
            missing = set(shows) - used_shows
            if missing:
                msg = f"[DEBUG] Block {block_name}: {len(missing)} shows never added: {sorted(missing)}\n"
                print(msg.strip());
                log.write(msg)
            msg = f"[DEBUG] Block {block_name}: picked {len(used_shows)} / {len(shows)} shows\n"
            print(msg.strip());
            log.write(msg)

        return schedule

    def create_kodi_anime(self):
        import datetime, random
        self.partial_spill = 0
        self.movie_overrun_slots = 0

        self.playlist = []
        self.channel_first_runs = set()  # ✅ reset at the start of this channel
        day = datetime.datetime.today().weekday()  # 0=Mon .. 6=Sun

        if day:
            self.playlist.extend(self.build_grid_for_block("ANIME", 7, 23))

        self.finalize_playlist()
        self.save_selected_shows(filename="selected_anime.txt")
        self.save_single_channel_ffmpeg_playlist("Anime.m3u")

    def create_kodi_phh(self):
        import datetime, random
        self.movie_overrun_slots = 0
        self.partial_spill = 0
        self.playlist = []
        self.channel_first_runs = set()  # ✅ reset at the start of this channel
        day = datetime.datetime.today().weekday()  # 0=Mon .. 6=Sun
        end1 = random.choice([17, 18])

        if day < 4:
            self.playlist.extend(self.build_grid_for_block("PowerHour", 7, 15))
            self.playlist.extend(self.build_grid_for_block("Toonami", 15, end1))
            self.playlist.extend(self.build_grid_for_block("PowerHour", end1, 19))
            self.playlist.extend(self.build_grid_for_block("Adult Swim", 19, 23))

        elif day == 4:
            self.playlist.extend(self.build_grid_for_block("PowerHour", 7, 15))
            self.playlist.extend(self.build_grid_for_block("Toonami", 15, end1))
            self.playlist.extend(self.build_grid_for_block("PowerHour", end1, 19))
            self.playlist.extend(self.build_grid_for_block("Adult Swim", 19, 23))

        elif day == 5:  # Saturday
            mode = random.randint(1, 10)
            if mode == 5:
                self.playlist.extend(self.build_grid_for_block("PowerHour", 7, 14))
                self.playlist.extend(self.build_grid_for_block("Toonami", 14, 16))
                self.playlist.extend(self.build_grid_for_block("PowerHour", 16, 19))
                self.playlist.extend(self.build_grid_for_block("Cartoon Theater", 19, 23))
            else:
                self.playlist.extend(self.build_grid_for_block("PowerHour", 7, 17))
                self.playlist.extend(self.build_grid_for_block("Cartoon Theater", 17, 18))
                self.playlist.extend(self.build_grid_for_block("SVES", 18, 23))

        elif day == 6:  # Sunday
            self.playlist.extend(self.build_grid_for_block("PowerHour", 7, 10))
            self.playlist.extend(self.build_grid_for_block("Cartoon Theater", 10, 11))
            self.playlist.extend(self.build_grid_for_block("PowerHour", 11, 19))
            self.playlist.extend(self.build_grid_for_block("Adult Swim", 19, 23))

        # finalize + save
        self.finalize_playlist()
        self.save_selected_shows(filename="selected_phh.txt")
        self.save_single_channel_ffmpeg_playlist("Powerhouse.m3u")

    def create_kodi_toonamii(self):
        import datetime, random
        self.partial_spill = 0
        self.movie_overrun_slots = 0
        self.playlist = []
        self.channel_first_runs = set()  # ✅ reset at the start of this channel
        day = datetime.datetime.today().weekday()  # 0=Mon .. 6=Sun


        # if day == 1:
        if day == 2:
        # if day == 0:
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 7, 10))
            self.playlist.extend(self.build_grid_for_block("Cartoon Theater", 10, 11))
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 11, 15))
            self.playlist.extend(self.build_grid_for_block("Toonami", 15, 17))
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 17, 19))
            self.playlist.extend(self.build_grid_for_block("Adult Swim", 19, 23))
        elif 0 < day:
        # elif 0 < day < 4:
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 7, 15))
            self.playlist.extend(self.build_grid_for_block("Toonami", 15, 17))
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 17, 19))
            self.playlist.extend(self.build_grid_for_block("Adult Swim", 19, 23))
        elif day == 4:
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 7, 16))
            self.playlist.extend(self.build_grid_for_block("Toonami", 16, 17))
            self.playlist.extend(self.build_grid_for_block("Toonami Movie", 17, 19))
            self.playlist.extend(self.build_grid_for_block("Adult Swim", 19, 23))

        elif day == 5:  # Saturday
            mode = random.randint(1, 2)
            if mode == 1:
                self.playlist.extend(self.build_grid_for_block("Cartoon Network", 7, 16))
                self.playlist.extend(self.build_grid_for_block("Cartoon Theater", 16, 18))
                self.playlist.extend(self.build_grid_for_block("SVES", 18, 23))
            else:
                self.playlist.extend(self.build_grid_for_block("Cartoon Network", 7, 16))
                self.playlist.extend(self.build_grid_for_block("Toonami Movie", 16, 17))
                self.playlist.extend(self.build_grid_for_block("Toonami", 17, 23))

        elif day == 6:  # Sunday
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 7, 10))
            self.playlist.extend(self.build_grid_for_block("Cartoon Theater", 10, 11))
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 12, 19))
            self.playlist.extend(self.build_grid_for_block("Adult Swim", 19, 23))

        # finalize + save
        self.finalize_playlist()
        self.save_selected_shows(filename="selected_toonami.txt")
        self.save_single_channel_ffmpeg_playlist("Toonami.m3u")

    def create_kodi_miguzii(self):
        import datetime, random
        self.movie_overrun_slots = 0
        self.partial_spill = 0
        self.playlist = []
        self.channel_first_runs = set()  # ✅ reset at the start of this channel
        day = datetime.datetime.today().weekday()  # 0=Mon .. 6=Sun
        end1 = random.choice([17, 18])

        if day < 4 :
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 7, 15))
            self.playlist.extend(self.build_grid_for_block("Miguzi", 15, 17))
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 17, 19))
            self.playlist.extend(self.build_grid_for_block("Adult Swim", 19, 23))

        # elif day == 4:
        elif day == 4:
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 7, 15))
            self.playlist.extend(self.build_grid_for_block("Toonami", 15, 18))
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 18, 19))
            self.playlist.extend(self.build_grid_for_block("Cartoon Theater", 19, 20))
            self.playlist.extend(self.build_grid_for_block("Adult Swim", 20, 23))

        elif day == 5:  # Saturday
            mode = random.randint(1, 2)
            if mode == 1:
                self.playlist.extend(self.build_grid_for_block("Cartoon Network", 7, 14))
                self.playlist.extend(self.build_grid_for_block("Cartoon Theater", 14, 16))
                self.playlist.extend(self.build_grid_for_block("Miguzi", 16, 18))
                self.playlist.extend(self.build_grid_for_block("Toonami", 18, 23))
            else:
                self.playlist.extend(self.build_grid_for_block("Cartoon Network", 7, 16))
                self.playlist.extend(self.build_grid_for_block("Miguzi", 16, 18))
                self.playlist.extend(self.build_grid_for_block("Toonami Movie", 18, 19))
                self.playlist.extend(self.build_grid_for_block("Toonami", 19, 23))

        elif day == 6:  # Sunday
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 7, 10))
            self.playlist.extend(self.build_grid_for_block("Cartoon Theater", 10, 11))
            self.playlist.extend(self.build_grid_for_block("Cartoon Network", 12, 19))
            self.playlist.extend(self.build_grid_for_block("Adult Swim", 19, 23))

        # finalize + save
        self.finalize_playlist()
        self.save_selected_shows(filename="selected_miguzi.txt")
        self.save_single_channel_ffmpeg_playlist("Miguzi.m3u")

    def create_kodi_nickk(self):
        import datetime, random
        self.partial_spill = 0
        self.movie_overrun_slots = 0
        self.playlist = []
        self.channel_first_runs = set()
        day = datetime.datetime.today().weekday()  # 0=Mon .. 6=Sun

        if day <= 3:  # Mon–Thu
            self.playlist.extend(self.build_grid_for_block("NICK", 7, 9))
            self.playlist.extend(self.build_grid_for_block("Nick Jr", 9, 12))
            self.playlist.extend(self.build_grid_for_block("NICK", 12, 20))
            self.playlist.extend(self.build_grid_for_block("Nick at Nite", 20, 23))

        elif day == 4:  # Fri
            self.playlist.extend(self.build_grid_for_block("NICK", 7, 9))
            self.playlist.extend(self.build_grid_for_block("Nick Jr", 9, 12))
            self.playlist.extend(self.build_grid_for_block("NICK", 12, 19))
            self.playlist.extend(self.build_grid_for_block("Nick Movie", 19, 20))
            self.playlist.extend(self.build_grid_for_block("Nick at Nite", 20, 23))

        else:  # Sat–Sun
            self.playlist.extend(self.build_grid_for_block("NICK", 7, 13))
            self.playlist.extend(self.build_grid_for_block("Nick Movie", 13, 14))
            self.playlist.extend(self.build_grid_for_block("NICK", 14, 20))
            self.playlist.extend(self.build_grid_for_block("Nick at Nite", 20, 23))

        # finalize + save
        self.finalize_playlist()
        self.save_selected_shows(filename="selected_nick.txt")
        self.save_single_channel_ffmpeg_playlist("Nick.m3u")

    def create_kodi_disneyy(self):
        import datetime, random
        self.movie_overrun_slots = 0
        self.partial_spill = 0
        self.playlist = []
        self.channel_first_runs = set()  # ✅ reset at the start of this channel
        day = datetime.datetime.today().weekday()  # 0=Mon .. 6=Sun

        if day in range(4):
            self.playlist.extend(self.build_grid_for_block("Toon Disney", 7, 9))
            self.playlist.extend(self.build_grid_for_block("Playhouse Disney", 9, 12))
            self.playlist.extend(self.build_grid_for_block("Disney", 12, 20))
            self.playlist.extend(self.build_grid_for_block("Disney Movie", 20, 21))
            self.playlist.extend(self.build_grid_for_block("Disney", 21, 23))
        else:  # Saturday
            self.playlist.extend(self.build_grid_for_block("Toon Disney", 7, 9))
            self.playlist.extend(self.build_grid_for_block("Disney Movie", 9, 10))
            self.playlist.extend(self.build_grid_for_block("Disney", 10, 18))
            self.playlist.extend(self.build_grid_for_block("Disney Movie", 18, 19))
            self.playlist.extend(self.build_grid_for_block("Disney", 19, 23))

        # finalize + save
        self.finalize_playlist()
        self.save_selected_shows(filename="selected_disney.txt")
        self.save_single_channel_ffmpeg_playlist("Disney.m3u")

    def create_kodi_toondisneyy(self):
        import datetime, random
        self.movie_overrun_slots = 0
        self.playlist = []
        self.partial_spill = 0
        self.channel_first_runs = set()  # ✅ reset at the start of this channel
        day = datetime.datetime.today().weekday()  # 0=Mon .. 6=Sun

        if day != 5:
            self.playlist.extend(self.build_grid_for_block("Toon Disney", 7, 15))
            self.playlist.extend(self.build_grid_for_block("Toon Disney Movie", 15, 16))
            self.playlist.extend(self.build_grid_for_block("Jetix", 16, 23))
        else:  # Saturday
            self.playlist.extend(self.build_grid_for_block("Jetix", 7, 11))
            self.playlist.extend(self.build_grid_for_block("Toon Disney Movie", 11, 12))
            self.playlist.extend(self.build_grid_for_block("Toon Disney", 13, 23))


        # finalize + save
        self.finalize_playlist()
        self.save_selected_shows(filename="selected_td.txt")
        self.save_single_channel_ffmpeg_playlist("ToonDisney.m3u")

    def create_kodi_wbb(self):
        print("[DEBUG] ENTER WB")

        import datetime, random
        self.partial_spill = 0
        self.movie_overrun_slots = 0

        self.playlist = []
        self.channel_first_runs = set()  # ✅ reset at the start of this channel
        day = datetime.datetime.today().weekday()  # 0=Mon .. 6=Sun

        if day < 5:
            # self.playlist.extend(self.build_grid_for_block("Infomercial", 7, 12))
            self.playlist.extend(self.build_grid_for_block("Xena", 12, 13))
            self.playlist.extend(self.build_grid_for_block("WB Day", 13, 15))
            self.playlist.extend(self.build_grid_for_block("Kids WB", 15, 17))
            self.playlist.extend(self.build_grid_for_block("WB Day", 17, 18))
            self.playlist.extend(self.build_grid_for_block("WB Prime", 18, 23))

        elif day == 5:
            self.playlist.extend(self.build_grid_for_block("Kids WB", 7, 12))
            self.playlist.extend(self.build_grid_for_block("Xena", 12, 13))
            self.playlist.extend(self.build_grid_for_block("WB Day", 13, 16))
            self.playlist.extend(self.build_grid_for_block("WB Prime", 16, 20))
            # self.playlist.extend(self.build_grid_for_block("Infomercial", 20, 23))

        else: # Saturday
            # self.playlist.extend(self.build_grid_for_block("Infomercial", 7, 14))
            self.playlist.extend(self.build_grid_for_block("Xena", 14, 15))
            self.playlist.extend(self.build_grid_for_block("WB Day", 15, 18))
            self.playlist.extend(self.build_grid_for_block("WB Prime", 18, 23))

        # finalize + save
        self.finalize_playlist()
        self.save_selected_shows(filename="selected_WB.txt")
        self.save_single_channel_ffmpeg_playlist("WB.m3u")

    def create_kodi_foxx(self):
        import datetime, random
        self.movie_overrun_slots = 0
        self.partial_spill = 0
        self.playlist = []
        self.channel_first_runs = set()  # ✅ reset at the start of this channel
        day = datetime.datetime.today().weekday()  # 0=Mon .. 6=Sun

        if day > 4:
            self.playlist.extend(self.build_grid_for_block("Fox", 7, 11))
            # self.playlist.extend(self.build_grid_for_block("Infomercial", 11, 14))
            self.playlist.extend(self.build_grid_for_block("House", 14, 18))
            self.playlist.extend(self.build_grid_for_block("Fox Prime", 18, 23))
        # elif day == 4:
        elif day == 2:
            self.playlist.extend(self.build_grid_for_block("Fox", 7, 11))
            # self.playlist.extend(self.build_grid_for_block("Infomercial", 11, 14))
            self.playlist.extend(self.build_grid_for_block("Fox Movie", 14, 16))
            self.playlist.extend(self.build_grid_for_block("Fox Prime", 16, 19))
            self.playlist.extend(self.build_grid_for_block("House", 19, 23))

        else:  # Saturday
            self.playlist.extend(self.build_grid_for_block("Fox", 7, 11))
            self.playlist.extend(self.build_grid_for_block("Fox Movie", 11, 13))
            self.playlist.extend(self.build_grid_for_block("Fox Prime", 13, 16))
            self.playlist.extend(self.build_grid_for_block("Fox Movie", 16, 18))
            self.playlist.extend(self.build_grid_for_block("Fox Prime", 18, 23))


        # finalize + save
        self.finalize_playlist()
        self.save_selected_shows(filename="selected_fox.txt")
        self.save_single_channel_ffmpeg_playlist("Fox.m3u")

    def create_kodi_abcc(self):
        import datetime, random
        self.movie_overrun_slots = 0
        self.partial_spill = 0

        self.playlist = []
        self.channel_first_runs = set()  # ✅ reset at the start of this channel
        day = datetime.datetime.today().weekday()  # 0=Mon .. 6=Sun

        if day < 4:
            self.playlist.extend(self.build_grid_for_block("ABC Jetix", 7, 12))
            self.playlist.extend(self.build_grid_for_block("ABC", 12, 16))
            self.playlist.extend(self.build_grid_for_block("ABC Prime", 16, 19))
            self.playlist.extend(self.build_grid_for_block("ABC Movie", 19, 20))
            self.playlist.extend(self.build_grid_for_block("Whos Line", 20, 23))

        elif day == 4:
            self.playlist.extend(self.build_grid_for_block("ABC Jetix", 7, 11))
            self.playlist.extend(self.build_grid_for_block("ABC Movie", 11, 12))
            self.playlist.extend(self.build_grid_for_block("ABC", 12, 16))
            self.playlist.extend(self.build_grid_for_block("ABC Prime", 16, 19))
            self.playlist.extend(self.build_grid_for_block("Kyle XY", 19, 20))
            self.playlist.extend(self.build_grid_for_block("Whos Line", 20, 23))

        else:
            self.playlist.extend(self.build_grid_for_block("ABC Jetix", 7, 11))
            self.playlist.extend(self.build_grid_for_block("ABC Prime", 11, 12))
            self.playlist.extend(self.build_grid_for_block("ABC", 12, 14))
            self.playlist.extend(self.build_grid_for_block("ABC Movie", 14, 15))
            self.playlist.extend(self.build_grid_for_block("ABC Movie", 16, 17))
            self.playlist.extend(self.build_grid_for_block("ABC Movie", 18, 19))
            self.playlist.extend(self.build_grid_for_block("ABC Prime", 20, 22))
            self.playlist.extend(self.build_grid_for_block("Whos Line", 22, 23))

        # finalize + save
        self.finalize_playlist()
        self.save_selected_shows(filename="selected_abc.txt")
        self.save_single_channel_ffmpeg_playlist("ABC.m3u")
        print("[DEBUG] ABC returning normally")

    def create_kodi_scifii(self):
        import datetime, random
        self.partial_spill = 0
        self.movie_overrun_slots = 0
        self.playlist = []
        self.channel_first_runs = set()  # ✅ reset at the start of this channel
        day = datetime.datetime.today().weekday()  # 0=Mon .. 6=Sun

        if day < 5:
            # self.playlist.extend(self.build_grid_for_block("Infomercial", 7, 10))
            self.playlist.extend(self.build_grid_for_block("Sci-Fi Anime", 10, 14))
            self.playlist.extend(self.build_grid_for_block("Sci-Fi Movie", 14, 15))
            self.playlist.extend(self.build_grid_for_block("Sci-Fi Anime", 15, 17))
            self.playlist.extend(self.build_grid_for_block("Sci-Fi", 17, 23))
        else:
            self.playlist.extend(self.build_grid_for_block("Sci-Fi", 7, 10))
            self.playlist.extend(self.build_grid_for_block("Sci-Fi Movie", 10, 12))
            self.playlist.extend(self.build_grid_for_block("Sci-Fi Anime", 12, 15))
            self.playlist.extend(self.build_grid_for_block("Sci-Fi Movie", 15, 17))
            self.playlist.extend(self.build_grid_for_block("Sci-Fi Anime", 17, 18))
            self.playlist.extend(self.build_grid_for_block("Sci-Fi", 18, 23))

        # finalize + save
        self.finalize_playlist()
        self.save_selected_shows(filename="selected_sci-fi.txt")
        self.save_single_channel_ffmpeg_playlist("SciFi.m3u")

    def create_kodi_schedule(self):
        import datetime, time, random

        now = datetime.datetime.now()
        day_start = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if now < day_start:
            day_start -= datetime.timedelta(days=1)

        # seconds since 07:00 today
        current_time = int((now - day_start).total_seconds())  # ← keep the old name

        self.channel_playlists = {
            "Anime": self.create_kodi_anime(),
            "PowerHour": self.create_kodi_phh(),
            "Miguzi": self.create_kodi_miguzii(),
            "Toonami": self.create_kodi_toonamii(),
            "Disney": self.create_kodi_disneyy(),
            "Toon Disney": self.create_kodi_toondisneyy(),
            "Fox": self.create_kodi_foxx(),
            "ABC": self.create_kodi_abcc(),
            # "The WB": self.create_kodi_wbb(),
            "Nick": self.create_kodi_nickk(),
            "Sci-Fi": self.create_kodi_scifii(),
            "Music": self.create_kodi_music(current_time),
        }

        # seed elapsed‑time tracking
        self.channel_elapsed_time = {ch: current_time for ch in self.channel_playlists}
        self.global_elapsed_time = current_time
        self.channel_start_time = time.time()

        #jump into the first channel
        first = "PowerHour"
        self.current_channel_index = self.channel_list.index(first)
        print(f"Live TV starting at real clock {now:%H:%M}, offset "
              f"{current_time // 3600}h{(current_time % 3600) // 60:02d}m.")
        self.switch_channel(first, force_reset=True)

    def create_kodi_schedule2(self):
        import datetime, time, random

        now = datetime.datetime.now()
        day_start = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if now < day_start:
            day_start -= datetime.timedelta(days=1)

        # seconds since 07:00 today
        current_time = int((now - day_start).total_seconds())  # ← keep the old name

        self.channel_playlists = {

            "PowerHour": self.create_kodi_phh(),
            "Miguzi": self.create_kodi_miguzii(),

            "Toonami": self.create_kodi_toonamii(),
            "Disney": self.create_kodi_disneyy(),
            "Toon Disney": self.create_kodi_toondisneyy(),
            "Fox": self.create_kodi_foxx(),
            "ABC": self.create_kodi_abcc(),
            # "The WB": self.create_kodi_wbb(),
            "Nick": self.create_kodi_nickk(),
            "Anime": self.create_kodi_anime(),
            "Sci-Fi": self.create_kodi_scifii(),
            "Music": self.create_kodi_music(current_time),

            # "Fox": self.create_kodi_fox(current_time),
            # "The WB": self.create_kodi_wb(current_time),
            # "PowerHour": self.create_kodi_ph(current_time),
            # "ABC": self.create_kodi_abc(current_time),
            # "Nick": self.create_kodi_nick(current_time),
            # "Miguzi": self.create_kodi_miguzi(current_time),
            # "Toonami": self.create_kodi_toonami(current_time),
            # "Disney": self.create_kodi_dis(current_time),
            # "Toon Disney": self.create_kodi_toondisney(current_time),
            # "Sci-Fi": self.create_kodi_scifi(current_time),
        }

        # seed elapsed‑time tracking
        self.channel_elapsed_time = {ch: current_time for ch in self.channel_playlists}
        self.global_elapsed_time = current_time
        self.channel_start_time = time.time()

        # jump into the first channel
        # first = "PowerHour"
        # self.current_channel_index = self.channel_list.index(first)
        # print(f"Live TV starting at real clock {now:%H:%M}, offset "
        #       f"{current_time // 3600}h{(current_time % 3600) // 60:02d}m.")
        # self.switch_channel(first, force_reset=True)

    def parse_m3u(self, playlist_file):
        """Reads the M3U file, extracts full paths, and retrieves durations from loaded media data."""
        try:
            with open(playlist_file, "r", encoding="utf-8") as file:
                lines = file.readlines()

            videos = []
            durations = []  # Stores durations for each video
            cumulative_durations = []  # Running total durations
            total_duration = 0  # Total playlist duration

            for line in lines:
                line = line.strip()
                if not line.startswith("#"):
                    full_path = os.path.abspath(line)  # Convert to absolute path
                    videos.append(full_path)

                    # 🔍 Get duration from `file_path_durations`
                    video_duration = self.file_path_durations.get(full_path, 0)
                    durations.append(video_duration)

                    # Compute cumulative durations
                    total_duration += video_duration
                    cumulative_durations.append(total_duration)

            return videos, durations, cumulative_durations, total_duration

        except FileNotFoundError:
            print(f"Playlist {playlist_file} not found.")
            return [], [], [], 0

    def print_m3u_timing(self, playlist_path, slot_len=1800, star_threshold=30, try_ffprobe=False):
        """
        Inspect an M3U and print per-file start times, durations and drift vs half-hour marks.
        - slot_len: slot length in seconds (default 1800 = 30 minutes)
        - star_threshold: seconds tolerance to consider a file aligned to a half-hour boundary
        - try_ffprobe: if True, will call ffprobe on local files when duration is missing
        Usage: self.print_m3u_timing("Powerhouse.m3u")
        """
        import os, re, subprocess, datetime

        def fmt_ts(s):
            return str(datetime.timedelta(seconds=int(round(s))))

        def human_delta(s):
            s = int(round(abs(s)))
            if s >= 3600:
                h = s // 3600
                m = (s % 3600) // 60
                sec = s % 60
                return f"{h}h{m:02d}m{sec:02d}s"
            if s >= 60:
                m = s // 60
                sec = s % 60
                return f"{m}m{sec:02d}s"
            return f"{s}s"

        def ffprobe_duration(path):
            try:
                out = subprocess.check_output([
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", path
                ], stderr=subprocess.STDOUT).decode().strip()
                return float(out) if out else None
            except Exception:
                return None

        # 1) read m3u and collect entries with optional #EXTINF before file
        entries = []
        playlist_dir = os.path.dirname(os.path.abspath(playlist_path))
        try:
            with open(playlist_path, "r", encoding="utf-8", errors="replace") as fh:
                last_ext = None
                for raw in fh:
                    line = raw.strip()
                    if not line:
                        continue
                    if line.startswith("#EXTINF"):
                        m = re.match(r"#EXTINF:([-+]?\d+)", line)
                        last_ext = int(m.group(1)) if m else None
                        continue
                    if line.startswith("#"):
                        continue
                    entries.append((line, last_ext))
                    last_ext = None
        except FileNotFoundError:
            print(f"[ERROR] playlist not found: {playlist_path}")
            return

        # 2) cache lookup helpers
        cache = getattr(self, "file_path_durations", {}) or {}
        # normalize cache keys once for faster matching
        norm_cache = {}
        for k, v in cache.items():
            try:
                key = os.path.normpath(os.path.abspath(str(k)))
            except Exception:
                key = os.path.normpath(str(k))
            try:
                norm_cache[key] = float(v)
            except Exception:
                try:
                    norm_cache[key] = float(str(v).strip())
                except Exception:
                    norm_cache[key] = 0.0

        results = []
        missing = []

        # 3) resolve durations
        for raw_path, extlen in entries:
            orig = raw_path.strip()
            dur = None
            matched = None

            candidates = []
            try:
                candidates = [
                    os.path.normpath(os.path.abspath(orig)),
                    os.path.normpath(os.path.join(playlist_dir, orig)),
                    os.path.normpath(orig),
                ]
            except Exception:
                candidates = [orig, os.path.join(playlist_dir, orig)]

            # try exact normalized keys
            for cand in candidates:
                if cand in norm_cache:
                    dur = norm_cache[cand]
                    matched = cand
                    break

            # basename match
            if dur is None:
                bn = os.path.basename(orig)
                for k, v in norm_cache.items():
                    if os.path.basename(k) == bn:
                        dur = v
                        matched = k
                        break

            # substring match (path contained or vice versa)
            if dur is None:
                for k, v in norm_cache.items():
                    if orig in k or k in orig or os.path.basename(orig) in k:
                        dur = v
                        matched = k
                        break

            # extinf fallback
            if dur is None and extlen and extlen > 0:
                dur = float(extlen)
                matched = "#EXTINF"

            # ffprobe fallback
            if dur is None and try_ffprobe:
                probepath = None
                for cand in candidates:
                    if os.path.exists(cand):
                        probepath = cand
                        break
                if probepath:
                    d = ffprobe_duration(probepath)
                    if d:
                        dur = float(d)
                        matched = f"ffprobe:{probepath}"

            if dur is None:
                dur = 0.0
                missing.append(orig)

            results.append({"orig": orig, "duration": float(dur), "matched": matched})

        # 4) print summary and per-entry with star + OVER/UNDER
        total = sum(r["duration"] for r in results)
        print(f"\nPlaylist: {playlist_path}")
        print(f"Total Duration: {fmt_ts(total)} ({int(round(total))} seconds)")
        print("-" * 100)

        cum = 0.0
        for r in results:
            start = int(round(cum))
            dur = r["duration"]
            basename = os.path.basename(r["orig"])
            # compute remainder relative to slot_len
            rem = start % slot_len
            # choose smaller distance to a boundary
            dist_to_lower = rem
            dist_to_upper = slot_len - rem
            star = ""
            drift_label = ""
            if dist_to_lower <= star_threshold or dist_to_upper <= star_threshold:
                # determine which boundary is the intended one
                if dist_to_lower <= dist_to_upper:
                    boundary = start - dist_to_lower
                    delta = start - boundary
                else:
                    boundary = start + dist_to_upper
                    delta = start - boundary
                star = "*"
                if delta > 0:
                    drift_label = f"OVER +{int(abs(delta))}s ({human_delta(delta)})"
                elif delta < 0:
                    drift_label = f"UNDER {int(abs(delta))}s ({human_delta(delta)})"
                else:
                    drift_label = "ON TIME"
            start_str = fmt_ts(start)
            dur_str = fmt_ts(dur)
            matched = r["matched"] or ""
            print(f"{star} {start_str:<10} | {basename:<55} | {dur_str:<10} {drift_label:<22}  (matched: {matched})")
            cum += dur

        print("-" * 100)
        print(f"End Time: {fmt_ts(cum)}")
        if missing:
            print(f"[MISSING DURATIONS] {len(missing)} entries lacked cached durations (showing up to 20):")
            for m in missing[:20]:
                print("  -", m)

    def export_all_playlists_to_csv(self, playlists=None, start_hour=7, slot_len=1800, star_threshold=30):
        """Safe version — no hangs, no crashes. Exports each .m3u playlist to its own CSV file."""
        import os, re, csv, datetime

        def fmt_ts(s):
            return str(datetime.timedelta(seconds=int(round(s))))

        def human_delta(s):
            s = int(round(abs(s)))
            if s >= 3600:
                h = s // 3600
                m = (s % 3600) // 60
                sec = s % 60
                return f"{h}h{m:02d}m{sec:02d}s"
            if s >= 60:
                m = s // 60
                sec = s % 60
                return f"{m}m{sec:02d}s"
            return f"{s}s"

        def is_show(path):
            p = os.path.normpath(os.path.abspath(path)).lower()
            return p.startswith("/media/weazle/seagate/sho") or p.startswith("/media/weazle/media/show")

        # --- build fast duration lookup safely ---
        cache = getattr(self, "file_path_durations", {}) or {}
        abs_cache, base_cache = {}, {}
        for k, v in cache.items():
            try:
                dur = float(v)
                norm = os.path.normpath(os.path.abspath(str(k))).lower()
                abs_cache[norm] = dur
                base_cache[os.path.basename(norm).lower()] = dur
            except Exception:
                continue  # skip malformed entries

        def safe_duration_lookup(path, playlist_dir, extlen):
            try:
                full = os.path.normpath(os.path.abspath(os.path.join(playlist_dir, path))).lower()
                if full in abs_cache:
                    return abs_cache[full]
                bn = os.path.basename(path).lower()
                if bn in base_cache:
                    return base_cache[bn]
                if extlen and extlen > 0:
                    return float(extlen)
            except Exception:
                pass
            return 0.0

        def parse_m3u(path):
            entries = []
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    last_ext = None
                    for raw in fh:
                        line = raw.strip()
                        if not line:
                            continue
                        if line.startswith("#EXTINF"):
                            m = re.match(r"#EXTINF:([-+]?\d+)", line)
                            last_ext = int(m.group(1)) if m else None
                            continue
                        if not line.startswith("#"):
                            entries.append((line, last_ext))
                            last_ext = None
            except FileNotFoundError:
                return []
            return entries

        # --- default playlists ---
        if not playlists:
            playlists = [
                "Powerhouse.m3u", "Toonami.m3u", "Miguzi.m3u", "ABC.m3u",
                "WB.m3u", "FOX.m3u", "NICK.m3u", "Music.m3u", "Sci-Fi.m3u",
                "Disney.m3u", "ToonDisney.m3u", "Anime.m3u"
            ]

        base_dir = os.getcwd()
        for plist in playlists:
            path = os.path.abspath(plist)
            entries = parse_m3u(path)
            if not entries:
                print(f"[WARN] Missing or empty playlist: {plist}")
                continue

            print(f"[INFO] Processing {plist} ({len(entries)} items)")
            playlist_dir = os.path.dirname(path)
            csv_name = os.path.splitext(os.path.basename(plist))[0] + "_timing.csv"
            csv_path = os.path.join(base_dir, csv_name)

            results = []
            cum = 0.0
            start_clock = datetime.datetime.combine(datetime.date.today(), datetime.time(hour=start_hour))

            for i, (raw_path, extlen) in enumerate(entries, start=1):
                dur = safe_duration_lookup(raw_path, playlist_dir, extlen)
                start = cum
                cum += dur
                clock = start_clock + datetime.timedelta(seconds=int(start))

                rem = start % slot_len
                dist_lower, dist_upper = rem, slot_len - rem
                star, drift = "", ""

                full = os.path.normpath(os.path.abspath(os.path.join(playlist_dir, raw_path)))
                show = is_show(full)
                if show:
                    if dist_lower <= star_threshold or dist_upper <= star_threshold:
                        if dist_lower <= dist_upper:
                            delta = -dist_lower
                        else:
                            delta = dist_upper
                        star = "*"
                        if delta > 0:
                            drift = f"OVER +{int(delta)}s ({human_delta(delta)})"
                        elif delta < 0:
                            drift = f"UNDER {abs(int(delta))}s ({human_delta(delta)})"
                        else:
                            drift = "ON TIME"

                results.append([
                    clock.strftime("%H:%M:%S"),
                    os.path.basename(raw_path).upper() if show else os.path.basename(raw_path),
                    fmt_ts(dur),
                    star,
                    drift
                ])

                if i % 50 == 0:
                    print(f"  {plist}: processed {i}/{len(entries)}")

            try:
                with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["Clock Time", "Filename", "Duration", "Mark", "Drift"])
                    writer.writerows(results)
                print(f"[OK] Exported {plist} → {csv_path} ({len(results)} rows)")
            except Exception as e:
                print(f"[ERROR] writing {csv_path}: {e}")

    def play_vlc(self, videos, start_index, start_offset):
        first = videos[start_index]
        rest = videos[start_index + 1:]

        cmd = [
            "mpv",
            "--fs",
            "--no-border",
            "--force-window=yes",
            "--no-shuffle",
            f"--start={int(start_offset)}",
            first,
            *rest
        ]

        self.mpv_process = subprocess.Popen(cmd)

    def play_first_segment(self, video, offset, on_done, channel_name):
        cmd = [
            "mpv",
            "--fs",
            "--no-border",
            "--force-window=yes",
            f"--start={int(offset)}",
            video,
        ]

        proc = subprocess.Popen(cmd)

        def watcher():
            # give mpv time to map + fullscreen
            time.sleep(0.3)

            # 🔑 NOW show overlay (mpv window exists)
            self.show_overlay_for_channel(channel_name, mode="switch")

            # extra insurance: re-raise again later
            threading.Timer(
                0.6,
                self._bring_overlay_to_front,
                kwargs=dict(overlay_title="TVOverlay")
            ).start()

            proc.wait()
            on_done()

        threading.Thread(target=watcher, daemon=True).start()

    def find_start_index(self, cumulative, elapsed):
        for i, t in enumerate(cumulative):
            if t > elapsed:
                prev = cumulative[i - 1] if i > 0 else 0
                return i, elapsed - prev
        return 0, 0

    def find_video_start_point(self, cumulative_durations, elapsed_time):
        total = cumulative_durations[-1]
        elapsed = elapsed_time % total

        for i, t in enumerate(cumulative_durations):
            if t > elapsed:
                prev = cumulative_durations[i - 1] if i > 0 else 0
                return i, elapsed - prev

        return 0, 0

    def switch_channel(self, new_channel, force_reset=False):
        # kill any existing mpv
        subprocess.run(["pkill", "-f", "mpv"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

        now_dt = datetime.datetime.now()
        schedule_start = now_dt.replace(hour=7, minute=0, second=0, microsecond=0)
        if now_dt < schedule_start:
            schedule_start -= datetime.timedelta(days=1)

        elapsed = (now_dt - schedule_start).total_seconds()
        if force_reset:
            elapsed = 0

        playlist_file = self.channels.get(new_channel)
        videos, _, cumulative, total = self.parse_m3u(playlist_file)
        if not videos:
            return

        elapsed %= total
        start_index, start_offset = self.find_video_start_point(cumulative, elapsed)

        first = videos[start_index]
        rest = videos[start_index + 1:]

        # IMPORTANT: mark current channel immediately
        self.current_channel = new_channel

        def continue_channel():
            if self.current_channel != new_channel:
                return

            cmd = [
                "mpv",
                "--fs",
                "--no-border",
                "--force-window=yes",
                "--no-shuffle",
                "--loop-playlist=inf",
                *rest
            ]

            proc = subprocess.Popen(cmd)

            def watcher():
                time.sleep(0.5)
                self.show_overlay_for_channel(new_channel, mode="continue")

            threading.Thread(target=watcher, daemon=True).start()

        self.play_first_segment(first, start_offset, continue_channel, new_channel)
        # self.show_overlay_for_channel(new_channel)

    def show_overlay_for_channel(self, channel_name, mode="switch"):
        now_dt = datetime.datetime.now()
        current_hour = now_dt.hour
        weekday = now_dt.strftime("%A")

        # Choose image based on channel and time
        if channel_name == 'Disney':
            if weekday in ["Saturday", "Sunday"]:
                image = "disney"
            elif 9 <= current_hour < 12:
                image = "phd1"
            else:
                image = "disney"

        elif channel_name == 'Toon Disney':
            if weekday != "Saturday":
                if current_hour >= 17:
                    image = random.choice(['jetix1', 'jetix2'])
                else:
                    image = random.choice(['td', 'td2'])
            else:
                if current_hour <= 11:
                    image = random.choice(['jetix1', 'jetix2'])
                else:
                    image = random.choice(['td', 'td2'])

        elif channel_name == 'FOX':
            if weekday != "Saturday":
                if current_hour <= 10:
                    image = random.choice(['foxbox', 'foxkids1', 'foxkids'])
                elif current_hour >= 14:
                    image = random.choice(['fox', 'fox2'])
            else:
                if current_hour <= 10:
                    image = random.choice(['foxbox', 'foxkids1', 'foxkids'])
                elif current_hour >= 14:
                    image = random.choice(['fox', 'fox2'])
                else:
                    image = "empty"

        elif channel_name == 'Toonami':
            if current_hour >= 19 and not self.sves_on:
                image = 'adultswim1'
            else:
                image = random.choice(['cn1', 'cn2'])

        elif channel_name == 'PowerHour':
            if current_hour >= 19:
                if weekday in ["Saturday", "Friday"]:
                    image = random.choice(['ph1', 'ph2', 'ph3', 'powerhour'])
                else:
                    image = 'adultswim1'
            else:
                image = random.choice(['ph1', 'ph2', 'ph3', 'powerhour'])

        elif channel_name == 'ABC':
            if current_hour <= 10:
                image = 'abcjetix'
            elif current_hour < 19:
                image = random.choice(['abc', 'abc1'])
            else:
                image = 'Empty'

        elif channel_name == 'Miguzi':
            if weekday in ['Monday','Tuesday','Wednesday','Thursday'] and 15 <= current_hour <= 17:
                image = "miguzi"
            elif weekday in ['Saturday'] and 16 <= current_hour <= 18:
                image = "miguzi"
            elif current_hour >= 19:
                if weekday in ["Saturday", "Friday"]:
                    image = random.choice(['cn1', 'cn2'])
                else:
                    image = 'adultswim1'
            else:
                image = random.choice(['cn1', 'cn2'])

        elif channel_name == 'Nickelodeon':
            if weekday in ["Saturday", "Sunday"]:
                if current_hour >= 20:
                    image = random.choice(['nickatnite', 'nn1', 'nn2', 'nn3', 'nn4'])
                else:
                    image = random.choice(['n', 'nick1', 'nick2', 'nick3', 'nick4', 'nick5', 'nick6', 'nick7'])
            elif weekday == "Friday":
                if current_hour >= 21:
                    image = random.choice(['nickatnite', 'nn1', 'nn2', 'nn3', 'nn4'])
                elif 9 <= current_hour < 12:
                    image = random.choice(['nj1', 'nj2', 'nj3', 'nj4'])
                else:
                    image = random.choice(['n', 'nick1', 'nick2', 'nick3', 'nick4', 'nick5', 'nick6', 'nick7'])
            else:
                if current_hour >= 19:
                    image = random.choice(['nickatnite', 'nn1', 'nn2', 'nn3', 'nn4'])
                elif 9 <= current_hour < 12:
                    image = random.choice(['nj1', 'nj2', 'nj3', 'nj4'])
                else:
                    image = random.choice(['n', 'nick1', 'nick2', 'nick3', 'nick4', 'nick5', 'nick6', 'nick7'])

        elif channel_name == 'THE WB':
            if weekday == "Saturday":
                if current_hour <= 11:
                    image = random.choice(['kidswb', 'kidswb2', 'kidswb3', 'kidswb4', 'kidswb5'])
                else:
                    image = random.choice(['wb', 'wb2', 'wb3', 'wb4'])
            elif weekday != "Sunday":
                if 16 <= current_hour <= 17:
                    image = random.choice(['kidswb', 'kidswb2', 'kidswb3', 'kidswb4', 'kidswb5'])
                else:
                    image = random.choice(['wb', 'wb2', 'wb3', 'wb4'])
            else:
                image = random.choice(['wb', 'wb2', 'wb3', 'wb4'])

        elif channel_name == 'Music':
            image = "mtv"

        elif channel_name == 'Sci-Fi':
            image = "scifi"

        else:
            image = "default"

        self.show_overlay(f"overlays/{image}.png", mode)

    def _bring_overlay_to_front(self, overlay_pid=None, overlay_title=None, tries=8, delay=0.12):
        """
        Raise/activate overlay window and mark it 'above'. Prefer PID; fallback to title.
        """
        for _ in range(tries):
            # Find overlay window id(s)
            wids = []
            try:
                if overlay_pid is not None:
                    out = subprocess.check_output(
                        ["xdotool", "search", "--pid", str(overlay_pid)],
                        stderr=subprocess.DEVNULL
                    )
                    wids = [w.decode() for w in out.split()]
                elif overlay_title:
                    out = subprocess.check_output(
                        ["xdotool", "search", "--name", overlay_title],
                        stderr=subprocess.DEVNULL
                    )
                    wids = [w.decode() for w in out.split()]
            except subprocess.CalledProcessError:
                pass

            # Apply raise/activate + 'above' on all found windows
            raised = False
            for wid in wids:
                try:
                    # Keep above and raise/activate
                    subprocess.run(["wmctrl", "-i", "-r", wid, "-b", "add,above,sticky,skip_taskbar,skip_pager"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                    subprocess.run(["xdotool", "windowraise", wid], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, check=False)
                    subprocess.run(["xdotool", "windowactivate", wid, "--sync"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                    raised = True
                except Exception:
                    pass

            if raised:
                return  # success
            time.sleep(delay)

    def _schedule_overlay_reraises(self, overlay_pid=None, overlay_title=None, mode="switch"):
        if mode == "switch":
            delays = [0.2, 0.5, 0.9, 1.4, 2.0]
        else:  # continuation
            delays = [0.4, 1.0, 1.8, 2.8, 4.0]

        for d in delays:
            threading.Timer(
                d,
                self._bring_overlay_to_front,
                kwargs=dict(
                    overlay_pid=overlay_pid,
                    overlay_title=overlay_title,
                    tries=3,
                    delay=0.08
                )
            ).start()

    def kill_existing_overlays(self):
        subprocess.run(
            ["xdotool", "search", "--name", "TVOverlay", "windowkill"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def show_overlay(self, image_path, mode="switch"):
        try:
            self.kill_existing_overlays()
            time.sleep(0.05)

            cmd = [
                "pqiv",
                "-T", "TVOverlay",
                "-i",
                "-f",
                "-c",
                "--transparent-background",
                image_path
            ]

            proc = subprocess.Popen(cmd)
            overlay_pid = proc.pid

            self._schedule_overlay_reraises(
                overlay_pid=overlay_pid,
                overlay_title="TVOverlay",
                mode=mode
            )

        except Exception as e:
            print(f"[Overlay] Error launching overlay: {e}")

    def close_overlay(self):
        if self.overlay_pid:
            subprocess.run(
                ["kill", "-9", str(self.overlay_pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.overlay_pid = None

    def play_next_video(self, videos, next_index, delay, session_id):
        start_time = time.time()
        extra_offset = 0.5  # ← Reduced from 1.95

        # Resolve the path for the next item (robust to different item shapes)
        def _resolve_path(item):
            # direct string path
            if isinstance(item, str):
                return item
            # dict-like: common keys
            if isinstance(item, dict):
                for k in ('path', 'file', 'filename', 'filepath'):
                    p = item.get(k)
                    if isinstance(p, str) and p:
                        return p
            # tuple/list: find the first string that looks like a path
            if isinstance(item, (list, tuple)):
                for v in item:
                    if isinstance(v, str) and v:
                        return v
            # fallback
            return str(item)

        # Guard next_index and compute next_path
        try:
            next_item = videos[next_index]
        except (IndexError, TypeError):
            print(
                f"[PLAY] Invalid next_index {next_index} for videos of size {len(videos) if hasattr(videos, '__len__') else 'unknown'}")
            return
        next_path = _resolve_path(next_item)

        # Wait until (delay + extra_offset), with session guard
        while time.time() - start_time < (delay + extra_offset):
            time.sleep(0.2)
            if session_id != self.current_session_id:
                return

        # Drift diagnostics
        now = time.time()
        actual_elapsed = now - start_time
        expected_elapsed = delay + extra_offset
        drift = actual_elapsed - expected_elapsed
        if abs(drift) > 1.0:
            print(f"[TIMING] Drift detected: {drift:.2f}s")

        # Update channel elapsed time
        self.channel_elapsed_time[self.current_channel] = self.global_elapsed_time + (now - self.channel_start_time)

        print(f"Auto-playing next video (index {next_index}) after {actual_elapsed:.2f} sec (drift: {drift:.2f}s)")

        # Start playback
        self.play_vlc(videos, next_index, 0)
        self.channel_start_time = time.time()

        # Always close any stale overlay first
        subprocess.run(["pkill", "pqiv"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        def delayed_overlay():
            time.sleep(1.0)  # small delay so VLC settles
            # Recommended: have this return PID of the overlay process
            overlay_pid = None
            try:
                overlay_pid = self.show_overlay_for_channel(self.current_channel)
            except TypeError:
                # Legacy signature: no PID returned; we’ll rely on title
                self.show_overlay_for_channel(self.current_channel)

            # Bring to front now + schedule a couple of re-raises
            self._bring_overlay_to_front(overlay_pid=overlay_pid, overlay_title="pqiv", tries=8, delay=0.12)
            self._schedule_overlay_reraises(overlay_pid=overlay_pid, overlay_title="pqiv")

        # Only show overlay if this next item isn’t a commercial (keep your existing logic if you already resolve next_path)
        threading.Thread(target=delayed_overlay, daemon=True).start()

    def next_channel(self):
        self.current_channel_index = (self.current_channel_index + 1) % len(self.channel_list)
        self.switch_channel(self.channel_list[self.current_channel_index])

    def previous_channel(self):
        self.current_channel_index = (self.current_channel_index - 1) % len(self.channel_list)
        self.switch_channel(self.channel_list[self.current_channel_index])

    def handle_key_event(self):
        for event in self.keyboard_device.read():
            if event.type == ecodes.EV_KEY and event.value == 1:  # Key press event
                if event.code == ecodes.KEY_PAGEDOWN:
                    self.previous_channel()
                elif event.code == ecodes.KEY_PAGEUP:
                    self.next_channel()
                elif event.code == ecodes.KEY_C:
                    subprocess.run([
                        "xdotool", "search", "--name", "VLC media player", "key", "c"
                    ])
                elif event.code == ecodes.KEY_A:
                    subprocess.run([
                        "xdotool", "search", "--name", "VLC media player", "key", "a"
                    ])

    def get_random_episode(self, show, count=1, unwatched_only=False):
        """
        Retrieve `count` random episodes for a given show from 'Episodes.csv'.
        - If unwatched_only=True, only pick episodes with Played='no'.
        - Each returned item may itself be a list (split episodes A/B/C).
        Always returns a list of lists (outer list = count, inner list = episode parts).
        """
        import random, csv

        try:
            episodes = []
            with open('Episodes.csv', newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['Show'] != show:
                        continue
                    if unwatched_only and row['Played'].strip().lower() != "no":
                        continue
                    ep_field = (row.get('Episode') or "").strip()
                    if ep_field:
                        split_eps = [ep.strip() for ep in ep_field.split(" / ") if ep.strip()]
                        episodes.append(split_eps)

            if not episodes:
                print(f"No episodes found for {show} (unwatched_only={unwatched_only}).")
                return []

            chosen_sets = random.sample(episodes, k=min(count, len(episodes)))
            return chosen_sets

        except Exception as e:
            print(f"Error reading Episodes.csv: {e}")
            return []

    def get_rerun_episode(self, show, max_count=1):
        """
        Retrieve up to `max_count` rerun episodes (Played != 'no') for a given show.
        - Splits on '/' so multi-part episodes are grouped.
        - Always returns a list (possibly empty).
        - If max_count=1 and the episode has slashes, expands them all.
        """
        try:
            episodes = []
            with open('Episodes.csv', newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['Show'] == show and row['Played'].strip().lower() != 'no':
                        ep_field = (row.get('Episode') or "").strip()
                        if ep_field:
                            split_eps = [ep.strip() for ep in ep_field.split(' / ') if ep.strip()]
                            if max_count == 1:
                                return split_eps  # expand full multi-part if single slot
                            else:
                                episodes.append(split_eps)
                    if len(episodes) >= max_count:
                        break

            # flatten and cap at max_count
            return [ep for group in episodes for ep in group][:max_count] or []

        except FileNotFoundError:
            print("⚠️ Episodes.csv not found.")
            return []
        except Exception as e:
            print(f"⚠️ Error reading Episodes.csv: {e}")
            return []

    def get_random_music(self, show):

        episodes = []
        try:
            with open('Episodes.csv', newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['Show'] == show:
                        episodes.append(row['Episode'])

            if episodes:
                chosen_episode = random.choice(episodes)
                # print(f"Chosen episode: {chosen_episode}")
                return chosen_episode
            else:
                print(f"No episodes found for {show}.")
                return None
        except Exception as e:
            print(f"Error reading file: {e}")
            return None

    def get_next_unwatched_episode(self, show, max_count=1):
        """
        Retrieve up to `max_count` next unwatched episodes for a given show from 'Episodes.csv'.
        If an episode contains '/', it's split and expanded accordingly.
        """
        try:
            episodes = []
            with open('Episodes.csv', newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['Show'] == show and row['Played'].lower() == 'no':
                        episodes_combined = row.get('Episode', '').strip()
                        if episodes_combined:
                            split_eps = [ep.strip() for ep in episodes_combined.split(' / ') if ep.strip()]
                            if max_count == 1:
                                # Automatically expand count if slashes are found
                                return split_eps
                            else:
                                episodes.append(split_eps)
                        if len(episodes) >= max_count:
                            break

            # Flatten and return up to `max_count` episode parts
            return [ep for group in episodes for ep in group][:max_count] or None

        except Exception as e:
            print(f"Error reading file: {e}")
            return None

    def toggle_play_pause(self):
        # Your existing method to toggle play/pause
        if self.player.is_playing():
            self.player.pause()
            self.play_button.setText("Play")
        else:
            if self.player.get_state() == vlc.State.Paused:
                self.player.play()
                self.play_button.setText("Pause")
            else:
                self.play_all()
                # self.play_media()

    def get_channel_block_for_show(self, show, episode):
        normalized_show = self.normalize_show_name(show)
        normalized_episode = self.normalize_episode_name(episode)
        key = (normalized_show, normalized_episode)
        # print(f"Current Show: {self.current_show}")
        # print(f"Next Show: {self.next_show}")
        # print(f"Looking up channel block for key: {key}")

        if key in self.media_data:
            channel_block = self.media_data[key]
        elif key[0] in self.media_data:
            channel_block = self.media_data[key]
        else:
            print(f"{key} Key  {key[0]}not found, using default 'General'. Check for normalization and loading issues.")
            channel_block = 'General'

        # print(f"Channel/Block for {key}: {channel_block}")
        return channel_block

    def calculate_total_break_duration(self, start_time, next_show_start, show_files):
        try:
            # First try parsing with the format that includes a colon
            start_time = datetime.strptime(start_time, '%I:%M%p')
            next_show_start = datetime.strptime(next_show_start, '%I:%M%p')
        except ValueError:
            # If there's a ValueError, try the format without a colon
            start_time = datetime.strptime(start_time, '%I%M%p')
            next_show_start = datetime.strptime(next_show_start, '%I%M%p')

        total_slot_duration = (next_show_start - start_time).total_seconds()
        total_show_duration = sum(self.get_show_duration(file) for file in show_files)

        return total_slot_duration - total_show_duration

    def get_show_duration(self, show_file):
        return int(self.media_data.get(show_file, {}).get('Duration', 0))

    def integrate_commercials_into_playlist(self, matched_media_files):
        updated_playlist = []
        block_intro_processed = {}

        # --- Preprocess: split episodes with slashes ---
        split_playlist = []
        for show, episode_str, block in self.playlist:
            episode_str = episode_str.strip()  # Clean overall string
            if "/" in episode_str:
                episodes = [e.strip() for e in episode_str.split("/") if e.strip()]
                for ep in episodes:
                    split_playlist.append((show.strip(), ep, block.strip()))
            else:
                split_playlist.append((show.strip(), episode_str, block.strip()))

        self.playlist = split_playlist
        for index, (show, episode, block) in enumerate(self.playlist):
            channel_block = block
            self.current_show, self.current_episode, self.current_block = show, episode, channel_block

            # Get all parts of the current episode
            current_parts = [key for key in self.playlist_files if key[0] == show and key[1].startswith(episode)]
            current_parts.sort(key=lambda x: x[1])  # Ensure correct part order

            # Determine next show/block
            if index + 1 < len(self.playlist):
                self.next_show, self.next_episode, self.next_block = self.playlist[index + 1]
            else:
                self.next_show, self.next_episode, self.next_block = None, None, None

            # Get total gap time for the full episode
            ep_key = f"{show} - {episode}".strip()
            total_gap = self.gap_durations.get(ep_key, 0)

            if total_gap == 0:
                total_gap = 160  # ✅ default gap
                warning = f"[WARN] Using default gap=160 for Show={show}, Episode={episode}"
                print(warning)
                try:
                    with open("gap_warnings.log", "a") as logf:
                        logf.write(warning + "\n")
                except Exception:
                    pass

            # Divide total gap across parts
            num_parts = len(current_parts)
            gap_per_part = total_gap // num_parts

            for part_index, part_key in enumerate(current_parts):
                part_show, part_episode = part_key

                # add episode part files
                updated_playlist.extend(self.playlist_files[part_key])

                # determine next show context
                if part_index + 1 < num_parts:
                    self.next_show = part_show
                    self.next_episode = current_parts[part_index + 1][1]
                    self.next_block = channel_block
                elif index + 1 < len(self.playlist):
                    self.next_show, self.next_episode, self.next_block = self.playlist[index + 1]
                else:
                    self.next_show = self.next_episode = self.next_block = None

                # add commercials
                part_commercials = commercial_scheduler.get_commercials_for_show(
                    channel_block,
                    gap_per_part,
                    index == 0 and part_index == 0,
                    current_show=part_show,
                    current_episode=part_episode,
                    current_block=channel_block,
                    next_show=self.next_show,
                    next_episode=self.next_episode,
                    next_block=self.next_block
                )

                updated_playlist.extend(part_commercials)

        self.playlist_files = [
            self._flatten_playlist_entry(e)
            for e in updated_playlist
        ]
    def _flatten_playlist_entry(self, entry):
        # commercials or media may come back as tuples
        if isinstance(entry, tuple):
            return entry[0]
        return entry

    def load_gap_durations(self):
        import csv, os
        gaps = {}

        def safe_int(v, default=0):
            try:
                if v is None:
                    return default
                v = str(v).strip()
                if v == "":
                    return default
                return int(float(v))
            except Exception:
                return default

        def load_file(path):
            if not os.path.exists(path):
                return {}
            result = {}
            with open(path, newline="", encoding="utf-8-sig", errors="replace") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    show = str(row.get("Show", "")).strip()
                    ep = str(row.get("Episode", "")).strip()
                    key = f"{show} - {ep}"
                    result[key] = safe_int(row.get("GapSeconds", 0), 0)
            return result

        # ✅ Load both files into one dictionary
        gaps.update(load_file("episodes_with_gaps.csv"))
        gaps.update(load_file("episodes_with_gaps_split.csv"))

        return gaps

    @staticmethod
    def parse_duration(value):
        """Robustly parse seconds from ints, floats, MM:SS, H:MM:SS, etc."""
        import re
        if value is None:
            return 0
        s = str(value).strip()
        if s == "":
            return 0

        # pure integer seconds
        if re.fullmatch(r"\d+", s):
            return int(s)

        # float seconds like 120.0
        if re.fullmatch(r"\d+\.\d+", s):
            try:
                return int(float(s))
            except Exception:
                return 0

        # time-like patterns H:MM:SS or MM:SS
        if ":" in s:
            parts = [p.strip() for p in s.split(":") if p.strip() != ""]
            try:
                if len(parts) == 3:
                    h, m, sec = parts
                    return int(h) * 3600 + int(m) * 60 + int(float(sec))
                elif len(parts) == 2:
                    m, sec = parts
                    return int(m) * 60 + int(float(sec))
                elif len(parts) == 1:
                    return int(float(parts[0]))
            except Exception:
                return 0

        # fallback: try float -> int
        try:
            return int(float(s))
        except Exception:
            return 0

    def load_media_data(self):
        """
        Load media_data.csv and commercials.csv robustly.
        Populates:
          - self.media_data[(show, filename)] = {'Channel/Block', 'Duration', 'File Path'}
          - self.video_durations[filename] = seconds
          - self.file_path_durations[abs_path] = seconds
        """
        import os, csv
        self.media_data = {}
        self.video_durations = {}
        self.file_path_durations = {}

        # --- media_data.csv ---
        try:
            with open('media_data.csv', newline='', encoding='utf-8', errors='ignore') as csvfile:
                reader = csv.DictReader(csvfile)
                count = 0
                for row in reader:
                    # skip empty rows
                    if not any((v or "").strip() for v in row.values()):
                        continue

                    show = (row.get('Show') or '').strip()
                    filename = (row.get('Filename') or '').strip()
                    full_path = (row.get('File Path') or '').strip()
                    raw_duration = (row.get('Duration') or '').strip()
                    channel_block = (row.get('Channel/Block') or '').strip()

                    dur_seconds = self.parse_duration(raw_duration)

                    if filename:
                        self.video_durations[filename] = dur_seconds

                    key = (show, filename)
                    self.media_data[key] = {
                        'Channel/Block': channel_block,
                        'Duration': dur_seconds,
                        'File Path': full_path or None
                    }

                    if full_path:
                        abs_path = os.path.abspath(full_path)
                        self.file_path_durations[abs_path] = dur_seconds

                    count += 1
            print(f"[load_media_data] Loaded media_data.csv rows: {count}")
        except FileNotFoundError:
            print("[load_media_data] media_data.csv not found.")
        except Exception as e:
            print(f"[load_media_data] Error reading media_data.csv: {e}")

        # --- commercials.csv ---
        try:
            with open('commercials.csv', newline='', encoding='utf-8', errors='ignore') as csvfile:
                reader = csv.DictReader(csvfile)
                comm_count = 0
                for row in reader:
                    if not any((v or "").strip() for v in row.values()):
                        continue
                    full_path = (row.get('File Path') or '').strip()
                    raw_duration = (row.get('Duration') or '').strip()
                    dur_seconds = self.parse_duration(raw_duration)

                    if full_path:
                        abs_path = os.path.abspath(full_path)
                        self.file_path_durations[abs_path] = dur_seconds
                        comm_count += 1
            print(f"[load_media_data] Loaded commercials.csv entries: {comm_count}")
        except FileNotFoundError:
            print("[load_media_data] commercials.csv not found. Skipping.")
        except Exception as e:
            print(f"[load_media_data] Error reading commercials.csv: {e}")

        # quick sanity summary
        try:
            total_files = len(self.file_path_durations)
            total_seconds = sum(self.file_path_durations.values())
            print(f"[load_media_data] file_path_durations: {total_files} files, total seconds={total_seconds}")
        except Exception:
            pass

    def match_schedule_with_media(self, schedule):
        if not self.media_data:
            print("Media data is not loaded.")
            return {}

        media_files = {}
        with open('media_data.csv', newline='', encoding='utf-8', errors='ignore') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                normalized_show = self.normalize_show_name(row['Show'])
                episode_base_name = self.normalize_episode_name(os.path.splitext(row['Filename'])[0])
                media_files.setdefault((normalized_show, episode_base_name), []).append(row['File Path'])

        playlist_files = {}
        for show, episode, block in schedule:  # Unpack block as well
            normalized_show = self.normalize_show_name(show)
            normalized_episode = self.normalize_episode_name(episode)

            # Directly check and add the first part (assuming it's always there without "- Part X" in the name)
            episode_key = (normalized_show, normalized_episode)
            if episode_key in media_files:
                playlist_files[episode_key] = media_files[episode_key]

            # Check for additional parts and add them as separate keys
            part_num = 2
            while True:
                part_key = (normalized_show, f"{normalized_episode} - Part {part_num}")
                if part_key in media_files:
                    # Instead of extending under the same key, create a new key for each part
                    playlist_files[part_key] = media_files[part_key]
                    # print(playlist_files[part_key])
                    # print( media_files[part_key])
                    part_num += 1
                else:
                    break
        # print(playlist_files)
        return playlist_files

    def finalize_playlist(self):
        self.save_selected_shows()

        # Use self.playlist directly
        self.playlist_files = self.match_schedule_with_media(self.playlist)
        # print(f"Playlist Files: {self.playlist_files}")  # Debugging
        try:
            self.integrate_commercials_into_playlist(self.playlist)
        except Exception as e:
            print(f"Error integrating commercials: {e}")
        print("Playlist prepared with episodes and commercials.")

    def find_media_file(self, show, episode):
        media_file = None
        try:
            with open('media_data.csv', newline='', encoding='utf-8', errors='ignore') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['Show'].strip().lower() == show.lower() and row[
                        'Episode'].strip().lower() == episode.lower():
                        media_file = row['Filename'].strip()
                        break
            if not media_file:
                print(f"No media file found for {show}, Episode {episode}")
            else:
                print(f"Media file found for {show}, Episode {episode}: {media_file}")
        except Exception as e:
            print(f"Error in find_media_file: {e}")
        return media_file

    def get_shows_for_block(self, block_name):
        shows = []
        try:
            with open('shows.csv', newline='', encoding='utf-8-sig', errors='ignore') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if block_name in row and row[block_name]:
                        shows.append(row[block_name])
            if shows:
                return shows
            else:
                print(f"No shows found for {block_name}.")
                return []
        except Exception as e:
            print(f"Error reading file: {e}")
            return []

        return shows

    def normalize_show_name(self, name):
        return name.replace(":", "").strip()

    def normalize_episode_name(self, name):
        return name.replace(";", " ").replace("?", "").strip()

    def write_m3u(self, path="temp_playlist.m3u"):
        with open(path, "w", encoding="utf-8") as f:
            for p in self.playlist_files:
                f.write(p + "\n")
        return path

    def play_media(self):
        if self.playlist_files:
            media_file = self.playlist_files.pop(0)
            self.player.set_media(self.instance.media_new(media_file))
            #  self.player.set_fullscreen(True)  # Set fullscreen mode
            #  self.player.video_set_aspect_ratio("4:3")
            # self.player.video_set_crop_geometry("4:3")
            # self.player.play()
            # self.timer.start()
            self.play_with_mpv(media_file)

    def play_all(self):
        if not self.playlist_files:
            return

        playlist_path = self.write_m3u()

        subprocess.Popen([
            "mpv",
            "--fs",
            "--no-border",
            "--geometry=100%x100%",
            "--keep-open=yes",
            "--force-window=yes",
            playlist_path
        ])

    def play_with_mpv(self, video_path):
        try:
            subprocess.run([
                "mpv",
                "--fs",
                "--no-border",
                "--geometry=100%x100%",
                video_path
            ])
        except Exception as e:
            print(f"error playing: {e}")

    def play_next_media(self):
        if self.playlist_files:
            media_file = self.playlist_files.pop(0)
            print(f"Playing next media: {media_file}")  # Debugging
            self.play_media()
        else:
            print("Playlist is empty.")

    def check_media_state(self):
        state = self.player.get_state()
        if state in [vlc.State.Ended, vlc.State.Error, vlc.State.Stopped]:
            self.timer.stop()
            self.play_media()

    def media_ended(self):
        print("Media ended, playing next")
        self.restart_player()  # Restart VLC player
        if self.playlist_files:
            if self.is_random_block:
                # Assuming the structure of the tuple is (current_show, current_episode)
                current_show, current_episode = self.current_show, self.current_episode
            self.play_next_media()
        else:
            print("Playlist finished")
            self.timer.stop()  # Stop the timer if the playlist is empty

    def skip_media(self):
        self.player.stop()  # Stop the current media
        self.media_ended()
        # self.play_next_media()  # Play the next media

    def restart_player(self):
        print("Restarting VLC Player to clear buffers...")
        self.player.stop()
        self.player.release()  # Release resources
        self.player = self.instance.media_player_new()  # Create a new player instance

    def view_playlist(self):
        if self.playlist_files:
            print("Upcoming Media:")
            for file in self.playlist_files:
                print(file)
        else:
            print("Playlist is empty.")

    def get_playlist_duration(self, channel_name):
        playlist_file = self.channels.get(channel_name)
        if not playlist_file:
            print(f"No playlist found for {channel_name}")
            return

        _, _, _, total_duration = self.parse_m3u(playlist_file)

        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)
        seconds = int(total_duration % 60)

        print(
            f"Total duration for {channel_name} is {hours}h {minutes}m {seconds}s ({total_duration:.2f} seconds)")


def on_key_press(key):
    try:
        if key == keyboard.Key.page_down:
            media_player.previous_channel()
        elif key == keyboard.Key.page_up:
            media_player.next_channel()
    except AttributeError:
        pass  # Ignore non-character keys


if __name__ == "__main__":
    app = QApplication(sys.argv)
    global media_player
    subprocess.Popen(["picom"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    media_player = CustomMediaPlayer()
    media_player.show()
    # media_player.secret_mpv()
    sys.exit(app.exec_())

