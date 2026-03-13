"""
LogNomaly - Rule Engine
FR-04: Layer 1 — Kural tabanlı hızlı filtreleme
"""

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    name: str
    pattern: re.Pattern
    threat_type: str
    description: str


# ======================================================================
#  Varsayılan kural seti (genişletilebilir)
# ======================================================================
DEFAULT_RULES: list[Rule] = [
    Rule(
        name="BruteForce",
        pattern=re.compile(
            r'(failed (login|password|auth)|authentication failure|'
            r'invalid (user|password)|too many (attempts|failures))',
            re.IGNORECASE
        ),
        threat_type="BruteForce",
        description="Tekrarlanan başarısız kimlik doğrulama girişimi",
    ),
    Rule(
        name="SQLInjection",
        pattern=re.compile(
            r"(union\s+select|drop\s+table|insert\s+into|'--|\bOR\b\s+1=1|"
            r"xp_cmdshell|exec\s*\(|script>)",
            re.IGNORECASE
        ),
        threat_type="SQLi",
        description="SQL injection veya script enjeksiyonu",
    ),
    Rule(
        name="SystemFailure",
        pattern=re.compile(
            r'(kernel panic|out of memory|oom killer|segmentation fault|'
            r'stack overflow|fatal error|system crash|disk full)',
            re.IGNORECASE
        ),
        threat_type="SystemFailure",
        description="Kritik sistem hatası",
    ),
    Rule(
        name="PrivilegeEscalation",
        pattern=re.compile(
            r'(sudo|su root|privilege escalat|unauthorized access|'
            r'permission denied.*root|setuid)',
            re.IGNORECASE
        ),
        threat_type="PrivilegeEscalation",
        description="Yetki yükseltme girişimi",
    ),
    Rule(
        name="PortScan",
        pattern=re.compile(
            r'(port scan|nmap|masscan|syn flood|connection refused.*\d{4,5})',
            re.IGNORECASE
        ),
        threat_type="PortScan",
        description="Port tarama aktivitesi",
    ),
    Rule(
        name="MalwareIndicator",
        pattern=re.compile(
            r'(ransomware|malware|trojan|backdoor|c2|command.and.control|'
            r'\.exe.*download|base64.*payload)',
            re.IGNORECASE
        ),
        threat_type="Malware",
        description="Zararlı yazılım belirtisi",
    ),
]


# ======================================================================
#  Rule Engine
# ======================================================================
class RuleEngine:
    """
    FR-04: Yapılandırılmış log mesajlarını önceden tanımlı
    tehdit imzalarıyla karşılaştırır.
    """

    def __init__(self, rules: list[Rule] | None = None):
        self.rules: list[Rule] = rules if rules is not None else DEFAULT_RULES
        logger.info("RuleEngine başlatıldı: %d kural yüklendi", len(self.rules))

    def check(self, message: str) -> dict:
        """
        Tek bir log mesajını tüm kurallarla kontrol eder.

        Returns:
            {
              "is_known_threat": bool,
              "threat_type": str | None,
              "matched_rule": str | None,
              "description": str | None,
            }
        """
        for rule in self.rules:
            if rule.pattern.search(message):
                logger.debug("Kural eşleşti: %s — '%s'", rule.name, message[:60])
                return {
                    "is_known_threat": True,
                    "threat_type": rule.threat_type,
                    "matched_rule": rule.name,
                    "description": rule.description,
                }
        return {
            "is_known_threat": False,
            "threat_type": None,
            "matched_rule": None,
            "description": None,
        }

    def add_rule(self, rule: Rule):
        """Çalışma zamanında yeni kural ekle."""
        self.rules.append(rule)
        logger.info("Yeni kural eklendi: %s", rule.name)
