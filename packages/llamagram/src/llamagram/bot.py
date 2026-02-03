import asyncio
import logging
import os
from typing import cast

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

from .utils import _setup_agentfs, handle_documents, handle_prompt, start


async def start_tg(update: Update, context: CallbackContext) -> None:
    val = start()
    if update.message:
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
        report = await handle_prompt(update.message.text)
        await update.message.reply_markdown_v2(text=report)
    else:
        raise ValueError("No message provided")


async def error_handler(update: Update, context: CallbackContext) -> None:
    logging.error(f"An error occurred: {context.error}")
    if update.message:
        await update.message.reply_text(f"An error occurred: {str(context.error)}")


async def run_bot() -> None:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", None)
    if TOKEN is None:
        raise ValueError(
            "No TELEGRAM_BOT_TOKEN has been provided as an environment variable"
        )
    else:
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
        application.run_polling(1.0)


def main() -> None:
    asyncio.run(run_bot())
