import config

def test_parse_valid_yaml():
    yaml_str = """
version: 1
rules:
  - text: "Never concatenate SQL queries."
    category: "security"
    priority: "critical"
  - text: "Validate external input."
    priority: "high"
architecture:
  - "We use httpx instead of requests."
  - "PostgreSQL in production."
"""
    parsed = config.parse_yaml(yaml_str)
    assert parsed.version == 1
    assert len(parsed.rules) == 2
    assert parsed.rules[0].text == "Never concatenate SQL queries."
    assert parsed.rules[0].priority == "critical"
    assert len(parsed.architecture) == 2

def test_parse_invalid_yaml():
    yaml_str = """
version: 1
rules:
  - text:
    - this is wrong
"""
    # Should catch ValidationError and return empty config
    parsed = config.parse_yaml(yaml_str)
    assert len(parsed.rules) == 0

def test_parse_empty_yaml():
    parsed = config.parse_yaml("")
    assert len(parsed.rules) == 0

def test_format_for_prompt():
    yaml_str = """
version: 1
rules:
  - text: "Critical rule"
    priority: "critical"
  - text: "High rule"
    priority: "high"
architecture:
  - "Arch decision"
"""
    parsed = config.parse_yaml(yaml_str)
    formatted = config.format_for_prompt(parsed, "test/repo")
    
    assert "Repository Engineering Rules" in formatted
    assert "Critical\n- Critical rule" in formatted
    assert "High\n- High rule" in formatted
    assert "Architecture Decisions\n- Arch decision" in formatted
    assert "Context\nRepository: test/repo" in formatted
