"""사람 채점(O/X)을 집계한다: 근거 정확도 = O / (O+X). 비어 있는 항목은 분모에서 빼고 수를 적는다."""

import re

from dta.config import RESULTS_DIR

text = (RESULTS_DIR / "c1_evidence_sample.md").read_text(encoding="utf-8")
marks = re.findall(r"^판정:\s*(.*)$", text, flags=re.M)
o = sum(1 for m in marks if m.strip().upper().startswith("O"))
x = sum(1 for m in marks if m.strip().upper().startswith("X"))
blank = len(marks) - o - x
print(f"근거 정확도 = {o}/{o + x} ({(o / (o + x) * 100) if (o + x) else 0:.0f}%) · 미채점 {blank}")
(RESULTS_DIR / "c1_evidence_score.md").write_text(f"| 근거 정확도 | {o}/{o + x} | 미채점 {blank} |\n", encoding="utf-8")
