from telethon.tl.functions.contacts import GetBlockedRequest


async def stats(event, args):
    await event.edit("⏳ Loading statistics...")

    client = event.client

    users = 0
    bots = 0
    groups = 0
    channels = 0
    archived = 0
    all_chats = 0

    blocked_users = 0
    blocked_bots = 0
    total_blocked = 0

    # -----------------------
    # BLOCKED USERS
    # -----------------------
    offset = 0
    limit = 100

    while True:
        res = await client(GetBlockedRequest(offset=offset, limit=limit))

        for u in res.users:
            if getattr(u, "bot", False):
                blocked_bots += 1
            else:
                blocked_users += 1

        total_blocked += len(res.users)

        if len(res.users) < limit:
            break

        offset += limit

    # -----------------------
    # DIALOGS COUNT
    # -----------------------
    async for d in client.iter_dialogs():
        if getattr(d, "archived", False):
            archived += 1

        if d.is_user:
            if getattr(d.entity, "bot", False):
                bots += 1
            else:
                users += 1
            all_chats += 1

        elif d.is_group:
            groups += 1
            all_chats += 1

        elif d.is_channel:
            if getattr(d.entity, "megagroup", False):
                groups += 1
            else:
                channels += 1
            all_chats += 1

    # -----------------------
    # OUTPUT
    # -----------------------
    await event.edit(
        f"""
<b>📊 Account Statistics</b>

💜 <b>Total chats:</b> <code>{all_chats}</code>

👤 <b>Users:</b> <code>{users}</code>
🤖 <b>Bots:</b> <code>{bots}</code>
👥 <b>Groups:</b> <code>{groups}</code>
📢 <b>Channels:</b> <code>{channels}</code>
📨 <b>Archived:</b> <code>{archived}</code>

🚫 <b>Blocked total:</b> <code>{total_blocked}</code>
 ├ 👤 Users: <code>{blocked_users}</code>
 └ 🤖 Bots: <code>{blocked_bots}</code>
"""
    )


# -----------------------
# MODULE REGISTER
# -----------------------
def load(client, register):
    register("stats", stats)
