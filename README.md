# Gleam API Guide

An AALang tool that helps users discover and understand Gleam's built-in public functions through browsing, searching, and semantic queries.

## Overview

The Gleam API Guide is an API documentation tool (not a tutorial or code generation tool) that provides reference information about Gleam's standard library functions. It allows users to:

- Browse functions by module (e.g., `gleam/list`, `gleam/string`) or by type (e.g., `Result`, `Option`)
- Search for exact function names
- Query semantically (e.g., "functions that work with lists", "string manipulation functions")

For each function, the tool provides:
- **Purpose**: What the function does
- **Parameters**: Each parameter with its type
- **Return type**: What the function returns
- **Why helpful**: Use cases and benefits
- **Examples**: 3-4 single-line code examples showing how to call the function
- **Related functions**: Suggestions for similar or related functions

## Important Note

**This tool does NOT generate code, provide tutorials, or solve problems.** It only provides function documentation. When you ask "how do I..." or "how might I...", you will receive function documentation, not code solutions.

## Files

- `gleam-api-guide.jsonld` - The AALang agent specification defining the tool's behavior
- `docs.jsonld` - Main index file containing references to all module files
- `gleam/` - Directory containing generated JSON-LD documentation files:
  - `gleam-types.jsonld` - Type system definitions (Result, Option, List, etc.)
  - `gleam/*.jsonld` - One JSON-LD file per Gleam module with function documentation
- `generate_docs.py` - Python script that generates the documentation files

## Generating Documentation Files

The files in the `gleam/` directory are generated from the Gleam standard library source code. To regenerate them:

### Prerequisites

1. **Python 3** - Required to run the generation script
2. **Gleam Standard Library** - The source code repository

### Steps

1. **Clone the Gleam standard library repository:**
   ```bash
   git clone https://github.com/gleam-lang/stdlib.git gleam-stdlib
   ```

2. **Run the generation script:**
   ```bash
   python3 generate_docs.py
   ```

   The script will:
   - Parse all `.gleam` files in `gleam-stdlib/src/gleam/`
   - Extract function signatures, documentation, parameters, return types, and examples
   - Generate `docs.jsonld` (main index file)
   - Generate `gleam/gleam-types.jsonld` (type system definitions)
   - Generate one JSON-LD file per module in the `gleam/` directory

3. **Verify the output:**
   - Check that `docs.jsonld` was created/updated
   - Check that `gleam/gleam-types.jsonld` was created/updated
   - Check that module files in `gleam/` were created/updated (e.g., `gleam/list.jsonld`, `gleam/string.jsonld`)

### Generated File Structure

- **`docs.jsonld`**: Contains a `DocumentationIndex` node with references to all module files and the types file
- **`gleam/gleam-types.jsonld`**: Contains `Type` nodes with definitions for core Gleam types (Result, Option, List, Dict, Order) and their constructors
- **`gleam/*.jsonld`**: Each module file contains:
  - A `Module` node with module information and function references
  - `Function` nodes with full details (purpose, parameters, return types, why helpful, examples)

All files use JSON-LD format with `@graph` arrays containing the nodes.

## Using the Tool

The tool is defined in `gleam-api-guide.jsonld` as an AALang agent. To use it:

1. Load the agent specification in an AALang-compatible environment
2. The tool will present an initial response explaining how to use it
3. Interact with the tool to browse, search, or query Gleam functions

## Architecture

The tool implements a **1-mode-4-actor pattern**:

- **Mode**: `ReferenceMode` - Provides reference documentation for Gleam functions
- **Actors**:
  - `BrowseActor` - Enables browsing by module or type
  - `SearchActor` - Handles exact name searches
  - `QueryActor` - Handles semantic queries
  - `PresentationActor` - Formats and presents function information

## License

This project uses documentation from the Gleam standard library. Please refer to the Gleam project's license for details.

## Created with

The tool, documentation, and the generate_docs.py file were created using AALang and Gab

