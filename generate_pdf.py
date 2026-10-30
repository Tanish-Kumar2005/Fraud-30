#!/usr/bin/env python3
"""Generate comprehensive PDF documentation for the Fraud 30 project."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, PageBreak, ListFlowable,
                                ListItem, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

DARK = HexColor("#1a1a2e")
ACCENT = HexColor("#e94560")
LIGHT = HexColor("#f0f0f0")

styles = getSampleStyleSheet()
title_st = ParagraphStyle("title", parent=styles["Title"], fontSize=20,
                          textColor=white, alignment=TA_CENTER, spaceAfter=10)
sub_st = ParagraphStyle("sub", parent=styles["Normal"], fontSize=11,
                        textColor=HexColor("#a0a0b0"), alignment=TA_CENTER)
h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=14,
                    textColor=ACCENT, spaceBefore=15, spaceAfter=8)
h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12,
                    textColor=DARK, spaceBefore=10, spaceAfter=5)
body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9.5,
                      alignment=TA_JUSTIFY, spaceAfter=6, leading=13)
code = ParagraphStyle("code", parent=styles["Normal"], fontSize=8,
                      fontName="Courier", textColor=HexColor("#333333"),
                      backColor=LIGHT, borderPadding=5, spaceAfter=6)
bullet = ParagraphStyle("bullet", parent=styles["Normal"], fontSize=9.5,
                        leftIndent=15, spaceAfter=3, leading=12)

doc = SimpleDocTemplate("CTBF-CS-02_Voice_Clone_Call_Detector.pdf",
                        pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                        topMargin=20*mm, bottomMargin=20*mm,
                        title="CTBF-CS-02 Voice Clone & Digital Arrest Call Detector",
                        author="AI Role - Fraud 30 Hackathon")

E = []
E.append(Spacer(1, 10))
E.append(Paragraph("CTBF-CS-02", title_st))
E.append(Paragraph("Voice-Clone and &ldquo;Digital Arrest&rdquo; Call Detector", title_st))
E.append(Spacer(1, 6))
E.append(Paragraph("Track: Cyber Security &bull; Category: Software &bull; Theme: Telecom Fraud &amp; Public Safety", sub_st))
E.append(Paragraph("AI Role Implementation &mdash; Voice Cloning Detection &amp; Call Safety Assistant", sub_st))
E.append(Spacer(1, 12))
E.append(HRFlowable(width="100%", color=ACCENT, thickness=2))
E.append(Spacer(1, 12))

E.append(Paragraph("1. Project Overview", h1))
E.append(Paragraph(
    "Fraudsters impersonate police, CBI, or relatives in distress, sometimes using "
    "AI-cloned voices, to pressure victims into money transfers. This project builds "
    "a call-safety assistant that analyses recorded or live call audio and estimates "
    "whether the voice is synthetic, transcribes and flags pressure tactics "
    "(arrest threats, secrecy demands, urgent transfer requests), shows on-screen "
    "warnings with a &ldquo;verify with family&rdquo; prompt, and processes audio "
    "on-device with secure deletion after analysis.", body))

E.append(Paragraph("2. System Architecture", h1))
E.append(Paragraph("The solution is organised into five Python modules:", body))
arch = [
    ["Module", "Purpose", "Key Functions"],
    ["audio_utils.py", "Audio loading, preprocessing, feature extraction",
     "load_audio, save_audio, delete_audio_file, compute_mfcc, compute_spectral_centroid, compute_zero_crossing_rate, compute_spectral_rolloff, compute_chroma, extract_all_features, compute_feature_statistics, normalize_audio, split_into_segments"],
    ["voice_clone_detector.py", "Synthetic / AI-cloned voice detection",
     "VoiceCloneDetector class, detect_from_file, detect_from_audio, detect_voice_clone"],
    ["scam_script_detector.py", "Pressure-tactic / scam-script detection",
     "ScamScriptDetector class, ScamTactic dataclass, detect, detect_from_file, detect_scam_script"],
    ["warning_display.py", "On-screen warnings & verify-with-family prompt",
     "WarningDisplay class, CallWarning dataclass, add, process_voice, process_scam, process_both"],
    ["call_safety_assistant.py", "Main orchestrator tying all modules together",
     "CallSafetyAssistant class, analyse_call, analyse_audio"],
]
t = Table(arch, colWidths=[25*mm, 45*mm, 110*mm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), DARK),
    ("TEXTCOLOR", (0,0), (-1,0), white),
    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE", (0,0), (-1,-1), 8),
    ("GRID", (0,0), (-1,-1), 0.5, HexColor("#666666")),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, LIGHT]),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
]))
E.append(t)
E.append(Spacer(1, 10))

E.append(Paragraph("3. Module Details", h1))
E.append(Paragraph("3.1 audio_utils.py &mdash; Audio Processing", h2))
E.append(Paragraph("Handles all audio I/O and feature extraction. All processing is "
                   "on-device; no audio is sent to external servers.", body))
E.append(Paragraph("<b>load_audio(file_path, target_sr=16000, mono=True)</b>: "
                   "Loads and resamples an audio file. Returns (audio_array, sample_rate).", body))
E.append(Paragraph("<b>save_audio(file_path, audio, sr)</b>: Saves audio array to disk.", body))
E.append(Paragraph("<b>delete_audio_file(file_path)</b>: Securely deletes audio after analysis (privacy).", body))
E.append(Paragraph("<b>extract_all_features(audio, sr)</b>: Computes MFCC, spectral centroid, "
                   "zero-crossing rate, spectral rolloff, chroma, RMS energy, tempo, and duration.", body))
E.append(Paragraph("<b>compute_feature_statistics(features)</b>: Flattens feature matrices into mean/std/min/max statistics.", body))
E.append(Paragraph("<b>normalize_audio(audio, target_db=-20)</b>: Normalises loudness for consistent analysis.", body))
E.append(Paragraph("<b>split_into_segments(audio, sr, duration=5.0, overlap=0.5)</b>: Splits long audio into overlapping segments for granular analysis.", body))
E.append(Paragraph("3.2 voice_clone_detector.py &mdash; Synthetic Voice Detection", h2))
E.append(Paragraph("Detects AI-cloned voices by analysing spectral and cepstral features "
                   "and scoring anomalies typical of voice-cloning algorithms.", body))
E.append(Paragraph("<b>VoiceCloneDetector</b> class:", body))
E.append(ListFlowable([
    ListItem(Paragraph("__init__(sr=16000, threshold=0.65): Configure detector with sample rate and synthetic probability threshold.", bullet)),
    ListItem(Paragraph("detect_from_file(file_path, delete_after=False): Analyse an audio file; optionally delete it after.", bullet)),
    ListItem(Paragraph("detect_from_audio(audio, sample_rate): Analyse in-memory audio data.", bullet)),
    ListItem(Paragraph("_score_segment(stats): Weighted heuristic scoring (MFCC variance, centroid stability, ZCR, rolloff, chroma, RMS dynamics, tempo). Returns score 0-1 and reasons.", bullet)),
    ListItem(Paragraph("_confidence_level(score): Maps score to 'very_low'/'low'/'medium'/'high'.", bullet)),
], bulletType="bullet", start="circle"))
E.append(Paragraph("<b>detect_voice_clone(file_path)</b>: Convenience function.", body))

E.append(Paragraph("3.3 scam_script_detector.py &mdash; Scam Script Detection", h2))
E.append(Paragraph("Uses rule-based regex pattern matching to detect three categories of "
                   "pressure tactics in transcribed call text.", body))
E.append(ListFlowable([
    ListItem(Paragraph("<b>Arrest Threat</b>: 'digital arrest', 'you will be arrested', 'police case', 'CBI investigation', 'legal action'. Severity: critical/high.", bullet)),
    ListItem(Paragraph("<b>Secrecy Demand</b>: 'don&rsquo;t tell anyone', 'keep this confidential', 'do not disclose', 'don&rsquo;t inform family'. Severity: medium.", bullet)),
    ListItem(Paragraph("<b>Urgent Transfer Request</b>: 'transfer money immediately', 'wire funds now', 'UPI ID', 'gift card', 'crypto wallet'. Severity: critical/high.", bullet)),
], bulletType="bullet", start="circle"))
E.append(Paragraph("<b>ScamScriptDetector.detect(transcript)</b>: Returns risk score (0-1), detected tactics, highlighted spans, and summary.", body))
E.append(Paragraph("<b>detect_scam_script(transcript)</b>: Convenience function.", body))
E.append(Paragraph("3.4 warning_display.py &mdash; On-Screen Warnings", h2))
E.append(Paragraph("Manages warnings raised during a call and displays them with severity "
                   "icons. Triggers a &ldquo;verify with family&rdquo; prompt for high/critical severity.", body))
E.append(ListFlowable([
    ListItem(Paragraph("<b>add(warning_type, severity, message, details)</b>: Adds a warning and renders it to console.", bullet)),
    ListItem(Paragraph("<b>trigger_verify_prompt()</b>: Displays the &ldquo;verify with family&rdquo; overlay.", bullet)),
    ListItem(Paragraph("<b>process_voice_clone_result(result)</b>: Converts voice-clone detection into a warning.", bullet)),
    ListItem(Paragraph("<b>process_scam_result(result)</b>: Converts scam detection into a warning.", bullet)),
    ListItem(Paragraph("<b>process_combined_result(voice, scam)</b>: If both detected, raises a combined CRITICAL warning.", bullet)),
    ListItem(Paragraph("<b>render_summary()</b>: Returns formatted text summary of all warnings.", bullet)),
], bulletType="bullet", start="circle"))
E.append(Paragraph("3.5 call_safety_assistant.py &mdash; Main Orchestrator", h2))
E.append(Paragraph("Ties all modules into a single call-safety assistant.", body))
E.append(ListFlowable([
    ListItem(Paragraph("<b>analyse_call(audio_file, transcript=None, delete_audio=False)</b>: Complete pipeline &mdash; voice detection, scam detection, warning generation, risk assessment.", bullet)),
    ListItem(Paragraph("<b>analyse_audio(audio, sample_rate, transcript)</b>: Same pipeline for in-memory audio.", bullet)),
    ListItem(Paragraph("<b>_risk_level()</b>: Computes combined risk: safe / caution / warning / critical.", bullet)),
    ListItem(Paragraph("<b>recommendation</b>: Actionable advice based on risk level.", bullet)),
], bulletType="bullet", start="circle"))
E.append(PageBreak())

E.append(Paragraph("4. Combined Risk Assessment", h1))
risk_table = [
    ["Combined Risk", "Conditions", "Recommendation"],
    ["CRITICAL", "Synthetic voice AND scam tactics detected, OR very high confidence in either", "Do NOT transfer money. Hang up. Verify with family. Report to cybercrime."],
    ["WARNING", "Synthetic voice OR scam tactics detected (moderate confidence)", "Exercise extreme caution. Verify caller identity before any action."],
    ["CAUTION", "Minor suspicious indicators (probability 0.5+ or risk 0.3+)", "Proceed with caution. Verify claims independently."],
    ["SAFE", "No significant indicators", "Continue normally but remain vigilant."],
]
t2 = Table(risk_table, colWidths=[30*mm, 70*mm, 80*mm])
t2.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), DARK),
    ("TEXTCOLOR", (0,0), (-1,0), white),
    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE", (0,0), (-1,-1), 8),
    ("GRID", (0,0), (-1,-1), 0.5, HexColor("#666666")),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, LIGHT]),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
]))
E.append(t2)

E.append(Paragraph("5. Privacy & On-Device Processing", h1))
E.append(Paragraph("All processing runs locally on the user&rsquo;s device. No audio or "
                   "transcripts are sent to external servers. After analysis, audio files "
                   "can be securely deleted via <b>delete_audio_file()</b>. The system is "
                   "designed for privacy-sensitive call-safety applications.", body))

E.append(Paragraph("6. Usage Examples", h1))
E.append(Paragraph("6.1 Basic voice-clone detection:", body))
E.append(Paragraph("from voice_clone_detector import detect_voice_clone", code))
E.append(Paragraph("result = detect_voice_clone(&quot;call_recording.wav&quot;, delete_after=True)", code))
E.append(Paragraph("print(result[&quot;is_synthetic&quot;], result[&quot;synthetic_probability&quot;])", code))
E.append(Paragraph("6.2 Scam script detection:", body))
E.append(Paragraph("from scam_script_detector import detect_scam_script", code))
E.append(Paragraph("result = detect_scam_script(transcript_text)", code))
E.append(Paragraph("print(result[&quot;is_scam&quot;], result[&quot;risk_score&quot;], result[&quot;summary&quot;])", code))
E.append(Paragraph("6.3 Full call-safety pipeline:", body))
E.append(Paragraph("from call_safety_assistant import CallSafetyAssistant", code))
E.append(Paragraph("assistant = CallSafetyAssistant(delete_audio_after=True)", code))
E.append(Paragraph("result = assistant.analyse_call(&quot;call.wav&quot;, transcript=text)", code))
E.append(Paragraph("print(result[&quot;combined_risk&quot;], result[&quot;recommendation&quot;])", code))

E.append(Paragraph("7. File Inventory", h1))
files = [
    ["File", "Description"],
    ["requirements.txt", "Python dependencies (librosa, numpy, scikit-learn, scipy, matplotlib, soundfile)"],
    ["audio_utils.py", "Audio loading, feature extraction, normalization, segmentation"],
    ["voice_clone_detector.py", "Synthetic/AI-cloned voice detection"],
    ["scam_script_detector.py", "Pressure-tactic / scam-script detection from transcripts"],
    ["warning_display.py", "On-screen warnings and verify-with-family prompt"],
    ["call_safety_assistant.py", "Main orchestrator - complete call-safety pipeline"],
    ["demo.py", "Demo script with synthetic audio generation and full pipeline demonstration"],
    ["test_detectors.py", "Unit tests (29 tests) for all modules"],
    ["generate_pdf.py", "This PDF generation script"],
]
t3 = Table(files, colWidths=[40*mm, 140*mm])
t3.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), DARK),
    ("TEXTCOLOR", (0,0), (-1,0), white),
    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE", (0,0), (-1,-1), 8),
    ("GRID", (0,0), (-1,-1), 0.5, HexColor("#666666")),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [white, LIGHT]),
]))
E.append(t3)

E.append(Paragraph("8. Installation and Running", h1))
E.append(Paragraph("<b>Install dependencies:</b>", body))
E.append(Paragraph("pip install -r requirements.txt", code))
E.append(Paragraph("<b>Run demo:</b>", body))
E.append(Paragraph("python demo.py", code))
E.append(Paragraph("<b>Run tests:</b>", body))
E.append(Paragraph("python test_detectors.py -v", code))
E.append(Spacer(1, 15))
E.append(HRFlowable(width="100%", color=ACCENT, thickness=1))
E.append(Spacer(1, 8))
E.append(Paragraph("Developed for Fraud 30 Hackathon &mdash; AI Role: Voice Cloning &amp; Call Safety", sub_st))
E.append(Paragraph("CTBF-CS-02 &bull; Cyber Security &bull; Telecom Fraud &amp; Public Safety", sub_st))
doc.build(E)
print("PDF generated: CTBF-CS-02_Voice_Clone_Call_Detector.pdf")