import struct, math, threading, time, os
import pymem, pymem.process
import customtkinter as ctk

# ── ОФФСЕТЫ build 8684 ───────────────────────────────────
VA    = 0x1230274   # hw.dll viewangles
ELIST = 0x12043C8   # hw.dll entity list
ESIZE = 0x250       # entity struct size
ENAME = 0x104       # name offset
EPOS  = 0x188       # position offset
EGRND = 0x122E2D4   # hw.dll onground

# ── ПАМЯТЬ ────────────────────────────────────────────────
pm = None
hw = cl = 0
ok = False

def attach():
    global pm, hw, cl, ok
    try:
        pm  = pymem.Pymem("cs.exe")
        hw  = pymem.process.module_from_name(pm.process_handle, "hw.dll").lpBaseOfDll
        cl  = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        ok  = True
        return "OK"
    except Exception as e:
        ok = False
        return str(e)

def rv3(a):
    try: return struct.unpack('fff', pm.read_bytes(a, 12))
    except: return (0.,0.,0.)

def wv3(a, x, y, z):
    try: pm.write_bytes(a, struct.pack('fff', x, y, z), 12)
    except: pass

def ri(a):
    try: return pm.read_int(a)
    except: return 0

def rstr(a):
    try: return pm.read_bytes(a, 44).split(b'\x00')[0].decode('utf-8','ignore').strip()
    except: return ""

def get_angles():   return rv3(hw + VA)
def set_angles(p,y): wv3(hw + VA, p, y, 0.)
def is_ground():    return ri(hw + EGRND) == 1

def get_bots():
    me  = rstr(hw + ELIST + 1 * ESIZE + ENAME)  # локальный = индекс 1
    out = []
    for i in range(1, 33):
        n = rstr(hw + ELIST + i * ESIZE + ENAME)
        if not n or n == me: continue
        p = rv3(hw + ELIST + i * ESIZE + EPOS)
        if p == (0.,0.,0.): continue
        out.append(p)
    return out

def my_pos():
    return rv3(hw + ELIST + 1 * ESIZE + EPOS)

# ── УТИЛИТЫ ───────────────────────────────────────────────
def norm(a):
    while a >  180: a -= 360
    while a < -180: a += 360
    return a

# ── СОСТОЯНИЕ ФУНКЦИЙ ─────────────────────────────────────
state = {'aim': False, 'esp': False, 'bhop': False}
aim_cfg = {'fov': 180., 'smooth': 2., 'head': True}

# ── AIMBOT ────────────────────────────────────────────────
def aim_loop():
    while True:
        if state['aim'] and ok:
            try:
                ca   = get_angles()
                src  = my_pos()
                bots = get_bots()
                best = None; best_d = aim_cfg['fov']
                for pos in bots:
                    tz = pos[2] + (64. if aim_cfg['head'] else 0.)
                    dx,dy,dz = pos[0]-src[0], pos[1]-src[1], tz-src[2]
                    ta = (-math.degrees(math.atan2(dz, math.hypot(dx,dy))),
                           math.degrees(math.atan2(dy, dx)))
                    d = math.hypot(norm(ca[0]-ta[0]), norm(ca[1]-ta[1]))
                    if d < best_d: best_d, best = d, ta
                if best:
                    s = aim_cfg['smooth']
                    set_angles(ca[0] + norm(best[0]-ca[0])/s,
                               ca[1] + norm(best[1]-ca[1])/s)
            except: pass
        time.sleep(0.008)

# ── BHOP ──────────────────────────────────────────────────
def bhop_loop():
    air = False
    while True:
        if state['bhop'] and ok:
            try:
                import win32api, win32con
                gnd = is_ground()
                if air and gnd:
                    win32api.keybd_event(win32con.VK_SPACE, 0, 0, 0)
                    time.sleep(0.013)
                    win32api.keybd_event(win32con.VK_SPACE, 0, win32con.KEYEVENTF_KEYUP, 0)
                air = not gnd
            except: pass
        time.sleep(0.005)

# ── ЗАПУСК ПОТОКОВ ────────────────────────────────────────
threading.Thread(target=aim_loop,  daemon=True).start()
threading.Thread(target=bhop_loop, daemon=True).start()

# ── UI ────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
AC = "#c850ff"; BG = "#0d0d0d"; C1 = "#161616"

root = ctk.CTk()
root.title("CS 1.6 Hack")
root.geometry("320x580")
root.resizable(False, False)
root.configure(fg_color=BG)

# Шапка
hdr = ctk.CTkFrame(root, fg_color=C1, corner_radius=0, height=48)
hdr.pack(fill="x")
ctk.CTkLabel(hdr, text="CS 1.6", font=("Arial",15,"bold"), text_color=AC).pack(side="left", padx=14, pady=10)
dot = ctk.CTkLabel(hdr, text="●", font=("Arial",18), text_color="#f44")
dot.pack(side="right", padx=12)
slbl = ctk.CTkLabel(hdr, text="NOT ATTACHED", font=("Arial",10), text_color="#555")
slbl.pack(side="right")

# Attach
def do_attach():
    msg = attach()
    if ok:
        dot.configure(text_color="#4f8")
        slbl.configure(text="ATTACHED")
    else:
        dot.configure(text_color="#f44")
        slbl.configure(text=f"ERR: {msg[:22]}")

ctk.CTkButton(root, text="ATTACH TO CS 1.6", command=do_attach,
              fg_color="#1e1040", hover_color="#2e1860",
              border_color=AC, border_width=1,
              font=("Arial",12,"bold"), height=36,
              corner_radius=8).pack(fill="x", padx=14, pady=(10,4))

# Дебаг строка
dbg = ctk.CTkLabel(root, text="pitch=--  yaw=--  bots=--",
                   font=("Courier",10), text_color="#444")
dbg.pack(pady=2)

# ── Кнопки-тогглы (большие, видимые) ─────────────────────
def make_toggle(label, key, color_on="#c850ff"):
    frame = ctk.CTkFrame(root, fg_color=C1, corner_radius=10)
    frame.pack(fill="x", padx=14, pady=4)
    btn = ctk.CTkButton(frame, text=f"◯  {label}  —  ВЫКЛ",
                        command=lambda: toggle(key, btn, label, color_on),
                        fg_color="#1a1a1a", hover_color="#222",
                        border_color="#333", border_width=1,
                        font=("Arial",13,"bold"), height=44,
                        corner_radius=8, text_color="#555")
    btn.pack(fill="x", padx=6, pady=6)
    return btn

def toggle(key, btn, label, color_on):
    state[key] = not state[key]
    if state[key]:
        btn.configure(text=f"●  {label}  —  ВКЛ",
                      fg_color="#1e1040", border_color=color_on,
                      text_color=color_on)
    else:
        btn.configure(text=f"◯  {label}  —  ВЫКЛ",
                      fg_color="#1a1a1a", border_color="#333",
                      text_color="#555")

btn_aim  = make_toggle("AIMBOT",     "aim",  "#c850ff")
btn_esp  = make_toggle("ESP / WH",   "esp",  "#ff5050")
btn_bhop = make_toggle("BUNNY HOP",  "bhop", "#50ffaa")

# FOV ползунок
fov_frame = ctk.CTkFrame(root, fg_color=C1, corner_radius=10)
fov_frame.pack(fill="x", padx=14, pady=4)
fov_row = ctk.CTkFrame(fov_frame, fg_color="transparent")
fov_row.pack(fill="x", padx=10, pady=(8,0))
ctk.CTkLabel(fov_row, text="FOV", font=("Arial",11), text_color="#aaa", width=60).pack(side="left")
fov_lbl = ctk.CTkLabel(fov_row, text="180°", font=("Arial",11,"bold"), text_color=AC, width=40)
fov_lbl.pack(side="right")
def set_fov(v):
    aim_cfg['fov'] = float(v)
    fov_lbl.configure(text=f"{int(v)}°")
fov_sl = ctk.CTkSlider(fov_frame, from_=5, to=180, command=set_fov,
                       button_color=AC, progress_color=AC)
fov_sl.set(180)
fov_sl.pack(fill="x", padx=10, pady=(4,10))

# SMOOTH ползунок
sm_frame = ctk.CTkFrame(root, fg_color=C1, corner_radius=10)
sm_frame.pack(fill="x", padx=14, pady=4)
sm_row = ctk.CTkFrame(sm_frame, fg_color="transparent")
sm_row.pack(fill="x", padx=10, pady=(8,0))
ctk.CTkLabel(sm_row, text="SMOOTH", font=("Arial",11), text_color="#aaa", width=60).pack(side="left")
sm_lbl = ctk.CTkLabel(sm_row, text="2x", font=("Arial",11,"bold"), text_color=AC, width=40)
sm_lbl.pack(side="right")
def set_smooth(v):
    aim_cfg['smooth'] = float(v)
    sm_lbl.configure(text=f"{float(v):.1f}x")
sm_sl = ctk.CTkSlider(sm_frame, from_=1, to=15, command=set_smooth,
                      button_color=AC, progress_color=AC)
sm_sl.set(2)
sm_sl.pack(fill="x", padx=10, pady=(4,10))

# ── Тик UI ───────────────────────────────────────────────
def tick():
    if ok:
        try:
            p,y,_ = get_angles()
            b = get_bots()
            status = "AIMING" if state['aim'] and b else ""
            dbg.configure(text=f"pitch={p:.1f}  yaw={y:.1f}  bots={len(b)}  {status}")
        except: pass
    root.after(150, tick)

tick()
root.mainloop()
