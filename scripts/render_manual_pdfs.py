from pathlib import Path

import pymupdf


root = Path(__file__).resolve().parents[1] / "output"
for pdf_path in sorted(root.glob("SupportHub-1.66.88-*.pdf")):
    target = root / f"qa-{pdf_path.stem}"
    target.mkdir(exist_ok=True)
    pdf = pymupdf.open(pdf_path)
    for page_number, page in enumerate(pdf, 1):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        pix.save(target / f"page-{page_number:02d}.png")
    print(f"{pdf_path.name}: {len(pdf)} pages -> {target}")
