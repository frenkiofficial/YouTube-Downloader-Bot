# 🎬 YouTube Downloader Telegram Bot

A simple Telegram bot built with Python that allows users to download video (MP4) or audio (MP3) from YouTube directly through Telegram. This bot utilizes the powerful `yt-dlp` library for efficient downloading and `python-telegram-bot` for interacting with the Telegram API.

This repository contains the code for a **basic version** of the bot.

---

## ✅ Basic Features (Implemented)

*   **Download Command:** Use `/download <youtube_link>` to initiate a download.
*   **Format Selection:** Choose between MP4 (video) or MP3 (audio) format via inline buttons.
*   **File Size Limit:** Adheres to Telegram's upload limits (default set to 49MB in the code) to prevent errors. Downloads exceeding this limit will be cancelled.
*   **`yt-dlp` Powered:** Leverages `yt-dlp` for reliable and fast download processing.
*   **Basic Error Handling:** Provides feedback on invalid links or download errors (e.g., file too large, video unavailable).

---

## ⚙️ Prerequisites

Before you can run this bot, you need the following installed on your server or local machine:

1.  **Python:** Version 3.7 or higher.
2.  **pip:** Python package installer (usually comes with Python).
3.  **Telegram Bot Token:** Obtain one from @BotFather on Telegram.
4.  **`ffmpeg`:** Required by `yt-dlp` for merging video/audio streams and converting to MP3.
    *   **Ubuntu/Debian:** `sudo apt update && sudo apt install ffmpeg`
    *   **MacOS (using Homebrew):** `brew install ffmpeg`
    *   **Windows:** Download from the [official FFmpeg website](https://ffmpeg.org/download.html) and add the `bin` directory to your system's PATH environment variable.

---

## 🛠️ Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/frenkiofficial/YouTube-Downloader-Bot.git
    cd YouTube-Downloader-Bot
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # Activate it:
    # Linux/macOS:
    source venv/bin/activate
    # Windows (cmd.exe):
    .\venv\Scripts\activate
    # Windows (PowerShell):
    .\venv\Scripts\Activate.ps1
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Bot Token:**
    *   Create a file named `.env` in the same directory as `bot.py`.
    *   Add your Telegram Bot Token to the `.env` file:
        ```dotenv
        TELEGRAM_BOT_TOKEN=YOUR_ACTUAL_BOT_TOKEN_HERE
        ```
        Replace `YOUR_ACTUAL_BOT_TOKEN_HERE` with the token you got from BotFather.

5.  **Run the Bot:**
    ```bash
    python bot.py
    ```
    The bot should now be running and connected to Telegram.

---

## ❓ How to Use (User Guide)

1.  **Find your Bot:** Open Telegram and search for the username of the bot you created with BotFather.
2.  **Start Chat:** Start a conversation with the bot. You can use the `/start` or `/help` command to see the welcome message and instructions.
3.  **Download Video/Audio:**
    *   Send the command `/download` followed by the YouTube video link.
    *   **Example:** `/download https://www.youtube.com/watch?v=dQw4w9WgXcQ`
4.  **Choose Format:** The bot will reply with buttons asking you to choose the desired format: `🎬 Video (MP4)` or `🎵 Audio (MP3)`.
5.  **Wait:** Click the button for your chosen format. The bot will show status messages like "Starting download..." and "Uploading...".
6.  **Receive File:** Once the download and upload are complete (and within the size limit), the bot will send the MP4 video or MP3 audio file directly to you in the chat.

---

## 🚀 Advanced Features & Customization (Optional)

The current version provides basic download functionality. If you require more advanced features or custom modifications for your specific needs, these can be developed. Potential enhancements include:

*   **🔹 Selectable Video Quality:** Allow users to choose specific resolutions (e.g., 360p, 480p, 720p, 1080p) before downloading.
*   **🔹 YouTube Playlist Support:** Download all videos within a given YouTube playlist link.
*   **🔹 Enhanced Audio Options:** More control over audio quality (bitrate) or different audio formats (e.g., M4A, OGG).
*   **🔹 Google Drive Integration:** Automatically upload downloaded files to a specified Google Drive folder.
*   **🔹 Premium Mode / User Tiers:** Implement limitations for free users (e.g., download count, file size, quality) and offer premium access for unrestricted usage.
*   **🔹 Channel/User Whitelisting/Blacklisting:** Control who can use the bot.
*   **🔹 Custom Watermarking:** Add text or image watermarks to downloaded videos.
*   **🔹 Download Queue Management:** Handle multiple requests more gracefully.

**Interested in implementing these advanced features or discussing a custom bot project?**

Please feel free to reach out to me!

---

## 🔗 Contact Me

You can contact me through the following platforms for inquiries about advanced features, custom bot development, or other collaborations:

*   **GitHub:** [frenkiofficial](https://github.com/frenkiofficial)
*   **Hugging Face:** [frenkiofficial](https://huggingface.co/frenkiofficial)
*   **Telegram:** [@FrenkiOfficial](https://t.me/FrenkiOfficial)
*   **Twitter / X:** [@officialfrenki](https://twitter.com/officialfrenki)
*   **Fiverr:** [frenkimusic](https://www.fiverr.com/frenkimusic/)

---

*(Optional: Add a License section here if you choose one, e.g., MIT License)*
