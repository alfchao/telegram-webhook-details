# Telegram Webhook 详情查看器（FastAPI 版）

本项目基于 Python 的 FastAPI 框架开发，旨在接收并打印 Telegram Bot Webhook 的请求体，方便开发者调试和查看 Telegram 推送的原始数据。项目可直接部署在 [Vercel](https://vercel.com/) 。

## 功能特性

- 自动回复收到的webhook请求体，方便开发者调试。

## 快速开始

### 1. 部署到 Vercel

1. 克隆本仓库。
2. 使用此项目部署到 Vercel。
3. 设置环境变量 BOT_TOKEN，可设置自定义域名 CUSTOM_DOMAIN 。
4. 重新部署即可生效。