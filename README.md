A simple remote media control server to manage your media without being at your computer. Designed for PulseAudio users.

Requires: playerctl (sudo apt install playerctl), flask (pip install flask), and pactl (sudo apt install pulseaudio-utils)

## Quick requirements install
```bash
./install-apt-requirements.sh && pip install -r requirements.txt
```


## To run
Once all your requirements are installed (see above section) and you're in the directory, run 
```bash
python3 mediacontrols.py
```
And in a web browser go to
```
localhost:7337
```
Or any preferred IP, port is still 7337 unless you change it.
