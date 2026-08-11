import os
import re

dir_path = r"d:\TrainingGround\BHAVIK-PROJECTS\ktechara"

cookie_notice_regex = re.compile(r'<li[^>]*menu-item-27555[^>]*>[\s\S]*?</li>', re.IGNORECASE)
manage_privacy_regex = re.compile(r'<div[^>]*elementor-element-31631383[^>]*>[\s\S]*?</div>', re.IGNORECASE)
didomi_sdk_regex = re.compile(r'<!-- Didomi SDK -->[\s\S]*?<!-- End Didomi SDK -->', re.IGNORECASE)

modified_files = 0

for root, dirs, files in os.walk(dir_path):
    for filename in files:
        if filename.endswith(".html"):
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
                continue

            original_content = content
            
            content = cookie_notice_regex.sub('', content)
            content = manage_privacy_regex.sub('', content)
            content = didomi_sdk_regex.sub('', content)

            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                modified_files += 1

print(f"Modified {modified_files} HTML files.")
