"""
DOI Resolver Module for ckanext-schemingdcat

Resolves DOI identifiers to retrieve metadata from various providers:
- DataCite API
- CrossRef API
- Zenodo API
- DOI.org content negotiation

Used for auto-filling document metadata in IHP-WINS.
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import quote, urlparse, urlunparse, urljoin

import requests
from ckan.common import config

log = logging.getLogger(__name__)

# DOI regex pattern
DOI_PATTERN = re.compile(r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$', re.IGNORECASE)

# API endpoints
DATACITE_API = "https://api.datacite.org/dois/{doi}"
CROSSREF_API = "https://api.crossref.org/works/{doi}"
ZENODO_API = "https://zenodo.org/api/records/{record_id}"
DOI_ORG_API = "https://doi.org/{doi}"

# Request timeout in seconds
REQUEST_TIMEOUT = 15

# User agent for API requests
USER_AGENT = "ckanext-schemingdcat/1.0 (IHP-WINS; UNESCO)"


def validate_doi(doi: str) -> bool:
    """
    Validate if a string is a valid DOI format.
    
    Args:
        doi: The DOI string to validate
        
    Returns:
        True if valid DOI format, False otherwise
    """
    if not doi:
        return False
    
    # Clean DOI
    doi = clean_doi(doi)
    
    return bool(DOI_PATTERN.match(doi))


def clean_doi(doi: str) -> str:
    """
    Clean and normalize a DOI string.
    
    Handles various input formats:
    - Full URL: https://doi.org/10.1234/example
    - dx.doi.org URL: http://dx.doi.org/10.1234/example
    - doi: prefix: doi:10.1234/example
    - Plain DOI: 10.1234/example
    
    Args:
        doi: The DOI string to clean
        
    Returns:
        Cleaned DOI string (just the identifier part)
    """
    if not doi:
        return ""
    
    doi = doi.strip()
    
    # Remove common URL prefixes
    prefixes = [
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi.org/",
        "dx.doi.org/",
        "doi:",
        "DOI:",
    ]
    
    for prefix in prefixes:
        if doi.lower().startswith(prefix.lower()):
            doi = doi[len(prefix):]
            break
    
    return doi.strip()


def extract_zenodo_record_id(doi: str) -> Optional[str]:
    """
    Extract Zenodo record ID from a Zenodo DOI.
    
    Zenodo DOIs follow the pattern: 10.5281/zenodo.{record_id}
    
    Args:
        doi: The DOI string
        
    Returns:
        Zenodo record ID if found, None otherwise
    """
    doi = clean_doi(doi)
    
    if doi.startswith("10.5281/zenodo."):
        return doi.replace("10.5281/zenodo.", "")
    
    return None


def _make_request(url: str, headers: Dict[str, str] = None) -> Optional[Dict]:
    """
    Make an HTTP GET request with error handling.
    
    Args:
        url: The URL to request
        headers: Optional headers dict
        
    Returns:
        JSON response as dict, or None on error
    """
    default_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        response = requests.get(
            url,
            headers=default_headers,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        log.warning(f"Request timeout for URL: {url}")
    except requests.exceptions.HTTPError as e:
        log.warning(f"HTTP error for URL {url}: {e}")
    except requests.exceptions.RequestException as e:
        log.warning(f"Request error for URL {url}: {e}")
    except json.JSONDecodeError as e:
        log.warning(f"JSON decode error for URL {url}: {e}")
    
    return None


def _prefer_https(url: str) -> str:
    """
    Upgrade http URLs to https when the host is not local/private.
    """
    if not url:
        return ""

    url = url.strip()

    try:
        parsed = urlparse(url)
    except Exception:
        return url

    if parsed.scheme != "http":
        return url

    hostname = (parsed.hostname or "").lower()
    if hostname in ("localhost", "127.0.0.1"):
        return url
    if re.match(r"^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname):
        return url
    if re.match(r"^192\.168\.\d{1,3}\.\d{1,3}$", hostname):
        return url

    secure = parsed._replace(scheme="https")
    return urlunparse(secure)


def _format_priority(fmt: str) -> int:
    """
    Rank formats to keep the most useful entry when deduplicating links.
    """
    if not fmt:
        return 0
    fmt = fmt.upper()
    if fmt == "PDF":
        return 3
    if fmt in ("HTML", "HTM"):
        return 2
    return 1


def _infer_format_from_url(url: str) -> str:
    """
    Infer a file format from a URL path extension.
    """
    if not url:
        return ""
    try:
        path = urlparse(url).path or ""
    except Exception:
        return ""
    filename = path.rsplit("/", 1)[-1]
    if "." not in filename:
        return ""
    ext = filename.rsplit(".", 1)[-1].strip()
    if not ext:
        return ""
    ext = ext.upper()
    if ext == "HTM":
        return "HTML"
    return ext


def _normalize_files(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize and deduplicate file/link entries.

    - Prefer https over http for non-local hosts
    - Remove duplicates by URL, keeping the entry with the richest data/format
    - Normalize formats to uppercase and drop UNSPECIFIED noise
    """
    normalized: List[Dict[str, Any]] = []
    seen: Dict[str, Dict[str, Any]] = {}

    for file in files or []:
        if not isinstance(file, dict):
            continue

        raw_url = file.get("url", "") or ""
        url = _prefer_https(raw_url)
        if not url:
            continue

        fmt = (file.get("format") or "").upper()
        if fmt == "UNSPECIFIED":
            fmt = ""

        entry = {
            "filename": file.get("filename", ""),
            "url": url,
            "description": file.get("description", ""),
            "format": fmt,
            "content_type": file.get("content_type", ""),
            "size": file.get("size"),
            "checksum": file.get("checksum", ""),
        }

        key = url.lower()
        if key in seen:
            existing = seen[key]
            # Keep the entry with the best-known format
            if _format_priority(fmt) > _format_priority(existing.get("format")):
                existing["format"] = fmt
                if entry.get("content_type"):
                    existing["content_type"] = entry["content_type"]

            # Fill in any missing metadata from the new entry
            for field in ("filename", "description", "size", "checksum"):
                if not existing.get(field) and entry.get(field):
                    existing[field] = entry[field]
            continue

        normalized.append(entry)
        seen[key] = entry

    return normalized


def _normalize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize resolver output before returning it to the client.
    """
    if not result:
        return result

    normalized = dict(result)
    if "url" in normalized:
        normalized["url"] = _prefer_https(normalized.get("url", ""))
    normalized["files"] = _normalize_files(normalized.get("files", []))
    return normalized


def fetch_from_datacite(doi: str) -> Optional[Dict[str, Any]]:
    """
    Fetch metadata from DataCite API.
    
    Args:
        doi: The DOI to look up
        
    Returns:
        Normalized metadata dict or None
    """
    doi = clean_doi(doi)
    url = DATACITE_API.format(doi=quote(doi, safe=''))
    
    data = _make_request(url)
    
    if not data or 'data' not in data:
        return None
    
    attributes = data['data'].get('attributes', {})
    
    # Extract authors
    authors = []
    for creator in attributes.get('creators', []):
        author = {
            'name': creator.get('name', ''),
            'given_name': creator.get('givenName', ''),
            'family_name': creator.get('familyName', ''),
            'orcid': '',
            'affiliation': '',
        }
        
        # Extract ORCID from nameIdentifiers
        for identifier in creator.get('nameIdentifiers', []):
            if identifier.get('nameIdentifierScheme') == 'ORCID':
                orcid = identifier.get('nameIdentifier', '')
                # Clean ORCID URL to just the ID
                if 'orcid.org/' in orcid:
                    orcid = orcid.split('orcid.org/')[-1]
                author['orcid'] = orcid
        
        # Extract affiliation
        affiliations = creator.get('affiliation', [])
        if affiliations:
            if isinstance(affiliations[0], dict):
                author['affiliation'] = affiliations[0].get('name', '')
            else:
                author['affiliation'] = affiliations[0]
        
        authors.append(author)
    
    # Extract publication year
    pub_year = attributes.get('publicationYear')
    
    # Extract dates
    dates = {}
    for date_item in attributes.get('dates', []):
        date_type = date_item.get('dateType', '').lower()
        dates[date_type] = date_item.get('date', '')
    
    # Extract subjects/keywords
    keywords = []
    for subject in attributes.get('subjects', []):
        if isinstance(subject, dict):
            keywords.append(subject.get('subject', ''))
        else:
            keywords.append(subject)
    
    # Map resource type
    resource_type = attributes.get('types', {}).get('resourceTypeGeneral', '')
    document_type = _map_datacite_type(resource_type)
    
    # Get license
    rights = attributes.get('rightsList', [])
    license_info = rights[0] if rights else {}
    
    return {
        'source': 'datacite',
        'doi': doi,
        'title': _get_first_title(attributes.get('titles', [])),
        'title_translations': _get_title_translations(attributes.get('titles', [])),
        'abstract': _get_first_description(attributes.get('descriptions', [])),
        'abstract_translations': _get_description_translations(attributes.get('descriptions', [])),
        'authors': authors,
        'publication_year': pub_year,
        'publisher': attributes.get('publisher', ''),
        'document_type': document_type,
        'resource_type_general': resource_type,
        'keywords': keywords,
        'language': attributes.get('language', ''),
        'license': license_info.get('rights', ''),
        'license_uri': license_info.get('rightsUri', ''),
        'version': attributes.get('version', ''),
        'created_date': dates.get('created', ''),
        'issued_date': dates.get('issued', '') or str(pub_year) if pub_year else '',
        'url': attributes.get('url', ''),
        # Add files/resources info - DataCite provides the landing page URL
        'files': [{
            'filename': '',
            'url': attributes.get('url', ''),
            'description': 'Document landing page',
            'format': '',
        }] if attributes.get('url') else [],
    }


def fetch_from_crossref(doi: str) -> Optional[Dict[str, Any]]:
    """
    Fetch metadata from CrossRef API.
    
    Args:
        doi: The DOI to look up
        
    Returns:
        Normalized metadata dict or None
    """
    doi = clean_doi(doi)
    url = CROSSREF_API.format(doi=quote(doi, safe=''))
    
    data = _make_request(url)
    
    if not data or 'message' not in data:
        return None
    
    message = data['message']
    
    # Extract authors
    authors = []
    for author in message.get('author', []):
        author_data = {
            'name': f"{author.get('given', '')} {author.get('family', '')}".strip(),
            'given_name': author.get('given', ''),
            'family_name': author.get('family', ''),
            'orcid': author.get('ORCID', '').replace('http://orcid.org/', '').replace('https://orcid.org/', ''),
            'affiliation': '',
        }
        
        affiliations = author.get('affiliation', [])
        if affiliations:
            author_data['affiliation'] = affiliations[0].get('name', '')
        
        authors.append(author_data)
    
    # Get title
    titles = message.get('title', [])
    title = titles[0] if titles else ''
    
    # Get abstract
    abstract = message.get('abstract', '')
    # CrossRef abstracts often have JATS XML tags
    if abstract:
        abstract = re.sub(r'<[^>]+>', '', abstract)
    
    # Get publication year
    pub_year = None
    published = message.get('published', message.get('published-print', message.get('published-online', {})))
    if published and 'date-parts' in published:
        date_parts = published['date-parts'][0]
        if date_parts:
            pub_year = date_parts[0]
    
    # Map type
    crossref_type = message.get('type', '')
    document_type = _map_crossref_type(crossref_type)
    
    # Get subjects
    keywords = message.get('subject', [])
    
    # Get license
    licenses = message.get('license', [])
    license_info = licenses[0] if licenses else {}
    
    return {
        'source': 'crossref',
        'doi': doi,
        'title': title,
        'title_translations': {},
        'abstract': abstract,
        'abstract_translations': {},
        'authors': authors,
        'publication_year': pub_year,
        'publisher': message.get('publisher', ''),
        'document_type': document_type,
        'resource_type_general': crossref_type,
        'keywords': keywords,
        'language': message.get('language', ''),
        'license': license_info.get('URL', ''),
        'license_uri': license_info.get('URL', ''),
        'version': '',
        'created_date': '',
        'issued_date': str(pub_year) if pub_year else '',
        'url': message.get('URL', ''),
        'container_title': message.get('container-title', [''])[0] if message.get('container-title') else '',
        'issn': message.get('ISSN', [''])[0] if message.get('ISSN') else '',
        # Add files/resources info - CrossRef provides links to the document
        'files': _extract_crossref_links(message),
    }


def _extract_crossref_links(message: Dict) -> List[Dict[str, Any]]:
    """
    Extract downloadable links from CrossRef message.
    
    Args:
        message: CrossRef API message dict
        
    Returns:
        List of file/link dicts
    """
    files = []

    landing_url = message.get('resource', {}).get('primary', {}).get('URL') or message.get('URL')

    # Primary/landing page
    if landing_url:
        files.append({
            'filename': '',
            'url': landing_url,
            'description': 'Publisher page',
            'format': 'HTML',
        })

    pdf_from_landing = _extract_pdf_from_landing(landing_url) if landing_url else None
    landing_host = urlparse(landing_url).hostname.lower() if landing_url else None
    pdf_host = urlparse(pdf_from_landing).hostname.lower() if pdf_from_landing else None
    if pdf_from_landing:
        files.append({
            'filename': '',
            'url': pdf_from_landing,
            'description': 'Full text (PDF)',
            'format': 'PDF',
        })
    
    # Check for PDF links
    for link in message.get('link', []):
        content_type = link.get('content-type', '')
        url = link.get('URL', '')
        
        if url:
            file_format = ''
            if content_type:
                file_format = 'PDF' if 'pdf' in content_type.lower() else content_type.split('/')[-1].upper()
            if not file_format:
                file_format = _infer_format_from_url(url)
            host = urlparse(url).hostname.lower() if url else None

            if not file_format and pdf_from_landing and host and (host == pdf_host or host == landing_host):
                continue

            # If we already captured a PDF from the landing page, skip CrossRef PDFs on the same host
            if pdf_from_landing and file_format == 'PDF' and pdf_host and host == pdf_host:
                continue

            description = f'Full text ({file_format})' if file_format else 'Full text'
            files.append({
                'filename': '',
                'url': url,
                'description': description,
                'format': file_format,
                'content_type': content_type,
            })
    
    return files


def _extract_pdf_from_landing(landing_url: str) -> Optional[str]:
    """
    Attempt to locate a PDF link from the landing page (e.g., via citation_pdf_url meta tag).
    """
    if not landing_url:
        return None

    try:
        resp = requests.get(
            landing_url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as e:
        log.debug(f"Could not fetch landing page {landing_url}: {e}")
        return None

    html = resp.text or ""

    # Look for standard meta tag used by many journal platforms (OJS, etc.)
    meta_match = re.search(
        r'<meta[^>]+name=[\"\']citation_pdf_url[\"\'][^>]+content=[\"\']([^\"\']+)[\"\']',
        html,
        flags=re.IGNORECASE,
    )
    if meta_match:
        pdf_url = meta_match.group(1).strip()
        return _prefer_https(urljoin(resp.url, pdf_url))

    # Fallback: any href pointing to a PDF
    href_match = re.search(
        r'<a[^>]+href=[\"\']([^\"\']+\\.pdf[^\"\']*)[\"\']',
        html,
        flags=re.IGNORECASE,
    )
    if href_match:
        pdf_url = href_match.group(1).strip()
        return _prefer_https(urljoin(resp.url, pdf_url))

    return None


def fetch_from_zenodo(doi: str) -> Optional[Dict[str, Any]]:
    """
    Fetch metadata from Zenodo API.
    
    Args:
        doi: The DOI to look up (must be a Zenodo DOI)
        
    Returns:
        Normalized metadata dict or None
    """
    record_id = extract_zenodo_record_id(doi)
    
    if not record_id:
        return None
    
    url = ZENODO_API.format(record_id=record_id)
    
    data = _make_request(url)
    
    if not data:
        return None
    
    metadata = data.get('metadata', {})
    
    # Extract authors
    authors = []
    for creator in metadata.get('creators', []):
        author = {
            'name': creator.get('name', ''),
            'given_name': '',
            'family_name': '',
            'orcid': creator.get('orcid', ''),
            'affiliation': creator.get('affiliation', ''),
        }
        
        # Try to split name into given/family
        name_parts = creator.get('name', '').split(', ')
        if len(name_parts) == 2:
            author['family_name'] = name_parts[0]
            author['given_name'] = name_parts[1]
        
        authors.append(author)
    
    # Get keywords
    keywords = metadata.get('keywords', [])
    
    # Map resource type
    resource_type = metadata.get('resource_type', {}).get('type', '')
    document_type = _map_zenodo_type(resource_type)
    
    # Get license
    license_id = metadata.get('license', {}).get('id', '') if isinstance(metadata.get('license'), dict) else metadata.get('license', '')
    
    # Get files info - normalize to consistent format
    files = []
    for file_info in data.get('files', []):
        filename = file_info.get('key', '')
        # Detect format from filename
        file_format = filename.split('.')[-1].upper() if '.' in filename else ''
        
        files.append({
            'filename': filename,
            'url': file_info.get('links', {}).get('self', ''),
            'description': f'Zenodo file: {filename}',
            'format': file_format,
            'size': file_info.get('size', 0),
            'checksum': file_info.get('checksum', ''),
        })
    
    return {
        'source': 'zenodo',
        'doi': clean_doi(doi),
        'title': metadata.get('title', ''),
        'title_translations': {},
        'abstract': metadata.get('description', ''),
        'abstract_translations': {},
        'authors': authors,
        'publication_year': metadata.get('publication_date', '')[:4] if metadata.get('publication_date') else None,
        'publisher': 'Zenodo',
        'document_type': document_type,
        'resource_type_general': resource_type,
        'keywords': keywords,
        'language': metadata.get('language', ''),
        'license': license_id,
        'license_uri': '',
        'version': metadata.get('version', ''),
        'created_date': data.get('created', ''),
        'issued_date': metadata.get('publication_date', ''),
        'url': data.get('links', {}).get('html', ''),
        'zenodo_id': record_id,
        'files': files,
        'communities': [c.get('id') for c in metadata.get('communities', [])],
    }


def resolve_doi(doi: str, providers: List[str] = None) -> Optional[Dict[str, Any]]:
    """
    Resolve a DOI using multiple providers with fallback.
    
    Args:
        doi: The DOI to resolve
        providers: List of providers to try, in order. 
                   Options: 'datacite', 'crossref', 'zenodo'
                   Default: ['zenodo', 'datacite', 'crossref']
        
    Returns:
        Normalized metadata dict from first successful provider, or None
    """
    doi = clean_doi(doi)
    
    if not validate_doi(doi):
        log.warning(f"Invalid DOI format: {doi}")
        return None
    
    # Default provider order
    if providers is None:
        # Check if it's a Zenodo DOI first
        if doi.startswith("10.5281/zenodo."):
            providers = ['zenodo', 'datacite', 'crossref']
        else:
            providers = ['datacite', 'crossref']
    
    provider_functions = {
        'datacite': fetch_from_datacite,
        'crossref': fetch_from_crossref,
        'zenodo': fetch_from_zenodo,
    }
    
    for provider in providers:
        if provider not in provider_functions:
            log.warning(f"Unknown DOI provider: {provider}")
            continue
        
        log.info(f"Trying DOI provider: {provider} for DOI: {doi}")
        
        try:
            result = provider_functions[provider](doi)
            if result:
                log.info(f"Successfully resolved DOI {doi} using {provider}")
                return _normalize_result(result)
        except Exception as e:
            log.error(f"Error with provider {provider} for DOI {doi}: {e}")
    
    log.warning(f"Could not resolve DOI {doi} with any provider")
    return None


# Helper functions for type mapping

def _get_first_title(titles: List) -> str:
    """Get the first/main title from a list of titles."""
    for title in titles:
        if isinstance(title, dict):
            if not title.get('titleType'):
                return title.get('title', '')
        else:
            return title
    
    # Fallback to first title regardless of type
    if titles:
        first = titles[0]
        return first.get('title', '') if isinstance(first, dict) else first
    
    return ''


def _get_title_translations(titles: List) -> Dict[str, str]:
    """Extract translated titles from a list of titles."""
    translations = {}
    for title in titles:
        if isinstance(title, dict):
            lang = title.get('lang', '')
            if lang:
                translations[lang] = title.get('title', '')
    return translations


def _get_first_description(descriptions: List) -> str:
    """Get the first abstract/description from a list."""
    for desc in descriptions:
        if isinstance(desc, dict):
            desc_type = desc.get('descriptionType', '')
            if desc_type in ('Abstract', ''):
                return desc.get('description', '')
        else:
            return desc
    
    # Fallback
    if descriptions:
        first = descriptions[0]
        return first.get('description', '') if isinstance(first, dict) else first
    
    return ''


def _get_description_translations(descriptions: List) -> Dict[str, str]:
    """Extract translated descriptions from a list."""
    translations = {}
    for desc in descriptions:
        if isinstance(desc, dict):
            lang = desc.get('lang', '')
            if lang and desc.get('descriptionType') in ('Abstract', ''):
                translations[lang] = desc.get('description', '')
    return translations


def _map_datacite_type(resource_type: str) -> str:
    """Map DataCite resource type to document type."""
    type_mapping = {
        'Text': 'scientific_paper',
        'Dataset': 'dataset_documentation',
        'Report': 'technical_report',
        'JournalArticle': 'scientific_paper',
        'Book': 'book',
        'BookChapter': 'book_chapter',
        'ConferencePaper': 'conference_paper',
        'Dissertation': 'thesis',
        'Preprint': 'preprint',
        'Software': 'software_documentation',
        'Other': 'other',
    }
    return type_mapping.get(resource_type, 'other')


def _map_crossref_type(crossref_type: str) -> str:
    """Map CrossRef type to document type."""
    type_mapping = {
        'journal-article': 'scientific_paper',
        'book': 'book',
        'book-chapter': 'book_chapter',
        'proceedings-article': 'conference_paper',
        'dissertation': 'thesis',
        'report': 'technical_report',
        'dataset': 'dataset_documentation',
        'posted-content': 'preprint',
        'monograph': 'book',
        'reference-entry': 'reference',
    }
    return type_mapping.get(crossref_type, 'other')


def _map_zenodo_type(zenodo_type: str) -> str:
    """Map Zenodo resource type to document type."""
    type_mapping = {
        'publication': 'scientific_paper',
        'dataset': 'dataset_documentation',
        'software': 'software_documentation',
        'poster': 'poster',
        'presentation': 'presentation',
        'video': 'video',
        'image': 'image',
        'lesson': 'educational_material',
        'other': 'other',
    }
    return type_mapping.get(zenodo_type, 'other')
