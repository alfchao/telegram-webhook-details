import json
import os
import sys
from pprint import pformat

import requests
import vercel_blob
from fastapi import FastAPI, Request, Depends, HTTPException
from loguru import logger
from pydantic_settings import BaseSettings

logger.remove()
logger.add(
    sys.stdout,
    level="DEBUG",
)


class Settings(BaseSettings):
    BOT_TOKEN: str = ''
    CUSTOM_DOMAIN: str = ''
    VERCEL_URL: str = ''
    BOT_DOMAIN: str = "api.telegram.org"
    TG_BOT_API: str = f"https://{BOT_DOMAIN}/bot"
    secret_token: str = 'alfchao'
    BLOB_READ_WRITE_TOKEN: str = ""


settings = Settings()


def set_webhook():
    webhook_info = get_webhook()
    receive_webhook_url = f"https://{settings.CUSTOM_DOMAIN or settings.VERCEL_URL}/"
    if webhook_info.get("result", {}).get("url") == receive_webhook_url:
        logger.info("webhook already set")
        return
    telegram_webhook = f"{settings.TG_BOT_API}{settings.BOT_TOKEN}/setWebhook"
    body = {
        "url": receive_webhook_url,
        "secret_token": settings.secret_token
    }
    rsp = requests.post(telegram_webhook.format(os.environ.get("TELEGRAM_BOT_TOKEN")), json=body)
    logger.info(f"set_webhook: {rsp.status_code} {pformat(rsp.json())}")


def get_webhook():
    telegram_webhook = f"{settings.TG_BOT_API}{settings.BOT_TOKEN}/getWebhookInfo"
    rsp = requests.get(telegram_webhook)
    logger.info(f"get_webhook: {rsp.status_code} {pformat(rsp.json())}")
    return rsp.json()


async def send_message(chat_id: int, text=None, json_body=None, parse_mode: str = 'MarkdownV2',
                       reply_message_id: int = None):
    """
    Send a message to a specific chat.
    :param json_body:
    :param chat_id:
    :param text:
    :param parse_mode:
    :param reply_message_id:
    :return:
    """
    telegram_sendmsg = f"{settings.TG_BOT_API}{settings.BOT_TOKEN}/sendMessage"
    send_body = {
        "chat_id": chat_id,
        "text": '',
        "reply_parameters": {
            "message_id": reply_message_id,
        }
    }
    if parse_mode:
        send_body["parse_mode"] = parse_mode
    if text:
        send_body['text'] = text
        logger.info(f"send_text: {pformat(text)}")
    elif json_body:
        send_body['text'] = json.dumps(json_body, indent=4, ensure_ascii=False)
        send_body['text'] = f"```json\n{send_body['text']}\n```"
        logger.info(f"send_json_body: {pformat(send_body)}")
    else:
        send_body['text'] = "无内容"
        logger.warning(f"send_message: {pformat(send_body['text'])}")
    logger.info(f"send_message: {pformat(send_body)}")
    rsp = requests.post(telegram_sendmsg, json=send_body)
    logger.info(f"send_message: {rsp.status_code} {pformat(rsp.json())}")


async def get_file(file_id):
    telegram_getfile = f"{settings.TG_BOT_API}{settings.BOT_TOKEN}/getFile"
    send_body = {
        "file_id": file_id
    }
    rsp = requests.post(telegram_getfile, json=send_body)
    logger.info(f"获取文件路径的响应: {pformat(rsp.json())}")
    file_path = rsp.json().get('result').get('file_path')
    return file_path


def verify_telegram_secret_token(request: Request) -> None:
    request_headers = dict(request.headers)

    if str(request_headers.get("x-telegram-bot-api-secret-token")) != settings.secret_token:
        raise HTTPException(status_code=403, detail="Forbidden")


def create_app():
    # set_webhook()
    app = FastAPI()

    @app.get("/")
    async def root(_: None = Depends(verify_telegram_secret_token)):
        return {"message": "Hello World"}

    @app.post("/")
    async def telegram_webhook(request: Request, _: None = Depends(verify_telegram_secret_token)):
        request_headers = dict(request.headers)
        request_body = await request.json()
        logger.info(f"request_body: {pformat(request_body)}")
        chat_id = request_body.get('message').get('chat').get('id')
        message_id = request_body.get('message').get('message_id')
        await send_message(chat_id=chat_id, json_body=request_headers,
                           reply_message_id=message_id)
        await send_message(chat_id=chat_id, json_body=request_body,
                           reply_message_id=message_id)

        # 如果收到一个文件，则再发送一个文件链接回去
        if request_body.get('message').get('document'):
            # 获取文件路径 getFile
            file_id = request_body.get('message').get('document').get('file_id')
            file_path = await get_file(file_id=file_id)
            file_download_url = f"https://{settings.BOT_DOMAIN}/file/bot{settings.BOT_TOKEN}/{file_path}"
            await send_message(chat_id=chat_id,
                               text=file_download_url,
                               reply_message_id=message_id,
                               parse_mode='')

            # 保存这个文件
            vercel_blob_put_result = vercel_blob.put(
                f"telegram/{request_body.get('message').get('document').get('file_name')}",
                requests.get(file_download_url).content,
                multipart=True, options={"allowOverwrite": True})
            logger.info(f"vercel_blob_put_result: {pformat(vercel_blob_put_result)}")

            # 发送文件下载链接
            await send_message(chat_id=chat_id,
                               text=vercel_blob_put_result['downloadUrl'],
                               reply_message_id=message_id,
                               parse_mode='')

        return {"status": "ok"}

    return app


app = create_app()

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
