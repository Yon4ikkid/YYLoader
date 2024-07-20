
function updateTasks() {
    // TODO
}

function flip() {
    document.getElementById('main-div').classList.toggle('is-flipped');
}

function disableStart() {
    document.getElementById('initiate-download-button').disabled = true;
}

function enableStart() {
    document.getElementById('initiate-download-button').disabled = false;
}

function showLoader() {
    document.getElementById('loader').style.visibility = 'visible';
}

function hideLoader() {
    document.getElementById('loader').style.visibility = 'hidden';
}

var g_url = "";

async function start() {
    console.log('Starting download');
    if (g_url == "") {
        console.error('Resource was empty');
        return;
    }

    const audio_list = document.getElementById("audio-list");
    const audio_id = audio_list.value;

    const video_list = document.getElementById("video-list");
    const video_id = video_list.value;

    showLoader();
    const response = await fetch('http://localhost:32567/download', {
        method: 'POST',
        headers: {
            'Content-type': 'application/json'
        },
        body: JSON.stringify({
            url: g_url,
            audio_id: audio_id,
            video_id: video_id
        })
    });
    hideLoader();
}

function addOptions(target_element_id, format_array, text_callback) {
    const select = document.getElementById(target_element_id);
    for (let i = 0; i < Object.keys(format_array).length; i++) {
        const option = document.createElement('option');
        option.className = 'cls-format-list-element';
        option.value = format_array[i].format_id;
        option.text = text_callback(format_array[i]);
        select.appendChild(option);
    }
}

async function prefetch(url) {
    const encoded_resource = btoa(url);
    const preprocessed_resource = encoded_resource.replace('/', '_');
    const response = await fetch(`http://localhost:32567/preview/${preprocessed_resource}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        }
    );
    response_json = await response.json();
    console.log('Fetched preview lists');

    const audio = response_json.audio;
    addOptions('audio-list', audio, (format) => {
        return `${format.ext} ${format.acodec} ${format.tbr}`;
    });
    console.log('Added audio options');

    const video = response_json.video;
    addOptions('video-list', video, (format) => {
        return `${format.ext} ${format.vcodec} ${format.width}x${format.height}`;
    });
    console.log('Added video options');
}

function validate(url) {
    const parsed_url = new URL(url);
    if (!parsed_url.hostname.endsWith(".youtube.com") ||
        parsed_url.pathname == "/") { 
        return false;
    }

    return true;
}

async function main(url) {
    if (!validate(url)) {
        console.error('URL was invalid: ' + url)
        alert('Not a youtube video');
        close();
        return;
    }

    showLoader();
    await prefetch(url);
    g_url = url;
    hideLoader();
    enableStart();
}

document.addEventListener('DOMContentLoaded', () => {
    if (typeof browser === "undefined") {
        var browser = chrome;
    }

    document.getElementById('flip-button').addEventListener('click',flip);
    document.getElementById('initiate-download-button').addEventListener('click', start);
    browser.tabs.query({active: true, lastFocusedWindow: true}, tabs => {
        const url = tabs[0].url;
        console.log('Command triggered for ' + url);
        main(url);
    });
});
