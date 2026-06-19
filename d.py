# modules/sender.py - Avtomatik xabar yuboruvchi modul

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from telethon import Button
from telethon.tl.custom import Message
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument, 
    MessageMediaWebPage, MessageMediaAudio,
    MessageMediaVoice, MessageMediaVideo
)

class SenderMod:
    """Avtomatik xabar yuboruvchi modul - 24/7 ishlaydi"""
    
    strings = {"name": "SenderMod"}
    
    def __init__(self):
        self.client = None
        self._db = None
        self.config = {}
        self.settings_file = "modules/sender_data.json"
        self._is_running = False
        self._task = None
        self._load_settings()
    
    async def client_ready(self, client, db):
        self.client = client
        self._db = db
        self._load_settings()
        print("✅ SenderMod tayyor!")
        
        # Avtomatik ishga tushirish
        if self.config.get("auto_start", True):
            await self.start_sending()
    
    def _load_settings(self):
        default = {
            "interval": 60,  # soniyalarda
            "timezone": 5,  # UTC+5
            "all_groups": True,
            "selected_groups": [],
            "saved_posts": {},
            "auto_start": True,
            "post_status": {},  # post_id -> {"active": True/False, "last_sent": timestamp}
            "send_count": 0,
            "last_send": None
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config = {**default, **data}
                return
            except:
                pass
        
        self.config = default
        self._save_settings()
    
    def _save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Saqlash xatosi: {e}")
    
    def _get_current_time(self):
        tz = self.config.get("timezone", 5)
        return datetime.utcnow() + timedelta(hours=tz)
    
    def _format_time(self, dt):
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    
    def _get_target_chats(self):
        """Yuboriladigan guruhlar ro'yxati"""
        chats = []
        
        if self.config.get("all_groups", True):
            # Barcha guruhlar (bot a'zo bo'lgan)
            try:
                for dialog in self.client.iter_dialogs():
                    if dialog.is_group:
                        chats.append(dialog.entity)
            except:
                pass
        else:
            # Tanlangan guruhlar
            for group_name in self.config.get("selected_groups", []):
                try:
                    entity = self.client.get_entity(group_name)
                    chats.append(entity)
                except:
                    print(f"⚠️ Guruh topilmadi: {group_name}")
        
        return chats
    
    # ==================== ASOSIY SENDER FUNKSIYASI ====================
    
    async def _send_post_to_chat(self, chat, post_id, post_data):
        """Postni chatga yuborish"""
        try:
            # Post holatini tekshirish
            status = self.config.get("post_status", {}).get(post_id, {})
            if not status.get("active", True):
                return False
            
            text = post_data.get("text", "")
            media_path = post_data.get("media")
            
            if media_path and os.path.exists(media_path):
                # Media bilan yuborish
                await self.client.send_file(
                    chat,
                    media_path,
                    caption=text,
                    parse_mode='html'
                )
            else:
                # Faqat matn
                await self.client.send_message(chat, text, parse_mode='html')
            
            # Statistikani yangilash
            self.config["send_count"] = self.config.get("send_count", 0) + 1
            self.config["last_send"] = self._format_time(self._get_current_time())
            
            status["last_sent"] = time.time()
            self.config["post_status"][post_id] = status
            self._save_settings()
            
            return True
            
        except Exception as e:
            print(f"❌ Yuborish xatosi: {e}")
            return False
    
    async def _sender_loop(self):
        """Asosiy yuborish sikli - 24/7"""
        print("🔄 Sender loop ishga tushdi!")
        
        while self._is_running:
            try:
                # Vaqt oralig'ini olish
                interval = self.config.get("interval", 60)
                
                # Yuboriladigan postlarni olish (faqat faollari)
                saved_posts = self.config.get("saved_posts", {})
                post_status = self.config.get("post_status", {})
                
                active_posts = []
                for post_id, data in saved_posts.items():
                    status = post_status.get(post_id, {})
                    if status.get("active", True):
                        active_posts.append((post_id, data))
                
                if active_posts:
                    # Guruhlarni olish
                    chats = self._get_target_chats()
                    
                    if chats:
                        print(f"📤 {len(active_posts)} ta post {len(chats)} ta guruhga yuborilmoqda...")
                        
                        for post_id, post_data in active_posts:
                            for chat in chats:
                                await self._send_post_to_chat(chat, post_id, post_data)
                                await asyncio.sleep(1)  # Spam oldini olish
                    else:
                        print("⚠️ Yuborish uchun guruh topilmadi")
                else:
                    print("💤 Faol postlar yo'q")
                
                # Intervalgacha kutish
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                print("⏹ Sender loop to'xtatildi")
                break
            except Exception as e:
                print(f"❌ Sender loop xatosi: {e}")
                await asyncio.sleep(10)
    
    # ==================== BUYRUQLAR ====================
    
    async def settings(self, message):
        """Sozlamalar paneli - .settings"""
        posts = self.config.get("saved_posts", {})
        post_status = self.config.get("post_status", {})
        active_posts = sum(1 for p in posts if post_status.get(p, {}).get("active", True))
        
        text = (
            f"⚙️ **Sozlamalar paneli**\n\n"
            f"🕐 **Vaqt zonasi:** UTC+{self.config.get('timezone', 5)}\n"
            f"⏱ **Oraliq vaqt:** {self.config.get('interval', 60)} soniya\n"
            f"🔄 **Barcha guruhlar:** {'✅ Yoqilgan' if self.config.get('all_groups', True) else '❌ Oʻchirilgan'}\n"
            f"📋 **Tanlangan guruhlar:** {len(self.config.get('selected_groups', []))} ta\n"
            f"📦 **Saqlangan postlar:** {len(posts)} ta ({active_posts} ta faol)\n"
            f"📊 **Jami yuborilgan:** {self.config.get('send_count', 0)} ta\n"
            f"🕐 **Oxirgi yuborish:** {self.config.get('last_send', 'Yoʻq')}\n"
            f"🔄 **Holat:** {'✅ Ishlamoqda' if self._is_running else '❌ Toʻxtatilgan'}\n\n"
            f"📝 **Buyruqlar:**\n"
            f"  `.interval 120` - Vaqt oraligʻini oʻrnatish\n"
            f"  `.settimezone 5` - Vaqt zonasini oʻrnatish\n"
            f"  `.groups on/off` - Barcha guruhlarni yoqish/oʻchirish\n"
            f"  `.addgroup @username` - Guruh qoʻshish\n"
            f"  `.delgroup @username` - Guruh oʻchirish\n"
            f"  `.listgroups` - Guruhlar roʻyxati\n"
            f"  `.copy` - Postni saqlash (reply qiling)\n"
            f"  `.myposts` - Saqlangan postlar\n"
            f"  `.poston/off <id>` - Postni yoqish/oʻchirish\n"
            f"  `.start` - Yuborishni boshlash\n"
            f"  `.stop` - Yuborishni toʻxtatish"
        )
        
        # Inline tugmalar
        buttons = [
            [Button.inline("📦 Postlar", b"show_posts")],
            [Button.inline("▶️ Boshlash", b"start_sender"), Button.inline("⏹ To'xtatish", b"stop_sender")],
            [Button.inline("📊 Statistika", b"show_stats")]
        ]
        
        await message.edit(text, buttons=buttons)
    
    async def interval(self, message):
        """Oraliq vaqtni o'rnatish - .interval 120"""
        args = message.raw_text.split(maxsplit=1)
        args = args[1] if len(args) > 1 else ""
        
        if not args:
            await message.edit("❌ Vaqtni kiriting!\nMisol: `.interval 120` (soniyalarda)")
            return
        
        try:
            interval = int(args.strip())
            if interval < 10:
                await message.edit("❌ Minimal interval 10 soniya")
                return
            
            self.config["interval"] = interval
            self._save_settings()
            await message.edit(f"✅ Oraliq vaqt {interval} soniyaga oʻrnatildi!")
        except ValueError:
            await message.edit("❌ To'g'ri raqam kiriting!")
    
    async def settimezone(self, message):
        """Vaqt zonasini o'rnatish - .settimezone 5"""
        args = message.raw_text.split(maxsplit=1)
        args = args[1] if len(args) > 1 else ""
        
        if not args:
            await message.edit("❌ Vaqt zonasini kiriting!\nMisol: `.settimezone 5`")
            return
        
        try:
            tz = int(args.strip())
            if tz < -12 or tz > 14:
                await message.edit("❌ Vaqt zonasi -12 dan 14 gacha")
                return
            
            self.config["timezone"] = tz
            self._save_settings()
            await message.edit(f"✅ Vaqt zonasi UTC+{tz} ga oʻrnatildi!")
        except ValueError:
            await message.edit("❌ To'g'ri raqam kiriting!")
    
    async def groups(self, message):
        """Barcha guruhlarni yoqish/o'chirish - .groups on/off"""
        args = message.raw_text.split(maxsplit=1)
        args = args[1] if len(args) > 1 else ""
        
        if not args or args.lower() not in ['on', 'off']:
            await message.edit("❌ `.groups on` yoki `.groups off`")
            return
        
        self.config["all_groups"] = args.lower() == 'on'
        self._save_settings()
        
        status = "✅ YOQILDI" if self.config["all_groups"] else "❌ OʻCHIRILDI"
        await message.edit(f"🔄 Barcha guruhlar {status}")
    
    async def addgroup(self, message):
        """Guruh qo'shish - .addgroup @username"""
        args = message.raw_text.split(maxsplit=1)
        args = args[1] if len(args) > 1 else ""
        
        if not args:
            await message.edit("❌ Guruh nomini kiriting!\nMisol: `.addgroup @mygroup`")
            return
        
        group = args.strip()
        if not group.startswith('@'):
            group = '@' + group
        
        if group not in self.config["selected_groups"]:
            self.config["selected_groups"].append(group)
            self._save_settings()
            await message.edit(f"✅ `{group}` qoʻshildi!")
        else:
            await message.edit(f"⚠️ `{group}` allaqachon roʻyxatda")
    
    async def delgroup(self, message):
        """Guruh o'chirish - .delgroup @username"""
        args = message.raw_text.split(maxsplit=1)
        args = args[1] if len(args) > 1 else ""
        
        if not args:
            await message.edit("❌ Guruh nomini kiriting!")
            return
        
        group = args.strip()
        if not group.startswith('@'):
            group = '@' + group
        
        if group in self.config["selected_groups"]:
            self.config["selected_groups"].remove(group)
            self._save_settings()
            await message.edit(f"✅ `{group}` oʻchirildi!")
        else:
            await message.edit(f"❌ `{group}` topilmadi")
    
    async def listgroups(self, message):
        """Guruhlar ro'yxati - .listgroups"""
        groups = self.config.get("selected_groups", [])
        
        if not groups:
            await message.edit("📋 Hech qanday guruh tanlanmagan")
            return
        
        text = f"📋 **Tanlangan guruhlar ({len(groups)}):**\n\n"
        text += "\n".join(f"• {g}" for g in groups)
        text += f"\n\n🔄 Barcha guruhlar: {'✅' if self.config.get('all_groups', True) else '❌'}"
        
        await message.edit(text)
    
    # ==================== COPY BUYRUG'I ====================
    
    async def copy(self, message):
        """Postni saqlash - .copy (reply qiling)"""
        reply = await message.get_reply_message()
        
        if not reply:
            await message.edit("❌ Postga reply qiling!")
            return
        
        try:
            post_id = f"post_{int(time.time())}"
            
            post_data = {
                "id": post_id,
                "text": reply.raw_text or reply.text or "",
                "media": None,
                "media_type": None,
                "date": self._format_time(self._get_current_time()),
                "sender": reply.sender_id,
                "chat": reply.chat_id
            }
            
            # Mediani saqlash
            if reply.media:
                try:
                    os.makedirs("modules/media", exist_ok=True)
                    media_path = f"modules/media/{post_id}"
                    
                    if reply.photo:
                        file_path = await reply.download_media(file=media_path + ".jpg")
                        post_data["media"] = file_path
                        post_data["media_type"] = "photo"
                    elif reply.document:
                        file_path = await reply.download_media(file=media_path + "_file")
                        post_data["media"] = file_path
                        post_data["media_type"] = "document"
                    elif reply.audio:
                        file_path = await reply.download_media(file=media_path + ".mp3")
                        post_data["media"] = file_path
                        post_data["media_type"] = "audio"
                    elif reply.voice:
                        file_path = await reply.download_media(file=media_path + ".ogg")
                        post_data["media"] = file_path
                        post_data["media_type"] = "voice"
                    elif reply.video:
                        file_path = await reply.download_media(file=media_path + ".mp4")
                        post_data["media"] = file_path
                        post_data["media_type"] = "video"
                    elif reply.sticker:
                        file_path = await reply.download_media(file=media_path + ".webp")
                        post_data["media"] = file_path
                        post_data["media_type"] = "sticker"
                    elif reply.gif:
                        file_path = await reply.download_media(file=media_path + ".gif")
                        post_data["media"] = file_path
                        post_data["media_type"] = "gif"
                    else:
                        file_path = await reply.download_media(file=media_path)
                        post_data["media"] = file_path
                        post_data["media_type"] = "file"
                except Exception as e:
                    print(f"Media saqlash xatosi: {e}")
            
            # Saqlash
            saved_posts = self.config.get("saved_posts", {})
            saved_posts[post_id] = post_data
            self.config["saved_posts"] = saved_posts
            
            # Holatni qo'shish
            if "post_status" not in self.config:
                self.config["post_status"] = {}
            self.config["post_status"][post_id] = {"active": True, "last_sent": None}
            
            self._save_settings()
            
            await message.edit(
                f"✅ **Post saqlandi!**\n\n"
                f"🆔 ID: `{post_id}`\n"
                f"📝 Matn: {len(post_data['text'])} belgi\n"
                f"🖼 Media: {'✅ Bor' if post_data['media'] else '❌ Yoʻq'}\n"
                f"📅 Sana: {post_data['date']}\n"
                f"🔄 Holat: ✅ Faol\n\n"
                f"📤 `.myposts` bilan koʻring"
            )
            
        except Exception as e:
            await message.edit(f"❌ Xatolik: {e}")
            traceback.print_exc()
    
    async def myposts(self, message):
        """Saqlangan postlar - .myposts"""
        saved_posts = self.config.get("saved_posts", {})
        post_status = self.config.get("post_status", {})
        
        if not saved_posts:
            await message.edit("📦 Hech qanday post saqlanmagan")
            return
        
        text = f"📦 **Saqlangan postlar ({len(saved_posts)}):**\n\n"
        
        for post_id, data in list(saved_posts.items())[:10]:
            status = post_status.get(post_id, {}).get("active", True)
            status_icon = "✅" if status else "❌"
            text += f"• **ID:** `{post_id}` {status_icon}\n"
            text += f"  📅 {data.get('date', 'Nomaʼlum')}\n"
            text += f"  📝 {data.get('text', '')[:50]}...\n\n"
        
        if len(saved_posts) > 10:
            text += f"\n📌 Jami: {len(saved_posts)} ta post\n"
        
        text += f"\n📤 `.poston/off <id>` - Yoqish/oʻchirish"
        
        await message.edit(text)
    
    async def poston(self, message):
        """Postni yoqish - .poston post_id"""
        args = message.raw_text.split(maxsplit=1)
        args = args[1] if len(args) > 1 else ""
        
        if not args:
            await message.edit("❌ Post ID sini kiriting!\nMisol: `.poston post_123456`")
            return
        
        post_id = args.strip()
        saved_posts = self.config.get("saved_posts", {})
        
        if post_id not in saved_posts:
            await message.edit(f"❌ `{post_id}` topilmadi!")
            return
        
        if "post_status" not in self.config:
            self.config["post_status"] = {}
        self.config["post_status"][post_id] = {"active": True, "last_sent": None}
        self._save_settings()
        
        await message.edit(f"✅ `{post_id}` faollashtirildi!")
    
    async def posto ff(self, message):
        """Postni o'chirish - .postoff post_id"""
        args = message.raw_text.split(maxsplit=1)
        args = args[1] if len(args) > 1 else ""
        
        if not args:
            await message.edit("❌ Post ID sini kiriting!\nMisol: `.postoff post_123456`")
            return
        
        post_id = args.strip()
        saved_posts = self.config.get("saved_posts", {})
        
        if post_id not in saved_posts:
            await message.edit(f"❌ `{post_id}` topilmadi!")
            return
        
        if "post_status" not in self.config:
            self.config["post_status"] = {}
        self.config["post_status"][post_id] = {"active": False, "last_sent": None}
        self._save_settings()
        
        await message.edit(f"✅ `{post_id}` oʻchirildi!")
    
    async def delpost(self, message):
        """Postni butunlay o'chirish - .delpost post_id"""
        args = message.raw_text.split(maxsplit=1)
        args = args[1] if len(args) > 1 else ""
        
        if not args:
            await message.edit("❌ Post ID sini kiriting!")
            return
        
        post_id = args.strip()
        saved_posts = self.config.get("saved_posts", {})
        
        if post_id not in saved_posts:
            await message.edit(f"❌ `{post_id}` topilmadi!")
            return
        
        # Median o'chirish
        post_data = saved_posts[post_id]
        if post_data.get("media") and os.path.exists(post_data["media"]):
            try:
                os.remove(post_data["media"])
            except:
                pass
        
        del saved_posts[post_id]
        if "post_status" in self.config and post_id in self.config["post_status"]:
            del self.config["post_status"][post_id]
        
        self._save_settings()
        await message.edit(f"✅ `{post_id}` oʻchirildi!")
    
    # ==================== START/STOP ====================
    
    async def start(self, message):
        """Yuborishni boshlash - .start"""
        if self._is_running:
            await message.edit("⚠️ Yuborish allaqachon ishlamoqda!")
            return
        
        await self.start_sending()
        await message.edit("✅ Yuborish boshlandi!")
    
    async def stop(self, message):
        """Yuborishni to'xtatish - .stop"""
        if not self._is_running:
            await message.edit("⚠️ Yuborish to'xtatilgan!")
            return
        
        await self.stop_sending()
        await message.edit("⏹ Yuborish to'xtatildi!")
    
    async def start_sending(self):
        """Yuborishni boshlash (ichki)"""
        if self._is_running:
            return
        
        self._is_running = True
        self._task = asyncio.create_task(self._sender_loop())
        self.config["auto_start"] = True
        self._save_settings()
    
    async def stop_sending(self):
        """Yuborishni to'xtatish (ichki)"""
        if not self._is_running:
            return
        
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except:
                pass
            self._task = None
        
        self.config["auto_start"] = False
        self._save_settings()
    
    async def on_unload(self):
        """Modul o'chirilganda"""
        await self.stop_sending()


# ==================== INLINE CALLBACK HANDLER ====================

async def handle_inline_callback(event, bot):
    """Inline tugmalarni qayta ishlash"""
    data = event.data.decode()
    message = event.message
    
    if data == "show_posts":
        # Postlar ro'yxatini ko'rsatish
        saved_posts = bot.sender_mod.config.get("saved_posts", {})
        if not saved_posts:
            await event.answer("Hech qanday post yo'q", alert=True)
            return
        
        text = "📦 **Saqlangan postlar:**\n\n"
        for pid, data in list(saved_posts.items())[:5]:
            status = bot.sender_mod.config.get("post_status", {}).get(pid, {}).get("active", True)
            icon = "✅" if status else "❌"
            text += f"• `{pid}` {icon} - {data.get('text', '')[:30]}...\n"
        
        await event.edit(text, buttons=[Button.inline("🔙 Orqaga", b"back_to_settings")])
    
    elif data == "start_sender":
        await bot.sender_mod.start_sending()
        await event.answer("✅ Yuborish boshlandi!", alert=True)
        await event.edit("✅ Yuborish boshlandi!", buttons=[Button.inline("🔙 Orqaga", b"back_to_settings")])
    
    elif data == "stop_sender":
        await bot.sender_mod.stop_sending()
        await event.answer("⏹ Yuborish to'xtatildi!", alert=True)
        await event.edit("⏹ Yuborish to'xtatildi!", buttons=[Button.inline("🔙 Orqaga", b"back_to_settings")])
    
    elif data == "show_stats":
        stats = bot.sender_mod.config
        text = (
            f"📊 **Statistika**\n\n"
            f"📤 Yuborilgan: {stats.get('send_count', 0)} ta\n"
            f"🕐 Oxirgi yuborish: {stats.get('last_send', 'Yoʻq')}\n"
            f"📦 Postlar: {len(stats.get('saved_posts', {}))} ta\n"
            f"📋 Guruhlar: {len(stats.get('selected_groups', []))} ta\n"
            f"⏱ Interval: {stats.get('interval', 60)} soniya\n"
            f"🔄 Holat: {'✅ Ishlamoqda' if bot.sender_mod._is_running else '❌ Toʻxtatilgan'}"
        )
        await event.edit(text, buttons=[Button.inline("🔙 Orqaga", b"back_to_settings")])
    
    elif data == "back_to_settings":
        # Settings ga qaytish
        await bot.sender_mod.settings(message)
        await event.answer()
