#Explanations (look at the amount of ##)
##Code review
###Stuff to improve
#---TITLES---
#The code helps to control a CCT-32 telescope, by implementing limits and exception handling for the 
#constructed CAN Frames and an keyboard interrupt to disable both drives.

import can
import time

#---VARIABLES---

#Limits the user input in a + or negative sense
limit_for_degrees = 60

#So for each revolution the motor moves 4000 encoder points
### The value might be slightly off so double check this value
encpointsperrev = 4000

#Wait time to ensure the drive got the message
enable_to_movement_wait_time = 0.3

#Cautionary wait time, move each axis one at a time
movement_wait_time = 5

#---CAN BUS---

#Sets up CAN Bus
bus = can.Bus(interface='canalystii', channel=0, bitrate=250000)

#So the motor moves according to position, but it only accepts positive int.
#So instead of doing a full 360 we are just going to set the position to 1000,
#and subtract to move to the other direction.
###Could not get group ID to work, something for next year team
center1 = can.Message(arbitration_id=0x07408180, data=[0xE8, 0x03, 0x00, 0x00], is_extended_id=True)
center2 = can.Message(arbitration_id=0x07408280, data=[0xE8, 0x03, 0x00, 0x00], is_extended_id=True)

#Sends command 00 that enables the drive depending if the data is a one or a zero.
enabledrive1 = can.Message(arbitration_id=0x07008180, data=[0x01], is_extended_id=True)
enabledrive2 = can.Message(arbitration_id=0x07008280, data=[0x01], is_extended_id=True)
disabledrive1 = can.Message(arbitration_id=0x07008180, data=[0x00], is_extended_id=True)
disabledrive2 = can.Message(arbitration_id=0x07008280, data=[0x00], is_extended_id=True)

#Moves motors back to original position
right_ascension_center = can.Message(arbitration_id=0x07418180, data=[0x00, 0xE8, 0x03, 0x00, 0x00], is_extended_id=True)
declination_center = can.Message(arbitration_id=0x07418280, data=[0x00, 0xE8, 0x03, 0x00, 0x00], is_extended_id=True)

#---"USER INTERFACE"---

#Makes sure that the telescope is in the original position before setting the encoders.
while True:
    in_og_place = input("Is the DFM CCT-32 in the original locked position (y/n)?: ")
    if(in_og_place == 'y'):
        break
    elif(in_og_place == 'n'):
        in_og_place = input("When CCT-32 is in the original locked position please input 'y': ")
        if(in_og_place == 'y'):
            break
    print("Incorrect value. Please try again.")

#Sends message set the encoder position to 1000, no need to enable the drive for this
try:
    bus.send(center1)
    print("Drive one set to neutral position")

except can.CanError:
    print("Drive one was unable to receive CAN Message")
    bus.shutdown
    exit()

try:
    bus.send(center2)
    print("Drive two set to neutral position")
except can.CanError:
    print("Drive two was unable to receive CAN Message")
    bus.shutdown
    exit()

print(f"The range is -{limit_for_degrees} to {limit_for_degrees} degrees")
while True:
    #limit_for_degrees_for_degrees the inputs to prevent the telescope from doing something crazy (hopefully)
    while True:
        try: 
            right_ascension_degrees = int(input("Please input the right ascension angle (- Left, + Right, perspective is front view from the yellow stairs): "))
            if((right_ascension_degrees <= limit_for_degrees) and (right_ascension_degrees >= -limit_for_degrees)):
                declination_degrees = int(input("Please input the declination angle (- Left, + Right, perspective is front view yellow stairs to your left): "))
                if((declination_degrees <= limit_for_degrees) and (declination_degrees >= -limit_for_degrees)):
                    break
            print("Incorrect value. Please try again")
        except ValueError:
            print("Incorrect value. Please try again")

    #---Math---
    #The ratio and proportion math converts the degrees into the unit the drive uses called encoder points
    right_ascension_encpoints = int(1000-(right_ascension_degrees*encpointsperrev)/360)
    declination_encpoints = int(1000-(declination_degrees*encpointsperrev)/360)

    #Converts the integer value into a byte array.
    right_ascension_bytearray = right_ascension_encpoints.to_bytes(2, 'little')
    declination_bytearray = declination_encpoints.to_bytes(2, 'little')

    #This 00 is a command within the Move Command. 
    #00 tells the drive to go to a specified location
    command = bytearray(b'\x00')

    #Adds the command to the byte array to complete the data section of the CAN Bus Message
    ### Max value is four bytes might cause issues if something is larger than 4 bytes (excluding the command)
    right_ascension_bytearray = command + right_ascension_bytearray
    declination_bytearray = command + declination_bytearray
    
    #---MORE CAN BUS---
    #This is the bulk of the work. The arbitration ID and data was constructed using CAN Reference Manual from 
    #Electrocraft. Electrocraft uses an extended id.
    right_ascension_move = can.Message(arbitration_id=0x07418180, data=right_ascension_bytearray, is_extended_id=True)
    declination_move = can.Message(arbitration_id=0x07418280, data=declination_bytearray, is_extended_id=True)

    #---CONTINUATION OF "USER INTERFACE"---
    ###This should be a function
    try:
        try:
            bus.send(enabledrive1)
            print("Drive one enabled")
            time.sleep(enable_to_movement_wait_time)
            bus.send(right_ascension_move)
            ##f and {} is to use string literals, so place variables inside strings
            print(f"Moving right ascension {right_ascension_degrees} degrees")

            ###Ideally you would check the status of the CAN bus to see if the movement is done,
            ###but I ran out of time so this will do.
            time.sleep(movement_wait_time)
            bus.send(disabledrive1)
            print("Drive one disabled")
        except can.CanError:
            print("Message to drive one was not sent")

        try:
            bus.send(enabledrive2)
            print("Drive two is enabled")
            time.sleep(enable_to_movement_wait_time)
            bus.send(declination_move)
            print(f"Moving declination {declination_degrees} degrees")
            time.sleep(movement_wait_time)
            bus.send(disabledrive2)
            print("Drive two is disabled")
        except can.CanError:
            print("Message to drive two was not sent")

    except KeyboardInterrupt:
        bus.send(disabledrive1)
        bus.send(disabledrive2)
        print("Both drives were disabled")
        break

    while True:
        retry = input("Would you like to enter a new position (y/n)?: ")
        if(retry == 'y' or 'n'):
            break
        else:
            print("Invalid value. Please try again")

    #When the user is done moving the telescope it returns to the original position to compensate
    #for the lack of proper calibration.
    ###Implement calibration process
    if(retry == 'n'):
        ###This is why it should be a function
        try:
            try:
                bus.send(enabledrive1)
                print("Drive one enabled")
                time.sleep(enable_to_movement_wait_time)
                bus.send(right_ascension_center)
                print(f"Moving right ascension to original position")
                time.sleep(movement_wait_time)
                bus.send(disabledrive1)
                print("Drive one disabled")
            except can.CanError:
                print("Message to drive one was not sent")

            try:
                bus.send(enabledrive2)
                print("Drive two is enabled")
                time.sleep(enable_to_movement_wait_time)
                bus.send(declination_center)
                print(f"Moving declination to original position")
                time.sleep(movement_wait_time)
                bus.send(disabledrive2)
                print("Drive two is disabled")
            except can.CanError:
                print("Message to drive two was not sent")

        except KeyboardInterrupt:
            bus.send(disabledrive1)
            bus.send(disabledrive2)
            print("Both drives were disabled")
        break

print("Goodbye!")
bus.shutdown()