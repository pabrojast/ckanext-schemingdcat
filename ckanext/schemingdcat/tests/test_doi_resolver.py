"""
Tests for DOI Resolver module.

Tests the DOI validation, cleaning, and resolution functionality.
"""

import pytest
from unittest.mock import patch, MagicMock

from ckanext.schemingdcat.lib.doi_resolver import (
    validate_doi,
    clean_doi,
    extract_zenodo_record_id,
    resolve_doi,
    fetch_from_datacite,
    fetch_from_crossref,
    fetch_from_zenodo,
    _extract_pdf_from_landing,
    _normalize_files,
    _map_datacite_type,
    _map_crossref_type,
    _map_zenodo_type,
)


class TestDoiValidation:
    """Tests for DOI validation functions."""

    def test_validate_doi_valid_simple(self):
        """Test valid simple DOI."""
        assert validate_doi("10.1234/example") is True

    def test_validate_doi_valid_complex(self):
        """Test valid complex DOI with special characters."""
        assert validate_doi("10.1000/xyz123") is True
        assert validate_doi("10.5281/zenodo.1234567") is True
        assert validate_doi("10.1038/s41586-021-03819-2") is True

    def test_validate_doi_invalid_no_prefix(self):
        """Test invalid DOI without 10. prefix."""
        assert validate_doi("11.1234/example") is False
        assert validate_doi("example/1234") is False

    def test_validate_doi_invalid_empty(self):
        """Test invalid empty DOI."""
        assert validate_doi("") is False
        assert validate_doi(None) is False

    def test_validate_doi_with_url(self):
        """Test DOI validation with URL prefix (should be cleaned first)."""
        # The validate function cleans the DOI first
        assert validate_doi("https://doi.org/10.1234/example") is True
        assert validate_doi("http://dx.doi.org/10.1234/example") is True


class TestDoiCleaning:
    """Tests for DOI cleaning functions."""

    def test_clean_doi_plain(self):
        """Test cleaning plain DOI."""
        assert clean_doi("10.1234/example") == "10.1234/example"

    def test_clean_doi_https_url(self):
        """Test cleaning DOI from https://doi.org URL."""
        assert clean_doi("https://doi.org/10.1234/example") == "10.1234/example"

    def test_clean_doi_http_url(self):
        """Test cleaning DOI from http://doi.org URL."""
        assert clean_doi("http://doi.org/10.1234/example") == "10.1234/example"

    def test_clean_doi_dx_url(self):
        """Test cleaning DOI from dx.doi.org URL."""
        assert clean_doi("https://dx.doi.org/10.1234/example") == "10.1234/example"
        assert clean_doi("http://dx.doi.org/10.1234/example") == "10.1234/example"

    def test_clean_doi_prefix(self):
        """Test cleaning DOI with doi: prefix."""
        assert clean_doi("doi:10.1234/example") == "10.1234/example"
        assert clean_doi("DOI:10.1234/example") == "10.1234/example"

    def test_clean_doi_whitespace(self):
        """Test cleaning DOI with whitespace."""
        assert clean_doi("  10.1234/example  ") == "10.1234/example"

    def test_clean_doi_empty(self):
        """Test cleaning empty DOI."""
        assert clean_doi("") == ""
        assert clean_doi(None) == ""


class TestZenodoExtraction:
    """Tests for Zenodo record ID extraction."""

    def test_extract_zenodo_id_valid(self):
        """Test extracting valid Zenodo record ID."""
        assert extract_zenodo_record_id("10.5281/zenodo.1234567") == "1234567"

    def test_extract_zenodo_id_with_url(self):
        """Test extracting Zenodo ID from URL."""
        assert extract_zenodo_record_id("https://doi.org/10.5281/zenodo.9876543") == "9876543"

    def test_extract_zenodo_id_non_zenodo(self):
        """Test non-Zenodo DOI returns None."""
        assert extract_zenodo_record_id("10.1234/example") is None
        assert extract_zenodo_record_id("10.1038/nature12373") is None


class TestTypeMapping:
    """Tests for document type mapping functions."""

    def test_map_datacite_type_journal(self):
        """Test mapping DataCite journal article type."""
        assert _map_datacite_type("JournalArticle") == "scientific_paper"
        assert _map_datacite_type("Text") == "scientific_paper"

    def test_map_datacite_type_report(self):
        """Test mapping DataCite report type."""
        assert _map_datacite_type("Report") == "technical_report"

    def test_map_datacite_type_dataset(self):
        """Test mapping DataCite dataset type."""
        assert _map_datacite_type("Dataset") == "dataset_documentation"

    def test_map_datacite_type_unknown(self):
        """Test mapping unknown DataCite type."""
        assert _map_datacite_type("UnknownType") == "other"

    def test_map_crossref_type_article(self):
        """Test mapping CrossRef article type."""
        assert _map_crossref_type("journal-article") == "scientific_paper"

    def test_map_crossref_type_book(self):
        """Test mapping CrossRef book type."""
        assert _map_crossref_type("book") == "book"
        assert _map_crossref_type("book-chapter") == "book_chapter"

    def test_map_zenodo_type_publication(self):
        """Test mapping Zenodo publication type."""
        assert _map_zenodo_type("publication") == "scientific_paper"
        assert _map_zenodo_type("dataset") == "dataset_documentation"


class TestNormalizationHelpers:
    """Tests for DOI link normalization helpers."""

    def test_normalize_files_deduplicates_and_prefers_https(self):
        files = [
            {'url': 'http://example.com/file.pdf', 'format': 'unspecified', 'description': ''},
            {'url': 'http://example.com/file.pdf', 'format': 'PDF', 'description': 'Full text'},
        ]

        normalized = _normalize_files(files)

        assert len(normalized) == 1
        assert normalized[0]['url'] == 'https://example.com/file.pdf'
        assert normalized[0]['format'] == 'PDF'
        assert normalized[0]['description'] == 'Full text'


class TestDoiResolution:
    """Tests for DOI resolution with mocked API calls."""

    @patch('ckanext.schemingdcat.lib.doi_resolver._make_request')
    def test_fetch_from_datacite_success(self, mock_request):
        """Test successful DataCite API fetch."""
        mock_request.return_value = {
            'data': {
                'attributes': {
                    'titles': [{'title': 'Test Document'}],
                    'descriptions': [{'description': 'Test abstract', 'descriptionType': 'Abstract'}],
                    'creators': [{'name': 'Test Author', 'givenName': 'Test', 'familyName': 'Author'}],
                    'publicationYear': 2024,
                    'publisher': 'Test Publisher',
                    'types': {'resourceTypeGeneral': 'Text'},
                    'subjects': [{'subject': 'water'}],
                    'language': 'en',
                    'rightsList': [{'rights': 'CC-BY-4.0'}],
                    'dates': [],
                    'url': 'https://example.com/doc',
                }
            }
        }

        result = fetch_from_datacite("10.1234/test")

        assert result is not None
        assert result['source'] == 'datacite'
        assert result['title'] == 'Test Document'
        assert result['abstract'] == 'Test abstract'
        assert result['publication_year'] == 2024
        assert result['publisher'] == 'Test Publisher'
        assert len(result['authors']) == 1

    @patch('ckanext.schemingdcat.lib.doi_resolver._make_request')
    def test_fetch_from_datacite_not_found(self, mock_request):
        """Test DataCite API when DOI not found."""
        mock_request.return_value = None

        result = fetch_from_datacite("10.1234/nonexistent")

        assert result is None

    @patch('ckanext.schemingdcat.lib.doi_resolver._make_request')
    def test_fetch_from_crossref_success(self, mock_request):
        """Test successful CrossRef API fetch."""
        mock_request.return_value = {
            'message': {
                'title': ['Test CrossRef Document'],
                'abstract': 'Test CrossRef abstract',
                'author': [{'given': 'John', 'family': 'Doe'}],
                'published': {'date-parts': [[2023]]},
                'publisher': 'CrossRef Publisher',
                'type': 'journal-article',
                'subject': ['hydrology'],
                'URL': 'https://example.com/crossref',
            }
        }

        result = fetch_from_crossref("10.1234/crossref-test")

        assert result is not None
        assert result['source'] == 'crossref'
        assert result['title'] == 'Test CrossRef Document'
        assert result['publication_year'] == 2023

    @patch('ckanext.schemingdcat.lib.doi_resolver.fetch_from_datacite')
    @patch('ckanext.schemingdcat.lib.doi_resolver.fetch_from_crossref')
    def test_resolve_doi_fallback(self, mock_crossref, mock_datacite):
        """Test DOI resolution with fallback to CrossRef."""
        mock_datacite.return_value = None
        mock_crossref.return_value = {
            'source': 'crossref',
            'title': 'Fallback Document',
            'doi': '10.1234/fallback',
        }

        result = resolve_doi("10.1234/fallback", providers=['datacite', 'crossref'])

        assert result is not None
        assert result['source'] == 'crossref'
        assert result['title'] == 'Fallback Document'

    def test_resolve_doi_invalid_format(self):
        """Test DOI resolution with invalid DOI format."""
        result = resolve_doi("invalid-doi")

        assert result is None

    @patch('ckanext.schemingdcat.lib.doi_resolver.fetch_from_zenodo')
    def test_resolve_doi_zenodo_priority(self, mock_zenodo):
        """Test Zenodo DOI is resolved with Zenodo provider first."""
        mock_zenodo.return_value = {
            'source': 'zenodo',
            'title': 'Zenodo Document',
            'zenodo_id': '1234567',
        }

        result = resolve_doi("10.5281/zenodo.1234567")

        assert result is not None
        assert result['source'] == 'zenodo'
        mock_zenodo.assert_called_once()

    @patch('ckanext.schemingdcat.lib.doi_resolver.fetch_from_datacite')
    def test_resolve_doi_normalizes_files(self, mock_datacite):
        """Ensure DOI resolution deduplicates and secures file links."""
        mock_datacite.return_value = {
            'source': 'datacite',
            'doi': '10.1234/test',
            'url': 'http://example.com/landing',
            'files': [
                {'url': 'http://example.com/file.pdf', 'format': 'pdf', 'description': 'PDF'},
                {'url': 'http://example.com/file.pdf', 'format': 'UNSPECIFIED', 'description': 'duplicate'},
                {'url': 'http://localhost/internal', 'format': 'html'},
            ],
        }

        result = resolve_doi("10.1234/test", providers=['datacite'])

        assert result is not None
        assert result['url'] == 'https://example.com/landing'
        assert len(result['files']) == 2

        urls = {f['url'] for f in result['files']}
        assert 'https://example.com/file.pdf' in urls
        assert 'http://localhost/internal' in urls  # local URLs stay http

        pdf_entry = [f for f in result['files'] if f['url'].endswith('file.pdf')][0]
        assert pdf_entry['format'] == 'PDF'
        assert pdf_entry['description'] == 'PDF'

    @patch('ckanext.schemingdcat.lib.doi_resolver._make_request')
    @patch('ckanext.schemingdcat.lib.doi_resolver.requests.get')
    def test_fetch_from_crossref_prefers_pdf_from_landing(self, mock_get_html, mock_get_json):
        """Prefer PDF discovered on landing page over broken CrossRef link."""

        class DummyResp:
            def __init__(self, text, url, status_code=200):
                self.text = text
                self.url = url
                self.status_code = status_code

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise Exception(f"HTTP {self.status_code}")

        mock_get_json.return_value = {
            'message': {
                'title': ['Test CrossRef Document'],
                'abstract': 'Test CrossRef abstract',
                'author': [{'given': 'John', 'family': 'Doe'}],
                'published': {'date-parts': [[2023]]},
                'publisher': 'CrossRef Publisher',
                'type': 'journal-article',
                'subject': ['hydrology'],
                'URL': 'http://example.com/view/18',
                'resource': {'primary': {'URL': 'http://example.com/view/18'}},
                'link': [
                    {'URL': 'http://example.com/download/18/18', 'content-type': 'application/pdf'},
                ],
            }
        }
        mock_get_html.return_value = DummyResp(
            '<meta name=\"citation_pdf_url\" content=\"/article/view/18/86\">',
            'http://example.com/view/18',
        )

        result = fetch_from_crossref("10.1234/test")

        urls = {f['url'] for f in result['files']}
        assert 'https://example.com/article/view/18/86' in urls
        assert not any('download/18/18' in u for u in urls)

    @patch('ckanext.schemingdcat.lib.doi_resolver._make_request')
    @patch('ckanext.schemingdcat.lib.doi_resolver.requests.get')
    def test_fetch_from_crossref_skips_untyped_link_when_pdf_from_landing(self, mock_get_html, mock_get_json):
        """Skip ambiguous links without content type when a PDF is already found."""

        class DummyResp:
            def __init__(self, text, url, status_code=200):
                self.text = text
                self.url = url
                self.status_code = status_code

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise Exception(f"HTTP {self.status_code}")

        mock_get_json.return_value = {
            'message': {
                'title': ['Test CrossRef Document'],
                'abstract': 'Test CrossRef abstract',
                'author': [{'given': 'John', 'family': 'Doe'}],
                'published': {'date-parts': [[2023]]},
                'publisher': 'CrossRef Publisher',
                'type': 'journal-article',
                'subject': ['hydrology'],
                'URL': 'http://example.com/view/18',
                'resource': {'primary': {'URL': 'http://example.com/view/18'}},
                'link': [
                    {'URL': 'http://example.com/download/18/18'},
                ],
            }
        }
        mock_get_html.return_value = DummyResp(
            '<meta name="citation_pdf_url" content="/article/download/18/86">',
            'http://example.com/view/18',
        )

        result = fetch_from_crossref("10.1234/test")

        urls = {f['url'] for f in result['files']}
        assert 'https://example.com/article/download/18/86' in urls
        assert not any('download/18/18' in u for u in urls)


class TestIntegration:
    """Integration tests (require network access, marked for skip by default)."""

    @pytest.mark.skip(reason="Requires network access")
    def test_real_datacite_fetch(self):
        """Test real DataCite API call."""
        # Using a well-known stable DOI
        result = resolve_doi("10.5281/zenodo.3509134")
        
        assert result is not None
        assert 'title' in result

    @pytest.mark.skip(reason="Requires network access")
    def test_real_crossref_fetch(self):
        """Test real CrossRef API call."""
        # Using a well-known stable DOI
        result = resolve_doi("10.1038/nature12373")
        
        assert result is not None
        assert 'title' in result
