#!/bin/sh


REQUIREMENT_ERROR="I require %s but it's not installed. (%s)\n\n";
REQUIREMENT_ERROR_CODE=1;

LINK_XDOTOOL='';

ERROR_CODE=0;

command -v xdotool >/dev/null 2>&1\
	|| { ERROR_CODE="$REQUIREMENT_ERROR_CODE"; printf "$REQUIREMENT_ERROR" 'xdotool' "$LINK_XDOTOOL" >&2; };


function RETURN_MIDI_EVENTS() {
	return 0
}

function TRIGGER_KEY_EVENTS() {
	aseqdump -p "Launchpad S" | \
		while IFS=" ," read src ev1 ev2 ch label1 data1 label2 data2 rest; do
			case "$ev1 $ev2 $data1" in
				"Note on 112" ) xdotool type hello ;;
			esac
		done
}


RETURN_MIDI_EVENTS &
TRIGGER_KEY_EVENTS &
