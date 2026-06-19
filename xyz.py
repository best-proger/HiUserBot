# modules/autopost.py - Tuzatilgan importlar bilan

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from telethon import Button, events
from telethon.tl.custom import Message
from telethon.tl.types import (
    MessageMediaPhoto, 
    MessageMediaDocument, 
    MessageMediaWebPage
)

class AutoPostMod:
    """Avtomatik xabar yuboruvchi - 1 post, minut bilan interval"""
    
    strings = {"name": "AutoPostMod"}
    
    def __init__(self):
        self.client = None
        self._db = None
        self.config = {}
        self.settings_file = "modules/autopost_data.json"
        self._is_running = False
        self._task = None
        self._load_settings()
    
    async def client_ready(self, client, db):
        self.client = client
        self._db = db
        self._load_settings()
        print("✅ AutoPostMod tayyor!")
        
        if self.config.get("auto_start", True):
            await self.start_sending()
    
    def _load_settings(self):
        default = {
            "interval_minutes": 5,
            "all_groups": False,
            "selected_groups": [],
            "saved_post": None,
            "post_active": False,
            "auto_start": True,
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
        return datetime.now()
    
    def _format_time(self, dt):
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    
    def _get_target_chats(self):
        chats = []
        
        if self.config.get("all_groups", False):
            try:
                for dialog in self.client.iter_dialogs():
                    if dialog.is_group:
                        chats.append(dialog.entity)
            except:
                pass
        else:
            for group_name in self.config.get("selected_groups", []):
                try:
                    entity = self.client.get_entity(group_name)
                    chats.append(entity)
                except:
                    print(f"⚠️ Guruh topilmadi: {group_name}")
        
        return chats
    
    async def _send_post_to_chat(self, chat):
        post_data = self.config.get("saved_post")
        
        if not post_data or not self.config.get("post_active", False):
            return False
        
        try:
            text = post_data.get("text", "")
            media_path = post_data.get("media")
            
            if media_path and os.path.exists(media_path):
                await self.client.send_file(
                    chat,
                    media_path,
                    caption=text,
                    parse_mode='html'
                )
            else:
                await self.client.send_message(chat, text, parse_mode='html')
            
            self.config["send_count"] = self.config.get("send_count", 0) + 1
            self.config["last_send"] = self._format_time(self._get_current_time())
            self._save_settings()
            
            return True
            
        except Exception as e:
            print(f"❌ Yuborish xatosi: {e}")
            return False
    
    async def _sender_loop(self):
        print("🔄 Sender loop ishga tushdi!")
        
        while self._is_running:
            try:
                interval = self.config.get("interval_minutes", 5) * 60
                
                post_data = self.config.get("saved_post")
                is_active = self.config.get("post_active", False)
                
                if post_data and is_active:
                    chats = self._get_target_chats()
                    
                    if chats:
                        print(f"📤 {len(chats)} ta guruhga yuborilmoqda...")
                        for chat in chats:
                            await self._send_post_to_chat(chat)
                            await asyncio.sleep(2)
                    else:
                        print("⚠️ Yuborish uchun guruh yo'q")
                else:
                    print("💤 Post mavjud emas yoki o'chirilgan")
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                print("⏹ Sender loop to'xtatildi")
                break
            except Exception as e:
                print(f"❌ Sender loop xatosi: {e}")
                await asyncio.sleep(10)
    
    # ==================== SETTINGS ====================
    
    async def settings(self, message):
        post_data = self.config.get("saved_post")
        is_active = self.config.get("post_active", False)
        
        text = (
            f"⚙️ **Sozlamalar paneli**\n\n"
            f"⏱ **Oraliq vaqt:** {self.config.get('interval_minutes', 5)} daqiqa\n"
            f"🔄 **Barcha guruhlar:** {'✅ Yoqilgan' if self.config.get('all_groups', False) else '❌ Oʻchirilgan'}\n"
            f"📋 **Tanlangan guruhlar:** {len(self.config.get('selected_groups', []))} ta\n"
            f"📦 **Post:** {'✅ Bor' if post_data else '❌ Yoʻq'}\n"
            f"🔄 **Post holati:** {'✅ Faol' if is_active else '❌ Oʻchirilgan'}\n"
            f"📊 **Jami yuborilgan:** {self.config.get('send_count', 0)} ta\n"
            f"🕐 **Oxirgi yuborish:** {self.config.get('last_send', 'Yoʻq')}\n"
            f"🔄 **Bot holati:** {'✅ Ishlamoqda' if self._is_running else '❌ Toʻxtatilgan'}\n\n"
            f"📝 **Buyruqlar:**\n"
            f"  `.interval 5` - Vaqt oraligʻi (daqiqa)\n"
            f"  `.add` - Guruh qoʻshish (guruhda yozing)\n"
            f"  `.del @username` - Guruh oʻchirish\n"
            f"  `.list` - Guruhlar roʻyxati\n"
            f"  `.copy` - Post saqlash (reply qiling)\n"
            f"  `.show` - Saqlangan postni koʻrish\n"
            f"  `.poston` - Postni yoqish\n"
            f"  `.postoff` - Postni oʻchirish\n"
            f"  `.delpost` - Postni butunlay oʻchirish\n"
            f"  `.start` - Yuborishni boshlash\n"
            f"  `.stop` - Yuborishni toʻxtatish"
        )
        
        buttons = [
            [Button.inline("📦 Post", b"show_post"), Button.inline("📊 Statistika", b"show_stats")],
            [Button.inline("▶️ Boshlash", b"start_sender"), Button.inline("⏹ To'xtatish", b"stop_sender")]
        ]
        
        await message.edit(text, buttons=buttons)
    
    # ==================== INTERVAL ====================
    
    async def interval(self, message):
        args = message.raw_text.split(maxsplit=1)
        args = args[1] if len(args) > 1 else ""
        
        if not args:
            await message.edit("❌ Vaqtni kiriting!\nMisol: `.interval 5` (daqiqalarda)")
            return
        
        try:
            minutes = int(args.strip())
            if minutes < 1:
                await message.edit("❌ Minimal interval 1 daqiqa")
                return
            
            self.config["interval_minutes"] = minutes
            self._save_settings()
            await message.edit(f"✅ Oraliq vaqt {minutes} daqiqaga oʻrnatildi!")
        except ValueError:
            await message.edit("❌ To'g'ri raqam kiriting!")
    
    # ==================== GURUHLAR ====================
    
    async def add(self, message):
        chat = await message.get_chat()
        
        if not chat.is_group:
            await message.edit("❌ Bu buyruq faqat guruhda ishlaydi!")
            return
        
        group_name = f"@{chat.username}" if chat.username else str(chat.id)
        
        if group_name not in self.config["selected_groups"]:
            self.config["selected_groups"].append(group_name)
            self._save_settings()
            await message.edit(f"✅ **{chat.title}** qoʻshildi!\n📋 Jami: {len(self.config['selected_groups'])} ta")
        else:
            await message.edit(f"⚠️ **{chat.title}** allaqachon roʻyxatda")
    
    async def delete(self, message):
        args = message.raw_text.split(maxsplit=1)
        args = args[1] if len(args) > 1 else ""
        
        if not args:
            await message.edit("❌ Guruh nomini kiriting!\nMisol: `.del @mygroup`")
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
    
    async def list(self, message):
        groups = self.config.get("selected_groups", [])
        
        if not groups:
            await message.edit("📋 Hech qanday guruh tanlanmagan\n\n🔄 `.add` deb guruhda yozing")
            return
        
        text = f"📋 **Tanlangan guruhlar ({len(groups)}):**\n\n"
        text += "\n".join(f"• {g}" for g in groups)
        
        await message.edit(text)
    
    # ==================== POST ====================
    
    async def copy(self, message):
        reply = await message.get_reply_message()
        
        if not reply:
            await message.edit("❌ Postga reply qiling!")
            return
        
        try:
            post_data = {
                "text": reply.raw_text or reply.text or "",
                "media": None,
                "media_type": None,
                "date": self._format_time(self._get_current_time()),
                "sender": reply.sender_id,
                "chat": reply.chat_id
            }
            
            # Mediani aniqlash va saqlash (Telethon versiyasiga mos)
            if reply.media:
                try:
                    os.makedirs("modules/media", exist_ok=True)
                    media_path = f"modules/media/post_{int(time.time())}"
                    
                    # Media turini aniqlash
                    if reply.photo:
                        file_path = await reply.download_media(file=media_path + ".jpg")
                        post_data["media"] = file_path
                        post_data["media_type"] = "photo"
                    elif reply.document:
                        # Fayl nomini aniqlash
                        file_ext = ".file"
                        if reply.file and reply.file.name:
                            ext = os.path.splitext(reply.file.name)[1]
                            if ext:
                                file_ext = ext
                        
                        # Audio, video, sticker, gif, voice ni aniqlash
                        if reply.audio:
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
                            file_path = await reply.download_media(file=media_path + file_ext)
                            post_data["media"] = file_path
                            post_data["media_type"] = "document"
                    else:
                        # Noma'lum media
                        file_path = await reply.download_media(file=media_path)
                        if file_path:
                            post_data["media"] = file_path
                            post_data["media_type"] = "file"
                            
                except Exception as e:
                    print(f"Media saqlash xatosi: {e}")
            
            # Eski postni o'chirish
            old_post = self.config.get("saved_post")
            if old_post and old_post.get("media") and os.path.exists(old_post["media"]):
                try:
                    os.remove(old_post["media"])
                except:
                    pass
            
            self.config["saved_post"] = post_data
            self.config["post_active"] = True
            self._save_settings()
            
            await message.edit(
                f"✅ **Post saqlandi!**\n\n"
                f"📝 Matn: {len(post_data['text'])} belgi\n"
                f"🖼 Media: {'✅ Bor' if post_data['media'] else '❌ Yoʻq'}\n"
                f"📅 Sana: {post_data['date']}\n"
                f"🔄 Holat: ✅ Faol\n\n"
                f"📤 `.show` bilan koʻring"
            )
            
        except Exception as e:
            await message.edit(f"❌ Xatolik: {e}")
    
    async def show(self, message):
        post_data = self.config.get("saved_post")
        
        if not post_data:
            await message.edit("📦 Hech qanday post saqlanmagan")
            return
        
        is_active = self.config.get("post_active", False)
        
        text = (
            f"📦 **Saqlangan post**\n\n"
            f"📝 Matn: {post_data.get('text', '')[:200]}\n"
            f"🖼 Media: {'✅ Bor' if post_data.get('media') else '❌ Yoʻq'}\n"
            f"📅 Sana: {post_data.get('date', 'Nomaʼlum')}\n"
            f"🔄 Holat: {'✅ Faol' if is_active else '❌ Oʻchirilgan'}\n\n"
            f"📤 `.poston` - Yoqish | `.postoff` - Oʻchirish"
        )
        
        await message.edit(text)
    
    async def poston(self, message):
        if not self.config.get("saved_post"):
            await message.edit("❌ Post saqlanmagan! `.copy` bilan saqlang")
            return
        
        self.config["post_active"] = True
        self._save_settings()
        await message.edit("✅ Post faollashtirildi!")
    
    async def postoff(self, message):
        if not self.config.get("saved_post"):
            await message.edit("❌ Post saqlanmagan")
            return
        
        self.config["post_active"] = False
        self._save_settings()
        await message.edit("✅ Post oʻchirildi!")
    
    async def delpost(self, message):
        post_data = self.config.get("saved_post")
        
        if not post_data:
            await message.edit("❌ Post saqlanmagan")
            return
        
        if post_data.get("media") and os.path.exists(post_data["media"]):
            try:
                os.remove(post_data["media"])
            except:
                pass
        
        self.config["saved_post"] = None
        self.config["post_active"] = False
        self._save_settings()
        
        await message.edit("✅ Post butunlay oʻchirildi!")
    
    # ==================== START/STOP ====================
    
    async def start(self, message):
        if self._is_running:
            await message.edit("⚠️ Yuborish allaqachon ishlamoqda!")
            return
        
        await self.start_sending()
        await message.edit("✅ Yuborish boshlandi!")
    
    async def stop(self, message):
        if not self._is_running:
            await message.edit("⚠️ Yuborish to'xtatilgan!")
            return
        
        await self.stop_sending()
        await message.edit("⏹ Yuborish to'xtatildi!")
    
    async def start_sending(self):
        if self._is_running:
            return
        
        self._is_running = True
        self._task = asyncio.create_task(self._sender_loop())
        self.config["auto_start"] = True
        self._save_settings()
    
    async def stop_sending(self):
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
        await self.stop_sending()
