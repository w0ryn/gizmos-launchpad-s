import time
import os

from math import floor
from subprocess import call

import rtmidi

LAUNCHPAD_COLS = 9
LAUNCHPAD_ROWS  = 8

GLOBAL_FLASH_TIME = 0.5
GLOBAL_FLASH_CYCLE = GLOBAL_FLASH_TIME
GLOBAL_CURRENT_FLASH_ON = True

GLOBAL_SLEEP_LOOP = 0.25


MAX_OUTPUT_VOLUME = 120
MAX_OUTPUT_LEVEL = LAUNCHPAD_COLS - 1

MAX_INPUT_VOLUME = 140
MAX_INPUT_LEVEL = LAUNCHPAD_COLS - 1


################################################################
### Colors and Basic Messages ##################################
################################################################
COLORS = {
    # Colors are combinations of red and green:
    # 0b00GG11RR
    'OFF'          : 0b00001100,

    'LOW_GREEN'    : 0b00011100,
    'MEDIUM_GREEN' : 0b00101100,
    'BRIGHT_GREEN' : 0b00111100,

    'LOW_RED'      : 0b00001101,
    'MEDIUM_RED'   : 0b00001110,
    'BRIGHT_RED'   : 0b00001111,

    'LOW_AMBER'    : 0b00011101,
    'MEDIUM_AMBER' : 0b00101110,
    'BRIGHT_AMBER' : 0b00111111,

    'MEDIUM_ORANGE': 0b00011110,
    'BRIGHT_ORANGE': 0b00101111,
    'RED_ORANGE'   : 0b00011111,

    'MEDIUM_YELLOW': 0b00101101,
    'BRIGHT_YELLOW': 0b00111110,
    'YELLOW_GREEN' : 0b00111101,
}

RESET_LIGHT_SIGNAL = [0xb0, 0x00, 0x00]

LIGHT_ON  = 0x90
LIGHT_OFF = 0x80

AUTOMAP_ON = 0xb0

BUTTON_COLORS = {
    '16': ['BRIGHT_ORANGE', 'MEDIUM_AMBER'],
    '32': ['BRIGHT_ORANGE', 'MEDIUM_AMBER'],
    '33': ['BRIGHT_ORANGE', 'MEDIUM_AMBER'],
    '48': ['BRIGHT_ORANGE', 'MEDIUM_AMBER'],
    'default': ['BRIGHT_RED', 'LOW_RED'],
}

def button_color(byte_signal=None, note=None, button_colors=None):
    note = note if note is not None else byte_signal[0][1]

    if button_colors is None:
        button_colors = BUTTON_COLORS.get(str(note), BUTTON_COLORS['default'])

    color = COLORS[
        button_colors[0] if is_keydown(byte_signal) else button_colors[1]
    ]

    midiout.send_message([LIGHT_ON, note, color])

AUTOMAP_COLORS = {
    '104': ['BRIGHT_GREEN', 'MEDIUM_YELLOW'],
    '105': ['BRIGHT_AMBER', 'MEDIUM_YELLOW'],
    '111': ['BRIGHT_RED', 'MEDIUM_ORANGE'],
    'default': [ 'YELLOW_GREEN', 'LOW_GREEN' ],
}

def automap_color(byte_signal, force_default=False):
    note = byte_signal[0][1]

    automap_colors = AUTOMAP_COLORS.get(
        'default' if force_default else str(note),
        AUTOMAP_COLORS['default']
    )

    color = COLORS[
        automap_colors[0] if is_keydown(byte_signal) else automap_colors[1]
    ]

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

def hold_key(byte_signal, key):
    # pylint: disable=expression-not-assigned
    keydown(key) if is_keydown(byte_signal) else keyup(key)
    button_color(byte_signal)

def keydown(key):
    call(['xdotool', 'keydown', key])
    return True

def keyup(key):
    call(['xdotool', 'keyup', key])
    return False


is_keydown = lambda byte_signal: byte_signal[0][2] == 127
is_automap_key = lambda byte_signal: byte_signal[0][0] == 176

midi_signal = lambda note=0, on=True: [[0,note,127 if on else 0]]



################################################################
### Keybindings and Keybound Actions ###########################
################################################################


AUTOMAP = {} # automap row is handled differently from other rows
HOLD_BINDINGS = {} # handles both keyup / keydown
KEYBINDINGS = {} # only triggered on keydown

HOLD_BINDINGS['16'] = lambda byte_signal: hold_key(byte_signal, 'Left')
HOLD_BINDINGS['32'] = lambda byte_signal: hold_key(byte_signal, 'Down')
HOLD_BINDINGS['33'] = lambda byte_signal: hold_key(byte_signal, 'Up')
HOLD_BINDINGS['48'] = lambda byte_signal: hold_key(byte_signal, 'Right')

def pulse_default_source_volume_control(level, set_volume=True):
    level = MAX_INPUT_LEVEL if level > MAX_INPUT_LEVEL else level

    INDICES = { 'main': [80, 88], 'staggered': [64, 71] }

    DEFAULT_COLOR = 'LOW_RED'

    COLOR_BY_LEVEL = [
        'MEDIUM_RED', 'MEDIUM_RED',
        'MEDIUM_AMBER', 'MEDIUM_AMBER', 'MEDIUM_AMBER',
        'BRIGHT_AMBER', 'BRIGHT_AMBER',
        'BRIGHT_YELLOW', 'BRIGHT_YELLOW',
    ]

    NO_VOLUME_COLOR = 'BRIGHT_AMBER'

    messages = []

    if set_volume:
        volume = '{0}%'.format(floor(MAX_INPUT_VOLUME * level/MAX_INPUT_LEVEL))
        call(['pactl', 'set-source-volume', '@DEFAULT_SOURCE@', volume])

    for x in range(level + 1):
        main_index = INDICES['main'][0] + x
        staggered_index = fix_value_to_bounds(
            INDICES['staggered'][0] + x - 1,
            INDICES['staggered'][0],
            INDICES['staggered'][1],
        )

        color = COLOR_BY_LEVEL[x] if level > 0 else NO_VOLUME_COLOR

        button_color([[0, main_index, 127]], button_colors=[color, DEFAULT_COLOR])
        button_color([[0, staggered_index, 127]], button_colors=[color, DEFAULT_COLOR])

    for x in range(MAX_INPUT_LEVEL - level):
        main_index = INDICES['main'][1] - x
        staggered_index = fix_value_to_bounds(
            INDICES['staggered'][1] - x,
            INDICES['staggered'][0] + 1,
            INDICES['staggered'][1],
        )

        button_color([[0, main_index, 0]], button_colors=[None, DEFAULT_COLOR])
        button_color([[0, staggered_index, 0]], button_colors=[None, DEFAULT_COLOR])

    for message in messages:
        midiout.send_message(message)

def pulse_default_source_toggle(toggle=True):
    ACTIVE_COLOR = 'BRIGHT_RED'
    MUTE_COLOR = 'LOW_AMBER'

    cmd = 'amixer -D pulse get Capture | grep -q off && echo 1'
    is_muted = bool(os.popen(cmd).read())

    if toggle:
        call(['amixer', '-D', 'pulse', 'set', 'Capture', 'toggle'])
        is_muted = not is_muted

    signal = LIGHT_ON if is_muted or GLOBAL_CURRENT_FLASH_ON else LIGHT_OFF
    color = MUTE_COLOR if is_muted else ACTIVE_COLOR
    midiout.send_message([signal, 72, COLORS[color]])

KEYBINDINGS['64'] = lambda byte_signal: pulse_default_source_volume_control(0)
KEYBINDINGS['65'] = lambda byte_signal: pulse_default_source_volume_control(1)
KEYBINDINGS['66'] = lambda byte_signal: pulse_default_source_volume_control(2)
KEYBINDINGS['67'] = lambda byte_signal: pulse_default_source_volume_control(3)
KEYBINDINGS['68'] = lambda byte_signal: pulse_default_source_volume_control(4)
KEYBINDINGS['69'] = lambda byte_signal: pulse_default_source_volume_control(5)
KEYBINDINGS['70'] = lambda byte_signal: pulse_default_source_volume_control(6)
KEYBINDINGS['71'] = lambda byte_signal: pulse_default_source_volume_control(7)
KEYBINDINGS['72'] = lambda byte_signal: pulse_default_source_toggle()

KEYBINDINGS['80'] = KEYBINDINGS['64']
KEYBINDINGS['81'] = KEYBINDINGS['65']
KEYBINDINGS['82'] = KEYBINDINGS['66']
KEYBINDINGS['83'] = KEYBINDINGS['67']
KEYBINDINGS['84'] = KEYBINDINGS['68']
KEYBINDINGS['85'] = KEYBINDINGS['69']
KEYBINDINGS['86'] = KEYBINDINGS['70']
KEYBINDINGS['87'] = KEYBINDINGS['71']
KEYBINDINGS['88'] = lambda byte_signal: pulse_default_source_volume_control(8)

def system_default_output_volume_control(level, set_volume=True):
    level = MAX_OUTPUT_LEVEL if level > MAX_OUTPUT_LEVEL else level

    INDICES = { 'main': [96, 104], 'staggered': [112, 119] }

    COLOR_BY_LEVEL = [
        'BRIGHT_GREEN', 'BRIGHT_GREEN', 'BRIGHT_GREEN', 'BRIGHT_GREEN',
        'YELLOW_GREEN', 'YELLOW_GREEN',
        'BRIGHT_YELLOW',
        'BRIGHT_RED', 'BRIGHT_RED',
    ]

    DEFAULT_COLOR = 'LOW_RED'
    NO_VOLUME_COLOR = 'BRIGHT_RED'

    messages = []

    if set_volume:
        volume = '{0}%'.format(floor(MAX_OUTPUT_VOLUME * level/MAX_OUTPUT_LEVEL))
        call(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', volume])

    for x in range(level + 1):
        main_index = INDICES['main'][0] + x
        staggered_index = fix_value_to_bounds(
            INDICES['staggered'][0] + x - 1,
            INDICES['staggered'][0],
            INDICES['staggered'][1],
        )

        color = COLOR_BY_LEVEL[x] if level > 0 else NO_VOLUME_COLOR

        button_color([[0, main_index, 127]], button_colors=[color, DEFAULT_COLOR])
        button_color([[0, staggered_index, 127]], button_colors=[color, DEFAULT_COLOR])

    for x in range(MAX_OUTPUT_LEVEL - level):
        main_index = INDICES['main'][1] - x
        staggered_index = fix_value_to_bounds(
            INDICES['staggered'][1] - x,
            INDICES['staggered'][0] + 1,
            INDICES['staggered'][1],
        )

        color = None
        button_color([[0, main_index, 0]], button_colors=[color, DEFAULT_COLOR])
        button_color([[0, staggered_index, 0]], button_colors=[color, DEFAULT_COLOR])


    for message in messages:
        midiout.send_message(message)

def system_default_output_toggle(toggle=True):
    ACTIVE_COLOR = 'BRIGHT_GREEN'
    MUTE_COLOR = 'LOW_GREEN'

    cmd = 'amixer -D pulse get Master | grep -q off && echo 1'
    is_muted = bool(os.popen(cmd).read())

    if toggle:
        call(['amixer', '-D', 'pulse', 'set', 'Master', 'toggle'])
        is_muted = not is_muted

    color = MUTE_COLOR if is_muted else ACTIVE_COLOR
    midiout.send_message([LIGHT_ON, 120, COLORS[color]])

KEYBINDINGS['96']  = lambda byte_signal: system_default_output_volume_control(0)
KEYBINDINGS['97']  = lambda byte_signal: system_default_output_volume_control(1)
KEYBINDINGS['98']  = lambda byte_signal: system_default_output_volume_control(2)
KEYBINDINGS['99']  = lambda byte_signal: system_default_output_volume_control(3)
KEYBINDINGS['100'] = lambda byte_signal: system_default_output_volume_control(4)
KEYBINDINGS['101'] = lambda byte_signal: system_default_output_volume_control(5)
KEYBINDINGS['102'] = lambda byte_signal: system_default_output_volume_control(6)
KEYBINDINGS['103'] = lambda byte_signal: system_default_output_volume_control(7)
KEYBINDINGS['104'] = lambda byte_signal: system_default_output_volume_control(8)

KEYBINDINGS['112'] = KEYBINDINGS['96']
KEYBINDINGS['113'] = KEYBINDINGS['97']
KEYBINDINGS['114'] = KEYBINDINGS['98']
KEYBINDINGS['115'] = KEYBINDINGS['99']
KEYBINDINGS['116'] = KEYBINDINGS['100']
KEYBINDINGS['117'] = KEYBINDINGS['101']
KEYBINDINGS['118'] = KEYBINDINGS['102']
KEYBINDINGS['119'] = KEYBINDINGS['103']
KEYBINDINGS['120'] = lambda byte_signal: system_default_output_toggle()

def automap_104(byte_signal):
    if is_keydown(byte_signal):
        automap_color(
            midi_signal(
                note=byte_signal[0][1],
                on=num_lock(toggle=True),
            )
        )

def automap_105(byte_signal):
    if is_keydown(byte_signal):
        automap_color(
            midi_signal(
                note=byte_signal[0][1],
                on=caps_lock(toggle=True),
            )
        )


def automap_111(byte_signal):
    restart_pulse_audio()
    automap_color(byte_signal)

AUTOMAP['default'] = automap_color
AUTOMAP['104'] = automap_104
AUTOMAP['105'] = automap_105
AUTOMAP['111'] = automap_111

################################################################
### Light Sequences ############################################
################################################################

def boot_sequence():
    sleep_time = 0.01
    multiplier = .99
    pause_time = 0.5

    automap_signal = lambda x: [[AUTOMAP_ON, 104 + x, 0]]
    button_signal = lambda x: [[LIGHT_ON, x, 0]]

    for x in range(LAUNCHPAD_COLS - 1):
        automap_color(automap_signal(x), force_default=True)
        time.sleep(sleep_time)
        sleep_time *= multiplier

    for x in range(LAUNCHPAD_ROWS * LAUNCHPAD_COLS):
        index = floor(x/LAUNCHPAD_COLS)*16 + x%LAUNCHPAD_COLS
        button_color(button_signal(index), button_colors=BUTTON_COLORS['default'])
        time.sleep(sleep_time)
        sleep_time *= multiplier

    time.sleep(pause_time)

    # load actual color settings
    for x in range(LAUNCHPAD_COLS - 1):
        automap_color(automap_signal(x))
    for x in range(LAUNCHPAD_ROWS*LAUNCHPAD_COLS):
        if not str(x) in KEYBINDINGS.keys():
            button_color(button_signal(x))


################################################################
### Persistent Updates #########################################
################################################################

def update():
    update_global_flash_cycle()
    update_output_volume_visual()
    update_input_volume_visual()
    update_key_lock_visual()

def update_global_flash_cycle():
    # pylint: disable=global-statement
    global GLOBAL_FLASH_CYCLE, GLOBAL_CURRENT_FLASH_ON,\
           GLOBAL_SLEEP_LOOP, GLOBAL_FLASH_TIME

    GLOBAL_FLASH_CYCLE -= GLOBAL_SLEEP_LOOP

    if GLOBAL_FLASH_CYCLE < 0:
        GLOBAL_CURRENT_FLASH_ON = not GLOBAL_CURRENT_FLASH_ON
        GLOBAL_FLASH_CYCLE = GLOBAL_FLASH_TIME


def update_output_volume_visual():
    cmd = 'amixer -D pulse sget Master | grep "Front Left:" | sed "s/^.*\\[\\(.*\\)%.*$/\\1/" || return 0'
    volume = os.popen(cmd).read()
    if volume:
        volume = int(volume)
        level = floor(
            round(volume / MAX_OUTPUT_VOLUME * MAX_OUTPUT_LEVEL)
        )

        system_default_output_volume_control(level, set_volume=False)
        system_default_output_toggle(toggle=False)

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
    automap_color(midi_signal(note=104, on=num_lock()))

def update_caps_lock_visual():
    automap_color(midi_signal(note=105, on=caps_lock()))


################################################################
### Application Loop ###########################################
################################################################

def input_callback(midi_in, dump):
    # @TODO: remove debug print
    if dump is not None:
        print(dump)

    note = midi_in[0][1]

    is_automap = is_automap_key(midi_in)
    is_keybinding = not is_automap and str(note) in KEYBINDINGS.keys()
    is_holdbinding = not is_automap and str(note) in HOLD_BINDINGS.keys()
    is_automap_binding = is_automap and str(note) in AUTOMAP.keys()

    if is_keybinding:
        if is_keydown(midi_in):
            KEYBINDINGS[str(note)](midi_in)

    elif is_holdbinding:
        HOLD_BINDINGS[str(note)](midi_in)

    elif is_automap:
        key = str(note) if is_automap_binding else 'default'
        AUTOMAP[key](midi_in)

    else:
        button_color(midi_in)
        print(note)


if __name__ == '__main__':
    # pylint: disable=no-member
    midiout = rtmidi.MidiOut()
    available_out = midiout.get_ports()
    midiout.open_port(1)

    midiin = rtmidi.MidiIn()
    available_in = midiin.get_ports()
    midiin.open_port(1)

    midiin.set_callback(input_callback)

    midiout.send_message(RESET_LIGHT_SIGNAL)
    boot_sequence()


    try:
        while True:
            update()
            time.sleep(GLOBAL_SLEEP_LOOP)
    except KeyboardInterrupt:
        midiout.send_message(RESET_LIGHT_SIGNAL)
        del midiin, midiout
