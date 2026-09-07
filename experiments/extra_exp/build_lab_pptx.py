from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


OUT = "extra_exp/MC9_EDA_VALIDATION_LAB_MEETING.pptx"

NAVY = RGBColor(17, 31, 52)
NAVY2 = RGBColor(27, 48, 76)
INK = RGBColor(25, 36, 50)
MUTED = RGBColor(92, 108, 126)
PAPER = RGBColor(247, 249, 252)
WHITE = RGBColor(255, 255, 255)
TEAL = RGBColor(0, 150, 151)
TEAL_PALE = RGBColor(224, 244, 243)
ORANGE = RGBColor(236, 132, 47)
ORANGE_PALE = RGBColor(253, 239, 225)
BLUE_PALE = RGBColor(229, 237, 248)
LINE = RGBColor(205, 214, 224)
GREEN = RGBColor(37, 139, 93)
GREEN_PALE = RGBColor(226, 245, 235)


def rgb(hex_value):
    return RGBColor.from_string(hex_value)


def add_box(slide, x, y, w, h, fill, line=None, radius=True):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    sh = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = line or fill
    sh.line.width = Pt(0.8)
    return sh


def add_text(slide, text, x, y, w, h, size=18, color=INK, bold=False,
             align=PP_ALIGN.LEFT, font="Arial", valign=MSO_ANCHOR.TOP,
             margin=0.08, italic=False):
    sh = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = sh.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.alignment = align
    p.space_after = Pt(0)
    p.line_spacing = 1.04
    run = p.add_run()
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return sh


def add_title(slide, title, subtitle, dark=False, page=None):
    color = WHITE if dark else NAVY
    muted = rgb("B8C5D4") if dark else MUTED
    add_text(slide, title, 0.58, 0.37, 12.15, 0.58, 36, color, True)
    add_text(slide, subtitle, 0.60, 1.02, 12.0, 0.35, 18, muted)
    if page is not None:
        add_text(slide, f"{page:02d}", 12.42, 0.36, 0.38, 0.28, 11, muted, True, PP_ALIGN.RIGHT)


def add_label(slide, text, x, y, w, fill, color=WHITE):
    add_box(slide, x, y, w, 0.32, fill, fill, False)
    add_text(slide, text, x + 0.05, y + 0.015, w - 0.1, 0.25, 11, color, True, PP_ALIGN.CENTER, margin=0)


def add_phase_card(slide, x, y, w, h, number, title, body, fill, num_fill):
    add_box(slide, x, y, w, h, fill, LINE)
    add_box(slide, x + 0.18, y + 0.18, 0.55, 0.55, num_fill, num_fill)
    add_text(slide, number, x + 0.18, y + 0.27, 0.55, 0.25, 16, WHITE, True, PP_ALIGN.CENTER, margin=0)
    add_text(slide, title, x + 0.87, y + 0.18, w - 1.05, 0.38, 18, NAVY, True, margin=0)
    add_text(slide, body, x + 0.20, y + 0.82, w - 0.40, h - 1.00, 15.5, INK, margin=0.02)


def add_footer(slide, text, dark=False):
    color = rgb("AEBCCC") if dark else MUTED
    add_text(slide, text, 0.60, 7.20, 12.1, 0.18, 9.5, color, margin=0)


prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank = prs.slide_layouts[6]

# Slide 1: experiment question and DUT conditions.
s = prs.slides.add_slide(blank)
s.background.fill.solid()
s.background.fill.fore_color.rgb = NAVY
add_title(
    s,
    "실험 질문과 DUT 조건을 고정했다",
    "MC9 EDA validation은 ‘실제 scan 응답이 공격 입력으로 이어지는가’를 검증한다.",
    dark=True,
    page=1,
)

add_box(s, 0.58, 1.55, 12.15, 1.15, NAVY2, TEAL)
add_label(s, "핵심 질문", 0.78, 1.73, 1.18, TEAL)
add_text(
    s,
    "MC 이후의 1-bit FF 하나만 scan-visible해도, 공격자가 위치·FF 이름·MC_9 label을 모르는 상태에서 이를 찾아 key-recovery 입력으로 연결할 수 있는가?",
    2.12, 1.68, 10.25, 0.80, 20, WHITE, True, margin=0.02,
)

add_box(s, 0.58, 2.98, 5.75, 2.55, rgb("F3F6FA"), rgb("F3F6FA"))
add_label(s, "DUT / 구현", 0.82, 3.20, 1.35, ORANGE)
add_text(
    s,
    "• 10-round iterative AES-128\n"
    "• STATE_REG → SB → SR → MC → MC_REG → ARK → STATE_REG\n"
    "• MC_REG는 round 1~9에서 재사용되는 실제 sequential boundary\n"
    "• 256-cell partial scan: target MC FF + state/round/control/data decoy\n"
    "• DC synthesis → DFT insertion → VCS/Verdi FSDB → Z3 joint solver",
    0.84, 3.68, 5.16, 1.56, 16.8, INK, margin=0.02,
)

add_box(s, 6.55, 2.98, 6.18, 2.55, NAVY2, NAVY2)
add_label(s, "공격자에게 공개 / 비공개", 6.80, 3.20, 2.30, TEAL)
add_text(s, "공개", 6.84, 3.72, 0.70, 0.30, 17, TEAL, True, margin=0)
add_text(s, "chosen plaintext · capture schedule · anonymous full scan-out", 7.55, 3.72, 4.75, 0.42, 16.5, WHITE, margin=0)
add_text(s, "비공개", 6.84, 4.36, 0.95, 0.30, 17, ORANGE, True, margin=0)
add_text(s, "K0 · scan stitching map · FF instance name · physical location · MC_9", 7.82, 4.36, 4.46, 0.60, 16.5, WHITE, margin=0)
add_text(s, "목적은 scan prevalence 추정이 아니라, 대표적인 MC scan-visible 조건의 공격 가능성과 EDA composability를 검증하는 것이다.", 6.84, 5.02, 5.45, 0.35, 14.5, rgb("C4D1DE"), italic=True, margin=0)

add_box(s, 0.58, 5.88, 12.15, 0.90, TEAL, TEAL, False)
add_text(s, "결국 확인할 것", 0.82, 6.08, 1.62, 0.28, 17, NAVY, True, margin=0)
add_text(s, "anonymous slot → MC function hypothesis → 실제 gate-level transcript → adaptive full-key uniqueness", 2.50, 6.04, 9.85, 0.36, 19, NAVY, True, margin=0)
add_footer(s, "Controlled representative case: late1_MC_9__seed2 · target identity is evaluator-only", dark=True)
s.notes_slide.notes_text_frame.text = (
    "이 슬라이드는 실험의 질문과 공격 경계를 먼저 고정한다. DUT에는 MC_REG를 실제 레지스터 경계로 넣고 "
    "DFT scan chain에 target MC FF와 decoy FF를 함께 포함했다. 공격 코드가 보는 것은 anonymous full scan-out뿐이며, "
    "MC_9와 scan mapping은 사후 evaluator check에서만 사용한다. 따라서 이 결과는 모든 AES 구현에서 MC FF가 노출된다는 주장보다, "
    "실제 합성·DFT·gate-level 경로에서도 제안 공격의 인터페이스가 닫힌다는 대표 검증이다."
)

# Slide 2: one connected attack stream.
s = prs.slides.add_slide(blank)
s.background.fill.solid()
s.background.fill.fore_color.rgb = PAPER
add_title(
    s,
    "anonymous slot을 MC function으로 연결했다",
    "Phase 0에서 찾은 물리적 slot을 Phase 1·2의 solver 입력으로 그대로 전달한다.",
    dark=False,
    page=2,
)

add_phase_card(
    s, 0.58, 1.58, 6.02, 2.03, "01", "Phase 0 · Anonymous discovery",
    "65 queries × 3 schedules로 전체 256-bit scan vector를 수집한다.\n"
    "101 AES-dependent → 55 pre-round → 1 MC-aware 후보로 축소한다.\n"
    "최종: slot 255, first-active = MC capture, support = {0, 5, 10, 15}, column = C0.",
    BLUE_PALE, TEAL,
)
add_phase_card(
    s, 6.74, 1.58, 6.00, 2.03, "02", "Phase 0.5 · Function attribution",
    "C0에 가능한 MC output bit/function 32개를 hypothesis로 만든다.\n"
    "Q128 gate-level transcript와 일관성을 검사해 불가능한 branch를 제거한다. h09만 생존; UNKNOWN/timeout = 0/0.",
    TEAL_PALE, TEAL,
)
add_phase_card(
    s, 0.58, 3.92, 6.02, 2.03, "03", "Phase 1 · Fixed-query solve",
    "동일한 physical slot 255를 round 1·2에서 재사용하고, differential leakage를 C_Q(K)에 넣는다.\n"
    "첫 Solve = SAT, 두 번째 Solve = SAT: 아직 alternative key가 남아 ambiguity로 판정한다.",
    ORANGE_PALE, ORANGE,
)
add_phase_card(
    s, 6.74, 3.92, 6.00, 2.03, "04", "Phase 2 · Adaptive recovery",
    "남은 Ka, Kb를 구분하는 separator plaintext를 합성하고 실제 VCS DUT에 재질의한다.\n"
    "새 leakage를 누적해 전체 surviving hypothesis를 다시 검사한다. Q131에서 SAT→UNSAT.",
    GREEN_PALE, GREEN,
)

add_box(s, 0.58, 6.26, 12.15, 0.72, NAVY, NAVY, False)
add_text(s, "판정 규칙", 0.82, 6.46, 1.12, 0.25, 16, TEAL, True, margin=0)
add_text(s, "C_Q(K) ∧ K ≠ K̂  |  SAT = ambiguity → separator 생성·DUT 재질의  |  UNSAT = full-key recovery 인정", 2.04, 6.39, 10.28, 0.35, 17, WHITE, True, margin=0)
add_footer(s, "Phase 0 discovery와 Phase 1·2 solver가 서로 다른 semantic label을 직접 공유하지 않고, slot·transcript·hypothesis로 연결됨")
s.notes_slide.notes_text_frame.text = (
    "여기서 중요한 연결은 Phase 0의 결과가 단순한 slot 번호로 끝나지 않는다는 점이다. slot 255와 C0 support를 이용해 "
    "32개의 MC function hypothesis를 만들고, Q128 transcript로 hypothesis를 검증한다. 이후에는 surviving hypothesis를 모두 포함한 "
    "joint key solve를 수행한다. 첫 번째 solve가 SAT라고 해서 성공으로 보지 않고, K가 다른 모델이 존재하는지를 두 번째 solve에서 확인한다. "
    "ambiguity가 남으면 현재 key pair를 구분하는 plaintext를 실제 DUT에 질의하고, 그 결과를 다시 제약에 추가한다."
)

# Slide 3: result and scope.
s = prs.slides.add_slide(blank)
s.background.fill.solid()
s.background.fill.fore_color.rgb = PAPER
add_title(
    s,
    "Q131에서 adaptive key uniqueness를 확인했다",
    "첫 후보가 맞는지만 본 것이 아니라, surviving hypothesis 전체에 대한 alternative-key 부재를 확인했다.",
    dark=False,
    page=3,
)

# Result table.
tx, ty, tw = 0.58, 1.56, 7.58
add_box(s, tx, ty, tw, 3.78, WHITE, LINE)
cols = [1.62, 1.08, 1.06, 1.17, 2.24]
headers = ["단계", "누적 Q", "Solve 1", "Solve 2", "해석"]
cx = tx
for idx, (hdr, cw) in enumerate(zip(headers, cols)):
    fill = NAVY if idx != 4 else TEAL
    add_box(s, cx, ty, cw, 0.52, fill, fill, False)
    add_text(s, hdr, cx + 0.05, ty + 0.12, cw - 0.10, 0.24, 14.5, WHITE, True, PP_ALIGN.CENTER, margin=0)
    cx += cw
rows = [
    ("Q128 fixed", "129", "SAT", "SAT", "ambiguity"),
    ("Q129 adaptive", "130", "SAT", "SAT", "ambiguity"),
    ("Q130 adaptive", "130", "SAT", "SAT", "ambiguity"),
    ("Q131 final", "131", "SAT", "UNSAT", "full-key unique"),
]
row_h = 0.81
for ridx, row in enumerate(rows):
    y = ty + 0.52 + ridx * row_h
    cx = tx
    for cidx, (val, cw) in enumerate(zip(row, cols)):
        fill = rgb("F1F5F9") if ridx % 2 == 0 else WHITE
        if ridx == 3 and cidx in (3, 4):
            fill = GREEN_PALE
        add_box(s, cx, y, cw, row_h, fill, LINE, False)
        color = GREEN if ridx == 3 and cidx in (3, 4) else INK
        add_text(s, val, cx + 0.06, y + 0.24, cw - 0.12, 0.30, 15.2, color, cidx in (0, 3, 4), PP_ALIGN.CENTER if cidx != 0 else PP_ALIGN.LEFT, margin=0)
        cx += cw
add_text(s, "Q131 result source: q131_mc_hypothesis_solver_attack.json", tx + 0.16, ty + 3.42, tw - 0.32, 0.20, 10.5, MUTED, margin=0)

add_box(s, 8.42, 1.56, 4.31, 3.78, NAVY, NAVY)
add_label(s, "FINAL PASS", 8.72, 1.86, 1.34, TEAL)
add_text(s, "Q131", 8.72, 2.40, 3.68, 0.60, 44, WHITE, True, margin=0)
add_text(s, "SAT  →  UNSAT", 8.72, 3.08, 3.60, 0.42, 26, TEAL, True, margin=0)
add_text(s, "surviving hypothesis: h09\nMC bit 9 · C0 · row 1 / bit 1\nkey exclusion scope: all surviving hypotheses\nUNKNOWN / timeout: 0 / 0", 8.72, 3.72, 3.48, 1.15, 16.2, WHITE, margin=0.02)

add_box(s, 0.58, 5.62, 5.88, 1.22, BLUE_PALE, BLUE_PALE)
add_label(s, "무엇이 증명됐나", 0.82, 5.84, 1.48, TEAL)
add_text(s, "anonymous scan slot → MC hypothesis → gate-level transcript → adaptive full-key uniqueness", 0.84, 6.22, 5.14, 0.34, 16.2, NAVY, True, margin=0.02)

add_box(s, 6.74, 5.62, 5.99, 1.22, ORANGE_PALE, ORANGE_PALE)
add_label(s, "주장 범위", 6.98, 5.84, 1.05, ORANGE)
add_text(s, "대표적인 MC scan-visible DUT의 EDA composability를 검증했다. 모든 AES retiming·routing에서의 노출 빈도까지 일반화한 결과는 아니다.", 6.99, 6.17, 5.45, 0.48, 15.2, INK, margin=0.02)
add_footer(s, "Evidence: extra_exp/results/final_summary.json · phase_b/q131_mc_hypothesis_solver_attack.json · Verdi FSDB / VCS gate transcript")
s.notes_slide.notes_text_frame.text = (
    "결과는 Q128에서 바로 unique였다는 식으로 요약하면 안 된다. Q128과 Q129, Q130은 모두 alternative key가 남아 SAT→SAT였고, "
    "adaptive separator를 통해 관측을 누적한 Q131에서만 second solve가 UNSAT이 됐다. Q131에서는 h09 하나가 surviving hypothesis였으며, "
    "공격 경로는 MC_9 ground-truth label이나 hidden key를 사용하지 않았다. 이 실험이 논문에서 지지하는 것은 anonymous scan channel을 "
    "실제 gate-level transcript와 solver로 연결할 수 있다는 점이다. 다만 한 개의 controlled representative DUT case이므로, physical implementation "
    "전체에 대한 scan exposure prevalence를 주장하는 결과로 확대해서는 안 된다."
)

prs.save(OUT)
print(OUT)
