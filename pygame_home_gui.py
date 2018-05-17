#---------------------------------------------
# Written by: Patrick Wang (pw349)
#             Shaurya Luthra (sl2462)
#---------------------------------------------

# import libs
import logging
import sys, os, pygame
import time, math
import RPi.GPIO as GPIO
import datetime

# Uncomment to run on piTFT
os.putenv('SDL_VIDEODRIVER', 'fbcon') # Display on piTFT
os.putenv('SDL_FBDEV', '/dev/fb1')
os.putenv('SDL_MOUSEDRV', 'TSLIB') # Track mouse clicks on piTFT
os.putenv('SDL_MOUSEDEV', '/dev/input/touchscreen')

# colors
black = 0, 0, 0
cyan = 50, 204, 255
navy = 34, 51, 68
gray = 160, 160, 160
red = 255, 50, 50
green=17,234,79

####################################
# GPIO Setup
####################################

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)

quit=0; # quit flag
state = 0 # 0 is home, 1 is zwave, 2 is alarm
# callbacks
# quit when button press detected
def GPIO_17_callback(channel):
    global state
    state = 0
def GPIO_27_callback(channel):
    global quit
    quit = 1
def GPIO_22_callback(channel):
    alarm_tone.stop()

GPIO.add_event_detect(17,GPIO.FALLING,callback=GPIO_17_callback,bouncetime=300)
GPIO.add_event_detect(27,GPIO.FALLING,callback=GPIO_27_callback,bouncetime=300)
GPIO.add_event_detect(22,GPIO.FALLING,callback=GPIO_22_callback,bouncetime=300)

####################################
# Init pygame
####################################
pygame.init()
pygame.mixer.init()
alarm_tone= pygame.mixer.Sound(os.path.normcase("/home/pi/Embedded_OS/final/alarm_tones/gucci_gang.wav"))
pygame.mouse.set_visible(False) # toggle True for debugging

# Description:  Class for organizing Things
# Main Fields:
#       - node: Saved node for control and info
class Thing:
    def __init__(self, index, node, font, bigger_font):
        self.node = node
        self.index = index

        
        ##########################
        # State variables and data extraction
        ##########################
        self.level = 0 # 0- 10, represents 10% increments
        self.on = False

        # data extraction
        for val in node.get_switches():
            self.on = node.get_switch_state(val)

        for val in node.get_dimmers():
            self.level = int(node.get_dimmer_level(val)/10)

        # name extraction
        node_str = str(node)
        name_str = node_str[node_str.find('name'):node_str.find('] ', node_str.find('name'))]
        name_str = name_str[(name_str.find(':')+2):]
        node_name = name_str.strip('[]')

        model_str = node_str[node_str.rfind('model:'):]
        model_str = model_str[(model_str.find(':')+2):]
        node_model = model_str.strip('[]')

        self.name = node_name
        if (node_name == ''):    self.name = node_model

        ##########################
        # GUI components
        ##########################
        # name label things
        self.label_text = bigger_font.render(self.name, True, cyan, None)
        self.label_rect = self.label_text.get_rect(top=20, left=20)
        
        # dimmer things
        self.minus_surface = pygame.image.load(os.path.normcase("/home/pi/Embedded_OS/final/GUI_resources/minus_button.png"))
        self.minus_rect = self.minus_surface.get_rect(center=[85,135])

        self.plus_surface = pygame.image.load(os.path.normcase("/home/pi/Embedded_OS/final/GUI_resources/plus_button.png"))
        self.plus_rect = self.plus_surface.get_rect(center=[235,135])

        self.level_text = font.render(str(self.level*10), True, cyan, None)
        self.level_rect = self.level_text.get_rect(center=[160,135])

        self.level_back = pygame.Surface([200, 40])
        self.level_back.fill(gray)
        self.level_back_rect = self.level_back.get_rect(center=[160, 80])

        self.level_front =pygame.Surface([int(self.level*20), 40])
        self.level_front.fill(cyan)

        # switch things
        self.switch_surface = pygame.image.load(os.path.normcase("/home/pi/Embedded_OS/final/GUI_resources/power_button.png"))
        self.switch_rect = self.switch_surface.get_rect(center = [160, 100])

        # alarm select button
        self.select_back = pygame.Surface([60,60])
        self.select_back.fill(gray)
        self.select_rect = self.select_back.get_rect(center= [160, 100])

        self.select_front = pygame.Surface([40,40])
        self.select_front.fill(cyan)

    def draw(self, state, screen, font):
        # Draw label
        screen.blit(self.label_text, self.label_rect)

        # If state is zwave control, display controls
        if (state == 1):
            if (self.node.get_dimmers()):
                # draw buttons
                screen.blit(self.minus_surface, self.minus_rect)
                screen.blit(self.plus_surface, self.plus_rect)
                # update level indicator (text)
                self.level_text = font.render(str(self.level*10), True, cyan, None)
                screen.blit(self.level_text, self.level_rect)
                # update level indicator (bar)
                self.level_front = pygame.Surface([int(self.level*20), 40])
                self.level_front.fill(cyan)
                self.level_back.fill(gray)
                self.level_back.blit(self.level_front, (0,0))
                screen.blit(self.level_back, self.level_back_rect)
            if (self.node.get_switches()):
                screen.blit(self.switch_surface, self.switch_rect)

        # if called in alarm state, show selection element
        elif (state == 2):
            if (self.node.get_dimmers() or self.node.get_switches()):
                self.select_back.fill(gray)
                if (alarms[alarm_index].zindex == self.index):
                    self.select_back.blit(self.select_front, (10,10))
                screen.blit(self.select_back, self.select_rect)

    def check(self, state, x, y):
        # if zwave control state, handle control inputs
        if (state == 1):
            if (self.node.get_dimmers()):
                if (self.plus_rect.collidepoint(x,y)):
                    self.level = min(10, self.level+1)
                    print("dim to " + str(self.level*10))
                    for val in self.node.get_dimmers():
                        self.node.set_dimmer(val, self.level*10)

                if (self.minus_rect.collidepoint(x,y)):
                    self.level = max(0, self.level-1)
                    print("dim to " + str(self.level*10))
                    for val in self.node.get_dimmers():
                        self.node.set_dimmer(val, self.level*10)

            if (self.node.get_switches()):
                if (self.switch_rect.collidepoint(x,y)):
                    self.on = not(self.on)
                    print("switch pressed, set to: " + str(self.on))
                    for val in self.node.get_switches():
                        self.node.set_switch(val, self.on)

        # handle selection for alarm state
        elif (state == 2):
            global alarm_state
            if (self.node.get_dimmers() or self.node.get_switches()):
                if (alarms[alarm_index].zindex == self.index):
                    alarms[alarm_index].zindex = 0
                    alarm_state = 0
                else:
                    alarms[alarm_index].zindex = self.index
                    alarm_state = 0

class Alarm_class():
   
    def __init__(self,corner_x,corner_y):
        self.corner_x=corner_x
        self.corner_y=corner_y
        self.time="12:00"
        self.per="pm"
        self.on=False
        self.zindex=0
        self.time_rect=pygame.Rect(corner_x, corner_y, 180, 45)
        self.on_off_rect=pygame.Rect(corner_x+190, corner_y, 50, 45)
        self.z_rect=pygame.Rect(corner_x+250, corner_y, 50, 45)

    def draw(self,screen,main_font, on_off_font):
        text=main_font.render(self.time+" "+self.per, True, cyan, None)
        t_rect = text.get_rect()
        t_rect.center=self.time_rect.center
        screen.blit(text, t_rect)

        if(self.on):
            text=on_off_font.render("on", True, green, None)
        else:
            text=on_off_font.render("off", True, red, None)

        t_rect = text.get_rect()
        t_rect.center=self.on_off_rect.center
        screen.blit(text, t_rect)

####################################
# ZWave Config Stuff
####################################
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('openzwave')

import openzwave
from openzwave.node import ZWaveNode
from openzwave.value import ZWaveValue
from openzwave.scene import ZWaveScene
from openzwave.controller import ZWaveController
from openzwave.network import ZWaveNetwork
from openzwave.option import ZWaveOption

import time
import six

if six.PY3:
    from pydispatch import dispatcher
else:
    from louie import dispatcher

# Program options
device="/dev/ttyACM0"
log = "None"
sniff=300.0

# manager options
options = ZWaveOption(device, \
    user_path="/home/pi/Embedded_OS/final/zwave_cfg/", cmd_line="")
options.set_log_file("OZW_Log.log")
options.set_append_log_file(False)
options.set_console_output(False)
options.set_save_log_level(log)
options.set_logging(True)
options.lock()

# fill below with more useful things later
def louie_network_started(network):
    print("Hello from network : I'm started : homeid {:08x} - {} nodes were found.".format(network.home_id, network.nodes_count))

def louie_network_failed(network):
    print("Hello from network : can't load :(.")

def louie_network_ready(network):
    print("Hello from network : I'm ready : {} nodes were found.".format(network.nodes_count))
    print("Hello from network : my controller is : {}".format(network.controller))
    dispatcher.connect(louie_node_update, ZWaveNetwork.SIGNAL_NODE)
    dispatcher.connect(louie_value_update, ZWaveNetwork.SIGNAL_VALUE)

def louie_node_update(network, node):
    print("Hello from node : {}.".format(node))

def louie_value_update(network, node, value):
    print("Hello from value : {}.".format( value ))

#Create a network object
network = ZWaveNetwork(options, autostart=False)

# We connect to the louie dispatcher
dispatcher.connect(louie_network_started, ZWaveNetwork.SIGNAL_NETWORK_STARTED)
dispatcher.connect(louie_network_failed, ZWaveNetwork.SIGNAL_NETWORK_FAILED)
dispatcher.connect(louie_network_ready, ZWaveNetwork.SIGNAL_NETWORK_READY)

# Start the network
network.start()

# Wait for network
print("***** Waiting for network to become ready : ")
for i in range(0,90):
    if network.state>=network.STATE_READY:
        print("***** Network is ready")
        break
    else:
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(1.0)

time.sleep(5.0)

####################################
# GUI components
####################################
# params
size = width, height = 320, 240

# fonts
main_font = pygame.font.Font(None, 40)
small_font = pygame.font.Font(None, 30)
clk_font = pygame.font.Font(None, 80)
on_off_font = pygame.font.Font(None, 30)

# button objects
my_font = pygame.font.Font(None, 40)
back_img = pygame.image.load(os.path.normcase("/home/pi/Embedded_OS/final/GUI_resources/home.png"))
back_rect = back_img.get_rect()
back_rect.move(0,0)

left_rect = pygame.Rect(10, 180, 145, 50)
right_rect = pygame.Rect(165, 180, 145, 50)

# display rect
# screen
screen = pygame.display.set_mode(size)

####################################
# Thing instantiation
####################################
things_index = 0
things = []
for n in network.nodes:
    things.append(Thing(things_index, network.nodes[n], small_font, main_font))
    things_index += 1

things_index = 0

####################################
# Alarm Instantiation
####################################
alarms=[Alarm_class(10,12),Alarm_class(10,69),Alarm_class(10,126),Alarm_class(10,183)]
alarm_state = 0
alarm_index = 0

set_time=alarms[alarm_index].time
set_per =alarms[alarm_index].per
h1=int(set_time[0])
h0=int(set_time[1])
h=h1*10+h0
m1=int(set_time[3])
m0=int(set_time[4])

# Alarm setting GUI components
hu_rect = pygame.Rect(40, 10, 50, 50)
hd_rect = pygame.Rect(40, 120, 50, 50)
m10u_rect = pygame.Rect(130, 10, 50, 50)
m10d_rect = pygame.Rect(130, 120, 50, 50)
m1u_rect = pygame.Rect(190, 10, 50, 50)
m1d_rect = pygame.Rect(190, 120, 50, 50)
pu_rect = pygame.Rect(250, 10, 60, 50)
pd_rect = pygame.Rect(250, 120, 60, 50)

h1_rect=pygame.Rect(10, 60, 50, 60)
h0_rect=pygame.Rect(70, 60, 50, 60)
m1_rect=pygame.Rect(130, 60, 50, 60)
m0_rect=pygame.Rect(190, 60, 50, 60)

per_rect=pygame.Rect(250, 60, 60, 60)

def display_alarm():
    for alarm in alarms:
        alarm.draw(screen, main_font, on_off_font)

def display_set():
    h1_text = main_font.render(set_time[0], True, cyan, None)
    h0_text = main_font.render(set_time[1], True, cyan, None)
    m1_text = main_font.render(set_time[3], True, cyan, None)
    m0_text = main_font.render(set_time[4], True, cyan, None)
   
    per_text = main_font.render(set_per, True, cyan, None)

    h1_trect = h1_text.get_rect()
    h1_trect.center=(h1_rect.center[0],h1_rect.center[1])
    h0_trect = h0_text.get_rect()
    h0_trect.center=(h0_rect.center[0],h0_rect.center[1])
    m1_trect = m1_text.get_rect()
    m1_trect.center=(m1_rect.center[0],m1_rect.center[1])
    m0_trect = m0_text.get_rect()
    m0_trect.center=(m0_rect.center[0],m0_rect.center[1])
    per_trect = per_text.get_rect()
    per_trect.center=(per_rect.center[0],per_rect.center[1])

    screen.blit(h1_text, h1_trect)
    screen.blit(h0_text, h0_trect)
    screen.blit(m1_text, m1_trect)
    screen.blit(m0_text, m0_trect)
    screen.blit(per_text, per_trect)

def check_alarm():
    #NEED TO FIX FOR 00 time!!!!
    now = datetime.datetime.today()
       
    seconds = float(str(now)[17:26])

    dt = str(now)
    hr=dt[11:13]
    if (hr == '00'):
        hr = '12'
    mins=dt[14:16]

    if (int(hr)>12):
        if(int(hr)-12<10):
            clock="0"+str(int(hr)-12)
        else:
            clock=str(int(hr)-12)

        clock+=":"+mins+" pm"
    else:
        clock=hr+":"+mins+" am"
    
    for alarm in alarms:
       
        if (alarm.time+" "+alarm.per==clock and alarm.on == True):
            alarm_tone.play()
            if (alarm.zindex!=0):
                t = things[alarm.zindex]
                if (t.node.get_switches()):
                    for val in t.node.get_switches():
                        t.on = True
                        print("switch pressed, set to: " + str(t.on))
                        t.node.set_switch(val, t.on)
                if (t.node.get_dimmers()):
                    for val in t.node.get_dimmers():
                        t.level = 10
                        print("dim to " + str(t.level*10))
                        t.node.set_dimmer(val, t.level*10)
            alarm.on=False

    

####################################
# Modular functions
####################################

def redraw(state):
    # erase screen
    screen.fill(black)

    # update background image
    if (state == 0):
        back_img = pygame.image.load(os.path.normcase("/home/pi/Embedded_OS/final/GUI_resources/home.png"))
    elif (state == 1):
        back_img = pygame.image.load(os.path.normcase("/home/pi/Embedded_OS/final/GUI_resources/zwave.png"))

    elif (state == 2):
        if (alarm_state == 0):
            back_img = pygame.image.load(os.path.normcase("/home/pi/Embedded_OS/final/GUI_resources/alarm.png"))
        elif (alarm_state == 1):
            back_img = pygame.image.load(os.path.normcase("/home/pi/Embedded_OS/final/GUI_resources/alarm_set.png"))
        elif (alarm_state == 2):
            back_img = pygame.image.load(os.path.normcase("/home/pi/Embedded_OS/final/GUI_resources/zwave.png"))

    # draw background
    screen.blit(back_img, back_rect)

    # Update content
    # main page
    if (state == 0):
        now = datetime.datetime.today()
       
        seconds = float(str(now)[17:26])

        dt = str(now)
        hr=dt[11:13]
        if (hr == '00'): hr = '12'
        mins=dt[14:16]

        if (int(hr)>12):
            clock=str(int(hr)-12)+":"+mins+" pm"
        else:
            clock=hr+":"+mins+" am"

        fontimg = clk_font.render(clock, True, cyan, None)
        clock_rect = fontimg.get_rect()
        clock_rect.center=(160,90)
        clock_rect.right=280
        screen.blit(fontimg, clock_rect)

    # zwave control
    elif (state == 1):
        things[things_index].draw(state, screen, small_font)

    # alarm state
    elif (state == 2):
        if (alarm_state == 0):
            display_alarm()
        elif (alarm_state == 1):
            display_set()
        elif (alarm_state == 2):
            things[things_index].draw(state, screen, small_font)

    pygame.display.flip()

def left_button_action(s):
    global state, things_index, things
    global alarm_state, alarms, alarm_index
    # main page
    if (s == 0):
        state = 2
        alarm_state = 0

    # zwave page
    elif (s == 1):
        things_index = (things_index - 1)%(len(things))

    # alarm state
    elif (s == 2):
        # nothing for main alarm page

        # alarm set
        if (alarm_state == 1):
            alarm_state=0

        # zwave selection
        elif (alarm_state == 2):
            things_index = (things_index - 1)%(len(things))

def right_button_action(s):
    global state, things_index, things
    global alarms, alarm_index, alarm_state
    # main page
    if (s == 0):
        state = 1

    # zwave page
    elif (s == 1):
        things_index = (things_index + 1)%(len(things))

    # alarm state
    elif (s == 2):
        # nothing for main alarm page

        # alarm set
        if (alarm_state == 1):
            alarms[alarm_index].time=str(h1)+str(h0)+":"+str(m1)+str(m0)
            alarms[alarm_index].per=set_per
            alarm_state=0

        # zwave selection
        elif (alarm_state == 2):
            things_index = (things_index + 1)%(len(things))

def check_other(s, x, y):
    global things_index, things
    global alarms, alarm_state, alarm_index
    global set_time, set_per, h1, h0, h, m1, m0
    # global hu_rect, hd_rect, m10u_rect, m10d_rect
    # global m1u_rect, m1d_rect, pu_rect, pd_rect

    # nothing on click for main page

    # zwave page
    if (s == 1):
        things[things_index].check(s,x,y)

    # alarm state
    elif (s == 2):
        # base alarm page
        if(alarm_state == 0):
            for i in range(len(alarms)):
                alarm=alarms[i]
                if alarm.time_rect.collidepoint(x,y):
                    alarm_state=1
                    alarm_index=i
                    set_time=alarm.time
                    set_per =alarm.per
                    h1=int(set_time[0])
                    h0=int(set_time[1])
                    h=h1*10+h0
                    m1=int(set_time[3])
                    m0=int(set_time[4])
                if alarm.on_off_rect.collidepoint(x,y):
                    if alarm.on:
                        alarm.on=False
                    else:
                        alarm.on=True
                if alarm.z_rect.collidepoint(x,y):
                    alarm_index = i
                    alarm_state = 2

        # set alarm
        elif (alarm_state == 1):
            if hu_rect.collidepoint(x,y):
                h=(h%12+1)
                h1=int(h/10)
                h0=int(h%10)

            if hd_rect.collidepoint(x,y):
                h=(h%12+1)
                h1=int(h/10)
                h0=int(h%10)

            if m10u_rect.collidepoint(x,y):
                m1=(m1+1)%6
                
            if m10d_rect.collidepoint(x,y):
                m1=(m1-1)%6
                
            if m1u_rect.collidepoint(x,y):
                m0=(m0+1)%10

            if m1d_rect.collidepoint(x,y):
                m0=(m0-1)%10

            if pu_rect.collidepoint(x,y) or pd_rect.collidepoint(x,y):
                if(set_per=="pm"):
                    set_per="am"
                else:
                    set_per="pm"

            set_time=str(h1)+str(h0)+":"+str(m1)+str(m0)

        elif (alarm_state == 2):
            things[things_index].check(s,x,y)

####################################
# Main Loop
####################################

while True:

    # check event
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            network.stop()
            GPIO.cleanup()
            pygame.quit()
            sys.exit()

        if (event.type is pygame.MOUSEBUTTONDOWN):
            pos = pygame.mouse.get_pos()
            x,y = pos
            if (state == 2 and alarm_state == 0):
                check_other(state, x, y)
            else:
                if left_rect.collidepoint(x,y):
                    left_button_action(state)
                elif right_rect.collidepoint(x,y):
                    right_button_action(state)
                else:
                    check_other(state, x, y)

    redraw(state)
    check_alarm()

    if (quit == 1):
        network.stop()
        GPIO.cleanup()
        pygame.quit()
        sys.exit()

    # delay for 30fps nominal
    time.sleep(0.033)

