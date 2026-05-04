import struct, math, threading, time
import pymem, pymem.process
import customtkinter as ctk

# ── ОФФСЕТЫ build 8684 ───────────────────────────────────
# viewangles — пишем во ВСЕ три адреса чтобы точно сработало
VA_HW1  = 0x1230274   # hw.dll
VA_HW2  = 0xEC7AB0    # hw.dll (зеркало)
VA_CL   = 0x12D9F0    # client.dll

ELIST   = 0x12043C8   # hw.dll entity list
ESIZE   = 0x250
ENAME   = 0x104
EPOS    = 0x188

ONGRND  = 0x122E2D4   # hw.dll onground
FJUMP   = 0x131434    # client.dll force jump (для bhop через память)

# ── ПАМЯТЬ ────────────────────────────────────────────────
pm = None; hw = cl = 0; ok = False

def attach():
    global pm, hw, cl, ok
    try:
        pm = pymem.Pymem("cs.exe")
        hw = pymem.process.module_from_name(pm.process_handle, "hw.dll").lpBaseOfDll
        cl = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        ok = True; return "OK"
    except Exception as e:
        ok = False; return str(e)

def rv3(a):
    try: return struct.unpack('fff', pm.read_bytes(a, 12))
    except: return (0.,0.,0.)

def ri(a):
    try: return pm.read_int(a)
    except: return 0

def wi(a, v):
    try: pm.write_int(a, v)
    except: pass

def wv3(a, x, y, z):
    try: pm.write_bytes(a, struct.pack('fff', x, y, z), 12)
    except: pass

def rstr(a):
    try: return pm.read_bytes(a, 44).split(b'\x00')[0].decode('utf-8','ignore').strip()
    except: return ""

def get_angles():
    return rv3(hw + VA_HW1)

def set_angles(p, y):
    # Пишем во все три адреса
    wv3(hw + VA_HW1, p, y, 0.)
    wv3(hw + VA_HW2, p, y, 0.)
    wv3(cl + VA_CL,  p, y, 0.)

def is_ground():
    return ri(hw + ONGRND) == 1

def get_bots():
    me  = rstr(hw + ELIST + 1 * ESIZE + ENAME)
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

def norm(a):
    while a >  180: a -= 360
    while a < -180: a += 360
    return a

# ── СОСТОЯНИЕ ─────────────────────────────────────────────
S = {'aim': False, 'bhop': False}
CFG = {'fov': 180., 'smooth': 2., 'head': True}

# ── AIMBOT ────────────────────────────────────────────────
def aim_loop():
    while True:
        if S['aim'] and ok:
            try:
                ca = get_angles(); src = my_pos(); bots = get_bots()
                best = None; best_d = CFG['fov']
                for pos in bots:
                    tz = pos[2] + (64. if CFG['head'] else 0.)
                    dx,dy,dz = pos[0]-src[0], pos[1]-src[1], tz-src[2]
                    ta = (-math.degrees(math.atan2(dz, math.hypot(dx,dy))),
                           math.degrees(math.atan2(dy, dx)))
                    d = math.hypot(norm(ca[0]-ta[0]), norm(ca[1]-ta[1]))
                    if d < best_d: best_d, best = d, ta
                if best:
                    s = CFG['smooth']
                    set_angles(ca[0]+norm(best[0]-ca[0])/s,
                               ca[1]+norm(best[1]-ca[1])/s)
            except: pass
        time.sleep(0.008)

# ── BHOP (через память) ───────────────────────────────────
def bhop_loop():
    air = False
    while True:
        if S['bhop'] and ok:
            try:
                gnd = is_ground()
                if not gnd:
                    wi(cl + FJUMP, 5)   # force jump flag
                    air = True
                else:
                    if air: wi(cl + FJUMP, 0)
                    air = False
            except: pass
        time.sleep(0.005)

threading.Thread(target=aim_loop,  daemon=True).start()
threading.Thread(target=bhop_loop, daemon=True).start()

# ── UI ────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
AC="#c850ff"; BG="#0d0d0d"; C1="#161616"

root = ctk.CTk()
root.title("CS 1.6"); root.geometry("320x560")
root.resizable(False,False); root.configure(fg_color=BG)

hdr = ctk.CTkFrame(root, fg_color=C1, corner_radius=0, height=48)
hdr.pack(fill="x")
ctk.CTkLabel(hdr, text="CS 1.6 HACK", font=("Arial",15,"bold"), text_color=AC).pack(side="left",padx=14,pady=10)
dot  = ctk.CTkLabel(hdr, text="●", font=("Arial",18), text_color="#f44"); dot.pack(side="right",padx=12)
slbl = ctk.CTkLabel(hdr, text="NOT ATTACHED", font=("Arial",10), text_color="#555"); slbl.pack(side="right")

def do_attach():
    msg = attach()
    if ok: dot.configure(text_color="#4f8"); slbl.configure(text="ATTACHED")
    else:  dot.configure(text_color="#f44"); slbl.configure(text=f"ERR:{msg[:20]}")

ctk.CTkButton(root, text="ATTACH TO CS 1.6", command=do_attach,
              fg_color="#1e1040", hover_color="#2e1860", border_color=AC, border_width=1,
              font=("Arial",12,"bold"), height=36, corner_radius=8).pack(fill="x",padx=14,pady=(10,2))

# Тест-кнопка: проверяет работает ли запись углов
def test_write():
    if not ok: return
    ca = get_angles()
    set_angles(ca[0] - 30, ca[1])  # задрать вверх на 30° — если сработало, вид изменится
    dbg.configure(text="TEST: написал pitch-30, если вид не изменился — адрес неверный", text_color="#fc8")

ctk.CTkButton(root, text="TEST (задрать вид вверх)", command=test_write,
              fg_color="#1a1000", hover_color="#2a2000", border_color="#fc8", border_width=1,
              font=("Arial",11), height=30, corner_radius=8).pack(fill="x",padx=14,pady=(2,4))

dbg = ctk.CTkLabel(root, text="pitch=--  yaw=--  bots=--", font=("Courier",10), text_color="#444")
dbg.pack(pady=2)

def make_btn(label, key, col):
    btn = ctk.CTkButton(root, text=f"◯  {label}  —  ВЫКЛ",
                        fg_color="#1a1a1a", hover_color="#222",
                        border_color="#333", border_width=1,
                        font=("Arial",13,"bold"), height=46, corner_radius=8, text_color="#555")
    def click():
        S[key] = not S[key]
        if S[key]: btn.configure(text=f"●  {label}  —  ВКЛ",  fg_color="#1e1040", border_color=col, text_color=col)
        else:      btn.configure(text=f"◯  {label}  —  ВЫКЛ", fg_color="#1a1a1a", border_color="#333", text_color="#555")
    btn.configure(command=click)
    btn.pack(fill="x", padx=14, pady=4)
    return btn

make_btn("AIMBOT",    "aim",  AC)
make_btn("BHOP",      "bhop", "#50ffaa")

# FOV
fr = ctk.CTkFrame(root,fg_color=C1,corner_radius=10); fr.pack(fill="x",padx=14,pady=4)
row = ctk.CTkFrame(fr,fg_color="transparent"); row.pack(fill="x",padx=10,pady=(8,0))
ctk.CTkLabel(row,text="AIM FOV",font=("Arial",11),text_color="#aaa").pack(side="left")
fl = ctk.CTkLabel(row,text="180°",font=("Arial",11,"bold"),text_color=AC); fl.pack(side="right")
def sf(v): CFG['fov']=float(v); fl.configure(text=f"{int(v)}°")
fsl = ctk.CTkSlider(fr,from_=5,to=180,command=sf,button_color=AC,progress_color=AC)
fsl.set(180); fsl.pack(fill="x",padx=10,pady=(4,10))

# SMOOTH
sr = ctk.CTkFrame(root,fg_color=C1,corner_radius=10); sr.pack(fill="x",padx=14,pady=4)
srow = ctk.CTkFrame(sr,fg_color="transparent"); srow.pack(fill="x",padx=10,pady=(8,0))
ctk.CTkLabel(srow,text="SMOOTH",font=("Arial",11),text_color="#aaa").pack(side="left")
sl2 = ctk.CTkLabel(srow,text="2x",font=("Arial",11,"bold"),text_color=AC); sl2.pack(side="right")
def ss(v): CFG['smooth']=float(v); sl2.configure(text=f"{float(v):.1f}x")
ssl = ctk.CTkSlider(sr,from_=1,to=15,command=ss,button_color=AC,progress_color=AC)
ssl.set(2); ssl.pack(fill="x",padx=10,pady=(4,10))

def tick():
    if ok:
        try:
            p,y,_ = get_angles()
            b = get_bots()
            aim_st = " ► AIMING" if S['aim'] and b else ""
            dbg.configure(text=f"p={p:.1f} y={y:.1f} bots={len(b)}{aim_st}", text_color="#555")
        except: pass
    root.after(150, tick)

tick()
root.mainloop()
