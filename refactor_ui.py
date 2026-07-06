import os
import re

TEMPLATE_DIR = os.path.join("app", "templates")

REPLACEMENTS = [
    (r'Loading buildings...', 'Retrieving facilities database...'),
    (r'Loading facilities...', 'Retrieving facilities database...'),
    (r'Scanning telemetry...', 'System nominal. Initializing pipeline...'),
]

def clean_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Clean inline styles from lucide icons
    def repl_icon(match):
        full_tag = match.group(0)
        # Extract existing class
        cls_match = re.search(r'class="([^"]+)"', full_tag)
        existing_classes = cls_match.group(1).split() if cls_match else []
        
        # Extract style
        style_match = re.search(r'style="([^"]+)"', full_tag)
        style = style_match.group(1) if style_match else ""
        
        # Map styles to new classes
        if "width" in style and "height" in style:
            w_match = re.search(r'width:\s*(\d+)px', style)
            w = int(w_match.group(1)) if w_match else 16
            
            if w <= 14: existing_classes.append("icon-sm")
            elif w <= 18: existing_classes.append("icon-md")
            elif w <= 20: existing_classes.append("icon-lg")
            elif w <= 24: existing_classes.append("icon-xl")
            elif w >= 48: existing_classes.append("icon-xxl")
            
            if "margin-right" in style: existing_classes.append("me-1")
            if "margin-bottom" in style: existing_classes.append("mb-3")
            if "color: var(--accent-danger)" in style or "text-danger" in full_tag: 
                if "text-danger" not in existing_classes: existing_classes.append("text-danger")
            if "color: var(--accent-success)" in style or "text-success" in full_tag: 
                if "text-success" not in existing_classes: existing_classes.append("text-success")
            if "color: var(--text-muted)" in style or "text-muted" in full_tag: 
                if "text-muted" not in existing_classes: existing_classes.append("text-muted")
            
            new_style = ' style="cursor: pointer;"' if "cursor: pointer" in style else ""
            
            tag_no_class = re.sub(r'\s*class="[^"]*"', '', full_tag)
            tag_no_style = re.sub(r'\s*style="[^"]*"', '', tag_no_class)
            
            class_str = ' class="' + " ".join(existing_classes) + '"' if existing_classes else ""
            
            return tag_no_style[:-1] + class_str + new_style + ">"
        
        return full_tag

    new_content = re.sub(r'<i data-lucide="[^"]*"[^>]*>', repl_icon, content)
    
    # 2. String replacements for text
    for old, new in REPLACEMENTS:
        new_content = re.sub(old, new, new_content)
        
    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, _, files in os.walk(TEMPLATE_DIR):
    for file in files:
        if file.endswith(".html"):
            clean_file(os.path.join(root, file))
print("Done.")
