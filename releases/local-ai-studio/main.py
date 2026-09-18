from __future__ import annotations
import hashlib, json, os, queue, shutil, socket, subprocess, sys, threading, time, tkinter as tk, urllib.request, webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox

VERSION="0.5.0"
APPDATA=Path(os.getenv("APPDATA") or Path.home())/"NextHorizonLocalAIStudio"
CONFIG=APPDATA/"settings.json"; EVENTS=APPDATA/"events.log"
ROOT=Path(r"C:\NextHorizon\LocalAIStudio")
COMFY=Path(r"C:\Users\parac\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI")
STAGING=ROOT/"staging"/"music-models"

DEFAULTS={
 "server_health_url":"https://www.nexthorizoncompass.com/health",
 "comfy_url":"http://127.0.0.1:8189",
 "public_enabled":False,"automation_armed":False,"paid_ai_enabled":False,
 "news_engine_enabled":False,"comfy_enabled":True,"music_enabled":False,
 "show_advanced":False
}
DOWNLOADS=[
 {"id":"ace_turbo","title":"Музыкальная модель ACE-Step 1.5 Turbo","why":"Создаёт музыку и фон для роликов.",
  "size":"≈ 4.5 ГБ","url":"https://huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files/resolve/main/split_files/diffusion_models/acestep_v1.5_turbo.safetensors?download=true",
  "name":"acestep_v1.5_turbo.safetensors","dest":COMFY/"models"/"diffusion_models",
  "sha":"3f6e0797fad420a39bd33979eb6e840e30989e34a3794e843d23b60ec6e422d7"},
 {"id":"ace_qwen","title":"Помощник для понимания музыкального запроса","why":"Лучше понимает стиль, настроение и описание музыки.",
  "size":"≈ 1.2 ГБ","url":"https://huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files/resolve/main/split_files/text_encoders/qwen_0.6b_ace15.safetensors?download=true",
  "name":"qwen_0.6b_ace15.safetensors","dest":COMFY/"models"/"text_encoders",
  "sha":"fd4590c82153b8ddb67e15a2e7aaa8afa8b83a858c8a9b82a4831063156aa7a7"},
 {"id":"ace_vae","title":"Аудио-декодер ACE-Step","why":"Превращает результат модели в готовый аудиофайл.",
  "size":"≈ 0.8 ГБ","url":"https://huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files/resolve/main/split_files/vae/ace_1.5_vae.safetensors?download=true",
  "name":"ace_1.5_vae.safetensors","dest":COMFY/"models"/"vae",
  "sha":"6de92e3a862acd287e08b024ac90f0783a8635451b728721a33ff03565bcb2bb"},
]
PROGRAMS=[
 ("Comfy Desktop",Path(r"C:\Users\parac\AppData\Local\Programs\Comfy Desktop\Comfy Desktop.exe")),
 ("FFmpeg",Path(r"C:\Users\parac\AppData\Local\Microsoft\WinGet\Packages")),
 ("Git",Path(r"C:\Program Files\Git\cmd\git.exe")),
 ("Python",Path(r"C:\Users\parac\AppData\Local\Programs\Python\Python312\python.exe")),
 ("Node.js",Path(r"C:\Program Files\nodejs\node.exe")),
 ("Desktop Commander",Path(r"C:\Users\parac\AppData\Local\Programs\Desktop Commander\Desktop Commander.exe")),
]
def load_settings():
 APPDATA.mkdir(parents=True,exist_ok=True); out=dict(DEFAULTS)
 try:
  x=json.loads(CONFIG.read_text(encoding="utf-8"))
  if isinstance(x,dict): out.update({k:x[k] for k in DEFAULTS if k in x})
 except Exception: pass
 return out
def save_settings(s):
 APPDATA.mkdir(parents=True,exist_ok=True); safe=dict(DEFAULTS); safe.update({k:s[k] for k in DEFAULTS if k in s})
 CONFIG.write_text(json.dumps(safe,ensure_ascii=False,indent=2),encoding="utf-8")
def get_json(url,timeout=6):
 req=urllib.request.Request(url,headers={"User-Agent":f"NextHorizonLocalAIStudio/{VERSION}"})
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read(2_000_000).decode("utf-8"))
def sha256(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
def single_instance_lock():
 try:
  guard=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
  guard.bind(("127.0.0.1",49871))
  guard.listen(1)
  return guard
 except OSError:
  return None

def vpn_active():
 try:
  cmd=["powershell.exe","-NoProfile","-Command",
       "$x=Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and (($_.Name -match 'Amnezia|Proton|VPN') -or ($_.InterfaceDescription -match 'Amnezia|Proton|VPN')) } | Select-Object -First 1 -ExpandProperty Name; if($x){Write-Output $x}"]
  flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
  out=subprocess.check_output(cmd,text=True,timeout=8,creationflags=flags).strip()
  return out or None
 except Exception:
  return None

class Studio(tk.Tk):
 def __init__(self):
  super().__init__(); self.settings=load_settings(); self.q=queue.Queue(); self.server=None; self.comfy=None
  self.stop_download=False; self.download_running=False
  self.title(f"Next Horizon Local AI Studio v{VERSION}"); self.geometry("1180x760"); self.minsize(980,640)
  self._style(); self._shell(); self.after(200,self._events); self.after(600,self.refresh)
 def _style(self):
  s=ttk.Style(self)
  try:s.theme_use("vista")
  except tk.TclError:pass
  s.configure("Title.TLabel",font=("Segoe UI",22,"bold")); s.configure("H2.TLabel",font=("Segoe UI",15,"bold"))
  s.configure("Good.TLabel",foreground="#16723a",font=("Segoe UI",11,"bold"))
  s.configure("Warn.TLabel",foreground="#9b6500",font=("Segoe UI",11,"bold"))
  s.configure("Bad.TLabel",foreground="#b42318",font=("Segoe UI",11,"bold"))
  s.configure("Big.TButton",font=("Segoe UI",12,"bold"),padding=10)
  s.configure("Card.TFrame",relief="solid",borderwidth=1)
 def _shell(self):
  root=ttk.Frame(self,padding=12); root.pack(fill="both",expand=True); root.columnconfigure(1,weight=1); root.rowconfigure(0,weight=1)
  left=ttk.Frame(root,padding=(0,0,12,0)); left.grid(row=0,column=0,sticky="ns")
  ttk.Label(left,text="NEXT HORIZON",style="H2.TLabel").pack(anchor="w",pady=(4,12))
  self.pages=["Главная","Система","Каналы и подключения","Скачать и настроить","Создание контента","Новости","Настройки"]
  self.menu=tk.Listbox(left,width=23,font=("Segoe UI",12),exportselection=False,activestyle="none")
  for x in self.pages:self.menu.insert("end",x)
  self.menu.pack(fill="y",expand=True); self.menu.selection_set(0); self.menu.bind("<<ListboxSelect>>",self._select)
  ttk.Button(left,text="Для разработчика",command=self.advanced).pack(fill="x",pady=(10,0))
  self.body=ttk.Frame(root); self.body.grid(row=0,column=1,sticky="nsew"); self.show("Главная")
 def _clear(self):
  for w in self.body.winfo_children():w.destroy()
 def _select(self,_=None):
  s=self.menu.curselection()
  if s:self.show(self.pages[s[0]])
 def show(self,name):
  self._clear(); {"Главная":self.home,"Система":self.system_page,"Каналы и подключения":self.channels_page,"Скачать и настроить":self.downloads_page,"Создание контента":self.create_page,"Новости":self.news_page,"Настройки":self.settings_page}[name]()
 def header(self,title,sub=""):
  ttk.Label(self.body,text=title,style="Title.TLabel").pack(anchor="w")
  if sub:ttk.Label(self.body,text=sub,wraplength=800,font=("Segoe UI",10)).pack(anchor="w",pady=(4,14))
 def card(self,title,status,desc):
  f=ttk.Frame(self.body,style="Card.TFrame",padding=12); f.pack(fill="x",pady=5)
  top=ttk.Frame(f); top.pack(fill="x"); ttk.Label(top,text=title,font=("Segoe UI",12,"bold")).pack(side="left")
  st="Good.TLabel" if status.startswith(("Работает","Готово","Установлено","Подключено")) else "Warn.TLabel" if status.startswith(("Нужно скачать","Выключено","Частично","Нужна авторизация")) else "Bad.TLabel"
  ttk.Label(top,text=status,style=st).pack(side="right"); ttk.Label(f,text=desc,wraplength=800).pack(anchor="w",pady=(5,0))
 def home(self):
  self.header("Главная","Здесь только то, что важно для обычной работы.")
  s_ok=bool(self.server and self.server.get("status")=="ok"); c_ok=bool(self.comfy)
  music_ready=all(self._download_status(x)=="Установлено" for x in DOWNLOADS)
  self.card("Сервер Next Horizon","Работает" if s_ok else "Нет связи","Главный сервер проекта. Он продолжает работать даже когда ноутбук выключен.")
  self.card("Comfy Studio","Работает" if c_ok else "Выключено","Создаёт изображения, графику и позже видео на твоей RTX 3050.")
  self.card("Музыка","Готово" if music_ready else "Нужно скачать","Для собственной фоновой музыки нужно около 6.5 ГБ моделей. Это делается один раз.")
  self.card("Новости","Выключено","News Engine уже предусмотрен, но пока не запускается в production.")
  pilot=((self.server or {}).get("components") or {}).get("pilot-recovery") or {}
  state=(pilot.get("details") or {}).get("state")
  if state=="awaiting_exact_mp4_review":
   self.card("Тестовый ролик","Готово","Thailand e-Visa уже отрендерен и прошёл QC. Осталась проверка готового MP4.")
  integrations=(self.server or {}).get("integrations") or {}
  connected=sum(1 for x in integrations.values() if x.get("status")=="connected")
  if integrations:self.card("Каналы",f"{connected} подключено","Открой «Каналы и подключения», чтобы увидеть каждый сервис.")
  ttk.Button(self.body,text="Проверить всё",style="Big.TButton",command=self.refresh).pack(anchor="e",pady=12)
 def system_page(self):
  self.header("Система","Здесь видно, что реально работает прямо сейчас.")
  server_ok=bool(self.server and self.server.get("status")=="ok")
  comfy_ok=bool(self.comfy)
  self.card("Основной сервер Next Horizon","Работает" if server_ok else "Нет связи","Сервер хранит Media Factory, каналы, аналитику и продолжает работать без ноутбука.")
  if comfy_ok:
   dev=(self.comfy.get("devices") or [{}])[0]
   gpu=str(dev.get("name") or "RTX 3050 6GB")
   free=round((dev.get("vram_free") or 0)/1024**3,1)
   self.card("Локальный AI / Comfy","Работает",f"{gpu}. Свободно примерно {free} ГБ видеопамяти.")
  else:
   self.card("Локальный AI / Comfy","Выключено","Запусти Studio через ярлык — он сам поднимет Comfy при необходимости.")
  music_ready=all(self._download_status(x)=="Установлено" for x in DOWNLOADS)
  self.card("Music Agent","Готово" if music_ready else "Нужно скачать","После загрузки моделей сможет делать собственную музыку и фон для роликов.")
  ttk.Button(self.body,text="Обновить состояние",style="Big.TButton",command=self.refresh).pack(anchor="e",pady=12)

 def _human_channel(self,key,data):
  status=data.get("status","not_connected")
  if key=="youtube":
   if status=="connected": return ("Подключено","YouTube готов. Публикация ограничена PRIVATE-тестами.")
   if status=="configured": return ("Нужна авторизация","Настройки Google сохранены, но активное подключение ещё не завершено.")
   return ("Не подключено","Нужно подключить Google/YouTube OAuth.")
  if key=="facebook":
   if status=="connected":
    return ("Подключено" if data.get("publisher_enabled") else "Подключено, публикация выключена","Facebook Page Gateway видит выбранную страницу. Публикация остаётся выключенной.")
   if status=="configured": return ("Нужна авторизация","Meta-настройки есть, но нужно заново пройти OWNER OAuth и выбрать страницу.")
   return ("Не подключено","Модуль Facebook установлен, но в текущем production нет активной Meta-конфигурации/OAuth.")
  if key=="telegram":
   if status=="connected":
    return ("Подключено" if data.get("public_enabled") else "Подключено, PUBLIC выключен","Telegram настроен. Публичный процесс сейчас безопасно выключен.")
   return ("Не подключено","Нужно проверить Telegram credentials/OWNER.")
  if key=="website": return ("Работает","Сайт Next Horizon доступен. Публичная автоматика выключена.")
  if key=="instagram": return ("Не подключено","Production-коннектор Instagram ещё не установлен.")
  if key=="tiktok": return ("Не подключено","Production-коннектор TikTok ещё не установлен.")
  return ("Не подключено","Статус неизвестен.")

 def channels_page(self):
  self.header("Каналы и подключения","Фактическое состояние с сервера. Секреты и токены здесь никогда не показываются.")
  data=(self.server or {}).get("integrations") or {}
  labels=[("youtube","YouTube"),("facebook","Facebook"),("telegram","Telegram"),("instagram","Instagram"),("tiktok","TikTok"),("website","Сайт")]
  for key,title in labels:
   state,desc=self._human_channel(key,data.get(key) or {})
   f=ttk.Frame(self.body,style="Card.TFrame",padding=12); f.pack(fill="x",pady=5)
   top=ttk.Frame(f); top.pack(fill="x")
   ttk.Label(top,text=title,font=("Segoe UI",12,"bold")).pack(side="left")
   style="Good.TLabel" if state.startswith(("Подключено","Работает")) else "Warn.TLabel"
   ttk.Label(top,text=state,style=style).pack(side="right")
   ttk.Label(f,text=desc,wraplength=800).pack(anchor="w",pady=(5,4))
   if key=="youtube": ttk.Button(f,text="Настройки YouTube",command=lambda:webbrowser.open("https://www.nexthorizoncompass.com/youtube-connect")).pack(anchor="e")
   elif key=="telegram": ttk.Button(f,text="Настройки Telegram",command=lambda:webbrowser.open("https://www.nexthorizoncompass.com/telegram-setup")).pack(anchor="e")
   elif key=="facebook": ttk.Button(f,text="Проверить Facebook",command=lambda:webbrowser.open("https://www.nexthorizoncompass.com/launch-readiness")).pack(anchor="e")
  ttk.Button(self.body,text="Обновить статусы",style="Big.TButton",command=self.refresh).pack(anchor="e",pady=12)

 def _download_status(self,item):
  final=Path(item["dest"])/item["name"]; part=STAGING/(item["name"]+".part")
  if final.exists():
   try:
    if sha256(final)==item["sha"]:return "Установлено"
   except Exception:pass
  if part.exists() and part.stat().st_size>0:return "Частично"
  return "Нужно скачать"
 def downloads_page(self):
  self.header("Скачать и настроить","Программа сама проверит VPN. После его выключения нажми одну кнопку — загрузка продолжится с уже скачанного места и не потеряет прогресс.")
  ttk.Label(self.body,text="Уже установлено на ноутбуке:",style="H2.TLabel").pack(anchor="w")
  for name,path in PROGRAMS:
   ttk.Label(self.body,text=f"✓ {name}" if path.exists() else f"• {name} — не найден").pack(anchor="w",pady=1)
  ttk.Separator(self.body).pack(fill="x",pady=12)
  ttk.Label(self.body,text="Нужно для Music Agent:",style="H2.TLabel").pack(anchor="w")
  self.dl_labels={}
  for item in DOWNLOADS:
   f=ttk.Frame(self.body,style="Card.TFrame",padding=10); f.pack(fill="x",pady=4)
   top=ttk.Frame(f); top.pack(fill="x"); ttk.Label(top,text=item["title"],font=("Segoe UI",11,"bold")).pack(side="left")
   status=self._download_status(item)
   part=STAGING/(item["name"]+".part")
   if status=="Частично" and part.exists(): status=f"Частично — {part.stat().st_size/1024/1024/1024:.2f} ГБ сохранено"
   lab=ttk.Label(top,text=status); lab.pack(side="right"); self.dl_labels[item["id"]]=lab
   ttk.Label(f,text=f"{item['why']}  Размер: {item['size']}",wraplength=780).pack(anchor="w",pady=(3,0))
  self.progress=ttk.Progressbar(self.body,mode="determinate",maximum=100); self.progress.pack(fill="x",pady=(14,4))
  self.progress_text=ttk.Label(self.body,text=""); self.progress_text.pack(anchor="w")
  row=ttk.Frame(self.body); row.pack(fill="x",pady=10)
  self.download_btn=ttk.Button(row,text="Я выключил VPN — скачать всё необходимое",style="Big.TButton",command=self.start_download); self.download_btn.pack(side="left")
  ttk.Button(row,text="Остановить",command=self.stop_downloads).pack(side="left",padx=8)
  ttk.Label(self.body,text="После загрузки файлы проверяются по SHA-256. Повреждённый файл не будет установлен.",wraplength=800).pack(anchor="w",pady=6)
 def start_download(self):
  if self.download_running:return
  vpn=vpn_active()
  if vpn:
   messagebox.showwarning("VPN включён",f"Сейчас активен VPN: {vpn}.\n\nВыключи VPN и нажми кнопку ещё раз. Уже скачанные части моделей сохранятся.")
   return
  if not messagebox.askyesno("Загрузка","VPN не обнаружен. Начать загрузку напрямую?\n\nПрограмма продолжит уже скачанные части и проверит каждый файл после завершения."):return
  self.stop_download=False; self.download_running=True; self.download_btn.config(state="disabled")
  threading.Thread(target=self._download_worker,daemon=True).start()
 def stop_downloads(self):
  self.stop_download=True; self.q.put(("download_note","Останавливаю после текущего сетевого шага…"))
 def _download_worker(self):
  STAGING.mkdir(parents=True,exist_ok=True)
  try:
   for item in DOWNLOADS:
    if self.stop_download:break
    final=Path(item["dest"])/item["name"]; Path(item["dest"]).mkdir(parents=True,exist_ok=True)
    if final.exists():
     try:
      if sha256(final)==item["sha"]:
       self.q.put(("download_status",item["id"],"Установлено")); continue
     except Exception:pass
    part=STAGING/(item["name"]+".part")
    self.q.put(("download_note",f"Скачиваю: {item['title']}"))
    failures=0
    last_size=part.stat().st_size if part.exists() else 0
    while True:
     if self.stop_download:break
     cmd=["curl.exe","-L","--fail","--retry","20","--retry-all-errors","--retry-delay","5",
          "--connect-timeout","20","--speed-time","90","--speed-limit","1024","-C","-",item["url"],"-o",str(part)]
     p=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                        creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
     while p.poll() is None:
      if self.stop_download:
       p.terminate(); break
      size=part.stat().st_size if part.exists() else 0
      self.q.put(("download_progress",item["id"],size,item["size"])); time.sleep(1)
     if self.stop_download:break
     if p.returncode==0:break
     size=part.stat().st_size if part.exists() else 0
     failures = 0 if size>last_size else failures+1
     last_size=size
     if failures>=6:raise RuntimeError("network_unstable")
     self.q.put(("download_note",f"Связь прервалась. Продолжаю {item['title']} с {size/1024/1024:,.0f} МБ…"))
     time.sleep(5)
    if self.stop_download:break
    self.q.put(("download_note",f"Проверяю: {item['title']}"))
    if sha256(part)!=item["sha"]:raise RuntimeError("sha256_mismatch")
    shutil.move(str(part),str(final)); self.q.put(("download_status",item["id"],"Установлено"))
   if not self.stop_download and all(self._download_status(x)=="Установлено" for x in DOWNLOADS):
    self.settings["music_enabled"]=True; save_settings(self.settings); self.q.put(("download_done","Готово. Music Agent получил все необходимые модели."))
   elif self.stop_download:self.q.put(("download_done","Загрузка остановлена. В следующий раз продолжится с этого места."))
  except Exception as e:self.q.put(("download_done",f"Ошибка: {type(e).__name__}. Уже скачанное сохранено, можно повторить позже."))
  finally:self.download_running=False
 def create_page(self):
  self.header("Создание контента","Здесь будут простые рабочие кнопки. Технические модели программа выбирает сама.")
  items=[("Создать изображение","Comfy готов. В следующем этапе добавим готовые шаблоны Next Horizon."),
         ("Создать музыку","Станет доступно после завершения загрузки Music Agent."),
         ("Создать видео","Будет использовать Media Factory и локальный GPU там, где это выгодно."),
         ("Открыть Comfy Studio","Для ручной работы, если она когда-нибудь понадобится.")]
  for title,desc in items:
   f=ttk.Frame(self.body,style="Card.TFrame",padding=12); f.pack(fill="x",pady=5)
   ttk.Label(f,text=title,font=("Segoe UI",12,"bold")).pack(anchor="w"); ttk.Label(f,text=desc,wraplength=800).pack(anchor="w",pady=3)
  ttk.Button(self.body,text="Открыть Comfy Studio",style="Big.TButton",command=lambda:webbrowser.open(self.settings["comfy_url"])).pack(anchor="e",pady=10)
 def news_page(self):
  self.header("Новости","Будущий автономный новостной канал. Пока он только подготовлен и не публикует ничего.")
  for t,d in [("Стартовый рынок","США"),("Главная платформа","YouTube"),("Дополнительно","Telegram, TikTok, Instagram, Facebook, сайт"),
              ("Главное правило","Сначала проверка фактов и источников, потом публикация."),("Персонаж","Оригинальный кот-ведущий с отдельным серьёзным режимом.")]:
   self.card(t,"Готово" if t!="Главное правило" else "Работает",d)
 def settings_page(self):
  self.header("Настройки","Обычные настройки. Опасные функции здесь не включаются.")
  ttk.Label(self.body,text="PUBLIC: ВЫКЛ",style="Good.TLabel").pack(anchor="w",pady=4)
  ttk.Label(self.body,text="Автоматическая публикация: ВЫКЛ",style="Good.TLabel").pack(anchor="w",pady=4)
  ttk.Label(self.body,text="Платный AI: ВЫКЛ",style="Good.TLabel").pack(anchor="w",pady=4)
  ttk.Separator(self.body).pack(fill="x",pady=12)
  ttk.Label(self.body,text="Если что-то перестало работать, просто нажми «Проверить всё» на главной.").pack(anchor="w")
 def advanced(self):
  self._clear(); self.header("Для разработчика","Этот раздел нужен мне для диагностики. Тебе обычно сюда заходить не нужно.")
  t=tk.Text(self.body,height=30,wrap="word"); t.pack(fill="both",expand=True)
  obj={"version":VERSION,"settings":self.settings,"server":self.server,"comfy":self.comfy,
       "downloads":[{**{k:v for k,v in x.items() if k not in ("url","sha","dest")}, "status":self._download_status(x)} for x in DOWNLOADS]}
  t.insert("end",json.dumps(obj,ensure_ascii=False,indent=2)[:50000])
 def refresh(self):
  def server():
   try:self.q.put(("server",get_json(self.settings["server_health_url"],8)))
   except Exception:self.q.put(("server",None))
  def comfy():
   try:self.q.put(("comfy",get_json(self.settings["comfy_url"].rstrip("/")+"/system_stats",8)))
   except Exception:self.q.put(("comfy",None))
  threading.Thread(target=server,daemon=True).start(); threading.Thread(target=comfy,daemon=True).start()
 def _events(self):
  try:
   while True:
    e=self.q.get_nowait(); kind=e[0]
    if kind=="server":self.server=e[1]
    elif kind=="comfy":self.comfy=e[1]
    elif kind=="download_status":
     if hasattr(self,"dl_labels") and e[1] in self.dl_labels:self.dl_labels[e[1]].config(text=e[2])
    elif kind=="download_note":
     if hasattr(self,"progress_text"):self.progress_text.config(text=e[1])
    elif kind=="download_progress":
     if hasattr(self,"progress_text"):
      mb=e[2]/1024/1024; self.progress_text.config(text=f"{e[1]}: скачано {mb:,.0f} МБ")
      self.progress.config(value=(int(time.time())%90)+5)
    elif kind=="download_done":
     if hasattr(self,"progress_text"):self.progress_text.config(text=e[1]); self.progress.config(value=100 if "Готово" in e[1] else 0)
     if hasattr(self,"download_btn"):self.download_btn.config(state="normal")
     messagebox.showinfo("Next Horizon",e[1])
  except queue.Empty:pass
  self.after(200,self._events)
if __name__=="__main__":
 if "--health-probe" in sys.argv:
  print(json.dumps({"status":"ok","version":VERSION},ensure_ascii=False))
  raise SystemExit(0)
 _single_instance_guard=single_instance_lock()
 if _single_instance_guard is None:raise SystemExit(0)
 Studio().mainloop()
