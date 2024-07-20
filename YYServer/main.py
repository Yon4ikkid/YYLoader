from flask import Flask
from flask import request
from flask import render_template, Response, jsonify
import base64
import logging
import toml
import api


app = Flask(__name__)

logger = logging.getLogger('main')

config = toml.load('config.toml')

status = ''


def split_formats(formats):
    accepted_extensions = config['download']['accepted_extensions']

    audio_formats = []
    video_formats = []
    for format in formats:
        if format['ext'] not in accepted_extensions:
            continue
        if 'acodec' not in format or 'vcodec' not in format or 'drc' in format['format_id']:
            continue

        is_audio = format['acodec'] != 'none' and format['vcodec'] == 'none'
        if is_audio:
            audio_formats.append(format)
        else:
            video_formats.append(format)
    return audio_formats, video_formats


@app.route('/preview/<encoded_link>', methods=['GET'])
def fetch_info(encoded_link: str):
    global status
    status = 'working'
    logger.info("fetch_info: Handling encoded link: %s", encoded_link)
    encoded_link = encoded_link.replace('_','/')
    decoded_link = base64.b64decode(encoded_link).decode()
    logger.info("fetch_info: Decoded link: %s", decoded_link)

    info = api.fetch_info(decoded_link)
    audio_formats, video_formats = split_formats(info.formats)
    
    return jsonify(
        audio=audio_formats,
        video=video_formats
    )


@app.route('/download', methods=['POST'])
def download():
    global status
    status = 'working'
    data = request.json
    logger.info("download: %s %s %s", data['url'], data['audio_id'], data['video_id'])
    api.download(config['download']['directory'], data['url'], data['audio_id'], data['video_id'])
    status = 'done'
    return Response(status=200)


@app.route('/status', methods=['GET'])
def get_status():
    return jsonify(status=status)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s:%(message)s')
    logger.info('starting server')
    app.run(port=config['server']['port'])
    logger.info('server end')
