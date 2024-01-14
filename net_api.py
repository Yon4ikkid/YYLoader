import pytube
from io import BytesIO
from tempfile import NamedTemporaryFile
from pathlib import Path
import psutil
import asyncio
import contextlib

class DownloadTarget:
    def __init__(self, name: str, progress_callback, save_path=None):
        self.__name = DownloadTarget.__strip_name(name)
        self.__progress = 0
        self.__progress_callback = progress_callback
        self.__save_path = save_path
        self._stages = 1.0


    def __strip_name(name: str):
        """Removes non-alphanumeric characters from the name string."""
        return "".join(filter(lambda c: c.isalnum() or c == ' ', name))


    def get_name(self) -> str:
        """Returns the target name."""
        return self.__name


    def set_save_path(self, path) -> str:
        """Sets the intended target save path."""
        self.__save_path = path


    def get_save_path(self) -> str:
        """Returns the intended target save path."""
        return self.__save_path


    def _update_progress(self, progress_addition: float):
        """Updates the target progress by progress_addition and uses the callback."""
        self.__progress = min(100, self.__progress + progress_addition / self._stages)
        if self.__progress_callback != None:
            self.__progress_callback(self.__progress)


    @classmethod
    async def create(cls, *args, **kwargs):
        """Delegates the target construction to an asyncio awaitable thread."""
        def __inner():
            return cls(*args, **kwargs)
        result = await asyncio.to_thread(__inner)
        return result


    async def download(self, *args, **kwargs):
        raise NotImplementedError()


    async def download_video(self, video_stream_index):
        raise NotImplementedError()


    async def download_audio(self, audio_stream_index):
        raise NotImplementedError()


    async def download_combined_streams(self, audio_stream_index, video_stream_index):
        raise NotImplementedError()


    async def download_as_mp3(self, audio_stream_index, track_number=1):
        raise NotImplementedError()


    def get_available_streams(self) -> tuple:
        raise NotImplementedError()


    def get_path_type(self) -> str:
        raise NotImplementedError()


class VideoTarget(DownloadTarget):
    def __init__(self, initialization_url: str, progress_callback, save_path=None):
        source_video = pytube.YouTube(initialization_url, on_progress_callback=self.__inner_progress_handler)
        super().__init__(source_video.title, progress_callback, save_path)
        self.__streams = (
            source_video.streams.filter(only_audio=True).order_by("abr").desc(),
            source_video.streams.filter(only_video=True).order_by("resolution").desc()
        )


    def __inner_progress_handler(self, chunk, file_handle, bytes_remaining):
        local_percentage = 100 * (chunk.filesize - bytes_remaining) / chunk.filesize
        self._update_progress(local_percentage)


    async def __async_download_stream_to_buffer(self, stream_type, stream_index, buffer):
        await asyncio.to_thread(self.__streams[stream_type][stream_index].stream_to_buffer, buffer)


    @contextlib.asynccontextmanager
    async def __download_temporary_stream(self, stream_type, stream_index):
        if self.__streams[stream_type][stream_index].filesize >= (psutil.virtual_memory().available):
            buffer = NamedTemporaryFile(delete=False)
            name = buffer.name
            is_piped = False
        else:
            buffer = BytesIO()
            name = '-'
            is_piped = True
        await self.__async_download_stream_to_buffer(stream_type, stream_index, buffer)
        buffer.seek(0)
        try:
            yield (buffer, name, is_piped)
        finally:
            buffer.close()
            if not is_piped:
                Path(name).unlink()


    async def download_video(self, video_stream_index):
        with open(self.get_save_path(), 'wb') as file_buffer:
            await self.__async_download_stream_to_buffer(1, video_stream_index, file_buffer)


    async def download_audio(self, audio_stream_index):
        print("audio")
        with open(self.get_save_path(), 'wb') as file_buffer:
            await self.__async_download_stream_to_buffer(0, audio_stream_index, file_buffer)


    async def download_combined_streams(self, audio_stream_index, video_stream_index):
        self._stages = 3
        async with contextlib.AsyncExitStack() as stack:
            (audio_buffer, audio_name, audio_is_piped), (video_buffer, video_name, video_is_piped) = await asyncio.gather(
                stack.enter_async_context(self.__download_temporary_stream(0, audio_stream_index)),
                stack.enter_async_context(self.__download_temporary_stream(1, video_stream_index)))
            command = [ 'ffmpeg','-y','-thread_queue_size','4096','-i',audio_name,
                        '-thread_queue_size','4096','-i',video_name,'-c:a','copy',
                        '-c:v','copy', self.get_save_path()]
            p = await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            if audio_is_piped:
                p.stdin.write(audio_buffer.read())
            if video_is_piped:
                p.stdin.write(video_buffer.read())
            await p.stdin.drain()
            p.stdin.close()
            _ = await p.wait()
        self._update_progress(100)


    async def download_as_mp3(self, audio_stream_index, track_number=1):
        self._stages = 2
        async with self.__download_temporary_stream(0, audio_stream_index) as (audio_buffer, audio_name, audio_is_piped):
            command = ['ffmpeg','-y','-i',audio_name,'-b:a','192k','-metadata',
                        f'title={self.get_name()}','-metadata',f'track={track_number}',
                        '-f', 'mp3', self.get_save_path()]
            p = await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            if audio_is_piped:
                p.stdin.write(audio_buffer.read())
            await p.stdin.drain()
            p.stdin.close()
            _ = await p.wait()
        self._update_progress(100)


    def get_available_streams(self) -> tuple:
        return [f"{x.audio_codec} - {x.abr}" for x in self.__streams[0]], [f"{x.video_codec} - {x.resolution}" for x in self.__streams[1]]


    def get_path_type(self):
        return "file"


class PlaylistTarget(DownloadTarget):
    def __init__(self, initialization_url: str, progress_callback, save_path=None):
        source_playlist = pytube.Playlist(initialization_url)
        super().__init__(source_playlist.title, progress_callback, save_path)
        self.__video_target_urls = source_playlist.video_urls
        self._stages = len(self.__video_target_urls)


    def __subtarget_callback(self, progress):
        self._update_progress(progress)


    async def __generate_targets(self, association):
        async def __inner(url):
            video_target = await VideoTarget.create(url, self.__subtarget_callback)
            video_target.set_save_path(self.get_save_path() + f"/{video_target.get_name()}.{association}")
            return video_target
        return await asyncio.gather(*(__inner(url) for url in self.__video_target_urls))


    async def download_video(self, video_stream_index):
        targets = await self.__generate_targets('mp4')
        await asyncio.gather(*(target.download_video(-video_stream_index) for target in targets))


    async def download_audio(self, audio_stream_index):
        targets = await self.__generate_targets('m4a')
        await asyncio.gather(*(target.download_audio(-audio_stream_index) for target in targets))


    async def download_combined_streams(self, audio_stream_index, video_stream_index):
        targets = await self.__generate_targets('mp4')
        await asyncio.gather(*(target.download_combined_streams(-audio_stream_index, -video_stream_index) for target in targets))


    async def download_as_mp3(self, audio_stream_index, track_number=1):
        targets = await self.__generate_targets('mp3')
        await asyncio.gather(*(target.download_as_mp3(-audio_stream_index, i) for i, target in enumerate(targets, start=track_number)))


    def get_available_streams(self) -> tuple:
        return (['max_bitrate', 'min_bitrate'],['max_resolution','min_resolution'])    


    def get_path_type(self):
        return "directory"
