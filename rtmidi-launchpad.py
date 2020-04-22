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

ON_SIGNAL = [[0,0,127]]

MAX_OUTPUT_VOLUME = 120
MAX_OUTPUT_LEVEL = LAUNCHPAD_COLS - 1

MAX_INPUT_VOLUME = 120
MAX_INPUT_LEVEL = LAUNCHPAD_COLS - 1


################################################################
### Colors and Basic Messages ##################################
################################################################
LIGHT_ON  = 0x90
LIGHT_OFF = 0x80

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
DEFAULT_COLOR = COLORS['LOW_RED']

################################################################
### Keybindings and Keybound Actions ###########################
################################################################

is_keydown = lambda byte_signal: byte_signal[0][2] == 127

HOLD_BINDINGS = {} # handles both keyup / keydown
KEYBINDINGS = {} # only triggered on keydown

def fix_value_to_bounds(val, lower, upper):
    if val < lower:
        return lower

    if val > upper:
        return upper

    return val


def system_default_input_volume_control(level, set_volume=True):
    level = MAX_INPUT_LEVEL if level > MAX_INPUT_LEVEL else level

    INDICES = { 'main': [80, 88], 'staggered': [64, 71] }

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

        messages.append([LIGHT_ON, main_index, COLORS[color]])
        messages.append([LIGHT_ON, staggered_index, COLORS[color]])

    for x in range(MAX_INPUT_LEVEL - level):
        main_index = INDICES['main'][1] - x
        staggered_index = fix_value_to_bounds(
            INDICES['staggered'][1] - x,
            INDICES['staggered'][0] + 1,
            INDICES['staggered'][1],
        )

        messages.append([LIGHT_ON, main_index, DEFAULT_COLOR])
        messages.append([LIGHT_ON, staggered_index, DEFAULT_COLOR])

    for message in messages:
        midiout.send_message(message)

def system_default_input_toggle(toggle=True):
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

KEYBINDINGS['64'] = lambda byte_signal: system_default_input_volume_control(0)
KEYBINDINGS['65'] = lambda byte_signal: system_default_input_volume_control(1)
KEYBINDINGS['66'] = lambda byte_signal: system_default_input_volume_control(2)
KEYBINDINGS['67'] = lambda byte_signal: system_default_input_volume_control(3)
KEYBINDINGS['68'] = lambda byte_signal: system_default_input_volume_control(4)
KEYBINDINGS['69'] = lambda byte_signal: system_default_input_volume_control(5)
KEYBINDINGS['70'] = lambda byte_signal: system_default_input_volume_control(6)
KEYBINDINGS['71'] = lambda byte_signal: system_default_input_volume_control(7)
KEYBINDINGS['72'] = lambda byte_signal: system_default_input_toggle()

KEYBINDINGS['80'] = KEYBINDINGS['64']
KEYBINDINGS['81'] = KEYBINDINGS['65']
KEYBINDINGS['82'] = KEYBINDINGS['66']
KEYBINDINGS['83'] = KEYBINDINGS['67']
KEYBINDINGS['84'] = KEYBINDINGS['68']
KEYBINDINGS['85'] = KEYBINDINGS['69']
KEYBINDINGS['86'] = KEYBINDINGS['70']
KEYBINDINGS['87'] = KEYBINDINGS['71']
KEYBINDINGS['88'] = lambda byte_signal: system_default_input_volume_control(8)

def system_default_output_volume_control(level, set_volume=True):
    level = MAX_OUTPUT_LEVEL if level > MAX_OUTPUT_LEVEL else level

    INDICES = { 'main': [96, 104], 'staggered': [112, 119] }

    COLOR_BY_LEVEL = [
        'BRIGHT_GREEN', 'BRIGHT_GREEN', 'BRIGHT_GREEN', 'BRIGHT_GREEN',
        'YELLOW_GREEN', 'YELLOW_GREEN',
        'BRIGHT_YELLOW',
        'BRIGHT_RED', 'BRIGHT_RED',
    ]

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

        messages.append([LIGHT_ON, main_index, COLORS[color]])
        messages.append([LIGHT_ON, staggered_index, COLORS[color]])

    for x in range(MAX_OUTPUT_LEVEL - level):
        main_index = INDICES['main'][1] - x
        staggered_index = fix_value_to_bounds(
            INDICES['staggered'][1] - x,
            INDICES['staggered'][0] + 1,
            INDICES['staggered'][1],
        )

        messages.append([LIGHT_ON, main_index, DEFAULT_COLOR])
        messages.append([LIGHT_ON, staggered_index, DEFAULT_COLOR])

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

def reset_colors():
    for x in range(LAUNCHPAD_ROWS * LAUNCHPAD_COLS):
        midiout.send_message(
            [LIGHT_ON, floor(x/LAUNCHPAD_COLS)*16 + x%LAUNCHPAD_COLS, DEFAULT_COLOR]
        )
        time.sleep(0.01)
    time.sleep(0.5)


################################################################
### Persistent Updates #########################################
################################################################

def update():
    update_global_flash_cycle()
    update_output_volume_visual()
    update_input_volume_visual()

def update_global_flash_cycle():
    global GLOBAL_FLASH_CYCLE, GLOBAL_CURRENT_FLASH_ON,\
           GLOBAL_SLEEP_LOOP, GLOBAL_FLASH_TIME

    GLOBAL_FLASH_CYCLE -= GLOBAL_SLEEP_LOOP

    if GLOBAL_FLASH_CYCLE < 0:
        GLOBAL_CURRENT_FLASH_ON = not GLOBAL_CURRENT_FLASH_ON
        GLOBAL_FLASH_CYCLE = GLOBAL_FLASH_TIME


def update_output_volume_visual():
    cmd = 'amixer -D pulse sget Master | grep "Front Left:" | sed "s/^.*\\[\\(.*\\)%.*$/\\1/" || return 0'
    volume = int(os.popen(cmd).read())
    level = floor( volume / MAX_OUTPUT_VOLUME * MAX_OUTPUT_LEVEL)

    system_default_output_volume_control(level, set_volume=False)
    system_default_output_toggle(toggle=False)

def update_input_volume_visual():
    cmd = 'amixer -D pulse sget Capture | grep "Front Left:" | sed "s/^.*\\[\\(.*\\)%.*$/\\1/" || return 0'
    volume = int(os.popen(cmd).read())
    level = floor( volume / MAX_INPUT_VOLUME * MAX_INPUT_LEVEL)

    system_default_input_volume_control(level, set_volume=False)
    system_default_input_toggle(toggle=False)



if __name__ == '__main__':
    midiout = rtmidi.MidiOut()
    available_out = midiout.get_ports()
    midiout.open_port(1)
    
    midiin = rtmidi.MidiIn()
    available_in = midiin.get_ports()
    midiin.open_port(1)

    midiout.send_message(RESET_LIGHT_SIGNAL)

    reset_colors()

    def input_callback(midi_in, dump):
        if dump is not None:
            print(dump)

        color = COLORS['BRIGHT_RED'] if midi_in[0][2] == 127 else DEFAULT_COLOR
        note = midi_in[0][1]

        if str(note) in KEYBINDINGS.keys():

            if is_keydown(midi_in):
                KEYBINDINGS[str(note)](midi_in)

        elif str(note) in HOLD_BINDINGS.keys():
            HOLD_BINDINGS[str(note)](midi_in)
        else:
            print(note)
            midiout.send_message([LIGHT_ON, note, color])

    midiin.set_callback(input_callback)


    try:
        while True:
            update()
            time.sleep(GLOBAL_SLEEP_LOOP)
    except KeyboardInterrupt:
        midiout.send_message(RESET_LIGHT_SIGNAL)
        del midiin, midiout
