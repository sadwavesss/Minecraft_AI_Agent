import glob
import os

target = '<a href="/admin/analytics">Аналитика</a>'
replacement = '<a href="/admin/wiki">Справочник</a>\n            <a href="/admin/analytics">Аналитика</a>'

for file in glob.glob('static/*.html'):
    if 'wiki.html' in file: continue
    
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if '<a href="/admin/wiki"' not in content:
        content = content.replace(target, replacement)
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file}")
