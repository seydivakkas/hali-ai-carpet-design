from pathlib import Path

pages_dir = Path("src/carpet_designer/ui/pages")
pages_dir.mkdir(parents=True, exist_ok=True)

pages = [
    ("1_Design_Studio.py", "Design Studio"),
    ("2_Variant_Batch.py", "Variant Batch"),
    ("3_Collection_Search.py", "Collection Search"),
    ("4_LoRA_Registry.py", "LoRA Registry"),
    ("5_Evaluation.py", "Evaluation"),
    ("6_System_Health.py", "System Health"),
]

template = """\"\"\"Streamlit page: {title}\"\"\"

import streamlit as st

st.set_page_config(page_title="{title}", layout="wide")
st.title("{title}")

st.info("This is the {title} module. Functionality is linked to backend services.")
"""

for file_name, title in pages:
    page_path = pages_dir / file_name
    page_path.write_text(template.format(title=title), encoding="utf-8")
    print(f"Created {file_name}")
