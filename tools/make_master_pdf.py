"""Build the untailored master resume as a PDF, in the same ATS-friendly style as the tailored ones.

    RESUME_FILE=path/to/resume.yaml python tools/make_master_pdf.py out.pdf [europe|gulf|india]

The region picks the second header line (relocation / visa / notice) from contact.line2_by_region.
Bullet order: resume.yaml `master_order: {<role id>: [bullet ids]}` if given, else the order in the file.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import yaml  # noqa: E402

from jobhunter import tailor  # noqa: E402

HEADLINE = "Senior Platform Engineer | Azure AKS & Databricks | DevOps & SRE"


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/Resume_MASTER.pdf")
    region = sys.argv[2] if len(sys.argv) > 2 else "europe"
    src = os.environ.get("RESUME_FILE") or "jobhunter/resume.yaml"
    resume = yaml.safe_load(open(src, encoding="utf-8"))
    plan = {"headline": HEADLINE,
            "summary": " ".join(resume["summary_facts"].split()),
            "skills": [[group, items] for group, items in resume["skills"].items()]}
    order = resume.get("master_order") or {}
    for role in resume["experience"]:
        ids = [b for b in order.get(role["id"], []) if b in role["bullets"]]
        ids += [b for b in role["bullets"] if b not in ids]
        plan[role["id"]] = [{"id": bid, "text": role["bullets"][bid]} for bid in ids]
    out.parent.mkdir(parents=True, exist_ok=True)
    tailor.render_pdf({"plan": plan, "resume": resume, "region": region}, out)
    print("saved", out)


if __name__ == "__main__":
    main()
