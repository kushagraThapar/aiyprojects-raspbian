#!/usr/bin/env python3
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Run a recognizer using the Google Assistant Library.

The Google Assistant Library has direct access to the audio API, so this Python
code doesn't need to record audio. Hot word detection "OK, Google" is supported.

It is available for Raspberry Pi 2/3 only; Pi Zero is not supported.
"""

import logging
import platform
import subprocess
import sys
import time
import datetime
import picamera
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import aiy.assistant.auth_helpers
from aiy.assistant.library import Assistant
import aiy.audio
import aiy.voicehat
from google.assistant.library.event import EventType

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)


def power_off_pi():
    aiy.audio.say('Good bye!')
    subprocess.call('sudo shutdown now', shell=True)


def pause_radio():
    print("pausing radio")
    subprocess.call("mpc stop", shell=True)


def play_radio():
    print("playing radio")
    subprocess.call("mpc clear; mpc add http://50.31.180.202:80/;mpc play", shell=True)


def reboot_pi():
    aiy.audio.say('See you in a bit!')
    subprocess.call('sudo reboot', shell=True)


def say_ip():
    ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
    aiy.audio.say('My IP address is %s' % ip_address.decode('utf-8'))


def take_and_send_picture(phone_number):
    # phone_number = re.sub('[^0-9]', '', phone_number)
    print('taking a picture and emailing it')
    aiy.audio.say('Well then smile please')
    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.start_preview()
        time.sleep(2)
        camera.capture('photo.jpg')
    f_time = datetime.datetime.now().strftime('%a %d %b @ %H %M')

    toaddr = 'kushuthapar@gmail.com'
    me = 'raspberrypeak6@gmail.com'
    subject = 'Photo ' + f_time

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = me
    msg['To'] = toaddr
    msg.preamble = "Photo @ " + f_time

    fp = open('photo.jpg', 'rb')
    img = MIMEImage(fp.read())
    fp.close()
    msg.attach(img)

    try:
        s = smtplib.SMTP('smtp.gmail.com:587')
        s.ehlo_or_helo_if_needed()
        s.starttls()
        s.ehlo_or_helo_if_needed()
        s.login('raspberrypeak6@gmail.com', 'techdaypeak6')
        s.send_message(msg)
        # s.sendmail(msg['From'], msg['To'], "", msg)

        print('phone_number:' + str(phone_number))
        if phone_number is not None and len(phone_number) > 0:
            carriers = ['messaging.sprintpcs.com', 'tmomail.net', 'txt.att.net', 'msg.fi.google.com']

            for carrier in carriers:
                try:
                    msg['To'] = phone_number + '@' + carrier
                    # s.send_message(msg)
                    print('sent to ' + msg['To'])
                    # success = True
                except:
                    pass

        aiy.audio.say('Check your mail dude')
    except RuntimeError as error:
        aiy.audio.say('Oops, I am not able to send an email right now')
        print('Error : ', error)
    print('DONE')


def process_event(assistant, event):
    status_ui = aiy.voicehat.get_status_ui()
    if event.type == EventType.ON_START_FINISHED:
        status_ui.status('ready')
        if sys.stdout.isatty():
            print('Say "OK, Google" then speak, or press Ctrl+C to quit...')

    elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
        status_ui.status('listening')

    elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:
        print('You said:', event.args['text'])
        text = event.args['text'].lower()
        if text == 'power off':
            assistant.stop_conversation()
            power_off_pi()
        elif text == 'reboot':
            assistant.stop_conversation()
            reboot_pi()
        elif text == 'ip address':
            assistant.stop_conversation()
            say_ip()
        elif text == 'play the radio':
            assistant.stop_conversation()
            play_radio()
        elif text in ['pause the radio', 'stop the radio']:
            assistant.stop_conversation()
            pause_radio()
        elif "take my picture" in text or "click my picture" in text or "take my photo" in text:
            assistant.stop_conversation()
            phone_number = None
            if "at" in text:
                phone_number = text.split("at")[1]
            take_and_send_picture(phone_number)

    elif event.type == EventType.ON_END_OF_UTTERANCE:
        status_ui.status('thinking')

    elif (event.type == EventType.ON_CONVERSATION_TURN_FINISHED
          or event.type == EventType.ON_CONVERSATION_TURN_TIMEOUT
          or event.type == EventType.ON_NO_RESPONSE):
        status_ui.status('ready')

    elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
        sys.exit(1)


def main():
    if platform.machine() == 'armv6l':
        print('Cannot run hotword demo on Pi Zero!')
        exit(-1)

    credentials = aiy.assistant.auth_helpers.get_assistant_credentials()
    with Assistant(credentials) as assistant:
        for event in assistant.start():
            process_event(assistant, event)


if __name__ == '__main__':
    main()
