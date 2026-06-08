import re


async def down(event, args):
    client = event.client

    if not args:
        await event.delete()
        return

    url = args.strip()

    match = re.search(r"t\.me/([^/]+)/(\d+)", url)
    if not match:
        await event.delete()
        return

    chat = match.group(1)
    msg_id = int(match.group(2))

    try:
        entity = await client.get_entity(chat)
        msg = await client.get_messages(entity, ids=msg_id)

        if not msg:
            await event.delete()
            return

        # MEDIA
        if msg.media:
            file = await msg.download_media()

            await client.send_file(
                "me",
                file,
                caption=msg.text or ""
            )
        else:
            await client.send_message(
                "me",
                msg.text or ""
            )

        # DELETE COMMAND MESSAGE (NO OUTPUT)
        await event.delete()

    except:
        await event.delete()


def load(client, register):
    register("down", down)
