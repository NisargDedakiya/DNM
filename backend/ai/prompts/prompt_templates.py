class PromptTemplates:
    """Modular templates for structured AI context injection."""

    FINDING_ANALYSIS = """
Analyze the following finding:
Title: {title}
Target: {target}
Severity: {severity}
Description: {description}

Please provide:
1. Exploitability Assessment
2. Business Impact
3. Recommended Next Steps
"""

    ATTACK_CHAIN_EXPLANATION = """
Analyze the following attack chain:
Chain Name: {chain_name}
Vulnerabilities: {findings_list}
Target Environment: {environment}

Please provide:
1. How an attacker could execute this chain
2. The blast radius of a successful compromise
"""
