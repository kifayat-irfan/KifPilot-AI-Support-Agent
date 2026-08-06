"""Built-in expansion rules for query expansion."""

import re
from typing import List, Dict, Any, Optional
from app.services.query_expansion.schemas import ExpansionRule


# Synonym rules - common synonyms for technical/business terms
SYNONYM_RULES: List[ExpansionRule] = [
    # General business
    ExpansionRule(pattern=r"\bHR\b", expansion="Human Resources", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bIT\b", expansion="Information Technology", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bCEO\b", expansion="Chief Executive Officer", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bCTO\b", expansion="Chief Technology Officer", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bCFO\b", expansion="Chief Financial Officer", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bCOO\b", expansion="Chief Operating Officer", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bVP\b", expansion="Vice President", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bSVP\b", expansion="Senior Vice President", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bCRM\b", expansion="Customer Relationship Management", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bERP\b", expansion="Enterprise Resource Planning", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bAPI\b", expansion="Application Programming Interface", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bSDK\b", expansion="Software Development Kit", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bUI\b", expansion="User Interface", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bUX\b", expansion="User Experience", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bKPI\b", expansion="Key Performance Indicator", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bROI\b", expansion="Return on Investment", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bSLA\b", expansion="Service Level Agreement", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bSOP\b", expansion="Standard Operating Procedure", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bQA\b", expansion="Quality Assurance", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bQC\b", expansion="Quality Control", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bR&D\b", expansion="Research and Development", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bB2B\b", expansion="Business to Business", rule_type="synonym", priority=10),
    ExpansionRule(pattern=r"\bB2C\b", expansion="Business to Consumer", rule_type="synonym", priority=10),
    
    # Technical terms
    ExpansionRule(pattern=r"\bDB\b", expansion="Database", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bML\b", expansion="Machine Learning", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bAI\b", expansion="Artificial Intelligence", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bNLP\b", expansion="Natural Language Processing", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bRAG\b", expansion="Retrieval Augmented Generation", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bLLM\b", expansion="Large Language Model", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bRAG\b", expansion="Retrieval Augmented Generation", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bCI/CD\b", expansion="Continuous Integration Continuous Deployment", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bDevOps\b", expansion="Development Operations", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bIaC\b", expansion="Infrastructure as Code", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bSaaS\b", expansion="Software as a Service", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bPaaS\b", expansion="Platform as a Service", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bIaaS\b", expansion="Infrastructure as a Service", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bGDPR\b", expansion="General Data Protection Regulation", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bHIPAA\b", expansion="Health Insurance Portability and Accountability Act", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bPCI\b", expansion="Payment Card Industry", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bSSO\b", expansion="Single Sign-On", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bMFA\b", expansion="Multi-Factor Authentication", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bRBAC\b", expansion="Role-Based Access Control", rule_type="synonym", priority=9),
    ExpansionRule(pattern=r"\bABAC\b", expansion="Attribute-Based Access Control", rule_type="synonym", priority=9),
    
    # Synonyms for common actions
    ExpansionRule(pattern=r"\bsearch\b", expansion="find", rule_type="synonym", priority=5),
    ExpansionRule(pattern=r"\bfind\b", expansion="search locate", rule_type="synonym", priority=5),
    ExpansionRule(pattern=r"\bget\b", expansion="retrieve fetch obtain", rule_type="synonym", priority=5),
    ExpansionRule(pattern=r"\bcreate\b", expansion="make generate build", rule_type="synonym", priority=5),
    ExpansionRule(pattern=r"\bupdate\b", expansion="modify edit change", rule_type="synonym", priority=5),
    ExpansionRule(pattern=r"\bdelete\b", expansion="remove erase", rule_type="synonym", priority=5),
    ExpansionRule(pattern=r"\blist\b", expansion="show display enumerate", rule_type="synonym", priority=5),
    ExpansionRule(pattern=r"\bshow\b", expansion="display view list", rule_type="synonym", priority=5),
    ExpansionRule(pattern=r"\bfilter\b", expansion="narrow refine", rule_type="synonym", priority=5),
    ExpansionRule(pattern=r"\bsort\b", expansion="order arrange", rule_type="synonym", priority=5),
]


# Abbreviation rules
ABBREVIATION_RULES: List[ExpansionRule] = [
    ExpansionRule(pattern=r"\bw/\b", expansion="with", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bw/o\b", expansion="without", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\betc\b", expansion="et cetera", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\be\.g\.\b", expansion="for example", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bi\.e\.\b", expansion="that is", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bvs\b", expansion="versus", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bvs\.\b", expansion="versus", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bapprox\b", expansion="approximately", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bmax\b", expansion="maximum", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bmin\b", expansion="minimum", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\badmin\b", expansion="administrator", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bconfig\b", expansion="configuration", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bparams\b", expansion="parameters", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bauth\b", expansion="authentication authorization", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\benv\b", expansion="environment", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bprod\b", expansion="production", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bdev\b", expansion="development", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bstaging\b", expansion="stage", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bqa\b", expansion="quality assurance", rule_type="abbreviation", priority=8),
    ExpansionRule(pattern=r"\bprod\b", expansion="production", rule_type="abbreviation", priority=8),
]


# Technical alias rules
TECHNICAL_ALIAS_RULES: List[ExpansionRule] = [
    # Programming languages
    ExpansionRule(pattern=r"\bJS\b", expansion="JavaScript", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bTS\b", expansion="TypeScript", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bPy\b", expansion="Python", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bRB\b", expansion="Ruby", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bGo\b", expansion="Golang", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bK8s\b", expansion="Kubernetes", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bTF\b", expansion="TensorFlow", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bPyTorch\b", expansion="PyTorch", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bReact\b", expansion="ReactJS", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bVue\b", expansion="VueJS", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bAngular\b", expansion="AngularJS", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bNext\b", expansion="NextJS", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bNuxt\b", expansion="NuxtJS", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bGraphQL\b", expansion="Graph Query Language", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bREST\b", expansion="Representational State Transfer", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bSQL\b", expansion="Structured Query Language", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bNoSQL\b", expansion="Not Only SQL", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bDocker\b", expansion="Container Platform", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bK8s\b", expansion="Kubernetes", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bAWS\b", expansion="Amazon Web Services", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bGCP\b", expansion="Google Cloud Platform", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bAzure\b", expansion="Microsoft Azure", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bVPC\b", expansion="Virtual Private Cloud", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bCDN\b", expansion="Content Delivery Network", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bDNS\b", expansion="Domain Name System", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bSSL\b", expansion="Secure Sockets Layer", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bTLS\b", expansion="Transport Layer Security", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bJWT\b", expansion="JSON Web Token", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bOAuth\b", expansion="Open Authorization", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bOIDC\b", expansion="OpenID Connect", rule_type="technical_alias", priority=7),
    ExpansionRule(pattern=r"\bSAML\b", expansion="Security Assertion Markup Language", rule_type="technical_alias", priority=7),
]


# Acronym rules (common acronyms that should be expanded)
ACRONYM_RULES: List[ExpansionRule] = [
    ExpansionRule(pattern=r"\bAPI\b", expansion="Application Programming Interface", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bSDK\b", expansion="Software Development Kit", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bREST\b", expansion="Representational State Transfer", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bSOAP\b", expansion="Simple Object Access Protocol", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bGraphQL\b", expansion="Graph Query Language", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bJSON\b", expansion="JavaScript Object Notation", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bXML\b", expansion="Extensible Markup Language", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bYAML\b", expansion="YAML Ain't Markup Language", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bHTML\b", expansion="HyperText Markup Language", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bCSS\b", expansion="Cascading Style Sheets", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bHTTP\b", expansion="HyperText Transfer Protocol", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bHTTPS\b", expansion="HyperText Transfer Protocol Secure", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bURL\b", expansion="Uniform Resource Locator", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bURI\b", expansion="Uniform Resource Identifier", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bUUID\b", expansion="Universally Unique Identifier", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bGUID\b", expansion="Globally Unique Identifier", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bMD5\b", expansion="Message Digest 5", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bSHA\b", expansion="Secure Hash Algorithm", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bAES\b", expansion="Advanced Encryption Standard", rule_type="acronym", priority=9),
    ExpansionRule(pattern=r"\bRSA\b", expansion="Rivest Shamir Adleman", rule_type="acronym", priority=9),
]


# Combined rules getter
def get_all_rules() -> List[ExpansionRule]:
    """Get all built-in expansion rules combined."""
    return (
        SYNONYM_RULES + 
        ABBREVIATION_RULES + 
        TECHNICAL_ALIAS_RULES + 
        ACRONYM_RULES
    )


def get_rules_by_type(rule_type: str) -> List[ExpansionRule]:
    """Get rules filtered by type."""
    rule_map = {
        "synonym": SYNONYM_RULES,
        "abbreviation": ABBREVIATION_RULES,
        "technical_alias": TECHNICAL_ALIAS_RULES,
        "acronym": ACRONYM_RULES,
    }
    return rule_map.get(rule_type, [])


# Pluralization rules (singular -> plural and vice versa)
PLURALIZATION_RULES: Dict[str, str] = {
    # Regular plurals
    "server": "servers",
    "database": "databases",
    "document": "documents",
    "chunk": "chunks",
    "index": "indices",
    "query": "queries",
    "search": "searches",
    "result": "results",
    "document": "documents",
    "chunk": "chunks",
    "embedding": "embeddings",
    "vector": "vectors",
    "model": "models",
    "token": "tokens",
    "parameter": "parameters",
    "argument": "arguments",
    "function": "functions",
    "method": "methods",
    "class": "classes",
    "object": "objects",
    "instance": "instances",
    "property": "properties",
    "attribute": "attributes",
    "variable": "variables",
    "constant": "constants",
    "module": "modules",
    "package": "packages",
    "library": "libraries",
    "framework": "frameworks",
    "service": "services",
    "endpoint": "endpoints",
    "route": "routes",
    "controller": "controllers",
    "middleware": "middlewares",
    "plugin": "plugins",
    "extension": "extensions",
    "feature": "features",
    "bug": "bugs",
    "issue": "issues",
    "ticket": "tickets",
    "task": "tasks",
    "story": "stories",
    "epic": "epics",
    "sprint": "sprints",
    "release": "releases",
    "version": "versions",
    "build": "builds",
    "deployment": "deployments",
    "environment": "environments",
    "configuration": "configurations",
    "setting": "settings",
    "option": "options",
    "flag": "flags",
    "flag": "flags",
    "switch": "switches",
    "toggle": "toggles",
    "filter": "filters",
    "sorter": "sorters",
    "paginator": "paginators",
    "cursor": "cursors",
    "iterator": "iterators",
    "generator": "generators",
    "stream": "streams",
    "channel": "channels",
    "topic": "topics",
    "partition": "partitions",
    "broker": "brokers",
    "consumer": "consumers",
    "producer": "producers",
    "subscriber": "subscribers",
    "publisher": "publishers",
    "event": "events",
    "message": "messages",
    "queue": "queues",
    "topic": "topics",
    "exchange": "exchanges",
    "binding": "bindings",
    "queue": "queues",
}

# Reverse mapping for singularization
SINGULAR_RULES: Dict[str, str] = {v: k for k, v in PLURALIZATION_RULES.items()}


def get_plural(word: str) -> Optional[str]:
    """Get plural form of a word."""
    word_lower = word.lower()
    if word_lower in PLURALIZATION_RULES:
        return PLURALIZATION_RULES[word_lower]
    # Default: add 's' or 'es'
    if word_lower.endswith(('s', 'x', 'z', 'ch', 'sh')):
        return word + 'es'
    elif word_lower.endswith('y') and not word_lower.endswith(('ay', 'ey', 'iy', 'oy', 'uy')):
        return word[:-1] + 'ies'
    return word + 's'


def get_singular(word: str) -> Optional[str]:
    """Get singular form of a word."""
    word_lower = word.lower()
    if word_lower in SINGULAR_RULES:
        return SINGULAR_RULES[word_lower]
    # Default: remove 's' or 'es'
    if word_lower.endswith('ies') and len(word) > 3:
        return word[:-3] + 'y'
    elif word_lower.endswith('es') and len(word) > 2:
        return word[:-2]
    elif word_lower.endswith('s') and len(word) > 1:
        return word[:-1]
    return word