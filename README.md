# Whisper Telegram Bot

Telegram bot which transcribes audio/voice messages/videos into high quality text, using the optimized [C++ port][whisper.cpp] of OpenAI's [Whisper][whisper] model.

I use the [Pyrogram][pyrogram] Telegram Client, which interacts directly with the main Telegram API ([MTProto][mtproto]) for minimal overhead.

No GPU is required, and since it runs natively performance is high.

## Getting Started

Clone this repo:

```bash
git clone https://github.com/extrange/whisper-telegram.git
```

Download the model file into the `models/` directory:

```bash
cd whisper-telegram
wget -P models https://huggingface.co/datasets/ggerganov/whisper.cpp/resolve/main/ggml-large.bin
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


[whisper]: https://openai.com/blog/whisper/
[whisper.cpp]: https://github.com/ggerganov/whisper.cpp
[pyrogram]: https://docs.pyrogram.org/
[mtproto]: https://docs.pyrogram.org/topics/mtproto-vs-botapi
[botfather]: https://core.telegram.org/bots/features#creating-a-new-bot
[rawdatabot]: https://t.me/RawDataBot