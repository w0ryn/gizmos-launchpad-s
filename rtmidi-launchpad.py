import time
import os

from math import floor
from subprocess import call

import rtmidi


LAUNCHPAD_COLS = 9
LAUNCHPAD_ROWS = 8

################################################################
### Application Settings #######################################
################################################################

GLOBAL_FLASH_TIME = 0.5
GLOBAL_FLASH_CYCLE = GLOBAL_FLASH_TIME
GLOBAL_FLASH_ON = True

PORT_COUNT = 0
GLOBAL_REFRESH_PORT_SIGNAL = False

APPLICATION_REFRESH_TIME = 0.25

MAX_OUTPUT_VOLUME = 140
MAX_OUTPUT_LEVEL = LAUNCHPAD_COLS - 1

MAX_INPUT_VOLUME = 140
MAX_INPUT_LEVEL = LAUNCHPAD_COLS - 1


################################################################
### Launchpad S API Signals ####################################
################################################################


COLORS = {
    # Colors are combinations of red and green:
    # 0b00GG11RR
    'OFF'          : 0b00001100,

    'DIM_GREEN'    : 0b00011100,
    'MEDIUM_GREEN' : 0b00101100,
    'BRIGHT_GREEN' : 0b00111100,

    'DIM_RED'      : 0b00001101,
    'MEDIUM_RED'   : 0b00001110,
    'BRIGHT_RED'   : 0b00001111,

    'DIM_AMBER'    : 0b00011101,
    'MEDIUM_AMBER' : 0b00101110,
    'BRIGHT_AMBER' : 0b00111111,

    'MEDIUM_ORANGE': 0b00011110,
    'BRIGHT_ORANGE': 0b00101111,
    'RED_ORANGE'   : 0b00011111,

    'MEDIUM_YELLOW': 0b00101101,
    'BRIGHT_YELLOW': 0b00111110,
    'YELLOW_GREEN' : 0b00111101,
}

LIGHT_ON  = 0x90
LIGHT_OFF = 0x80

AUTOMAP_ON = 0xb0

ACTIVE_SIGNAL = 127

AUTOMAP_SIGNAL = 176

RESET_LIGHT_SIGNAL = [0xb0, 0x00, 0x00]


################################################################
### Customizable Colors ########################################
################################################################

BUTTON_FLASH_ON_ACTIVE = {
    '72': True,
}

BUTTON_COLORS = {
    'default': ['BRIGHT_RED', 'DIM_RED'],

    '4' : ['BRIGHT_ORANGE', 'MEDIUM_GREEN'],
    '20': ['BRIGHT_ORANGE', 'MEDIUM_GREEN'],
    '52': ['BRIGHT_ORANGE', 'MEDIUM_GREEN'],
    '53': ['BRIGHT_ORANGE', 'MEDIUM_GREEN'],

    '54': ['BRIGHT_ORANGE', 'YELLOW_GREEN'],
    '55': ['BRIGHT_ORANGE', 'YELLOW_GREEN'],
    '36': ['BRIGHT_ORANGE', 'YELLOW_GREEN'],

    '5' : ['BRIGHT_ORANGE', 'MEDIUM_RED'],
    '6' : ['BRIGHT_ORANGE', 'MEDIUM_RED'],
    '7' : ['BRIGHT_ORANGE', 'MEDIUM_RED'],
    '8' : ['BRIGHT_ORANGE', 'MEDIUM_RED'],
    '21': ['BRIGHT_ORANGE', 'MEDIUM_RED'],
    '22': ['BRIGHT_ORANGE', 'MEDIUM_RED'],
    '23': ['BRIGHT_ORANGE', 'MEDIUM_RED'],
    '24': ['BRIGHT_ORANGE', 'MEDIUM_RED'],
    '37': ['BRIGHT_ORANGE', 'MEDIUM_RED'],
    '38': ['BRIGHT_ORANGE', 'MEDIUM_RED'],
    '39': ['BRIGHT_ORANGE', 'MEDIUM_RED'],
    '40': ['BRIGHT_ORANGE', 'MEDIUM_RED'],
    '56': ['BRIGHT_ORANGE', 'MEDIUM_RED'],
}

BUTTON_COLORS['automap'] = {
    '104': ['BRIGHT_GREEN', 'MEDIUM_YELLOW'],
    '105': ['BRIGHT_AMBER', 'MEDIUM_YELLOW'],

    '107': ['BRIGHT_ORANGE', 'MEDIUM_AMBER'],
    '108': ['BRIGHT_ORANGE', 'MEDIUM_YELLOW'],
    '109': ['BRIGHT_ORANGE', 'MEDIUM_AMBER'],

    '111': ['BRIGHT_RED', 'MEDIUM_ORANGE'],
    'default': [ 'YELLOW_GREEN', 'DIM_GREEN' ],
}

BUTTON_COLORS['source'] = {
    'default': BUTTON_COLORS['default'][1],
    'no-volume': 'BRIGHT_AMBER',
    'toggle': ['BRIGHT_RED', 'DIM_AMBER'],
    'levels': [
        'MEDIUM_RED', 'MEDIUM_RED',
        'MEDIUM_AMBER', 'MEDIUM_AMBER', 'MEDIUM_AMBER',
        'BRIGHT_AMBER', 'BRIGHT_AMBER',
        'BRIGHT_YELLOW', 'BRIGHT_YELLOW',
    ],
}

BUTTON_COLORS['sink'] = {
    'default': BUTTON_COLORS['default'][1],
    'no-volume': 'BRIGHT_RED',
    'toggle': ['BRIGHT_GREEN', 'DIM_GREEN'],
    'levels': [
        'BRIGHT_GREEN', 'BRIGHT_GREEN', 'BRIGHT_GREEN',
        'YELLOW_GREEN', 'YELLOW_GREEN',
        'BRIGHT_YELLOW',
        'BRIGHT_RED', 'BRIGHT_RED', 'BRIGHT_RED',
    ],
}


################################################################
### Launchpad S API Helpers ####################################
################################################################

is_flashing_button = lambda note: BUTTON_FLASH_ON_ACTIVE.get(str(note), False)
is_active_signal = lambda byte_signal: byte_signal[2] == ACTIVE_SIGNAL

def color_button(byte_signal=None, colors=None):
    active = is_keydown(byte_signal)

    note = byte_signal[1]

    if colors is None:
        colors = BUTTON_COLORS.get(str(note), BUTTON_COLORS['default'])

    color = COLORS[colors[0] if active else colors[1]]

    if GLOBAL_FLASH_ON or not active or not is_flashing_button(note):
        signal = LIGHT_ON
    else:
        signal = LIGHT_OFF

    midiout.send_message([signal, note, color])


def color_automap_button(byte_signal, force_default=False):
    active = is_active_signal(byte_signal)

    note = byte_signal[1]

    colors = BUTTON_COLORS['automap'].get(
        'default' if force_default else str(note),
        BUTTON_COLORS['automap']['default']
    )

    color = COLORS[colors[0] if active else colors[1]]

    midiout.send_message([AUTOMAP_ON, note, color])


################################################################
### General Utilities ##########################################
################################################################

def fix_value_to_bounds(val, lower, upper):
    if val < lower:
        return lower
    return upper if val > upper else val

def restart_pulse_audio():
    call(['pulseaudio', '-k'])

def num_lock(toggle=False):
    if toggle:
        call(['xdotool', 'key', 'Num_Lock'])

    cmd = 'xset q | grep -q "Num Lock:\\s*on" && echo 1'
    return bool(os.popen(cmd).read())

def caps_lock(toggle=False):
    if toggle:
        call(['xdotool', 'key', 'Caps_Lock'])

    cmd = 'xset q | grep -q "Caps Lock:\\s*on" && echo 1'
    return bool(os.popen(cmd).read())

def bind_key(byte_signal, key):
    # pylint: disable=expression-not-assigned
    keydown(key) if is_keydown(byte_signal) else keyup(key)
    color_button(byte_signal)

keydown = lambda key: call(['xdotool', 'keydown', key])
keyup = lambda key: call(['xdotool', 'keyup', key])


is_keydown = is_active_signal
is_automap_key = lambda byte_signal: byte_signal[0] == AUTOMAP_SIGNAL

generate_fake_midi_signal = lambda note=0, on=True: [0,note,127 if on else 0]


################################################################
### Keybindings and Keybound Actions ###########################
################################################################

HOLD_BINDINGS = {} # handles both keyup / keydown
KEYBINDINGS = {} # only triggered on keydown

AUTOMAP = {} # automap row is handled differently from other rows


# --------------------------------------------------------------
# Basic keybindings
# --------------------------------------------------------------

# tenkeypad
HOLD_BINDINGS['4']  = lambda byte_signal: bind_key(byte_signal, '0')
HOLD_BINDINGS['5']  = lambda byte_signal: bind_key(byte_signal, '1')
HOLD_BINDINGS['6']  = lambda byte_signal: bind_key(byte_signal, '4')
HOLD_BINDINGS['7']  = lambda byte_signal: bind_key(byte_signal, '7')
HOLD_BINDINGS['8']  = lambda byte_signal: bind_key(byte_signal, 'equal')
HOLD_BINDINGS['20'] = lambda byte_signal: bind_key(byte_signal, '0')
HOLD_BINDINGS['21'] = lambda byte_signal: bind_key(byte_signal, '2')
HOLD_BINDINGS['22'] = lambda byte_signal: bind_key(byte_signal, '5')
HOLD_BINDINGS['23'] = lambda byte_signal: bind_key(byte_signal, '8')
HOLD_BINDINGS['24'] = lambda byte_signal: bind_key(byte_signal, 'slash')
HOLD_BINDINGS['36'] = lambda byte_signal: bind_key(byte_signal, 'period')
HOLD_BINDINGS['37'] = lambda byte_signal: bind_key(byte_signal, '3')
HOLD_BINDINGS['38'] = lambda byte_signal: bind_key(byte_signal, '6')
HOLD_BINDINGS['39'] = lambda byte_signal: bind_key(byte_signal, '9')
HOLD_BINDINGS['40'] = lambda byte_signal: bind_key(byte_signal, 'asterisk')
HOLD_BINDINGS['52'] = lambda byte_signal: bind_key(byte_signal, 'Return')
HOLD_BINDINGS['53'] = lambda byte_signal: bind_key(byte_signal, 'Return')
HOLD_BINDINGS['54'] = lambda byte_signal: bind_key(byte_signal, 'plus')
HOLD_BINDINGS['55'] = lambda byte_signal: bind_key(byte_signal, 'plus')
HOLD_BINDINGS['56'] = lambda byte_signal: bind_key(byte_signal, 'minus')


# --------------------------------------------------------------
# Automap keybindings
# --------------------------------------------------------------

def toggle_num_lock(byte_signal):
    if is_keydown(byte_signal):
        color_automap_button(
            generate_fake_midi_signal(
                note=byte_signal[1],
                on=num_lock(toggle=True),
            )
        )

def toggle_caps_lock(byte_signal):
    if is_keydown(byte_signal):
        color_automap_button(
            generate_fake_midi_signal(
                note=byte_signal[1],
                on=caps_lock(toggle=True),
            )
        )

def restart_audio_engine(byte_signal):
    restart_pulse_audio()
    color_automap_button(byte_signal)

def play_pause(byte_signal):
    color_automap_button(byte_signal)
    bind_key(byte_signal, 'XF86AudioPlay')

def next_song(byte_signal):
    color_automap_button(byte_signal)
    bind_key(byte_signal, 'XF86AudioNext')

def prev_song(byte_signal):
    color_automap_button(byte_signal)
    bind_key(byte_signal, 'XF86AudioPrev')

AUTOMAP['default'] = color_automap_button
AUTOMAP['104'] = toggle_num_lock
AUTOMAP['105'] = toggle_caps_lock
#AUTOMAP['106'] =
AUTOMAP['107'] = prev_song
AUTOMAP['108'] = play_pause
AUTOMAP['109'] = next_song
#AUTOMAP['110'] =
AUTOMAP['111'] = restart_audio_engine


# --------------------------------------------------------------
# Default system microphone controls
# --------------------------------------------------------------

def pulse_default_source_volume_control(level, set_volume=True):
    INDICES = { 'main': [80, 88], 'staggered': [64, 71] }

    level = fix_value_to_bounds(level, 0, MAX_INPUT_LEVEL)

    if set_volume:
        volume = '{0}%'.format(floor(MAX_INPUT_VOLUME * level/MAX_INPUT_LEVEL))
        call(['pactl', 'set-source-volume', '@DEFAULT_SOURCE@', volume])

    get_active_colors = lambda x: [
        BUTTON_COLORS['source']['levels'][x] if level > 0 else BUTTON_COLORS['source']['no-volume'],
        None
    ]

    for x in range(level + 1):
        main_index = INDICES['main'][0] + x
        staggered_index = fix_value_to_bounds(
            INDICES['staggered'][0] + x - 1,
            INDICES['staggered'][0],
            INDICES['staggered'][1],
        )

        active_colors = get_active_colors(x)

        for note in [main_index, staggered_index]:
            color_button(
                generate_fake_midi_signal(note=note, on=True),
                colors=active_colors
            )

    inactive_colors = [None, BUTTON_COLORS['source']['default']]

    for x in range(MAX_INPUT_LEVEL - level):
        main_index = INDICES['main'][1] - x
        staggered_index = fix_value_to_bounds(
            INDICES['staggered'][1] - x,
            INDICES['staggered'][0] + 1,
            INDICES['staggered'][1],
        )

        for note in [main_index, staggered_index]:
            color_button(
                generate_fake_midi_signal(note=note, on=False),
                colors=inactive_colors
            )

def pulse_default_source_toggle(toggle=True):
    cmd = 'amixer -D pulse get Capture | grep -q off && echo 1'
    is_muted = bool(os.popen(cmd).read())

    if toggle:
        call(['amixer', '-D', 'pulse', 'set', 'Capture', 'toggle'])
        is_muted = not is_muted

    color_button(
        generate_fake_midi_signal(note=72, on=not is_muted),
        colors=BUTTON_COLORS['source']['toggle'],
    )

KEYBINDINGS['80'] = lambda byte_signal: pulse_default_source_volume_control(0)
KEYBINDINGS['81'] = lambda byte_signal: pulse_default_source_volume_control(1)
KEYBINDINGS['82'] = lambda byte_signal: pulse_default_source_volume_control(2)
KEYBINDINGS['83'] = lambda byte_signal: pulse_default_source_volume_control(3)
KEYBINDINGS['84'] = lambda byte_signal: pulse_default_source_volume_control(4)
KEYBINDINGS['85'] = lambda byte_signal: pulse_default_source_volume_control(5)
KEYBINDINGS['86'] = lambda byte_signal: pulse_default_source_volume_control(6)
KEYBINDINGS['87'] = lambda byte_signal: pulse_default_source_volume_control(7)
KEYBINDINGS['88'] = lambda byte_signal: pulse_default_source_volume_control(8)

KEYBINDINGS['64'] = KEYBINDINGS['80']
KEYBINDINGS['65'] = KEYBINDINGS['81']
KEYBINDINGS['66'] = KEYBINDINGS['82']
KEYBINDINGS['67'] = KEYBINDINGS['83']
KEYBINDINGS['68'] = KEYBINDINGS['84']
KEYBINDINGS['69'] = KEYBINDINGS['85']
KEYBINDINGS['70'] = KEYBINDINGS['86']
KEYBINDINGS['71'] = KEYBINDINGS['87']
KEYBINDINGS['72'] = lambda byte_signal: pulse_default_source_toggle()


# --------------------------------------------------------------
# Default system speaker controls
# --------------------------------------------------------------

def system_default_sink_volume_control(level, set_volume=True):
    INDICES = { 'main': [96, 104], 'staggered': [112, 119] }

    level = MAX_OUTPUT_LEVEL if level > MAX_OUTPUT_LEVEL else level

    if set_volume:
        volume = '{0}%'.format(floor(MAX_OUTPUT_VOLUME * level/MAX_OUTPUT_LEVEL))
        call(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', volume])

    get_active_colors = lambda x: [
        BUTTON_COLORS['sink']['levels'][x] if level > 0 else BUTTON_COLORS['sink']['no-volume'],
        None
    ]

    for x in range(level + 1):
        main_index = INDICES['main'][0] + x
        staggered_index = fix_value_to_bounds(
            INDICES['staggered'][0] + x - 1,
            INDICES['staggered'][0],
            INDICES['staggered'][1],
        )

        active_colors = get_active_colors(x)

        for note in [main_index, staggered_index]:
            color_button(
                byte_signal=generate_fake_midi_signal(note=note, on=True),
                colors=active_colors
            )

    inactive_colors = [None, BUTTON_COLORS['sink']['default']]

    for x in range(MAX_INPUT_LEVEL - level):
        main_index = INDICES['main'][1] - x
        staggered_index = fix_value_to_bounds(
            INDICES['staggered'][1] - x,
            INDICES['staggered'][0] + 1,
            INDICES['staggered'][1],
        )

        for note in [main_index, staggered_index]:
            color_button(
                byte_signal=generate_fake_midi_signal(note=note, on=False),
                colors=inactive_colors
            )


def system_default_sink_toggle(toggle=True):
    cmd = 'amixer -D pulse get Master | grep -q off && echo 1'
    is_muted = bool(os.popen(cmd).read())

    if toggle:
        call(['amixer', '-D', 'pulse', 'set', 'Master', 'toggle'])
        is_muted = not is_muted

    color_button(
        generate_fake_midi_signal(note=120, on=not is_muted),
        colors=BUTTON_COLORS['sink']['toggle'],
    )

KEYBINDINGS['96']  = lambda byte_signal: system_default_sink_volume_control(0)
KEYBINDINGS['97']  = lambda byte_signal: system_default_sink_volume_control(1)
KEYBINDINGS['98']  = lambda byte_signal: system_default_sink_volume_control(2)
KEYBINDINGS['99']  = lambda byte_signal: system_default_sink_volume_control(3)
KEYBINDINGS['100'] = lambda byte_signal: system_default_sink_volume_control(4)
KEYBINDINGS['101'] = lambda byte_signal: system_default_sink_volume_control(5)
KEYBINDINGS['102'] = lambda byte_signal: system_default_sink_volume_control(6)
KEYBINDINGS['103'] = lambda byte_signal: system_default_sink_volume_control(7)
KEYBINDINGS['104'] = lambda byte_signal: system_default_sink_volume_control(8)

KEYBINDINGS['112'] = KEYBINDINGS['96']
KEYBINDINGS['113'] = KEYBINDINGS['97']
KEYBINDINGS['114'] = KEYBINDINGS['98']
KEYBINDINGS['115'] = KEYBINDINGS['99']
KEYBINDINGS['116'] = KEYBINDINGS['100']
KEYBINDINGS['117'] = KEYBINDINGS['101']
KEYBINDINGS['118'] = KEYBINDINGS['102']
KEYBINDINGS['119'] = KEYBINDINGS['103']
KEYBINDINGS['120'] = lambda byte_signal: system_default_sink_toggle()


################################################################
### Light Sequences ############################################
################################################################

def boot_sequence(update_me=True):
    sleep_time = 0.03
    multiplier = .98
    pause_time = 0.5

    automap_signal = lambda x: [None, 104 + x, 0]
    button_signal = lambda x: [None, floor(x/LAUNCHPAD_COLS)*16 + x%LAUNCHPAD_COLS, 0]

    for x in range(LAUNCHPAD_COLS - 1):
        color_automap_button(automap_signal(x), force_default=True)
        time.sleep(sleep_time)
        sleep_time *= multiplier

    for x in range(LAUNCHPAD_ROWS * LAUNCHPAD_COLS):
        color_button(byte_signal=button_signal(x), colors=BUTTON_COLORS['default'])
        time.sleep(sleep_time)
        sleep_time *= multiplier

    time.sleep(pause_time)

    for x in range(LAUNCHPAD_COLS - 1):
        color_automap_button(automap_signal(x))
    for x in range(LAUNCHPAD_ROWS*LAUNCHPAD_COLS):
        color_button(button_signal(x))

    if update_me:
        update()

################################################################
### Persistent Updates #########################################
################################################################

def update():
    update_midi_port()
    update_global_flash_cycle()
    update_output_volume_visual()
    update_input_volume_visual()
    update_key_lock_visual()

def update_global_flash_cycle():
    # pylint: disable=global-statement
    global GLOBAL_FLASH_CYCLE, GLOBAL_FLASH_ON,\
           APPLICATION_REFRESH_TIME, GLOBAL_FLASH_TIME

    GLOBAL_FLASH_CYCLE -= APPLICATION_REFRESH_TIME

    if GLOBAL_FLASH_CYCLE < 0:
        GLOBAL_FLASH_ON = not GLOBAL_FLASH_ON
        GLOBAL_FLASH_CYCLE = GLOBAL_FLASH_TIME


def update_output_volume_visual():
    cmd = 'amixer -D pulse sget Master | grep "Front Left:" | sed "s/^.*\\[\\(.*\\)%.*$/\\1/" || return 0'
    volume = os.popen(cmd).read()
    if volume:
        volume = int(volume)
        level = floor(
            round(volume / MAX_OUTPUT_VOLUME * MAX_OUTPUT_LEVEL)
        )

        system_default_sink_volume_control(level, set_volume=False)
        system_default_sink_toggle(toggle=False)

def update_input_volume_visual():
    cmd = 'amixer -D pulse sget Capture | grep "Front Left:" | sed "s/^.*\\[\\(.*\\)%.*$/\\1/" || return 0'
    volume = os.popen(cmd).read()
    if volume:
        volume = int(volume)
        level = floor(
            round(volume / MAX_INPUT_VOLUME * MAX_INPUT_LEVEL)
        )

        pulse_default_source_volume_control(level, set_volume=False)
        pulse_default_source_toggle(toggle=False)

def update_key_lock_visual():
    update_num_lock_visual()
    update_caps_lock_visual()

def update_num_lock_visual():
    color_automap_button(generate_fake_midi_signal(note=104, on=num_lock()))

def update_caps_lock_visual():
    color_automap_button(generate_fake_midi_signal(note=105, on=caps_lock()))

def update_midi_port():
    # pylint: disable=global-statement
    global GLOBAL_REFRESH_PORT_SIGNAL, PORT_COUNT

    current_port_count = midiout.get_port_count()

    if current_port_count < PORT_COUNT:
        PORT_COUNT = midiout.get_port_count()

    elif current_port_count > PORT_COUNT:
        activate_ports()
        boot_sequence(update_me=False)

def activate_ports():
    # pylint: disable=global-statement
    global PORT_COUNT

    midiout.close_port()
    midiin.close_port()

    time.sleep(2.0)

    cmd = '''amidi --list-devices | grep Launchpad -n | sed 's/:.*$//'; '''
    cmd_output = os.popen(cmd).read()
    port_number = int(cmd_output)

    midiout.open_port(port_number)
    midiin.open_port(port_number)

    PORT_COUNT = midiout.get_port_count()

    midiin.set_callback(input_callback)
    midiout.send_message(RESET_LIGHT_SIGNAL)

################################################################
### Application Loop ###########################################
################################################################

def input_callback(midi_in, dump):
    # @TODO: remove debug print
    if dump is not None:
        print(dump)

    byte_signal = midi_in[0]
    note = byte_signal[1]

    is_automap = is_automap_key(byte_signal)
    is_keybinding = not is_automap and str(note) in KEYBINDINGS.keys()
    is_holdbinding = not is_automap and str(note) in HOLD_BINDINGS.keys()
    is_automap_binding = is_automap and str(note) in AUTOMAP.keys()

    print(byte_signal)
    print('input callback')

    if is_keybinding:
        if is_keydown(byte_signal):
            KEYBINDINGS[str(note)](byte_signal)

    elif is_holdbinding:
        HOLD_BINDINGS[str(note)](byte_signal)

    elif is_automap:
        key = str(note) if is_automap_binding else 'default'
        AUTOMAP[key](byte_signal=byte_signal)

    else:
        color_button(byte_signal=byte_signal)
        print(note)


if __name__ == '__main__':
    # pylint: disable=no-member
    midiout = rtmidi.MidiOut()
    midiin = rtmidi.MidiIn()

    activate_ports()
    boot_sequence()

    try:
        while True:
            update()
            time.sleep(APPLICATION_REFRESH_TIME)
    except KeyboardInterrupt:
        midiout.send_message(RESET_LIGHT_SIGNAL)
        del midiin, midiout
