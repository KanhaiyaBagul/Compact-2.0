#!/usr/bin/env python3
import os
import re
import sys
from datetime import datetime
from pathlib import Path

class ReportGenerator:
    """Converts markdown analysis reports into high-fidelity HTML reports."""
    
    def __init__(self, output_name="CodePlus-AI_Review_Report.html"):
        self.output_name = output_name
        self.css = """
@media print {
    body { padding: 0; }
    .page-break { page-break-before: always; }
}
body { 
    font-family: Arial, sans-serif; 
    padding: 40px; 
    color: #1a202c; 
    line-height: 1.6; 
    max-width: 900px;
    margin: auto;
}
h1 { 
    text-align: center; 
    border-bottom: 3px solid #2d3748; 
    padding-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 40px;
}
h2 { 
    background: #f7fafc; 
    padding: 12px 15px; 
    border-left: 6px solid #2d3748; 
    margin-top: 40px;
    font-size: 20px;
}
h3 { 
    color: #c53030; 
    margin-top: 30px; 
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 5px;
}
h4 { 
    margin-top: 20px; 
    color: #4a5568; 
    font-size: 16px;
    text-transform: uppercase;
}
table { 
    border-collapse: collapse; 
    width: 100%; 
    margin: 20px 0;
}
th, td { 
    border: 1px solid #e2e8f0; 
    padding: 12px; 
    text-align: left;
    font-size: 14px;
}
th { 
    background: #edf2f7; 
    font-weight: 600;
}
pre { 
    background: #2d3748; 
    color: #f7fafc; 
    padding: 15px; 
    border-radius: 6px;
    overflow-x: auto; 
    font-size: 13px;
    margin: 15px 0;
}
code { 
    font-family: "JetBrains Mono", "Courier New", monospace; 
}
ul { 
    margin: 15px 0; 
}
li { 
    margin-bottom: 8px; 
}
.risk-low { color: #38a169; font-weight: bold; }
.risk-high { color: #e53e3e; font-weight: bold; }
.risk-med { color: #dd6b20; font-weight: bold; }
        """

    def generate(self, md_content: str, output_path: Path):
        """Parse markdown and generate HTML."""
        
        # Extract metadata
        project = re.search(r'\*\*Project:\*\* `(.*?)`', md_content)
        scanned = re.search(r'\*\*Scanned:\*\* (.*?) files', md_content)
        lines = re.search(r'· (.*?) lines', md_content)
        score_match = re.search(r'(\d+)/100\s+(\w+)', md_content)
        
        project_name = project.group(1) if project else "CodePlus-AI"
        files_scanned = scanned.group(1) if scanned else "0"
        total_lines = lines.group(1) if lines else "0"
        overall_score = score_match.group(1) if score_match else "0"
        risk_level = score_match.group(2) if score_match else "UNKNOWN"
        
        # Risk color class
        risk_class = "risk-low" if int(overall_score) < 30 else "risk-med" if int(overall_score) < 70 else "risk-high"

        # Build HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
<title>CodePlus-AI Review Report</title>
<style>{self.css}</style>
</head>
<body>

<h1>CODE REVIEW REPORT</h1>

<h2>Dashboard Summary</h2>
<table>
<tr><th>Metric</th><th>Details</th></tr>
<tr><td>Project Name</td><td>{project_name}</td></tr>
<tr><td>Analysis Date</td><td>{datetime.now().strftime('%Y-%m-%d')}</td></tr>
<tr><td>Files Scanned</td><td>{files_scanned}</td></tr>
<tr><td>Lines of Code</td><td>{total_lines}</td></tr>
<tr><td>Overall Risk Profile</td><td><span class="{risk_class}">{overall_score}/100 ({risk_level})</span></td></tr>
</table>

<h2>Risk Distributions</h2>
<table>
<tr><th>Severity</th><th>Affected Files</th><th>Total Issues Found</th></tr>
"""
        # Extract severity table
        sev_matches = re.findall(r'\| ([🟠🟡🔵]) (High|Medium|Low) \| (\d+) \| (\d+) \|', md_content)
        for icon, sev, files, issues in sev_matches:
            s_class = "risk-high" if sev == "High" else "risk-med" if sev == "Medium" else "risk-low"
            html += f'<tr><td class="{s_class}">{sev}</td><td>{files}</td><td>{issues}</td></tr>'
        
        html += """
</table>

<div class="page-break"></div>

<h2>Included Files</h2>
<table>
<tr><th>Rank</th><th>File Path</th><th>Risk Score</th><th>Issue Summary</th></tr>
"""
        # Extract top files table
        top_files = re.findall(r'\| (\d+) \| `(.*?)` \| (\d+)/100 \| (.*?) \|', md_content)
        for rank, path, score, issues in top_files[:10]:
            html += f"<tr><td>{rank}</td><td><code>{path}</code></td><td>{score}/100</td><td>{issues}</td></tr>"

        html += """
</table>

<div class="page-break"></div>

<h2>Detailed Analysis</h2>
"""
        # Extract detailed findings
        sections = re.split(r'### [🟠🟡🔵] `(.*?)` — score (.*?)/100', md_content)[1:]
        for i in range(0, len(sections), 3):
            file_path = sections[i]
            score = sections[i+1]
            if i+2 >= len(sections): break
            content = sections[i+2]
            
            s_class = "risk-high" if int(score) > 80 else "risk-med" if int(score) > 30 else "risk-low"
            
            html += f"""
<h3>{file_path}</h3>
<p><strong>Risk:</strong> <span class="{s_class}">{score}/100</span></p>
"""
            
            # Extract code snippets
            snippet_match = re.search(r'```(.*?)```', content, re.DOTALL)
            if snippet_match:
                html += f"<h4>Code Snippet</h4><pre><code>{snippet_match.group(1).strip()}</code></pre>"
            
            html += '<div class="page-break"></div>'

        html += """
</body>
</html>
"""
        output_path.write_text(html, encoding='utf-8')
        print(f"Created HTML report at: {output_path}")

if __name__ == "__main__":
    import sys
    input_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("analysis_report.md")
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("CodePlus-AI_Review_Report.html")
    
    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        sys.exit(1)
        
    md_text = input_file.read_text(encoding='utf-8')
    gen = ReportGenerator()
    gen.generate(md_text, output_file)
