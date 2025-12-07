#!/usr/bin/env python3
from flask import Flask, render_template_string, request
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Thread pool for non-blocking subprocess
executor = ThreadPoolExecutor(max_workers=2)

# Global mute state
mute_lock = threading.Lock()
is_muted = False
previous_volume = 50

def is_valid_volume(volume_str):
    try:
        vol = float(volume_str)
        if not (0 <= vol <= 100):
            return False
        vol_str = f"{vol:g}"
        return vol_str[-1] in '05'
    except ValueError:
        return False

def get_current_volume():
    """Get current sink volume (1s timeout)"""
    try:
        result = subprocess.run(['pactl', 'get-sink-volume', '@DEFAULT_SINK@'],
                                capture_output=True, text=True, timeout=1)
        for part in result.stdout.split('/'):
            part = part.strip()
            if part.endswith('%'):
                return float(part.rstrip('%'))
        return 50
    except:
        return 50

def run_pactl_nonblock(change):
    try:
        subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', change],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                      timeout=2, check=False)
        return True
    except:
        return False

def run_playerctl_nonblock():
    try:
        subprocess.run(['playerctl', 'play-pause'], 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                      timeout=2, check=False)
        return True
    except:
        return False

def run_pactl(change):
    """Blocking wrapper for mute"""
    executor.submit(run_pactl_nonblock, change)

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html><head><title>Remote Media Control</title>
<style>
body {font-family:sans-serif;text-align:center;padding:50px;}
button {font-size:24px;padding:20px 40px;margin:10px;background:#007cba;color:white;border:none;border-radius:8px;cursor:pointer;}
button:hover {background:#005a87;}
.mute {background:#dc3545;}
.mute:hover {background:#c82333;}
input {font-size:20px;padding:15px;width:100px;margin:10px;}
.controls {display:flex;justify-content:center;align-items:center;gap:20px;margin-bottom:20px;}
</style></head>
<body>
<h1>Remote Media Controls</h1>

<div class="controls">
  <button onclick="send('/previous')">⏮</button>
  <button onclick="send('/play-pause')">⏯</button>
  <button onclick="send('/next')">⏭</button>
</div>

<button onclick="send('/volume-up')">Vol +5</button>
<button onclick="send('/volume-down')">Vol -5</button>
<button class="mute" id="muteBtn" onclick="send('/mute')">Mute</button>
<br>
<input id="vol" type="number" min="0" max="100" step="5" value="50">
<button onclick="setVol()">Set Volume</button>
<div id="status"></div>

<script>
function send(cmd){
  fetch(cmd)
    .then(r=>r.text())
    .then(t=>document.getElementById('status').innerHTML=t);
}
function setVol(){
  let vol=document.getElementById('vol').value;
  if(!/^(0|5|10|15|20|25|30|35|40|45|50|55|60|65|70|75|80|85|90|95|100)$/.test(vol)){
    document.getElementById('status').innerHTML='<span style="color:red">Must be 0-100 ending in 0 or 5</span>'; 
    return;
  }
  send('/set-volume?vol='+vol);
}
</script>
</body></html>''')

@app.route('/play-pause')
def play_pause():
    executor.submit(run_playerctl_nonblock)
    return 'OK'

@app.route('/volume-up')
def volume_up():
    global is_muted
    with mute_lock:
        is_muted = False
    current_vol = get_current_volume()
    new_vol = min(100, current_vol + 5) 
    executor.submit(run_pactl_nonblock, '+5%')
    return f'OK - Volume: {new_vol:.0f}%'

@app.route('/volume-down')
def volume_down():
    global is_muted
    with mute_lock:
        is_muted = False
    current_vol = get_current_volume()
    new_vol = max(0, current_vol - 5) 
    executor.submit(run_pactl_nonblock, '-5%')
    return f'OK - Volume: {new_vol:.0f}%'

@app.route('/set-volume')
def set_volume():
    vol = request.args.get('vol', '').strip()
    if not is_valid_volume(vol):
        return '<span style="color:red">Invalid: use 0,5,10,15,...,100</span>', 400
    global is_muted
    with mute_lock:
        is_muted = False
    executor.submit(run_pactl_nonblock, f'{vol}%')
    return f'<span style="color:green">Volume set to {vol}%</span>'

@app.route('/mute')
def mute_toggle():
    global is_muted, previous_volume
    with mute_lock:
        if is_muted:
            # restore previous volume
            executor.submit(run_pactl_nonblock, f'{previous_volume}%')
            is_muted = False
            return '<span style="color:green">Unmuted</span>'
        else:
            previous_volume = get_current_volume()
            executor.submit(run_pactl_nonblock, '0%')
            is_muted = True
            return f'<span style="color:orange">Muted (was {previous_volume}%)</span>'
@app.route('/next')
def next_track():
    executor.submit(subprocess.run, ['playerctl', 'next'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 'OK - Next track'

@app.route('/previous')
def previous_track():
    executor.submit(subprocess.run, ['playerctl', 'previous'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 'OK - Previous track'


if __name__ == '__main__':
    print("Running")
    app.run(host='0.0.0.0', port=7337, debug=False, threaded=True)
