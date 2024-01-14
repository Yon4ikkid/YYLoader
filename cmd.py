import net_api
import pytube
import sys
import threading
import asyncio
from pathlib import Path

current_progress = 0
def progress_callback(progress):
    global current_progress
    dif = (progress - current_progress) / 100.0
    print('#'*int(dif/0.05), end='')
    current_progress = progress


def fetch_target(url: str) -> net_api.DownloadTarget:
    if 'playlist' in url:
        return net_api.PlaylistTarget(url, progress_callback)
    else:
        return net_api.VideoTarget(url, progress_callback)


def print_details(target: net_api.DownloadTarget):
    print("--------------")
    print("Target details:")
    print("[NAME] >> ", target.get_name())

    audio_options, video_options = target.get_available_streams()
    print("[AUDIO STREAMS]")
    for i, option in enumerate(audio_options, 1):
        print(f"\t[{i:0>2}] >> {option}")
    print("[VIDEO STREAMS]")
    for i, option in enumerate(video_options, 1):
        print(f"\t[{i:0>2}] >> {option}")
    print("--------------")
    return len(audio_options), len(video_options)


def print_error(prompt):
    print("[ERROR] >> ", prompt)


def input_string(prompt):
    return input(f"[{prompt}] << ")


def input_number(prompt, minv, maxv):
    while (True):
        try:
            v = int(input_string(prompt))
            if v > maxv or v < minv:
                raise ValueError
            return v
        except ValueError:
            print("[ERROR] >> Invalid option")


def main():
    print("==== YYLOADER ====")
    print("Enter target URL:")
    url = input_string('URL')
    print("Fetching target data...")
    
    try:
        target = fetch_target(url)
    except pytube.exceptions.PytubeError:
        print_error("Failed to fetch data.")
        return 1

    audio_count, video_count = print_details(target)

    print("Change stream preferences? (default is [1])")
    choice = input_string('Y/N')
    if choice.lower() in ['yes', 'y']:
        audio_stream = input_number('AUDIO', 1, audio_count) - 1
        video_stream = input_number('VIDEO', 1, video_count) - 1
    elif choice.lower() in ['no', 'n', '']:
        audio_stream = 0
        video_stream = 0

    print("Download options:")
    for i, option in enumerate(['mp4 - Combined A&V', 'mp4 - Only Video', 'm4a - Only Audio', 'mp3 - Convert to MP3'], 1):
        print(f"\t[{i:0>2}] >> {option}")
    print("Choose download type:")
    download_type = input_number('TYPE', 1, 4)

    match download_type:
        case 1:
            suffix = ".mp4"
            download_handler = target.download_combined_streams(audio_stream, video_stream)
        case 2:
            suffix = ".mp4"
            download_handler = target.download_video(video_stream)
        case 3:
            suffix = ".m4a"
            download_handler = target.download_audio(audio_stream)
        case 4:
            suffix = ".mp3"
            download_handler = target.download_as_mp3(audio_stream)

    match target.get_path_type():
        case "file":
            print("Enter file path:")
            path = Path(input_string('FILE'))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
            if not path.is_file():
                print_error("Path given is not a file or does not exist.")
        case "directory":
            print("Enter dir path:")
            path = Path(input_string('DIR')).mkdir(parents=True, exist_ok=True)
            if not path.is_dir():
                print_error("Path given is not a dir or does not exist.")
        case _:
            path = None
    
    if not path:
        print_error("Save path is empty.")
        return 1
    
    print("Downloading target...")
    target.set_save_path(path)
    asyncio.run(download_handler)
    return 0
    

if __name__ == '__main__':
    code = main()
    sys.exit(code)
