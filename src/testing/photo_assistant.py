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
import boto3
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import aiy.assistant.auth_helpers
from aiy.assistant.library import Assistant
import aiy.audio
import aiy.voicehat
from google.assistant.library.event import EventType
import re

email_mappings = {
    "kthapar": "Kushagra Thapar",
    "htiwari": "Harshit Tiwari",
    "tharris": "Trevor Harris",
    "afarquhar": "Austin Farquhar",
    "rgarand": "Rory Garand",
    "lquach": "Lan Quach",
    "pjain": "Palak Jain",
    "atirumale": "Adithya Tirumale",
    "mvanderpluym": "Michael Vander Pluym",
    "rkhandel": "Ramakant Khandel",
    "lpeeler": "Luke Peeler",
    "pwhalen": "Paul Whalen",
    "djamrozik": "Dan Jamrozik",
    "jgoldrich": "Jake Goldrich",
    "zbukhari": "Zahid Bukhari",
    "jdoshier": "John Doshier",
    "dcarvajal": "Deb Carvajal",
    "pkuprys": "Peter Kuprys"
}

name_mappings = {
    "Kushagra Thapar": "kthapar@peak6.com",
    "Harshit Tiwari": "htiwari@peak6.com",
    "Trevor Harris": "tharris@peak6.com",
    "Austin Farquhar": "afarquhar@peak6.com",
    "Rory Garand": "rgarand@peak6.com",
    "Lan Quach": "lquach@peak6.com",
    "Palak Jain": "pjain@peak6.com",
    "Adithya Tirumale": "atirumale@peak6.com",
    "Michael Vander Pluym": "mvanderpluym@peak6.com",
    "Ramakant Khandel": "rkhandel@peak6.com",
    "Luke Peeler": "lpeeler@peak6.com",
    "Paul Whalen": "pwhalen@peak6.com",
    "Dan Jamrozik": "djamrozik@peak6.com",
    "Jake Goldrich": "jgoldrich@peak6.com",
    "Zahid Bukhari": "zbukhari@peak6.com",
    "John Doshier": "jdoshier@peak6.com",
    "Deb Carvajal": "dcarvajal@peak6.com",
    "Peter Kuprys": "pkuprys@peak6.com"
}

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


def take_and_upload_photo():
    print('taking a picture and uploading it')
    f_time = datetime.datetime.now().microsecond
    image_id = "photo-" + str(f_time) + ".jpg"
    with picamera.PiCamera() as camera:
        camera.resolution = (1024, 768)
        camera.start_preview()
        time.sleep(2)
        camera.capture(image_id)

    upload_file(image_id)
    print("Indexing this new face now")
    index_faces(image_id)
    results = search_faces_by_image(image_id)
    print("Results are")
    print(results)
    images = set()
    to_addr = None
    if len(results) > 0:
        for single_result in results:
            image = single_result["Face"]["ExternalImageId"]
            if image in email_mappings:
                aiy.audio.say("Hello " + email_mappings[image])
                to_addr = name_mappings[email_mappings[image]]
                images.add(image)

    print(str(images))
    if to_addr is not None and len(to_addr) > 0:
        take_and_send_picture(to_addr, image_id)
    return to_addr


def take_and_send_picture(to_addr, file_path):
    print('taking a picture and emailing it')
    f_time = datetime.datetime.now().strftime('%a %d %b @ %H %M')

    me = 'raspberrypeak6@gmail.com'
    subject = 'Tech Day photo ' + f_time

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = me
    msg['To'] = to_addr
    msg.preamble = "Photo @ " + f_time

    fp = open(file_path, 'rb')
    img = MIMEImage(fp.read())
    fp.close()
    msg.attach(img)

    try:
        s = smtplib.SMTP('smtp.gmail.com:587')
        s.ehlo_or_helo_if_needed()
        s.starttls()
        s.ehlo_or_helo_if_needed()
        s.login('raspberrypeak6@gmail.com', 'techdaypeak6')

        print("Message is ", str(msg))
        s.send_message(msg)
    except RuntimeError as error:
        aiy.audio.say('Oops, I am not able to send an email right now')
        print('Error : ', error)
    print('DONE')


def list_buckets():
    # Create an S3 client
    s3 = boto3.client('s3')

    # Call S3 to list current buckets
    response = s3.list_buckets()

    # Get a list of all bucket names from the response
    buckets = [bucket['Name'] for bucket in response['Buckets']]

    # Print out the bucket list
    print("Bucket List: %s" % buckets)


def upload_file(file_path):
    # Create an S3 client
    s3 = boto3.client('s3')
    bucket_name = 'techday-bucket'
    s3.upload_file(file_path, bucket_name, file_path)


def index_faces(image_id, attributes=(), region="us-east-2"):
    rekognition = boto3.client("rekognition", region)
    response = rekognition.index_faces(
        Image={
            "S3Object": {
                "Bucket": "techday-bucket",
                "Name": image_id,
            }
        },
        CollectionId="first-collection",
        ExternalImageId=image_id,
        DetectionAttributes=attributes,
    )
    return response['FaceRecords']


def search_faces_by_image(image_id, threshold=80, region="us-east-2"):
    rekognition = boto3.client("rekognition", region)
    response = rekognition.search_faces_by_image(
        Image={
            "S3Object": {
                "Bucket": "techday-bucket",
                "Name": image_id,
            }
        },
        CollectionId="first-collection",
        FaceMatchThreshold=threshold,
    )
    return response['FaceMatches']


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
            to_addr = take_and_upload_photo()
        elif "upload photo" in text:
            assistant.stop_conversation()
            to_addr = take_and_upload_photo()
        elif "buckets" in text:
            assistant.stop_conversation()
            list_buckets()

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
