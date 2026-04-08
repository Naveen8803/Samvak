"""
gen_diagrams_v13.py — Generate all 10 fresh diagrams for Samvak V13 document.
Output: E:\sam\Project documents\fresh_diagrams\  (PNG, 300 DPI)
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = r"E:\sam\Project documents\fresh_diagrams"
os.makedirs(OUT, exist_ok=True)

def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {name}")

colors = {
    "head":  "#1a3a5c",   # dark navy
    "box":   "#eaf1fb",   # light blue fill
    "green": "#e8f5e9",
    "orange":"#fff3e0",
    "purple":"#f3e5f5",
    "gray":  "#f5f5f5",
    "red":   "#fce4ec",
    "border":"#546e7a",
    "actor": "#0d47a1",
    "line":  "#37474f",
}

def box(ax, x, y, w, h, label, fill="#eaf1fb", fs=9, bold=False, radius=0.04, border="#546e7a"):
    r = FancyBboxPatch((x-w/2, y-h/2), w, h,
                       boxstyle=f"round,pad={radius}", linewidth=1.2,
                       edgecolor=border, facecolor=fill)
    ax.add_patch(r)
    weight = "bold" if bold else "normal"
    ax.text(x, y, label, ha="center", va="center", fontsize=fs,
            fontweight=weight, wrap=True,
            multialignment="center")

def hdr(ax, x, y, w, h, label, fill="#1a3a5c", fs=9):
    r = FancyBboxPatch((x-w/2, y-h/2), w, h,
                       boxstyle="round,pad=0.02", linewidth=1.2,
                       edgecolor="#37474f", facecolor=fill)
    ax.add_patch(r)
    ax.text(x, y, label, ha="center", va="center", fontsize=fs,
            fontweight="bold", color="white", multialignment="center")

def arr(ax, x1, y1, x2, y2, label="", color="#37474f", style="-|>"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=1.2))
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my+0.03, label, ha="center", va="bottom", fontsize=7, color=color)

def actor(ax, x, y, label, color="#0d47a1"):
    circle = plt.Circle((x, y+0.18), 0.07, fill=False, color=color, lw=1.5)
    ax.add_patch(circle)
    ax.plot([x, x], [y+0.11, y-0.05], color=color, lw=1.5)
    ax.plot([x-0.09, x+0.09], [y+0.02, y+0.02], color=color, lw=1.5)
    ax.plot([x, x-0.07], [y-0.05, y-0.18], color=color, lw=1.5)
    ax.plot([x, x+0.07], [y-0.05, y-0.18], color=color, lw=1.5)
    ax.text(x, y-0.26, label, ha="center", va="top", fontsize=8, fontweight="bold", color=color)

def usecase(ax, x, y, w, h, label, fill="#eaf1fb"):
    e = mpatches.Ellipse((x, y), w, h, edgecolor="#546e7a", facecolor=fill, lw=1.2)
    ax.add_patch(e)
    ax.text(x, y, label, ha="center", va="center", fontsize=7.5,
            multialignment="center")

# ═══════════════════════════════════════════════════════════
# 1. USE CASE DIAGRAM
# ═══════════════════════════════════════════════════════════
def make_use_case():
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_xlim(0, 11); ax.set_ylim(0, 7); ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_title("Figure 5.1: Use Case Diagram — Saṁvāk System", fontsize=12, fontweight="bold", pad=10)

    # System boundary
    sys_rect = FancyBboxPatch((1.8, 0.4), 7.0, 6.2, boxstyle="round,pad=0.05",
                              edgecolor="#1a3a5c", facecolor="#f8fbff", lw=2, linestyle="--")
    ax.add_patch(sys_rect)
    ax.text(5.3, 6.45, "Saṁvāk System Boundary", ha="center", fontsize=9,
            color="#1a3a5c", fontstyle="italic")

    # Actors
    actor(ax, 0.8, 3.5, "Deaf User\n(Signer)")
    actor(ax, 10.2, 3.5, "Hearing User")
    actor(ax, 5.3, 0.1, "Gemini API\n(External)", color="#c62828")

    # Use cases
    ucs = [
        (5.3, 5.7, 2.6, 0.55, "UC1: Register / Login", colors["box"]),
        (3.0, 4.6, 2.5, 0.55, "UC2: Sign-to-Speech\nRecognition", colors["green"]),
        (7.6, 4.6, 2.5, 0.55, "UC3: Speech-to-Sign\n& Avatar Animation", colors["orange"]),
        (3.0, 3.4, 2.5, 0.55, "UC4: Browse ISL Dictionary", colors["box"]),
        (7.6, 3.4, 2.5, 0.55, "UC5: View Translation\nHistory", colors["purple"]),
        (3.0, 2.2, 2.5, 0.55, "UC6: Learn ISL (XP\nGamification)", colors["green"]),
        (7.6, 2.2, 2.5, 0.55, "UC7: Manage\nPreferences", colors["orange"]),
        (5.3, 1.1, 2.5, 0.55, "UC8: Contact Support", colors["gray"]),
    ]
    for x, y, w, h, lbl, fill in ucs:
        usecase(ax, x, y, w, h, lbl, fill)

    # Actor → UC associations
    conns_left  = [(3.0,4.6),(3.0,3.4),(3.0,2.2),(5.3,5.7),(5.3,1.1)]
    conns_right = [(7.6,4.6),(7.6,3.4),(7.6,2.2),(5.3,5.7),(5.3,1.1)]
    for (x,y) in conns_left:
        ax.plot([0.8+0.12, x-1.25], [3.5, y], color="#546e7a", lw=1, alpha=0.7)
    for (x,y) in conns_right:
        ax.plot([10.2-0.12, x+1.25], [3.5, y], color="#546e7a", lw=1, alpha=0.7)

    # Gemini → UC3
    ax.annotate("", xy=(7.6, 2.2-0.28), xytext=(5.3, 0.1+0.35),
                arrowprops=dict(arrowstyle="-|>", color="#c62828", lw=1, linestyle="dashed"))
    ax.text(6.6, 1.3, "OSV gloss", fontsize=7, color="#c62828", ha="center")

    save(fig, "uc_diagram.png")

# ═══════════════════════════════════════════════════════════
# 2. CLASS DIAGRAM
# ═══════════════════════════════════════════════════════════
def make_class():
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(0, 13); ax.set_ylim(0, 8); ax.axis("off")
    ax.set_title("Figure 5.2: Class Diagram — Saṁvāk Data Models (models.py)", fontsize=11, fontweight="bold")

    def cls_box(ax, x, y, w, title, attrs, methods, fill=colors["box"]):
        row_h = 0.28
        n = len(attrs) + len(methods) + 1
        total_h = n * row_h + 0.4
        top = y + total_h/2

        # Title header
        hdr(ax, x, top - 0.2, w, 0.38, title, fill="#1a3a5c")
        cy = top - 0.52
        # attrs
        for a in attrs:
            ax.text(x - w/2 + 0.08, cy, a, fontsize=7.2, va="center", color="#37474f")
            cy -= row_h
        # divider
        ax.plot([x-w/2+0.05, x+w/2-0.05], [cy+row_h*0.5, cy+row_h*0.5], color="#90a4ae", lw=0.8)
        # methods
        for m in methods:
            ax.text(x - w/2 + 0.08, cy, m, fontsize=7.2, va="center", color="#1565c0")
            cy -= row_h
        # outline
        ax.add_patch(FancyBboxPatch((x-w/2, y-total_h/2), w, total_h,
                     boxstyle="round,pad=0.02", edgecolor="#546e7a", facecolor=fill, lw=1.2))
        return y - total_h/2, y + total_h/2

    cls_box(ax, 2.0, 6.0, 3.6, "User",
            ["- id: Integer (PK)", "- username: String(80)", "- email: String(120)",
             "- password_hash: String", "- xp_points: Integer", "- level: Integer"],
            ["+ set_password()", "+ check_password(): bool", "+ to_dict(): dict"])

    cls_box(ax, 6.5, 6.0, 3.8, "Translation",
            ["- id: Integer (PK)", "- user_id: Integer (FK)", "- input_text: Text",
             "- output_text: Text", "- source_type: String(20)", "- confidence: Float",
             "- timestamp: DateTime"],
            ["+ to_dict(): dict"])

    cls_box(ax, 11.0, 6.0, 3.6, "UserProgress",
            ["- id: Integer (PK)", "- user_id: Integer (FK)", "- word: String(100)",
             "- points: Integer"],
            ["+ to_dict(): dict"])

    cls_box(ax, 2.0, 2.2, 3.6, "UserPreference",
            ["- id: Integer (PK)", "- user_id: Integer (FK) 1:1", "- target_language: String",
             "- tts_enabled: Boolean", "- avatar_speed: Float"],
            ["+ to_dict(): dict"])

    cls_box(ax, 6.5, 2.2, 3.8, "ContactMessage",
            ["- id: Integer (PK)", "- name: String(100)", "- email: String(200)",
             "- message: Text", "- submitted_at: DateTime"],
            ["+ to_dict(): dict"])

    cls_box(ax, 11.0, 2.2, 3.6, "LSTMModel (utility)",
            ["- model_path: String", "- num_classes: Integer = 40",
             "- feature_size: Integer = 258", "- seq_length: Integer = 30",
             "- accuracy: Float = 0.946"],
            ["+ predict(): ndarray", "+ load_model(): void"])

    # Relationships
    rels = [
        (2.0, 4.68, 6.5, 4.68, "1    has    N"),
        (2.0, 4.68, 11.0, 4.68, "1         has         N"),
        (2.0, 4.68, 2.0, 3.5, "1 has 1"),
    ]
    for x1,y1,x2,y2,lbl in rels:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#37474f", lw=1.2))
        ax.text((x1+x2)/2, max(y1,y2)+0.12, lbl, fontsize=7, ha="center", color="#546e7a")

    save(fig, "class_diagram.png")

# ═══════════════════════════════════════════════════════════
# 3. SEQUENCE DIAGRAM
# ═══════════════════════════════════════════════════════════
def make_sequence():
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(0, 13); ax.set_ylim(0, 8); ax.axis("off")
    ax.set_title("Figure 5.3: Sequence Diagram — Sign-to-Speech Flow", fontsize=11, fontweight="bold")

    lifelines = [
        (1.0,  "User"),
        (3.0,  "Browser\n(JS)"),
        (5.0,  "MediaPipe\nHolistic"),
        (7.0,  "TF.js\nLSTM"),
        (9.0,  "Flask\nAPI"),
        (11.0, "SQLite\nDB"),
    ]
    top_y = 7.5
    bot_y = 0.3

    for x, lbl in lifelines:
        hdr(ax, x, top_y, 1.4, 0.55, lbl, fill="#1a3a5c", fs=8)
        ax.plot([x, x], [top_y - 0.28, bot_y], color="#90a4ae", lw=1, linestyle="--")

    msgs = [
        (1.0, 3.0, 7.0, "1: open webcam"),
        (3.0, 5.0, 6.5, "2: video frame"),
        (5.0, 3.0, 6.0, "3: 258D landmarks"),
        (3.0, 7.0, 5.5, "4: tensor(1,30,258)"),
        (7.0, 3.0, 5.0, "5: class_idx + confidence"),
        (3.0, 9.0, 4.5, "6: POST /sign/predict"),
        (9.0, 3.0, 4.0, "7: translate (deep-translator)"),
        (9.0, 11.0, 3.5, "8: INSERT Translation"),
        (11.0, 9.0, 3.0, "9: DB ack"),
        (9.0, 3.0, 2.5, "10: JSON {phrase, audio_url}"),
        (3.0, 1.0, 2.0, "11: display text + play TTS"),
    ]
    back = {5, 7, 9, 10}  # return arrows (right←left becomes left←right drawn differently)

    for i, (x1, x2, y, lbl) in enumerate(msgs):
        is_ret = i in back
        col = "#c62828" if is_ret else "#1565c0"
        style = "<|-" if is_ret else "-|>"
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle=style, color=col, lw=1.2))
        mx = (x1 + x2) / 2
        ax.text(mx, y + 0.08, lbl, ha="center", va="bottom", fontsize=7.5, color=col)

        # activation box on receiver
        recv = x2
        ax.add_patch(FancyBboxPatch((recv-0.07, y-0.25), 0.14, 0.5,
                     boxstyle="square,pad=0", facecolor="#bbdefb", edgecolor="#1565c0", lw=0.8))

    save(fig, "sequence_diagram.png")

# ═══════════════════════════════════════════════════════════
# 4. ACTIVITY DIAGRAM
# ═══════════════════════════════════════════════════════════
def make_activity():
    fig, ax = plt.subplots(figsize=(10, 13))
    ax.set_xlim(0, 10); ax.set_ylim(0, 13); ax.axis("off")
    ax.set_title("Figure 5.4: Activity Diagram — Saṁvāk System Flow", fontsize=11, fontweight="bold")

    def act(x, y, w, h, label, fill=colors["box"]):
        box(ax, x, y, w, h, label, fill=fill, fs=8)

    def diamond(ax, x, y, label):
        d = 0.32
        xs = [x, x+d, x, x-d, x]
        ys = [y+d, y, y-d, y, y+d]
        ax.fill(xs, ys, facecolor=colors["orange"], edgecolor="#bf360c", lw=1.2)
        ax.text(x, y, label, ha="center", va="center", fontsize=7.2, fontstyle="italic")

    def start(x, y):
        ax.add_patch(plt.Circle((x, y), 0.18, color="#1a3a5c"))

    def end(x, y):
        ax.add_patch(plt.Circle((x, y), 0.18, color="#1a3a5c"))
        ax.add_patch(plt.Circle((x, y), 0.11, color="white"))
        ax.add_patch(plt.Circle((x, y), 0.07, color="#1a3a5c"))

    def arrow(x1, y1, x2, y2, label=""):
        arr(ax, x1, y1, x2, y2, label)

    start(5, 12.5)
    arrow(5, 12.32, 5, 11.95)
    act(5, 11.7, 3.2, 0.42, "User Opens Saṁvāk in Browser")

    arrow(5, 11.49, 5, 11.1)
    diamond(ax, 5, 10.8, "Authenticated?")
    # Yes branch
    ax.annotate("", xy=(5, 10.2), xytext=(5, 10.48),
                arrowprops=dict(arrowstyle="-|>", color="#37474f", lw=1))
    ax.text(5.35, 10.33, "Yes", fontsize=7.5, color="green")
    act(5, 9.9, 3.2, 0.42, "Load Dashboard + History")

    # No branch
    arrow(5+0.32, 10.8, 8.5, 10.8, "No")
    act(8.5, 10.8, 2.4, 0.42, "Show Login /\nRegister Page")
    arrow(8.5, 10.59, 8.5, 10.2)
    act(8.5, 9.9, 2.4, 0.42, "Submit\nCredentials")
    diamond(ax, 8.5, 9.45, "Valid?")
    ax.annotate("", xy=(5.5, 9.45), xytext=(8.18, 9.45),
                arrowprops=dict(arrowstyle="-|>", color="green", lw=1))
    ax.text(6.7, 9.5, "Yes", fontsize=7.5, color="green")
    ax.annotate("", xy=(5, 9.9-0.21), xytext=(5.5, 9.45),
                arrowprops=dict(arrowstyle="-|>", color="green", lw=1))
    ax.text(8.82, 9.3, "No  ↓ error", fontsize=7, color="red")

    arrow(5, 9.69, 5, 9.3)
    act(5, 9.05, 3.2, 0.42, "Render Main Navigation")

    arrow(5, 8.84, 5, 8.45)
    diamond(ax, 5, 8.15, "Mode?")

    # Sign-to-Speech left
    ax.annotate("", xy=(2.0, 7.8), xytext=(4.68, 8.15),
                arrowprops=dict(arrowstyle="-|>", color="#37474f", lw=1))
    ax.text(3.2, 7.98, "Sign→Speech", fontsize=7)
    act(2.0, 7.55, 2.4, 0.42, "Request\nWebcam")
    arrow(2.0, 7.34, 2.0, 6.95)
    act(2.0, 6.7, 2.4, 0.42, "MediaPipe\n258D Extract")
    arrow(2.0, 6.49, 2.0, 6.1)
    act(2.0, 5.85, 2.4, 0.42, "Buffer 30 Frames\nTF.js LSTM Infer")
    arrow(2.0, 5.64, 2.0, 5.25)
    diamond(ax, 2.0, 4.95, "Conf>0.75?")
    ax.text(2.35, 4.6, "Yes↓", fontsize=7, color="green")
    ax.text(1.0, 4.95, "No→loop", fontsize=7, color="red")
    ax.annotate("", xy=(2.0, 4.3), xytext=(2.0, 4.63),
                arrowprops=dict(arrowstyle="-|>", color="green", lw=1))
    act(2.0, 4.05, 2.4, 0.42, "Translate +\ngTTS + Save DB")
    arrow(2.0, 3.84, 2.0, 3.45)
    act(2.0, 3.2, 2.4, 0.42, "Display Text\n+ Play Audio")

    # Speech-to-Sign right
    ax.annotate("", xy=(8.0, 7.8), xytext=(5.32, 8.15),
                arrowprops=dict(arrowstyle="-|>", color="#37474f", lw=1))
    ax.text(6.8, 7.98, "Speech→Sign", fontsize=7)
    act(8.0, 7.55, 2.4, 0.42, "Request\nMicrophone")
    arrow(8.0, 7.34, 8.0, 6.95)
    act(8.0, 6.7, 2.4, 0.42, "Record & Upload\nWebM Audio")
    arrow(8.0, 6.49, 8.0, 6.1)
    act(8.0, 5.85, 2.4, 0.42, "Google STT\nTranscription")
    arrow(8.0, 5.64, 8.0, 5.25)
    act(8.0, 5.0, 2.4, 0.42, "grammar_helper.py\n+ Gemini OSV Gloss")
    arrow(8.0, 4.79, 8.0, 4.4)
    act(8.0, 4.15, 2.4, 0.42, "Three.js Avatar\nSignAnimate")
    arrow(8.0, 3.94, 8.0, 3.55)
    act(8.0, 3.3, 2.4, 0.42, "Show Signed\nOutput")

    # Merge to end
    arrow(2.0, 2.99, 2.0, 2.6)
    arrow(8.0, 3.09, 8.0, 2.6)
    ax.plot([2.0, 5.0], [2.6, 2.6], color="#37474f", lw=1)
    ax.plot([8.0, 5.0], [2.6, 2.6], color="#37474f", lw=1)
    arrow(5.0, 2.6, 5.0, 2.2)
    diamond(ax, 5.0, 1.9, "Continue?")
    ax.text(5.35, 1.5, "No↓", fontsize=7, color="red")
    ax.annotate("", xy=(5.0, 1.3), xytext=(5.0, 1.58),
                arrowprops=dict(arrowstyle="-|>", color="red", lw=1))
    end(5.0, 1.1)
    ax.text(3.2, 1.9, "Yes→loop↑", fontsize=7, color="green")

    save(fig, "activity_diagram.png")

# ═══════════════════════════════════════════════════════════
# 5. ER DIAGRAM
# ═══════════════════════════════════════════════════════════
def make_er():
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13); ax.set_ylim(0, 7); ax.axis("off")
    ax.set_title("Figure 5.5: ER Diagram — Saṁvāk Database Schema", fontsize=11, fontweight="bold")

    def entity(ax, x, y, w, title, attrs):
        h = 0.3 * (len(attrs) + 1) + 0.35
        hdr(ax, x, y + h/2 - 0.22, w, 0.42, title)
        cy = y + h/2 - 0.55
        for a in attrs:
            pk = "🔑 " if "(PK)" in a else ("FK " if "(FK)" in a else "   ")
            ax.text(x - w/2 + 0.1, cy, pk + a.replace("(PK)","").replace("(FK)",""), fontsize=7.5, va="center")
            cy -= 0.3
        ax.add_patch(FancyBboxPatch((x-w/2, y-h/2+0.1), w, h,
                     boxstyle="square,pad=0.02", edgecolor="#546e7a", facecolor=colors["box"], lw=1.4))

    entity(ax, 2.2, 5.2, 3.5, "USERS",
           ["id INTEGER (PK)", "username VARCHAR(80)", "email VARCHAR(120)",
            "password_hash TEXT", "xp_points INTEGER", "level INTEGER"])

    entity(ax, 6.5, 5.5, 3.5, "TRANSLATIONS",
           ["id INTEGER (PK)", "user_id INTEGER (FK)", "input_text TEXT",
            "output_text TEXT", "source_type VARCHAR(20)", "confidence REAL",
            "timestamp DATETIME"])

    entity(ax, 10.8, 5.2, 3.5, "USER_PROGRESS",
           ["id INTEGER (PK)", "user_id INTEGER (FK)", "word VARCHAR(100)",
            "points INTEGER"])

    entity(ax, 2.2, 1.5, 3.5, "USER_PREFERENCES",
           ["id INTEGER (PK)", "user_id INTEGER (FK) 1:1", "target_language VARCHAR",
            "tts_enabled BOOLEAN", "avatar_speed REAL"])

    entity(ax, 10.8, 1.5, 3.5, "CONTACT_MESSAGES",
           ["id INTEGER (PK)", "name VARCHAR(100)", "email VARCHAR(200)",
            "message TEXT", "submitted_at DATETIME"])

    # Relationships
    def rel_line(ax, x1, y1, x2, y2, card1, card2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-", color="#37474f", lw=1.5))
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(x1+0.05, y1, card1, fontsize=8, fontweight="bold", color="#c62828")
        ax.text(x2-0.18, y2, card2, fontsize=8, fontweight="bold", color="#c62828")

    rel_line(ax, 3.95, 5.5, 4.75, 5.5, "1", "N")
    rel_line(ax, 8.25, 5.5, 9.05, 5.5, "1", "N")
    rel_line(ax, 2.2, 3.7, 2.2, 2.8, "1", "1")
    ax.text(5.35, 5.65, "has →", fontsize=7.5, ha="center", color="#1565c0", fontstyle="italic")
    ax.text(8.65, 5.65, "has →", fontsize=7.5, ha="center", color="#1565c0", fontstyle="italic")
    ax.text(2.55, 3.2, "has →", fontsize=7.5, ha="center", rotation=270, color="#1565c0", fontstyle="italic")

    save(fig, "er_diagram.png")

# ═══════════════════════════════════════════════════════════
# 6. COMPONENT DIAGRAM
# ═══════════════════════════════════════════════════════════
def make_component():
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(0, 13); ax.set_ylim(0, 9); ax.axis("off")
    ax.set_title("Figure 5.6: Component Diagram — Saṁvāk Layered Architecture", fontsize=11, fontweight="bold")

    def layer(ax, y, h, label, fill):
        r = FancyBboxPatch((0.2, y), 12.6, h, boxstyle="round,pad=0.05",
                           edgecolor="#37474f", facecolor=fill, lw=1.5, zorder=1)
        ax.add_patch(r)
        ax.text(0.5, y + h - 0.2, label, fontsize=8.5, fontweight="bold", va="top", color="#1a3a5c")

    layer(ax, 6.5, 2.2, "Layer 1: Frontend (Browser — HTML5 / JavaScript / CSS3)", "#e8f5e9")
    layer(ax, 4.5, 1.8, "Layer 2: REST API / WebSocket Interface (Flask + SocketIO)", "#fff3e0")
    layer(ax, 2.0, 2.3, "Layer 3: Backend Modules (Python Flask Blueprints)", "#e3f2fd")
    layer(ax, 0.1, 1.7, "Layer 4: Data & External Services", "#fce4ec")

    components = {
        # Layer 1
        "sign.js\n(1600+ lines\nTF.js LSTM)": (1.6, 7.7),
        "MediaPipe\nHolistic JS\n(258D/frame)": (4.0, 7.7),
        "speech.js\n(STT + Gloss\nUI)":        (6.4, 7.7),
        "Three.js\nAvatar r128\n(3D ISL)":      (8.8, 7.7),
        "HTML/CSS\nJinja2 Templates\n(UI)":     (11.2, 7.7),
        # Layer 2
        "POST /sign/*\n(predict)":     (2.0, 5.45),
        "POST /speech/*\n(STT+gloss)": (5.0, 5.45),
        "SocketIO Events\n(predict_result)": (8.0, 5.45),
        "GET /auth/* /dict/*\n/learn/*": (11.0, 5.45),
        # Layer 3
        "app.py\n(Factory +\nBlueprints)": (1.6, 3.2),
        "sign.py\n(4146 lines\nLSTM infer)": (4.0, 3.2),
        "speech.py\n(STT+Gemini\n+gTTS)":   (6.4, 3.2),
        "grammar\n_helper.py\n(ISL OSV)":   (8.8, 3.2),
        "models.py\n(SQLAlchemy\n5 tables)": (11.2, 3.2),
        # Layer 4
        "SQLite DB\n(database.db)": (2.0, 0.9),
        "Gemini API\n(gemini-1.5-flash)": (5.0, 0.9),
        "iSign Index\n(132MB .npz)": (8.0, 0.9),
        "gTTS / Google\nSTT API":   (11.0, 0.9),
    }
    fills = {
        0: "#c8e6c9", 1: "#c8e6c9", 2: "#c8e6c9", 3: "#c8e6c9", 4: "#c8e6c9",
        5: "#ffe0b2", 6: "#ffe0b2", 7: "#ffe0b2", 8: "#ffe0b2",
        9: "#bbdefb", 10: "#bbdefb", 11: "#bbdefb", 12: "#bbdefb", 13: "#bbdefb",
        14: "#ffcdd2", 15: "#ffcdd2", 16: "#ffcdd2", 17: "#ffcdd2",
    }
    for i, (lbl, (x, y)) in enumerate(components.items()):
        f = fills.get(i, colors["box"])
        box(ax, x, y, 2.1, 0.9, lbl, fill=f, fs=7.5, radius=0.03)

    # Arrows between layers
    for x in [2.0, 5.0, 8.0, 11.0]:
        ax.annotate("", xy=(x, 6.28), xytext=(x, 6.5),
                    arrowprops=dict(arrowstyle="<->", color="#546e7a", lw=1))
        ax.annotate("", xy=(x, 4.28), xytext=(x, 4.5),
                    arrowprops=dict(arrowstyle="<->", color="#546e7a", lw=1))
        ax.annotate("", xy=(x, 1.68), xytext=(x, 2.0),
                    arrowprops=dict(arrowstyle="<->", color="#546e7a", lw=1))

    save(fig, "component_diagram.png")

# ═══════════════════════════════════════════════════════════
# 7. DEPLOYMENT DIAGRAM
# ═══════════════════════════════════════════════════════════
def make_deployment():
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13); ax.set_ylim(0, 7); ax.axis("off")
    ax.set_title("Figure 5.7: Deployment Diagram — Saṁvāk on Render.com", fontsize=11, fontweight="bold")

    def node(ax, x, y, w, h, title, items, fill, stereot="Node"):
        r = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                           edgecolor="#37474f", facecolor=fill, lw=1.8, zorder=2)
        ax.add_patch(r)
        ax.text(x+0.15, y+h-0.12, f"«{stereot}»", fontsize=7, color="#546e7a", fontstyle="italic")
        ax.text(x+w/2, y+h-0.38, title, ha="center", fontsize=9, fontweight="bold", color="#1a3a5c")
        ax.plot([x+0.1, x+w-0.1], [y+h-0.52, y+h-0.52], color="#90a4ae", lw=0.8)
        cy = y + h - 0.75
        for item in items:
            ax.text(x+0.2, cy, "▸ " + item, fontsize=7.5, va="center", color="#37474f")
            cy -= 0.28

    node(ax, 0.3, 1.0, 3.8, 5.5,
         "User Device (Browser)",
         ["sign.js  (~1600 lines)", "TF.js LSTM (tfjs_lstm/)", "MediaPipe Holistic JS",
          "Three.js r128 Avatar", "Web Speech API (TTS)", "HTML5 Webcam Video",
          "CSS3 + Vanilla JS UI"],
         "#e8f5e9")

    node(ax, 4.6, 1.0, 4.0, 5.5,
         "Render.com Cloud (Linux)",
         ["app.py  (Flask factory)", "sign.py  (4146 lines)", "speech.py + grammar_helper",
          "isign_retrieval.py", "models.py  (SQLAlchemy)", "database.db  (SQLite)",
          "Gunicorn + Eventlet workers", "isign_retrieval_index.npz (132MB)"],
         "#e3f2fd")

    node(ax, 9.1, 1.0, 3.6, 5.5,
         "Google Cloud Services",
         ["Gemini API", "  (gemini-1.5-flash)", "Google Speech-to-Text", "  (SpeechRecognition)",
          "gTTS Audio Synthesis", "  (REST endpoint)"],
         "#fce4ec", stereot="Service")

    # Arrows
    ax.annotate("", xy=(4.6, 3.8), xytext=(4.1, 3.8),
                arrowprops=dict(arrowstyle="<->", color="#1565c0", lw=2))
    ax.text(4.35, 4.05, "HTTPS/WSS\n(port 443)", ha="center", fontsize=8, color="#1565c0")

    ax.annotate("", xy=(9.1, 3.8), xytext=(8.6, 3.8),
                arrowprops=dict(arrowstyle="<->", color="#c62828", lw=2))
    ax.text(8.85, 4.05, "REST/JSON\n(HTTPS TLS)", ha="center", fontsize=8, color="#c62828")

    save(fig, "deployment_diagram.png")

# ═══════════════════════════════════════════════════════════
# 8. COLLABORATIVE DIAGRAM
# ═══════════════════════════════════════════════════════════
def make_collab():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 12); ax.set_ylim(0, 7); ax.axis("off")
    ax.set_title("Figure 5.8: Collaborative Diagram — Sign-to-Speech Cycle", fontsize=11, fontweight="bold")

    objs = {
        ":User":             (1.2, 5.8),
        ":Browser (JS)":     (5.5, 5.8),
        ":MediaPipe\nHolistic": (9.5, 5.8),
        ":TF.js LSTM":       (9.5, 3.5),
        ":Flask API":        (5.5, 3.5),
        ":iSign\nRetrieval": (1.2, 3.5),
        ":SQLite DB":        (3.2, 1.5),
    }
    for lbl, (x, y) in objs.items():
        box(ax, x, y, 2.2, 0.65, lbl, fill=colors["box"], fs=8, bold=True)

    msgs_def = [
        (":User", ":Browser (JS)", "1: perform ISL gesture", "#1565c0"),
        (":Browser (JS)", ":MediaPipe\nHolistic", "2: video frame", "#1565c0"),
        (":MediaPipe\nHolistic", ":Browser (JS)", "3: 258D landmarks", "#c62828"),
        (":Browser (JS)", ":TF.js LSTM", "4: tensor(1,30,258)", "#1565c0"),
        (":TF.js LSTM", ":Browser (JS)", "5: class_idx + confidence", "#c62828"),
        (":Browser (JS)", ":Flask API", "6: POST /sign/predict", "#1565c0"),
        (":Flask API", ":iSign\nRetrieval", "7: cosine query", "#1565c0"),
        (":iSign\nRetrieval", ":Flask API", "8: top-k clip URLs", "#c62828"),
        (":Flask API", ":SQLite DB", "9: INSERT Translation", "#1565c0"),
        (":SQLite DB", ":Flask API", "10: DB ack", "#c62828"),
        (":Flask API", ":Browser (JS)", "11: JSON response", "#c62828"),
        (":Browser (JS)", ":User", "12: display + TTS audio", "#c62828"),
    ]
    for src, dst, lbl, c in msgs_def:
        x1, y1 = objs[src]
        x2, y2 = objs[dst]
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=c, lw=1.2,
                                   connectionstyle="arc3,rad=0.15"))
        mx, my = (x1+x2)/2, (y1+y2)/2+0.15
        ax.text(mx, my, lbl, ha="center", va="center", fontsize=7, color=c,
                bbox=dict(boxstyle="round,pad=0.1", facecolor="white", edgecolor="none", alpha=0.8))

    save(fig, "collab_diagram.png")

# ═══════════════════════════════════════════════════════════
# 9. DFD LEVEL 0
# ═══════════════════════════════════════════════════════════
def make_dfd0():
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_xlim(0, 10); ax.set_ylim(0, 7); ax.axis("off")
    ax.set_title("Figure 5.9: DFD Level 0 — Context Diagram", fontsize=11, fontweight="bold")

    def ext(ax, x, y, w, h, lbl):
        ax.add_patch(FancyBboxPatch((x-w/2, y-h/2), w, h,
                     boxstyle="square,pad=0.05", edgecolor="#37474f",
                     facecolor="#fff3e0", lw=1.5))
        ax.text(x, y, lbl, ha="center", va="center", fontsize=8.5, fontweight="bold")

    def proc(ax, x, y, r, lbl):
        c = plt.Circle((x, y), r, facecolor="#e3f2fd", edgecolor="#1565c0", lw=2)
        ax.add_patch(c)
        ax.text(x, y, lbl, ha="center", va="center", fontsize=8.5,
                fontweight="bold", color="#1a3a5c", multialignment="center")

    ext(ax, 1.2, 5.5, 2.0, 0.7, "User\n(Deaf/Hearing)")
    ext(ax, 1.2, 1.5, 2.0, 0.7, "Gemini API\n(Google Cloud)")
    ext(ax, 8.8, 3.5, 2.0, 0.7, "iSign Dataset\n(14,674 clips)")
    proc(ax, 5.0, 3.5, 1.8, "0\nSaṁvāk\nSystem")

    flows = [
        (1.2, 5.15, 3.22, 4.1, "webcam frames / voice audio / text input"),
        (3.22, 3.0, 1.2, 1.85, "ISL gloss query"),
        (1.2, 2.15, 3.22, 3.0, "gloss tokens (OSV JSON)"),
        (3.22, 4.0, 1.2, 5.2, "recognized text / TTS audio / avatar sign"),
        (6.78, 3.5, 8.8, 3.5, "embedding query vector"),
        (8.8, 3.2, 6.78, 3.2, "nearest clip URLs + embeddings"),
    ]
    for x1,y1,x2,y2,lbl in flows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#37474f", lw=1.3))
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my+0.12, lbl, ha="center", fontsize=7, color="#37474f",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.8))

    save(fig, "dfd_level0.png")

# ═══════════════════════════════════════════════════════════
# 10. DFD LEVEL 1
# ═══════════════════════════════════════════════════════════
def make_dfd1():
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(0, 13); ax.set_ylim(0, 9); ax.axis("off")
    ax.set_title("Figure 5.10: DFD Level 1 — Sub-Processes", fontsize=11, fontweight="bold")

    def ext(ax, x, y, w, h, lbl):
        ax.add_patch(FancyBboxPatch((x-w/2, y-h/2), w, h,
                     boxstyle="square,pad=0.05", edgecolor="#37474f", facecolor="#fff3e0", lw=1.5))
        ax.text(x, y, lbl, ha="center", va="center", fontsize=8, fontweight="bold")

    def proc(ax, x, y, r, lbl):
        c = plt.Circle((x, y), r, facecolor="#e3f2fd", edgecolor="#1565c0", lw=1.8)
        ax.add_patch(c)
        ax.text(x, y, lbl, ha="center", va="center", fontsize=7.8,
                fontweight="bold", color="#1a3a5c", multialignment="center")

    def store(ax, x, y, w, lbl):
        h = 0.42
        ax.plot([x-w/2, x-w/2, x+w/2, x+w/2], [y+h/2, y-h/2, y-h/2, y+h/2],
                color="#546e7a", lw=1.3)
        ax.plot([x-w/2, x+w/2], [y+h/2, y+h/2], color="#546e7a", lw=1.3)
        ax.fill_betweenx([y-h/2, y+h/2], x-w/2, x+w/2, color="#f3f4f6", alpha=0.5)
        ax.text(x, y, lbl, ha="center", va="center", fontsize=7.5)

    # External entities
    ext(ax, 1.0, 7.5, 1.8, 0.6,  "User")
    ext(ax, 1.0, 1.5, 1.8, 0.6,  "User")
    ext(ax, 12.0, 5.5, 1.8, 0.6, "Gemini\nAPI")

    # Processes
    proc(ax, 3.5, 7.5, 0.95, "1.0\nPose\nExtract")
    proc(ax, 6.0, 7.5, 0.95, "2.0\nLSTM\nClassify")
    proc(ax, 8.5, 7.5, 0.95, "3.0\nTranslate\n(8 langs)")
    proc(ax, 11.0, 7.5, 0.95, "4.0\ngTTS\nSynth")

    proc(ax, 3.5, 3.5, 0.95, "5.0\nSTT\nTranscribe")
    proc(ax, 6.0, 3.5, 0.95, "6.0\nISL Gloss\nConvert")
    proc(ax, 8.5, 3.5, 0.95, "7.0\nAvatar\nAnimate")

    # Data stores
    store(ax, 6.0, 5.5, 2.2, "D1: SQLite DB (translations, users, progress)")
    store(ax, 9.5, 2.0, 2.2, "D2: iSign Index (132 MB cosine embeddings)")

    # Flows — Sign path
    ff = [
        (1.9, 7.5, 2.55, 7.5, "webcam frames"),
        (4.45, 7.5, 5.05, 7.5, "258D/frame"),
        (6.95, 7.5, 7.55, 7.5, "class+confidence"),
        (9.45, 7.5, 10.05, 7.5, "translated text"),
        (11.95, 7.5, 11.95, 7.5, ""),
        (6.0, 6.95, 6.0, 5.72, "save Translation"),
        (6.0, 5.28, 6.0, 4.45, ""),
    ]
    pairs = [
        (1.9, 7.5, 2.55, 7.5, "webcam frames"),
        (4.45, 7.5, 5.05, 7.5, "258D/frame"),
        (6.95, 7.5, 7.55, 7.5, "class+conf"),
        (9.45, 7.5, 10.05, 7.5, "translated text"),
        (11.95, 7.5, 11.95, 8.3, ""),
        (6.0, 6.95, 6.0, 5.72, "save Translation"),
        (1.9, 3.5, 2.55, 3.5, "voice audio"),
        (4.45, 3.5, 5.05, 3.5, "transcription"),
        (6.95, 3.5, 7.55, 3.5, "gloss tokens"),
        (6.0, 4.55, 6.0, 4.45, ""),
        (6.0, 5.28, 8.5, 4.45, "gloss tokens"),
        (9.5, 3.5, 9.5, 2.21, "embedding query"),
        (9.5, 1.79, 9.5, 3.05, "clip URLs"),
        (6.0, 3.5, 12.0, 3.5, "OSV query"),
        (12.0, 5.28, 12.0, 4.45, "gloss tokens"),
    ]
    for x1, y1, x2, y2, lbl in pairs:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#37474f", lw=1.1))
        if lbl:
            ax.text((x1+x2)/2, (y1+y2)/2+0.12, lbl, ha="center", fontsize=7, color="#37474f",
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.7))

    save(fig, "dfd_level1.png")

# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating diagrams →", OUT)
    make_use_case()
    make_class()
    make_sequence()
    make_activity()
    make_er()
    make_component()
    make_deployment()
    make_collab()
    make_dfd0()
    make_dfd1()
    print("\nAll 10 diagrams generated successfully.")
