#!/bin/bash
##
## This code and all components (c) Copyright 2006 - 2025, Wowza Media Systems, LLC. All rights reserved.
## This code is licensed pursuant to the Wowza Public License version 1.0, available at www.wowza.com/legal.
##

# usage: whisper_online_server.py 
# [-h] [--host HOST] [--port PORT] [--warmup-file WARMUP_FILE] [--min-chunk-size MIN_CHUNK_SIZE]
# [--model {tiny.en,tiny,base.en,base,small.en,small,medium.en,medium,large-v1,large-v2,large-v3,large,large-v3-turbo}]
# [--model_cache_dir MODEL_CACHE_DIR] [--model_dir MODEL_DIR] [--lan LAN] [--task {transcribe,translate}]
# [--backend {faster-whisper,whisper_timestamped,mlx-whisper,openai-api}] [--vac] [--vac-chunk-size VAC_CHUNK_SIZE] [--vad]
# [--buffer_trimming {sentence,segment}] [--buffer_trimming_sec BUFFER_TRIMMING_SEC] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

backend="${BACKEND:-faster-whisper}"
model="${MODEL:-tiny.en}"
language="${LANGUAGE:-auto}"
log_level="${LOG_LEVEL:-INFO}"
source_stream="${SOURCE_STREAM:-none}"
min_chunk_size="${MIN_CHUNK_SIZE:-1}"
sampling_rate="${SAMPLING_RATE:-16000}"
report_languages="${REPORT_LANGUAGES:-en}"
source_language="${SOURCE_LANGUAGE:-en}"
use_gpu="${USE_GPU:-False}"
buffer_trimming="${BUFFER_TRIMMING:-segment}"
buffer_trimming_sec="${BUFFER_TRIMMING_SEC:-15}"
libretranslate_host="${LIBRETRANSLATE_HOST:-none}"
libretranslate_port="${LIBRETRANSLATE_PORT:-5000}"

exec python whisper_online_server.py \
--backend $backend \
--model $model \
--source-stream $source_stream \
--report-languages $report_languages \
--source-language $source_language \
--min-chunk-size $min_chunk_size \
--sampling_rate $sampling_rate \
--buffer_trimming $buffer_trimming \
--buffer_trimming_sec $buffer_trimming_sec \
--libretranslate-host $libretranslate_host \
--libretranslate-port $libretranslate_port \
--use_gpu $use_gpu \
--port 3000 \
--host 0.0.0.0 \
--log-level $log_level \
--warmup-file samples_jfk.wav \
--model_cache_dir /tmp \
--lan $language
