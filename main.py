import os
import re
import pickle
from pytube import Playlist, YouTube
from tqdm import tqdm
import requests

selected_quality = None


def sanitize_filename(filename):
    # Remove characters that are not allowed in file names
    return re.sub(r'[\\/*?:"<>|]', '', filename)


def get_available_quality_options(video):
    streams = video.streams.filter(progressive=True, file_extension='mp4').order_by('resolution')
    return [stream.resolution for stream in streams]


def download_video(video_url, output_path):
    global selected_quality
    video = YouTube(video_url)

    available_qualities = get_available_quality_options(video)

    if selected_quality is None:
        print("Choose Quality:")
        for i, quality in enumerate(available_qualities, start=1):
            print(f"{i}. {quality}")
        choice = input("Enter the number corresponding to the desired quality: ")
        if not choice.isdigit() or int(choice) not in range(1, len(available_qualities) + 1):
            print("Invalid choice.")
            return
        selected_quality = available_qualities[int(choice) - 1]

    if selected_quality not in available_qualities:
        print(
            f"Selected quality '{selected_quality}' is not available. Available options: {', '.join(available_qualities)}")
        return

    stream = video.streams.get_by_resolution(selected_quality)
    file_size = stream.filesize

    # Check if the file has been previously downloaded
    safe_filename = sanitize_filename(video.title)
    file_path = os.path.join(output_path, safe_filename + '.' + stream.subtype)
    if os.path.exists(file_path):
        print(f"Skipping download: '{safe_filename}' already exists.")
        return

    # Check if a partial download exists
    temp_file_path = file_path + '.temp'
    resume_byte_position = 0
    if os.path.exists(temp_file_path):
        resume_byte_position = os.path.getsize(temp_file_path)

    progress_bar = tqdm(total=file_size, initial=resume_byte_position, unit='bytes', unit_scale=True, desc=video.title,
                        ascii=False)

    # Download the video stream
    response = requests.get(stream.url, stream=True, headers={'Range': f'bytes={resume_byte_position}-'})
    with open(temp_file_path, 'ab') as file_handle:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file_handle.write(chunk)
                progress_bar.update(len(chunk))

    # Save the progress
    with open(temp_file_path + '.pickle', 'wb') as progress_file:
        pickle.dump(progress_bar.n, progress_file)

    progress_bar.close()

    # Rename temp file to original filename upon completion
    os.rename(temp_file_path, file_path)
    os.remove(temp_file_path + '.pickle')

    print(f"Downloaded: {video.title} - Quality: {selected_quality}")


def download_playlist(playlist_url, output_path='./'):
    playlist = Playlist(playlist_url)
    print(f"Total videos in playlist: {len(playlist.video_urls)}")

    for video_url in playlist.video_urls:
        try:
            download_video(video_url, output_path)
        except Exception as e:
            print(f"Error downloading {video_url}: {e}")


if __name__ == "__main__":
    playlist_url = input("Enter YouTube playlist URL: ")
    output_path = input("Enter output path (press Enter for current directory): ").strip() or './'

    download_playlist(playlist_url, output_path)
