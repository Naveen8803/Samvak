"""
Generate improved, project-specific UML and DFD diagrams for Samvak.
V2: Better colors, proper UML notation, project-specific content.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon
import numpy as np
import os

OUT = r"E:\sam\Project documents\diagrams"
os.makedirs(OUT, exist_ok=True)

# Color palette
C = {
    'blue': '#1976D2', 'blue_bg': '#E3F2FD',
    'green': '#2E7D32', 'green_bg': '#E8F5E9',
    'orange': '#E65100', 'orange_bg': '#FFF3E0',
    'purple': '#6A1B9A', 'purple_bg': '#F3E5F5',
    'red': '#C62828', 'red_bg': '#FFEBEE',
    'teal': '#00695C', 'teal_bg': '#E0F2F1',
    'gray': '#455A64', 'gray_bg': '#ECEFF1',
    'amber': '#F57F17', 'amber_bg': '#FFFDE7',
}

def save(fig, name):
    p = os.path.join(OUT, f"{name}.png")
    fig.savefig(p, dpi=200, bbox_inches='tight', facecolor='white', pad_inches=0.25)
    plt.close(fig)
    print(f"  OK: {name}.png")


# ══════════════════════════════════════════════════
# 1. USE CASE DIAGRAM (project-specific)
# ══════════════════════════════════════════════════
def use_case():
    fig, ax = plt.subplots(figsize=(15, 11))
    ax.set_xlim(-1, 15); ax.set_ylim(-0.5, 11)
    ax.set_aspect('equal'); ax.axis('off')
    ax.set_title('Use Case Diagram — Saṁvāk Sign Language Translator',
                 fontsize=15, fontweight='bold', pad=18, color='#1a1a1a')

    # System boundary
    r = FancyBboxPatch((3, -0.2), 11.5, 10.8, boxstyle="round,pad=0.4",
                        edgecolor=C['blue'], facecolor='#FAFBFF', lw=2.5)
    ax.add_patch(r)
    ax.text(8.75, 10.8, '« System »  Saṁvāk', ha='center', fontsize=12,
            fontweight='bold', color=C['blue'], style='italic')

    # Stick figure actor
    def draw_actor(x, y, label):
        ax.plot(x, y+0.4, 'o', ms=14, color=C['blue'], mec=C['blue'], mew=2, zorder=5)
        ax.plot([x, x], [y+0.15, y-0.35], color=C['blue'], lw=2, zorder=5)
        ax.plot([x-0.35, x+0.35], [y, y], color=C['blue'], lw=2, zorder=5)
        ax.plot([x, x-0.25], [y-0.35, y-0.7], color=C['blue'], lw=2, zorder=5)
        ax.plot([x, x+0.25], [y-0.35, y-0.7], color=C['blue'], lw=2, zorder=5)
        ax.text(x, y-0.95, label, ha='center', fontsize=10, fontweight='bold')

    draw_actor(1.5, 5.5, 'User')

    # Use case ellipses
    main_uc = [
        (6.5, 9.5, 'Register / Login', C['green_bg'], C['green']),
        (6.5, 8.0, 'Sign-to-Text\nTranslation', C['blue_bg'], C['blue']),
        (6.5, 6.5, 'Speech-to-Sign\nTranslation', C['orange_bg'], C['orange']),
        (6.5, 5.0, 'Browse ISL\nDictionary', C['purple_bg'], C['purple']),
        (6.5, 3.5, 'Learn ISL\nSigns', C['teal_bg'], C['teal']),
        (6.5, 2.0, 'View Dashboard\n& History', C['gray_bg'], C['gray']),
        (6.5, 0.5, 'Update Language\nPreferences', C['amber_bg'], C['amber']),
    ]

    for x, y, lbl, bg, ec in main_uc:
        el = mpatches.Ellipse((x, y), 3.6, 1.1, ec=ec, fc=bg, lw=2)
        ax.add_patch(el)
        ax.text(x, y, lbl, ha='center', va='center', fontsize=8, fontweight='bold', color='#1a1a1a')
        ax.plot([2.1, x-1.8], [5.5, y], '-', color='#888', lw=1, zorder=1)

    # Sign-to-Text sub-cases  (<<include>>)
    sign_sub = [
        (11, 9.5, 'Capture Hand\nGestures (Webcam)', C['blue']),
        (11, 8.3, 'Extract Landmarks\n(MediaPipe 258D)', C['blue']),
        (11, 7.1, 'Classify Sign\n(LSTM-TCN Model)', C['blue']),
        (11, 5.9, 'Translate &\nSpeak (gTTS)', C['blue']),
    ]
    for x, y, lbl, ec in sign_sub:
        el = mpatches.Ellipse((x, y), 2.8, 0.9, ec=ec, fc='#f0f7ff', lw=1.5, ls='--')
        ax.add_patch(el)
        ax.text(x, y, lbl, ha='center', va='center', fontsize=6.8, color='#333')
        ax.annotate('', xy=(x-1.4, y), xytext=(8.3, 8.0),
                    arrowprops=dict(arrowstyle='->', color='#aaa', lw=0.8, ls='dashed'))

    # Speech-to-Sign sub-cases
    speech_sub = [
        (11, 4.5, 'Transcribe Audio\n(Google STT)', C['orange']),
        (11, 3.3, 'ISL Grammar\nTransform (OSV)', C['orange']),
        (11, 2.1, 'Animate Avatar\n(Three.js 3D)', C['orange']),
    ]
    for x, y, lbl, ec in speech_sub:
        el = mpatches.Ellipse((x, y), 2.8, 0.9, ec=ec, fc='#fff8f0', lw=1.5, ls='--')
        ax.add_patch(el)
        ax.text(x, y, lbl, ha='center', va='center', fontsize=6.8, color='#333')
        ax.annotate('', xy=(x-1.4, y), xytext=(8.3, 6.5),
                    arrowprops=dict(arrowstyle='->', color='#cca', lw=0.8, ls='dashed'))

    # Include labels
    ax.text(9.5, 8.8, '«include»', fontsize=7, style='italic', color=C['blue'], rotation=15)
    ax.text(9.5, 5.2, '«include»', fontsize=7, style='italic', color=C['orange'], rotation=-15)

    save(fig, 'use_case_diagram')


# ══════════════════════════════════════════════════
# 2. CLASS DIAGRAM (project-specific with real attrs)
# ══════════════════════════════════════════════════
def class_diagram():
    fig, ax = plt.subplots(figsize=(16, 11))
    ax.set_xlim(0, 16); ax.set_ylim(0, 11)
    ax.axis('off')
    ax.set_title('Class Diagram — Saṁvāk Application Data Model',
                 fontsize=15, fontweight='bold', pad=18, color='#1a1a1a')

    def draw_class(x, y, w, name, attrs, methods, hdr_color, border_color):
        lh = 0.26  # line height
        attr_h = len(attrs) * lh + 0.15
        meth_h = len(methods) * lh + 0.15
        h = 0.55 + attr_h + meth_h
        # Box
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06",
                               ec=border_color, fc='white', lw=2)
        ax.add_patch(rect)
        # Header
        hdr = FancyBboxPatch((x+0.02, y+h-0.52), w-0.04, 0.5, boxstyle="round,pad=0.04",
                              ec='none', fc=hdr_color, lw=0)
        ax.add_patch(hdr)
        ax.text(x+w/2, y+h-0.28, name, ha='center', va='center',
                fontsize=10, fontweight='bold', color='white')
        ax.text(x+w/2, y+h-0.48, '<<entity>>' if 'Helper' not in name and 'Classifier' not in name else '<<service>>',
                ha='center', va='center', fontsize=7, color=(1, 1, 1, 0.7), style='italic')
        # Separator
        sep1 = y + h - 0.55 - attr_h
        ax.plot([x+0.05, x+w-0.05], [y+h-0.55, y+h-0.55], color=border_color, lw=0.8)
        ax.plot([x+0.05, x+w-0.05], [sep1, sep1], color=border_color, lw=0.8)
        # Attributes
        for i, a in enumerate(attrs):
            ax.text(x+0.18, y+h-0.72-i*lh, a, fontsize=7, family='monospace', color='#333')
        # Methods
        for i, m in enumerate(methods):
            ax.text(x+0.18, sep1-0.18-i*lh, m, fontsize=7, family='monospace', color='#1565C0')
        return y + h  # top y

    # --- Draw classes ---
    # User (center-left)
    draw_class(0.3, 5.5, 3.6, 'User',
               ['+ id : Integer «PK»', '+ username : String «UK»',
                '+ email : String «UK»', '+ password_hash : String',
                '+ is_active : Boolean'],
               ['+ check_password(pwd)', '+ get_id() : String',
                '+ set_preference(key, val)'],
               C['blue'], C['blue'])

    # Translation (top-center)
    draw_class(5, 7.5, 3.8, 'Translation',
               ['+ id : Integer «PK»', '+ user_id : Integer «FK»',
                '+ source_type : String', '+ input_text : Text',
                '+ output_text : Text', '+ source_lang : String',
                '+ target_lang : String', '+ timestamp : DateTime'],
               ['+ to_dict() : Dict'],
               C['green'], C['green'])

    # UserPreference (mid-center)
    draw_class(5, 4.2, 3.8, 'UserPreference',
               ['+ id : Integer «PK»', '+ user_id : Integer «FK UK»',
                '+ sign_input_lang : String', '+ sign_output_lang : String',
                '+ sign_detection_mode : String',
                '+ speech_input_lang : String', '+ speech_sign_lang : String'],
               ['+ to_dict() : Dict', '+ default_payload() : Dict'],
               C['orange'], C['orange'])

    # UserProgress (bottom-center)
    draw_class(5, 1.0, 3.8, 'UserProgress',
               ['+ id : Integer «PK»', '+ user_id : Integer «FK»',
                '+ word : String', '+ points : Integer',
                '+ timestamp : DateTime'],
               ['+ add_xp(amount)'],
               C['red'], C['red'])

    # GeometryClassifier (right-top)
    draw_class(10.5, 7.2, 4.5, 'GeometryClassifier',
               ['- MIN_CONFIDENCE : Float = 0.82',
                '- BASIC_SIGNS : Tuple[String]',
                '+ last_prediction : String'],
               ['+ predict(landmarks) : String',
                '+ predict_with_metadata(lm) : Dict',
                '- _analyze_frame(lm) : Dict',
                '- _hand_metrics(hand) : Dict',
                '- _basic_static_candidates(f)',
                '- _dynamic_candidates(seq, f)'],
               C['purple'], C['purple'])

    # GrammarHelper (right-bottom)
    draw_class(10.5, 3.2, 4.5, 'GrammarHelper',
               ['- _DROP_WORDS : Set{a,an,the,...}',
                '- _WH_WORDS : Set{what,where,...}',
                '- _TIME_MARKERS : Set{today,...}',
                '- _PHRASE_MAP : Dict'],
               ['+ english_to_isl_glosses(text)',
                '+ gloss_to_english(glosses)',
                '- _apply_isl_grammar(words)',
                '- _expand_contractions(text)',
                '- _find_best_phrase(text)'],
               C['teal'], C['teal'])

    # ContactMessage (bottom-left)
    draw_class(0.3, 1.0, 3.6, 'ContactMessage',
               ['+ id : Integer «PK»', '+ name : String',
                '+ email : String', '+ message : Text',
                '+ timestamp : DateTime'],
               [],
               C['gray'], C['gray'])

    # --- Relationships with cardinality labels ---
    def rel_arrow(x1, y1, x2, y2, label, card1, card2, style='-'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='-|>', color='#333', lw=1.8, ls=style))
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my+0.2, label, ha='center', fontsize=7.5, style='italic',
                color='#555', bbox=dict(fc='white', ec='none', pad=1))
        ax.text(x1+0.15, y1-0.15, card1, fontsize=8, fontweight='bold', color=C['blue'])
        ax.text(x2+0.15, y2+0.15, card2, fontsize=8, fontweight='bold', color=C['blue'])

    rel_arrow(3.9, 8.5, 5.0, 9.5, 'has', '1', '*')
    rel_arrow(3.9, 7.0, 5.0, 6.5, 'configures', '1', '1')
    rel_arrow(3.9, 5.8, 5.0, 2.8, 'tracks', '1', '*')

    # Dashed dependency arrows for service classes
    ax.annotate('', xy=(10.5, 8.5), xytext=(8.8, 9.0),
                arrowprops=dict(arrowstyle='->', color='#999', lw=1.2, ls='dashed'))
    ax.text(9.5, 9.0, '«uses»', fontsize=7, color='#999', style='italic')

    ax.annotate('', xy=(10.5, 5.0), xytext=(8.8, 6.0),
                arrowprops=dict(arrowstyle='->', color='#999', lw=1.2, ls='dashed'))
    ax.text(9.3, 5.7, '«uses»', fontsize=7, color='#999', style='italic')

    save(fig, 'class_diagram')


# ══════════════════════════════════════════════════
# 3. SEQUENCE DIAGRAM - Sign-to-Text
# ══════════════════════════════════════════════════
def sequence_sign():
    fig, ax = plt.subplots(figsize=(15, 10))
    ax.set_xlim(0, 15); ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('Sequence Diagram — Sign-to-Text Translation Flow',
                 fontsize=14, fontweight='bold', pad=15, color='#1a1a1a')

    # Lifelines
    lifelines = [
        (1.5, 'User', C['blue']),
        (4, 'Browser\n(sign.js)', C['green']),
        (6.5, 'MediaPipe\n(WASM)', C['orange']),
        (9, 'TF.js\nLSTM-TCN', C['purple']),
        (11.5, 'Flask\nServer', C['teal']),
        (14, 'SQLite\nDB', C['red']),
    ]

    for x, label, color in lifelines:
        # Header box
        r = FancyBboxPatch((x-0.7, 9.0), 1.4, 0.8, boxstyle="round,pad=0.08",
                            ec=color, fc=color, lw=2)
        ax.add_patch(r)
        ax.text(x, 9.4, label, ha='center', va='center', fontsize=7.5,
                fontweight='bold', color='white')
        # Lifeline
        ax.plot([x, x], [0.3, 9.0], '--', color='#ccc', lw=1, zorder=0)

    # Messages
    def msg(x1, x2, y, text, color='#333', ret=False):
        style = '<-' if ret else '->'
        ax.annotate('', xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle=style, color=color, lw=1.5))
        mx = (x1+x2)/2
        ax.text(mx, y+0.12, text, ha='center', fontsize=7, color=color,
                bbox=dict(fc='white', ec='none', pad=1))

    # Activation boxes
    def act(x, y1, y2, color):
        ax.add_patch(FancyBboxPatch((x-0.12, y2), 0.24, y1-y2,
                     boxstyle="square,pad=0", ec=color, fc=color, alpha=0.2, lw=1))

    # Flow
    act(1.5, 8.5, 0.5, C['blue'])
    act(4, 8.3, 0.8, C['green'])

    msg(1.5, 4, 8.5, '1: startCamera()')
    msg(4, 6.5, 7.8, '2: processFrame(rgbImage)')
    act(6.5, 7.8, 6.8, C['orange'])
    msg(6.5, 4, 6.8, '3: return 258D landmarkVector', C['orange'], ret=True)

    # Loop box
    ax.add_patch(FancyBboxPatch((2.5, 6.5), 5.5, 2.0, boxstyle="round,pad=0.1",
                 ec='#999', fc='#f9f9f9', lw=1.5, ls='--'))
    ax.text(2.7, 8.3, 'loop', fontsize=8, fontweight='bold', color='#666',
            bbox=dict(fc='#eee', ec='#999', pad=2))
    ax.text(4.5, 8.3, '[every frame @ 30 FPS]', fontsize=7, color='#888')

    msg(4, 4, 7.0, '4: appendToBuffer()', C['green'])

    msg(4, 9, 5.8, '5: predict(30×258 sequence)')
    act(9, 5.8, 4.8, C['purple'])
    msg(9, 4, 4.8, '6: return {phrase, confidence}', C['purple'], ret=True)

    msg(4, 11.5, 4.2, '7: POST /api/sign/translate')
    act(11.5, 4.2, 2.2, C['teal'])
    msg(11.5, 14, 3.6, '8: INSERT translation')
    act(14, 3.6, 3.0, C['red'])
    msg(14, 11.5, 3.0, '9: OK', C['red'], ret=True)
    msg(11.5, 4, 2.2, '10: {translatedText, audioUrl}', C['teal'], ret=True)
    msg(4, 1.5, 1.5, '11: displayText() + playAudio()', C['green'], ret=True)

    save(fig, 'sequence_sign')


# ══════════════════════════════════════════════════
# 4. SEQUENCE DIAGRAM - Speech-to-Sign
# ══════════════════════════════════════════════════
def sequence_speech():
    fig, ax = plt.subplots(figsize=(15, 9))
    ax.set_xlim(0, 15); ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_title('Sequence Diagram — Speech-to-Sign Translation Flow',
                 fontsize=14, fontweight='bold', pad=15, color='#1a1a1a')

    lifelines = [
        (1.5, 'User', C['blue']),
        (4, 'Browser\n(speech.js)', C['green']),
        (7, 'Flask\nServer', C['teal']),
        (9.5, 'Speech\nRecognition', C['orange']),
        (12, 'spaCy +\nGrammar Engine', C['purple']),
        (14, 'Three.js\n3D Avatar', C['red']),
    ]

    for x, label, color in lifelines:
        r = FancyBboxPatch((x-0.7, 7.8), 1.4, 0.8, boxstyle="round,pad=0.08",
                            ec=color, fc=color, lw=2)
        ax.add_patch(r)
        ax.text(x, 8.2, label, ha='center', va='center', fontsize=7.5,
                fontweight='bold', color='white')
        ax.plot([x, x], [0.5, 7.8], '--', color='#ccc', lw=1, zorder=0)

    def msg(x1, x2, y, text, color='#333', ret=False):
        style = '<-' if ret else '->'
        ax.annotate('', xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle=style, color=color, lw=1.5))
        mx = (x1+x2)/2
        ax.text(mx, y+0.12, text, ha='center', fontsize=7, color=color,
                bbox=dict(fc='white', ec='none', pad=1))

    def act(x, y1, y2, color):
        ax.add_patch(FancyBboxPatch((x-0.12, y2), 0.24, y1-y2,
                     boxstyle="square,pad=0", ec=color, fc=color, alpha=0.2, lw=1))

    act(1.5, 7.5, 0.8, C['blue'])
    act(4, 7.2, 1.0, C['green'])

    msg(1.5, 4, 7.5, '1: clickRecord() / typeText()')
    msg(4, 7, 6.8, '2: POST /api/speech-to-sign (audio blob)')
    act(7, 6.8, 2.0, C['teal'])
    msg(7, 9.5, 6.2, '3: transcribe(audioData)')
    act(9.5, 6.2, 5.3, C['orange'])
    msg(9.5, 7, 5.3, '4: return transcribedText', C['orange'], ret=True)

    msg(7, 7, 4.8, '5: translateToEnglish()', C['teal'])

    msg(7, 12, 4.2, '6: tokenize + applyISLGrammar(text)')
    act(12, 4.2, 3.0, C['purple'])
    msg(12, 7, 3.0, '7: return {glosses, signTokens}', C['purple'], ret=True)

    msg(7, 4, 2.0, '8: return signTokens + timings', C['teal'], ret=True)
    msg(4, 14, 1.5, '9: animateGestures(tokens)')
    act(14, 1.5, 0.8, C['red'])
    msg(14, 1.5, 0.8, '10: avatar performs ISL signs', C['red'], ret=True)

    save(fig, 'sequence_speech')


# ══════════════════════════════════════════════════
# 5. ACTIVITY DIAGRAM
# ══════════════════════════════════════════════════
def activity():
    fig, ax = plt.subplots(figsize=(11, 15))
    ax.set_xlim(0, 11); ax.set_ylim(-0.5, 15)
    ax.axis('off')
    ax.set_title('Activity Diagram — Sign-to-Text Recognition Pipeline',
                 fontsize=14, fontweight='bold', pad=15, color='#1a1a1a')

    def box(x, y, text, color=C['blue_bg'], edge=C['blue'], w=3.8, h=0.65):
        r = FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle="round,pad=0.12",
                            ec=edge, fc=color, lw=2)
        ax.add_patch(r)
        ax.text(x, y, text, ha='center', va='center', fontsize=8.5, fontweight='bold', color='#1a1a1a')

    def diamond(x, y, text, color=C['amber_bg'], edge=C['amber']):
        pts = [[x, y+0.55], [x+1.3, y], [x, y-0.55], [x-1.3, y]]
        d = Polygon(pts, closed=True, ec=edge, fc=color, lw=2)
        ax.add_patch(d)
        ax.text(x, y, text, ha='center', va='center', fontsize=7.5, fontweight='bold')

    def arrow(x1, y1, x2, y2, label='', color='#555'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.8))
        if label:
            mx = (x1+x2)/2 + 0.2
            my = (y1+y2)/2
            ax.text(mx, my, label, fontsize=7.5, color=color, fontweight='bold')

    # Start
    ax.plot(5.5, 14.5, 'o', ms=18, color='#333', zorder=5)
    ax.text(5.5, 14.5, '▶', ha='center', va='center', fontsize=8, color='white', fontweight='bold')
    arrow(5.5, 14.3, 5.5, 13.7)

    box(5.5, 13.3, 'Initialize Webcam\n& MediaPipe Holistic')
    arrow(5.5, 12.95, 5.5, 12.35)

    box(5.5, 12.0, 'Capture Video Frame\n(30 FPS)', C['blue_bg'], C['blue'])
    arrow(5.5, 11.65, 5.5, 11.05)

    diamond(5.5, 10.6, 'Hand\nDetected?')
    arrow(5.5, 10.05, 5.5, 9.45, 'Yes', C['green'])
    # No -> loop back
    ax.annotate('', xy=(3.0, 12.0), xytext=(4.2, 10.6),
                arrowprops=dict(arrowstyle='->', color=C['red'], lw=1.5,
                               connectionstyle="arc3,rad=0.4"))
    ax.text(3.0, 11.2, 'No', fontsize=8, color=C['red'], fontweight='bold')

    box(5.5, 9.1, 'Extract 258D Landmark Vector\n(33 Pose + 21×2 Hands)', C['green_bg'], C['green'])
    arrow(5.5, 8.75, 5.5, 8.15)

    box(5.5, 7.8, 'Append to 30-Frame\nSliding Window Buffer', C['blue_bg'], C['blue'])
    arrow(5.5, 7.45, 5.5, 6.85)

    diamond(5.5, 6.4, 'Buffer\nFull (30)?')
    ax.annotate('', xy=(3.0, 12.0), xytext=(4.2, 6.4),
                arrowprops=dict(arrowstyle='->', color=C['red'], lw=1.2,
                               connectionstyle="arc3,rad=0.5"))
    ax.text(3.2, 9.0, 'No', fontsize=8, color=C['red'], fontweight='bold')
    arrow(5.5, 5.85, 5.5, 5.25, 'Yes', C['green'])

    box(5.5, 4.9, 'Run LSTM-TCN\nClassification (30×258)', C['purple_bg'], C['purple'])
    arrow(5.5, 4.55, 5.5, 3.95)

    diamond(5.5, 3.5, 'Confidence\n≥ Threshold?')
    arrow(5.5, 2.95, 5.5, 2.35, 'Yes', C['green'])

    # No -> Geometry fallback
    arrow(6.8, 3.5, 8.3, 3.5, 'No', C['red'])
    box(9.5, 3.5, 'Geometry\nClassifier\nFallback', C['red_bg'], C['red'], w=2.8, h=0.9)

    box(5.5, 2.0, 'Display Recognized\nISL Phrase', C['green_bg'], C['green'])
    arrow(5.5, 1.65, 5.5, 1.05)

    box(5.5, 0.7, 'Translate → gTTS Speech\n→ Save to History', C['teal_bg'], C['teal'])
    arrow(5.5, 0.35, 5.5, -0.1)

    # End
    ax.plot(5.5, -0.35, 'o', ms=18, color='#333', zorder=5)
    ax.plot(5.5, -0.35, 'o', ms=12, color='white', zorder=6)
    ax.plot(5.5, -0.35, 'o', ms=9, color='#333', zorder=7)

    save(fig, 'activity_diagram')


# ══════════════════════════════════════════════════
# 6. ER DIAGRAM (project-specific)
# ══════════════════════════════════════════════════
def er_diagram():
    fig, ax = plt.subplots(figsize=(15, 9))
    ax.set_xlim(0, 15); ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_title('ER Diagram — Saṁvāk Database Schema',
                 fontsize=14, fontweight='bold', pad=15, color='#1a1a1a')

    def entity(x, y, w, name, attrs, pk_count, color, edge):
        lh = 0.30
        h = 0.55 + len(attrs) * lh + 0.1
        # Shadow
        ax.add_patch(FancyBboxPatch((x+0.08, y-0.08), w, h, boxstyle="round,pad=0.06",
                     ec='none', fc='#ddd', lw=0))
        # Box
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06",
                     ec=edge, fc='white', lw=2))
        # Header
        ax.add_patch(FancyBboxPatch((x+0.03, y+h-0.53), w-0.06, 0.5,
                     boxstyle="round,pad=0.04", ec='none', fc=color, lw=0))
        ax.text(x+w/2, y+h-0.28, name, ha='center', va='center',
                fontsize=10, fontweight='bold', color='white')
        ax.plot([x+0.03, x+w-0.03], [y+h-0.55, y+h-0.55], color=edge, lw=1)
        for i, a in enumerate(attrs):
            icon = 'PK' if i < pk_count else '  '
            weight = 'bold' if i < pk_count else 'normal'
            ax.text(x+0.2, y+h-0.75-i*lh, f'{icon} {a}', fontsize=7.5,
                    family='monospace', color='#333', fontweight=weight)
        return y + h / 2  # center y

    # USERS
    cy1 = entity(0.3, 4.5, 3.5, 'USERS',
                 ['id : INTEGER', 'username : VARCHAR', 'email : VARCHAR',
                  'password_hash : VARCHAR', 'is_active : BOOLEAN'],
                 1, C['blue'], C['blue'])

    # TRANSLATIONS
    cy2 = entity(5, 6.0, 4, 'TRANSLATIONS',
                 ['id : INTEGER', 'user_id : INTEGER   «FK»',
                  'source_type : VARCHAR', 'input_text : TEXT',
                  'output_text : TEXT', 'source_lang : VARCHAR',
                  'target_lang : VARCHAR', 'timestamp : DATETIME'],
                 1, C['green'], C['green'])

    # USER_PREFERENCES
    cy3 = entity(5, 1.5, 4, 'USER_PREFERENCES',
                 ['id : INTEGER', 'user_id : INTEGER   «FK UK»',
                  'sign_input_language : VARCHAR', 'sign_output_language : VARCHAR',
                  'sign_detection_mode : VARCHAR',
                  'speech_input_language : VARCHAR', 'speech_sign_language : VARCHAR'],
                 1, C['orange'], C['orange'])

    # USER_PROGRESS
    cy4 = entity(10.5, 6.0, 4, 'USER_PROGRESS',
                 ['id : INTEGER', 'user_id : INTEGER   «FK»',
                  'word : VARCHAR', 'points : INTEGER',
                  'timestamp : DATETIME'],
                 1, C['purple'], C['purple'])

    # CONTACT_MESSAGES
    cy5 = entity(10.5, 1.5, 4, 'CONTACT_MESSAGES',
                 ['id : INTEGER', 'name : VARCHAR', 'email : VARCHAR',
                  'message : TEXT', 'timestamp : DATETIME'],
                 1, C['red'], C['red'])

    # Relationships with diamond
    def rel_diamond(x, y, label, lw=1.8):
        pts = [[x, y+0.3], [x+0.5, y], [x, y-0.3], [x-0.5, y]]
        d = Polygon(pts, closed=True, ec='#333', fc=C['amber_bg'], lw=lw)
        ax.add_patch(d)
        ax.text(x, y, label, ha='center', va='center', fontsize=6, fontweight='bold')

    # USERS -> TRANSLATIONS
    ax.plot([3.8, 5], [7, 8], '-', color='#333', lw=1.5)
    rel_diamond(4.4, 7.5, 'has')
    ax.text(3.8, 7.3, '1', fontsize=10, fontweight='bold', color=C['blue'])
    ax.text(5.0, 8.0, 'N', fontsize=10, fontweight='bold', color=C['green'])

    # USERS -> PREFERENCES
    ax.plot([3.8, 5], [5.5, 4.5], '-', color='#333', lw=1.5)
    rel_diamond(4.4, 5.0, 'sets')
    ax.text(3.8, 5.7, '1', fontsize=10, fontweight='bold', color=C['blue'])
    ax.text(5.0, 4.2, '1', fontsize=10, fontweight='bold', color=C['orange'])

    # USERS -> PROGRESS
    ax.plot([3.8, 10.5], [6.5, 7.5], '-', color='#333', lw=1.2)
    rel_diamond(7.5, 7.2, 'earns')
    ax.text(3.9, 6.8, '1', fontsize=10, fontweight='bold', color=C['blue'])
    ax.text(10.3, 7.8, 'N', fontsize=10, fontweight='bold', color=C['purple'])

    save(fig, 'er_diagram')


# ══════════════════════════════════════════════════
# 7. DFD Level 0
# ══════════════════════════════════════════════════
def dfd_l0():
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13); ax.set_ylim(0, 7)
    ax.axis('off')
    ax.set_title('DFD Level 0 — Context Diagram',
                 fontsize=14, fontweight='bold', pad=15, color='#1a1a1a')

    # User entity
    r1 = FancyBboxPatch((0.5, 2.5), 2.5, 2, boxstyle="round,pad=0.12",
                         ec=C['blue'], fc=C['blue_bg'], lw=2.5)
    ax.add_patch(r1)
    ax.text(1.75, 3.5, 'USER', ha='center', va='center', fontsize=14, fontweight='bold', color=C['blue'])

    # System circle
    circle = plt.Circle((6.5, 3.5), 2.4, ec=C['green'], fc=C['green_bg'], lw=3)
    ax.add_patch(circle)
    ax.text(6.5, 4.0, '0.0', ha='center', fontsize=10, fontweight='bold', color=C['green'])
    ax.text(6.5, 3.4, 'SAṀVĀK', ha='center', fontsize=13, fontweight='bold', color='#1a1a1a')
    ax.text(6.5, 2.7, 'Sign Language\nTranslator System', ha='center', fontsize=9, color='#555')

    # Database
    r2 = FancyBboxPatch((10, 2.5), 2.5, 2, boxstyle="round,pad=0.12",
                         ec=C['orange'], fc=C['orange_bg'], lw=2.5)
    ax.add_patch(r2)
    ax.text(11.25, 3.5, 'SQLite\nDatabase', ha='center', va='center', fontsize=11, fontweight='bold', color=C['orange'])

    # Input arrows
    ax.annotate('', xy=(4.1, 4.5), xytext=(3.0, 4.5),
                arrowprops=dict(arrowstyle='->', lw=2.5, color=C['blue']))
    ax.text(3.4, 5.2, 'Video Frames\nVoice Input\nText Input\nCredentials', fontsize=8, ha='center', color=C['blue'])

    # Output arrows
    ax.annotate('', xy=(3.0, 2.5), xytext=(4.1, 2.5),
                arrowprops=dict(arrowstyle='->', lw=2.5, color=C['red']))
    ax.text(3.4, 1.6, 'Recognized Text\nSpeech Output\nAvatar Animation\nDashboard Data', fontsize=8, ha='center', color=C['red'])

    # DB arrows
    ax.annotate('', xy=(10, 4.0), xytext=(8.9, 4.0),
                arrowprops=dict(arrowstyle='->', lw=2, color=C['orange']))
    ax.annotate('', xy=(8.9, 3.0), xytext=(10, 3.0),
                arrowprops=dict(arrowstyle='->', lw=2, color=C['orange']))
    ax.text(9.5, 4.5, 'Store', fontsize=8, ha='center', color=C['orange'])
    ax.text(9.5, 2.5, 'Retrieve', fontsize=8, ha='center', color=C['orange'])

    save(fig, 'dfd_level0')


# ══════════════════════════════════════════════════
# 8. DFD Level 1
# ══════════════════════════════════════════════════
def dfd_l1():
    fig, ax = plt.subplots(figsize=(15, 10))
    ax.set_xlim(0, 15); ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('DFD Level 1 — Process Decomposition',
                 fontsize=14, fontweight='bold', pad=15, color='#1a1a1a')

    # User
    r = FancyBboxPatch((0.2, 3.5), 2, 2, boxstyle="round,pad=0.12",
                        ec=C['blue'], fc=C['blue_bg'], lw=2.5)
    ax.add_patch(r)
    ax.text(1.2, 4.5, 'USER', ha='center', fontsize=12, fontweight='bold', color=C['blue'])

    # Processes
    procs = [
        (5, 8.5, '1.0', 'Sign-to-Text\nRecognition', C['blue'], C['blue_bg']),
        (5, 6.3, '2.0', 'Speech-to-Sign\nTranslation', C['orange'], C['orange_bg']),
        (5, 4.1, '3.0', 'ISL Dictionary\n& Learning', C['purple'], C['purple_bg']),
        (5, 1.9, '4.0', 'Authentication\n& User Mgmt', C['red'], C['red_bg']),
    ]

    for x, y, num, label, ec, fc in procs:
        c = plt.Circle((x, y), 1.0, ec=ec, fc=fc, lw=2.5)
        ax.add_patch(c)
        ax.text(x, y+0.3, num, ha='center', fontsize=9, fontweight='bold', color=ec)
        ax.text(x, y-0.15, label, ha='center', fontsize=7.5, color='#333')
        ax.annotate('', xy=(x-1.0, y), xytext=(2.2, 4.5),
                    arrowprops=dict(arrowstyle='->', lw=1.2, color='#888'))

    # Data stores
    stores = [
        (11, 8.5, 'D1', 'LSTM Model + iSign Index', C['blue']),
        (11, 6.3, 'D2', 'Grammar Rules + Sign Tokens', C['orange']),
        (11, 4.1, 'D3', 'ISL CSLRT Corpus', C['purple']),
        (11, 1.9, 'D4', 'SQLite DB (Users, Prefs, History)', C['red']),
    ]

    for x, y, did, label, ec in stores:
        ax.plot([x-1.5, x+1.5], [y+0.35, y+0.35], color=ec, lw=2)
        ax.plot([x-1.5, x-1.5], [y+0.35, y-0.35], color=ec, lw=2)
        ax.plot([x-1.5, x+1.5], [y-0.35, y-0.35], color=ec, lw=2)
        ax.fill_between([x-1.5, x+1.5], y-0.35, y+0.35, color=ec, alpha=0.08)
        ax.text(x-1.3, y, did, fontsize=8, fontweight='bold', color=ec)
        ax.text(x+0.1, y, label, ha='center', fontsize=7, color='#333')
        ax.annotate('', xy=(x-1.5, y), xytext=(6.0, y),
                    arrowprops=dict(arrowstyle='<->', lw=1.2, color='#aaa'))

    save(fig, 'dfd_level1')


# ══════════════════════════════════════════════════
# 9. DFD Level 2
# ══════════════════════════════════════════════════
def dfd_l2():
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.set_xlim(0, 15); ax.set_ylim(0, 6)
    ax.axis('off')
    ax.set_title('DFD Level 2 — Sign-to-Text Module Detail',
                 fontsize=14, fontweight='bold', pad=15, color='#1a1a1a')

    steps = [
        (1.5, 3, '1.1', 'Capture\nFrame', C['blue'], C['blue_bg']),
        (3.8, 3, '1.2', 'MediaPipe\nLandmarks', C['green'], C['green_bg']),
        (6.1, 3, '1.3', 'Build 30-Frame\nWindow', C['amber'], C['amber_bg']),
        (8.4, 3, '1.4', 'LSTM-TCN\nClassify', C['purple'], C['purple_bg']),
        (10.7, 3, '1.5', 'Translate\nLanguage', C['teal'], C['teal_bg']),
        (13, 3, '1.6', 'TTS +\nSave', C['red'], C['red_bg']),
    ]

    for i, (x, y, num, label, ec, fc) in enumerate(steps):
        c = plt.Circle((x, y), 0.8, ec=ec, fc=fc, lw=2.5)
        ax.add_patch(c)
        ax.text(x, y+0.2, num, ha='center', fontsize=8, fontweight='bold', color=ec)
        ax.text(x, y-0.2, label, ha='center', fontsize=7, color='#333')
        if i > 0:
            px = steps[i-1][0]
            ax.annotate('', xy=(x-0.8, y), xytext=(px+0.8, y),
                        arrowprops=dict(arrowstyle='->', lw=2, color='#555'))

    # Data flow labels
    flows = ['RGB\nFrame', '258D\nVector', '30×258\nMatrix', 'ISL Phrase\n+ Confidence', 'Translated\nText', 'Audio\nFile']
    for i, fl in enumerate(flows):
        ax.text(steps[i][0], 1.6, fl, ha='center', fontsize=7, color='#888', style='italic')

    # External entities
    ax.text(0.2, 3, 'Camera', ha='center', fontsize=9, fontweight='bold', color=C['blue'],
            bbox=dict(boxstyle='round,pad=0.3', fc=C['blue_bg'], ec=C['blue']))

    ax.text(14.5, 3, 'User', ha='center', fontsize=9, fontweight='bold', color=C['red'],
            bbox=dict(boxstyle='round,pad=0.3', fc=C['red_bg'], ec=C['red']))

    # Geometry fallback
    ax.text(8.4, 5.2, 'Geometry\nClassifier', ha='center', fontsize=7,
            bbox=dict(boxstyle='round,pad=0.2', fc=C['amber_bg'], ec=C['amber']))
    ax.annotate('', xy=(8.4, 4.7), xytext=(8.4, 3.8),
                arrowprops=dict(arrowstyle='<->', lw=1.2, color=C['amber'], ls='dashed'))

    save(fig, 'dfd_level2')


# ══════════════════════════════════════════════════
# 10. DEPLOYMENT DIAGRAM (improved)
# ══════════════════════════════════════════════════
def deployment():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14); ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('Deployment Diagram — Saṁvāk System Architecture',
                 fontsize=14, fontweight='bold', pad=15, color='#1a1a1a')

    # Client node
    r1 = FancyBboxPatch((0.3, 0.5), 5.5, 6.8, boxstyle="round,pad=0.25",
                         ec=C['blue'], fc='#f0f5ff', lw=3)
    ax.add_patch(r1)
    # 3D tab effect
    ax.add_patch(FancyBboxPatch((0.3, 7.0), 2.0, 0.5, boxstyle="round,pad=0.08",
                 ec=C['blue'], fc=C['blue'], lw=2))
    ax.text(1.3, 7.25, '«device»', fontsize=7, color='white', style='italic')
    ax.text(3.05, 7.0, 'Client Browser', fontsize=12, fontweight='bold', color=C['blue'])

    client_items = [
        ('HTML5 / CSS3 / JS', C['gray']),
        ('TensorFlow.js (LSTM-TCN)', C['purple']),
        ('MediaPipe Holistic (WASM)', C['orange']),
        ('Three.js (3D Sign Avatar)', C['teal']),
        ('Web Speech API (STT)', C['green']),
        ('sign.js + speech.js', C['blue']),
    ]
    for i, (label, color) in enumerate(client_items):
        y = 6.0 - i * 0.85
        r = FancyBboxPatch((0.8, y-0.25), 4.5, 0.55, boxstyle="round,pad=0.08",
                            ec=color, fc='white', lw=1.5)
        ax.add_patch(r)
        ax.text(3.05, y, label, ha='center', va='center', fontsize=8.5, color='#333')

    # Server node
    r2 = FancyBboxPatch((8.2, 0.5), 5.5, 6.8, boxstyle="round,pad=0.25",
                         ec=C['green'], fc='#f0fff0', lw=3)
    ax.add_patch(r2)
    ax.add_patch(FancyBboxPatch((8.2, 7.0), 2.0, 0.5, boxstyle="round,pad=0.08",
                 ec=C['green'], fc=C['green'], lw=2))
    ax.text(9.2, 7.25, '«cloud»', fontsize=7, color='white', style='italic')
    ax.text(10.95, 7.0, 'Render Server', fontsize=12, fontweight='bold', color=C['green'])

    server_items = [
        ('Flask App (app.py + Blueprints)', C['green']),
        ('sign.py — Gesture Pipeline', C['blue']),
        ('speech.py — Speech Pipeline', C['orange']),
        ('grammar_helper.py — ISL Rules', C['purple']),
        ('SQLite DB (Users, Translations)', C['red']),
        ('ML Models (LSTM, iSign Index)', C['teal']),
    ]
    for i, (label, color) in enumerate(server_items):
        y = 6.0 - i * 0.85
        r = FancyBboxPatch((8.7, y-0.25), 4.5, 0.55, boxstyle="round,pad=0.08",
                            ec=color, fc='white', lw=1.5)
        ax.add_patch(r)
        ax.text(10.95, y, label, ha='center', va='center', fontsize=8.5, color='#333')

    # Connection
    ax.annotate('', xy=(8.2, 4.2), xytext=(5.8, 4.2),
                arrowprops=dict(arrowstyle='<->', lw=3.5, color=C['amber']))
    ax.text(7.0, 4.7, 'HTTPS', ha='center', fontsize=10, fontweight='bold', color=C['amber'])
    ax.text(7.0, 4.0, 'REST API\nWebSocket', ha='center', fontsize=8, color=C['amber'])

    save(fig, 'deployment_diagram')


# ══════════════════════════════════════════════════
# RUN ALL
# ══════════════════════════════════════════════════
print("Generating improved diagrams v2...")
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
