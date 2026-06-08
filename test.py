from .. import loader, utils


@loader.tds
class EchoMod(loader.Module):
    """Simple echo module"""

    strings = {
        "name": "Echo",
        "usage": "Write: .echo text"
    }

    @loader.command("echo", doc="Echo your text")
    async def echo(self, message):
        text = utils.get_args_raw(message)

        if not text:
            return await utils.answer(message, "❌ Usage: .echo text")

        await utils.answer(message, f"📢 Echo: <b>{text}</b>")


    @loader.command("id", doc="Get user ID")
    async def id(self, message):
        reply = await message.get_reply_message()

        if reply:
            user = await self.client.get_entity(reply.sender_id)
        else:
            user = await self.client.get_entity(message.sender_id)

        await utils.answer(message, f"🆔 ID: <code>{user.id}</code>")
