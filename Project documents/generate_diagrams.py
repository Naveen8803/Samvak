"""
Generate all UML and DFD diagrams as PNG images using matplotlib.
These are then embedded into the Word document.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

OUT_DIR = r"E:\sam\Project documents\diagrams"
os.makedirs(OUT_DIR, exist_ok=True)

def save(fig, name):
    path = os.path.join(OUT_DIR, f"{name}.png")
    fig.savefig(path, dpi=180, bbox_inches='tight', facecolor='white', pad_inches=0.3)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


# ═══════════════════════════════════════════════════════════════
# 1. USE CASE DIAGRAM
# ═══════════════════════════════════════════════════════════════
def draw_use_case():
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Use Case Diagram — Saṁvāk Sign Language Translator', fontsize=14, fontweight='bold', pad=15)

    # System boundary
    rect = FancyBboxPatch((3.5, 0.3), 10, 9.2, boxstyle="round,pad=0.3",
                           edgecolor='#333', facecolor='#f8f9fa', linewidth=2)
    ax.add_patch(rect)
    ax.text(8.5, 9.7, 'Saṁvāk System', ha='center', fontsize=11, fontweight='bold', color='#333')

    # Actor
    ax.plot(1.5, 6.0, 'o', markersize=18, color='#2196F3', markeredgecolor='#1565C0', markeredgewidth=2)
    ax.plot([1.5, 1.5], [5.6, 4.6], color='#1565C0', linewidth=2)
    ax.plot([1.0, 2.0], [5.2, 5.2], color='#1565C0', linewidth=2)
    ax.plot([1.5, 1.0], [4.6, 3.8], color='#1565C0', linewidth=2)
    ax.plot([1.5, 2.0], [4.6, 3.8], color='#1565C0', linewidth=2)
    ax.text(1.5, 3.4, 'User', ha='center', fontsize=10, fontweight='bold')

    # Use cases
    use_cases = [
        (6.0, 8.8, 'Register / Login'),
        (6.0, 7.6, 'Sign-to-Text Translation'),
        (6.0, 6.4, 'Speech-to-Sign Translation'),
        (6.0, 5.2, 'Browse ISL Dictionary'),
        (6.0, 4.0, 'Learn ISL Signs'),
        (6.0, 2.8, 'View Dashboard'),
        (6.0, 1.6, 'View Translation History'),
        (6.0, 0.6, 'Update Settings / Preferences'),
    ]

    for x, y, label in use_cases:
        ellipse = mpatches.Ellipse((x, y), 3.8, 0.85, edgecolor='#1565C0',
                                    facecolor='#E3F2FD', linewidth=1.5)
        ax.add_patch(ellipse)
        ax.text(x, y, label, ha='center', va='center', fontsize=7.5, fontweight='bold')
        ax.annotate('', xy=(x - 1.9, y), xytext=(2.2, 5.0),
                    arrowprops=dict(arrowstyle='-', color='#666', lw=1))

    # Sub use cases for Sign-to-Text
    sub_sign = [
        (10.5, 8.5, 'Capture Gesture\n(Webcam)'),
        (10.5, 7.6, 'Detect Landmarks\n(MediaPipe)'),
        (10.5, 6.7, 'Classify ISL Phrase\n(LSTM-TCN)'),
    ]
    for x, y, label in sub_sign:
        ellipse = mpatches.Ellipse((x, y), 3.0, 0.7, edgecolor='#43A047',
                                    facecolor='#E8F5E9', linewidth=1.2)
        ax.add_patch(ellipse)
        ax.text(x, y, label, ha='center', va='center', fontsize=6.5)
        ax.annotate('', xy=(x - 1.5, y), xytext=(7.9, 7.6),
                    arrowprops=dict(arrowstyle='-', color='#aaa', lw=0.8, linestyle='dashed'))

    # Sub use cases for Speech-to-Sign
    sub_speech = [
        (10.5, 5.6, 'Transcribe Speech\n(STT)'),
        (10.5, 4.7, 'Apply ISL Grammar\nRules'),
        (10.5, 3.8, 'Animate 3D Avatar\n(Three.js)'),
    ]
    for x, y, label in sub_speech:
        ellipse = mpatches.Ellipse((x, y), 3.0, 0.7, edgecolor='#F57C00',
                                    facecolor='#FFF3E0', linewidth=1.2)
        ax.add_patch(ellipse)
        ax.text(x, y, label, ha='center', va='center', fontsize=6.5)
        ax.annotate('', xy=(x - 1.5, y), xytext=(7.9, 6.4),
                    arrowprops=dict(arrowstyle='-', color='#aaa', lw=0.8, linestyle='dashed'))

    # Legend
    ax.text(10.5, 2.4, '<<include>>', ha='center', fontsize=7, style='italic', color='#666')
    ax.plot([9.5, 11.5], [2.2, 2.2], '--', color='#aaa', lw=0.8)

    return save(fig, 'use_case_diagram')


# ═══════════════════════════════════════════════════════════════
# 2. CLASS DIAGRAM
# ═══════════════════════════════════════════════════════════════
def draw_class_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('Class Diagram — Saṁvāk Data Model', fontsize=14, fontweight='bold', pad=15)

    def draw_class(ax, x, y, w, h, name, attrs, methods, color='#E3F2FD', edge='#1565C0'):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                               edgecolor=edge, facecolor=color, linewidth=1.5)
        ax.add_patch(rect)
        # Class name
        ax.fill_between([x, x+w], y+h-0.45, y+h, color=edge, alpha=0.2)
        ax.text(x + w/2, y + h - 0.25, name, ha='center', va='center',
                fontsize=9, fontweight='bold')
        # Separator
        ax.plot([x, x+w], [y+h-0.45, y+h-0.45], color=edge, lw=1)
        # Attributes
        for i, attr in enumerate(attrs):
            ax.text(x + 0.15, y + h - 0.7 - i*0.28, attr, fontsize=6.5, family='monospace')
        sep_y = y + h - 0.55 - len(attrs)*0.28
        ax.plot([x, x+w], [sep_y, sep_y], color=edge, lw=0.8)
        # Methods
        for i, method in enumerate(methods):
            ax.text(x + 0.15, sep_y - 0.25 - i*0.28, method, fontsize=6.5, family='monospace')

    # User class
    draw_class(ax, 1, 5.5, 3.5, 3.5, 'User',
               ['+ id: Integer [PK]', '+ username: String [UK]', '+ email: String [UK]',
                '+ password_hash: String'],
               ['+ translations: List', '+ preferences: UserPref', '+ progress: List'],
               '#E3F2FD', '#1565C0')

    # Translation class
    draw_class(ax, 6, 7, 3.8, 3.0, 'Translation',
               ['+ id: Integer [PK]', '+ user_id: Integer [FK]', '+ source_type: String',
                '+ input_text: Text', '+ output_text: Text', '+ timestamp: DateTime'],
               ['+ to_dict(): dict'],
               '#E8F5E9', '#43A047')

    # UserPreference class
    draw_class(ax, 6, 3.5, 3.8, 3.0, 'UserPreference',
               ['+ id: Integer [PK]', '+ user_id: Integer [FK]',
                '+ sign_input_language: String', '+ sign_output_language: String',
                '+ speech_input_language: String'],
               ['+ to_dict(): dict', '+ default_payload(): dict'],
               '#FFF3E0', '#F57C00')

    # UserProgress class
    draw_class(ax, 6, 0.3, 3.8, 2.6, 'UserProgress',
               ['+ id: Integer [PK]', '+ user_id: Integer [FK]',
                '+ word: String', '+ points: Integer', '+ timestamp: DateTime'],
               [],
               '#FCE4EC', '#C62828')

    # GeometryClassifier class
    draw_class(ax, 11.5, 6.5, 3.8, 3.0, 'GeometryClassifier',
               ['+ last_prediction: String', '+ MIN_CONFIDENCE: Float'],
               ['+ predict(landmarks)', '+ predict_with_metadata()', '- _analyze_frame()',
                '- _basic_static_candidates()', '- _dynamic_candidates()'],
               '#F3E5F5', '#7B1FA2')

    # GrammarHelper class
    draw_class(ax, 11.5, 2.8, 3.8, 3.0, 'GrammarHelper',
               ['- _DROP_WORDS: Set', '- _WH_WORDS: Set', '- _TIME_MARKERS: Set'],
               ['+ english_to_isl_glosses()', '+ gloss_to_english()',
                '- _apply_isl_grammar()', '- _expand_contractions()'],
               '#E0F7FA', '#00838F')

    # Relationships
    # User -> Translation (1 to many)
    ax.annotate('', xy=(6, 8.5), xytext=(4.5, 7.5),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.5))
    ax.text(5.2, 8.3, '1..*', fontsize=8, fontweight='bold')

    # User -> UserPreference (1 to 1)
    ax.annotate('', xy=(6, 5.0), xytext=(4.5, 6.5),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.5))
    ax.text(5.2, 5.5, '1..1', fontsize=8, fontweight='bold')

    # User -> UserProgress (1 to many)
    ax.annotate('', xy=(6, 1.8), xytext=(3.0, 5.5),
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.5))
    ax.text(4.0, 3.2, '1..*', fontsize=8, fontweight='bold')

    return save(fig, 'class_diagram')


# ═══════════════════════════════════════════════════════════════
# 3. ACTIVITY DIAGRAM - Sign Recognition
# ═══════════════════════════════════════════════════════════════
def draw_activity_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(12, 14))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 14)
    ax.axis('off')
    ax.set_title('Activity Diagram — Sign-to-Text Recognition Flow', fontsize=14, fontweight='bold', pad=15)

    def activity_box(x, y, text, color='#E3F2FD', edge='#1565C0', w=3.5, h=0.7):
        rect = FancyBboxPatch((x - w/2, y - h/2), w, h, boxstyle="round,pad=0.15",
                               edgecolor=edge, facecolor=color, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x, y, text, ha='center', va='center', fontsize=8, fontweight='bold')

    def diamond(x, y, text, color='#FFF9C4', edge='#F9A825'):
        diamond_pts = [[x, y+0.5], [x+1.2, y], [x, y-0.5], [x-1.2, y]]
        from matplotlib.patches import Polygon
        d = Polygon(diamond_pts, closed=True, edgecolor=edge, facecolor=color, linewidth=1.5)
        ax.add_patch(d)
        ax.text(x, y, text, ha='center', va='center', fontsize=7, fontweight='bold')

    def arrow(x1, y1, x2, y2, label=''):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color='#555', lw=1.5))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx + 0.15, my, label, fontsize=7, color='#333', style='italic')

    # Start
    ax.plot(6, 13.5, 'o', markersize=15, color='#333')
    arrow(6, 13.3, 6, 12.8)

    activity_box(6, 12.5, 'Open Webcam')
    arrow(6, 12.15, 6, 11.6)

    activity_box(6, 11.3, 'Capture Video Frame')
    arrow(6, 10.95, 6, 10.4)

    diamond(6, 10.0, 'Hand\nDetected?')
    arrow(6, 9.5, 6, 8.9)
    ax.text(6.15, 9.65, 'Yes', fontsize=7, color='green')
    # No loop back
    ax.annotate('', xy=(3.5, 11.3), xytext=(4.8, 10.0),
                arrowprops=dict(arrowstyle='->', color='#999', lw=1, connectionstyle="arc3,rad=0.3"))
    ax.text(3.6, 10.5, 'No', fontsize=7, color='red')

    activity_box(6, 8.6, 'Extract Landmarks\n(MediaPipe Holistic)', color='#E8F5E9', edge='#43A047')
    arrow(6, 8.25, 6, 7.7)

    activity_box(6, 7.4, 'Append to Frame Buffer')
    arrow(6, 7.05, 6, 6.5)

    diamond(6, 6.1, 'Buffer = 30\nframes?')
    ax.annotate('', xy=(3.5, 11.3), xytext=(4.8, 6.1),
                arrowprops=dict(arrowstyle='->', color='#999', lw=1, connectionstyle="arc3,rad=0.4"))
    ax.text(3.8, 8.5, 'No', fontsize=7, color='red')
    arrow(6, 5.6, 6, 5.1)
    ax.text(6.15, 5.3, 'Yes', fontsize=7, color='green')

    activity_box(6, 4.8, 'Run LSTM-TCN Prediction', color='#F3E5F5', edge='#7B1FA2')
    arrow(6, 4.45, 6, 3.9)

    diamond(6, 3.5, 'Confidence\n≥ Threshold?')
    arrow(6, 3.0, 6, 2.5)
    ax.text(6.15, 2.7, 'Yes', fontsize=7, color='green')

    # No -> Geometry fallback
    ax.annotate('', xy=(9.5, 3.5), xytext=(7.2, 3.5),
                arrowprops=dict(arrowstyle='->', color='#999', lw=1))
    ax.text(7.5, 3.7, 'No', fontsize=7, color='red')
    activity_box(9.5, 3.5, 'Geometry\nClassifier\nFallback', w=2.5, h=0.9, color='#FCE4EC', edge='#C62828')

    activity_box(6, 2.2, 'Display Recognized Sign', color='#C8E6C9', edge='#2E7D32')
    arrow(6, 1.85, 6, 1.3)

    activity_box(6, 1.0, 'Translate to Target Language')
    arrow(6, 0.65, 6, 0.1, '')

    # End
    ax.plot(6, -0.15, 'o', markersize=15, color='#333')
    ax.plot(6, -0.15, 'o', markersize=10, color='white')
    ax.plot(6, -0.15, 'o', markersize=8, color='#333')

    return save(fig, 'activity_diagram')


# ═══════════════════════════════════════════════════════════════
# 4. DFD LEVEL 0 (Context Diagram)
# ═══════════════════════════════════════════════════════════════
def draw_dfd_level0():
    fig, ax = plt.subplots(1, 1, figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis('off')
    ax.set_title('DFD Level 0 — Context Diagram', fontsize=14, fontweight='bold', pad=15)

    # External entity - User
    rect = FancyBboxPatch((0.5, 2.5), 2.5, 2, boxstyle="round,pad=0.1",
                           edgecolor='#1565C0', facecolor='#E3F2FD', linewidth=2)
    ax.add_patch(rect)
    ax.text(1.75, 3.5, 'USER', ha='center', va='center', fontsize=12, fontweight='bold')

    # System
    circle = plt.Circle((6.5, 3.5), 2.2, edgecolor='#2E7D32', facecolor='#E8F5E9', linewidth=2.5)
    ax.add_patch(circle)
    ax.text(6.5, 3.8, 'SAṀVĀK', ha='center', va='center', fontsize=12, fontweight='bold')
    ax.text(6.5, 3.2, 'Sign Language\nTranslator', ha='center', va='center', fontsize=9)

    # Arrows with labels
    ax.annotate('', xy=(4.3, 4.3), xytext=(3.0, 4.3),
                arrowprops=dict(arrowstyle='->', lw=2, color='#1565C0'))
    ax.text(3.5, 4.7, 'Video Frames\nVoice / Text\nCredentials', fontsize=7, ha='center', color='#1565C0')

    ax.annotate('', xy=(3.0, 2.7), xytext=(4.3, 2.7),
                arrowprops=dict(arrowstyle='->', lw=2, color='#C62828'))
    ax.text(3.5, 2.0, 'Recognized Text\nSpeech Output\nAvatar Animation\nDashboard', fontsize=7, ha='center', color='#C62828')

    # Database
    rect2 = FancyBboxPatch((9.5, 2.5), 2, 2, boxstyle="round,pad=0.1",
                            edgecolor='#F57C00', facecolor='#FFF3E0', linewidth=2)
    ax.add_patch(rect2)
    ax.text(10.5, 3.5, 'SQLite\nDatabase', ha='center', va='center', fontsize=10, fontweight='bold')

    ax.annotate('', xy=(9.5, 3.8), xytext=(8.7, 3.8),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#F57C00'))
    ax.annotate('', xy=(8.7, 3.2), xytext=(9.5, 3.2),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#F57C00'))
    ax.text(9.1, 4.2, 'Read/Write', fontsize=7, ha='center', color='#F57C00')

    return save(fig, 'dfd_level0')


# ═══════════════════════════════════════════════════════════════
# 5. DFD LEVEL 1
# ═══════════════════════════════════════════════════════════════
def draw_dfd_level1():
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('DFD Level 1 — Major Processes', fontsize=14, fontweight='bold', pad=15)

    # User entity
    rect = FancyBboxPatch((0.3, 4), 2, 2, boxstyle="round,pad=0.1",
                           edgecolor='#1565C0', facecolor='#E3F2FD', linewidth=2)
    ax.add_patch(rect)
    ax.text(1.3, 5, 'USER', ha='center', va='center', fontsize=11, fontweight='bold')

    # Processes
    processes = [
        (6, 8.5, '1.0', 'Sign-to-Text\nModule', '#E8F5E9', '#2E7D32'),
        (6, 6.5, '2.0', 'Speech-to-Sign\nModule', '#FFF3E0', '#F57C00'),
        (6, 4.5, '3.0', 'Dictionary\nModule', '#F3E5F5', '#7B1FA2'),
        (6, 2.5, '4.0', 'Learning\nModule', '#E0F7FA', '#00838F'),
        (6, 0.7, '5.0', 'Auth\nModule', '#FCE4EC', '#C62828'),
    ]

    for x, y, num, label, color, edge in processes:
        circle = plt.Circle((x, y), 0.9, edgecolor=edge, facecolor=color, linewidth=2)
        ax.add_patch(circle)
        ax.text(x, y + 0.2, num, ha='center', va='center', fontsize=8, fontweight='bold', color=edge)
        ax.text(x, y - 0.2, label, ha='center', va='center', fontsize=7)

        ax.annotate('', xy=(x - 0.9, y), xytext=(2.3, 5),
                    arrowprops=dict(arrowstyle='->', lw=1.2, color='#666'))

    # Data stores on right
    stores = [
        (11, 8.5, 'D1', 'LSTM Model\n+ iSign Index'),
        (11, 6.5, 'D2', 'Grammar Rules\n+ Sign Tokens'),
        (11, 4.5, 'D3', 'ISL CSLRT\nCorpus'),
        (11, 2.5, 'D4', 'User Progress\nXP Data'),
        (11, 0.7, 'D5', 'SQLite DB\n(Users, etc.)'),
    ]

    for x, y, did, label in stores:
        ax.plot([x - 1.2, x + 1.2], [y + 0.35, y + 0.35], color='#333', lw=1.5)
        ax.plot([x - 1.2, x - 1.2], [y + 0.35, y - 0.35], color='#333', lw=1.5)
        ax.plot([x - 1.2, x + 1.2], [y - 0.35, y - 0.35], color='#333', lw=1.5)
        ax.fill_between([x - 1.2, x + 1.2], y - 0.35, y + 0.35, color='#f5f5f5')
        ax.text(x - 1.0, y, did, fontsize=7, fontweight='bold')
        ax.text(x + 0.1, y, label, ha='center', va='center', fontsize=6.5)

    # Connect processes to stores
    for i, (px, py, _, _, _, edge) in enumerate(processes):
        sx = stores[i][0]
        sy = stores[i][1]
        ax.annotate('', xy=(sx - 1.2, sy), xytext=(px + 0.9, py),
                    arrowprops=dict(arrowstyle='->', lw=1, color='#999'))

    return save(fig, 'dfd_level1')


# ═══════════════════════════════════════════════════════════════
# 6. DFD LEVEL 2 - Sign-to-Text Detail
# ═══════════════════════════════════════════════════════════════
def draw_dfd_level2():
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6)
    ax.axis('off')
    ax.set_title('DFD Level 2 — Sign-to-Text Module Detail', fontsize=14, fontweight='bold', pad=15)

    steps = [
        (1.5, 3, '2.1', 'Capture\nFrame'),
        (3.5, 3, '2.2', 'MediaPipe\nLandmarks'),
        (5.5, 3, '2.3', 'Build\nWindow'),
        (7.5, 3, '2.4', 'LSTM-TCN\nClassify'),
        (9.5, 3, '2.5', 'Translate\nLanguage'),
        (11.5, 3, '2.6', 'TTS\nOutput'),
    ]

    colors = ['#E3F2FD', '#E8F5E9', '#FFF3E0', '#F3E5F5', '#E0F7FA', '#FCE4EC']
    edges = ['#1565C0', '#2E7D32', '#F57C00', '#7B1FA2', '#00838F', '#C62828']

    for i, (x, y, num, label) in enumerate(steps):
        circle = plt.Circle((x, y), 0.7, edgecolor=edges[i], facecolor=colors[i], linewidth=2)
        ax.add_patch(circle)
        ax.text(x, y + 0.15, num, ha='center', fontsize=7, fontweight='bold', color=edges[i])
        ax.text(x, y - 0.2, label, ha='center', fontsize=6.5)

        if i > 0:
            px = steps[i-1][0]
            ax.annotate('', xy=(x - 0.7, y), xytext=(px + 0.7, y),
                        arrowprops=dict(arrowstyle='->', lw=1.5, color='#555'))

    # Data flow labels
    labels = ['Video\nFrame', '258D\nVector', '30-Frame\nBuffer', 'ISL Phrase\n+ Conf.', 'Translated\nText', 'Speech\nAudio']
    for i, lbl in enumerate(labels):
        x = steps[i][0]
        ax.text(x, 1.8, lbl, ha='center', fontsize=6.5, color='#666', style='italic')

    # External entities
    ax.text(0.3, 3, 'Camera\nInput', ha='center', fontsize=8, fontweight='bold', color='#1565C0',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#E3F2FD', edgecolor='#1565C0'))
    ax.annotate('', xy=(0.8, 3), xytext=(0.3, 3),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#1565C0'))

    ax.text(13, 3, 'User\nOutput', ha='center', fontsize=8, fontweight='bold', color='#C62828',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#FCE4EC', edgecolor='#C62828'))
    ax.annotate('', xy=(12.5, 3), xytext=(12.2, 3),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#C62828'))

    # Geometry fallback
    ax.text(7.5, 5.0, 'Geometry\nFallback', ha='center', fontsize=7,
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFF9C4', edgecolor='#F9A825'))
    ax.annotate('', xy=(7.5, 4.5), xytext=(7.5, 3.7),
                arrowprops=dict(arrowstyle='<->', lw=1, color='#F9A825', linestyle='dashed'))

    # DB store
    ax.text(11.5, 5.0, 'Translation\nHistory DB', ha='center', fontsize=7,
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#f5f5f5', edgecolor='#333'))
    ax.annotate('', xy=(11.5, 4.5), xytext=(11.5, 3.7),
                arrowprops=dict(arrowstyle='->', lw=1, color='#333', linestyle='dashed'))

    return save(fig, 'dfd_level2')


# ═══════════════════════════════════════════════════════════════
# 7. ER Diagram
# ═══════════════════════════════════════════════════════════════
def draw_er_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis('off')
    ax.set_title('ER Diagram — Saṁvāk Database Schema', fontsize=14, fontweight='bold', pad=15)

    def entity_box(x, y, name, attrs, pk_count=1, w=3.2, color='#E3F2FD', edge='#1565C0'):
        h = 0.5 + len(attrs) * 0.32
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                               edgecolor=edge, facecolor='white', linewidth=2)
        ax.add_patch(rect)
        # Header
        ax.fill_between([x, x+w], y+h-0.45, y+h, color=color)
        ax.text(x + w/2, y + h - 0.25, name, ha='center', va='center',
                fontsize=10, fontweight='bold')
        ax.plot([x, x+w], [y+h-0.45, y+h-0.45], color=edge, lw=1.5)
        # Attributes
        for i, attr in enumerate(attrs):
            prefix = '🔑 ' if i < pk_count else '   '
            ax.text(x + 0.15, y + h - 0.7 - i*0.32, prefix + attr, fontsize=7, family='monospace')

    # USERS
    entity_box(0.5, 4, 'USERS',
               ['id INTEGER PK', 'username VARCHAR UK', 'email VARCHAR UK', 'password_hash VARCHAR'],
               pk_count=1, color='#E3F2FD', edge='#1565C0')

    # TRANSLATIONS
    entity_box(5.5, 5.5, 'TRANSLATIONS',
               ['id INTEGER PK', 'user_id INTEGER FK', 'source_type VARCHAR',
                'input_text TEXT', 'output_text TEXT', 'timestamp DATETIME'],
               pk_count=1, color='#E8F5E9', edge='#2E7D32')

    # USER_PREFERENCES
    entity_box(5.5, 2.5, 'USER_PREFERENCES',
               ['id INTEGER PK', 'user_id INTEGER FK UK',
                'sign_input_language VARCHAR', 'sign_output_language VARCHAR',
                'speech_input_language VARCHAR', 'speech_sign_language VARCHAR'],
               pk_count=1, color='#FFF3E0', edge='#F57C00')

    # USER_PROGRESS
    entity_box(10, 5.5, 'USER_PROGRESS',
               ['id INTEGER PK', 'user_id INTEGER FK',
                'word VARCHAR', 'points INTEGER', 'timestamp DATETIME'],
               pk_count=1, color='#F3E5F5', edge='#7B1FA2')

    # CONTACT_MESSAGES
    entity_box(10, 2.5, 'CONTACT_MESSAGES',
               ['id INTEGER PK', 'name VARCHAR', 'email VARCHAR',
                'message TEXT', 'timestamp DATETIME'],
               pk_count=1, color='#FCE4EC', edge='#C62828')

    # Relationships
    # Users -> Translations (1:N)
    ax.annotate('', xy=(5.5, 6.5), xytext=(3.7, 5.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))
    ax.text(4.3, 6.3, '1 : N', fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#fff', edgecolor='#333'))

    # Users -> Preferences (1:1)
    ax.annotate('', xy=(5.5, 4.0), xytext=(3.7, 4.8),
                arrowprops=dict(arrowstyle='->', lw=2, color='#333'))
    ax.text(4.3, 4.0, '1 : 1', fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#fff', edgecolor='#333'))

    # Users -> Progress (1:N)
    ax.annotate('', xy=(10, 6.5), xytext=(3.7, 5.2),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='#333', connectionstyle="arc3,rad=-0.2"))
    ax.text(7, 7.2, '1 : N', fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#fff', edgecolor='#333'))

    return save(fig, 'er_diagram')


# ═══════════════════════════════════════════════════════════════
# 8. DEPLOYMENT DIAGRAM
# ═══════════════════════════════════════════════════════════════
def draw_deployment_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(14, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.axis('off')
    ax.set_title('Deployment Diagram — Saṁvāk System', fontsize=14, fontweight='bold', pad=15)

    # Client node
    rect1 = FancyBboxPatch((0.5, 1), 5, 5, boxstyle="round,pad=0.2",
                            edgecolor='#1565C0', facecolor='#E3F2FD', linewidth=2.5)
    ax.add_patch(rect1)
    ax.text(3, 5.6, '<<device>>', ha='center', fontsize=8, style='italic', color='#666')
    ax.text(3, 5.2, 'Client Browser', ha='center', fontsize=11, fontweight='bold')

    components_client = [
        (3, 4.3, 'HTML5 / CSS3 / JavaScript'),
        (3, 3.6, 'TensorFlow.js (LSTM Model)'),
        (3, 2.9, 'MediaPipe (WASM)'),
        (3, 2.2, 'Three.js (3D Avatar)'),
        (3, 1.5, 'Web Speech API'),
    ]
    for x, y, label in components_client:
        r = FancyBboxPatch((x - 2, y - 0.25), 4, 0.5, boxstyle="round,pad=0.08",
                            edgecolor='#1565C0', facecolor='white', linewidth=1)
        ax.add_patch(r)
        ax.text(x, y, label, ha='center', va='center', fontsize=8)

    # Server node
    rect2 = FancyBboxPatch((8, 1), 5.5, 5, boxstyle="round,pad=0.2",
                            edgecolor='#2E7D32', facecolor='#E8F5E9', linewidth=2.5)
    ax.add_patch(rect2)
    ax.text(10.75, 5.6, '<<cloud>>', ha='center', fontsize=8, style='italic', color='#666')
    ax.text(10.75, 5.2, 'Render Cloud Server', ha='center', fontsize=11, fontweight='bold')

    components_server = [
        (10.75, 4.3, 'Flask App (app.py)'),
        (10.75, 3.6, 'sign.py + speech.py'),
        (10.75, 2.9, 'grammar_helper.py'),
        (10.75, 2.2, 'SQLite Database'),
        (10.75, 1.5, 'ML Models (LSTM, TCN)'),
    ]
    for x, y, label in components_server:
        r = FancyBboxPatch((x - 2.2, y - 0.25), 4.4, 0.5, boxstyle="round,pad=0.08",
                            edgecolor='#2E7D32', facecolor='white', linewidth=1)
        ax.add_patch(r)
        ax.text(x, y, label, ha='center', va='center', fontsize=8)

    # Connection
    ax.annotate('', xy=(8, 3.5), xytext=(5.5, 3.5),
                arrowprops=dict(arrowstyle='<->', lw=2.5, color='#F57C00'))
    ax.text(6.75, 3.9, 'HTTPS\nREST API / WebSocket', ha='center', fontsize=8,
            fontweight='bold', color='#F57C00')

    return save(fig, 'deployment_diagram')


# ═══════════════════════════════════════════════════════════════
# RUN ALL
# ═══════════════════════════════════════════════════════════════
print("Generating diagrams...")
draw_use_case()
draw_class_diagram()
draw_activity_diagram()
draw_dfd_level0()
draw_dfd_level1()
draw_dfd_level2()
draw_er_diagram()
draw_deployment_diagram()
print(f"\nAll diagrams saved to: {OUT_DIR}")
print(f"Files: {os.listdir(OUT_DIR)}")
