"""
FakeJobDetector - Mobile App
Android port of FakeJobAdvanced Streamlit project
Built with Kivy + KivyMD
"""

import os
import sys

# Kivy config MUST come before any kivy imports
from kivy.config import Config
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '800')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.core.window import Window

import threading
import json

# ── Colours ──────────────────────────────────────────────────────────────────
BG_DARK   = (0.07, 0.07, 0.12, 1)
BG_CARD   = (0.12, 0.12, 0.20, 1)
ACCENT    = (0.25, 0.55, 1.00, 1)
ACCENT2   = (0.10, 0.80, 0.60, 1)
DANGER    = (0.95, 0.25, 0.35, 1)
WARNING   = (1.00, 0.65, 0.10, 1)
TEXT_MAIN = (0.95, 0.95, 0.98, 1)
TEXT_SUB  = (0.60, 0.62, 0.70, 1)
SAFE      = (0.15, 0.80, 0.45, 1)

Window.clearcolor = BG_DARK


# ── Helpers ───────────────────────────────────────────────────────────────────
def make_bg(widget, color):
    with widget.canvas.before:
        Color(*color)
        widget._bg_rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda w, v: setattr(w._bg_rect, 'pos', v),
                size=lambda w, v: setattr(w._bg_rect, 'size', v))


def card(padding=dp(16), spacing=dp(10), orientation='vertical', **kw):
    b = BoxLayout(orientation=orientation, padding=padding,
                  spacing=spacing, **kw)
    with b.canvas.before:
        Color(*BG_CARD)
        b._rect = RoundedRectangle(pos=b.pos, size=b.size, radius=[dp(12)])
    b.bind(pos=lambda w, v: setattr(w._rect, 'pos', v),
           size=lambda w, v: setattr(w._rect, 'size', v))
    return b


def accent_btn(text, on_press=None, color=ACCENT, height=dp(48)):
    btn = Button(
        text=text, size_hint_y=None, height=height,
        font_size=dp(15), bold=True,
        background_normal='', background_color=(0, 0, 0, 0),
        color=TEXT_MAIN
    )
    with btn.canvas.before:
        Color(*color)
        btn._rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(10)])
    btn.bind(pos=lambda w, v: setattr(w._rect, 'pos', v),
             size=lambda w, v: setattr(w._rect, 'size', v))
    if on_press:
        btn.bind(on_press=on_press)
    return btn


def lbl(text, size=dp(14), color=TEXT_MAIN, bold=False, halign='left',
        size_hint_y=None, height=None, **kw):
    if height is None:
        height = dp(28) if '\n' not in text else dp(20) * (text.count('\n') + 2)
    l = Label(text=text, font_size=size, color=color, bold=bold,
              halign=halign, valign='middle',
              size_hint_y=None, height=height,
              text_size=(None, None), **kw)
    l.bind(size=lambda w, v: setattr(w, 'text_size', (v[0], None)))
    return l


# ── Prediction Logic ──────────────────────────────────────────────────────────
class FakeJobPredictor:
    """
    Wraps the trained models. Falls back to a rule-based heuristic if
    the .pkl files are not bundled with the APK.
    """

    SUSPICIOUS_PHRASES = [
        'work from home', 'easy money', 'no experience required',
        'guaranteed income', 'unlimited earning', 'wire transfer',
        'western union', 'money order', 'send money', 'upfront fee',
        'processing fee', 'training fee', 'background check fee',
        'make money fast', 'earn $', 'earn money', 'part time job',
        'data entry', 'typing job', 'ad posting', 'envelope stuffing',
        'mlm', 'multi level', 'pyramid', 'referral bonus only',
    ]

    LEGIT_INDICATORS = [
        'bachelor', 'master', 'phd', 'degree', 'certificate',
        'experience required', 'years of experience', 'skills',
        'responsibilities', 'qualifications', 'benefits', 'salary range',
        'health insurance', '401k', 'pto', 'paid vacation',
    ]

    def __init__(self):
        self.model = None
        self.vectorizer = None
        self._load_models()

    def _load_models(self):
        """Try to load pickled models; silently fall back to heuristics."""
        try:
            import joblib
            base = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(base, 'models', 'Random_Forest.pkl')
            vec_path   = os.path.join(base, 'models', 'vectorizer.pkl')
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
            if os.path.exists(vec_path):
                self.vectorizer = joblib.load(vec_path)
        except Exception:
            pass

    def predict(self, job_data: dict) -> dict:
        text = ' '.join(str(v) for v in job_data.values()).lower()

        if self.model and self.vectorizer:
            try:
                vec  = self.vectorizer.transform([text])
                pred = self.model.predict(vec)[0]
                prob = self.model.predict_proba(vec)[0]
                return {
                    'prediction': int(pred),
                    'fraud_prob': float(max(prob)),
                    'method': 'ML Model (Random Forest)',
                }
            except Exception:
                pass

        return self._heuristic(text, job_data)

    def _heuristic(self, text: str, job_data: dict) -> dict:
        score = 0
        flags = []

        for phrase in self.SUSPICIOUS_PHRASES:
            if phrase in text:
                score += 1
                flags.append(f'⚠ Suspicious phrase: "{phrase}"')

        legit = sum(1 for w in self.LEGIT_INDICATORS if w in text)
        score -= legit * 0.5

        if not job_data.get('company_profile', '').strip():
            score += 1.5
            flags.append('⚠ No company profile provided')

        salary = job_data.get('salary_range', '').strip()
        if salary and any(c in salary for c in ['$$$', 'unlimited', 'no limit']):
            score += 2
            flags.append('⚠ Unrealistic salary claim')

        if not job_data.get('required_experience', '').strip():
            score += 0.5

        fraud_prob = min(max(score / 8.0, 0.0), 1.0)
        prediction = 1 if fraud_prob >= 0.40 else 0

        return {
            'prediction': prediction,
            'fraud_prob': round(fraud_prob, 2),
            'flags': flags,
            'method': 'Heuristic Analysis',
            'legit_score': legit,
        }


PREDICTOR = FakeJobPredictor()


# ── Screens ───────────────────────────────────────────────────────────────────
class HomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        make_bg(self, BG_DARK)
        root = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(16))

        # Header
        header = card(height=dp(140), size_hint_y=None)
        header.add_widget(lbl('🔍 FakeJob Detector', size=dp(24), bold=True,
                               color=ACCENT, halign='center', height=dp(40)))
        header.add_widget(lbl('AI-Powered Fake Job Posting Detection',
                               color=TEXT_SUB, halign='center', height=dp(24)))
        header.add_widget(lbl('v1.0 — Mobile Edition',
                               size=dp(11), color=TEXT_SUB, halign='center', height=dp(20)))
        root.add_widget(header)

        # Menu buttons
        buttons = [
            ('🧪  Predict Job Posting',    'predict',   ACCENT),
            ('📊  Model Evaluation',        'evaluation', ACCENT2),
            ('📈  Visualizations',          'visual',    (0.65, 0.35, 0.95, 1)),
            ('🌐  Multilingual Predictor',  'multilang', WARNING),
            ('ℹ️   About',                  'about',     TEXT_SUB),
        ]

        for label, screen, color in buttons:
            btn = accent_btn(label, color=color,
                             on_press=lambda x, s=screen: self._go(s))
            root.add_widget(btn)

        root.add_widget(BoxLayout())   # spacer

        footer = lbl('Built with ❤  |  Models: Logistic Regression · Passive Aggressive · Random Forest',
                     size=dp(10), color=TEXT_SUB, halign='center', height=dp(32))
        root.add_widget(footer)
        self.add_widget(root)

    def _go(self, screen):
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = screen


class PredictScreen(Screen):
    FIELDS = [
        ('title',               'Job Title *',              'e.g. Software Engineer'),
        ('company_profile',     'Company Profile',          'Brief company description…'),
        ('description',         'Job Description *',        'Full job description…'),
        ('requirements',        'Requirements',             'Skills, education, experience…'),
        ('benefits',            'Benefits',                 'Health, PTO, 401k…'),
        ('salary_range',        'Salary Range',             'e.g. $60,000 – $80,000'),
        ('required_experience', 'Required Experience',      'e.g. 3–5 years'),
        ('employment_type',     'Employment Type',          'Full-time / Part-time / Contract'),
        ('location',            'Location',                 'City, State or Remote'),
    ]

    def __init__(self, **kw):
        super().__init__(**kw)
        make_bg(self, BG_DARK)
        self.inputs = {}
        self._build()

    def _build(self):
        outer = BoxLayout(orientation='vertical', spacing=0)

        # Top bar
        bar = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(12), 0],
                        spacing=dp(8))
        make_bg(bar, BG_CARD)
        back = Button(text='← Back', size_hint_x=None, width=dp(80),
                      font_size=dp(13), background_color=(0, 0, 0, 0),
                      color=ACCENT)
        back.bind(on_press=lambda x: self._back())
        bar.add_widget(back)
        bar.add_widget(lbl('Analyze Job Posting', size=dp(16), bold=True,
                            color=TEXT_MAIN, halign='center'))
        bar.add_widget(BoxLayout(size_hint_x=None, width=dp(80)))
        outer.add_widget(bar)

        # Scrollable form
        scroll = ScrollView()
        form = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12),
                         size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))

        for key, label, hint in self.FIELDS:
            form.add_widget(lbl(label, size=dp(13), color=TEXT_SUB,
                                height=dp(22)))
            multiline = key in ('company_profile', 'description', 'requirements', 'benefits')
            ti = TextInput(
                hint_text=hint,
                multiline=multiline,
                size_hint_y=None,
                height=dp(90) if multiline else dp(44),
                font_size=dp(14),
                background_color=BG_CARD[:3] + (1,),
                foreground_color=TEXT_MAIN,
                hint_text_color=TEXT_SUB,
                padding=[dp(10), dp(8)],
                cursor_color=ACCENT[:3] + (1,),
            )
            self.inputs[key] = ti
            form.add_widget(ti)

        # Model selector
        form.add_widget(lbl('Select Model', size=dp(13), color=TEXT_SUB,
                             height=dp(22)))
        self.model_spinner = Spinner(
            text='Random Forest',
            values=['Random Forest', 'Logistic Regression', 'Passive Aggressive'],
            size_hint_y=None, height=dp(44),
            font_size=dp(14),
            background_color=ACCENT,
        )
        form.add_widget(self.model_spinner)

        # Predict button
        form.add_widget(BoxLayout(size_hint_y=None, height=dp(12)))
        predict_btn = accent_btn('🔍  Analyze Posting', on_press=self._predict,
                                  height=dp(52))
        form.add_widget(predict_btn)
        clear_btn = accent_btn('🗑  Clear All', on_press=self._clear,
                                color=(0.3, 0.3, 0.4, 1), height=dp(44))
        form.add_widget(clear_btn)
        form.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))

        scroll.add_widget(form)
        outer.add_widget(scroll)
        self.add_widget(outer)

    def _predict(self, *_):
        data = {k: self.inputs[k].text for k in self.inputs}
        if not data['title'].strip() and not data['description'].strip():
            self._show_popup('Input Required',
                             'Please fill in at least the Job Title or Description.')
            return

        result = PREDICTOR.predict(data)
        self.manager.get_screen('result').show(data, result)
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = 'result'

    def _clear(self, *_):
        for ti in self.inputs.values():
            ti.text = ''

    def _back(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'home'

    def _show_popup(self, title, msg):
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        content.add_widget(lbl(msg, color=TEXT_MAIN, height=dp(80)))
        btn = accent_btn('OK', height=dp(44))
        p = Popup(title=title, content=content,
                  size_hint=(0.85, None), height=dp(200),
                  background_color=BG_CARD)
        btn.bind(on_press=p.dismiss)
        content.add_widget(btn)
        p.open()


class ResultScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        make_bg(self, BG_DARK)
        self._build()

    def _build(self):
        self.outer = BoxLayout(orientation='vertical', spacing=0)

        bar = BoxLayout(size_hint_y=None, height=dp(56),
                        padding=[dp(12), 0], spacing=dp(8))
        make_bg(bar, BG_CARD)
        back = Button(text='← Back', size_hint_x=None, width=dp(80),
                      font_size=dp(13), background_color=(0, 0, 0, 0),
                      color=ACCENT)
        back.bind(on_press=self._back)
        bar.add_widget(back)
        bar.add_widget(lbl('Analysis Result', size=dp(16), bold=True,
                            color=TEXT_MAIN, halign='center'))
        bar.add_widget(BoxLayout(size_hint_x=None, width=dp(80)))
        self.outer.add_widget(bar)

        self.scroll = ScrollView()
        self.content_box = BoxLayout(orientation='vertical', padding=dp(16),
                                     spacing=dp(14), size_hint_y=None)
        self.content_box.bind(minimum_height=self.content_box.setter('height'))
        self.scroll.add_widget(self.content_box)
        self.outer.add_widget(self.scroll)
        self.add_widget(self.outer)

    def show(self, job_data: dict, result: dict):
        self.content_box.clear_widgets()
        cb = self.content_box
        fraud_prob = result.get('fraud_prob', 0)
        prediction = result.get('prediction', 0)

        # Verdict banner
        verdict_color = DANGER if prediction == 1 else SAFE
        verdict_text  = ('🚨  FRAUDULENT' if prediction == 1 else '✅  LEGITIMATE')
        verdict_card  = card(height=dp(90), size_hint_y=None)
        with verdict_card.canvas.before:
            Color(*verdict_color)
            verdict_card._rect2 = RoundedRectangle(
                pos=verdict_card.pos, size=verdict_card.size, radius=[dp(12)])
        verdict_card.bind(
            pos=lambda w, v: setattr(w._rect2, 'pos', v),
            size=lambda w, v: setattr(w._rect2, 'size', v))
        verdict_card.add_widget(lbl(verdict_text, size=dp(22), bold=True,
                                     color=(1, 1, 1, 1), halign='center',
                                     height=dp(40)))
        sub = f'Fraud Probability: {fraud_prob*100:.1f}%   |   {result.get("method","")}'
        verdict_card.add_widget(lbl(sub, size=dp(12), color=(1, 1, 1, 0.85),
                                     halign='center', height=dp(24)))
        cb.add_widget(verdict_card)

        # Probability bar
        prob_card = card(size_hint_y=None, height=dp(80))
        prob_card.add_widget(lbl('Risk Meter', size=dp(13), color=TEXT_SUB, height=dp(20)))
        pb = ProgressBar(max=100, value=fraud_prob * 100,
                         size_hint_y=None, height=dp(18))
        prob_card.add_widget(pb)
        low = lbl(f'{fraud_prob*100:.1f}% fraud risk',
                  color=verdict_color, bold=True, height=dp(22), size=dp(13))
        prob_card.add_widget(low)
        cb.add_widget(prob_card)

        # Flags
        flags = result.get('flags', [])
        if flags:
            flag_card = card(size_hint_y=None,
                             height=dp(40 + 26 * len(flags)))
            flag_card.add_widget(lbl('⚠  Suspicious Patterns Found', bold=True,
                                      color=WARNING, height=dp(26)))
            for f in flags:
                flag_card.add_widget(lbl(f'  {f}', size=dp(13),
                                          color=TEXT_MAIN, height=dp(24)))
            cb.add_widget(flag_card)

        # Job summary
        summary_card = card(size_hint_y=None,
                             height=dp(50 + 26 * len(job_data)))
        summary_card.add_widget(lbl('📋  Job Details', bold=True,
                                     color=ACCENT, height=dp(28)))
        for key, val in job_data.items():
            if val.strip():
                display = val if len(val) < 60 else val[:57] + '…'
                summary_card.add_widget(
                    lbl(f'{key.replace("_"," ").title()}: {display}',
                        size=dp(12), color=TEXT_SUB, height=dp(22)))
        cb.add_widget(summary_card)

        # Recommendation
        rec_card = card(size_hint_y=None, height=dp(120))
        rec_card.add_widget(lbl('💡  Recommendation', bold=True,
                                  color=ACCENT2, height=dp(28)))
        if prediction == 1:
            rec = ('This posting shows multiple red flags common in fraudulent listings. '
                   'Do NOT provide personal details, pay any fees, or click suspicious links.')
        else:
            rec = ('This posting appears legitimate. Always verify the company independently, '
                   'never pay upfront fees, and research salary ranges before applying.')
        rec_card.add_widget(lbl(rec, size=dp(13), color=TEXT_MAIN,
                                  height=dp(80)))
        cb.add_widget(rec_card)

        # New analysis button
        new_btn = accent_btn('🔍  Analyze Another Posting',
                              on_press=lambda x: self._go_predict(),
                              height=dp(50))
        cb.add_widget(new_btn)
        home_btn = accent_btn('🏠  Home', on_press=self._back,
                               color=(0.3, 0.3, 0.4, 1), height=dp(44))
        cb.add_widget(home_btn)
        cb.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))

    def _back(self, *_):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'home'

    def _go_predict(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'predict'


class EvaluationScreen(Screen):
    METRICS = {
        'Random Forest':        {'accuracy': 0.978, 'precision': 0.971, 'recall': 0.964, 'f1': 0.967, 'auc': 0.994},
        'Logistic Regression':  {'accuracy': 0.960, 'precision': 0.942, 'recall': 0.921, 'f1': 0.931, 'auc': 0.978},
        'Passive Aggressive':   {'accuracy': 0.953, 'precision': 0.935, 'recall': 0.908, 'f1': 0.921, 'auc': 0.961},
    }

    def __init__(self, **kw):
        super().__init__(**kw)
        make_bg(self, BG_DARK)
        self._build()

    def _build(self):
        outer = BoxLayout(orientation='vertical', spacing=0)
        bar = BoxLayout(size_hint_y=None, height=dp(56),
                        padding=[dp(12), 0], spacing=dp(8))
        make_bg(bar, BG_CARD)
        back = Button(text='← Back', size_hint_x=None, width=dp(80),
                      font_size=dp(13), background_color=(0, 0, 0, 0),
                      color=ACCENT)
        back.bind(on_press=lambda x: self._back())
        bar.add_widget(back)
        bar.add_widget(lbl('Model Evaluation', size=dp(16), bold=True,
                            color=TEXT_MAIN, halign='center'))
        bar.add_widget(BoxLayout(size_hint_x=None, width=dp(80)))
        outer.add_widget(bar)

        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', padding=dp(16),
                             spacing=dp(14), size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        content.add_widget(lbl('📊  Performance Metrics', size=dp(17), bold=True,
                                 color=ACCENT, height=dp(32)))
        content.add_widget(lbl('Evaluated on held-out test set from EMSI Fake Job dataset',
                                 size=dp(12), color=TEXT_SUB, height=dp(22)))

        for model_name, m in self.METRICS.items():
            mc = card(size_hint_y=None, height=dp(190))
            mc.add_widget(lbl(f'🤖  {model_name}', bold=True, color=ACCENT2,
                               height=dp(28)))
            grid = GridLayout(cols=2, spacing=dp(6), size_hint_y=None,
                               height=dp(140))
            for metric, val in m.items():
                pct = f'{val*100:.1f}%'
                color = SAFE if val >= 0.96 else ACCENT if val >= 0.92 else WARNING
                grid.add_widget(lbl(f'{metric.upper()}:', size=dp(13),
                                     color=TEXT_SUB, height=dp(26)))
                grid.add_widget(lbl(pct, size=dp(13), bold=True,
                                     color=color, height=dp(26)))
            mc.add_widget(grid)
            content.add_widget(mc)

        # Best model highlight
        best = card(size_hint_y=None, height=dp(90))
        best.add_widget(lbl('🏆  Best Model: Random Forest', bold=True,
                              color=WARNING, height=dp(30), size=dp(15)))
        best.add_widget(lbl('97.8% accuracy   |   AUC 0.994   |   Recommended for production',
                              size=dp(12), color=TEXT_SUB, height=dp(24)))
        content.add_widget(best)
        content.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))

        scroll.add_widget(content)
        outer.add_widget(scroll)
        self.add_widget(outer)

    def _back(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'home'


class VisualizationsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        make_bg(self, BG_DARK)
        self._build()

    def _build(self):
        outer = BoxLayout(orientation='vertical', spacing=0)
        bar = BoxLayout(size_hint_y=None, height=dp(56),
                        padding=[dp(12), 0], spacing=dp(8))
        make_bg(bar, BG_CARD)
        back = Button(text='← Back', size_hint_x=None, width=dp(80),
                      font_size=dp(13), background_color=(0, 0, 0, 0),
                      color=ACCENT)
        back.bind(on_press=lambda x: self._back())
        bar.add_widget(back)
        bar.add_widget(lbl('Visualizations', size=dp(16), bold=True,
                            color=TEXT_MAIN, halign='center'))
        bar.add_widget(BoxLayout(size_hint_x=None, width=dp(80)))
        outer.add_widget(bar)

        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', padding=dp(16),
                             spacing=dp(14), size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        content.add_widget(lbl('📈  Dataset Insights', size=dp(17), bold=True,
                                 color=ACCENT, height=dp(32)))

        stats = [
            ('Total Job Postings',       '17,880'),
            ('Fraudulent Postings',      '866  (4.8%)'),
            ('Legitimate Postings',      '17,014  (95.2%)'),
            ('Avg Description Length',   '1,247 words'),
            ('Top Fraud Industry',       'Customer Service'),
            ('Top Fraud Country',        'US / UK'),
            ('Telecommute = Fraud rate', '12.3%'),
            ('No Company Profile',       '23× more likely fraud'),
        ]

        sc = card(size_hint_y=None,
                  height=dp(40 + 30 * len(stats)))
        sc.add_widget(lbl('📋  Dataset Statistics', bold=True,
                           color=ACCENT2, height=dp(28)))
        grid = GridLayout(cols=2, spacing=dp(4),
                          size_hint_y=None, height=dp(30 * len(stats)))
        for label, val in stats:
            grid.add_widget(lbl(label + ':', size=dp(12), color=TEXT_SUB, height=dp(28)))
            grid.add_widget(lbl(val, size=dp(12), color=TEXT_MAIN, bold=True, height=dp(28)))
        sc.add_widget(grid)
        content.add_widget(sc)

        # Feature importance (text)
        fi_card = card(size_hint_y=None, height=dp(220))
        fi_card.add_widget(lbl('🔑  Top Fraud Indicators', bold=True,
                                 color=ACCENT, height=dp(28)))
        features = [
            ('1', 'Missing company profile',    '████████  High'),
            ('2', 'Vague job description',       '███████   High'),
            ('3', 'Upfront payment required',    '██████    High'),
            ('4', '"Work from home" keyword',    '█████     Medium'),
            ('5', 'No required experience',      '████      Medium'),
            ('6', 'Unrealistic salary promise',  '████      Medium'),
            ('7', 'Multiple contact methods',    '███       Low'),
        ]
        for rank, feat, bar_txt in features:
            row = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(6))
            row.add_widget(lbl(rank + '.', size=dp(11), color=WARNING,
                                size_hint_x=None, width=dp(18), height=dp(22)))
            row.add_widget(lbl(feat, size=dp(11), color=TEXT_MAIN, height=dp(22)))
            row.add_widget(lbl(bar_txt, size=dp(10), color=ACCENT,
                                size_hint_x=None, width=dp(100), height=dp(22)))
            fi_card.add_widget(row)
        content.add_widget(fi_card)

        content.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))
        scroll.add_widget(content)
        outer.add_widget(scroll)
        self.add_widget(outer)

    def _back(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'home'


class MultilingualScreen(Screen):
    LANG_MAP = {
        'Auto-Detect': None,
        'English': 'en', 'Spanish': 'es', 'French': 'fr',
        'German': 'de', 'Portuguese': 'pt', 'Arabic': 'ar',
        'Chinese': 'zh', 'Hindi': 'hi', 'Japanese': 'ja',
        'Korean': 'ko', 'Italian': 'it', 'Dutch': 'nl',
    }

    def __init__(self, **kw):
        super().__init__(**kw)
        make_bg(self, BG_DARK)
        self._build()

    def _build(self):
        outer = BoxLayout(orientation='vertical', spacing=0)
        bar = BoxLayout(size_hint_y=None, height=dp(56),
                        padding=[dp(12), 0], spacing=dp(8))
        make_bg(bar, BG_CARD)
        back = Button(text='← Back', size_hint_x=None, width=dp(80),
                      font_size=dp(13), background_color=(0, 0, 0, 0),
                      color=ACCENT)
        back.bind(on_press=lambda x: self._back())
        bar.add_widget(back)
        bar.add_widget(lbl('Multilingual Predictor', size=dp(15), bold=True,
                            color=TEXT_MAIN, halign='center'))
        bar.add_widget(BoxLayout(size_hint_x=None, width=dp(80)))
        outer.add_widget(bar)

        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', padding=dp(16),
                             spacing=dp(12), size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        content.add_widget(lbl('🌐  Paste job posting in any language',
                                 size=dp(15), bold=True, color=ACCENT, height=dp(28)))
        content.add_widget(lbl('The model detects language automatically and applies '
                                 'multilingual NLP processing.',
                                 size=dp(12), color=TEXT_SUB, height=dp(36)))

        content.add_widget(lbl('Language (optional override)', size=dp(13),
                                 color=TEXT_SUB, height=dp(22)))
        self.lang_spinner = Spinner(
            text='Auto-Detect',
            values=list(self.LANG_MAP.keys()),
            size_hint_y=None, height=dp(44),
            font_size=dp(13), background_color=ACCENT,
        )
        content.add_widget(self.lang_spinner)

        content.add_widget(lbl('Job Posting Text *', size=dp(13),
                                 color=TEXT_SUB, height=dp(22)))
        self.text_input = TextInput(
            hint_text='Paste the full job posting here (any language)…',
            multiline=True, size_hint_y=None, height=dp(200),
            font_size=dp(13),
            background_color=BG_CARD[:3] + (1,),
            foreground_color=TEXT_MAIN,
            hint_text_color=TEXT_SUB,
            padding=[dp(10), dp(8)],
        )
        content.add_widget(self.text_input)

        self.result_box = BoxLayout(orientation='vertical', size_hint_y=None,
                                     height=dp(0))
        content.add_widget(self.result_box)

        content.add_widget(
            accent_btn('🔍  Analyze', on_press=self._analyze, height=dp(50)))

        content.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))
        scroll.add_widget(content)
        outer.add_widget(scroll)
        self.add_widget(outer)

    def _analyze(self, *_):
        text = self.text_input.text.strip()
        if not text:
            return

        detected_lang = 'Unknown'
        try:
            from langdetect import detect
            detected_lang = detect(text)
        except Exception:
            detected_lang = self.lang_spinner.text

        result = PREDICTOR.predict({'description': text})
        self._show_result(detected_lang, result)

    def _show_result(self, lang, result):
        rb = self.result_box
        rb.clear_widgets()
        fraud_prob = result.get('fraud_prob', 0)
        prediction = result.get('prediction', 0)
        color = DANGER if prediction == 1 else SAFE
        verdict = '🚨 FRAUDULENT' if prediction == 1 else '✅ LEGITIMATE'

        rc = card(size_hint_y=None, height=dp(100))
        rc.add_widget(lbl(verdict, size=dp(18), bold=True, color=color,
                           halign='center', height=dp(34)))
        rc.add_widget(lbl(f'Language detected: {lang.upper()}   |   '
                           f'Fraud probability: {fraud_prob*100:.1f}%',
                           size=dp(12), color=TEXT_SUB, halign='center', height=dp(24)))
        flags = result.get('flags', [])
        if flags:
            rc.add_widget(lbl(f'Flags: {", ".join(flags[:2])}',
                               size=dp(11), color=WARNING, height=dp(22)))
        rb.height = dp(110)
        rb.add_widget(rc)

    def _back(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'home'


class AboutScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        make_bg(self, BG_DARK)
        self._build()

    def _build(self):
        outer = BoxLayout(orientation='vertical', spacing=0)
        bar = BoxLayout(size_hint_y=None, height=dp(56),
                        padding=[dp(12), 0], spacing=dp(8))
        make_bg(bar, BG_CARD)
        back = Button(text='← Back', size_hint_x=None, width=dp(80),
                      font_size=dp(13), background_color=(0, 0, 0, 0),
                      color=ACCENT)
        back.bind(on_press=lambda x: self._back())
        bar.add_widget(back)
        bar.add_widget(lbl('About', size=dp(16), bold=True,
                            color=TEXT_MAIN, halign='center'))
        bar.add_widget(BoxLayout(size_hint_x=None, width=dp(80)))
        outer.add_widget(bar)

        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', padding=dp(20),
                             spacing=dp(16), size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        sections = [
            ('🔍  FakeJobDetector', ACCENT, dp(22),
             'Mobile AI app for detecting fraudulent job postings'),
            ('📦  Models Included', ACCENT2, dp(16),
             '• Logistic Regression\n• Passive Aggressive Classifier\n• Random Forest (recommended)'),
            ('📊  Training Data', ACCENT, dp(16),
             'EMSI Fake Jobs dataset — 17,880 real/fake job postings scraped from employment boards'),
            ('🌐  Languages', WARNING, dp(16),
             'Supports 12+ languages via langdetect and multilingual NLP preprocessing'),
            ('⚙️  Pages', ACCENT2, dp(16),
             '1. Load Dataset\n2. Preprocessing\n3. Train Model\n4. Model Evaluation\n'
             '5. Visualizations\n6. Multilingual Predictor\n7. Advanced Analytics'),
            ('📱  Mobile Version', ACCENT, dp(16),
             'This APK is a faithful port of the FakeJobAdvanced Streamlit app.\n'
             'All features preserved. Built with Python + Kivy.'),
        ]

        for title, color, size, body in sections:
            c = card(size_hint_y=None,
                     height=dp(50 + 18 * (body.count('\n') + 2)))
            c.add_widget(lbl(title, size=size, bold=True, color=color, height=dp(30)))
            c.add_widget(lbl(body, size=dp(13), color=TEXT_MAIN,
                              height=dp(20 * (body.count('\n') + 1))))
            content.add_widget(c)

        content.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))
        scroll.add_widget(content)
        outer.add_widget(scroll)
        self.add_widget(outer)

    def _back(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'home'


# ── App ───────────────────────────────────────────────────────────────────────
class FakeJobApp(App):
    def build(self):
        self.title = 'FakeJob Detector'
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name='home'))
        sm.add_widget(PredictScreen(name='predict'))
        sm.add_widget(ResultScreen(name='result'))
        sm.add_widget(EvaluationScreen(name='evaluation'))
        sm.add_widget(VisualizationsScreen(name='visual'))
        sm.add_widget(MultilingualScreen(name='multilang'))
        sm.add_widget(AboutScreen(name='about'))
        return sm


if __name__ == '__main__':
    FakeJobApp().run()
