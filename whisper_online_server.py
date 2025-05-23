#!/usr/bin/env python3
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

logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser()

# server options
parser.add_argument("--host", type=str, default='localhost')
parser.add_argument("--port", type=int, default=3000)
parser.add_argument("--warmup-file", type=str, dest="warmup_file", 
        help="The path to a speech audio wav file to warm up Whisper so that the very first chunk processing is fast. It can be e.g. https://github.com/ggerganov/whisper.cpp/raw/master/samples/jfk.wav .")
parser.add_argument("--source-stream", type=str, default=None)
parser.add_argument("--report-language", type=str, default=None)

# options from whisper_online
add_shared_args(parser)
args = parser.parse_args()

set_logging(args,logger,other="")

running=True
# setting whisper object by args 

SAMPLING_RATE = args.sampling_rate
size = args.model
language = args.lan
asr, online = asr_factory(args)
min_chunk = args.min_chunk_size

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

    def format_output_transcript(self,o):
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
            logger.info("%s -> %s %s" % (beg_webvtt, end_webvtt, o[2].strip()))

            data = {}
            if(report_language != None and report_language != 'none'):
                data['language'] = "en"
            data['start'] = "%1.3f" % datetime.timedelta(seconds=beg).total_seconds()
            data['end'] = "%1.3f" % datetime.timedelta(seconds=end).total_seconds()
            data['text'] = o[2].strip()

            #return "%1.0f %1.0f %s" % (beg,end,o[2])
            return json.dumps(data)
        else:
            logger.debug("No text in this segment")
            return None

    def send_result(self, o):
        msg = self.format_output_transcript(o)
        if msg is not None and (source_stream == None or source_stream == 'none'):
            self.connection.send(msg)

    def process(self):
        global running
        # handle one client connection
        self.online_asr_proc.init()
        first_time = True
        while running:
            a = self.receive_audio_chunk()
            if a is None:
                if first_time:
                    logger.debug("No audio, exiting")
                else:
                    logger.info("No audio, exiting")
                break
            else:
                if first_time:
                    first_time = False
                    logger.info("Receiving Audio")
                
                self.online_asr_proc.insert_audio_chunk(a)
                o = online.process_iter()
                try:
                    self.send_result(o)
                except BrokenPipeError:
                    logger.info("broken pipe -- connection closed?")
                    break
        #need to send what we have left
        o = online.finish()
        try:
            self.send_result(o)
        except BrokenPipeError:
            logger.info("broken pipe -- connection closed?")

def run_subprocess(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout.decode(), stderr.decode(), process.returncode

def worker_thread(command):
    global running    
    while running:
        stdout, stderr, returncode = run_subprocess(command)
        logger.debug(f"Return Code: {returncode}")
        time.sleep(1.0)

def stop(self, signum=None, frame=None):
    global running,server_socket
    server_socket.close()
    running = False

# source_stream = "rtmp://wse.docker/live/myStream_160p"
#command = "ffmpeg -hide_banner -loglevel error -f flv -i rtmp://host.docker.internal/live/myStream_aac -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | nc -q 1 localhost 3000"
#command = "ffmpeg -hide_banner -loglevel error -f flv -i rtmp://d93ab27c23fd-qa.entrypoint.cloud.wowza.com/app-Qp8R494H/259c678c_stream7 -c:a pcm_s16le -ac 1 -ar 16000 -f s16le - | nc -q 1 localhost 3000"
report_language = args.report_language
source_stream = args.source_stream
if source_stream != None and source_stream != 'none':
    command = "ffmpeg -hide_banner -loglevel error -f flv -i " + source_stream + " -vn -c:a pcm_s16le -ac 1 -ar " + str(SAMPLING_RATE) + " -f s16le - | nc -q 1 localhost 3000"
    logger.info("Running ffmpeg to connect stream "+source_stream+ " with whisper server:")
    logger.info("    " + command)
    thread = threading.Thread(target=worker_thread, args=(command,))
    thread.start()


# server loop

signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    global server_socket
    server_socket = s
    s.bind((args.host, args.port))
    s.listen(1)
    logger.info('Listening on'+str((args.host, args.port)))
    while running:
        try:
            conn, addr = s.accept()
            logger.debug('Connected to client on {}'.format(addr))
            connection = Connection(conn)
            proc = ServerProcessor(connection, online, args.min_chunk_size)
            proc.process()
            conn.close()
        except socket.error as e:
          break # Exit the loop on socket errors            
        logger.debug('Connection to client closed{}'.format(addr))

logger.info('Server Stopped')
running=False
