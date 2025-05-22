#!/bin/bash
##
## This code and all components (c) Copyright 2006 - 2025, Wowza Media Systems, LLC. All rights reserved.
## This code is licensed pursuant to the Wowza Public License version 1.0, available at www.wowza.com/legal.
##

#docker build  -t "whisper_streaming:local" .
docker build --platform linux/arm64,linux/amd64 -t "whisper_streaming:local" .
