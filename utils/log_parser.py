"""
LogNomaly - Log Parser Module
FR-01: Log File Upload validation
FR-02: Log Parsing and Normalization
"""

import re
import os
import uuid
import logging
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.log', '.txt', '.csv'}
MAX_FILE_SIZE_MB = 50
TEMP_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'temp_uploads')

# Common log patterns (sırası önemli — en spesifikten genele)
LOG_PATTERNS = [
    # HDFS / BGL style: 2025-01-20 14:30:15 ERROR [AuthService] message
    re.compile(
        r'^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2})'
        r'\s+(?P<level>\w+)\s+\[(?P<service>[^\]]+)\]\s+(?P<message>.+)$'
    ),
    # Syslog style: Jan 20 14:30:15 hostname service[pid]: message
    re.compile(
        r'^(?P<date>\w{3}\s+\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})'
        r'\s+\S+\s+(?P<service>\S+?)(?:\[\d+\])?:\s+(?P<level>\w+)?\s*(?P<message>.+)$'
    ),
    # Simple: LEVEL message  or  LEVEL [service] message
    re.compile(
        r'^(?P<level>DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)'
        r'(?:\s+\[(?P<service>[^\]]+)\])?\s+(?P<message>.+)$',
        re.IGNORECASE
    ),
]

LEVEL_NORMALIZATION = {
    'WARN': 'WARNING',
    'FATAL': 'CRITICAL',
    'SEVERE': 'CRITICAL',
    'ERR': 'ERROR',
    'DBG': 'DEBUG',
    'INF': 'INFO',
}


class ValidationError(Exception):
    pass


class LogParser:
    """
    FR-01 + FR-02: Log dosyası doğrulama ve yapısal parse işlemleri.
    """

    def __init__(self, upload_dir: str = TEMP_UPLOAD_DIR):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  FR-01: Dosya doğrulama ve geçici kayıt                             #
    # ------------------------------------------------------------------ #
    def validate_and_save(self, file_storage) -> dict:
        """
        Werkzeug FileStorage nesnesini doğrular ve geçici dizine kaydeder.

        Returns:
            {"session_id": str, "file_path": str}
        Raises:
            ValidationError
        """
        filename = secure_filename(file_storage.filename)
        ext = os.path.splitext(filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"Geçersiz dosya uzantısı: '{ext}'. "
                f"İzin verilenler: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Boyut kontrolü (stream okumadan önce seek ile)
        file_storage.stream.seek(0, 2)          # sona git
        size_bytes = file_storage.stream.tell()
        file_storage.stream.seek(0)             # başa dön
        if size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValidationError(
                f"Dosya boyutu {size_bytes / (1024*1024):.1f} MB, "
                f"maksimum {MAX_FILE_SIZE_MB} MB."
            )

        session_id = str(uuid.uuid4())
        session_dir = os.path.join(self.upload_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        file_path = os.path.join(session_dir, filename)
        file_storage.save(file_path)
        logger.info("Dosya kaydedildi: %s (session=%s)", file_path, session_id)
        return {"session_id": session_id, "file_path": file_path}

    # ------------------------------------------------------------------ #
    #  FR-02: Parse & Normalize                                           #
    # ------------------------------------------------------------------ #
    def parse_file(self, file_path: str) -> pd.DataFrame:
        """
        Ham log dosyasını satır satır okur, yapısal DataFrame döndürür.

        Columns: date, time, level, service, message, raw
        """
        records = []
        unparseable = 0
        total = 0

        with open(file_path, 'r', encoding='utf-8', errors='replace') as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                total += 1
                parsed = self._parse_line(line)
                if parsed:
                    parsed['raw'] = line
                    records.append(parsed)
                else:
                    unparseable += 1
                    logger.debug("Parse edilemeyen satır: %s", line[:80])
                    records.append({
                        'date': None, 'time': None,
                        'level': 'UNKNOWN', 'service': 'UNKNOWN',
                        'message': line, 'raw': line,
                    })

        if total == 0:
            raise ValidationError("Dosya boş veya okunamıyor.")

        unparseable_ratio = unparseable / total
        if unparseable_ratio > 0.20:
            raise ValidationError(
                f"Satırların %{unparseable_ratio*100:.0f}'i parse edilemedi "
                f"({unparseable}/{total}). Geçersiz log formatı."
            )

        df = pd.DataFrame(records)
        df = self._normalize_levels(df)
        df = self._parse_timestamps(df)
        logger.info("Parse tamamlandı: %d satır, %d parse edilemedi", total, unparseable)
        return df

    # ------------------------------------------------------------------ #
    #  Yardımcı metodlar                                                  #
    # ------------------------------------------------------------------ #
    def _parse_line(self, line: str) -> dict | None:
        for pattern in LOG_PATTERNS:
            m = pattern.match(line)
            if m:
                gd = m.groupdict()
                return {
                    'date':    gd.get('date', ''),
                    'time':    gd.get('time', ''),
                    'level':   (gd.get('level') or 'INFO').upper(),
                    'service': gd.get('service') or 'UNKNOWN',
                    'message': (gd.get('message') or '').strip(),
                }
        return None

    def _normalize_levels(self, df: pd.DataFrame) -> pd.DataFrame:
        df['level'] = df['level'].str.upper().replace(LEVEL_NORMALIZATION)
        return df

    def _parse_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """date + time sütunlarını birleştirip datetime'a çevirir."""
        def _to_dt(row):
            try:
                return pd.to_datetime(f"{row['date']} {row['time']}")
            except Exception:
                return pd.NaT

        df['timestamp'] = df.apply(_to_dt, axis=1)
        return df

    # ------------------------------------------------------------------ #
    #  NFR-06: Geçici dosyaları temizle                                   #
    # ------------------------------------------------------------------ #
    def cleanup_session(self, session_id: str):
        """Parse tamamlandıktan sonra ham dosyayı sil (NFR-06)."""
        session_dir = os.path.join(self.upload_dir, session_id)
        import shutil
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            logger.info("Session temizlendi: %s", session_id)
