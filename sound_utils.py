from colorama import init, Fore
import subprocess
import os

def play_sound(success=True):
    """Play a .mp3 sound file for success or failure using macOS-safe afplay."""
    sound_file = "./success.mp3" if success else "fail.mp3"
    sound_path = os.path.join(os.path.dirname(__file__), sound_file)

    if os.path.exists(sound_path):
        try:
            subprocess.run(["afplay", sound_path])
        except Exception as e:
            print(Fore.YELLOW + f"Could not play sound: {e}" + Fore.RESET)
    else:
        print(Fore.YELLOW + f"Sound file not found: {sound_path}" + Fore.RESET)

