from __future__ import unicode_literals
import yt_dlp as ydl
import dataclasses
import pathlib
from typing import List, Dict, Any
import logging

logger = logging.getLogger('api')

@dataclasses.dataclass
class Video:
    title: str
    url: str
    formats: List[Dict[Any, Any]]


def fetch_info(url: str):
    logger.info('fetch_info: %s', url)
    ydl_params = {}
    with ydl.YoutubeDL(ydl_params) as downloader:
        logger.info('fetch_info: starting extraction')
        info_dict = downloader.extract_info(url, download=False, process=False)
        logger.info('fetch_info: finished extraction')
        return Video(
            info_dict.get('title'),
            info_dict.get('url'),
            info_dict.get('formats')
        )


def download(directory: str, url: str, audio_id: str, video_id: str):
    logger.info('download: %s %s %s %s', directory, url, audio_id, video_id)
    path = pathlib.Path(directory)
    ydl_params = {
        'format': f'{video_id}+{audio_id}',
        'outtmpl': f'{path / "%(title)s.%(ext)s"}',
    }
    logger.info('download: format is %s', ydl_params['format'])
    with ydl.YoutubeDL(ydl_params) as downloader:
        logger.info('download: starting download')
        downloader.download([url])
        logger.info('download: finished download')
