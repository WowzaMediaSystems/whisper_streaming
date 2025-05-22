# Whisper Streaming for WSE

This provides a docker container to run a Whisper services that integrates with WSE module *********


## Usage
local build 
local run

Environment variables

|Variable  |Default  |Description |
|----------|---------|------------|
|BACKEND   |faster-whisper| [faster-whisper,whisper_timestamped,openai-api] Load only this backend for Whisper processing.|
|MODEL     |  tiny.en| [tiny.en,tiny,base.en,base,small.en,small,medium.en,medium,large-v1,large-v2,large-v3,large,large-v3-turbo] Name size of the Whisper model to use. The model is automatically downloaded from the model hub if not present in model cache dir. (/tmp)|
|LANGUAGE  |     auto| Source language code, e.g. en,de,cs, or 'auto' for language detection.|
|LOG_LEVEL |     INFO| [DEBUG,INFO,WARNING,ERROR,CRITICAL] The level for logging|
|SOURCE_STREAM | none| an RTMP url to pull a stream in.  Uses ffmpeg to capture the auto and forward to the service |
|MIN_CHUNK_SIZE | 1| Minimum audio chunk size in seconds. It waits up to this time to do processing. If the processing takes shorter time, it waits, otherwise it processes the whole segment that was
                        received by this time.|
|SAMPLING_RATE | 16000| Sample rate of the Audio.  |
|REPORT_LANGUAGE | none| Language to report back to WSE|


[Original README.md](https://github.com/WowzaMediaSystems/whisper_streaming/blob/main/README_ORG.md)

## Contact

[Wowza Media Systems, LLC](https://www.wowza.com/contact)

## License

This code is distributed under the [Wowza Public License](https://github.com/WowzaMediaSystems/whisper_streaming/blob/main/LICENSE.txt).
