import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
import json
import os
from dotenv import load_dotenv
import asyncio
import logging
from collections import deque
import random
import re

# Loglama için özel bir handler
class DiscordLogHandler(logging.Handler):
    def __init__(self, bot_instance, log_channel_id):
        super().__init__()
        self.bot = bot_instance
        self.log_channel_id = log_channel_id
        self.log_buffer = deque()  # Logları biriktirmek için deque kullanıyoruz
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s: %(message)s'))
        self.send_task = None

    def emit(self, record):
        # Sadece belirli seviyedeki ve daha yüksek seviyedeki logları gönder
        if record.levelno >= self.level:
            self.log_buffer.append((record.levelname, self.format(record)))
            # Eğer hemen gönderilmesi gereken kritik bir log varsa
            if record.levelno >= logging.ERROR:
                if self.bot.is_ready() and self.log_channel_id:
                    # Görev zaten çalışıyorsa durdurup yeniden başlat
                    if self.send_task and not self.send_task.done():
                        self.send_task.cancel()
                    self.send_task = self.bot.loop.create_task(self.flush_logs())

    async def flush_logs(self):
        if not self.log_buffer:
            return

        logs_to_send = list(self.log_buffer)
        self.log_buffer.clear() # Buffer'ı temizle

        if self.log_channel_id:
            channel = self.bot.get_channel(self.log_channel_id)
            if channel:
                # Tüm logları tek bir embed içinde tablo şeklinde birleştir
                description_parts = ["```ansi"] # ANSI escape kodları için
                max_level_len = max(len(level) for level, _ in logs_to_send)
                max_msg_len = 0 # Mesaj uzunluğunu bulmak için

                # Geçici olarak mesaj uzunluklarını topla, sonra limit koy
                for _, msg in logs_to_send:
                    # Zaman damgasını ve level'ı çıkararak mesajın kendisine odaklan
                    msg_content = msg[msg.find(' - ') + 3:] # Zaman ve level'dan sonraki kısım
                    max_msg_len = max(max_msg_len, len(msg_content))

                # Başlık
                description_parts.append(f"\u001b[2;37m{'Level'.ljust(max_level_len)} | Mesaj\u001b[0m")
                description_parts.append("\u001b[2;37m" + "-" * (max_level_len + 3 + max_msg_len) + "\u001b[0m")

                for level, msg in logs_to_send:
                    msg_content = msg[msg.find(' - ') + 3:] # Zaman ve level'dan sonraki kısım
                    # Renklendirme
                    color_code = self.get_ansi_color_code(level)
                    description_parts.append(f"{color_code}{level.ljust(max_level_len)}\u001b[0m | {color_code}{msg_content}\u001b[0m")

                final_description = "\n".join(description_parts) + "\n```"

                # Discord Embed limitlerini kontrol et
                if len(final_description) > 4000: # Embed description limiti
                    final_description = final_description[:3997] + "...\n```"

                embed = discord.Embed(
                    title="Bot Aktivite Logları",
                    description=final_description,
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text=f"Gray Zone Warfare Wiki Bot | Log ID: {discord.utils.utcnow().timestamp()}")

                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"Discord log kanalına mesaj gönderilemedi: {e}")
            else:
                print(f"Log kanalı ID'si ayarlı değil veya kanal bulunamadı: {self.log_channel_id}")
        else:
            print("Log kanalı ID'si ayarlı değil.")

    def get_ansi_color_code(self, levelname):
        if levelname == 'CRITICAL':
            return "\u001b[1;31m" # Bright Red
        elif levelname == 'ERROR':
            return "\u001b[0;31m" # Red
        elif levelname == 'WARNING':
            return "\u001b[0;33m" # Yellow
        elif levelname == 'INFO':
            return "\u001b[0;34m" # Blue
        elif levelname == 'DEBUG':
            return "\u001b[0;36m" # Cyan
        else:
            return "\u001b[0m" # Reset

    def start_sending(self):
        if self.send_task is None or self.send_task.done():
            # Her 10 saniyede bir logları gönder
            self.send_task = self.bot.loop.create_periodic_task(self.flush_logs(), 10)

    def stop_sending(self):
        if self.send_task:
            self.send_task.cancel()
            self.send_task = None


# Konsol loglamasını yapılandır
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s: %(message)s')
logger = logging.getLogger('discord_bot')

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN is None:
    logger.error("Hata: DISCORD_TOKEN .env dosyasında bulunamadı. Lütfen kontrol edin.")
    exit()

WIKI_FILE = 'wiki.json'
CONFIG_FILE = 'config.json'
CHAT_FILE = 'chat_data.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Hata: {CONFIG_FILE} dosyasında JSON ayrıştırma hatası: {e}. Varsayılan config oluşturuluyor.")
            default_config = {"LOG_CHANNEL_ID": None, "SETUP_COMPLETE": False}
            save_config(default_config)
            return default_config
    default_config = {"LOG_CHANNEL_ID": None, "SETUP_COMPLETE": False}
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2)
    return default_config

def save_config(config_data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2)

config = load_config()
log_channel_id = config["LOG_CHANNEL_ID"]

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

discord_log_handler = DiscordLogHandler(bot, log_channel_id)
discord_log_handler.setLevel(logging.INFO) # Hangi seviyedeki logları Discord'a gönderecek
logger.addHandler(discord_log_handler)

active_wiki_channels = {} 

def load_wiki_data():
    if not os.path.exists(WIKI_FILE):
        logger.error(f"Hata: {WIKI_FILE} dosyası bulunamadı.")
        return {"categories": []}
    try:
        with open(WIKI_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Hata: {WIKI_FILE} dosyasında JSON ayrıştırma hatası: {e}")
        return {"categories": []}
    except Exception as e:
        logger.error(f"Hata: Wiki verilerini yüklerken bir sorun oluştu: {e}")
        return {"categories": []}

def load_chat_data():
    if not os.path.exists(CHAT_FILE):
        logger.error(f"Hata: {CHAT_FILE} dosyası bulunamadı.")
        return {"greetings": [], "responses": {}, "topics": {}, "random_facts": []}
    try:
        with open(CHAT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Hata: {CHAT_FILE} dosyasında JSON ayrıştırma hatası: {e}")
        return {"greetings": [], "responses": {}, "topics": {}, "random_facts": []}
    except Exception as e:
        logger.error(f"Hata: Sohbet verilerini yüklerken bir sorun oluştu: {e}")
        return {"greetings": [], "responses": {}, "topics": {}, "random_facts": []}

@bot.event
async def on_ready():
    logger.info(f'{bot.user.name} olarak giriş yapıldı!')
    try:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Gray Zone Warfare Wiki & Sohbet"))
        logger.info("Bot durumu başarıyla ayarlandı.")
    except Exception as e:
        logger.error(f"Bot durumu ayarlanırken hata oluştu: {e}")
    logger.info('--------------------')
    
    discord_log_handler.log_channel_id = config["LOG_CHANNEL_ID"]
    discord_log_handler.start_sending()
    if discord_log_handler.log_channel_id:
        logger.info(f"Discord loglama aktif. Kanal ID: {discord_log_handler.log_channel_id}")
    else:
        logger.warning("Log kanalı ID'si ayarlanmadığı için Discord loglama pasif.")

@bot.event
async def on_guild_join(guild):
    logger.info(f"Yeni sunucuya katıldı: {guild.name} (ID: {guild.id})")
    
    # Kurulum tamamlanmadıysa ve log kanalı ayarlanmadıysa
    if not config["SETUP_COMPLETE"] or config["LOG_CHANNEL_ID"] is None:
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        admin_roles = [role for role in guild.roles if role.permissions.administrator]
        for role in admin_roles:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            setup_channel = await guild.create_text_channel(
                f'{guild.name.lower().replace(" ", "-")}-bot-kurulumu',
                overwrites=overwrites,
                topic="Bot kurulumu için geçici kanal. Sadece yöneticiler görebilir."
            )
            logger.info(f"Bot kurulum kanalı oluşturuldu: {setup_channel.name} (ID: {setup_channel.id})")

            class SetupConfirmView(View):
                def __init__(self, setup_channel_id, admin_user_id):
                    super().__init__(timeout=180)
                    self.setup_channel_id = setup_channel_id
                    self.admin_user_id = admin_user_id
                    self.add_item(Button(label="Evet, Oluştur", style=discord.ButtonStyle.green, custom_id="setup_yes"))
                    self.add_item(Button(label="Hayır, Daha Sonra", style=discord.ButtonStyle.red, custom_id="setup_no"))

                async def interaction_check(self, interaction: discord.Interaction) -> bool:
                    return interaction.user.id == self.admin_user_id and interaction.channel.id == self.setup_channel_id

                async def on_timeout(self):
                    channel = bot.get_channel(self.setup_channel_id)
                    if channel:
                        try:
                            await channel.send("Kurulum süresi doldu. Log kanalını daha sonra `!setlogchannel` komutuyla ayarlayabilirsiniz.", ephemeral=False)
                            await asyncio.sleep(5)
                            await channel.delete()
                            logger.info(f"Kurulum kanalı '{channel.name}' süresi dolduğu için silindi.")
                        except Exception as e:
                            logger.error(f"Kurulum kanalı silinirken hata oluştu (timeout): {e}")

                @discord.ui.button(label="Evet, Oluştur", style=discord.ButtonStyle.green, custom_id="setup_yes")
                async def confirm_setup(self, interaction: discord.Interaction, button: Button):
                    await interaction.response.send_message("Log kanalının adını girin (ör: `bot-log`) veya otomatik bir isim için `otomatik` yazın:", ephemeral=True)
                    self.stop() 

                    def check(m):
                        return m.author == interaction.user and m.channel == interaction.channel

                    try:
                        channel_name_msg = await bot.wait_for('message', check=check, timeout=60)
                        new_log_channel_name = channel_name_msg.content.lower().strip()
                        await channel_name_msg.delete()

                    except asyncio.TimeoutError:
                        new_log_channel_name = "otomatik"
                        await interaction.followup.send("Yanıt alınamadı, otomatik bir isim kullanılıyor.", ephemeral=True)

                    if new_log_channel_name == "otomatik":
                        final_channel_name = f"{guild.name.lower().replace(' ', '-')}-gzw-log"
                    else:
                        final_channel_name = new_log_channel_name.replace(' ', '-')

                    try:
                        log_channel = await guild.create_text_channel(
                            final_channel_name,
                            category=setup_channel.category,
                            overwrites={
                                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
                            },
                            topic="Gray Zone Warfare botunun aktivite logları bu kanalda tutulur. Sadece yöneticiler görebilir."
                        )
                        global config
                        global discord_log_handler
                        config["LOG_CHANNEL_ID"] = log_channel.id
                        config["SETUP_COMPLETE"] = True
                        save_config(config)
                        discord_log_handler.log_channel_id = log_channel.id
                        discord_log_handler.start_sending()

                        await interaction.followup.send(f"Log kanalı {log_channel.mention} başarıyla oluşturuldu ve ayarlandı.", ephemeral=True)
                        logger.info(f"Log kanalı '{log_channel.name}' (ID: {log_channel.id}) başarıyla oluşturuldu ve ayarlandı.")
                        
                        await setup_channel.delete()
                        logger.info(f"Kurulum kanalı '{setup_channel.name}' başarıyla silindi.")

                    except discord.Forbidden:
                        await interaction.followup.send("Log kanalını oluşturmak için yetkim yok. Lütfen botun izinlerini kontrol edin.", ephemeral=True)
                        logger.error(f"Log kanalı oluşturmak için yetki hatası: {guild.name}")
                        await setup_channel.delete()
                        logger.info(f"Kurulum kanalı '{setup_channel.name}' hata sonrası silindi.")
                    except Exception as e:
                        await interaction.followup.send(f"Log kanalı oluşturulurken bir hata oluştu: {e}", ephemeral=True)
                        logger.error(f"Log kanalı oluşturma hatası: {e}")
                        await setup_channel.delete()
                        logger.info(f"Kurulum kanalı '{setup_channel.name}' hata sonrası silindi.")


                @discord.ui.button(label="Hayır, Daha Sonra", style=discord.ButtonStyle.red, custom_id="setup_no")
                async def cancel_setup(self, interaction: discord.Interaction, button: Button):
                    await interaction.response.send_message("Log kanalı oluşturma iptal edildi. Daha sonra `!setlogchannel` komutuyla ayarlayabilirsiniz.", ephemeral=True)
                    logger.info(f"Log kanalı oluşturma '{interaction.user.name}' tarafından iptal edildi.")
                    await interaction.channel.delete()
                    logger.info(f"Kurulum kanalı '{interaction.channel.name}' iptal edildiği için silindi.")
                    self.stop()

            admin_members = [member for member in guild.members if member.guild_permissions.administrator and not member.bot]
            for admin_member in admin_members:
                try:
                    view_to_send = SetupConfirmView(setup_channel.id, admin_member.id)
                    await setup_channel.send(f"{admin_member.mention}, botun log kanalını şimdi ayarlamak ister misiniz?", view=view_to_send)
                    logger.info(f"Admin '{admin_member.name}' ({admin_member.id}) için kurulum teklifi gönderildi.")
                    break # Sadece bir adminin yanıt vermesi yeterli
                except Exception as e:
                    logger.error(f"Admin '{admin_member.name}'e kurulum mesajı gönderilemedi: {e}")

        except discord.Forbidden:
            logger.error(f"Bot kurulum kanalı oluşturmak için yetkim yok: {guild.name}")
        except Exception as e:
            logger.error(f"Bot kurulum kanalı oluşturulurken hata oluştu: {e}")


async def create_temp_wiki_channel(ctx_or_interaction, initial_message="Gray Zone Warfare Wiki'ye hoş geldiniz! Bir kategori seçmek için aşağıdaki menüyü kullanın:", view_instance=None):
    user = ctx_or_interaction.author if isinstance(ctx_or_interaction, commands.Context) else ctx_or_interaction.user
    guild = ctx_or_interaction.guild

    channel_name = f"wiki-{user.name.lower().replace(' ', '-')}-{user.discriminator}"

    for ch_id, u_id in list(active_wiki_channels.items()):
        if u_id == user.id:
            existing_channel = guild.get_channel(ch_id)
            if existing_channel:
                await ctx_or_interaction.send(f"{user.mention}, zaten açık bir wiki kanalınız var: {existing_channel.mention}", ephemeral=True)
                logger.info(f"Kullanıcı {user.name} için zaten açık bir wiki kanalı bulundu: {existing_channel.name}")
                return None
            else:
                del active_wiki_channels[ch_id]
                logger.info(f"Aktif kanallar listesinden silinen kanal: {ch_id} (Discord'da bulunamadı).")

    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        if isinstance(ctx_or_interaction, commands.Context) and ctx_or_interaction.channel.category:
            category_to_use = ctx_or_interaction.channel.category
        else:
            category_to_use = discord.utils.find(lambda c: isinstance(c, discord.CategoryChannel), guild.channels)
            if not category_to_use:
                raise Exception("Sunucuda uygun bir kategori bulunamadı.")

        temp_channel = await guild.create_text_channel(
            channel_name,
            category=category_to_use,
            overwrites=overwrites,
            topic=f"{user.name} için Gray Zone Warfare Wiki bilgileri. Bu kanal 3 dakika sonra otomatik olarak silinecektir veya 'Kapat' butonuyla silinebilir."
        )
        logger.info(f"'{temp_channel.name}' adlı geçici kanal oluşturuldu (ID: {temp_channel.id}).")
        
        active_wiki_channels[temp_channel.id] = user.id

        # Kanal linki mesajını hemen sil (eğer ephemeral ise otomatik silinir, değilse manuel)
        sent_link_message = await ctx_or_interaction.send(f"{user.mention}, wiki bilgileri için özel kanalın oluşturuldu: {temp_channel.mention}", ephemeral=True)
        
        if not sent_link_message.is_done(): # Mesajın gönderildiğinden emin ol
             await asyncio.sleep(0.5) # Kısa bekleme, mesajın gönderildiğinden emin olmak için
        try:
            # Ephemeral mesajlar delete() metoduna sahip olmayabilir veya Discord otomatik siler
            # is_done() kontrolü doğru çalışmazsa kaldırılabilir
            if not getattr(sent_link_message, 'ephemeral', False): # Ephemeral değilse silmeye çalış
                 await sent_link_message.delete()
            logger.info("Kanal linki mesajı başarıyla silindi (veya ephemeral olduğu için otomatik silindi).")
        except discord.NotFound:
            logger.warning("Kanal linki mesajı zaten silinmiş.")
        except discord.Forbidden:
            logger.error("Kanal linki mesajını silmek için yetkim yok.")
        except Exception as e:
            logger.error(f"Kanal linki mesajı silinirken hata oluştu: {e}")


        if view_instance:
            message_with_view = await temp_channel.send(initial_message, view=view_instance)
            if hasattr(view_instance, 'set_message_to_delete_id'):
                view_instance.set_message_to_delete_id(message_with_view.id)
        else:
            await temp_channel.send(initial_message)

        return temp_channel

    except discord.Forbidden:
        error_msg = "Geçici kanal oluşturmak için yetkim yok. Lütfen botun kanal oluşturma ve yönetme izinlerine sahip olduğundan emin olun."
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(error_msg, ephemeral=True)
        else:
            await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
        logger.error(f"Geçici kanal oluşturmak için yetki hatası: {guild.name}")
        return None
    except Exception as e:
        error_msg = f"Geçici kanal oluşturulurken bir hata oluştu: {e}"
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(error_msg, ephemeral=True)
        else:
            await ctx_or_interaction.followup.send(error_msg, ephemeral=True)
        logger.error(f"Kanal oluşturma hatası: {e}")
        return None

class CloseChannelButton(Button):
    def __init__(self):
        super().__init__(label="Kapat", style=discord.ButtonStyle.red, emoji="🗑️")

    async def callback(self, interaction: discord.Interaction):
        logger.info(f"Kullanıcı {interaction.user.name} tarafından '{interaction.channel.name}' kanalını kapatma butonu kullanıldı.")
        if interaction.channel.id in active_wiki_channels and active_wiki_channels[interaction.channel.id] == interaction.user.id:
            try:
                await interaction.response.send_message("Kanal kapatılıyor...", ephemeral=True)
                # Logları hemen gönder (flush) çünkü işlem bitiyor
                await discord_log_handler.flush_logs() 
                await asyncio.sleep(1) 
                await interaction.channel.delete()
                del active_wiki_channels[interaction.channel.id]
                logger.info(f"Kanal '{interaction.channel.name}' başarıyla silindi (Kapat butonuyla).")
            except discord.Forbidden:
                await interaction.response.send_message("Kanalı silmek için yetkim yok.", ephemeral=True)
                logger.error(f"Kanalı silmek için yetki hatası: {interaction.channel.name}")
            except Exception as e:
                await interaction.response.send_message(f"Kanalı kapatırken bir hata oluştu: {e}", ephemeral=True)
                logger.error(f"Kanal kapatma hatası ({interaction.channel.name}): {e}")
        else:
            await interaction.response.send_message("Bu kanalı kapatma yetkiniz yok veya kanal zaten sona ermiş.", ephemeral=True)
            logger.warning(f"Yetkisiz kanal kapatma girişimi: Kullanıcı {interaction.user.name}, Kanal: {interaction.channel.name}")

class CategorySelect(Select):
    def __init__(self, categories):
        options = []
        for index, category in enumerate(categories):
            options.append(discord.SelectOption(label=category['name'], description=category['description'], value=str(index)))
        
        super().__init__(placeholder="Bir kategori seçin...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        logger.info(f"Kullanıcı {interaction.user.name} kategori seçti: {self.values[0]}. Kanal: {interaction.channel.name}")
        try:
            if interaction.message:
                await interaction.message.delete()
        except discord.NotFound:
            logger.warning("Kategori seçim mesajı zaten silinmiş.")
        except discord.Forbidden:
            logger.error("Kategori seçim mesajını silmek için yetkim yok.")
        except Exception as e:
            logger.error(f"Kategori seçim mesajı silinirken hata oluştu: {e}")

        selected_category_index = int(self.values[0])
        wiki_data = load_wiki_data()
        category = wiki_data['categories'][selected_category_index]

        await interaction.response.defer()
        
        item_select_view_instance = ItemSelectView(category)
        sent_message = await interaction.channel.send(
            f"**{category['name']}** kategorisi seçildi. Lütfen bir öğe seçin:",
            view=item_select_view_instance
        )
        item_select_view_instance.set_message_to_delete_id(sent_message.id)
        logger.info(f"Öğe seçim menüsü '{interaction.channel.name}' kanalına gönderildi.")

class ItemSelect(Select):
    def __init__(self, category, message_to_delete_id=None):
        options = []
        for index, item in enumerate(category['items']):
            options.append(discord.SelectOption(label=item['title'], value=str(index)))
        
        super().__init__(placeholder="Bir öğe seçin...", min_values=1, max_values=1, options=options)
        self.category = category
        self.message_to_delete_id = message_to_delete_id

    async def callback(self, interaction: discord.Interaction):
        logger.info(f"Kullanıcı {interaction.user.name} öğe seçti: {self.values[0]}. Kanal: {interaction.channel.name}")
        try:
            if interaction.message:
                await interaction.message.delete()
        except discord.NotFound:
            logger.warning("Öğe seçim mesajı zaten silinmiş.")
        except discord.Forbidden:
            logger.error("Öğe seçim mesajını silmek için yetkim yok.")
        except Exception as e:
            logger.error(f"Öğe seçim mesajı silinirken hata oluştu: {e}")

        selected_item_index = int(self.values[0])
        item = self.category['items'][selected_item_index]

        embed_description = f"**Kategori:** {self.category['name']}"
        if 'description' in item and item['description']:
            embed_description += f"\n*{item['description']}*"
        
        embed = discord.Embed(
            title=f"Wiki Bilgisi: {item['title']}",
            description=embed_description,
            color=discord.Color.blue()
        )
        
        for key, value in item['data']:
            field_value = str(value) if value is not None else "Bilgi Yok"
            embed.add_field(name=key, value=field_value, inline=True)
        
        try:
            await interaction.response.send_message(
                embed=embed,
                view=CloseChannelView(),
                ephemeral=False
            )
            logger.info(f"Wiki bilgisi embed olarak gönderildi. Öğe: {item['title']}. Kanal: {interaction.channel.name}")
        except discord.Forbidden:
            logger.error(f"Embed mesajını göndermek için yetkim yok. Kanal: {interaction.channel.name}")
            await interaction.followup.send("Bilgiyi gönderemedim. Lütfen botun izinlerini kontrol edin.", ephemeral=True)
        except Exception as e:
            logger.error(f"Embed mesajı gönderilirken hata oluştu: {e}")
            await interaction.followup.send("Bir hata oluştu, lütfen daha sonra tekrar deneyin.", ephemeral=True)
        
        current_channel = interaction.channel
        channel_id = current_channel.id
        await asyncio.sleep(180) 
        
        if channel_id in active_wiki_channels and active_wiki_channels[channel_id] == interaction.user.id:
            try:
                logger.info(f"Otomatik kanal silme başlatıldı: {current_channel.name} (ID: {channel_id})")
                # Otomatik silmeden önce logları gönder
                await discord_log_handler.flush_logs()
                await current_channel.delete()
                del active_wiki_channels[channel_id]
                logger.info(f"Kanal başarıyla otomatik olarak silindi: {current_channel.name}")
            except discord.NotFound:
                logger.warning(f"Kanal zaten silinmiş veya bulunamadı (otomatik silme): {current_channel.name}")
            except discord.Forbidden:
                logger.error(f"Kanalı otomatik silmek için yetkim yok: {current_channel.name}. Lütfen botun izinlerini kontrol edin.")
            except Exception as e:
                logger.error(f"Kanal otomatik silinirken beklenmeyen bir hata oluştu ({current_channel.name}): {e}")
        else:
            logger.info(f"Kanal {current_channel.name} otomatik silinmedi çünkü zaten kapatıldı veya yetki değişti.")

class CategorySelectView(View):
    def __init__(self, categories, timeout=180):
        super().__init__(timeout=timeout)
        self.add_item(CategorySelect(categories))

class ItemSelectView(View):
    def __init__(self, category, timeout=180):
        super().__init__(timeout=timeout)
        self.select_item = ItemSelect(category)
        self.add_item(self.select_item)

    def set_message_to_delete_id(self, message_id):
        self.select_item.message_to_delete_id = message_id

class CloseChannelView(View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)
        self.add_item(CloseChannelButton())

def get_chat_response(message_content):
    """Basit pattern matching ile sohbet yanıtları üretir"""
    chat_data = load_chat_data()
    message_lower = message_content.lower().strip()
    
    # Normalize Turkish characters for better matching
    message_normalized = message_lower.replace('ç', 'c').replace('ğ', 'g').replace('ı', 'i').replace('ö', 'o').replace('ş', 's').replace('ü', 'u')
    
    # Greeting patterns
    greeting_patterns = ['merhaba', 'selam', 'hey', 'hi', 'hello', 'gunaydin', 'günaydın']
    if any(pattern in message_normalized for pattern in greeting_patterns):
        return random.choice(chat_data.get('greetings', ['Merhaba!']))
    
    # Common question patterns
    how_are_you_patterns = ['nasilsin', 'nasılsın', 'ne_haber', 'naber']
    if any(pattern in message_normalized for pattern in how_are_you_patterns):
        return random.choice(chat_data.get('responses', {}).get('nasılsın', ['İyiyim, teşekkürler!']))
    
    what_doing_patterns = ['ne_yapiyorsun', 'ne yapıyorsun', 'neler_yapiyorsun']
    if any(pattern in message_normalized for pattern in what_doing_patterns):
        return random.choice(chat_data.get('responses', {}).get('ne_yapıyorsun', ['Sohbet etmeyi bekliyorum!']))
    
    # Thank you patterns
    thank_patterns = ['tesekkur', 'teşekkür', 'sagol', 'sağol', 'thanks']
    if any(pattern in message_normalized for pattern in thank_patterns):
        return random.choice(chat_data.get('responses', {}).get('teşekkür', ['Rica ederim!']))
    
    # Good morning/night patterns
    if 'gunaydin' in message_normalized or 'günaydın' in message_normalized:
        return random.choice(chat_data.get('responses', {}).get('günaydın', ['Günaydın!']))
    
    good_night_patterns = ['iyi_geceler', 'iyi geceler', 'bye', 'gule_gule', 'güle güle']
    if any(pattern in message_normalized for pattern in good_night_patterns):
        return random.choice(chat_data.get('responses', {}).get('iyi_geceler', ['İyi geceler!']))
    
    # Help patterns
    help_patterns = ['yardim', 'yardım', 'help']
    if any(pattern in message_normalized for pattern in help_patterns):
        return random.choice(chat_data.get('responses', {}).get('yardım', ['Nasıl yardım edebilirim?']))
    
    # Topic-based responses
    topics = chat_data.get('topics', {})
    for topic, responses in topics.items():
        if topic in message_normalized:
            return random.choice(responses)
    
    # Game patterns
    game_patterns = ['oyun', 'game', 'gray_zone', 'gzw']
    if any(pattern in message_normalized for pattern in game_patterns):
        return random.choice(chat_data.get('responses', {}).get('oyun', ['Gray Zone Warfare hakkında konuşalım!']))
    
    # Bored patterns
    bored_patterns = ['sikildim', 'sıkıldım', 'bored']
    if any(pattern in message_normalized for pattern in bored_patterns):
        return random.choice(chat_data.get('responses', {}).get('sıkıldım', ['Bir şeyler öğrenelim!']))
    
    # Random fact request
    fact_patterns = ['bilgi', 'fact', 'gercek', 'gerçek', 'anlat']
    if any(pattern in message_normalized for pattern in fact_patterns):
        facts = chat_data.get('random_facts', [])
        if facts:
            return random.choice(facts)
    
    # Default response
    return random.choice(chat_data.get('responses', {}).get('default', ['İlginç! Daha fazla anlat.']))

@bot.command(name='yap', aliases=['sohbet', 'chat'])
async def chat_command(ctx, *, message: str = None):
    """Sohbet komutu - botla casual konuşma yapmak için"""
    logger.info(f"'{ctx.author.name}' tarafından '!yap' komutu kullanıldı. Mesaj: {message}")
    
    if message is None:
        # If no message provided, start a conversation
        chat_data = load_chat_data()
        greeting = random.choice(chat_data.get('greetings', ['Merhaba! Seninle sohbet etmeye hazırım.']))
        response = f"{greeting}\n\nBana bir şeyler yazabilirsin, sohbet edelim! 💬\nÖrnekler: `!yap merhaba`, `!yap nasılsın`, `!yap Gray Zone Warfare oynuyor musun?`"
    else:
        response = get_chat_response(message)
    
    embed = discord.Embed(
        title="💬 Sohbet Zamanı",
        description=response,
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    
    if message:
        embed.add_field(name="Sen:", value=message, inline=False)
        embed.add_field(name="Ben:", value=response, inline=False)
    
    embed.set_footer(text="Gray Zone Warfare Wiki Bot | Sohbet Modu")
    
    try:
        await ctx.send(embed=embed)
        logger.info(f"Sohbet yanıtı gönderildi: {ctx.author.name}")
    except Exception as e:
        logger.error(f"Sohbet mesajı gönderilirken hata oluştu: {e}")
        await ctx.send("Sohbet ederken bir hata oluştu. Lütfen daha sonra tekrar deneyin.")

@bot.command(name='random', aliases=['rastgele'])
async def random_fact(ctx):
    """Rastgele bir bilgi paylaşır"""
    logger.info(f"'{ctx.author.name}' tarafından '!random' komutu kullanıldı.")
    
    chat_data = load_chat_data()
    facts = chat_data.get('random_facts', [])
    
    if not facts:
        await ctx.send("Üzgünüm, şu anda paylaşabileceğim rastgele bilgi yok.")
        return
    
    fact = random.choice(facts)
    
    embed = discord.Embed(
        title="🎲 Rastgele Bilgi",
        description=fact,
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text="Gray Zone Warfare Wiki Bot | Bilgi Zamanı")
    
    try:
        await ctx.send(embed=embed)
        logger.info(f"Rastgele bilgi gönderildi: {ctx.author.name}")
    except Exception as e:
        logger.error(f"Rastgele bilgi gönderilirken hata oluştu: {e}")
        await ctx.send("Bilgi paylaşırken bir hata oluştu.")

@bot.command(name='komutlar', aliases=['commands', 'help'])
async def help_command(ctx):
    """Bot komutlarını listeler"""
    logger.info(f"'{ctx.author.name}' tarafından '!komutlar' komutu kullanıldı.")
    
    embed = discord.Embed(
        title="🤖 Bot Komutları",
        description="Gray Zone Warfare Wiki Bot'un kullanabileceğiniz komutları:",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    
    # Wiki commands
    embed.add_field(
        name="📚 Wiki Komutları",
        value="`!wiki` - Ana wiki menüsünü açar\n`!wiki ara <kelime>` - Wiki'de arama yapar",
        inline=False
    )
    
    # Chat commands  
    embed.add_field(
        name="💬 Sohbet Komutları",
        value="`!yap <mesaj>` - Botla sohbet edersiniz\n`!random` - Rastgele bir bilgi paylaşır\n`!komutlar` - Bu yardım mesajını gösterir",
        inline=False
    )
    
    # Admin commands
    embed.add_field(
        name="⚙️ Yönetici Komutları",
        value="`!setlogchannel` - Log kanalını ayarlar (Sadece yöneticiler)",
        inline=False
    )
    
    embed.add_field(
        name="💡 İpuçları",
        value="• Wiki için geçici kanallar oluşturulur\n• Sohbet komutları doğrudan bu kanalda çalışır\n• Bot Türkçe konuşur!",
        inline=False
    )
    
    embed.set_footer(text="Gray Zone Warfare Wiki Bot | Yardım")
    
    try:
        await ctx.send(embed=embed)
        logger.info(f"Yardım mesajı gönderildi: {ctx.author.name}")
    except Exception as e:
        logger.error(f"Yardım mesajı gönderilirken hata oluştu: {e}")
        await ctx.send("Yardım mesajı gönderilirken bir hata oluştu.")

@bot.group(name='wiki', invoke_without_command=True)
async def wiki_group(ctx):
    if ctx.invoked_subcommand is None:
        logger.info(f"'{ctx.author.name}' tarafından '!wiki' ana komutu kullanıldı.")
        wiki_data = load_wiki_data()
        if not wiki_data or not wiki_data.get('categories'):
            await ctx.send("Wiki verileri yüklenemedi veya boş. Lütfen `wiki.json` dosyasını kontrol edin.", ephemeral=True)
            logger.warning("Wiki verileri boş veya yüklenemedi.")
            return

        categories = wiki_data['categories']
        if not categories:
            await ctx.send("Wiki'de henüz hiç kategori bulunmuyor.", ephemeral=True)
            logger.warning("Wiki'de hiç kategori bulunmuyor.")
            return
        
        category_select_view_instance = CategorySelectView(categories)
        temp_channel = await create_temp_wiki_channel(
            ctx,
            initial_message="Gray Zone Warfare Wiki'ye hoş geldiniz! Bir kategori seçmek için aşağıdaki menüyü kullanın:",
            view_instance=category_select_view_instance
        )
        if temp_channel:
            logger.info(f"Kategori seçim menüsü '{temp_channel.name}' kanalına gönderildi.")
        else:
            logger.error("Geçici kanal oluşturulamadı.")

@wiki_group.command(name='ara', aliases=['search'])
async def search_wiki(ctx, *, query: str):
    logger.info(f"'{ctx.author.name}' tarafından '!wiki ara {query}' komutu kullanıldı.")
    wiki_data = load_wiki_data()
    if not wiki_data or not wiki_data.get('categories'):
        await ctx.send("Wiki verileri yüklenemedi veya boş. Lütfen `wiki.json` dosyasını kontrol edin.", ephemeral=True)
        logger.warning("Arama için wiki verileri boş veya yüklenemedi.")
        return

    found_items = []
    query_lower = query.lower()

    for category in wiki_data['categories']:
        for item in category['items']:
            if query_lower in item['title'].lower():
                found_items.append({'category': category['name'], 'item': item})
                continue 

            if 'description' in item and item['description'] and query_lower in item['description'].lower():
                found_items.append({'category': category['name'], 'item': item})
                continue
                
            for key, value in item['data']:
                if query_lower in key.lower() or query_lower in str(value).lower():
                    found_items.append({'category': category['name'], 'item': item})
                    break

    if not found_items:
        await ctx.send(f"'{query}' için wiki'de sonuç bulunamadı.", ephemeral=True)
        logger.info(f"'{query}' için sonuç bulunamadı.")
        return

    embed = discord.Embed(
        title=f"'{query}' için Arama Sonuçları",
        description=f"Toplam **{len(found_items)}** sonuç bulundu. Lütfen bir öğe seçin:",
        color=discord.Color.green()
    )

    options_for_select = []
    for index, result in enumerate(found_items[:25]): 
        item = result['item']
        category_name = result['category']
        
        item_description_snippet = item.get('description', 'Açıklama mevcut değil.')
        if len(item_description_snippet) > 50:
            item_description_snippet = item_description_snippet[:47] + "..."

        embed.add_field(
            name=f"{index + 1}. {item['title']} (Kategori: {category_name})",
            value=f"```fix\n{item_description_snippet}\n```",
            inline=False
        )
        options_for_select.append(
            discord.SelectOption(
                label=f"{item['title']} ({category_name})", 
                value=f"{category_name}|{item['title']}",
                description=item_description_snippet
            )
        )
    
    if len(found_items) > 25:
        embed.set_footer(text=f"İlk 25 sonuç gösteriliyor. Toplam {len(found_items)} sonuç bulundu.")

    class SearchResultSelect(Select):
        def __init__(self, search_results_options):
            super().__init__(placeholder="Detaylarını görmek için bir öğe seçin...", min_values=1, max_values=1, options=search_results_options)
        
        async def callback(self, interaction: discord.Interaction):
            logger.info(f"Kullanıcı {interaction.user.name} arama sonucundan öğe seçti: {self.values[0]}. Kanal: {interaction.channel.name}")
            selected_value = self.values[0]
            category_name, item_title = selected_value.split('|', 1)

            wiki_data = load_wiki_data()
            selected_category = next((cat for cat in wiki_data['categories'] if cat['name'] == category_name), None)
            selected_item = None
            if selected_category:
                selected_item = next((it for it in selected_category['items'] if it['title'] == item_title), None)

            if not selected_item:
                await interaction.response.send_message("Seçilen öğe bulunamadı. Lütfen daha sonra tekrar deneyin.", ephemeral=True)
                logger.error(f"Arama sonucundan seçilen öğe bulunamadı: {selected_value}")
                return

            if interaction.message:
                try:
                    await interaction.message.delete()
                except (discord.NotFound, discord.Forbidden):
                    logger.warning("Arama sonucu mesajı zaten silinmiş veya silinemedi.")

            embed_description = f"**Kategori:** {selected_category['name']}"
            if 'description' in selected_item and selected_item['description']:
                embed_description += f"\n*{selected_item['description']}*"
            
            embed = discord.Embed(
                title=f"Wiki Bilgisi: {selected_item['title']}",
                description=embed_description,
                color=discord.Color.blue()
            )
            
            for key, value in selected_item['data']:
                field_value = str(value) if value is not None else "Bilgi Yok"
                embed.add_field(name=key, value=field_value, inline=True)
            
            try:
                await interaction.response.send_message(
                    embed=embed,
                    view=CloseChannelView(),
                    ephemeral=False
                )
                logger.info(f"Arama sonucundan seçilen wiki bilgisi embed olarak gönderildi. Öğe: {selected_item['title']}. Kanal: {interaction.channel.name}")
            except discord.Forbidden:
                logger.error(f"Embed mesajını göndermek için yetkim yok. Kanal: {interaction.channel.name}")
                await interaction.followup.send("Bilgiyi gönderemedim. Lütfen botun izinlerini kontrol edin.", ephemeral=True)
            except Exception as e:
                logger.error(f"Embed mesajı gönderilirken hata oluştu: {e}")
                await interaction.followup.send("Bir hata oluştu, lütfen daha sonra tekrar deneyin.", ephemeral=True)

            current_channel = interaction.channel
            channel_id = current_channel.id
            await asyncio.sleep(180) 
            
            if channel_id in active_wiki_channels and active_wiki_channels[channel_id] == interaction.user.id:
                try:
                    logger.info(f"Otomatik kanal silme başlatıldı (arama sonrası): {current_channel.name} (ID: {channel_id})")
                    await discord_log_handler.flush_logs() # Otomatik silmeden önce logları gönder
                    await current_channel.delete()
                    del active_wiki_channels[channel_id]
                    logger.info(f"Kanal başarıyla otomatik olarak silindi (arama sonrası): {current_channel.name}")
                except discord.NotFound:
                    logger.warning(f"Kanal zaten silinmiş veya bulunamadı (otomatik silme): {current_channel.name}")
                except discord.Forbidden:
                    logger.error(f"Kanalı otomatik silmek için yetkim yok: {current_channel.name}. Lütfen botun izinlerini kontrol edin.")
                except Exception as e:
                    logger.error(f"Kanal otomatik silinirken beklenmeyen bir hata oluştu ({current_channel.name}): {e}")
            else:
                logger.info(f"Kanal {current_channel.name} otomatik silinmedi çünkü zaten kapatıldı veya yetki değişti.")

    class SearchResultView(View):
        def __init__(self, search_results_options, timeout=180):
            super().__init__(timeout=timeout)
            if search_results_options:
                self.add_item(SearchResultSelect(search_results_options))

    search_result_view_instance = SearchResultView(options_for_select)

    temp_channel = await create_temp_wiki_channel(
        ctx,
        initial_message="Arama sonuçlarınız aşağıdadır. Detaylarını görmek için bir öğe seçin:",
        view_instance=search_result_view_instance
    )
    if temp_channel:
        await temp_channel.send(embed=embed)
        logger.info(f"Arama sonuçları '{temp_channel.name}' kanalına gönderildi.")
    else:
        logger.error("Arama sonuçları için geçici kanal oluşturulamadı.")

@bot.command(name='setlogchannel')
@commands.has_permissions(administrator=True)
async def set_log_channel(ctx):
    global config
    global discord_log_handler

    old_log_channel_id = config["LOG_CHANNEL_ID"]
    new_log_channel_id = ctx.channel.id

    config["LOG_CHANNEL_ID"] = new_log_channel_id
    config["SETUP_COMPLETE"] = True
    save_config(config)

    # Log handler'ın hedef kanalını güncelle
    discord_log_handler.log_channel_id = new_log_channel_id
    # Logları hemen yeni kanala göndermek için zorla
    await discord_log_handler.flush_logs() 
    discord_log_handler.start_sending() # Periyodik görevi yeniden başlat/başlat

    await ctx.send(f"Bu kanal ({ctx.channel.mention}) başarıyla log kanalı olarak ayarlandı. Bot logları artık buraya gönderilecek.", ephemeral=True)
    logger.info(f"Log kanalı '{ctx.channel.name}' (ID: {ctx.channel.id}) olarak ayarlandı. Eski log kanalı ID: {old_log_channel_id}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"Bu komutu kullanmak için gerekli izinlere sahip değilsiniz: {error.missing_permissions}", ephemeral=True)
        logger.warning(f"Kullanıcı {ctx.author.name} '{ctx.command}' komutunu kullanmak için yetersiz izne sahip.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Komut için eksik argüman: {error.param.name}. Kullanım: `!{ctx.command.name} {ctx.command.signature}`", ephemeral=True)
        logger.warning(f"Kullanıcı {ctx.author.name} '{ctx.command}' komutunu eksik argümanla kullandı.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        logger.error(f"Komut çalıştırılırken bir hata oluştu: {ctx.command} - {error}", exc_info=True)
        await ctx.send("Komut çalıştırılırken beklenmeyen bir hata oluştu. Lütfen logları kontrol edin.", ephemeral=True)


if __name__ == '__main__':
    # discord.py'nin kendi logger'ını da kontrol edebiliriz
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING) # HTTP isteklerini daha az logla

    # Periyodik görevleri çalıştırmak için botu başlat
    # bot.run yerine bot.start kullanmak daha esnek olabilir
    # Ancak bot.run da async döngüyü otomatik başlatır
    bot.run(TOKEN)