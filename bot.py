import logging
import os
import re
import yt_dlp
from uuid import uuid4
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.constants import ParseMode

# --- Configuration ---
load_dotenv() # Load environment variables from .env file
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables or .env file")

# Max file size in MB for Telegram uploads (adjust as needed, free bots max is 50MB)
MAX_FILE_SIZE_MB = 49
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
DOWNLOAD_PATH = "downloads" # Directory to temporarily store downloads

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Helper Functions ---

def cleanup_file(file_path: str):
    """Deletes a file if it exists."""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Cleaned up file: {file_path}")
        except OSError as e:
            logger.error(f"Error deleting file {file_path}: {e}")

def is_valid_youtube_url(url: str) -> bool:
    """Basic check for YouTube URL patterns."""
    # Regex to match common YouTube URL patterns
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    return re.match(youtube_regex, url) is not None

# --- Telegram Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! 👋",
        reply_markup=InlineKeyboardMarkup([
             [InlineKeyboardButton("How to use?", callback_data="help_info")]
        ])
    )
    await help_command(update, context) # Also show help info

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends instructions when the /help command is issued or help button clicked."""
    help_text = (
        "🤖 **YouTube Downloader Bot**\n\n"
        "Send me a YouTube link and I'll help you download it!\n\n"
        "**How to use:**\n"
        "1. Use the command `/download <youtube_link>`\n"
        "   Example: `/download https://www.youtube.com/watch?v=dQw4w9WgXcQ`\n"
        "2. I will ask you to choose the format (MP4 Video or MP3 Audio).\n"
        "3. Select the format and I'll start downloading.\n\n"
        "**Note:**\n"
        f"🔹 Downloads are limited to **{MAX_FILE_SIZE_MB} MB** due to Telegram restrictions.\n"
        "🔹 Make sure you have `ffmpeg` installed on the server where the bot runs for audio conversion."
    )
    # Check if called from callback query or command
    if update.callback_query:
        await update.callback_query.answer() # Answer the callback query first
        await update.callback_query.edit_message_text(
            text=help_text, parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(text=help_text, parse_mode=ParseMode.MARKDOWN)


async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /download command, validates the URL, and asks for format."""
    if not context.args:
        await update.message.reply_text("Please provide a YouTube link after the command.\n"
                                         "Example: `/download https://youtu.be/dQw4w9WgXcQ`")
        return

    url = context.args[0]

    if not is_valid_youtube_url(url):
        await update.message.reply_text("Hmm, that doesn't look like a valid YouTube URL. Please try again.")
        return

    # Store url in context for the callback query
    # Using user_data is safer if multiple users interact concurrently
    context.user_data['url_to_download'] = url

    keyboard = [
        [
            InlineKeyboardButton("🎬 Video (MP4)", callback_data=f"download_video"),
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data=f"download_audio"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Choose download format:', reply_markup=reply_markup)


# --- Callback Query Handler (Button Clicks) ---

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button clicks for format selection or help."""
    query = update.callback_query
    await query.answer() # Acknowledge button press

    callback_data = query.data

    if callback_data == "help_info":
        await help_command(update, context)
        return

    # Retrieve the URL stored earlier
    url = context.user_data.get('url_to_download')
    if not url:
        await query.edit_message_text(text="Error: Could not find the URL to download. Please try the /download command again.")
        return

    # Clear the stored URL after retrieving it
    del context.user_data['url_to_download']

    download_type = "video" if "video" in callback_data else "audio"

    # Inform user download is starting
    try:
        await query.edit_message_text(text=f"⏳ Starting download for {download_type}... Please wait.")
    except Exception as e:
        logger.warning(f"Could not edit message (might be the same content): {e}")

    await process_download(update, context, url, download_type)


# --- Download Logic ---

async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, download_type: str):
    """Downloads the file using yt-dlp, checks size, and uploads."""
    query = update.callback_query # Get query to send messages later
    chat_id = query.message.chat_id
    message_id = query.message.message_id # To potentially edit status later

    # Create download directory if it doesn't exist
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)

    # Unique filename base to avoid collisions
    file_id = str(uuid4())
    output_template = os.path.join(DOWNLOAD_PATH, f"{file_id}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_template,
        'noplaylist': True, # Don't download playlists if a playlist link is given
        'logger': logger, # Use our logger
        'progress_hooks': [lambda d: download_progress_hook(d, context.bot, chat_id, message_id)],
        # Try to limit size *during* download if possible (less reliable than post-check)
        'max_filesize': MAX_FILE_SIZE_BYTES,
    }

    if download_type == "audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192', # Standard MP3 quality
            }],
            # Ensure the final file extension is .mp3
             'outtmpl': os.path.join(DOWNLOAD_PATH, f"{file_id}.mp3"),
        })
        final_extension = ".mp3"
    else: # Video
        ydl_opts.update({
            # Download best mp4 video format with audio. Fallback to best mp4 if separate streams exceed size.
            'format': f'bestvideo[ext=mp4][filesize<{MAX_FILE_SIZE_BYTES}]+bestaudio[ext=m4a][filesize<{MAX_FILE_SIZE_BYTES}]/best[ext=mp4][filesize<{MAX_FILE_SIZE_BYTES}]/mp4[filesize<{MAX_FILE_SIZE_BYTES}]',
            'merge_output_format': 'mp4', # Ensure merged output is mp4
        })
        final_extension = ".mp4" # Assume mp4, yt-dlp might correct it

    downloaded_file_path = None
    final_file_path = os.path.join(DOWNLOAD_PATH, f"{file_id}{final_extension}") # Predicted final path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            # yt-dlp might choose a slightly different extension if merging fails or format isn't available
            # Try to find the actual downloaded file
            downloaded_file_path = ydl.prepare_filename(info_dict)
            # Sometimes the template has '%(ext)s', sometimes it's resolved
            if not os.path.exists(downloaded_file_path):
                 # If the direct path doesn't exist (e.g., after postprocessing), use the predicted final path
                 if os.path.exists(final_file_path):
                      downloaded_file_path = final_file_path
                 else:
                      # Fallback: search directory for the file_id (less robust)
                      found = False
                      for f in os.listdir(DOWNLOAD_PATH):
                          if f.startswith(file_id):
                              downloaded_file_path = os.path.join(DOWNLOAD_PATH, f)
                              found = True
                              break
                      if not found:
                           raise FileNotFoundError(f"Could not locate downloaded file for ID {file_id}")

        logger.info(f"Download finished. File tentatively at: {downloaded_file_path}")

        # --- File Size Check (Crucial) ---
        if not os.path.exists(downloaded_file_path):
             raise FileNotFoundError(f"Downloaded file {downloaded_file_path} not found after yt-dlp finished.")

        file_size = os.path.getsize(downloaded_file_path)
        if file_size > MAX_FILE_SIZE_BYTES:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"❌ Error: File size ({file_size / 1024 / 1024:.2f} MB) exceeds the {MAX_FILE_SIZE_MB} MB limit."
            )
            cleanup_file(downloaded_file_path)
            return

        # --- Uploading ---
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text="⬆️ Uploading to Telegram..."
        )

        caption_text = info_dict.get('title', 'YouTube Download') # Get title if available

        if download_type == "audio":
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=open(downloaded_file_path, 'rb'),
                caption=caption_text,
                filename=os.path.basename(downloaded_file_path), # Use actual filename
                # You might want to extract duration/performer if needed from info_dict
                # duration=info_dict.get('duration'),
                # performer=info_dict.get('uploader') or info_dict.get('channel')
            )
        else: # Video
             # Try getting thumbnail (optional)
            thumbnail_url = info_dict.get('thumbnail')
            thumb_path = None
            # Note: Downloading thumbnail adds complexity, skipping for this basic version.
            # You'd typically download the thumbnail separately if needed.

            await context.bot.send_video(
                chat_id=chat_id,
                video=open(downloaded_file_path, 'rb'),
                caption=caption_text,
                filename=os.path.basename(downloaded_file_path), # Use actual filename
                # width=info_dict.get('width'), # Optional
                # height=info_dict.get('height'), # Optional
                # duration=info_dict.get('duration'), # Optional
                # supports_streaming=True # Generally true for videos
            )

        # Delete the original status message ("Choose format...") after successful upload
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp download error for {url}: {e}")
        error_message = f"❌ Download Error: {e}"
        # Check for specific common errors
        if "File is larger than max-filesize" in str(e):
             error_message = f"❌ Error: Video is larger than the {MAX_FILE_SIZE_MB}MB limit allowed by the bot."
        elif "Video unavailable" in str(e):
             error_message = "❌ Error: This video is unavailable."
        elif "Private video" in str(e):
             error_message = "❌ Error: This video is private."
        elif "Premiere" in str(e):
            error_message = "❌ Error: Livestreams/premieres that haven't finished cannot be downloaded yet."

        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=error_message)
        except Exception as edit_err:
             logger.warning(f"Could not edit message to show download error: {edit_err}")
             # If editing fails, send a new message
             await context.bot.send_message(chat_id=chat_id, text=error_message)

    except FileNotFoundError as e:
         logger.error(f"File not found error: {e}")
         await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ Error: Could not find the downloaded file on the server.")

    except Exception as e:
        logger.error(f"An unexpected error occurred during download/upload for {url}: {e}", exc_info=True)
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=f"❌ An unexpected error occurred: {e}"
            )
        except Exception as edit_err:
            logger.warning(f"Could not edit message to show unexpected error: {edit_err}")
            await context.bot.send_message(chat_id=chat_id, text=f"❌ An unexpected error occurred.")

    finally:
        # --- Cleanup ---
        if downloaded_file_path:
            cleanup_file(downloaded_file_path)
        # Clean up any other potential temp files if needed (e.g., separate audio/video before merge)
        # This simple version relies mainly on the single output file cleanup.

# --- yt-dlp Progress Hook ---
# Note: This hook can be called very frequently. Editing messages too often can lead to rate limiting.
# A more advanced implementation might only update the message every few seconds.
async def download_progress_hook(d, bot, chat_id, message_id):
    """Reports download progress."""
    if d['status'] == 'downloading':
        try:
            # Simple progress reporting - you could make this fancier
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            # logger.info(f"Downloading: {percent} at {speed}, ETA: {eta}")
            # Optional: Update Telegram message (be mindful of rate limits)
            # await bot.edit_message_text(f"⏳ Downloading... {percent} done", chat_id=chat_id, message_id=message_id)
        except Exception as e:
            # Ignore errors here, usually 'message is not modified' if percent didn't change
            # logger.warning(f"Progress hook update failed: {e}")
            pass
    elif d['status'] == 'finished':
        logger.info(f"Finished downloading {d.get('filename')}, now post-processing or checking...")
    elif d['status'] == 'error':
        logger.error(f"yt-dlp reported an error during download: {d.get('filename')}")


# --- Main Bot Execution ---

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("download", download_command))

    # handler for button clicks
    application.add_handler(CallbackQueryHandler(button_callback))

    # Optional: Add a handler for non-command messages (e.g., if user just sends a link)
    # async def handle_plain_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #     url = update.message.text
    #     if is_valid_youtube_url(url):
    #         # Simulate calling /download <url>
    #         context.args = [url]
    #         await download_command(update, context)
    #     else:
    #         await update.message.reply_text("Send /help to see how to use me.")
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plain_link))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
