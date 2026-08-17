"""
scripts/generate_presentation.py
Generates a streamlined, IEEE-grade presentation (.pptx) tailored to user specifications:
1. Title Slide
2. Abstract Slide (Executive overview of the entire project)
3. Problem Statement (1 Unified Problem, simple English, point-wise)
4. Theoretical Foundation & Literature Survey (Combined SF-DTM base paper & key related works)
5. Novel Architecture & Key Innovations (Focusing only on novel advancements)
6. End-to-End System Architecture (IEEE Block Diagram)
7. Methodology: Proactive Code Quality & Security Gates (Simple English, unified flow)
8. Methodology: Closed-Loop Runtime Self-Healing (Simple English, unified flow)
9. Closed-Loop Operational Lifecycle (Workflow Flowchart)
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

# ── Color Palette (Modern Minimalist / Editorial Engineering) ─────────────────
BG_LIGHT     = RGBColor(251, 249, 245)  # Soft Cream/Beige
BG_WHITE     = RGBColor(255, 255, 255)  # Pure White for Cards
TEXT_DARK    = RGBColor(30, 41, 59)     # Deep Slate (#1E293B)
TEXT_MUTED   = RGBColor(100, 116, 139)  # Medium Slate (#64748B)
TEXT_LIGHT   = RGBColor(241, 245, 249)  # Light Slate
ACCENT_BROWN = RGBColor(67, 56, 50)     # Warm Espresso (#433832)
ACCENT_AMBER = RGBColor(217, 119, 6)    # Warm Terracotta/Amber (#D97706)
ACCENT_TEAL  = RGBColor(13, 148, 136)   # Deep Seafoam Teal (#0D9488)
ACCENT_BLUE  = RGBColor(37, 99, 235)    # Royal Blue (#2563EB)
BORDER_COLOR = RGBColor(226, 232, 240)  # Light Slate Border (#E2E8F0)
CARD_BG      = RGBColor(248, 250, 252)  # Card Fill (#F8FAFC)


def apply_background(slide, color=BG_LIGHT):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_header(slide, title_text, category_text=""):
    """Adds a standardized clean modern header."""
    if category_text:
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.5), Inches(0.3))
        tf_c = cat_box.text_frame
        tf_c.word_wrap = True
        p_c = tf_c.paragraphs[0]
        p_c.text = category_text.upper()
        p_c.font.size = Pt(9.5)
        p_c.font.bold = True
        p_c.font.color.rgb = ACCENT_AMBER
        p_c.font.name = "Calibri"

    top_pos = Inches(0.65) if category_text else Inches(0.5)
    title_box = slide.shapes.add_textbox(Inches(0.8), top_pos, Inches(11.5), Inches(0.6))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = TEXT_DARK
    p.font.name = "Calibri"


def add_card(slide, left, top, width, height, title="", body="", items=None, border_color=BORDER_COLOR, fill_color=BG_WHITE):
    """Adds a rounded clean rectangular card with optional bullet items."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.color.rgb = border_color
    shape.line.width = Pt(1)

    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.2)
    tf.margin_right = Inches(0.2)
    tf.margin_top = Inches(0.2)
    tf.margin_bottom = Inches(0.2)

    if title:
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(13)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_DARK
        p_t.font.name = "Calibri"

    if body:
        p_b = tf.add_paragraph() if title else tf.paragraphs[0]
        p_b.text = body
        p_b.font.size = Pt(11)
        p_b.font.color.rgb = TEXT_MUTED
        p_b.font.name = "Calibri"
        p_b.space_before = Pt(4)

    if items:
        for idx, itm in enumerate(items):
            p_i = tf.add_paragraph() if (title or body or idx > 0) else tf.paragraphs[0]
            p_i.text = f"•  {itm}"
            p_i.font.size = Pt(10.5)
            p_i.font.color.rgb = TEXT_DARK
            p_i.font.name = "Calibri"
            p_i.space_before = Pt(3)

    return shape


def create_presentation(output_path="Agentic_AI_Self_Healing_Cloud_Presentation.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # ── SLIDE 1: Title Slide ──────────────────────────────────────────────────
    s1 = prs.slides.add_slide(blank_layout)
    apply_background(s1, BG_LIGHT)

    pill = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.0), Inches(4.8), Inches(0.4))
    pill.fill.solid()
    pill.fill.fore_color.rgb = RGBColor(237, 233, 227)
    pill.line.fill.background()
    p_pill = pill.text_frame.paragraphs[0]
    p_pill.text = "CLOUD COMPUTING & DISTRIBUTED SYSTEMS • PROJECT"
    p_pill.font.size = Pt(9.5)
    p_pill.font.bold = True
    p_pill.font.color.rgb = ACCENT_BROWN

    t_box = s1.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(11.5), Inches(2.2))
    tf1 = t_box.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "Agentic AI-Driven Self-Healing Cloud Infrastructure"
    p1.font.size = Pt(32)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_DARK

    p2 = tf1.add_paragraph()
    p2.text = "with Explainable Anomaly Detection, Digital Twin Simulation & Autonomous Shift-Left PR Intelligence"
    p2.font.size = Pt(16)
    p2.font.color.rgb = ACCENT_AMBER
    p2.space_before = Pt(8)

    add_card(s1, Inches(0.8), Inches(4.2), Inches(11.7), Inches(2.5),
             title="Project Scope & Architecture Overview",
             body="An end-to-end intelligent platform that unifies proactive code quality control before deployment with autonomous, closed-loop Kubernetes self-healing during live cloud operations.",
             items=[
                 "Foundational Theory: Grounded in the SF-DTM model (Saxena & Singh, IEEE TII 2025)",
                 "Dual-Engine Decision System: Sub-millisecond RL reflex (0.001s) paired with Gemini 2.0 Flash ReAct reasoning (2.4s)",
                 "Safety & Explainability: KernelSHAP root-cause attribution + SimPy 0.01s pre-execution simulation dry-run gate",
                 "Production Cloud Deployment: Microsoft Azure (Container Apps, PostgreSQL, Key Vault, Container Registry)"
             ])

    # ── SLIDE 2: Abstract ─────────────────────────────────────────────────────
    s2 = prs.slides.add_slide(blank_layout)
    apply_background(s2, BG_LIGHT)
    add_header(s2, "Abstract: Proactive & Autonomous Cloud Reliability", "Executive Summary")

    add_card(s2, Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3),
             title="Project Abstract",
             body="Modern distributed cloud systems suffer from two major sources of downtime: faulty code slipping through manual reviews (Shift-Left) and slow, opaque recovery tools when live servers experience traffic spikes or crashes (Runtime Operations).\n\nThis project presents an Agentic AI-Driven Self-Healing Framework that bridges the gap between software development and live infrastructure management through a single, continuous closed loop:",
             items=[
                 "Proactive Shift-Left Quality: Automatically inspects Pull Requests using static AST linters, security scanners, test-coverage auditors, and Gemini LLM reasoning to catch defects before code is merged.",
                 "Real-Time Digital Twin Monitoring: Continuously mirrors live microservice states and dependency call chains in an in-memory graph model (TDTdb).",
                 "Explainable Anomaly Detection: Replaces black-box thresholding with Isolation Forest and KernelSHAP to show operators exactly which metrics (CPU, RAM, latency, request rate) triggered an alert.",
                 "Dual-Agent Consensus Decision Engine: Evaluates incident remediation by running a fast SimiFed reinforcement learning reflex alongside deep Gemini ReAct chain-of-thought analysis.",
                 "Pre-Execution Safety Simulation: Validates proposed healing actions (scale up, restart, patch limits) inside a 0.01-second SimPy discrete-event queue before touching live cloud servers.",
                 "Enterprise Cloud Delivery: Deployed natively on Microsoft Azure with automated GitOps PR creation and a real-time operator control console."
             ])

    # ── SLIDE 3: Problem Statement (1 Unified Problem, Simple English, Point-Wise) ──
    s3 = prs.slides.add_slide(blank_layout)
    apply_background(s3, BG_LIGHT)
    add_header(s3, "Problem Statement: Why Modern Cloud Systems Fail", "Motivation")

    add_card(s3, Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3),
             title="The Core Problem: Reactive Tools & Unchecked Code Cause Costly Downtime",
             body="Cloud applications break easily when buggy code gets merged without thorough checks, and live monitoring tools react too slowly without explaining what went wrong.",
             items=[
                 "Slow & Incomplete Code Reviews: Manual PR reviews take hours to days, and humans easily overlook hidden security flaws (hardcoded credentials, injection bugs) and missing unit tests.",
                 "Delayed Outage Reaction: Standard cloud auto-scalers (like Kubernetes HPA) wait 3 to 5 minutes of continuous high CPU before reacting, causing service outages for users during sudden traffic surges.",
                 "Black-Box Alert Confusion: Traditional monitoring alarms tell engineers that an error occurred, but never explain *why* it happened, forcing on-call engineers to guess root causes under high stress.",
                 "Risky Blind Fixes: Automated recovery tools apply actions directly to live servers without testing them first, often causing destructive restart loops and cascading microservice failures.",
                 "Disconnected Tools: Developers and operations teams use separate, disconnected tools, meaning errors caught in production are not fed back into the code review cycle to prevent repeat mistakes."
             ])

    # ── SLIDE 4: Combined Literature Survey & Theoretical Foundation ──────────
    s4 = prs.slides.add_slide(blank_layout)
    apply_background(s4, BG_LIGHT)
    add_header(s4, "Theoretical Foundation & Literature Survey", "Literature Review")

    add_card(s4, Inches(0.8), Inches(1.4), Inches(5.6), Inches(5.3),
             title="Base Paper: SF-DTM (Saxena & Singh, IEEE TII 2025)",
             body="D. Saxena and A. K. Singh, 'A Self-Healing and Fault-Tolerant Cloud-based Digital Twin Processing Management Model,' in IEEE Transactions on Industrial Informatics, 2025.",
             items=[
                 "SimiFed Resource Estimation: Uses Cosine Similarity vector matching on past incidents to estimate needed compute without exposing raw client telemetry.",
                 "Digital Twin State Synchronizer: Continuously tracks task execution sequences and resource allocations in a temporal database (TDTdb).",
                 "Frequent Sequence Patterns (FSP): Mines supportive vs non-supportive task sequences to separate conflicting microservices.",
                 "Formal Availability Metrics: Proves mathematical bounds for Mean Time Between Failures (MTBF) and Mean Time To Repair (MTTR)."
             ])

    add_card(s4, Inches(6.8), Inches(1.4), Inches(5.7), Inches(5.3),
             title="Key Insights Adopted from Related Literature",
             body="Core engineering principles integrated from top IEEE & ACM publications:",
             items=[
                 "Two-Tier Cloud-Edge Collaboration (Zhang et al., IEEE IoTJ 2024): Splitting intelligence into fast local reflexes (0.001s) and deep centralized cloud reasoning.",
                 "Multi-Expert Consensus Arbitration (JAISE 2026): Combining multiple distinct decision algorithms to prevent single-point-of-failure errors.",
                 "Shift-Left Security & Admission Control (FGCS 2026): Enforcing security scanning, secret detection, and AST validation directly at the pull request stage.",
                 "Idempotent Operations & Async Safety (IJPEDS 2026): Using deduplicated, non-blocking queues to prevent conflicting self-healing actions from flapping."
             ])

    # ── SLIDE 5: Novel Architecture & Key Innovations ─────────────────────────
    s5 = prs.slides.add_slide(blank_layout)
    apply_background(s5, BG_LIGHT)
    add_header(s5, "Novel System Architecture & Key Innovations", "Scientific Contributions")

    add_card(s5, Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3),
             title="Our 5 Novel Architectural Advancements",
             body="We extended baseline literature into a complete, enterprise-grade self-healing platform with 5 major technological innovations:",
             items=[
                 "1. Explainable AI with KernelSHAP: Replaced black-box thresholding with exact Shapley feature attributions, showing operators exactly which metrics (CPU, RAM, latency, request rate) caused the anomaly.",
                 "2. SimPy 0.01s Pre-Execution Simulation Gate: Added an active discrete-event M/M/c queuing simulator that tests and verifies healing actions *before* touching live cloud servers to guarantee zero downtime.",
                 "3. Dual Parallel Decision Engine: Engineered a dual-stream architecture pairing an instantaneous SimiFed RL reflex (0.001s) with a Gemini 2.0 Flash ReAct reasoning model (2.4s) via consensus arbitration.",
                 "4. Shift-Left Proactive PR Intelligence: Extended self-healing backwards to developer pull requests, automatically detecting security flaws, missing test cases, and opening self-healing GitOps PRs.",
                 "5. Production Cloud Deployment: Built fully automated Infrastructure as Code (IaC) on Microsoft Azure with live single-pane-of-glass operator monitoring."
             ])

    # ── SLIDE 6: End-to-End System Architecture (IEEE Block Diagram) ──────────
    s6 = prs.slides.add_slide(blank_layout)
    apply_background(s6, BG_LIGHT)
    add_header(s6, "End-to-End System Architecture (IEEE Block Diagram)", "System Design")

    img_path1 = r"C:\Users\aadih\.gemini\antigravity\brain\8eddc301-69ad-4197-aa38-da21c8e8aed2\ieee_architecture_diagram_1786944193005.jpg"
    if os.path.exists(img_path1):
        s6.shapes.add_picture(img_path1, Inches(0.8), Inches(1.35), Inches(11.7), Inches(5.5))

    # ── SLIDE 7: Methodology: Proactive Code Quality & Security Gates ─────────
    s7 = prs.slides.add_slide(blank_layout)
    apply_background(s7, BG_LIGHT)
    add_header(s7, "Methodology: Proactive Code Quality & Security Gates", "System Methodology")

    add_card(s7, Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3),
             title="How the Agent Protects Code Before Deployment (Simple Step-by-Step)",
             body="When a developer opens or updates a Pull Request on GitHub, the autonomous pipeline immediately runs the following 5-step process:",
             items=[
                 "Step 1 — Fast Static Scanning: Concurrently runs Ruff (Python linter), Bandit (security vulnerabilities like shell=True or SQL injections), Detect-Secrets (prevents API token leaks), and Pip-Audit (checks dependencies for known CVEs).",
                 "Step 2 — AI Contextual Code Review: Injects code diffs and scanner findings into Gemini 2.0 Flash. The model reasons through logic errors, evaluates edge cases, and posts line-by-line GitHub suggestion blocks.",
                 "Step 3 — Abstract Syntax Tree (AST) Test Gap Audit: Parses Python code trees to detect when critical public functions are modified without matching unit tests, preventing silent regression bugs.",
                 "Step 4 — Quality Gate Enforcement: Updates the GitHub Check Run status (review-agent/quality-gate). If critical security vulnerabilities or severe flaws are detected, merging is automatically blocked.",
                 "Step 5 — Autonomous Auto-Fix PRs: For recognized critical issues, the system can automatically create a fix branch (autoreview/fix-*), commit verified patches, and open a ready-to-merge Pull Request."
             ])

    # ── SLIDE 8: Methodology: Real-Time Anomaly Detection & Self-Healing ───────
    s8 = prs.slides.add_slide(blank_layout)
    apply_background(s8, BG_LIGHT)
    add_header(s8, "Methodology: Closed-Loop Runtime Self-Healing", "System Methodology")

    add_card(s8, Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3),
             title="How the System Heals Live Cloud Infrastructure (Simple Step-by-Step)",
             body="During live cloud operations on Microsoft Azure, the autonomous control plane monitors and repairs services through the following 5-step process:",
             items=[
                 "Step 1 — Digital Twin Telemetry Sync: Continuously pulls CPU, RAM, response latency, and request rates from Kubernetes pods and updates a live in-memory dependency graph (frontend -> checkout -> cart -> redis).",
                 "Step 2 — Anomaly Detection: Machine learning models (Isolation Forest & XGBoost) inspect incoming telemetry vectors to catch performance degradation before full service crashes occur.",
                 "Step 3 — Explainable Root Cause (KernelSHAP): Computes Shapley feature attribution scores to tell human operators exactly why the anomaly happened (e.g. CPU spike +0.82 vs memory leak +0.41).",
                 "Step 4 — Dual-Agent Decision & Consensus: SimiFed RL (0.001s reflex) and Gemini ReAct LLM (2.4s reasoning) simultaneously decide the best action (SCALE_UP, RESTART_POD, PATCH_LIMITS) and reach consensus.",
                 "Step 5 — SimPy Dry-Run Safety Gate & Actuation: Runs a 0.01-second queuing simulation to verify that the fix drops CPU load below threshold without breaking downstream services. Once verified, it executes the remediation on Azure."
             ])

    # ── SLIDE 9: Closed-Loop Operational Lifecycle (Workflow Flowchart) ───────
    s9 = prs.slides.add_slide(blank_layout)
    apply_background(s9, BG_LIGHT)
    add_header(s9, "5-Step Closed-Loop Operational Lifecycle", "Operational Workflow")

    img_path2 = r"C:\Users\aadih\.gemini\antigravity\brain\8eddc301-69ad-4197-aa38-da21c8e8aed2\closed_loop_lifecycle_diagram_1786944217223.jpg"
    if os.path.exists(img_path2):
        s9.shapes.add_picture(img_path2, Inches(0.8), Inches(1.35), Inches(11.7), Inches(5.5))

    # Save presentation
    try:
        prs.save(output_path)
        print(f"[+] Successfully generated 9-slide presentation at: {output_path}")
    except PermissionError:
        alt_path = "Agentic_AI_Self_Healing_Cloud_Presentation_v3.pptx"
        prs.save(alt_path)
        print(f"[+] Primary file was locked in PowerPoint. Saved presentation to: {alt_path}")


if __name__ == "__main__":
    create_presentation()
