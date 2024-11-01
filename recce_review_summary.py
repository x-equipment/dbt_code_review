#!/usr/bin/env python3

import json
import argparse
from datetime import datetime
from collections import defaultdict

ADD_COLOR = '#1dce00'
MODIFIED_COLOR = '#ffa502'
REMOVE_COLOR = '#ff067e'
BORDER_COLOR = '#FFA500'
TRANSPARENT_COLOR = '#cccccc'

def load_recce_state(filepath):
    """Load the recce_state.json file."""
    with open(filepath, 'r') as file:
        return json.load(file)

def get_model_status(node_id, nodes, base_nodes):
    """Determine if the model is added, modified, or removed."""
    current_checksum = nodes.get(node_id, {}).get('checksum', {}).get('checksum')
    base_checksum = base_nodes.get(node_id, {}).get('checksum', {}).get('checksum')

    if node_id not in base_nodes:
        return 'added'
    elif node_id not in nodes:
        return 'removed'
    elif current_checksum != base_checksum:
        return 'modified'
    else:
        return None

def get_modified_models(manifest):
    """Get the models that have been added, modified, or removed based on checksum differences."""
    models_status = defaultdict(dict)

    nodes = manifest.get('artifacts', {}).get('current', {}).get('manifest', {}).get('nodes', {})
    base_nodes = manifest.get('artifacts', {}).get('base', {}).get('manifest', {}).get('nodes', {})

    for node_id, node_data in nodes.items():
        if node_data['resource_type'] == 'model':
            status = get_model_status(node_id, nodes, base_nodes)
            if status:
                models_status[node_id] = status

    for node_id, node_data in base_nodes.items():
        if node_id not in nodes and node_data['resource_type'] == 'model':
            models_status[node_id] = 'removed'

    return models_status

def get_relevant_dependencies(manifest, modified_models):
    """Get relevant dependencies for modified models."""
    dependencies = defaultdict(list)
    nodes = manifest.get('artifacts', {}).get('current', {}).get('manifest', {}).get('nodes', {})

    for model, _ in modified_models.items():  # Iterate over keys (model ids) for efficiency
        parent_nodes = nodes.get(model, {}).get('depends_on', {}).get('nodes', [])
        dependencies[model] = [parent for parent in parent_nodes if nodes.get(parent, {}).get('resource_type') == 'model']

    for model, node_data in nodes.items():
        if model not in modified_models and node_data['resource_type'] == 'model':
            for parent in node_data.get('depends_on', {}).get('nodes', []):
                if parent in modified_models:
                    dependencies[model].append(parent)

    return dependencies

def format_model_name(name):
    """Format model name by removing the first part up to the second dot."""
    parts = name.split('.')
    return '.'.join(parts[2:]) if len(parts) > 2 else name

def generate_mermaid_graph(models_status, dependencies):
    """Generate Mermaid graph content."""
    mermaid_content = "graph LR\n"

    for model, status in models_status.items():
        formatted_model = format_model_name(model)
        style = {
            'added': f'style {model} stroke:{ADD_COLOR},stroke-width:2px;\n',
            'modified': f'style {model} stroke:{BORDER_COLOR},stroke-width:2px;\n',
            'removed': f'style {model} stroke:{REMOVE_COLOR},stroke-width:2px;\n',
        }.get(status, '')
        mermaid_content += f"{model}[" + formatted_model + "]\n" + style

    for model, deps in dependencies.items():
        for dep in deps:
            if model in models_status:
                mermaid_content += f'{dep}-->{model}\n'
            else:
                mermaid_content += f'{dep}-.->{model}\n'

    return mermaid_content

def generate_markdown(checks, models_status, dependencies):
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    passed_checks = sum(1 for check in checks if check["is_checked"])
    failed_checks = len(checks) - passed_checks

    md_content = f"# 📊 Recce Review Summary\n\n"
    md_content += f"**Generated on:** {current_date}\n\n"
    md_content += f"---\n"
    md_content += f"### **Overview of Results:**\n\n"
    md_content += f"- ✅ Passed checks: {passed_checks}\n"
    md_content += f"- ❌ Failed checks: {failed_checks}\n\n"
    md_content += "---\n"

    md_content += "## **Lineage Graph**\n"
    md_content += "Below is the lineage graph depicting the relationships between the models:\n\n"
    mermaid_graph = generate_mermaid_graph(models_status, dependencies)
    md_content += "```mermaid\n"
    md_content += mermaid_graph
    md_content += "```\n\n"

    md_content += "## **Checks Overview**\n"
    md_content += "Click the sections below to expand the details of each check:\n\n"

    for check in checks:
        status_icon = "✅" if check["is_checked"] else "❌"
        findings = check['description'].strip() or "(No findings)"

        md_content += f"<details>\n"
        md_content += f"<summary><h3>{check['name']} {status_icon}</h3></summary>\n\n"
        md_content += f"**Findings:**\n\n{findings}\n\n"
        md_content += "</details>\n\n"

    return md_content

def save_markdown(filepath, content):
    with open(filepath, 'w') as file:
        file.write(content)

def main():
    parser = argparse.ArgumentParser(description='Generate a Recce review summary.')
    parser.add_argument('recce_filepath', type=str, help='Path to the recce_state.json file')
    args = parser.parse_args()

    recce_data = load_recce_state(args.recce_filepath)
    checks = recce_data.get('checks', [])
    models_status = get_modified_models(recce_data)
    dependencies = get_relevant_dependencies(recce_data, models_status)
    markdown_content = generate_markdown(checks, models_status, dependencies)
    save_markdown('recce_review_summary.md', markdown_content)
    print("Markdown file generated: recce_review_summary.md")

if __name__ == "__main__":
    main()
