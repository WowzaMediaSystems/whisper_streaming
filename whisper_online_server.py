#!/usr/bin/env python3
##
## This code and all components (c) Copyright 2006 - 2025, Wowza Media Systems, LLC. All rights reserved.
## This code is licensed pursuant to the Wowza Public License version 1.0, available at www.wowza.com/legal.
##

from whisper_online import *

import sys
import argparse
import os
import logging
import numpy as np
import time
import subprocess
import threading
import signal
import datetime
import json
import http.client
import re

logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser()

# server options
parser.add_argument("--host", type=str, default='localhost')
parser.add_argument("--port", type=int, default=3000)
parser.add_argument("--warmup-file", type=str, dest="warmup_file", 
        help="The path to a speech audio wav file to warm up Whisper so that the very first chunk processing is fast. It can be e.g. https://github.com/ggerganov/whisper.cpp/raw/master/samples/jfk.wav .")
parser.add_argument("--source-stream", type=str, default=None, dest="source_stream")
parser.add_argument("--report-languages", type=str, default='en', dest="report_languages")
parser.add_argument("--source-language", type=str, default='en', dest="source_language")
parser.add_argument("--translate-host", type=str, default=None, dest="translate_host")
parser.add_argument("--translate-port", type=int, default=5000, dest="translate_port")

# options from whisper_online
add_shared_args(parser)
args = parser.parse_args()

set_logging(args,logger,other="")

running=True
# setting whisper object by args 

SAMPLING_RATE = args.sampling_rate
size = args.model
language = args.lan
min_chunk = args.min_chunk_size


######### Server objects

import line_packet
import socket

class Connection:
    '''it wraps conn object'''
    PACKET_SIZE = 32000*5*60 # 5 minutes # was: 65536

    def __init__(self, conn):
        self.conn = conn
        self.last_line = ""

        self.conn.setblocking(True)

    def send(self, line):
        '''it doesn't send the same line twice, because it was problematic in online-text-flow-events'''
        if line == self.last_line:
            return
        line_packet.send_one_line(self.conn, line)
        self.last_line = line

    def receive_lines(self):
        in_line = line_packet.receive_lines(self.conn)
        return in_line

    def non_blocking_receive_audio(self):
        try:
            r = self.conn.recv(self.PACKET_SIZE)
            return r
        except ConnectionResetError:
            return None


import io
import soundfile

# wraps socket and ASR object, and serves one client connection. 
# next client should be served by a new instance of this object
class ServerProcessor:

    def timedelta_to_webvtt(self,delta):
    #Format this:0:00:00
    #Format this:0:00:09.480000
      parts = delta.split(":")
      parts2 = parts[2].split(".")

      final_data  = "{:02d}".format(int(parts[0])) + ":"
      final_data += "{:02d}".format(int(parts[1])) + ":"
      final_data += "{:02d}".format(int(parts2[0])) + "."
      if(len(parts2) == 1):
        final_data += "000"
      else:
        final_data += "{:03d}".format(int(int(parts2[1])/1000))
      return final_data

    def __init__(self, c, online_asr_proc, min_chunk):
        self.connection = c
        self.online_asr_proc = online_asr_proc
        self.min_chunk = min_chunk

        self.last_end = None

        self.is_first = True

        #put english first as the may source to translate
        self.report_languages = args.report_languages.split(',')
        self.report_languages.insert(0, self.report_languages.pop(self.report_languages.index('en')))

    def receive_audio_chunk(self):
        global running
        # receive all audio that is available by this time
        # blocks operation if less than self.min_chunk seconds is available
        # unblocks if connection is closed or a chunk is available
        out = []
        minlimit = self.min_chunk*SAMPLING_RATE
        while running and sum(len(x) for x in out) < minlimit:
            raw_bytes = self.connection.non_blocking_receive_audio()
            if not raw_bytes:
                break
#            print("received audio:",len(raw_bytes), "bytes", raw_bytes[:10])
            sf = soundfile.SoundFile(io.BytesIO(raw_bytes), channels=1,endian="LITTLE",samplerate=SAMPLING_RATE, subtype="PCM_16",format="RAW")
            audio, _ = librosa.load(sf,sr=SAMPLING_RATE,dtype=np.float32)
            out.append(audio)
        if not out:
            return None
        conc = np.concatenate(out)
        if self.is_first and len(conc) < minlimit:
            return None
        self.is_first = False
        return np.concatenate(out)

    def format_output_transcript(self,o, report_language):
        # This function differs from whisper_online.output_transcript in the following:
        # succeeding [beg,end] intervals are not overlapping because ELITR protocol (implemented in online-text-flow events) requires it.
        # Therefore, beg, is max of previous end and current beg outputed by Whisper.
        # Usually it differs negligibly, by appx 20 ms.

        if o[0] is not None:
            beg, end = o[0],o[1]
            if self.last_end is not None:
                beg = max(beg, self.last_end)

            self.last_end = end
            beg_webvtt = self.timedelta_to_webvtt(str(datetime.timedelta(seconds=beg)))
            end_webvtt = self.timedelta_to_webvtt(str(datetime.timedelta(seconds=end)))
            org_txt = o[2].strip()

            data = {}
            data['language'] = report_language
            data['start'] = "%1.3f" % datetime.timedelta(seconds=beg).total_seconds()
            data['end'] = "%1.3f" % datetime.timedelta(seconds=end).total_seconds()
            data['text'] = org_txt

            #return "%1.0f %1.0f %s" % (beg,end,o[2])
            return data
        else:
            logger.debug("No text in this segment")
            return None

    def send_result(self, o, id):
        msg = self.format_output_transcript(o, args.source_language)
        if msg is not None and (source_stream == None or source_stream == 'none'):
            logger.info("%i) (%s) %s -> %s %s" % ( id, msg['language'], self.timedelta_to_webvtt(str(datetime.timedelta(seconds=float(msg['start'])))) ,  self.timedelta_to_webvtt(str(datetime.timedelta(seconds=float(msg['end'])))), msg['text']))
            self.connection.send(json.dumps(msg))

            if(args.translate_host != None and args.translate_host != 'none'):
                org_txt = msg['text']
                source_language = args.source_language

                for report_language in self.report_languages:
                    if(report_language != args.source_language):
                        msg['language'] = report_language
                        msg['text'] = self.translate_text(id, org_txt, source_language, msg['language'])
                        self.connection.send(json.dumps(msg))
                        if(report_language == 'en'):
                            #switch to translation to english, for non-english to non-english, going to english works 
                            source_language = 'en'
                            msg['text'] = self.remove_non_english_chars(msg['text'])
                            org_txt = msg['text']
                        logger.info("%i) (%s) %s -> %s %s" % ( id, msg['language'],  self.timedelta_to_webvtt(str(datetime.timedelta(seconds=float(msg['start'])))) ,  self.timedelta_to_webvtt(str(datetime.timedelta(seconds=float(msg['end'])))), msg['text']))

    def process(self, id):
        global running
        # handle one client connection
        self.online_asr_proc.init()
        first_time = True
        while running:
            a = self.receive_audio_chunk()
            if a is None:
                if first_time:
                    logger.debug(f"{id}) No audio, exiting")
                else:
                    logger.info(f"{id}) No audio, exiting")
                break
            else:
                if first_time:
                    first_time = False
                    logger.info(f"{id}) Receiving Audio")
                
                self.online_asr_proc.insert_audio_chunk(a)
                o = self.online_asr_proc.process_iter()
                try:
                    self.send_result(o, id)
                except Exception as e:
                    logger.error(f"{id}) Socket Error:"+str(e))
                    break
        #need to send what we have left
        o = self.online_asr_proc.finish()
        try:
            self.send_result(o, id)
        except Exception as e:
            logger.error(f"{id}) Socket Error:"+str(e))

    def translate_text(self, id, org_txt, source_language, dst_language):
        new_txt = "???"
        try:
            # docker run -ti --rm -p 5001:5000 -v ~/libretranslate_models:/home/libretranslate/.local -e LT_LOAD_ONLY=en,jp libretranslate/libretranslate:latest
            # curl -X POST http://localhost:5001/translate -H "Content-Type:application/json" -d '{"q":"Hello!","source":"en","target":"es"}'
            js = {
                'q': org_txt,
                'source': source_language,
                'target': dst_language
            }
            json_data = json.dumps(js).encode('utf-8')
            headers = { 'Content-type': 'application/json' }

            connection = http.client.HTTPConnection(args.translate_host, args.translate_port, timeout=10)
            connection.request("POST", "/translate", json_data, headers)

            response = connection.getresponse()
            if(response.status == 200 or response.status == 201):
                json_string = response.read().decode('utf-8')
                objects = json.loads(json_string)
                new_txt = objects.get('translatedText')
            else:
                logger.error(f"{id}) Error:" + str(response.status))
                logger.error(f"{id}) {response.read().decode('utf-8')}")

        except Exception as e:
            logger.error(f"{id}) translation_api:" + str(e))
        return new_txt

    def remove_non_english_chars(self, text):
        # This regex pattern matches characters that are NOT:
        # a-z (lowercase English letters)
        # A-Z (uppercase English letters)
        # 0-9 (digits)
        # common punctuation and whitespace (.,!?;:()[]{}'" -)
        # You can customize this pattern to include or exclude specific characters
        pattern = r'[^a-zA-Z0-9 .,!?;:()\[\]{}\'" -]'
        cleaned_text = re.sub(pattern, '', text)
        return cleaned_text

def run_subprocess(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout.decode(), stderr.decode(), process.returncode

def worker_thread(command):
    global running    
    while running:
        stdout, stderr, returncode = run_subprocess(command)
        logger.info(f"Return Code: {returncode}")
        time.sleep(1.0)

def stop(self, signum=None, frame=None):
    global running,server_socket
    server_socket.close()
    running = False

# source_stream = "rtmp://wse.docker/live/myStream_160p"
#command = "ffmpeg -hide_banner -loglevel error -f flv -i rtmp://host.docker.internal/live/myStream_aac -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | nc -q 1 localhost 3000"
#command = "ffmpeg -hide_banner -loglevel error -f flv -i rtmp://d93ab27c23fd-qa.entrypoint.cloud.wowza.com/app-Qp8R494H/259c678c_stream7 -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | nc -q 1 localhost 3000"

source_stream = args.source_stream
if source_stream != None and source_stream != 'none':
    command = "ffmpeg -hide_banner -loglevel error -f flv -i " + source_stream + " -vn -c:a pcm_s16le -ac 1 -ar " + str(SAMPLING_RATE) + " -f s16le - | nc -q 1 localhost 3000"
    logger.info("Running ffmpeg to connect stream "+source_stream+ " with whisper server:")
    logger.info("    " + command)
    thread = threading.Thread(target=worker_thread, args=(command,))
    thread.start()

def socket_thread(conn, asr, online_asr_proc, addr, id):
    try:
        connection = Connection(conn)
        conn.settimeout(15)
        proc = ServerProcessor(connection, online_asr_proc, args.min_chunk_size)
        proc.process(id)
    except Exception as e:
        logger.error(f"{id}) Error:"+str(e))
    if(conn is not None):
        conn.close()
    logger.info(f"{id}) Client connection closed {format(addr)}")
    logger.info(f"{id}) Ending socket thread")

# server loop

signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    
    asr, online = asr_factory(args)
    # warm up the ASR because the very first transcribe takes more time than the others. 
    # Test results in https://github.com/ufal/whisper_streaming/pull/81
    msg = "Whisper is not warmed up. The first chunk processing may take longer."
    if args.warmup_file:
        if os.path.isfile(args.warmup_file):
            a = load_audio_chunk(args.warmup_file,0,1)
            asr.transcribe(a)
            logger.info("Whisper is warmed up.")
        else:
            logger.critical("The warm up file is not available. "+msg)
            sys.exit(1)
    else:
        logger.warning(msg) 
           
    global server_socket
    server_socket = s
    s.bind((args.host, args.port))
    s.listen(1)
    id = 0
    logger.info("Using translation server: "+args.translate_host)    
    logger.info('Listening on'+str((args.host, args.port)))
    while running:
        try:
            addr = None
            conn = None

            logger.info('Waiting for new connection')
            conn, addr = s.accept()
            id = id + 1
            logger.info(f"{id}) Connected on {format(addr)}")
            thread = threading.Thread(target=socket_thread, args=(conn, asr, online, addr, id))
            thread.start()

            #create a new asr for the next request
            asr, online = asr_factory(args)
            # warm up the ASR because the very first transcribe takes more time than the others. 
            # Test results in https://github.com/ufal/whisper_streaming/pull/81
            msg = "Whisper is not warmed up. The first chunk processing may take longer."
            if args.warmup_file:
                if os.path.isfile(args.warmup_file):
                    a = load_audio_chunk(args.warmup_file,0,1)
                    asr.transcribe(a)
                    logger.info("Whisper is warmed up.")
                else:
                    logger.critical("The warm up file is not available. "+msg)
                    sys.exit(1)
            else:
                logger.warning(msg) 

        except socket.error as e:
            logger.error("f{id} Socket error:"+str(e))
            #break # Exit the loop on socket errors
        except Exception as e:
            logger.error("f{id} Error:"+str(e))

logger.info('Server Stopped')
running=False
