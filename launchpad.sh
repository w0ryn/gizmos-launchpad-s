#!/bin/sh

CONSOLE_MESSAGE='Launchpad Driver'


REQUIREMENT_ERROR="I require %s but it's not installed. (%s)\n\n";
REQUIREMENT_ERROR_CODE=1;

function CHECK_REQUIREMENT() {
	ERROR_CODE=0;

	command -v "$1" >/dev/null 2>&1\
		|| { ERROR_CODE="$REQUIREMENT_ERROR_CODE"; printf "$REQUIREMENT_ERROR" "$1" "$2" >&2; };

	return $ERROR_CODE;
}


LINK_AMIDI='';
LINK_XDOTOOL='';
LINK_AMIXER='';
LINK_PACTL='';

CHECK_REQUIREMENT 'amidi'   $LINK_AMIDI;
CHECK_REQUIREMENT 'xdotool' $LINK_XDOTOOL;
CHECK_REQUIREMENT 'amixer'  $LINK_AMIXER;
CHECK_REQUIREMENT 'pactl'   $LINK_PACTL;

[ $ERROR_CODE -ne 0 ] && exit $ERROR_CODE;


#MIDI_PORT='hw:2,0,0';
#RESET_LAUNCHPAD_BYTES='B0 00 00'
#
#amidi --port="$MIDI_PORT" -S "$RESET_LAUNCHPAD_BYTES"

clear
command -v figlet >/dev/null 2>&1 && {
	command -v lolcat >/dev/null 2>&1 && {
		figlet "$CONSOLE_MESSAGE" | lolcat;
	} || {
		figlet "$CONSOLE_MESSAGE";
	}
} || {
	command -v lolcat >/dev/null 2>&1 && {
		echo -e "\n$CONSOLE_MESSAGE\n" | lolcat;
	} || {
		echo -e "\n$CONSOLE_MESSAGE\n";
	}
}

echo -e "\e[3m(C-c to exit)\e[0m"

python $(dirname "$0")/rtmidi-launchpad.py >/dev/null 2>&1;
