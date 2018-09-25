from microbit import * 
import music

WORD_LIMIT = 20

EOL = "\n"

DASH_TIME = 1200/10 * 3		  # Duration of ideal dash mark
MARK_SPACE =  1200/10			 # Time between marks
SIGNAL_SPACE = 1200/10 * 3	     # Time between letters
WORD_SPACE = 1200/10 * 7		 # Time between words

""" Following thresholds are used to detect input """
DOT_TIME_MIN =  1200/10/4		 # Minimum dot duration
DOT_TIME_MAX = DASH_TIME/2		# Maximum dot duration

DASH_TIME_MIN = DOT_TIME_MAX				# Min dash duration
DASH_TIME_MAX = DASH_TIME + (1200/10 * 2)  # Max dash duration

SIGNAL_SPACE_MIN = SIGNAL_SPACE * 2
SIGNAL_SPACE_MAX = WORD_SPACE * 2  # Max duration between letters
WORD_SPACE_MIN = SIGNAL_SPACE_MAX  # Min duration between words

# Characters for dot, dash, space
DOT = "."   
DASH = "-"  
SPACE = " "
WORD = "|"

""" LED matrix images of dots, dashes, and over time """
DOT_IMAGE = Image.DIAMOND_SMALL
DASH_IMAGE = Image.DIAMOND
OVER_TIME_IMAGE = Image.CONFUSED

TONE_PITCH = 800  # Frequency to play through speaker

''' State and timers to derive button input '''
mark_has_begun = False			 # State when key pressed
mark_start_time = running_time()   # Used to derive dot or dash
space_has_begun = False			# State when key let up
space_start_time = running_time()  # Used to derive space
message = list()  # List accumulates Dots, Dashes, and Spaces 

is_serial_receive_mode = False

def not_at_max_message_length():
	""" Indicates if we have room left in message """
	global message
	return message.count(SPACE) < WORD_LIMIT

def clear_extra_space():
	""" remove extra space at list front """
	global message
	if len(message) == 1 and message[0] == SPACE:
		message.clear()

def display_dot_dash():
	""" based on time interval, display appropriate image """
	mark_interval = running_time() - mark_start_time

	if mark_interval < DOT_TIME_MAX:
		display.show(DOT_IMAGE) 
	elif mark_interval >= DASH_TIME_MIN and mark_interval < DASH_TIME_MAX:
		display.show(DASH_IMAGE)
	elif mark_interval >= DASH_TIME_MAX:
		display.show(OVER_TIME_IMAGE)

def process_mark_time():
	""" Determine if DOT or DASH timing has elapsed """
	global mark_has_begun, mark_start_time
	if not mark_has_begun: return

	clear_extra_space()

	mark_interval = running_time() - mark_start_time

	if mark_interval > DOT_TIME_MIN and mark_interval < DOT_TIME_MAX:
		message.append(DOT)
		space_start_time = running_time() 
	elif mark_interval > DASH_TIME_MIN and mark_interval < DASH_TIME_MAX:
		message.append(DASH)
		space_start_time = running_time() 

	mark_has_begun = False
	
def message_has_first_mark():
	""" Message list contains at lease one dot or dash """
	return len(message) > 0 and message[0] != SPACE

def process_space_time():
	""" Determines if enough time has elapsed to generate a space """
	global space_has_begun, space_start_time, mark_start_time
	if not message_has_first_mark(): return

	if not space_has_begun:
		space_start_time = running_time() 
		return  

	space_interval = running_time() - space_start_time
	if space_interval > SIGNAL_SPACE_MIN and space_interval < SIGNAL_SPACE_MAX:
		# Don't put two spaces in a row
		if len(message) > 0 and not message[len(message)-1] == SPACE and not message[len(message)-1] == SPACE:
			message.append(SPACE)		
	if space_interval > WORD_SPACE_MIN:
		# Don't put two spaces in a row
		if len(message) > 0 and not message[len(message)-1] == WORD:
			message.append(WORD)

	space_has_begun = False

def encode_keyed_morse_code():
	""" Depending on button state, encode keys to marks """
	global mark_has_begun, mark_start_time, message, space_start_time, space_has_begun

	button_pressed = button_a.is_pressed()  

	if button_pressed:
		if not mark_has_begun:
			mark_start_time = running_time() 
			mark_has_begun = True

		display_dot_dash()
		music.pitch(TONE_PITCH,duration=-1,wait=False)

		if not_at_max_message_length():
			process_space_time()
	else:  # not button_pressed
		display.clear() 
		music.stop() 

		if not space_has_begun:
			space_start_time = running_time() 
			space_has_begun = True
		if not_at_max_message_length():
			process_mark_time()

def display_character(character):
	""" Display Dot, Dash, or Space images on LED Matrix """
	if character == DASH:
		display.show(DASH_IMAGE)
		music.pitch(TONE_PITCH,duration=int(round(DASH_TIME)),wait=True)
		display.clear()
		sleep(MARK_SPACE)

	if character == DOT:
		display.show(DOT_IMAGE)
		music.pitch(TONE_PITCH,duration=int(round(1200/10)),wait=True)
		display.clear()
		sleep(MARK_SPACE)

	if character == SPACE:
		display.clear() 
		sleep(WORD_SPACE)


def process_incoming_serial_data():
	""" gets comma delimited data from serial applies changes appropriately """
	global message, is_serial_receive_mode
	parsed_data = ""
	while uart.any() is True and not parsed_data.endswith('\n'): 
		parsed_data += str(uart.read(), "utf-8", "ignore")
		sleep(10)

	if parsed_data:
		uart.write("parsed {}".format(parsed_data.split(',')) + EOL)
		try:
			is_serial_receive_mode = ("1" == parsed_data.split(',')[0]) # TODO do we need to do anything with serial_mode??
			serial_message_str = parsed_data.split(',')[1]

			if parsed_data.split(',')[2]:
				message.clear()

			if serial_message_str and len(serial_message_str) > 0 and is_serial_receive_mode:
				for character in serial_message_str:
					uart.write(character+EOL)
					display_character(character)

		except IndexError:
			return

	
uart.init(baudrate=9600) 
uart.write(",,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,"+EOL)
last_message_length = 0

while True: 
	if not is_serial_receive_mode: encode_keyed_morse_code()
	process_incoming_serial_data()
	if last_message_length != len(message) and not is_serial_receive_mode:
		for character in message:
			if character == SPACE:
				uart.write(",")
			elif character == WORD:
				uart.write(", ,")
			else:
				uart.write(character)

		uart.write(EOL)		 
		last_message_length = len(message)