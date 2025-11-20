#!/usr/bin/env python3
"""
Generate JSON-LD documentation files from Gleam standard library source code.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

def extract_examples(doc: str) -> List[str]:
    """Extract single-line code examples from documentation."""
    examples = []
    # Look for code blocks with examples
    # Format: /// ```gleam\n/// function_call\n/// // -> result\n/// ```
    # Remove /// prefix first
    doc_clean = re.sub(r'^///\s*', '', doc, flags=re.MULTILINE)
    
    # Find code blocks
    code_blocks = re.finditer(r'```gleam\n(.*?)\n```', doc_clean, re.MULTILINE | re.DOTALL)
    for block_match in code_blocks:
        block_content = block_match.group(1)
        # Find lines that end with // ->
        lines = block_content.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if '// ->' in line and i > 0:
                # The example is the previous line
                example = lines[i-1].strip()
                if example and not example.startswith('//') and not example.startswith('import'):
                    # Remove leading pipe if present
                    if example.startswith('|>'):
                        example = example[2:].strip()
                    # Skip if it's a variable declaration or empty
                    if not example.startswith('let ') and example and example not in examples:
                        examples.append(example)
                        if len(examples) >= 4:
                            return examples
    return examples[:4]  # Return up to 4 examples

def parse_function_signature(lines: List[str], start_idx: int) -> Optional[Dict[str, Any]]:
    """Parse a function signature, potentially spanning multiple lines."""
    # Collect the full signature
    sig_lines = []
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()
        sig_lines.append(line)
        # Check if we've reached the function body (starts with {)
        if '{' in line and not line.strip().startswith('pub fn'):
            break
        i += 1
    
    full_sig = ' '.join(sig_lines)
    
    # Match: pub fn function_name(params) -> ReturnType
    # Need to find the closing paren of params and the return type
    match = re.search(r'pub fn (\w+)\(', full_sig)
    if not match:
        return None
    
    name = match.group(1)
    params_start = match.end()
    
    # Find matching closing paren for parameters
    depth = 1
    params_end = params_start
    for i in range(params_start, len(full_sig)):
        if full_sig[i] == '(':
            depth += 1
        elif full_sig[i] == ')':
            depth -= 1
            if depth == 0:
                params_end = i
                break
    
    params_str = full_sig[params_start:params_end].strip()
    
    # Find return type (after -> and before {)
    return_match = re.search(r'\)\s*->\s*([^{]+)', full_sig[params_end:])
    if not return_match:
        return None
    
    return_type = return_match.group(1).strip()
    
    # Parse parameters - need to handle nested generics and function types
    parameters = []
    if params_str:
        # Split parameters manually, accounting for nested generics and function types
        param_parts = []
        current = ""
        depth = 0
        in_fn = False
        i = 0
        while i < len(params_str):
            char = params_str[i]
            if char == '(' or char == '<':
                depth += 1
                current += char
            elif char == ')' or char == '>':
                depth -= 1
                current += char
            elif char == '-' and i + 1 < len(params_str) and params_str[i+1] == '>':
                # Function arrow ->, not a parameter separator
                current += "->"
                i += 1
            elif char == ',' and depth == 0:
                if current.strip():
                    param_parts.append(current.strip())
                current = ""
            else:
                current += char
            i += 1
        if current.strip():
            param_parts.append(current.strip())
        
        # Parse each parameter
        for param_str in param_parts:
            param_str = param_str.strip()
            if not param_str:
                continue
            
            # Pattern: (label )?name: Type
            match = re.match(r'(?:(\w+)\s+)?(\w+)\s*:\s*(.+)', param_str)
            if match:
                label = match.group(1)
                param_name = match.group(2)
                param_type = match.group(3).strip()
                parameters.append({
                    'name': param_name,
                    'label': label,
                    'type': param_type
                })
    
    return {
        'name': name,
        'parameters': parameters,
        'returnType': return_type
    }

def parse_gleam_file(file_path: Path) -> Dict[str, Any]:
    """Parse a Gleam file and extract module and function information."""
    content = file_path.read_text()
    
    # Extract module name from path
    rel_path = file_path.relative_to('gleam-stdlib/src')
    module_name = str(rel_path).replace('.gleam', '').replace('/', '.')
    
    # Extract module-level documentation (//// comments)
    module_doc_match = re.search(r'^////\s*(.+?)(?=\n\n|\n[^/]|\Z)', content, re.MULTILINE | re.DOTALL)
    module_description = ''
    if module_doc_match:
        module_description = module_doc_match.group(1).strip()
    
    # Find all public functions
    functions = []
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a public function
        if line.strip().startswith('pub fn '):
            # Collect documentation before the function
            doc_lines = []
            j = i - 1
            while j >= 0 and lines[j].strip().startswith('///'):
                doc_lines.insert(0, lines[j])
                j -= 1
            
            doc_text = '\n'.join(doc_lines)
            
            # Parse function signature (may span multiple lines)
            func_info = parse_function_signature(lines, i)
            if func_info:
                # Extract purpose from first doc line (skip empty lines)
                purpose = ''
                for doc_line in doc_lines:
                    clean_line = doc_line.replace('///', '').strip()
                    if clean_line and not clean_line.startswith('##'):
                        purpose = clean_line
                        break
                
                # Extract why helpful from documentation (before Examples section)
                why_helpful = ''
                # Remove Examples section and code blocks for whyHelpful extraction
                doc_for_helpful = re.sub(r'## Examples.*', '', doc_text, flags=re.DOTALL)
                doc_for_helpful = re.sub(r'```.*?```', '', doc_for_helpful, flags=re.DOTALL)
                
                # Look for sentences explaining usefulness
                helpful_patterns = [
                    r'This function[^.]+\.[^.]*\.',
                    r'Useful[^.]+\.[^.]*\.',
                    r'This[^.]+\.[^.]*\.',
                ]
                for pattern in helpful_patterns:
                    helpful_match = re.search(pattern, doc_for_helpful, re.IGNORECASE)
                    if helpful_match:
                        why_helpful = helpful_match.group(0).strip()
                        # Clean up - remove markdown and extra whitespace
                        why_helpful = re.sub(r'///', '', why_helpful)
                        why_helpful = re.sub(r'```.*', '', why_helpful)  # Remove any remaining markdown
                        why_helpful = ' '.join(why_helpful.split())
                        # Only use if it's a reasonable length and doesn't contain markdown
                        if len(why_helpful) > 10 and '```' not in why_helpful:
                            break
                        else:
                            why_helpful = ''
                
                # If no specific helpful text, use second doc line if available
                if not why_helpful and len(doc_lines) > 1:
                    for doc_line in doc_lines[1:]:
                        clean_line = doc_line.replace('///', '').strip()
                        if clean_line and not clean_line.startswith('##') and '```' not in clean_line and len(clean_line) < 200 and len(clean_line) > 10:
                            why_helpful = clean_line
                            break
                
                # Extract examples
                examples = extract_examples(doc_text)
                
                func_info['purpose'] = purpose
                func_info['whyHelpful'] = why_helpful
                func_info['examples'] = examples
                func_info['module'] = module_name
                
                functions.append(func_info)
        
        i += 1
    
    return {
        'name': module_name,
        'description': module_description,
        'functions': functions
    }

def generate_module_jsonld(module_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate JSON-LD structure for a module."""
    module_id = module_data['name'].replace('.', '_').replace('/', '_')
    
    # Create function nodes
    function_nodes = []
    for func in module_data['functions']:
        func_id = f"ex:{module_id}_{func['name']}"
        function_node = {
            '@id': func_id,
            '@type': 'Function',
            'name': func['name'],
            'module': module_data['name'],
            'purpose': func.get('purpose', ''),
            'parameters': func.get('parameters', []),
            'returnType': func.get('returnType', ''),
            'whyHelpful': func.get('whyHelpful', ''),
            'examples': func.get('examples', [])
        }
        function_nodes.append(function_node)
    
    # Create module node
    module_node = {
        '@id': f"ex:{module_id}_module",
        '@type': 'Module',
        'name': module_data['name'],
        'description': module_data.get('description', ''),
        'functions': [{'@id': fn['@id']} for fn in function_nodes]
    }
    
    return {
        '@context': {
            '@vocab': 'https://aalang.org/spec',
            'ex': 'https://aalang.org/example/'
        },
        '@graph': [module_node] + function_nodes
    }

def generate_docs_jsonld(modules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate the main docs.jsonld index file."""
    module_refs = []
    for module_data in modules:
        module_id = module_data['name'].replace('.', '_').replace('/', '_')
        module_refs.append({
            '@id': f"ex:{module_id}_module",
            'name': module_data['name'],
            'file': f"{module_data['name'].replace('.', '/')}.jsonld",
            'functionCount': len(module_data['functions'])
        })
    
    return {
        '@context': {
            '@vocab': 'https://aalang.org/spec',
            'ex': 'https://aalang.org/example/'
        },
        '@graph': [
            {
                '@id': 'ex:docs_index',
                '@type': 'DocumentationIndex',
                'modules': module_refs,
                'typesFile': 'gleam/gleam-types.jsonld'
            }
        ]
    }

def generate_types_jsonld() -> Dict[str, Any]:
    """Generate gleam-types.jsonld with type system definitions."""
    types = [
        {
            '@id': 'ex:Result',
            '@type': 'Type',
            'name': 'Result',
            'description': 'Represents the result of something that may succeed or not. Ok means it was successful, Error means it was not successful.',
            'constructors': [
                {'name': 'Ok', 'description': 'Successful result', 'parameters': ['a']},
                {'name': 'Error', 'description': 'Error result', 'parameters': ['e']}
            ]
        },
        {
            '@id': 'ex:Option',
            '@type': 'Type',
            'name': 'Option',
            'description': 'Represents a value that may be present or not. Some means the value is present, None means the value is not.',
            'constructors': [
                {'name': 'Some', 'description': 'Value is present', 'parameters': ['a']},
                {'name': 'None', 'description': 'Value is not present', 'parameters': []}
            ]
        },
        {
            '@id': 'ex:List',
            '@type': 'Type',
            'name': 'List',
            'description': 'An ordered sequence of elements. New elements can be added and removed from the front in constant time.',
            'constructors': []
        },
        {
            '@id': 'ex:Dict',
            '@type': 'Type',
            'name': 'Dict',
            'description': 'A dictionary of keys and values. Each key can only be present once. Dicts are not ordered.',
            'constructors': []
        },
        {
            '@id': 'ex:Order',
            '@type': 'Type',
            'name': 'Order',
            'description': 'Represents the ordering relationship between two values.',
            'constructors': [
                {'name': 'Lt', 'description': 'Less than'},
                {'name': 'Eq', 'description': 'Equal'},
                {'name': 'Gt', 'description': 'Greater than'}
            ]
        }
    ]
    
    return {
        '@context': {
            '@vocab': 'https://aalang.org/spec',
            'ex': 'https://aalang.org/example/'
        },
        '@graph': types
    }

def main():
    """Main function to generate all documentation files."""
    stdlib_path = Path('gleam-stdlib/src/gleam')
    
    # Parse all modules
    modules = []
    for file_path in sorted(stdlib_path.rglob('*.gleam')):
        try:
            module_data = parse_gleam_file(file_path)
            if module_data['functions']:  # Only include modules with functions
                modules.append(module_data)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            continue
    
    # Generate docs.jsonld
    docs_data = generate_docs_jsonld(modules)
    with open('docs.jsonld', 'w') as f:
        json.dump(docs_data, f, indent=2)
    print(f"Generated docs.jsonld with {len(modules)} modules")
    
    # Generate gleam/gleam-types.jsonld
    types_data = generate_types_jsonld()
    with open('gleam/gleam-types.jsonld', 'w') as f:
        json.dump(types_data, f, indent=2)
    print("Generated gleam/gleam-types.jsonld")
    
    # Generate module files
    for module_data in modules:
        module_jsonld = generate_module_jsonld(module_data)
        # Create directory structure
        module_file = module_data['name'].replace('.', '/') + '.jsonld'
        file_path = Path(module_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(module_jsonld, f, indent=2)
        print(f"Generated {module_file} with {len(module_data['functions'])} functions")

if __name__ == '__main__':
    main()

