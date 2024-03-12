# Transcription Bot

Telegram bot which transcribes audio/voice messages/videos into high quality text, using [`faster-whisper`] on CPU, at about 3x realtime speed.

Benchmark for a 464s file (CPU only):

| Model                        | Processing Time (s) | With VAD (s) |
| ---------------------------- | ------------------- | ------------ |
| Transformers Base            | 275                 | -            |
| BetterTransformer w/ Optimum | 193                 | -            |
| faster-whisper               | 166                 | 106          |

## Getting Started

Clone this repo:

```bash
git clone https://github.com/extrange/transcription-bot.git
```

[Create a Telegram bot][botfather] and obtain the API key (it looks like `110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw`)

Build the container:

```bash
docker compose build
```

Run the app once with `docker compose up` and enter your API key when prompted.

To run in the background, do `docker compose up -d`.

Login credentials will be stored in a `<name>.session` file for future runs.

## Notes

`MY_CHAT_ID` is the chat id of your own private chat with the bot. It's used to alert you when users use your bot. To obtain it you can either print the output of `message.chat.id` or use [@RawDataBot][rawdatabot].


[`faster-whisper`]: https://github.com/guillaumekln/faster-whisper
[botfather]: https://core.telegram.org/bots/features#creating-a-new-bot
[rawdatabot]: https://t.me/RawDataBot