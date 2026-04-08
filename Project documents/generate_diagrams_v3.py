"""
Generate improved diagrams v3 for Samvak project.
- Bigger, bolder text for readability
- Workflow diagram for section 3.5
- Better color contrast
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Polygon
import os

OUT = r"E:\sam\Project documents\diagrams"
os.makedirs(OUT, exist_ok=True)

# Colors with better contrast
C = {
    'blue': '#1565C0', 'blue_bg': '#E3F2FD',
    'green': '#2E7D32', 'green_bg': '#E8F5E9',
    'orange': '#E65100', 'orange_bg': '#FFF3E0',
    'purple': '#6A1B9A', 'purple_bg': '#F3E5F5',
    'red': '#C62828', 'red_bg': '#FFEBEE',
    'teal': '#00695C', 'teal_bg': '#E0F2F1',
    'gray': '#37474F', 'gray_bg': '#ECEFF1',
    'amber': '#F57F17', 'amber_bg': '#FFFDE7',
}

def save(fig, name):
    p = os.path.join(OUT, f"{name}.png")
    fig.savefig(p, dpi=200, bbox_inches='tight', facecolor='white', pad_inches=0.3)
    plt.close(fig)
    print(f"  OK: {name}.png")


# ══════════════════════════════════════════════════
# 0. WORKFLOW DIAGRAM (for Section 3.5)
# ══════════════════════════════════════════════════
def workflow():
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14); ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('System Workflow — Saṁvāk Sign Language Translator',
                 fontsize=16, fontweight='bold', pad=20, color='#1a1a1a')

    def box(x, y, text, color, edge, w=3.2, h=0.9):
        r = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=0.15",
                            ec=edge, fc=color, lw=2.5)
        ax.add_patch(r)
        ax.text(x, y, text, ha='center', va='center', fontsize=10, fontweight='bold', color='#1a1a1a')

    def arrow(x1, y1, x2, y2, label='', color='#555'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=2.5))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx+0.15, my, label, fontsize=8, color=color, fontweight='bold',
                    bbox=dict(fc='white', ec='none', pad=1))

    def diamond(x, y, text, color=C['amber_bg'], edge=C['amber']):
        pts = [[x, y+0.55], [x+1.5, y], [x, y-0.55], [x-1.5, y]]
        d = Polygon(pts, closed=True, ec=edge, fc=color, lw=2)
        ax.add_patch(d)
        ax.text(x, y, text, ha='center', va='center', fontsize=9, fontweight='bold')

    # Start
    ax.plot(7, 9.5, 'o', ms=22, color='#333', zorder=5)
    ax.text(7, 9.5, '▶', ha='center', va='center', fontsize=10, color='white', fontweight='bold')
    arrow(7, 9.3, 7, 8.9)

    # User opens app
    box(7, 8.5, 'User Opens Web App\n(Browser)', C['blue_bg'], C['blue'])
    arrow(7, 8.05, 7, 7.55)

    # Login
    box(7, 7.1, 'Login / Register\n(Flask + SQLite)', C['gray_bg'], C['gray'])
    arrow(7, 6.65, 7, 6.15)

    # Choose mode
    diamond(7, 5.7, 'Select\nMode?')

    # Sign-to-Text branch (left)
    arrow(5.5, 5.7, 3.5, 5.7, '', C['blue'])
    ax.text(4.5, 6.0, 'Sign-to-Text', fontsize=9, color=C['blue'], fontweight='bold')
    box(3.5, 5.0, 'Capture Webcam\nFrames (30 FPS)', C['blue_bg'], C['blue'], w=3.0)
    arrow(3.5, 4.55, 3.5, 4.05)
    box(3.5, 3.6, 'MediaPipe Holistic\n258D Landmarks', C['green_bg'], C['green'], w=3.0)
    arrow(3.5, 3.15, 3.5, 2.65)
    box(3.5, 2.2, 'LSTM-TCN Model\nClassification', C['purple_bg'], C['purple'], w=3.0)
    arrow(3.5, 1.75, 3.5, 1.25)
    box(3.5, 0.8, 'Display Text +\ngTTS Speech Output', C['teal_bg'], C['teal'], w=3.0)

    # Speech-to-Sign branch (right)
    arrow(8.5, 5.7, 10.5, 5.7, '', C['orange'])
    ax.text(9.0, 6.0, 'Speech-to-Sign', fontsize=9, color=C['orange'], fontweight='bold')
    box(10.5, 5.0, 'Record Voice /\nType Text', C['orange_bg'], C['orange'], w=3.0)
    arrow(10.5, 4.55, 10.5, 4.05)
    box(10.5, 3.6, 'Google STT +\nTranslation', C['green_bg'], C['green'], w=3.0)
    arrow(10.5, 3.15, 10.5, 2.65)
    box(10.5, 2.2, 'ISL Grammar Engine\n(OSV Reordering)', C['purple_bg'], C['purple'], w=3.0)
    arrow(10.5, 1.75, 10.5, 1.25)
    box(10.5, 0.8, '3D Avatar Animates\nISL Gestures', C['teal_bg'], C['teal'], w=3.0)

    # Dictionary/Learn branch (center)
    arrow(7, 5.15, 7, 4.55, '', C['gray'])
    ax.text(7.3, 4.85, 'Learn / Dict', fontsize=9, color=C['gray'], fontweight='bold')
    box(7, 4.1, 'Browse Dictionary\n& Learn Module', C['gray_bg'], C['gray'], w=3.0)

    save(fig, 'workflow_diagram')


# ══════════════════════════════════════════════════
# 1. USE CASE DIAGRAM (bigger text)
# ══════════════════════════════════════════════════
def use_case():
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_xlim(-1.5, 16); ax.set_ylim(-0.5, 12)
    ax.set_aspect('equal'); ax.axis('off')
    ax.set_title('Use Case Diagram — Saṁvāk Sign Language Translator',
                 fontsize=17, fontweight='bold', pad=20, color='#1a1a1a')

    # System boundary
    r = FancyBboxPatch((3.5, -0.2), 12, 11.5, boxstyle="round,pad=0.5",
                        edgecolor=C['blue'], facecolor='#FAFBFF', lw=3)
    ax.add_patch(r)
    ax.text(9.5, 11.5, '« System »  Saṁvāk', ha='center', fontsize=14,
            fontweight='bold', color=C['blue'], style='italic')

    # Stick figure
    def draw_actor(x, y, label):
        ax.plot(x, y+0.5, 'o', ms=16, color=C['blue'], mec=C['blue'], mew=2.5, zorder=5)
        ax.plot([x, x], [y+0.2, y-0.4], color=C['blue'], lw=2.5, zorder=5)
        ax.plot([x-0.4, x+0.4], [y+0.05, y+0.05], color=C['blue'], lw=2.5, zorder=5)
        ax.plot([x, x-0.3], [y-0.4, y-0.8], color=C['blue'], lw=2.5, zorder=5)
        ax.plot([x, x+0.3], [y-0.4, y-0.8], color=C['blue'], lw=2.5, zorder=5)
        ax.text(x, y-1.1, label, ha='center', fontsize=12, fontweight='bold')

    draw_actor(1.5, 5.5, 'User')

    # Main use cases (bigger ellipses, bigger text)
    main_uc = [
        (7, 10.0, 'Register / Login', C['green_bg'], C['green']),
        (7, 8.3, 'Sign-to-Text\nTranslation', C['blue_bg'], C['blue']),
        (7, 6.6, 'Speech-to-Sign\nTranslation', C['orange_bg'], C['orange']),
        (7, 4.9, 'Browse ISL\nDictionary', C['purple_bg'], C['purple']),
        (7, 3.2, 'Learn ISL\nSigns', C['teal_bg'], C['teal']),
        (7, 1.5, 'View Dashboard\n& History', C['gray_bg'], C['gray']),
    ]

    for x, y, lbl, bg, ec in main_uc:
        el = mpatches.Ellipse((x, y), 4.0, 1.2, ec=ec, fc=bg, lw=2.5)
        ax.add_patch(el)
        ax.text(x, y, lbl, ha='center', va='center', fontsize=11, fontweight='bold', color='#1a1a1a')
        ax.plot([2.2, x-2.0], [5.5, y], '-', color='#999', lw=1.2, zorder=1)

    # Include sub-cases (right side)
    sub = [
        (12.5, 10.0, 'Capture Gesture\n(Webcam)', C['blue']),
        (12.5, 8.8, 'Extract Landmarks\n(MediaPipe)', C['blue']),
        (12.5, 7.6, 'Classify Sign\n(LSTM-TCN)', C['blue']),
        (12.5, 6.0, 'Transcribe Speech\n(Google STT)', C['orange']),
        (12.5, 4.8, 'ISL Grammar\nConversion', C['orange']),
        (12.5, 3.6, 'Animate 3D Avatar\n(Three.js)', C['orange']),
    ]
    for x, y, lbl, ec in sub:
        el = mpatches.Ellipse((x, y), 3.2, 1.0, ec=ec, fc='white', lw=1.8, ls='--')
        ax.add_patch(el)
        ax.text(x, y, lbl, ha='center', va='center', fontsize=9, fontweight='bold', color='#444')

    # Include arrows from main to sub
    for i in range(3):
        ax.annotate('', xy=(12.5-1.6, sub[i][1]), xytext=(7+2.0, 8.3),
                    arrowprops=dict(arrowstyle='->', color='#bbb', lw=1, ls='dashed'))
    for i in range(3, 6):
        ax.annotate('', xy=(12.5-1.6, sub[i][1]), xytext=(7+2.0, 6.6),
                    arrowprops=dict(arrowstyle='->', color='#dbb', lw=1, ls='dashed'))

    ax.text(10.2, 9.0, '<<include>>', fontsize=9, style='italic', color=C['blue'])
    ax.text(10.2, 5.5, '<<include>>', fontsize=9, style='italic', color=C['orange'])

    save(fig, 'use_case_diagram')


# ══════════════════════════════════════════════════
# 2. CLASS DIAGRAM (bigger text, clearer)
# ══════════════════════════════════════════════════
def class_diagram():
    fig, ax = plt.subplots(figsize=(17, 12))
    ax.set_xlim(0, 17); ax.set_ylim(0, 12)
    ax.axis('off')
    ax.set_title('Class Diagram — Saṁvāk Application',
                 fontsize=17, fontweight='bold', pad=20, color='#1a1a1a')

    def draw_class(x, y, w, name, attrs, methods, hdr_color, border_color):
        lh = 0.30
        attr_h = len(attrs) * lh + 0.2
        meth_h = len(methods) * lh + 0.2
        h = 0.65 + attr_h + meth_h
        # Shadow
        ax.add_patch(FancyBboxPatch((x+0.06, y-0.06), w, h, boxstyle="round,pad=0.08",
                     ec='none', fc='#ddd', lw=0))
        # Box
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                               ec=border_color, fc='white', lw=2.5)
        ax.add_patch(rect)
        # Header
        hdr = FancyBboxPatch((x+0.03, y+h-0.62), w-0.06, 0.58, boxstyle="round,pad=0.06",
                              ec='none', fc=hdr_color, lw=0)
        ax.add_patch(hdr)
        ax.text(x+w/2, y+h-0.33, name, ha='center', va='center',
                fontsize=12, fontweight='bold', color='white')
        # Separator
        sep1 = y + h - 0.65 - attr_h
        ax.plot([x+0.05, x+w-0.05], [y+h-0.65, y+h-0.65], color=border_color, lw=1)
        ax.plot([x+0.05, x+w-0.05], [sep1, sep1], color=border_color, lw=1)
        # Attributes
        for i, a in enumerate(attrs):
            ax.text(x+0.2, y+h-0.85-i*lh, a, fontsize=9, family='monospace', color='#333')
        # Methods
        for i, m in enumerate(methods):
            ax.text(x+0.2, sep1-0.22-i*lh, m, fontsize=9, family='monospace', color='#1565C0')
        return y + h

    # User
    draw_class(0.3, 6.0, 4.0, 'User',
               ['+ id : Integer [PK]', '+ username : String [UK]',
                '+ email : String [UK]', '+ password_hash : String'],
               ['+ check_password(pwd)', '+ get_id() : String'],
               C['blue'], C['blue'])

    # Translation
    draw_class(5.5, 7.8, 4.5, 'Translation',
               ['+ id : Integer [PK]', '+ user_id : Integer [FK]',
                '+ source_type : String', '+ input_text : Text',
                '+ output_text : Text', '+ timestamp : DateTime'],
               ['+ to_dict() : Dict'],
               C['green'], C['green'])

    # UserPreference
    draw_class(5.5, 4.2, 4.5, 'UserPreference',
               ['+ id : Integer [PK]', '+ user_id : Integer [FK]',
                '+ sign_input_lang : String', '+ sign_output_lang : String',
                '+ speech_input_lang : String'],
               ['+ to_dict() : Dict', '+ default_payload()'],
               C['orange'], C['orange'])

    # UserProgress
    draw_class(5.5, 0.8, 4.5, 'UserProgress',
               ['+ id : Integer [PK]', '+ user_id : Integer [FK]',
                '+ word : String', '+ points : Integer'],
               ['+ add_xp(amount)'],
               C['red'], C['red'])

    # GeometryClassifier
    draw_class(11.5, 7.5, 5.0, 'GeometryClassifier',
               ['- MIN_CONFIDENCE : 0.82',
                '- BASIC_SIGNS : Tuple',
                '+ last_prediction : String'],
               ['+ predict(landmarks)', '+ predict_with_metadata(lm)',
                '- _analyze_frame(lm)', '- _hand_metrics(hand)'],
               C['purple'], C['purple'])

    # GrammarHelper
    draw_class(11.5, 3.5, 5.0, 'GrammarHelper',
               ['- _DROP_WORDS : Set', '- _WH_WORDS : Set',
                '- _PHRASE_MAP : Dict'],
               ['+ english_to_isl_glosses()', '+ gloss_to_english()',
                '- _apply_isl_grammar()'],
               C['teal'], C['teal'])

    # ContactMessage
    draw_class(0.3, 1.0, 4.0, 'ContactMessage',
               ['+ id : Integer [PK]', '+ name : String',
                '+ email : String', '+ message : Text'],
               [],
               C['gray'], C['gray'])

    # Relationships
    def rel(x1, y1, x2, y2, label, c1, c2):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='-|>', color='#333', lw=2))
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my+0.22, label, ha='center', fontsize=9, style='italic',
                color='#555', bbox=dict(fc='white', ec='none', pad=2))
        ax.text(x1+0.15, y1-0.1, c1, fontsize=10, fontweight='bold', color=C['blue'])
        ax.text(x2+0.15, y2+0.15, c2, fontsize=10, fontweight='bold', color=C['blue'])

    rel(4.3, 9.5, 5.5, 10.5, 'has', '1', '*')
    rel(4.3, 7.5, 5.5, 6.5, 'configures', '1', '1')
    rel(4.3, 6.5, 5.5, 3.0, 'tracks', '1', '*')

    # Dependency arrows
    ax.annotate('', xy=(11.5, 9.0), xytext=(10.0, 9.5),
                arrowprops=dict(arrowstyle='->', color='#999', lw=1.5, ls='dashed'))
    ax.text(10.3, 9.6, 'uses', fontsize=9, color='#999', style='italic')

    ax.annotate('', xy=(11.5, 5.5), xytext=(10.0, 6.0),
                arrowprops=dict(arrowstyle='->', color='#999', lw=1.5, ls='dashed'))
    ax.text(10.3, 6.0, 'uses', fontsize=9, color='#999', style='italic')

    save(fig, 'class_diagram')


# ══════════════════════════════════════════════════
# 3. SEQUENCE DIAGRAM - Sign-to-Text (clearer)
# ══════════════════════════════════════════════════
def sequence_sign():
    fig, ax = plt.subplots(figsize=(16, 11))
    ax.set_xlim(0, 16); ax.set_ylim(0, 11)
    ax.axis('off')
    ax.set_title('Sequence Diagram — Sign-to-Text Translation',
                 fontsize=16, fontweight='bold', pad=18, color='#1a1a1a')

    lifelines = [
        (2, 'User', C['blue']),
        (5, 'Browser\n(sign.js)', C['green']),
        (8, 'MediaPipe', C['orange']),
        (10.5, 'TF.js\nLSTM-TCN', C['purple']),
        (13, 'Flask\nServer', C['teal']),
        (15, 'SQLite', C['red']),
    ]

    for x, label, color in lifelines:
        r = FancyBboxPatch((x-0.8, 9.6), 1.6, 1.0, boxstyle="round,pad=0.1",
                            ec=color, fc=color, lw=2.5)
        ax.add_patch(r)
        ax.text(x, 10.1, label, ha='center', va='center', fontsize=10,
                fontweight='bold', color='white')
        ax.plot([x, x], [0.3, 9.6], '--', color='#ccc', lw=1.2, zorder=0)

    def msg(x1, x2, y, text, color='#333', ret=False):
        style = '<-' if ret else '->'
        ax.annotate('', xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle=style, color=color, lw=2))
        mx = (x1+x2)/2
        ax.text(mx, y+0.18, text, ha='center', fontsize=9, color=color, fontweight='bold',
                bbox=dict(fc='white', ec='none', pad=2))

    def act(x, y1, y2, color):
        ax.add_patch(FancyBboxPatch((x-0.15, y2), 0.3, y1-y2,
                     boxstyle="square,pad=0", ec=color, fc=color, alpha=0.2, lw=1.5))

    act(2, 9.0, 0.5, C['blue'])
    act(5, 8.8, 0.8, C['green'])

    msg(2, 5, 9.0, '1: startCamera()')

    # Loop
    ax.add_patch(FancyBboxPatch((3.3, 6.5), 6.5, 2.8, boxstyle="round,pad=0.12",
                 ec='#888', fc='#fafafa', lw=1.8, ls='--'))
    ax.text(3.5, 9.1, 'loop', fontsize=10, fontweight='bold', color='#666',
            bbox=dict(fc='#eee', ec='#999', pad=3))
    ax.text(5.3, 9.1, '[every frame @ 30 FPS]', fontsize=9, color='#888')

    msg(5, 8, 8.3, '2: processFrame(rgbImage)')
    act(8, 8.3, 7.2, C['orange'])
    msg(8, 5, 7.2, '3: return 258D landmarks', C['orange'], ret=True)
    msg(5, 5, 7.5, '4: appendToBuffer()', C['green'])

    msg(5, 10.5, 5.8, '5: predict(30×258 tensor)')
    act(10.5, 5.8, 4.8, C['purple'])
    msg(10.5, 5, 4.8, '6: {phrase, confidence}', C['purple'], ret=True)

    msg(5, 13, 4.0, '7: POST /api/sign/translate')
    act(13, 4.0, 2.0, C['teal'])
    msg(13, 15, 3.4, '8: INSERT translation')
    act(15, 3.4, 2.8, C['red'])
    msg(15, 13, 2.8, '9: OK', C['red'], ret=True)
    msg(13, 5, 2.0, '10: {translatedText, audioUrl}', C['teal'], ret=True)
    msg(5, 2, 1.2, '11: displayText + playAudio', C['green'], ret=True)

    save(fig, 'sequence_sign')


# ══════════════════════════════════════════════════
# 4. SEQUENCE DIAGRAM - Speech-to-Sign
# ══════════════════════════════════════════════════
def sequence_speech():
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 16); ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('Sequence Diagram — Speech-to-Sign Translation',
                 fontsize=16, fontweight='bold', pad=18, color='#1a1a1a')

    lifelines = [
        (2, 'User', C['blue']),
        (5, 'Browser\n(speech.js)', C['green']),
        (8, 'Flask\nServer', C['teal']),
        (10.5, 'Google\nSTT', C['orange']),
        (13, 'Grammar\nEngine', C['purple']),
        (15, 'Three.js\nAvatar', C['red']),
    ]

    for x, label, color in lifelines:
        r = FancyBboxPatch((x-0.8, 8.6), 1.6, 1.0, boxstyle="round,pad=0.1",
                            ec=color, fc=color, lw=2.5)
        ax.add_patch(r)
        ax.text(x, 9.1, label, ha='center', va='center', fontsize=10,
                fontweight='bold', color='white')
        ax.plot([x, x], [0.5, 8.6], '--', color='#ccc', lw=1.2, zorder=0)

    def msg(x1, x2, y, text, color='#333', ret=False):
        style = '<-' if ret else '->'
        ax.annotate('', xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle=style, color=color, lw=2))
        mx = (x1+x2)/2
        ax.text(mx, y+0.18, text, ha='center', fontsize=9, color=color, fontweight='bold',
                bbox=dict(fc='white', ec='none', pad=2))

    def act(x, y1, y2, color):
        ax.add_patch(FancyBboxPatch((x-0.15, y2), 0.3, y1-y2,
                     boxstyle="square,pad=0", ec=color, fc=color, alpha=0.2, lw=1.5))

    act(2, 8.2, 0.8, C['blue'])
    act(5, 7.8, 1.0, C['green'])

    msg(2, 5, 8.2, '1: clickRecord() / typeText()')
    msg(5, 8, 7.4, '2: POST /speech-to-sign')
    act(8, 7.4, 2.0, C['teal'])
    msg(8, 10.5, 6.6, '3: transcribe(audio)')
    act(10.5, 6.6, 5.6, C['orange'])
    msg(10.5, 8, 5.6, '4: transcribedText', C['orange'], ret=True)
    msg(8, 8, 5.0, '5: translateToEnglish()', C['teal'])
    msg(8, 13, 4.2, '6: applyISLGrammar(text)')
    act(13, 4.2, 3.2, C['purple'])
    msg(13, 8, 3.2, '7: {glosses, signTokens}', C['purple'], ret=True)
    msg(8, 5, 2.0, '8: signTokens + timings', C['teal'], ret=True)
    msg(5, 15, 1.5, '9: animateGestures(tokens)')
    act(15, 1.5, 0.8, C['red'])
    msg(15, 2, 0.8, '10: avatar signs ISL', C['red'], ret=True)

    save(fig, 'sequence_speech')


# ══════════════════════════════════════════════════
# 5. ACTIVITY DIAGRAM
# ══════════════════════════════════════════════════
def activity():
    fig, ax = plt.subplots(figsize=(12, 16))
    ax.set_xlim(0, 12); ax.set_ylim(-0.5, 16)
    ax.axis('off')
    ax.set_title('Activity Diagram — Sign-to-Text Recognition',
                 fontsize=16, fontweight='bold', pad=20, color='#1a1a1a')

    def box(x, y, text, color=C['blue_bg'], edge=C['blue'], w=4.2, h=0.75):
        r = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=0.14",
                            ec=edge, fc=color, lw=2.5)
        ax.add_patch(r)
        ax.text(x, y, text, ha='center', va='center', fontsize=10, fontweight='bold', color='#1a1a1a')

    def diamond(x, y, text, color=C['amber_bg'], edge=C['amber']):
        pts = [[x, y+0.6], [x+1.4, y], [x, y-0.6], [x-1.4, y]]
        d = Polygon(pts, closed=True, ec=edge, fc=color, lw=2.5)
        ax.add_patch(d)
        ax.text(x, y, text, ha='center', va='center', fontsize=9, fontweight='bold')

    def arrow(x1, y1, x2, y2, label='', color='#555'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=2))
        if label:
            ax.text((x1+x2)/2+0.2, (y1+y2)/2, label, fontsize=9, color=color, fontweight='bold')

    # Start
    ax.plot(6, 15.5, 'o', ms=20, color='#333', zorder=5)
    arrow(6, 15.3, 6, 14.8)

    box(6, 14.4, 'Initialize Webcam\n& MediaPipe Holistic')
    arrow(6, 14.0, 6, 13.4)
    box(6, 13.0, 'Capture Video Frame\n(30 FPS)', C['blue_bg'], C['blue'])
    arrow(6, 12.6, 6, 12.0)
    diamond(6, 11.5, 'Hand\nDetected?')
    arrow(6, 10.9, 6, 10.3, 'Yes', C['green'])
    ax.annotate('', xy=(3.0, 13.0), xytext=(4.6, 11.5),
                arrowprops=dict(arrowstyle='->', color=C['red'], lw=1.8, connectionstyle="arc3,rad=0.4"))
    ax.text(2.8, 12.0, 'No', fontsize=10, color=C['red'], fontweight='bold')

    box(6, 9.9, 'Extract 258D Landmark\n(33 Pose + 42 Hand)', C['green_bg'], C['green'])
    arrow(6, 9.5, 6, 8.9)
    box(6, 8.5, 'Append to 30-Frame\nSliding Window', C['blue_bg'], C['blue'])
    arrow(6, 8.1, 6, 7.5)
    diamond(6, 7.0, 'Buffer\nFull?')
    ax.annotate('', xy=(3.0, 13.0), xytext=(4.6, 7.0),
                arrowprops=dict(arrowstyle='->', color=C['red'], lw=1.2, connectionstyle="arc3,rad=0.5"))
    ax.text(3.2, 9.5, 'No', fontsize=10, color=C['red'], fontweight='bold')
    arrow(6, 6.4, 6, 5.8, 'Yes', C['green'])

    box(6, 5.4, 'LSTM-TCN Classification\n(30×258 Input)', C['purple_bg'], C['purple'])
    arrow(6, 5.0, 6, 4.4)
    diamond(6, 3.9, 'Confidence\n≥ 0.82?')
    arrow(6, 3.3, 6, 2.7, 'Yes', C['green'])

    arrow(7.4, 3.9, 9.0, 3.9, 'No', C['red'])
    box(10.2, 3.9, 'Geometry\nClassifier', C['red_bg'], C['red'], w=2.8)

    box(6, 2.3, 'Display Recognized\nISL Phrase', C['green_bg'], C['green'])
    arrow(6, 1.9, 6, 1.3)
    box(6, 0.9, 'Translate + gTTS\n+ Save History', C['teal_bg'], C['teal'])
    arrow(6, 0.5, 6, 0.05)

    # End
    ax.plot(6, -0.2, 'o', ms=20, color='#333', zorder=5)
    ax.plot(6, -0.2, 'o', ms=13, color='white', zorder=6)
    ax.plot(6, -0.2, 'o', ms=10, color='#333', zorder=7)

    save(fig, 'activity_diagram')


# ══════════════════════════════════════════════════
# 6. ER DIAGRAM
# ══════════════════════════════════════════════════
def er_diagram():
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 16); ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('ER Diagram — Saṁvāk Database Schema',
                 fontsize=16, fontweight='bold', pad=20, color='#1a1a1a')

    def entity(x, y, w, name, attrs, pk_count, color, edge):
        lh = 0.32
        h = 0.6 + len(attrs) * lh + 0.15
        ax.add_patch(FancyBboxPatch((x+0.08, y-0.08), w, h, boxstyle="round,pad=0.08",
                     ec='none', fc='#ddd', lw=0))
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                     ec=edge, fc='white', lw=2.5))
        ax.add_patch(FancyBboxPatch((x+0.03, y+h-0.58), w-0.06, 0.55,
                     boxstyle="round,pad=0.05", ec='none', fc=color, lw=0))
        ax.text(x+w/2, y+h-0.30, name, ha='center', va='center',
                fontsize=12, fontweight='bold', color='white')
        ax.plot([x+0.03, x+w-0.03], [y+h-0.6, y+h-0.6], color=edge, lw=1)
        for i, a in enumerate(attrs):
            weight = 'bold' if i < pk_count else 'normal'
            prefix = 'PK' if i < pk_count else '  '
            ax.text(x+0.22, y+h-0.82-i*lh, f'{prefix} {a}', fontsize=9,
                    family='monospace', color='#333', fontweight=weight)

    entity(0.3, 4.8, 3.8, 'USERS',
           ['id : INTEGER', 'username : VARCHAR', 'email : VARCHAR',
            'password_hash : VARCHAR', 'is_active : BOOLEAN'],
           1, C['blue'], C['blue'])

    entity(5.5, 6.5, 4.2, 'TRANSLATIONS',
           ['id : INTEGER', 'user_id : INTEGER  [FK]',
            'source_type : VARCHAR', 'input_text : TEXT',
            'output_text : TEXT', 'source_lang : VARCHAR',
            'target_lang : VARCHAR', 'timestamp : DATETIME'],
           1, C['green'], C['green'])

    entity(5.5, 1.8, 4.2, 'USER_PREFERENCES',
           ['id : INTEGER', 'user_id : INTEGER  [FK]',
            'sign_input_lang : VARCHAR', 'sign_output_lang : VARCHAR',
            'speech_input_lang : VARCHAR', 'speech_sign_lang : VARCHAR'],
           1, C['orange'], C['orange'])

    entity(11, 6.5, 4.5, 'USER_PROGRESS',
           ['id : INTEGER', 'user_id : INTEGER  [FK]',
            'word : VARCHAR', 'points : INTEGER',
            'timestamp : DATETIME'],
           1, C['purple'], C['purple'])

    entity(11, 1.8, 4.5, 'CONTACT_MESSAGES',
           ['id : INTEGER', 'name : VARCHAR', 'email : VARCHAR',
            'message : TEXT', 'timestamp : DATETIME'],
           1, C['red'], C['red'])

    # Relationships
    ax.plot([4.1, 5.5], [7.5, 9.0], '-', color='#333', lw=2)
    ax.text(4.0, 7.8, '1', fontsize=12, fontweight='bold', color=C['blue'])
    ax.text(5.5, 9.2, 'N', fontsize=12, fontweight='bold', color=C['green'])

    ax.plot([4.1, 5.5], [6.0, 4.5], '-', color='#333', lw=2)
    ax.text(4.0, 6.2, '1', fontsize=12, fontweight='bold', color=C['blue'])
    ax.text(5.5, 4.2, '1', fontsize=12, fontweight='bold', color=C['orange'])

    ax.plot([4.1, 11], [7.0, 8.0], '-', color='#333', lw=1.5)
    ax.text(4.1, 7.3, '1', fontsize=12, fontweight='bold', color=C['blue'])
    ax.text(10.8, 8.3, 'N', fontsize=12, fontweight='bold', color=C['purple'])

    save(fig, 'er_diagram')


# ══════════════════════════════════════════════════
# 7-9. DFD + DEPLOYMENT (keep same as v2 with bigger text)
# ══════════════════════════════════════════════════
def dfd_l0():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14); ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('DFD Level 0 — Context Diagram', fontsize=16, fontweight='bold', pad=18)

    r1 = FancyBboxPatch((0.5, 2.5), 3, 2.5, boxstyle="round,pad=0.15",
                         ec=C['blue'], fc=C['blue_bg'], lw=3)
    ax.add_patch(r1)
    ax.text(2, 3.75, 'USER', ha='center', va='center', fontsize=16, fontweight='bold', color=C['blue'])

    circle = plt.Circle((7, 3.75), 2.6, ec=C['green'], fc=C['green_bg'], lw=3.5)
    ax.add_patch(circle)
    ax.text(7, 4.3, '0.0', ha='center', fontsize=12, fontweight='bold', color=C['green'])
    ax.text(7, 3.5, 'SAṀVĀK', ha='center', fontsize=15, fontweight='bold', color='#1a1a1a')
    ax.text(7, 2.7, 'Sign Language\nTranslator', ha='center', fontsize=11, color='#555')

    r2 = FancyBboxPatch((10.5, 2.5), 3, 2.5, boxstyle="round,pad=0.15",
                         ec=C['orange'], fc=C['orange_bg'], lw=3)
    ax.add_patch(r2)
    ax.text(12, 3.75, 'SQLite\nDatabase', ha='center', va='center', fontsize=13, fontweight='bold', color=C['orange'])

    ax.annotate('', xy=(4.4, 4.5), xytext=(3.5, 4.5),
                arrowprops=dict(arrowstyle='->', lw=3, color=C['blue']))
    ax.text(3.5, 5.6, 'Video Frames\nVoice Input\nCredentials', fontsize=10, ha='center', color=C['blue'])

    ax.annotate('', xy=(3.5, 2.5), xytext=(4.4, 2.5),
                arrowprops=dict(arrowstyle='->', lw=3, color=C['red']))
    ax.text(3.5, 1.5, 'Sign Text\nSpeech Output\nAvatar Animation', fontsize=10, ha='center', color=C['red'])

    ax.annotate('', xy=(10.5, 4.2), xytext=(9.6, 4.2),
                arrowprops=dict(arrowstyle='->', lw=2.5, color=C['orange']))
    ax.annotate('', xy=(9.6, 3.2), xytext=(10.5, 3.2),
                arrowprops=dict(arrowstyle='->', lw=2.5, color=C['orange']))
    ax.text(10, 5.0, 'Store', fontsize=10, ha='center', color=C['orange'], fontweight='bold')
    ax.text(10, 2.5, 'Retrieve', fontsize=10, ha='center', color=C['orange'], fontweight='bold')

    save(fig, 'dfd_level0')


def dfd_l1():
    fig, ax = plt.subplots(figsize=(16, 11))
    ax.set_xlim(0, 16); ax.set_ylim(0, 11)
    ax.axis('off')
    ax.set_title('DFD Level 1 — Process Decomposition', fontsize=16, fontweight='bold', pad=18)

    r = FancyBboxPatch((0.2, 3.8), 2.5, 2.5, boxstyle="round,pad=0.15",
                        ec=C['blue'], fc=C['blue_bg'], lw=3)
    ax.add_patch(r)
    ax.text(1.45, 5.05, 'USER', ha='center', fontsize=14, fontweight='bold', color=C['blue'])

    procs = [
        (6, 9, '1.0', 'Sign-to-Text\nRecognition', C['blue'], C['blue_bg']),
        (6, 6.5, '2.0', 'Speech-to-Sign\nTranslation', C['orange'], C['orange_bg']),
        (6, 4, '3.0', 'ISL Dictionary\n& Learning', C['purple'], C['purple_bg']),
        (6, 1.5, '4.0', 'Authentication\n& User Mgmt', C['red'], C['red_bg']),
    ]

    for x, y, num, label, ec, fc in procs:
        c = plt.Circle((x, y), 1.2, ec=ec, fc=fc, lw=3)
        ax.add_patch(c)
        ax.text(x, y+0.35, num, ha='center', fontsize=11, fontweight='bold', color=ec)
        ax.text(x, y-0.2, label, ha='center', fontsize=9, fontweight='bold', color='#333')
        ax.annotate('', xy=(x-1.2, y), xytext=(2.7, 5.05),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='#888'))

    stores = [
        (12, 9, 'D1', 'LSTM Model + iSign Index', C['blue']),
        (12, 6.5, 'D2', 'Grammar Rules + Sign Tokens', C['orange']),
        (12, 4, 'D3', 'ISL CSLRT Corpus', C['purple']),
        (12, 1.5, 'D4', 'SQLite DB', C['red']),
    ]

    for x, y, did, label, ec in stores:
        ax.plot([x-1.8, x+1.8], [y+0.4, y+0.4], color=ec, lw=2.5)
        ax.plot([x-1.8, x-1.8], [y+0.4, y-0.4], color=ec, lw=2.5)
        ax.plot([x-1.8, x+1.8], [y-0.4, y-0.4], color=ec, lw=2.5)
        ax.fill_between([x-1.8, x+1.8], y-0.4, y+0.4, color=ec, alpha=0.08)
        ax.text(x-1.6, y, did, fontsize=10, fontweight='bold', color=ec)
        ax.text(x+0.1, y, label, ha='center', fontsize=9, color='#333')
        ax.annotate('', xy=(x-1.8, y), xytext=(7.2, y),
                    arrowprops=dict(arrowstyle='<->', lw=1.5, color='#aaa'))

    save(fig, 'dfd_level1')


def dfd_l2():
    fig, ax = plt.subplots(figsize=(16, 7))
    ax.set_xlim(0, 16); ax.set_ylim(0, 7)
    ax.axis('off')
    ax.set_title('DFD Level 2 — Sign-to-Text Module Detail', fontsize=16, fontweight='bold', pad=18)

    steps = [
        (1.5, 3.5, '1.1', 'Capture\nFrame', C['blue'], C['blue_bg']),
        (4.2, 3.5, '1.2', 'MediaPipe\nLandmarks', C['green'], C['green_bg']),
        (6.9, 3.5, '1.3', 'Buffer\n30 Frames', C['amber'], C['amber_bg']),
        (9.6, 3.5, '1.4', 'LSTM-TCN\nClassify', C['purple'], C['purple_bg']),
        (12.3, 3.5, '1.5', 'Translate\n+ TTS', C['teal'], C['teal_bg']),
        (15, 3.5, '1.6', 'Save\nHistory', C['red'], C['red_bg']),
    ]

    for i, (x, y, num, label, ec, fc) in enumerate(steps):
        c = plt.Circle((x, y), 1.0, ec=ec, fc=fc, lw=3)
        ax.add_patch(c)
        ax.text(x, y+0.25, num, ha='center', fontsize=10, fontweight='bold', color=ec)
        ax.text(x, y-0.25, label, ha='center', fontsize=9, fontweight='bold', color='#333')
        if i > 0:
            px = steps[i-1][0]
            ax.annotate('', xy=(x-1.0, y), xytext=(px+1.0, y),
                        arrowprops=dict(arrowstyle='->', lw=2.5, color='#555'))

    flows = ['RGB Frame', '258D Vector', '30×258 Matrix', 'ISL Phrase', 'Translated Text', 'Audio File']
    for i, fl in enumerate(flows):
        ax.text(steps[i][0], 1.8, fl, ha='center', fontsize=9, color='#777', style='italic', fontweight='bold')

    save(fig, 'dfd_level2')


def deployment():
    fig, ax = plt.subplots(figsize=(15, 9))
    ax.set_xlim(0, 15); ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_title('Deployment Diagram — Saṁvāk Architecture', fontsize=16, fontweight='bold', pad=18)

    r1 = FancyBboxPatch((0.3, 0.5), 6, 7.5, boxstyle="round,pad=0.3",
                         ec=C['blue'], fc='#f0f5ff', lw=3.5)
    ax.add_patch(r1)
    ax.add_patch(FancyBboxPatch((0.3, 7.7), 2.2, 0.6, boxstyle="round,pad=0.1",
                 ec=C['blue'], fc=C['blue'], lw=2.5))
    ax.text(1.4, 8.0, 'device', fontsize=9, color='white', style='italic', fontweight='bold')
    ax.text(3.3, 7.7, 'Client Browser', fontsize=14, fontweight='bold', color=C['blue'])

    items_l = [
        ('HTML5 / CSS3 / JavaScript', C['gray']),
        ('TensorFlow.js (LSTM-TCN)', C['purple']),
        ('MediaPipe Holistic (WASM)', C['orange']),
        ('Three.js (3D Sign Avatar)', C['teal']),
        ('Web Speech API (STT)', C['green']),
        ('sign.js + speech.js', C['blue']),
    ]
    for i, (label, color) in enumerate(items_l):
        y = 6.5 - i * 0.95
        r = FancyBboxPatch((0.8, y-0.3), 5, 0.6, boxstyle="round,pad=0.1",
                            ec=color, fc='white', lw=2)
        ax.add_patch(r)
        ax.text(3.3, y, label, ha='center', va='center', fontsize=10, fontweight='bold', color='#333')

    # Server
    r2 = FancyBboxPatch((8.7, 0.5), 6, 7.5, boxstyle="round,pad=0.3",
                         ec=C['green'], fc='#f0fff0', lw=3.5)
    ax.add_patch(r2)
    ax.add_patch(FancyBboxPatch((8.7, 7.7), 2.2, 0.6, boxstyle="round,pad=0.1",
                 ec=C['green'], fc=C['green'], lw=2.5))
    ax.text(9.8, 8.0, 'cloud', fontsize=9, color='white', style='italic', fontweight='bold')
    ax.text(11.7, 7.7, 'Render Server', fontsize=14, fontweight='bold', color=C['green'])

    items_r = [
        ('Flask App (app.py + Blueprints)', C['green']),
        ('sign.py — Gesture Pipeline', C['blue']),
        ('speech.py — Speech Pipeline', C['orange']),
        ('grammar_helper.py — ISL Rules', C['purple']),
        ('SQLite DB (Users, Translations)', C['red']),
        ('ML Models (LSTM, iSign)', C['teal']),
    ]
    for i, (label, color) in enumerate(items_r):
        y = 6.5 - i * 0.95
        r = FancyBboxPatch((9.2, y-0.3), 5, 0.6, boxstyle="round,pad=0.1",
                            ec=color, fc='white', lw=2)
        ax.add_patch(r)
        ax.text(11.7, y, label, ha='center', va='center', fontsize=10, fontweight='bold', color='#333')

    ax.annotate('', xy=(8.7, 4.5), xytext=(6.3, 4.5),
                arrowprops=dict(arrowstyle='<->', lw=4, color=C['amber']))
    ax.text(7.5, 5.1, 'HTTPS', ha='center', fontsize=12, fontweight='bold', color=C['amber'])
    ax.text(7.5, 4.1, 'REST API', ha='center', fontsize=10, color=C['amber'])

    save(fig, 'deployment_diagram')


# ══════════════════════════════════════════════════
# RUN ALL
# ══════════════════════════════════════════════════
print("Generating improved diagrams v3...")
workflow()
use_case()
class_diagram()
sequence_sign()
sequence_speech()
activity()
er_diagram()
dfd_l0()
dfd_l1()
dfd_l2()
deployment()
print(f"\nAll done! Files in: {OUT}")
