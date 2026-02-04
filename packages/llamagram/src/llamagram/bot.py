import asyncio
import logging
import os
from pathlib import Path
from typing import cast

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ReactionEmoji
from telegram.ext import (
    Application,
    BaseHandler,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.ext._utils.types import HandlerCallback

from .constants import STR_TO_LOG_LEVEL
from .utils import (
    _escape_markdow_for_tg,
    _remove_temporary_report_file,
    _setup_agentfs,
    _write_temporary_report_file,
    handle_documents,
    handle_prompt,
    start,
)


async def start_tg(update: Update, context: CallbackContext) -> None:
    if update.message:
        val = start(update.message.from_user)
        await update.message.reply_text(val)
    else:
        raise ValueError("No message provided")


async def handle_documents_tg(update: Update, context: CallbackContext) -> None:
    if update.message and update.message.document:
        doc = update.message.document
        val = await handle_documents(document=doc, context=context)
        await update.message.reply_text(val)
    else:
        raise ValueError("No message or document provided")


async def handle_prompt_tg(update: Update, context: CallbackContext) -> None:
    if update.message and update.message.text:
        await update.message.set_reaction(reaction=ReactionEmoji.EYES)
        await update.message.reply_text(
            "Starting a new task, I will get back to you when I'm done!"
        )
        report, final_response = await handle_prompt(update.message.text)
        final_response = _escape_markdow_for_tg(final_response)
        report_path = await _write_temporary_report_file(report)
        await update.message.reply_markdown_v2(text=final_response)
        await update.message.reply_document(
            document=Path(report_path),
            caption="Here is the activity report for the last session",
        )
        await _remove_temporary_report_file(report_path)
    else:
        raise ValueError("No message provided")


async def error_handler(update: Update, context: CallbackContext) -> None:
    logging.error(f"An error occurred: {context.error}")
    if update.message:
        await update.message.reply_text(f"An error occurred: {str(context.error)}")


async def run_bot(log_level: str) -> None:
    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", None)
    if TOKEN is None:
        raise ValueError(
            "No TELEGRAM_BOT_TOKEN has been provided as an environment variable"
        )
    else:
        logging.basicConfig(
            level=STR_TO_LOG_LEVEL.get(log_level, logging.INFO),
            format="%(asctime)s [%(levelname)s] %(message)s",
        )
        await _setup_agentfs()
        logging.info("Starting Telegram bot...")
        application = Application.builder().token(TOKEN).build()
        cmd_handler = cast(BaseHandler, CommandHandler("start", start_tg))
        application.add_handler(cmd_handler)
        application.add_handler(
            MessageHandler(filters.Document.PDF, handle_documents_tg)
        )
        application.add_handler(MessageHandler(filters.TEXT, handle_prompt_tg))
        application.add_error_handler(cast(HandlerCallback, error_handler))
        if application.updater is not None:
            await application.initialize()
            await application.updater.start_polling()
            await application.start()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                logging.info("Received shutdown signal")
                return
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                return
            finally:
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
        else:
            raise TypeError("application.updater cannot be None")
