import io
import os
import socket
import struct
import zipfile
from pathlib import PurePath


class FileValidationError(Exception):
    def __init__(self, code, status=400):
        super().__init__(code)
        self.code = code
        self.status = status


MAX_BYTES = 25 * 1024 * 1024
ALLOWED = {
    'application/pdf',
    'text/plain',
    'text/csv',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'image/png',
    'image/jpeg',
}
EXTENSIONS_BY_MIME = {
    'application/pdf': {'.pdf'},
    'text/plain': {'.txt'},
    'text/csv': {'.csv'},
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {'.docx'},
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': {'.xlsx'},
    'image/png': {'.png'},
    'image/jpeg': {'.jpg', '.jpeg'},
}


def _openxml_safe(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos = z.infolist()
            if len(infos) > 5000:
                return False
            total = sum(i.file_size for i in infos)
            compressed = sum(max(i.compress_size, 1) for i in infos)
            if total > 100 * 1024 * 1024 or total / compressed > 100:
                return False
            names = {i.filename for i in infos}
            return '[Content_Types].xml' in names and all(
                not n.startswith(('/', '\\')) and '..' not in n.split('/') for n in names
            )
    except zipfile.BadZipFile:
        return False


def _signature_ok(content_type, data):
    if content_type == 'application/pdf':
        return data.startswith(b'%PDF-')
    if content_type == 'image/png':
        return data.startswith(b'\x89PNG\r\n\x1a\n')
    if content_type == 'image/jpeg':
        return data.startswith(b'\xff\xd8\xff')
    if content_type in {'text/plain', 'text/csv'}:
        return b'\x00' not in data[:8192]
    if 'openxmlformats' in content_type:
        return data.startswith(b'PK\x03\x04') and _openxml_safe(data)
    return False


def validate_filename(filename, content_type):
    """Reject path tricks and extension/MIME disagreement before any storage write."""
    raw = str(filename or '').strip()
    if not raw or len(raw) > 255:
        raise FileValidationError('invalid_filename', 400)
    if '\x00' in raw or '/' in raw or '\\' in raw or PurePath(raw).name != raw:
        raise FileValidationError('unsafe_filename', 400)
    suffix = PurePath(raw).suffix.lower()
    if suffix not in EXTENSIONS_BY_MIME.get(content_type, set()):
        raise FileValidationError('file_extension_mime_mismatch', 415)
    return raw


def safe_storage_name(filename, fallback='document.bin'):
    raw = PurePath(str(filename or '')).name
    cleaned = ''.join(c for c in raw if c.isalnum() or c in '._-').strip(' .')[-180:]
    return cleaned or fallback


def _clamav(data):
    host = os.getenv('CLAMAV_HOST', '').strip()
    required = os.getenv('CLAMAV_REQUIRED', 'false').lower() == 'true'
    if not host:
        if required:
            raise FileValidationError('malware_scanner_unavailable', 503)
        return 'not_configured'
    port = int(os.getenv('CLAMAV_PORT', '3310'))
    try:
        with socket.create_connection((host, port), timeout=8) as sock:
            sock.sendall(b'zINSTREAM\0')
            for i in range(0, len(data), 65536):
                chunk = data[i:i + 65536]
                sock.sendall(struct.pack('!I', len(chunk)) + chunk)
            sock.sendall(struct.pack('!I', 0))
            reply = sock.recv(4096).decode(errors='replace')
        if 'FOUND' in reply:
            raise FileValidationError('malware_detected', 422)
        if 'OK' not in reply:
            raise FileValidationError('malware_scan_failed', 503)
        return 'clean'
    except FileValidationError:
        raise
    except OSError:
        if required:
            raise FileValidationError('malware_scanner_unavailable', 503)
        return 'unavailable_optional'


def clamav_readiness():
    host = os.getenv('CLAMAV_HOST', '').strip()
    required = os.getenv('CLAMAV_REQUIRED', 'false').lower() == 'true'
    if not host:
        return not required
    port = int(os.getenv('CLAMAV_PORT', '3310'))
    try:
        with socket.create_connection((host, port), timeout=3) as sock:
            sock.sendall(b'zPING\0')
            reply = sock.recv(128).decode(errors='replace')
        return 'PONG' in reply
    except OSError:
        return False


def validate_upload(upload):
    content_type = str(getattr(upload, 'content_type', '') or '').lower().strip()
    if content_type not in ALLOWED:
        raise FileValidationError('unsupported_file_type', 415)
    validate_filename(getattr(upload, 'name', ''), content_type)
    if upload.size > MAX_BYTES:
        raise FileValidationError('file_too_large', 413)
    data = upload.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise FileValidationError('file_too_large', 413)
    if not _signature_ok(content_type, data):
        raise FileValidationError('file_signature_mismatch', 415)
    scan_status = _clamav(data)
    upload.seek(0)
    return data, scan_status
